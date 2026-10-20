# R078 NVIDIA State writer partition：有限独立代码审阅

本报告仅审离线 qualification helper，不是 whole-goal 或其它后端签字。旧版本有三个可由有限、合法 PTX 触发的 false-pass 问题，以下保留其首次审阅记录。末尾追加的冻结修正版及 matching v9 收据已关闭这三项具体缺陷，并支持登记材料的 NVIDIA V1 State writer 有限子门。没有证据表明实际 40/118 份原件曾发生错误 State 写入，也没有用正例计数代替缺陷反例。

## 阅读与身份

- 完整阅读候选 `tests/timeline/nvidia_state_writer_partition.py`、`test_nvidia_state_writer_partition.py`，以及 `run-078/preflight/check_nvidia_writers_v6.py`。
- 读取 `nvidia-writers-poll-v7.json` 和 `nvidia-writers-input-v6.tgz` 的成员、源码与 SHA。归档 SHA256：`23c88c8ffc03edd81a07cb370b7e144df434cd50501cc0430a35ad46a7b1316b`。归档 helper 为 `47bb62a729054ceed69f2ef765cf001163291d0421f579f9ac2af0fab7295afc`，runner 为 `aaa55f9be45747eada68005243621af959f59b3314f086cc11e6b5a515c525f6`。
- 审阅期间首次观察到的修正版 helper 为 `735b8dd90375f597472bf8e1be19baddc27e7688a090d7bc653c461c1b59db61`；测试为 `9a9dbee8e868f3a83c06cedc64093fc91da7e12e677301f7ae26290fb6352ab5`。这两文件均未提交；观察时 candidate HEAD 为 `8ede89f833eb71f1ed07d520fe84e54cde1a9aa9`。下述首轮“当前行号”对应这个 helper 快照；后续修复另列快照。
- 未读 peer 报告；未运行 helper、pytest、产品 import、编译器、SDK、数学、设备、TP 或服务器任务。仅本地读文件、归档、Git 身份及哈希，反例结论来自代码和 PTX 整数语义的静态推理。
- 原请求配置为 GPT-6.1-Sol / xhigh；实际 resolved 型号和推理档位未暴露，记为未知。

## Confirmed major

### M1：文本最近定义不能代表 CFG reaching definition；可能漏掉真实 State store

**位置。** 归档 helper 的 `evaluate` 183–188 行、`pointer_roots` 139–150 行；对应当前修复区域为 `reaching_definitions` 161–181 行、`pointer_roots` 197–212 行、`evaluate` 244–250 行。

**触发与推理。** 旧实现用 `bisect_left(definitions, use)-1` 选文本上最近的定义，再验证其支配 use。支配并不排除路径上另一次覆盖，尤其是文本位置在 use 后、CFG 中却先执行的定义。例如保留原 scalar 地址和 State store，将代码组织为：

```ptx
mad.lo.u32 %r3, %r2, 4, %r1;
bra later;
target:
mul.wide.u32 %rd2, %r3, 4;
add.u64 %rd3, %rd1, %rd2;
st.global.b32 [%rd3], {%r1};
ret;
later:
mov.u32 %r3, 0;
bra target;
```

这是无环 CFG，所有实际返回均经过 store，store 也不在循环内。旧 checker 为 `%r3` 选择入口 `mad`，得到 `tid`，从而认为四线程唯一覆盖四元素；实际每个线程在 store 前都执行 `mov %r3,0`，均写 State[0]。

`pointer_roots` 的同一问题还会在分类阶段隐藏额外写入：先完成正常 State 分区，再令地址寄存器保存 State 地址，随后用恒 false 谓词执行 `mov.u64 address, Out`，最后再次 store。旧根分析只看到最近的 Out 定义，跳过该 store；实际 false 谓词保留 State 地址，形成重复写入。各参数独立分配不能消除这种直接寄存器 provenance 替换。

**后果。** 可以将重复或缺失 State writer 误报为完整唯一分区；这不是仅有保守拒绝。

**源码修正进度。** 当前快照沿真实 CFG predecessors 反向找全部 reaching definitions，遇无条件定义停止，遇有条件定义继续保留旧定义；求值要求唯一、非 undefined、非 predicated 的实际定义；根分析合并所有候选。这覆盖上述两个具体漏洞的源码原因。未把当前源码修正当成已执行闭合。

**最小验证。** 加入上述无环“文本后置但实际先执行覆盖”及 false-predicate State→Out 根分类两条反例，要求保留 store 后明确拒绝；随后用同一批 40/118 份原件进行离线定向复核。

### M2：接受 opcode 前缀却没有实现修饰符语义

**位置。** 归档 helper 195、221–224、241–253 行；当前修复为 `_ARITIES` 25–52 行及 257 行的精确 opcode/arity/单目标校验。

**触发与推理。** 旧实现接受所有 `mul.*`，却一律计算低乘积。将 scalar index 替换成 `mul.hi.u32 %r3,%r1,1` 后，checker 仍得到 `tid` 并通过；实际高 32 位恒为 0，四线程重复写 State[0]。旧实现也接受 `setp.lt.and.u32 %p1,%r3,4,%p2`，但仅比较前两个 operand，忽略组合谓词 `%p2`；当 `%p2` 恒 false 时，会将实际无写入的 store 算作有效 writer。

**后果。** 未实现的模式能够假通过，`Unsupported ...` 的承诺没有在这些输入上兑现。

**源码修正进度。** 当前快照使用精确白名单及 arity，拒绝 `.hi`、组合 setp、carry/saturating 等未实现形式和非单一目标，不要求实现所有 PTX。该路线覆盖上述两个反例；旧 14 项测试及 v6 收据尚未覆盖它们。

**最小验证。** 各保留一条 `mul.hi` 和恒 false 组合 setp 的语义负例，要求明确拒绝，并完成同批原件的修后离线复核。

### M3：已支持的无符号源 operand 没有先按字宽归一化

**位置。** 当前 helper `evaluate` 237–238 行读负立即数，283–286 行处理 `mul.wide.u32`，291–296 行处理 `shr.u32/64`。旧归档也存在同一问题。

**触发与推理。** Python 负整数不是 PTX 无符号 word。当前逻辑仅在运算后 mask 结果，无法修复逻辑右移和宽乘输入的区别。例如用以下三条计算 scalar index，再接原 `mul.wide.u32`、地址加法、State store：

```ptx
shr.u32 %r4, -1, 31;
add.u32 %r3, %r1, %r4;
add.u32 %r3, %r3, 1;
```

checker 执行 Python `-1 >> 31`，再 mask 得 `0xffffffff`，最终 `%r3=tid`，会接受四元素唯一覆盖。实际 PTX 将 `-1` 解释为 u32 word `0xffffffff`，逻辑右移得 1，最终 `%r3=tid+2`，漏 State[0..1] 且写过尾部。

同类例子是 `mul.wide.u32 %rd4,-1,1; add.u64 %rd4,%rd4,1`：checker 得 0，实际 unsigned 32→64 宽乘后得到 `2^32`。将其加到正常 State store 地址，会把实际偏移 4 GiB 的写入误记为原地址。

**后果。** 精确 opcode 白名单内仍可假通过；不是需要新增 ISA 覆盖的情况。

**最小修正与验证。** 仅对已支持算式按其源 operand 类型先作 word 截断，signed 源再作符号解释；尤其修正 unsigned 右移和 `mul.wide.u32`。对上述两条保留 store 的反例要求拒绝错误分区，normal / `-O` 执行，并用同批原件复核。无须实现新 opcode 或重跑数学。

## Confirmed blocker / minor / optional

本次没有另列 blocker、minor 或 optional 项。上述均是离线 qualification checker 的正确性问题，未据此指称产品 runtime 或原数学结果错误。

## 已有执行证据与 verification gaps

`nvidia-writers-poll-v7.json` 实际 terminal 为 0，耗时 31.570308548 s，绑定归档 helper `47bb62a7...` 和 runner `aaa55f9b...`，登记并通过 40 ordinary、118 profile，共 72 distinct partitions。runner 显式执行原 14 项 fixture 的 normal / `-O` 两条路径；terminal 成功能支持这些原测试成功，不能支持尚未加入的反例。

身份方面，runner 检查 ordinary frozen math report 与对象 SHA；profile 对照 R059 登记 capture SHA、保留对象 SHA，并检查 PTX/CUBIN 与 math `asm_sha256` 相等。State 位置来自 retained TTGIR 的命名 pointer 参数，线程数来自 math 的 warps 与 PTX `reqntid` 对照，grid 与 frozen math 相等。此有限服务确实使用实际 retained PTX 和 launch geometry，不是从正 duration 推断 writer。helper 也明确保留 `native_sass_semantics_verified=False`、`device_executed=False`。

仍需新收据精确绑定修正后的 helper 和新增反例。现有 v6 成功不能直接继承为修正版成功，也没有必要因这次离线修复增加 GPU/SDK/math 矩阵。

本报告接受已声明的独立分配前提：State、数学输入/Out、隐式 scratch/recorder 对象不别名。非 State 参数根可跳过，不等于提供通用 alias 证明；直接 State provenance 的替换或不确定根仍必须被保守处理。没有将本 helper 扩成全部 SASS 解释器，也不据此放行 GCU/Ascend、ordinary pipeline、source timing 或 whole-goal。

## 有限结论

这个 helper 的方向及实际 PTX/数学/capture 身份链符合本次有限目标；旧快照有上述三个 confirmed major，不能按现有正例计数直接签其判定健全。M1/M2 当前源码路线已覆盖具体根因，M3 仍需修正及语义反例，之后只需同批原件与修正反例的离线执行闭环。本报告不要求新增数学矩阵，也不提升任何原有未闭产品资格。

## 三项修复的有限源码追加

再次完整读取 helper 与新增测试，实际 SHA256 分别为 `5f8d53f745ec19e73b5d937beb553104cefcc959f51d16355d7970ec30e8849f`、`99eaed4700b4de0ae1b6ec8ae4f9c7eef6ad9bf9cd92043aa27f2604cb96702a`。没有执行测试或产品。

M1 的 CFG reaching-definition 修复保持：求值与根分类共享真实 predecessors，条件定义保留旧定义，求值拒绝多定义/undefined/predicated 定义。测试 78–79 行的 later-text address/predicate 反例确实是无环 CFG，实际定义先于目标 store 执行；测试 91–101 行保留恒 false Out 覆盖前的 State 地址，不能再通过“非 State 根”跳过额外 store。

M2 的精确 opcode/arity/单目标白名单保持；测试 80–82 行覆盖 `mul.hi`、组合 setp、双 predicate destination，均应走未支持路径，不需要增加这些模式的语义实现。

M3 修复在 helper 259–276 行按源类型先截断 word，predicate 输入要求布尔值；`cvt` 保留单独的源类型转换。unsigned shift 因此不再接收 Python 负 word；signed shift 和 `mul.wide.s32` 再作符号解释。307–316 行将 shift count 按源位宽 clamp。测试 83–84 行与报告的 unsigned negative immediate 反例相符，实际结果应越 State tail，修正版不会再算成原 tid 地址。

三项具体缺陷的**源码修正均已覆盖**，本次小修复未发现新的具体 false-pass。新增八项回归与原十四项合计二十二项；执行闭环仍待准确绑定这份源码或 AST 等价格式化源码的新 normal / `-O` 及同批 40/118 原件收据。旧 v6 成功不用于关闭新增反例。原 whole-goal、其它后端及普通 pipeline 的剩余范围保持不变。

## 冻结 93fc2a0 / writers-v9 最终有限 closure

本次追加独立读取冻结 HEAD `93fc2a091fcf0df051db8be4b3530d208d8dde1b` 的两个完整文件、v9 runner、输入登记、完整 ordinary/profile JSON 检查结果、fixture 日志及 terminal。Git 提交只新增这两个 qualification/test 文件。实际 helper SHA256 为 `eabb1173d46d7545432ba4e644f80b37c1068ab975fb17b6395ba3eccd04eec3`，测试为 `404998ee3d2e0466a97d59eb1c03ecbe6506d518d7bcf77ba2fff2213836c5fd`，两者与归档 `writers-input-v9/` 成员逐字节相等。

最终源码继续采用 M1 的真实 CFG reaching definitions，并拒绝不唯一、undefined 或 predicated 的必要求值定义。`pointer_roots` 205–243 行改为遍历完整依赖闭包后才缓存完整根集合，循环使用 `seen` 截断，且保留 20,000 节点预算；不再将递归中的空部分结果缓存成最终 provenance。special register token 保留 `.x/.y/.z`，避免将 `%tid.x` 截成 `%tid`。这条修正与 M1 的根分类目标一致，没有放宽 State/非 State 分类。

M2 的精确 opcode/modifier/arity/单目标约束在 302–307 行保持；M3 的 typed 源归一化在 309–336 行，signed 宽乘及右移解释、shift count clamp 在 382–407 行保持。冻结测试 97–137 行确实包括八条新增回归，覆盖 later-text 地址和谓词定义、predicated 非 State 指针、未支持乘高/组合谓词/双谓词目标，以及 unsigned 负立即数右移和宽乘。有限静态复核未发现这三项修复的新具体误放行。

实际归档 `preflight/nvidia-receipts-v1.tgz` SHA256 为 `8cfead6fa990d0d3260226282d7890369bc0b6526db003775f33d7b883c02973`。本次用 stdlib 逐核 `receipt-index.json` 的 **241 个登记成员**的 bytes/SHA，全部相符，成员集合也恰好相等；含 index 自身共 **242 个 regular members**，不是 241 个包含 index 的总成员。没有执行其中的脚本。

`nvidia-writers-poll-v11.json` 与归档 terminal 一致：v9 实际使用 runner SHA `bc187f969f5b8989a0c3e9ee5b7ffd2286c2ca60662f0499447a008b2025dc97`，终态 returncode 0，`wall_ns=44240985879`，即 44.240985879 s；实际 `timeout_seconds=120`，不采用早期 300 秒记载。日志明确给出 normal **22 passed**、`-O` **22 passed**；`-O` 只有预期 pytest assertion warning。旧 v7 terminal 1 保留，不能将其 tokenizer 拒绝正例的失败改写为成功。

完整 JSON 结果为：ordinary 40/40 pass（primary 24、runtime-K 8、supplement 8），profile 118/118 pass（affected-six 10、original-six 60、unit-repair 12、supplement-affected 12、supplement-first 24），72 distinct partitions，failures 为空。这里 normal / `-O` 双模式指 **fixture**；158 份原件由本次正常 CPU runner 读取和检查，不声称做了新的数学或设备执行。每项 partition 都保留 `native_sass_semantics_verified=False`、`device_executed=False`，且 `unique_writers == elements`。

v9 runner 的身份链比 v6 更明确：补二 ordinary result 通过已配置的原 freeze SHA 固定；profile 逐项核登记 capture SHA、retained 对象 SHA，以及 actual math 的 PTX/CUBIN SHA，并与 frozen ordinary 比较 shape/config/source/input 和适用的 runtime K。它检查数学记录的 requested launch、输入不变、原 State pass，读取 host-once marker 的 requested_launches=1，在数学记录含 PID 时比较 PID，并保留 marker SHA。独立读取完整结果可确认 118 个 capture 路径/SHA/case/stage 与输入登记逐项相等，118 个 ordinary reference 均对应同批 frozen ordinary report SHA；所有 158 项都具有 host-once 记录。本次未自行重新执行这些检查，也没有将保留 marker SHA 表述成通用 host-execution 证明器。

**结论：M1/M2/M3 按冻结源码、准确语义反例及 matching v9 实际执行证据均已关闭；本报告不再保留这三项的 verification gap。** 在声明的独立参数分配前提下，这足以支持上述登记原件的 NVIDIA V1 State writer 有限子门。它没有修改产品 runtime，没有授予通用 alias、全部 SASS 语义、GCU/Ascend writer、source/loop、ordinary pipeline 或 whole-goal 资格；这些范围不因本次 closure 自动改变。
