# R080 Ascend State checker：原缺陷修复的有限 v2 复核

本次只复核 v1 的 M1/M2/M3/m1 修复及对应新增测试，不重开整体审阅。完整读取当前两个文件，未运行检查器、pytest、产品、SDK、编译器、数学或设备，不读 peer。实际观察源码 SHA256：helper `bde4b02ede637f5f4ed8e8dd3256ce47ecb34c3c3cbd61c49a49805e31713351`；测试 `c9f854c74d1595b97d4513083d7c1f56852ffcd4b807af413b5e6f8a316231f6`。以下行号对应该未提交快照。请求配置 GPT-6.1-Sol / xhigh；resolved 未暴露，记为 unknown。

以下保留 v2 首次复核的两个剩余问题及修复过程；末尾的 matching v4 追加已关闭这些具体 checker 缺陷及负例准确性问题。SDK actor / transfer ABI 与 State 整体资格仍待证明。

## 原缺陷源码修复进度

- **M1 已覆盖原具体根因。** helper 217–218 行对未在 call/store 分支处理、但含有 State provenance 的指令使用封闭允许规则；`atomicrmw`、`cmpxchg` 不在允许集合内。测试 107–113 行保留原正常 transfer 并加入额外原子写，预期直接拒绝未知 State-use；不会因删去原 writer 或无 State writer 而掩盖缺陷。
- **M2 已覆盖原具体根因。** `UnknownCone` 与普通 `ValueError` 分开，branch 324 行仅捕获前者；已知 nsw/nuw overflow、除零等检查仍抛普通错误，不再被降格为未知条件。测试 116–120 行是类型正确的 `add nsw i8` → `icmp i8` → 两臂合流同一正常 transfer，确实对应 v1 的假通过路径。原地址 poison 测试 74 行也修成 i8 结果显式 sext 到 i64，不依赖不合法 SSA 跨宽引用。
- **M3 只覆盖了一种方向，仍有同根因漏项，见下文。** 当前会检查 `inbounds` 的结果位置，并新增 one-past 正例 / beyond-one-past 负例；但没有检查该 `inbounds` 的基指针位置。
- **m1 的实际 UB→GM 误拒已覆盖，但 constructed-GM guard 有括号 constexpr 漏项，见下文。** 新 regex 不再跨 UB conversion 后的 GM 目的形参；测试 134–136 行保留 AS6 `inttoptr (...)` 加 AS1 State destination 的实际形式。

`_split('')` 现在返回空列表，使无参数 BLOCK/SUBBLOCK helper 不再被误记为一个空参数。每 actor 在 pruning 后要求存在 reachable return，避免已解析条件只留下不返回路径时仍计为 solved actor。这两项是有限机械修正，没有放宽原 writer 路径规则。

## Confirmed major：M3 的 reverse 形式仍可假通过

**位置。** helper 311–317 行，特别是 315–316 行只约束 `result.byte_offset`。

**触发。** 对三元素 State，用以下合法 SSA 形式替换测试中的两步 GEP，并让实际 transfer 使用 `%back`：

```llvm
%outside = getelementptr i32, ptr addrspace(1) %state, i64 4
%back = getelementptr inbounds i32, ptr addrspace(1) %outside, i64 -4
```

第一步不带 `inbounds`，可计算出分配外地址而不因此产生该约束的 poison；第二步的 base 已超过 State 的 one-past。`inbounds` 不能以这个越界 base 仅凭最终回到 offset 0 就成为有效派生。当前实现第一步不检查，第二步只看到 `result.byte_offset=0`，于是原最终 range/count 可通过。这仍是 v1 M3 的“中间指针语义不能由最终数值恢复”问题，非新增 LLVM/ISA 覆盖要求。

**后果。** 原 M3 不能按当前结果位置检查关闭。

**最小修正与 negative。** 在已知 State 分配上同时要求 `base.byte_offset` 和 `result.byte_offset` 均位于 `[0, elements*4]`，允许 one-past；在现有 intermediate GEP fixture 加上述 reverse negative，并保留合法 one-past 后回到对象内的 positive。无需新增 SDK 编译或数学矩阵。

## Confirmed minor：GM pointer guard 未覆盖带括号 constant expression

**位置。** helper 192 行。

**触发与推理。** 新 regex 要求 `inttoptr` 后直接为 `iN`，因此不能识别合法 LLVM operand `ptr addrspace(1) inttoptr (i64 42 to ptr addrspace(1))`。这种 operand 本身没有 formal provenance，call 扫描可能按“没有 State uses”跳过；它没有经过原本的 constructed-GM pointer 拒绝规则。

这不是已证明登记原件发生 alias，也不声称数值 42 等于实际 State 分配地址；问题是本次 guard 改写后，原先明确拒绝的未模型 constructed-GM 输入有一种直接表示形式漏掉了。若输入合同固定排除所有 constructed-GM pointers，应在 checker 中保持该边界，不能依赖一个未声明的常量地址 alias 假设。

**最小修正与 negative。** result-type 识别同时覆盖指令及带括号 constexpr，仍不得跨到 call 后续参数。增加一条 GM constexpr 拒绝例；现有 AS6 constexpr + AS1 State destination positive 保持。无需解释常量地址或做通用 alias 分析。

## Confirmed blocker / optional

本有限修复复核没有另列 blocker 或 optional。M1/M2 的原问题在源码层已覆盖；M3 和上述 guard 表示形式仍需最小修正。未据此推断产品 runtime 或已完成数学错误。

## Verification gaps 与有限结论

新增测试与原测试合计 30 个 fixture。root 已启动 normal / `-O` 及原 32 实际 caller 的 CPU 检查，但本次尚未读取修正版准确终态，因此不认执行闭环，也不以旧 lowering 成功替代 checker 成功。

SDK transfer ABI 对这些描述符字段的实际作用、launch 主体与物理 actor extent 绑定、各 actor multiplicity 聚合为整体唯一 writer 的原 pending 保持。此复核不要求全 LLVM 解释器、新 SDK 或数学矩阵，不授 Ascend State 整体资格及 whole-goal。最小下一步仍是上述两处有限修正、相应语义例及同批原件 CPU 收据。

## 两处剩余问题修正后的有限追加

再次读取实际修改区域及新增测试，观察到 helper SHA256 `9c044bda86733e4c422ba98217a7a3382eda934c57bc88e39014d655c597b3fe`、测试 `3a854e1d6eeaf634d41b6a946fa9bfbb7b2acf7d08d732551723b53910d377fc`。此时格式化仍在进行，未将其当最终冻结身份。

helper 422–426 行现在同时检查 State 的 inbounds base 和 result 均位于 `[0,elements*4]`，保留 one-past；新增 reverse fixture 确实先以普通 GEP 到 outside，再用 inbounds GEP 回原位，应因 base 越界拒绝。M3 两个方向的具体源码原因均已覆盖。

constructed-GM 正则加入可选 opening parenthesis，识别 instruction 与 constexpr 的具体 result type；AS6 UB constexpr 后跟 AS1 State destination 不会被跨参数匹配，而 AS1 constexpr 会拒绝。m1 的实际误拒及后续表示漏项在源码层均已覆盖。

新增 GM constexpr negative 还有一个小的 **fixture 准确性问题**：它把真实 transfer 的 AS6 源参数直接替成 AS1 常量，若按原函数声明验证 LLVM，会存在参数类型不匹配。虽然当前 checker 的 `pointer` 拒绝确实来自 guard，建议只将这个 fixture 改成在原 sample body 附加 `call void @unknown(ptr addrspace(1) inttoptr (i64 42 to ptr addrspace(1)))`，保留完整正常 State transfer，并为外部函数使用匹配声明。该形式可构成类型合法的 LLVM，旧 guard 会因没有 formal roots 而跳过此 call，新 guard 明确拒绝；无需 SDK 执行或新增矩阵。这是目标负例的准确性修正，不是新产品门。

另已读取 `ascend-state-partition-poll-v2.json`：实际 terminal 0、`wall_ns=2919504453`、120 秒预算，32 registered / checked / partitioned，failures 为空，明确 `state_writer_qualified=false`。该收据绑定的是此前 `bde4b02e...`，不能直接用于关闭后来 `9c044bda...` 修复及新增 reverse/constexpr 反例。此次未读取新版本的最终 fixture 日志，故不冒认最新执行成功。

**最新有限结论：原 M1/M2/M3/m1 的具体源码根因均已覆盖，小修复未发现新的具体 checker false-pass。** 最终 source/fixture matching 的 CPU 收据以及上面一个 negative 的合法类型形式仍需准确闭合；SDK transfer ABI、launch 主体与 State 整体资格的 pending 不变。没有扩大 LLVM/ISA 或数学验收范围。

## 最终测试字节与 state-partition-v4 的有限 closure

本次追加核对 candidate 两文件与 `preflight/ascend-state-partition-input-v4.tgz` 的实际成员逐字节一致。helper 仍为 `9c044bda86733e4c422ba98217a7a3382eda934c57bc88e39014d655c597b3fe`；最终测试 SHA256 为 `78c31240ced96ffddd73eb863bd79654f4c66282c61e97de77ac5c9ca8570cb3`。输入归档 SHA256 为 `3a697e6ff70311d27ba9a5bc522ea92f36379ba9503ed2bb7e6152cd5695c22c`。

最终 GM constexpr negative 已改成独立 `@unknown(ptr addrspace(1) inttoptr (...))` 外部调用，保留原正确类型的 State transfer；不再将 AS1 常量塞入真实 helper 的 AS6 参数。它可以放在具有匹配外部声明的合法 LLVM 上下文中，旧 guard 会因无 formal provenance 跳过，新 guard 则明确拒绝。前述 fixture 准确性问题已关闭。atomic/cmpxchg、正确 i8 poison branch、正向及 reverse inbounds、one-past 和 UB constexpr positive 均保留。

已实际读取 `preflight/ascend-state-partition-poll-v4.json`：terminal returncode 0，`wall_ns=2919602164`（2.919602164 s），实际预算 120 s；32 registered / checked / partitioned，failures 为空，checker SHA 与当前相同。摘要明确 `state_writer_qualified=false`、`device_executed=false`、`mathematical_application_replayed=false`、`source_loaded_qualification_tool=true`。

归档内 runner SHA256 为 `7d71301014d36e3320d3a3f68d1632230d1c8ca9ce8a9a1182b1b069a8b379d2`，与 terminal `script_sha256` 相同。独立阅读其控制流可见：它先依次执行最终 32 个 fixture 的 normal 和 `-O` pytest，任一 child 非 0 即抛错，随后才分析原 32 个 caller 并输出结果；因此这个 matching terminal 0 支持两条 fixture 路径及同批 caller 实际成功。完整 fixture stdout 日志仍在回收，本次未读到它们，不编造日志逐字内容或额外运行时测量。

此 runner 的 caller 聚合是在**显式模型**内进行：原 math/TTIR、保留 codegen 结果和 source SHA 对照，实际函数摘录与保留输入逐行相等，按提供的 actor/subblock 模型聚合各 State 元素恰一次，并明确把 physical transfer ABI qualification 留作 pending。该终态没有自动建立 hidden GM prefix、物理 actor extent 和 SDK transfer 实现语义的整体资格。

**有限结论：本报告原 M1/M2/M3/m1 及后续 negative 准确性问题，已按 matching 源码、目标反例和 v4 CPU 执行闭环关闭。** 没有新增产品 runtime/native 变化或 GPU/math replay；本结论只关闭 checker 的这几项具体缺陷。SDK actor / transfer ABI、launch 主体与 Ascend State 整体资格仍 pending，不作 whole-goal 签字。

### 完整 fixture 日志回收后的最终补核

已实际读取 `preflight/ascend-receipts-v1/runs/state-partition-v4/output/fixtures-normal.log` 与 `fixtures-optimized.log`：分别明确 **32 passed in 0.07s**、**32 passed, 1 warning in 0.08s**；后者为预期 pytest `-O` assertion warning。并逐字节比较回收的 `state-partition-input-v4/` 两源码与当前 candidate，均相等，SHA 与上述 `9c044bda...` / `78c31240...` 一致，也与 `integration/evidence/timeline-state-ranges-r080/executed-source-bindings.json` 相等。最终合法 GM constexpr fixture、matching terminal 和 normal / `-O` 原始日志的有限闭环已直接核实，不再保留“完整 fixture stdout 尚未读取”的缺口。原 SDK actor / transfer ABI、State 整体资格及 whole-goal pending 完全不变。
