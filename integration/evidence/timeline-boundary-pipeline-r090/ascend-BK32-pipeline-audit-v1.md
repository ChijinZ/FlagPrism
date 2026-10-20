# R090 Ascend BK32 ordinary / sparse1 / default8 有限 pipeline 审计

结论：本次实际 BK32 对象足以支持**三方关键 pipe/event、缓冲消费/归还、末轮 publication/drain 的静态关系保持**。未发现插桩新增原本没有的完成等待、全局 logger lock 或 MMA 结果到原提交/控制路径的数据依赖。特别是原 ordinary 在每次 MMA helper 返回前已有 M completion cut；不能仅凭 `num_stages=1` 推导这一点，本次已核到实际同库 helper 的具体等待。

这关闭本 BK32 案例的上述有限 preservation 问题；不把它提升为全 P03/P07/C2、所有调度变体或 whole-goal 通过，也不提升旧 capture 的 clock/value-flow/native-region/跨泳道 flow 资格。

## 范围与身份

- 仅本地只读文本/JSON/Git、字节比较及 SHA 核对；未执行产品、测试、编译器、SDK、模型、设备、数学、TP/UI 或 SSH，未读 peer 报告。仅写本报告。
- 请求配置为 GPT-6.1-Sol / xhigh；实际 resolved 型号及 effort 未暴露，记 unknown。
- 阅读根 `timeline_goal_prompt.md` §2.2，candidate `Profiler/docs/timeline_design.md` §0.6/§8.12/§8.14，以及 `timeline_testing.md` P03/P07/C2 与 §5/§8.7。按原合同核关键关系及允许的 overlap 机会，不要求 issue 顺序完全相同、exclusive cost 或 hardware busy。
- 阅读时 candidate HEAD `7dc27a1b9564f3ecf56e47da63f41537b00febe9`，工作树 clean。实际审计主体是下面冻结的旧真实对象，不把当前 HEAD 冒充旧 producer。辅助阅读当前 `AscendLateObserver.cpp` SHA `0d5b551951df6407604d81b2e03dcb1b3299f71f6e5903d0cb0f7ea0963fe805`、`AscendNativeTimeline.h` SHA `f8c317ab0469a54c0bb23136932f9739dd06488589a8d96f02c60724ed158735`；四份实际 `adapted-0.ll` 是本次插桩增量的直接依据。

路径缩写（均在本工作区）：

- `R = artifacts/timeline/run-090/preflight/ascend-BK32-pipeline-receipts-v1`；已读其 `pipeline-index-v1.json`，106 项。`P = R/retained/chijin-timeline-r057-ascend/runs/controlled-density-v1`。
- `O = R/retained/chijin-timeline-r0120-ascend/runs/ordinary-BK32-codegen-v1/output`。`r0120` 是实际 retained 路径，未把路径名称当成另一次应用运行。
- `H = artifacts/timeline/run-090/preflight/ascend-mma-helper-receipts-v1/runs/mma-helper-closure-v1/output`。
- `S-AIC/S-AIV = P/tmp/flagprism-ascend-compiler-wtsqmazv/8783f3f6-cfe0-4c2f-8842-aa0fd7188539/jobs/{a9aadf87-dbdb-486a-8f2b-8c83ab48f193,8c1da3ab-1878-4b6c-8107-8d47acbd7f0e}`。
- `D-AIC/D-AIV = P/tmp/flagprism-ascend-compiler-u6sxbfzj/06348174-868b-4570-a6d9-6cdaf77ba6da/jobs/{ca11526e-bb10-4007-945d-5e5fbda2546a,926b3f05-5b1c-4510-b5e1-d4331aa51ede}`。

实际读了 ordinary AIC/AIV 的 LLVM 主体及 descriptor wrapper、四 actor job 的 original/adapted 主体、manifest/receipt 的身份及相关站点、两 capture/events/raw 身份及 counter-map 状态、两组 result、实际 driver；另读 H 的完整所需 MMA/搬运/flag/MAD 闭包及其三方 resource bindings。未重新做无变化的历史矩阵审计。

实际调用固定 `M=N=64,K=192,BK=32,grid=(2,2),num_warps=4,num_stages=1`，同一 A/B 输入、独立 C/State，普通数学三次与各密度 profile 三次均 `math_passed=true,original_calls=1`。sparse 的实际请求为 `max_sites=1`、选择 `[32]`；default 为 `max_sites=8`，两者不是同一密度的别名。

| 对象 | 实际身份/绑定 |
| --- | --- |
| ordinary | binary ID `444d86a0a189f1d0b1a424fce116d0e69c4dc63079a2fc741433868fb7a2ea56`；原 `ordinary.npubin` 与 O/kernel.o 亲自 `cmp` 相同，SHA `77d49b1a3f9f67358f72743a68c39e8adef48a4799af591e4b1ad4f484e8d0cd` |
| ordinary codegen 输入 | O/objects/`f10d38067e4ea5c5d2c92cda5468904298a881046e52743fd3b5abf6f0bdc4e4.ll`（AIC）、`1933e02e5b94638c23ef2078abca10b20e6260ed194505472caef4ed2a7bbc67.ll`（AIV），亲自核 SHA；actual receipt 与最终 byte-identical kernel 关联；CPU passive codegen terminal 0，3.270642897s，不是新设备数学 |
| sparse1 capture | invocation `29f2502d79e44b2389c77695306be227`，JSON SHA `fe8edd6976185419c484e4f40838d5c229faffaec4f5edf8e76e7b0b57145a77`；loaded ELF / snapshot / producer association 一致为 `0876c7da200bb942aa8d8f37dd3b52866773d0657edd17e1931f3cbf0cde9854` |
| default8 capture | invocation `89ee5e07fa5d4eaca22dda0ed0dbac8a`，JSON SHA `f6ce2bf6e2e98ced39edf19e7602345a10e1724796d5dcf9a71de857abca866f`；三处 ELF 身份一致为 `16fe3af431187563bf12bab074e96d5f398c9b3b8b6e2967b5242fa24c4c6be2` |
| 四个 actual adapted LLVM | S-AIC `fa38e7ec1aac09ba90ff47ad770929e6a7b73ed9a9621d0893515a7eaaec655a`；S-AIV `1680aed106b1430b259e8c45da401c2e80f5a78b42c3174d85d25eee4897ec58`；D-AIC `d66cc1ee6eb06f66c80ae42461217f2b630b3ec01f2ab01b3d40d602d40ec2d2`；D-AIV `d1a7ef09475d9a0faffdec2b6ada410affbad4e0d4f2d9449871d99558b7ce44`；均亲自核 SHA，与 actual executed_input_files 一致 |
| 同一具体 SDK helper | ordinary receipt 与两 profile executed resource 都为 meta_op.aic.bc `94c9885a52c9e4cfdfbc239ad104f0a4d14cd330cff9c51d141eb08e88f9ef4f`；H/mma-helper.ll SHA `7f4e64f840da5f1c581754e8e57cfa3f9510ddff57b422fc2f3f05824d70c7e9` 已亲自核。只读 llvm-extract 闭包 terminal 0、8.085384960s，无 SDK 重编译/设备/模型 |

ordinary 的 SDK 是原 isolated fixed SDK `1f5cc5054402e901add18af133b3495b861775d68e2113bb8ba94667eef6cf9e`。AIC receipt 同实际 bisheng `2b5d17a037767ad41123868e14bedb91741b0682cafd1a2aa05a1da5d8b8bade`、`-O2`、cube target 和资源库绑定；profile 另有原观测所需 debug 参数，未声称命令逐字节相同。没有将新 CPU 推导对象代替旧真机 ELF：ordinary whole bytes 相同，profile 用各自实际 loaded 对象和执行输入链。

## 三方关系的具体核验

下表 ordinary 行号指 O/objects/f10d…ll；后两列指各 `adapted-0.ll`。`SET/WAIT(a,b,e)` 中 a/b 是实际 HIVM pipe enum，e 是独立于方向的事件号，不把不同方向同号事件混成同一 token。

| 关键关系 | ordinary | sparse1 / default8 |
| --- | --- | --- |
| 首轮 L1 可写 | 40–41：`SET(3,4,1/2)` | 91/231；276/416；均在循环前 |
| A 提交及 readiness | 90–92：`WAIT(3,4,1)` → GM A offset `row*192+i*32` 的 nd2nz → `SET(4,3,0)`，L1 A byte 0 | 837/934/978；1118/1215/1259；同指针、shape/stride、event |
| B 提交及 readiness | 113–115：`WAIT(3,4,2)` → GM B offset `i*32*64+col` 的 nd2nz → `SET(4,3,1)`，L1 B byte 2048 | 1416/1513/1557；1837/1934/1978；同参数及 event |
| 消费与归还 | 117：同 `mma_tile_half_to_float`；readiness 参数 0/1，L1 release 参数 1/2，迭代参数 i，back M→MTE1 两参数均 -1 | 1655；2120；这些参数、A/B descriptor、L0C base 及 init=(i==0) 保持 |
| 轮次/尾部 drain | 44–46/118–119：i 从 0 到 5；122–124：`WAIT(3,4,1/2)`、`SET(2,10,0)` | source-loop phi/compare/increment 仍 6 轮；1703/1843/1983；2264/2404/2544 |
| C publication | 141–143：`WAIT(2,10,0)` → L0C→GM C fixpipe → 原 `BARRIER(6)` | 2139/2236/2237；2744/2841/2982；同 C buffer、范围与顺序 |

原 tail-padding 分支的 `SET/WAIT(3,4,0)`、L1 zero fill 和 `BARRIER(4)` 两份都保留；本实际 full 32×32×32 tiles 不走这些 padding 分支。没有把未执行分支里的 0 号事件充当实际 generation。A/B 实际 tile 各 32×32 half，即每轮各 2048B，6 个真实 K tile，源地址逐轮变化而 L1 A/B 固定复用。

### 为什么本例不能凭 stages 猜 overlap

H/mma-helper.ll 的实参命名和主体给出原先 opaque 的有限闭包：

1. 628：等待本 L0 ping-pong buffer 的 `M(2)→MTE1(3)` 可复用事件；640、679 等待 caller 已提交的 `MTE2(4)→MTE1(3)` readiness 0/1。
2. 652、691 把同一 L1 A/B 搬到 L0A/L0B；664、703 在 MTE1 pipe 发出 L1 可重用事件 1/2。这些 release 确实先于 MAD，故只看它们不能断言“全部计算完成”。
3. 753–755 的 MTE1→M set/wait 后，870 经真实 mad wrapper 到 1329 的 `MAD.f162f32`。实际 m/n=32，helper 的 `l0c_m_size=2*16=32`，小 tile 条件 `(32/16)*32/16 = 4 < 10`，原 883 `BARRIER(2)` 成立。
4. 888 发出该 ping-pong buffer 的 `SET(2,3,p)`；caller 的两个 back-event 参数都是 -1，所以 **913/922 两个 M→MTE1 WAIT 在 helper 返回前执行**。本实参 `k_part=512,k_actual=32`，每次 helper 只有一个非空内 part；即使不依赖小 tile barrier，匹配的尾部事件等待也构成 completion cut。

由此，三方实际调用语义中，“本轮 helper 返回→下一 caller 轮 GM nd2nz 提交”处没有保留未完成的前轮 MMA。虽有真实异步提交/事件及 L1/L0 复用，本对象不能充当非空未来 MMA 与下一轮 GM 搬运重叠的正例。这个结论来自实际参数和同库函数体，不来自 `stages=1`，也不把 header 中 `enable_double_buffer` 或 ping-pong 名称当 overlap 证明。profile 未将原有的非空 future 在这个 cut 额外 drain。

在每轮内部，GM A/B 提交仍先于其 MTE2→MTE1 等待；原事件只约束相应 pipe 工作集合，A/B 的真实非空 footprint、消费者、归还事件、L0 交替和最终 C publication 都保持。实际硬件什么时候并行执行、编译调度的全部细节和 busy 占比不是此有限结论。

### AIV 与记录器增量

ordinary AIV block `%64` 及随后主体（O/objects/1933…ll:168–175）是 **State** GM→UB load、`SET/WAIT(4,1,0)`、UB int32 `+1`、`SET/WAIT(1,5,0)`、UB→State GM store、原 `BARRIER(6)`。两 profile 保留同 State formal、每 subblock 16×32 范围和 offset、同 UB base 和这些切点（S-AIV:614/659/801/899/944/1086/1184；D-AIV:1043/1088/1230/1328/1373/1560/1658）。可选 padding 的 V→MTE2 事件也未新增或改写。

AIV 并不读取 AIC 写出的 C；不能因它们在同一 mixed kernel 或 source 名称相同而构造 C→State 跨 actor 消费关系。default AIV 的 `tt.dot` 六次是保留的 source-marker 空循环，不是六次 AIV MMA。实际 metadata 的 `static_readiness.state=partial,reason=no_unique_cross_actor_typed_channel` 与此相容。

四份 adapted 主体的新访存均经 hidden trace formal `%7` 的 GEP；数学仍使用原 A/B/C/State formals。新增标量内容是 SYS_CNT 输出、只取坐标的空注释 asm、observer/容量判断、trace header/record 的有界 volatile GM load/store、单向分支及合流。未见新增 PIPE wait/barrier、完成轮询、atomic/global lock、对原数据 buffer 的 logger load/store、或 M/向量结果读回后再控制下次 submit。数学 pipe/helper calls 均 void，原地址和循环条件来自原坐标/induction/shape；clock/trace cursor 的值只控制记录分支并在原数学前合流。D-AIC:2117–2121 的 source marker/MMA、2122–2218 的记录分支和回边是具体例子；overflow 分支仍返回同一原 continuation。

因此这里不是仅凭“没有新增 barrier”放行，而是同时核了原数据/控制来源、独立 trace 目的地址、原关键等待覆盖、helper completion cut 与实际 buffer 参数。记录器有显著额外指令/GM traffic，会扰动观测；上述结论不声称零开销或普通执行时间逐点保持。

## 实际 occurrence 与剩余资格的分界

- sparse raw SHA `3d15be391a1114026c169ea4809958ab59324646070b7048fa5c4cf816d0e07d`；default raw SHA `617cf28cb29a7ec76eef2c1390935e5cf982401aac6bf4ec3f657beb6d0b32fe`，亲自核同 capture 登记。
- 两份 retained events 分别 complete、112/160 intervals（224/320 endpoints），6 个实际展示 observer、无 dropped。每个被展示 AIC：循环内 `WAIT(3,4,1)`、`WAIT(3,4,2)`、`SET(4,3,0)`、`SET(4,3,1)` 各 6 occurrences；首轮两 initial SET 各 1、末轮两 reuse WAIT 各 1、M→FIX SET/WAIT 各 1。default 的真实 AIC dot 各 6 次；与 6 轮真实非空提交及固定 buffer/event 复用一致。未将这些 occurrence 改写为 native/source iteration_id。
- 本次直接细查的是 repetition0 两 capture；result 登记其余 warm 数学与完整性成功可复用，不把它们冒充本次逐 raw endpoint 重算。展示 program 是 (0,0,0)/(1,1,0)，不把抽样 observer 当全 grid 计时证书。
- 原 counter-map 仍 `counter_mapping_complete_region_unverified`，`region_boundaries_verified=false,record_value_provenance_verified=false,clock_epoch_verified=false`；capture 的 observed dependency 仍 `unavailable: Native instruction/getter bindings are incomplete`，`time_arrow_verified=false`，原 dependency exports 为空。**这些 timed-flow/native qualification 未由本审计关闭**；不能用这份 preservation 报告给它们填 true。针对该 BK32 原件，若今后主张 P07 时间箭头，最少仍是把这些已具体定位的 control sample 的 reader→raw 值流及所需端点 clock 资格绑定，而不是另添完成同步或猜跨 actor channel。本报告不要求为本次静态关系结论先实现通用 ISA/alias 证明器。
- 原 result 的 `device_stream_span_ms` 明确含 host submission gaps（cold 还含编译/采集等待）；warm sparse 约186–193ms、default约201–203ms 对照普通 sub-ms 也不能据此换算纯 device logger overhead 或 hardware overlap。它是原始扰动/耗时记录，未证明 busy，也未据此额外判一个原合同没有阈值的失败。

## 缺陷、缺口与最少下一步

**Confirmed blocker / major / minor：本有限审计未新增确认缺陷。** 未发现必须先修改 runtime/插桩才能保住上述 BK32 原有关键关系的具体路径。

**Verification gaps：** 上列旧 capture 的 native sample/value-flow、相应时钟及实际 timed dependency 资格仍独立开放；本 BK32 亦不是证明有非空未来 MMA 的 overlap 案例。其它 BK/stage/target、其它后端与整个 C2 范围未由本报告审核/关闭。

**本有限项最少下一步：** 将这里已绑定的关系表、同 SDK helper 及“每轮原有 completion cut，因此该 cut 无非空 future”事实归入 BK32 三方 qualification 记录即可；保留现有 partial/unavailable 字段。无需为了声称漂亮 overlap 改 stages、加入新同步或重做数学矩阵。若另行继续 P07，沿原已命名的 reader/raw/clock 缺口办理，不从本报告自动授予 timed flow。

**Optional：** 文档或 qualification 摘要可直接注明“本 BK32 普通版本每 MMA helper 原有 drain；支持关键关系保持，不声称跨轮 GM/MMA overlap”。这是呈现澄清，不要求删除 source membership、改 raw 或重新计时。

## 同轮文档澄清的有限追加

报告形成后，另静态阅读 parent 新增的 `Profiler/docs/timeline_runtime.md` 两段 diff（文件 SHA `2459a651edf15960b54df90a9323b3439aea5f9d0d0b1e028081186534ff671d`）。其 observer 两读钟区间、source navigation 不承诺所有 membership 指令均在区间、Asc recurrence 的 vector mul/add 与 induction 位置、occurrence 非已证 iteration_id、wait-return 仅给所述 readiness、zero-width/missing 保留等说明，与本席已审原件及本次关系结论相容。未见该文档增量改动资格门或把 issue 提升为 busy/completion；没有源码/ABI/计时变更需要在本追加中执行测试。此追加不覆盖文档以外的并行修改。
