# R080 Ascend State checker：有限独立代码审阅

本次仅审新增离线 qualification checker。首轮源码有三个 confirmed major 的假通过路径，以及一个会误拒实际 transfer 形式的 minor；不支持按首轮源码签署 State writer 整体资格。未发现产品 runtime/native 被本 delta 修改，也未将代码走查扩成 LLVM/ISA 全解释器。

## 阅读、身份及未运行范围

- 完整阅读候选 `tests/timeline/ascend_state_writer_partition.py`、`test_ascend_state_writer_partition.py`。观察时 HEAD 为 `ebf5237bd775eed6e93d0be35f4d6e0639769c63`，两文件尚未提交；helper SHA256 为 `fed3118676ca98ee9c49aabb9cddc7d205f6a8f46f0d844a566b77a6f46b3058`，测试为 `505b7e2f2fae29b5b73bbe8d43869cdfbdacb9913f82527658ef0303219a4994`。以下行号均对应这个首轮快照。
- 阅读 `preflight/ascend-ordinary-lowering-poll-v2.json` 的真实终态，以及 `ascend-byte-bound-callers-v1.json` 的数据结构和实际 actor/transfer 片段。该 JSON 有 20 个 distinct code-object 记录。本次没有重新完成对其中全部 LLVM 的逐指令审计。
- 不读 peer；不执行 helper、测试、产品 import、SDK、编译器、数学、设备、模拟器或服务器任务。仅本地读源码、Git 身份、JSON 与 SHA。下面反例均为静态语义推理，未冒称本机复现。
- 沿用请求 GPT-6.1-Sol / xhigh；实际 resolved 型号和推理档位未暴露，记为未知。

## Confirmed major

### M1：未知的 State 消费指令可能静默漏掉真实写入

**位置。** helper 183–210 行的 State 使用/逃逸扫描，只对包含 `call` 的 operation 和 `store ` operation 作处理。

**触发。** 在正常、覆盖完整 State 的 transfer 旁加入合法 LLVM 指令，例如：

```llvm
%old = atomicrmw add ptr addrspace(1) %state, i32 1 monotonic
```

或同类 `cmpxchg`。指令可被 `_parse` 当作普通有结果 operation 收录；如果结果不被地址/分支锥使用，不会进入 `operation` 求值。State 预扫描也不处理它，所以正常 transfer 的 range/count 原样返回，额外 State 写入被忽略。

**推理与后果。** 此问题来自 State-use 的漏项，不依赖未定义 SSA、错误地址宽度或参数 alias。实际登记代码未被证明存在这条额外写入；但首轮 checker 的“未知 State 逃逸/写入失败”边界没有按代码实现。SDK 对 particular atomic opcode 的目标支持仍由输入验证链约束，本修复无须要求 SDK 支持或运行它。

**最小修正与 negative。** 对含有 State provenance 的 operation 建立封闭的允许列表；未建模 State-use 指令直接 unverified/reject。无需解释 atomic 语义。加入正常 transfer 之外的 `atomicrmw`（以及可选择的 `cmpxchg`）负例，要求在 range/count 返回前明确拒绝，保留正常 transfer，不能通过删写入来触发其它错误。

### M2：分支求值将已检测到的 poison 降为未知条件

**位置。** helper 277–299 行明确检测整数 poison，但 306–312 行捕获所有 `ValueError` 并继续保留两个 CFG 分支。

**触发。** 用类型正确的 SSA 在分支条件内产生已知 poison，并让两臂重新合流到同一个正常 State transfer：

```llvm
%bad = add nsw i8 127, 1
%condition = icmp eq i8 %bad, 0
br i1 %condition, label %left, label %right
left:
  br label %write
right:
  br label %write
write:
  ; 原正常 State transfer
```

这里 `%bad` 仅用作 i8，不依赖跨宽度非法引用。`integer` 在求值时会检测有符号 overflow 并抛 `Signed poison arithmetic`，但分支处理吞掉该错误。保留两条边后，共用 writer 仍支配所有 return、也不在循环中；于是地址正常的 transfer 会返回完整 writer 计数。实际以 poison 作为 `br` 条件不能作为合法确定执行来认证。

**后果。** checker 具备的 poison 检测对控制锥失效；“无法知道条件，但两路都安全”与“已知条件使用非法/poison 值”被混成一种结果。

**最小修正与 negative。** 区分未知/未支持锥与已知 poison/非法整数操作；后者在控制锥必须使整个分析拒绝。无需解释浮点或所有 LLVM 指令。加入上述两臂汇合同一正常 writer 的合法 i8 SSA 负例，确认不会因 writer 的 CFG postdom 检查通过而接受。

### M3：接受 `inbounds` GEP，却丢失中间越界造成的 poison

**位置。** helper 300–303 行允许 `getelementptr inbounds i32`，但只累计 Python 整数偏移，没有检查该带约束的中间指针是否仍在对象内或 one-past。

**触发。** 对已知 `elements=3` 的 State，在实际 State transfer 前使用：

```llvm
%outside = getelementptr inbounds i32, ptr addrspace(1) %state, i64 4
%back = getelementptr i32, ptr addrspace(1) %outside, i64 -4
```

transfer 的 allocated/aligned State operands 均替换成 `%back`，保持原 block offset 和尺寸。checker 将 `%outside` 记为 State+16B，再将 `%back` 记成 State+0B，最终 range/对齐/根检查均可通过。实际前一个 `inbounds` 已超过三元素分配的 one-past 边界，不能通过后续普通 GEP 恢复为有效非 poison 指针。

**后果。** 最终数值地址合法不等于中间带 `inbounds` 约束的计算合法，可能为已无有效指针语义的写入授予分区结论。

**最小修正与 negative。** 对 State 的已知分配界限检查每一步 `inbounds` 派生（允许 one-past），或保守拒绝不能证明的 `inbounds`，无需推广到未知对象的一般 alias/对象大小分析。加入上述“越界再回到原址”的负例；另保留合法 zero GEP，以及 one-past 后回到对象内的正例，避免把本问题修成全禁 GEP。

## Confirmed minor

### m1：constructed-GM 正则会跨 call 参数误拒真实 UB→GM transfer

**位置。** helper 186 行的 `\binttoptr.*ptr addrspace\(1\)`。

**实际证据。** `ascend-byte-bound-callers-v1.json` 的实际 q06 user actor 有 `store_ubuf_to_gm_2d_int32_t` 调用：前面的 UB operands 为 `ptr addrspace(6) inttoptr (... to ptr addrspace(6))`，后面的目的 operands 为 `ptr addrspace(1) %8`。这个正则从前面的 `inttoptr` 贪婪跨到后面的 GM 形参，虽然该 conversion 本身的结果只是 addrspace(6)，仍命中拒绝条件。

**后果。** 合法、已保留的原 transfer 调用会被误记为 constructed-GM pointer，不是 unsafe acceptance。当前正例执行尚未见终态，不能因此声称已通过实际 32 报告。

**最小修正与验证。** 按单个 typed operand 或准确 conversion 的 result type 判断，禁止跨到后续参数；以该实际 retained call 形式作 positive，同时保留真正 `inttoptr ... to ptr addrspace(1)` 的 negative。无需新的 SDK 编译或数学矩阵。

## Confirmed blocker / optional

本次没有另列 blocker 或 optional 项。上述 major 均限于本离线 checker 的判定健全性，不指称实际数学结果或产品 runtime 已错误。

## 有限范围未证与已有事实

已有 `ascend-ordinary-lowering-poll-v2.json` 显示真实 CPU lowering terminal 0，耗时 73.570988377 s，预算 300 s；32 registered / checked / bound，20 distinct byte-bound code objects，19 new CPU compiles、13 reuse。结果明确 `device_executed=false`、`mathematical_application_replayed=false`、`SDK_rebuilt=false`、`product_runtime_changed=false`，并且 **`state_writer_qualified=false`**。这些是原件与 codegen 输入身份事实，不是本新 checker 已通过的替代收据。

helper 的 API 明确返回单个 actor 函数的 `element_writers` multiplicities，并允许 nonwriting actor；因此不将“函数自身没有要求每个元素都出现”列为缺陷。整体 caller 仍需聚合实际 actor 函数/实例，核每元素恰一次、无 tail 写入，并将 State formal、grid 参数及物理 subblock extent 与实际 launch 主体绑定。caller 提供的 `subblocks` 不能从缺失 slots 推断；本报告没有自行证明它。

1D/2D transfer 的参数定位与 int32 每元素四字节模型，是本有限算法的输入合同。真正 SDK transfer implementation 对 allocated/aligned/offset、源/目的 size/stride、模式 0 的作用及 launch/actor 主体关系仍按请求保留 pending；不能因为函数名匹配、Python 枚举无重叠就把 ABI 关联升格为已证。此次也没有将未知浮点 helper 或 native 调度纳入解释。

源码中原有保守边界包括：SSA 名称重复拒绝、必要求值 definition 支配 use、未知整数/指针锥拒绝、State transfer 不能绕过实际 return 或重复在 cycle 中、物理 actor/grid 与元素枚举预算。它们有工程价值，但不抵消本报告的具体遗漏。测试代码存在正反例，实际终态尚未提供；在首轮 snapshot 上不能冒认 CPU fixture 或全部 32 原件已通过。

## 最小下一步及有限结论

修正 M1–M3 与 m1，加入对应有限语义反例/实际 positive，然后复用同一批 byte-bound 原件做 CPU 离线验证，准确绑定新源码和结果即可；本报告不要求新数学、设备或 SDK 矩阵。第三方 transfer ABI、launch 主体和聚合范围的既有 pending 独立保留。在上述修正与匹配收据到达前，不支持签署此 checker 的健全性或 Ascend State 整体资格。
