# R082 GCU State checker：有限独立 compiler review

本次只审 qualification checker、fixture 和对应 retained 输入/CPU 收据，不作 State 整体或 whole-goal 签字。初读发现两个 confirmed major：signed remainder overflow 被算成正常零，以及未知指针来源的空 roots 可能隐藏写入。以下保留原问题与修复过程；末尾 matching 冻结源码 / v4 追加已关闭这两个具体缺陷，SDK/launch/State 整体资格继续 pending。

## 阅读、身份与未覆盖范围

- 完整阅读 `tests/timeline/gcu_state_writer_partition.py`、`test_gcu_state_writer_partition.py`，阅读实际 runner、v1/v2/v3 poll 及输入 v1/v2 归档。观察时 candidate HEAD 为 `6e6fa4ac2bb256763e493529f5afd3d89fd0bc5b`；两个新增文件未提交。
- 初读 helper SHA256 `9a4352397cf98260387d94a1b821e9b560baf900c69e31e87c823db51a0479d5`，测试 `a80671737f6bf06a94dc4b5c4948b35ca41d0d0d2eb2bdc890eb7cb427c26d44`，与 input-v2 归档身份相同。归档 SHA256 为 `9ae87fe119736a68b929fa0bd341b886b32273c6ffd18e96aa5c7703913e9d88`。
- 随后有限读取相对 input-v2 的源码增量，观察到 `c87436d5...`，再到 helper `0c737481db3d5fe900174209e36e1cb43d06c9ff880f14b64dc81d5427928b13`、测试 `d73e782f5d228aa4951849b3fe6efe7c1a303a1034bcc9bb5c10333549e57d59`。以下原行号对应初读 9a435239，后续修复另行说明；没有混用成功收据与后来源码。
- 读取 retained SDK primitive 文本中四类搬运的参数、窗口/裁剪计算片段，及 translated view / 原件登记的数据结构。SDK primitive 文本身份为 `d52b889366fe0e06a21049958f10eb59f2e826444a6c1352b06038a1912153aa`。没有完成整个 SDK helper/DTE 实现逐指令证明，也未将私有源码、完整 IR 或 dump 复制到报告或 Git。
- 不读 peer；未运行 import、helper、pytest、产品、SSH、SDK、编译器、数学、设备、TP 或 UI。仅本地读文件、Git、JSON、归档和哈希，反例为静态推理。
- 原请求 GPT-6.1-Sol / xhigh；实际 resolved 型号和推理档位未暴露，记为 unknown。

## Confirmed major

### M1：`srem` 的 signed-min / -1 溢出没有拒绝

**位置。** 初读 helper 264–267 行，特别是只对 `kind == 'sdiv'` 检查 min/-1 的 266 行；对照同文件 233 行的 `tops_remsi_si32` helper 路径反而已经拒绝同类溢出。

**触发。** 保留原 sample 的正常 thread-zero、地址与 memcpy writer，在原 byte offset 上加入类型正确的：

```llvm
%bad = srem i64 -9223372036854775808, -1
%off = add i64 %offset, %bad
%address = add i64 %base, %off
```

LLVM 的这一 signed remainder overflow 不能作为正常定义值认证；首轮实现按 Python quotient/remainder 算 `%bad=0`，于是原正常 partition 原样返回，实际 poison/非法值派生地址被认证。

**后果。** 已支持整数集合内发生假通过，非要求增加未支持 ISA。

**源码修正进度及最小验证。** `c87436d5...` 起已将 guard 改为 `kind in ('sdiv','srem')`；最新已读测试也加入保留正常 writer、用上述 typed srem 派生 `%off` 的 negative，预期 `Poison` 拒绝。这个源码与 fixture 对应正确。最终 matching normal / `-O` 与同批原件执行收据尚需绑定，不能仅用未包含该 negative 的旧 v3 成功关闭。

### M2：未知 pointer 被空 roots 当作非 State，可能隐藏额外写入

**位置。** 初读 helper 160–175 行将 load 结果的依赖设空；178–196 行仅基于 `has_state` 分类 call/指令，185 行没有 State roots 即跳过。

**触发与推理。** 例如在原正常 writer 之外，增加 `%hidden = load ptr, ptr %tag` 或 `%hidden = call ptr @unknown()`，然后 `store i32 1, ptr %hidden`。前者的 loaded result roots 被置空，后者的无参数返回指针也没有 formal roots；额外 store 因而不进入 State-use 检查。未知指针可能指向 State，不能由空集合推出“不写 State”。`%tag` 与 State 的分配互不重叠，也不等于 `%tag` 的内存内容不能保存一个 State 地址。没有据此声称登记原件实际发生了这类写入。

同一分类问题也曾允许无 formal origin 的 `inttoptr` 指针、inline constant-expression pointer 隐藏写入；这些未知根应直接拒绝，不需要解释常量地址 alias 或新增一般 alias 分析。

**修正进度。** 最新 `0c737481...` 增加 formal-rooted pointer load 拒绝、未知 ptr-return call 拒绝，只保留已知 local/shared getter；另拒无 formal origin 的 inttoptr 指令及 inline constexpr。对应新增原始表示的 negative 均保留原正常 State writer。这是正确的有限收紧路线。

**仍在最新已读快照中的两条绕过。** pointer-load guard 只匹配 `load ptr...`，不能识别合法 `load volatile ptr, ptr %tag`；ptr-return guard 只匹配 `call ptr`，不能识别合法 `call noundef ptr @unknown()`。两者均可接同一额外 store，仍以空 roots 被忽略，而原 writer 计数正常。

这里使用 **noundef**，不是 noalias：noundef 只限制返回值的 definedness，仍可返回 State；noalias 返回本身附有不别名承诺，不适合作为这个 State-alias 语义反例。

**最小修正与 negative。** 对已经要拒绝的 pointer-load / pointer-return 类，识别其合法 modifiers/return attributes，至少覆盖 volatile load 和 noundef ptr-return；atomic pointer load 可保守拒绝。各加入一条保留原 writer 并真正使用 `%hidden` 写入的 negative。维持 local/shared getter 及实际 tag local-alloca load 的有限允许范围，不要求全 LLVM 指令解释。

## Confirmed blocker / minor / optional

本次没有另列 blocker、minor 或 optional。Pad readonly 尚未识别时的 unverified 是明确可用性缺口，不将它误写成 unsafe acceptance；后续支持进度见下文。

## 搬运模型与已有实际证据

初读的 1D slice-deslice 参数解释为 source offset / requested extent / destination offset，2D 为 source offsets / requested rows-columns / destination offsets；索引与已读 retained SDK 参数及窗口计算一致。1D deslice 和 slice-deslice 的目的裁剪有对应显式计算；2D deslice 的 source shape 不能被凭空按目的剩余空间裁小，当前模型对该 primitive 要求原窗口完整落入目的；source offset 加实际复制尺寸也必须在 source shape 内。所附 window-origin、source-window 和 unclipped 2D 三类 negative 对应这些有限区别。没有将同一 clipping 规则无差别套到四类 primitive。

旧 `State-partition-v1` 实际 terminal 1、0.966397417 s / 90 s；其 helper 为 `fb217534...`，8/32 partitioned，其余 24 明确是 `tops_slice_pad_async_1_si32` / `_2_si32` 未识别。input-v1 helper/tests 与初读 input-v2 不同，不能继承前者 fixture 成功为后者通过。`State-partition-v2` 也保留 terminal 1，绑定初读 `9a435239...`，仍只有 8/32，不能把修改模型后自动算作普通 32 通过。

已实际读取 `State-partition-v3`：terminal 0，`wall_ns=2869682746`，90 秒预算，32 checked / registered / partitioned，failures 为空，helper SHA 为 `c87436d5869863ccc5977e91a420a155808d9992ca9145fa8eb8de34ab93e6b3`。这一版本将 Pad 的 State **source** 识别为只读，State **destination** 仍明确拒绝；新增正反例没有把 Pad dest 误当 read-only。v3 是原 24 个拒绝项在该显式模型下的实际进展，但它不包含后来完整 pointer guards / srem negative 的最终执行闭环。

已读 matching runner 会先执行 normal / `-O` fixture，两条 child 任一失败即停止，然后才处理原件；它核对 translated LLVM、原 SDK input、math SHA，确认外部 wrapper 原样转发 user pointer args，并从实际 num-warps / threads-per-warp=1 枚举物理线程。该服务分析的是从原 LLVM dialect 输入逐行保留、去 GPU 容器后翻译的 opaque LLVM 视图，**不是 vendor final IR**。没有因 SDK translate 成功就认定 native 地址语义全证。

## 仍待证明的有限范围

所有已读摘要均保留 `state_writer_qualified=false`、`vendor_final_IR=false`、`device_executed=false`、`application_replayed=false`；helper 保留 `SDK_transfer_ABI_verified=false`、`native_schedule_verified=false`。第三方搬运与 launch ABI 的实际绑定、local/tag 条件、输入视图到实际执行的完整模型关系仍 pending，不因 32 partition 数值通过关闭。

helper 返回部分 `element_writers`，runner 再核全部 State 元素恰一次；不把 helper 单独允许空/部分 actor 输出列为缺陷。未知、poison 和未经证明的 pointer root 需要保持拒绝，不能把当前 M2 的空 roots 当作额外的非别名假设。

## 有限结论与最小下一步

先完成 M2 两条语法表示的封闭及目标 negative，再以最终精确源字节执行相同 fixture / 原 32 份 CPU 检查并保留 matching 终态。M1 的源码修正与 typed negative 已对应，但仍需同一最终收据。无需新 SDK、数学、设备、TP 或 UI 矩阵，也不要求通用 ISA/LLVM 证明器。当前不能用旧 v3 的成功签当前最终 checker，更不能据此授予 GCU State 整体或 whole-goal 资格。

## 最终格式冻结 / State-partition-v4 有限 closure

本次仅再读对应修复区域和最终 fixture，并核对输入归档 / v4 poll，未运行任何 checker 或测试。最终 helper SHA256 为 `7aeadcab3ecb2e6e64f37fb86d8479cf88f3400de7cd5d5d33dc998810e2102e`，测试为 `1b48bb1a87e56c027f08210f7f2e274ed8c83baadf372570567b59da7aff93f7`。两文件与 `preflight/gcu-State-partition-input-v4.tgz` 成员逐字节相等；该归档 SHA256 为 `67a7f7f1a6776454ca4e3a57bffd8f1cbfd3f936919a5b1ba0a6038defc66868`。

M1 的 signed-min/-1 guard 在最终 helper 459–464 行同时覆盖 sdiv/srem；最终测试 190–196 行是类型正确的 srem 结果加到原 offset 后，再用于原正常 State transfer，确实针对旧版算零的 false-pass。

M2 的最终 load guard（209–216 行）先拆 typed operand，再检测其指针类型，因此 volatile / atomic pointer load 不再因修饰符漏掉 formal-rooted unknown provenance。ptr-return guard（217–221 行）检查 `@callee` 之前的 return prefix，且要求结果存在，能识别 noundef 等返回修饰符；只保留已知 local/shared getter。最终测试 217–225 行分别使用 `load volatile ptr` 和 `call noundef ptr`，都接真实 `%hidden` store，保留原 writer；原形式和 inline constexpr / 无 formal-origin inttoptr 负例亦保留。这些修改覆盖原 M2 的具体根因，未发现该小修复新的具体误放行。

已实际读取 `preflight/enflame-State-partition-poll-v4.json`：terminal returncode 0，`wall_ns=2969512766`（2.969512766 s），实际预算 90 s；32 checked / registered / partitioned，failures 为空，checker SHA 与上述最终 helper 相同。归档 `run.py` SHA256 `ae103b2965c339bd8557a524dc8a5275a7da208d09c70473773d9bc497cf410e` 与 terminal script SHA 一致，执行顺序是 normal / `-O` 两条 pytest，任一 child 失败即停止，再处理 32 原件。结合 matching 最终测试文件，该终态支持最终 30 个 fixture 双模式成功及原 32 份材料的正常 CPU 分析成功；本次未读取完整 fixture stdout，不编造其逐字日志或 child 耗时。

**M1 / M2 按最终源码、准确语义反例和 matching v4 CPU 终态的有限闭环已关闭。** v1/v2 失败仍作为历史失败保留，v4 的 32/32 只表示显式 SDK 模型中的登记原件分区检查通过。最终摘要仍明确 `state_writer_qualified=false`、`vendor_final_IR=false`、`device_executed=false`、`application_replayed=false`；SDK transfer/launch ABI 及整体 State/whole-goal 资格不因此关闭。本次没有要求或执行任何新数学、SDK、设备、TP、UI 矩阵。
