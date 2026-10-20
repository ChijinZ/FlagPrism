# R089 Ascend State readonly assembly：有限独立 compiler review

仅审 `ascend_state_writer_partition.py` 新 readonly assembly delta、对应 fixtures 与所给 pattern/初始终态；不重开 whole，不读取 peer 或其它席的 SDK ABI/补二结论。没有执行代码、import、测试、SDK、设备、数学或 SSH，只读取文件/Git/哈希；仅写本报告。请求 GPT-6.1-Sol / xhigh，实际 resolved model/effort 未暴露，记 unknown。

## 实际阅读与身份

阅读全文及 diff：`tests/timeline/ascend_state_writer_partition.py`、`test_ascend_state_writer_partition.py`；读取 `run-089/preflight/ascend-profile-asm-patterns-v1.json`、`ascend-profile-State-poll-v1.json`、限定 CPU runner。没有重审原 R080/R081 的不变整数、State transfer/descriptor、actor 规则。

审阅时 candidate HEAD `61e47e0dd16ca6ccea2ee07865110cca7844c50c`，delta 尚未提交。实际观察 SHA256：

- helper：`739ce2fa9b6d8ccd1f87e4122f006c36010c826128927d829ae776f8b9946105`。
- tests：`52ab684ac4b7aa2701b723e0240041ffbbff4a05d95b8836861321d57d229252`。
- assembly pattern receipt：`5c862e4c433348813e92a9ea69c63def21600a4f48b6677b0cb27f41267a1ab5`。

## Confirmed findings

### M1 — major：未知 inline asm 可被字符串中的假 direct callee 绕过拒绝

位置：helper `:48–56` `_call` 的非词法 `call ... @name(` 搜索，以及两个新精确白名单之后 `:241–250` 的普通 call 路径。

最小触发是在合法 fixture body 中加入：

```llvm
call void asm sideeffect "/* @fake() */", "l"(ptr addrspace(1) %state)
```

静态推理：该行不匹配新的 clock / source-marker 白名单；普通 call 分支仍调用 `_call`。其正则可以命中 assembly **字符串内部**的 `@fake(`，把空 `()` 当成调用参数，返回 `fake, []`。真实 inline-asm 参数 `%state` 被漏掉，`state_uses` 为空，因而整行 `continue`。本例不依赖任何未知 ISA：注释内假符号足以绕过“所有其它 assembly / State 地址 operand 均拒绝”的 parser 合同；同样手法也能隐藏其它 asm 内容或 clobber。没有运行该反例，也没有发现当前 44 个真实输入使用此模式。

后果：有限 checker 的白名单并未实际封闭；不能仅凭新增正例与不含 `@...()` 的负例，断言未知 inline assembly 一律保守拒绝。这是 qualification helper false-pass，不是已证明当前 State 数学或产品运行故障。

最小修复：在两个精确白名单之后，显式拒绝其余 inline asm，再进入普通 direct-call 解析；或以等价的有限词法区分保证字符串不能成为 callee。无需新增 ISA、memory taint 或 IPA。最少 negative 就是上面的带假 callee 注释、真实 State operand 的合法 LLVM 行，要求命中明确的 unknown-assembly 拒绝；原 extra-op/clobber/args negatives 同版保留。已向 root 发出此具体修复建议。**截至本报告写入，尚未读取修复源码/匹配终态。**

没有另外确认 blocker 或 minor。

## 其余 delta 的有限判断

clock 分支 `:220` 为整串相等：只接受 `call i64 asm sideeffect "MOV $0, SYS_CNT", "=l"()`，无参数、额外指令或 memory clobber。它没有把读出的 ticks 解释成已知常量，也没有跳过后续实际 State transfer/guard/descriptor/actor 检查。该精确模板作为 scalar register read 豁免有界、与给出的真实 pattern 相符，不需要为此增加通用 ISA 证明。

marker 分支 `:222–236` 为整串模板匹配，三个字段只允许 digits，assembly 本体为一条完整注释，六个约束精确为 input-only `l`，参数必须正好六个 i64；另核 State 不在参数的根闭包中。未知模板、额外文本、constraint/clobber 或错误 ABI 不由此分支放行。State `ptrtoint` 等其它未建模地址操作仍受原严格规则约束，没有随这个 comment-only 特例获得许可。

`operation():338–339` 对不在普通 `calls` 表中的 scalar call 结果抛 `UnknownCone('Unmodeled scalar call result')` 是正确的保守处理，避免把跳过的 clock 直接索引为不存在的普通 callee。State offset 使用该值会拒绝；分支求值若遇 UnknownCone 则保留两条边，再按原 writer dominance/return/cycle 义务检查，不据此挑选有利路径。root 提供了初稿 KeyError 的经历，本 reviewer 未独立运行或复现该初稿；本次只确认修后实现及 targeted fixture 的静态对应关系。

新增 fixture 包含 clock 与精确 marker 正例，extra op / clobber / args / marker 错 ABI negatives，以及 clock-dependent State offset 的明确错误匹配。当前缺的最小语义反例为 M1；不建议扩展矩阵或增加 memory taint。

## 实际证据与 verification gaps

pattern receipt 登记 44 个当前 actual actor LLVM 输入：一种 SYS_CNT 模板（2,328 occurrences）及 55 种精确空 source-census marker 模板。其例子带 `!dbg`；实际 checker 输入应沿既有抽取/归一链消去 debug 后缀，模板才能整串匹配。本报告没有替其它席核最终 loaded-object/SDK ABI 组合，也不把 pattern 计数当 native schedule 或 State writer 总资格。

初始 `ascend-profile-State-poll-v1.json` 明确是旧 helper `bfad3bcf…` 的 CPU 结果：terminal 0 / 54.983603509 s，96 checked、0 partitioned，失败上下文为该精确 SYS_CNT call，`Unsupported indirect call`。这是 checker 的保守拒绝结果；terminal 0 仅说明诊断 job 正常完成，不等于 96 条资格通过，更不等于数学失败。输出 State writer / SDK ABI / native boundary flags 均 false。

尚待最少收据：M1 封闭后的最终 helper/test SHA、针对本 delta 的 normal/-O fixtures（包括上述 negative）及原 actual96 finite partition 同版终态。原正在运行的结果不能预判，旧 pattern/初始 job 不能继承为新 SHA 的执行通过。无需重跑 SDK、设备、数学、TP 或 UI。

## Optional 与有限结论

无额外 optional 工作。两条精确白名单和 clock UnknownCone 路线本身未见其它具体缺陷；M1 需要封闭未知 asm 的 parser 入口并补唯一对应负例后再确认执行。原 SDK ABI/补二适用性及 native source/loop、pipeline、whole-goal 均不由本报告放行。

## M1 最小源码修复追加（执行仍待同版 v4）

root 修复后，已再次实际读取 helper/test：SHA 分别为 `be21ab003a5d1a4604698fbb495c977b91b5a836b21647f544b9a4bd28793030`、`a2dc1d7c2e57d2ffcc588e27661a8b4485f352cc96f7c0e7f32a1963997b7107`。两个精确白名单之后、普通 `_call` 之前已有 `\bcall\b.*\basm\b` 的显式拒绝；新增 `test_assembly_comment_cannot_impersonate_a_direct_call` 正是带 `@fake()` 字符串注释及真实 `%state` input 的原触发，要求明确拒绝。

这一最小修复在本 finite parser 合同内封闭了 M1，不需要解释任何新增 ISA。clock-dependent call result 仍采用既有 UnknownCone 修复。**M1 源码修复已静态确认；尚未读取含新 guard/negative 的 v4 matching 终态，执行缺口继续保留。** root 提到的 v2 初稿失败和 v3 40 项执行不继承为新增 M1 negative 的执行通过。

## M1 v4 最终 CPU 终态追加

本追加只核 M1 的已审修复及同版 CPU 结果，不重审 native/ISA/whole。已读取 `ascend-final-jobs-poll-v2.json` 中的 `profile-State-v4` 分支；同文件的 supplementary sidecar 结果未用作本报告依据。

再次读取 candidate：helper SHA 仍为 `be21ab003a5d1a4604698fbb495c977b91b5a836b21647f544b9a4bd28793030`；最终格式化 test SHA 为 `96f7a80400a343e44201855ea21bc3415e3ea9ce33608332661606356761aaf1`。实际重读 unknown-asm guard 位于两白名单后、普通 call parser 前，`@fake()` + State operand negative 保留且要求拒绝。

本地 `ascend-profile-State-input-v4.tgz` SHA 为 `68556edacf21ba723306321a0e3982cdf555f31db50e3a87144dd779326f04c6`。仅流式读取其中两个 helper/test 文件并分别 `cmp`，均与 candidate 字节完全相同；最终 test 也与 `gcu-ascend-State-formatted-v3.tgz` 对应文件字节相同。归档 `run.py` SHA 为 `8cc28cd1c6b3bfa57953a135e5acb558a5549f8a9f69a8d84be24a1a79624baf`，与实际 v4 terminal 的 script SHA 相同。实际 partition result 回报的 checker SHA 也正是上述最终 helper SHA。

v4 poll 给出的实际结果：

- terminal 0，**83.165427087 s**，deadline 300 s；fixture normal、fixture -O、actual-profile 三个 step 返回码均 0。
- 两份完整嵌入 stdout 分别为 **41 passed / 0.10 s**、**41 passed / 0.10 s**；-O 只有预期 pytest assert warning。该最终测试源包含 M1 的唯一对应 negative 和原 clock-dependent offset negative。
- current96 注册 SHA `88a1cac1606f9bbb6093c3a10f21ccd03209ba68723d71d595f565ae1c44846e`；96 checked、**96 partitioned / 40 distinct successful parts**，failure examples 为空。旧版 0/96 和初稿失败仍为历史记录，不再作为当前结果。
- receipt 保持 `SDK_recompiled=false`、`device_executed=false`、`application_replayed=false`；State writer / SDK ABI / native timing boundary 资格仍均 false。整体 stderr 的 `can not use command: npu-smi info` 保留，不影响上述三 step/terminal 的实报返回码。

**M1 的最小源码修复及有限 CPU 执行闭环已成立，没有因此新增本 scope 内未修实现问题。** 这一结论绑定已取得的输入归档、实际回报的 helper SHA、脚本身份和嵌入完整 fixture stdout。尚未取得/独立核对服务器 executed-source 副本及完整 v4 source-receipts ledger；不把本追加说成已经完成该完整归档审计，若回收有差异应重新核这一身份连接。本文不复核或继承其它席的 SDK ABI/补二结论，也不外推 native、pipeline、whole 资格。

## 最终回收 executed-source matching 追加

随后实际取得并读取 `ascend-final-State-receipts-v1/profile-State-input-v4/` 与 `runs/profile-State-v4/` 的同版原件。分别对回收 helper/test 与 candidate 作 SHA256 和 `cmp`，两者字节完全相同：helper **`be21ab003a5d1a4604698fbb495c977b91b5a836b21647f544b9a4bd28793030`**，executed test **`96f7a80400a343e44201855ea21bc3415e3ea9ce33608332661606356761aaf1`**。`a2dc1d7c…` 仅属于前文格式化前的静态审阅快照，不是最终执行 test 身份。已读 `ascend-State-source-freeze-v4.json`，与上述独立文件比较结果一致；root 告知 QA-only commit 为 `2a1f065`。

实际回收 `run.py` SHA 与 terminal script SHA 同为 `8cc28cd1c6b3bfa57953a135e5acb558a5549f8a9f69a8d84be24a1a79624baf`。完整原 terminal、normal/-O stdout、actual-profile result 均与此前 poll 一致：terminal 0 / 83.165427087 s，41 + 41 tests，96 / 96 partition，40 distinct，`failures=[]`；实际 checker SHA 匹配。不是用旧 v3 或旧 helper 的结果代替 M1 修后结果。

因此，上段暂留的 **executed-source/关键终态原件未取得** 缺口现已关闭，M1 完整有限 closure 无新增待办。本 reviewer 没有重算全部 129 个归档 member 的 ledger；这不冒充独立全归档审计，root 的全 index 核同记录与本次关键文件独立比较范围分别保留。不重开 State SDK ABI/补二、native/ISA、pipeline 或 whole-goal 资格。
