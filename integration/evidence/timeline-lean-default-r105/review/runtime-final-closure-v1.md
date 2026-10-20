# R105 R2：最终 runtime 收尾

请求配置：GPT-6.1-Sol / xhigh。resolved serving model/effort 未暴露，**unknown**。正式冻结为 **`244bd8c1bc67071b6ddf4eee7a62221fb0152b5a`**，产品行为冻结为 **`6e78f136214da74254211fa19b90a3f7b7353fa2`**；本席用 Git 核对两者间 Profiler/Debugger 产品及 integration patches 无 diff。当前 quickstart 的未提交修改属于公共示例命令说明，未以未冻结文档冒充产品变更或安装验证。

本报告延续本席 [runtime-final-requirements-v1.md](runtime-final-requirements-v1.md) 的 mandatory、E01–E12、P01–P10 表，以及自己 R075–R103 的独立有限 closure；不重新整体走查或执行矩阵。不读其它席意见、新 q11/q12 数学源码，不 import/执行产品或测试，不运行 SDK/设备/服务器/TP/UI。只读 Git、文本和已有直接证据，写本报告。

## 当前判定

**没有未处置的 confirmed blocker/major/minor，也没有另须实施的 runtime 功能工作。** 原三后端公开内部采集、实际 source/observer/raw 身份、限定 clock、真实异步关联、ordinary 关键 pipeline、owner/预算/恢复、兼容及 Perfetto 消费要求，按原声明的有限范围均可复用已核闭合。

**whole 尚待 V1 完整24份 q11/q12 新数学原件及 V3 最终冻结/交付事实。** 父任务通报的21/24进度不是本席的完整证据闭合，不提前授证。下表是此时状态，完整 primary 到齐后只追加这两项；不要求新实现、旧矩阵重跑或全部静态诊断成功。

| 原要求或原问题 | 当前状态及证据边界 |
| --- | --- |
| mandatory runtime / 三后端 P01 vertical | 公开 CLI/API 自动编译与实际 launch→device raw→canonical→有资格的 time/dependency→标准 Perfetto 已通。独立新数学最后泛化补项仍待 V1；不能以辅助 graph 成功替代它。 |
| 多内部正区间、source、runtime-loop / 原 G1/V4 | R105 已核既有有限 SDK/native family、producer 原位置/body、typed tuple/编译闭包与 raw 的适用连接；GCU R098 required96 和 Asc R104 fresh96 各按原范围。source 多对多、原 block-fragment/issue/wait 语义不升级为 exclusive cost。无需 current96 每个可选 fragment static status 都成功；新 planner 在新矩阵结构的事实等 V1。 |
| 真实 writer / ABI / 发布 / loss / P04–P05 | 三个物理解码器与全 raw 校验、Asc 实际 participation、GCU full identity/descriptor、NV 隐藏 actor loss 均已闭；未选择与丢失分开，不补空端点。 |
| clock / P06 | 既有来源、内容身份、位宽/单位/窗口、domain/epoch 的正负例维持。此次无 time/clock/producer 改动，不重开。 |
| physical 动态依赖 / P07 | 原每 backend 专用实际异步样本及两代 buffer/flag/tag，原 wait 覆盖和 generation 资格维持。每 capture 的时间门与每 backend 专用 async 门分别通过，不强迫每 capture 有 flow。 |
| ordinary/default/sparse 关键关系 / 原 G2 | 本席 R083 NV、R091 两家 BK32 三方 primary/SDK helper 对 submit、publication、consume、reuse/flags 的有限对应已闭。不是硬件 busy、实测 overlap 或逐字节 schedule 一致资格。 |
| owner/readback/release/异常恢复 | 原 resume、unknown-free quarantine/ledger、stale index、完整 owner pending-release 校验、CAS/public reader 与 bounded owned-child 修复均已闭；新 provider/store 的独立有限修复已 matching。无新全局同步要求。 |
| E01–E12 | 原 R105 表逐项闭合/范围限制保持；E02 的旧阅读限制不自动变成新设备门。V2 只针对新默认文件的预算风险，现已闭。不得把 CPU fault/零-grid fixture 称新设备正例。 |
| P02、P08–P10 | target/SDK/ABI/cache 前置身份、真实适配边界、公共 validator/exporter、legacy/离线恢复及三家实际安装维持。原1740及后续 SQL/UI 证据按未变范围复用，不再跑全套。 |
| V2 Asc 默认 E01 bundle | **已闭**：正常安装6e78、450成员核同；CPU owned-copy 十次真实 installed default decode，禁 Popen/aux、仅 machine 使用原同 binary facts，before=after66,815,281B；raw/pftrace/ns/原dep保持。此项不冒新设备/数学执行。 |
| V1 两个独立新数学 | **待最终 primary**：完整 ordinary/冻结/eligible/24 cold-warm result、每调用 source/实际 compute body/循环、数学/input/tail/once、完整性/单位与预算、原始失败和身份索引。只补既定 q11/q12。 |
| V3 最终交付 | **待最终 primary**：匹配 source/install/native复用身份、原失败/修复映射、最终 Git/远端/clean、相关 owned 终态/live 清单和三席问题处置路径。文档/证据 commit 不触发新安装或设备运行。 |

## 保留的时间解释限制

以下限制是真实能力边界，应随交付说明保留；它们不是新增待实现门，也不能用于掩盖实际计时、身份、完整性错误：

- **NV**：在原证据支持的实际 invocation/program/单 CTA epoch 与目标上使用 u64 globaltimer/1ns；不把这一范围扩张成跨 GPU、跨 invocation 或任意目标同步。
- **Asc**：实际 SYS_CNT/20ns 和原保守有效窗口、实际 actor participation；导出范围沿 provider proof，不因原始 i64 字段就承诺无限计时窗口或跨 observer 任意绝对对齐。
- **GCU**：实际 full SIPINFO/capture 的 rational scale与窗口；helper 的46bit是返回值表示上界，不是独立测得物理 counter 模周期。相同 MMIO 地址不证明跨 SIP 共享 epoch。
- **observer/source**：代表性 writer 的 issue、wait 返回、原 block-fragment elapsed 不等于整个协作主体耗时；融合 source 导航不拆分 duration，不授 source-exclusive/all-SSA 成本。未知精度、participation、source iteration ID、静态模糊匹配保持未知。
- **engine/dependency**：真实动态 flow/原 wait cut 不授 engine busy、精确物理完成、跨域 overlap。不同 clock domain 不归零拼成并行；坏单位/不确定回绕不 clamp。

用户已批准暂缓的 NV 独占性能实验保持暂缓。已有 C1/C2 普通参照与扰动说明可按原 scope 交付，不把插桩 span 或 SDK host 提交/编译间隙冒充纯 kernel overhead 或调优收益。

历史首次失败继续保留：NV 七条零记录拒绝且有限未复现不称修复；Asc 原 reserved-unknown partial/48+24 dependency unavailable 不倒洗；BK64 sparse1 严格失败不计 default；原 Asc E01 whole 失败和 CPU whitespace 修复、脚本检查错误与其后正确收据各自记账。此后仍须对新真实失败按原分母处理，不能用可选 metadata 的性质豁免。

## 停止范围与后续动作

本席没有新增 optional 工程项目。停止扩建全 ISA/全 SSA/全 CFG/全路径 iteration-ID、逐算子批准、全部 static fragment 证书；不新增 source-exclusive、busy、hidden scoreboard、同 issue order 或未变 State/clock/SQL/UI 的验收。若 V1/V3 原件无矛盾且产品未再变化，本席只核其终态、内容身份、最低每调用结果与交付事实后追加 closure，无需再次 whole 代码审查。

## V1 新矩阵数学/raw/planner matching closure

**V1 的受影响新数学、实际 raw、planner/循环 body 与默认产物范围现已关闭。** 此追加取代上文21/24及等待完整数学原件的状态。当前仍待这批新144份 trace 的已计划 pinned TP CPU 导入，以及 V3 最终 owner/Git/交付事实；不提前称完整 whole 已交付。

直接读取 `preflight/new-matrix-aggregate-v1.json`（SHA `2299304d7071efe9a481d3f90962736ecaa6708def22674a0d02e1c2b0f747cd`）及所引八份 result/terminal；各 result SHA、terminal SHA 均与实际文件匹配，八个 controller terminal0。另核四批 index：`phase-receipts-v1-recovered` 871项、v2 36项、v3 30项、v4 45项，合计982项 size/SHA 全匹配。这里是本地 stdlib 文件审计，不是执行产品或 qualification checker。

预先冻结 manifest SHA `6ec0dacb76b4ce9884827141d5f38a90e293cbffe4843193e2c63eda5bc50e86`，声明独立作者、受影响 Ascend910B4 矩阵范围、两种不同数学及固定输入/oracle/tolerance/结构预期。没有读取新数学源码；其冻结文件字节只按 index/hash 核对。ordinary 原结果为8/8组合通过，terminal0；两 shape（含tail）×两 config ×两数学，未排除 ordinary-eligible 失败。每份 profile eligibility 绑定本组合 ordinary report SHA、真实非空 contraction/loop 的 retained TTIR SHA 和同一 manifest。没有拿单纯 ordinary 数学成功代替 profile 结构检查。

八组均为 cold、warm1、warm2，合计24份，产品 source 全为 `6e78f136…`、实际使用新正常安装/NPU4公开 CLI。每组 cold/warm binary 相同；八组为八个 specialization/binary，24个 capture invocation 分开。这里4/6次属于两 shape 的实际 device TileLimit，**不把两 shape 的不同 binary 冒称同 binary 改 K 实验**；原 runtime-K 同 binary 门沿既有独立证据保持。

本席逐读受测 launcher、24份 math/application-terminal/host-once 与八份 eligibility/ordinary 对应：所有 application return0，status为 math pass，error为空；固定输入 SHA、冻结 source SHA、guard、不可变 runtime tile limit、logical state once 检查通过，host marker 每次 requested_launches=1。launcher 调用公开 CLI 后 fresh `load_capture`/raw decode，拒 pending/failure/retained owner、任何 incomplete/drop、guard改变、缺 ns、缺真实 dot及不匹配 occurrence；没有读取可选 cached fragment status来决定成功。这些是新实际数学/设备结果的原始收据，不是用 CPU synthetic interval 补出的正例。本席没有重算私有 oracle 或把报告中未另授的 physical-writer/native 字段提升为新资格。

| 本次最低功能 | 直接结果 |
| --- | --- |
| 多个正内部区间与不同source | 每capture35–66个正区间，7–8个不同正source origin；不是仅整核条或instant。 |
| 真正被修复的matrix body选择 | 每份有实际 selected `tt.dot` source；AIC observer的对应区间与实际 retained actor MMA call 同在编译闭包。q11原actor有2处MMA call，q12有3处；不只数 planner 元数据。 |
| 实际循环body重复 | 每个matrix site/observer为4/4或6/6 occurrence/positive，共72条site-observer结果；每份均超过三次body最低要求。未用loop容器计时替代compute issue区间。 |
| raw/完整性/调用 | 24份各786,816B，128B guards另计，fresh decode complete且drop0；各调用自己的raw SHA和capture，未跨调用补空。 |
| 时间/标准导出 | 每份6个counter-ns导出及6个标准`.pftrace`，共144份。沿既有实际unit proof；engine busy和source-exclusive仍false。标准文件存在不冒TP导入已过。 |
| 默认产物与预算 | 全部默认无auxiliary graph字段/目录；timeline包为2,461,976–3,418,453B，远低于64MiB；raw含guard低于8MiB。原CLI冷编译/导出预算按冻结值执行且终态0。 |

此补项满足 planner 修复后至少两个独立新数学的原要求，支持实际 compute issue/真实 loop/source/raw 的有限功能泛化。没有确认新的 runtime defect，也没有增加新实现或验证门。原 clock/State/async/pipeline/旧数学与旧SQL/UI闭合不重开。

**当前最短剩余**：原本已计划的144新trace pinned TP导入/SQL结果（CPU，无新device/UI）及V3交付终态。到齐只需核新索引/原 stats/owner/Git；无需重跑这些24数学或新增静态证明。

## 新144 trace 的 pinned TP 与本轮 owner closure

**新增 trace 的 P08 导入/SQL及本轮 owned工作终态现已闭合。** 这取代上一追加中的 TP/owner pending；当前只余最终 Git/交付冻结事实，未提出任何新的 runtime 实现或测试工作。

直接核 `preflight/tp-receipts-v2/tp-receipts-index-v1.json` 的 **874项 size/SHA 全匹配**。原回收 archive 身份为 `b9a28cd306ffa8a08b4d628b2fa9a450e02f8bdfb817e3f2282cff117460aa5e`（本席核解包索引，未另外重跑/重导 trace）。controller terminal0 / **43.443762926s**，受测 CPU driver SHA `97c75a0f39b771dd1cdb5473410dac2f2a19118b7a74f09afe64ff598e999164`。它先逐输入核 size/SHA，复用原 verifier SHA `75e1b08b1dd71256dd442f6ad3bfbffe745ba900026e8f6493e6ef208931a618`，用既有 pinned TP环境实际逐份导入；没有产品、设备或应用重放。

`runs/new-matrix-tp-v1/output/result.json` SHA为 `282131afb4fd8c65bb8b89983e116ce875d5173bbbca84b2c7bc13c27d8995d1`。本席遍历000–143全部独立 terminal/manifest/`verified/result.json`，不是只读aggregate成功字样：**144/144 return0**，result SHA与逐条receipt相等，全部 `fixture=False`、`exact_ns_and_raw_references=True`；每份完整 **263条 importer stats**，无正 error/data_loss、无 importer_errors。24个组合/repetition各恰6trace；每份manifest的invocation/raw SHA与前述24实际capture对应，无借其它调用原件补数。

导入的是这次数学产生的真实标准counter-ns protobuf。它证明原 raw/单位/精确导出坐标及 TP 消费，不追加 source boundary、read precision、async 或 UI 资格；`not_full_P01`等原verifier限制保留。UI沿既有未变范围复用，本次没有重复UI，也无需追加新设备矩阵。

直接读 `preflight/ascend-owner-v1.json`（SHA `ee9a0c65f9bb35b15bb8c64e7086630c597807d29fbc1d710253742cecc9b985`）：本轮12个Asc owned job、24个登记controller/worker，terminal均0且其SHA与原收据匹配，全部同身份已absent。TP原 `owned-final.json` 列worker absent；controller同startticks仍为 **Z**、`same_identity_running=False`。据此可称无本轮同身份运行任务，不能把Z写成“PID全部已消失/已reap”。这是已有owner检查收据的审计，本席没有自行访问服务器。

至此，本席原 mandatory/E01–E12/P01–P10 中的必要 runtime 功能/受影响验证没有新增剩余；原限制、历史失败和NV性能批准暂缓照旧。只等最终source/Git/远端/clean交付事实做最后记录；不为证据或文档commit重装/重跑，不以未扩展的static资格重新开门。

## Runtime 最终接受与 Git 归档收尾

**本席通过原完整 mandatory runtime 范围及 E01–E12/P01–P10 的最终审阅：无未处置 confirmed blocker/major/minor，无尚需实施或补证的 runtime 工作。** 以上 V1、V2、TP 和 owned-work closure 均保持；不是“全部可选资格为true”，而是在原 timer/observer/issue/wait/适配范围内满足合同。engine busy、source-exclusive、任意跨域 epoch、未证精度/参与及NV性能批准暂缓等限制继续随交付保留。

直接读取 `preflight/git-delivery-v2.json`；该阶段收据记正式 `detailed-profiler`/candidate/已核remote均为 **`891281f2a432d213e256c0ab7d61326b5cb4abd4`**、canonical clean、无force push。本席另用本地只读Git核canonical和candidate实际HEAD均为该SHA，canonical工作树确实clean；candidate仅新增 `integration/evidence/timeline-lean-default-r105/HANDOFF.md`。6e78到该提交的产品/后端patch路径无diff。remote相等是所读交付收据的事实，本席没有另行联网查询。

已读当前HANDOFF：列匹配安装命令/实际trace及原UI路径，明确新144SQL为CPU导入、默认实际区间与显式静态辅助分析分开、历史失败和时钟/observer/engine限制。它没有引入产品调用或新资格。quickstart公共应用示例去`-I`与已执行真实命令一致；这是说明修正，不要求因文档再build或设备执行。

**最后仅报告/HANDOFF证据归档commit由root完成常规ff、push及clean核验，并保精确Git终态收据。** 该归档不改变6e78产品行为，不需要再一轮runtime审阅、安装、数学、SQL/UI或其它验证。最终Git receipt到齐只补交付SHA记录；不能据报告归档递归制造新的产品验收门。此处接受的是本席独立runtime范围，不依据其它席投票替代事实，也不修改论文/Study。
