# R092 Ascend BK64 三方关键 pipeline：有限 delta 审计 v1

后续 matching 原件及 ordinary whole-byte-identical CPU 输入链已补齐并实际审读；本页保留最初缺件状态，当前有限闭合结论见同目录 [v2 审计](ascend-BK64-pipeline-audit-v2.md)。

**当前结论：可复用 BK32 的具体 SDK helper 语义，但本地缺 BK64 actual LLVM/receipt，尚不能关闭 BK64 三方关键关系项。** 未发现新增 confirmed blocker / major / minor；下面是明确的原件/参数验证缺口，不是已证明 profile 强加串行依赖。历史 sparse1 第二 capture 只有1 positive 的失败保留，不要求它变通过，也不否定 default8 成功。

本次仅继承原 R091 G3 的 BK64 子项，不重审 whole-goal，不新增矩阵、ISA 或硬件 schedule 门。请求配置 GPT-6.1-Sol / xhigh，resolved 型号/effort 未暴露，记 unknown。未读 peer；仅本地只读 Git/文本/JSON，未运行产品、测试、SDK、编译、设备、模型、数学、TP/UI 或 SSH。只写本报告。

## 实际阅读材料与已成立事实

读取：

- `integration/evidence/timeline-independent-qualification-r057/ascend-density-summary-v1.json`（及 root 同字节版本中的相关 BK64 记录）；
- root `run057/preflight/ascend-density-default64-{runner-v1.py,current-v1.jsonl}` 的真实命令、终态、源码身份；
- root `run090/preflight/ascend-BK32-density-inventory-v1.json`、实际存在的 `ascend-BK32-density-details-v1.json`；
- 本人 `run090/review/ascend-BK32-pipeline-audit-v1.md` 及已核的实际 driver；
- 原同库完整所需 MMA closure 的关键等待、tile/part、MAD 与返回路径：`run090/preflight/ascend-mma-helper-receipts-v1/runs/mma-helper-closure-v1/output/mma-helper.ll`，及其 `result.json` 的三方 resource bindings。

初始线索名 `run090/preflight/ascend-density-details-v1.json` 在本地不存在；实际 BK32 details/归档只提供 BK32，不把它改称 BK64 材料。

原维护 driver SHA **298743dc44abde27a6326f02be3b0204c1a046c855a8eb6f24fe5a27006cca50**。BK64 是同 C2 数学与输入：M=N64、K192、grid(2,2)、num_warps4、num_stages1，只把 reduction tile 改为64；State/输出独立分配，原主输出不变。源层预期是3轮 K tile，但**还未用 BK64 final actor 实参/CFG 确认**，不能用 constexpr 或 stages 值冒充最终循环及 overlap 事实。

| 原 BK64 对象 | 既有实际登记 |
| --- | --- |
| ordinary | binary ID **21681db4dbb5059b5954421e5b97334d670b29a5718d8f0d544af54504a6e91d**；两个 density 运行均登记普通3次 math_passed / original_calls1 |
| sparse1 | binary ID **31f2a9ce155693913e894535db6eeb06db56c326da08279ebb608a46228da20c**；首 capture `invocation-b6c9871feb4f4c1fb5f084a704e049d4`，70 intervals /8 positive；第二 `invocation-7b5a5f89f6974d18a500e5de7dae7cbc` 仅1 positive，原 run 不完整，不能填全3次 |
| default8 | binary ID **2b76cd0cfcc0de6d13a28596095764dec41f7956f37eac117a5bc8470a514c74**；三 capture 各106 intervals、23/27/24 positive；actual controller terminal0，56.605556806s，未新执行 |
| sparse actor LLVM 摘要 | AIC original **19c2e787b74b7f4b07a32380da660cdfb7f89d20671d4bd6108c6e006b515af6** → adapted **64df64e78e9ac21852edea1583cb4371accb95db3d0e2bd3f4284fd9557928fc**；AIV original **46637061b475ef2091d031a4cf061dc7b28649c16e9dc4f4efe5df400bba3c98** → adapted **65fea3e8995bce439a80cce34c4d2595ae95a787152e64472d55bb1982000a49** |
| default actor LLVM 摘要 | AIC original **0047bd770859e3e5ef18f6aa9bee4f686ac48a1f2bbd53f516f717df19321c0f** → adapted **bb24d757abec68e379c99701e3b30a584251c1ccde900ba60f25e888a3f6fb40**；AIV original **c777e1ecffadf927e0981475080d91beb886850fa4ee99328b77ac53ac2083ad** → adapted **0da49020468104d5e9779c5180c19f89b7088b4032d5fbbe1440fb7046b14219** |

原摘要自述范围为实际 late-observer SDK input primitive projection，明确不是完整最终 scheduling 证明。它保留了有用身份，但没有 call 的 buffer/shape/offset/pipe实参和 branch/loop；不能仅由 primitive 名称/顺序相同关闭本项。

## BK32 helper 能复用的具体条件

已独立核的 closure SHA **7f4e64f840da5f1c581754e8e57cfa3f9510ddff57b422fc2f3f05824d70c7e9**，来源 resource `meta_op.aic.bc` SHA **94c9885a52c9e4cfdfbc239ad104f0a4d14cd330cff9c51d141eb08e88f9ef4f**。R090 三个 actual resource binding 目前都是 **BK32**；尚未证明 BK64 也用相同 bytes。

若 BK64 actual receipt 绑定相同 resource，以下语义不用重新提取 helper 或实验：

- 628：L0 ping-pong reuse 的 M(2)→MTE1(3) wait，事件来自实际 back-event / ping-pong 选择；
- 640/679：本 part 首次加载前等待 caller 提供的 MTE2→MTE1 A/B readiness，相关实参非 -1 时生效；
- 652/691 L1→L0 A/B 搬运，664/703 发布 L1 reuse；这些 release 在 MAD 前，不能独自读作 MMA 完成；
- 753–755 MTE1→M readiness、870 MAD调用；883 小 tile barrier 条件为 `(l0c_m_size/16)*n/16 < 10`；
- **907–922 返回尾部**分别比较两个 `back_pipe_m_pipe_mte1_db_event{0,1}` 是否为 **-1**；为 -1 时在 return 前执行 **WAIT(2,3,0)** / **WAIT(2,3,1)**。这个分支**不直接取决于 k_actual=32/64**。

因此，若 actual BK64 仍 m/n32、k64、k_part512、back-event=-1/-1、同 resource，单 part 与原 completion cut 可以有限复用；不能只因 BK 从32变64就断言 ordinary 获得了跨 caller 轮的未来 MMA。若实际 back-event 改成外部管理事件，或 kpart/part数/尾部条件改变，必须按实际参数解释，不沿用 BK32 结论。现阶段这些是明确的**待核条件**，不是本报告已确认的 BK64 参数。

## 确实必要的最小原件与检查

已向 root 给出如下只读回收请求，不要求新设备/数学/模型：

1. 原首 sparse capture：

   `/tmp/chijin-timeline-r057-ascend/runs/controlled-density-v1/output/BK64-density-1/64-0/capture/timeline/captures/invocation-b6c9871feb4f4c1fb5f084a704e049d4.json`

   原首 default capture：

   `/tmp/chijin-timeline-r057-ascend/runs/controlled-density-default64-v1/output/BK64-density-8/64-0/capture/timeline/captures/invocation-57c17c5b907847fe9bd0801916e1d5c7.json`

   保实际 compiled snapshot / handoff / actor associations、binary bytes/hash、compiler/SDK/resource参数；有现成 `events.json` 可同取，供原循环控制 occurrences 交叉检查，不新增 timed-flow 资格。

2. 按上述 capture 的实际 handoff job 路径，取 **AIC/AIV 各两组**原 `original-0.ll`、`adapted-0.ll`、manifest 和 receipt（文件名以实际 job 索引为准），包括 executed input/resource SHA。只需这些 actor 主体和绑定资料，不需全部 SDK library/native dump。

3. 从两个原 `output/compile-cache/*/product.json` 中定位 metadata.hash 为 ordinary **21681db4…6e91d** 的条目，取相应 metadata、原 npubin/bcmlir 及已有 ordinary SDK input/command receipt。若普通最终 actor LLVM 未留存，可以由 root 决定沿 BK32 相同 CPU passive-codegen 路径补 actual inputs，前提是 whole kernel.o 与原 npubin **逐字节相同**；本席不会启动该动作，也不将可能重现预当通过。

收到这些后，最小核验仅为：

| 关系 | 实际必须读取的字段/路径 |
| --- | --- |
| 提交与非空范围 | A/B GM、L1 descriptor/base、tile/stride/offset，实际 i 的推进；不能从 BK64名字猜 buffer分离/轮数 |
| readiness 与 consumer | 每个 nd2nz 后的 SET 与 helper 参数中的 A/B wait 方向和事件，首次消费/part路径是否匹配 |
| reuse | L1 release事件、L0 ping-pong/back-event参数，下一次对同buffer提交前的原等待 |
| 原返回 cut | actual m/n/k/kpart、back-event、同 library SHA；据上述 helper 判3轮 caller 之间是否本来已有 MMA completion cut |
| 尾部 publication | drain→M/FIX readiness→C搬出、AIV State路径及末端 barrier，确认不是把 mixed AIV 误作 C 的 consumer |
| logger 增量 | 新 trace load/store 根限独立 hidden buffer，原地址/提交/控制不依赖 clock/MMA结果；无新增原 completion wait 或全局锁 |

这能回答原 C2 的静态关键关系与原合法机会是否保持，不要求相同 issue 排序、隐藏 scoreboard 全解码或 engine busy。无需完整 source/loop 产品规则先通过才审这些明确事件/参数；反过来本项通过也不会填 source/native clock-valueflow/epoch资格。

## 缺陷与当前判断

- **Confirmed blocker / major / minor：无新增。** 当前只有摘要不足，尚未见实际新增完成串行化路径。
- **Necessary verification gap：** BK64 actual ordinary actor输入到原 whole binary、两个密度的 actual参数/resource/consumer/reuse/cut 对照未在本地闭合。最小缺物就是上列两个capture、四actor job和ordinary相应cache/input链。
- **Optional：无新增。** 不建议新矩阵、换调度、补同步或专用算子代码。

本报告当前不支持关闭 R091 G3 的 Ascend BK64 子项；支持复用已经核实的具体 helper 语义与原 default/sparse结果身份，收到 matching 原件后只需对此有限 delta 追加。没有否定已闭 BK32，也没有把历史 sparse1失败改为default失败或要求其重跑成功。
