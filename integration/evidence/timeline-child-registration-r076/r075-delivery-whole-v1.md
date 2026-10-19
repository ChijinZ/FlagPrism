# R075 独立整体 delivery / acceptance 复核

评审对象：请求冻结的正式 `FlagPrism-method` / `detailed-profiler`，`ea27308b009427f7137299daa71ae1f09f045c8f`；runtime source `efb23636c2aa3a6e8866875133765c4de3a00f91`。开始检查时正式工作树 clean。收尾时正式 HEAD 已前进到 R075 tooling 提交 `1dd2baafd0458a33141702c2c332495be733f66c`、仍 clean；针对 runtime/Debugger/安装实现的 diff 为空。本报告的产品结论仍绑定原冻结及相同 runtime，R075 新材料作为 qualification tooling / 原件离线取证单列，不冒称已经改变或重新安装 runtime。

配置请求：原最终三席中的 R3，GPT-6.1-Sol / xhigh / 原始 fresh independent reviewer。实际 resolved model / effort 未向本席暴露，记 **unknown**。未阅读 peer 报告或其结论；未运行产品、import 产品、测试、SDK、设备、TP 或 browser；只用 Git、文本和 Python stdlib 读取现有证据。仅写本报告，不改实现或论文。

## 结论与真实剩余清单

**现在不能按原合同签署 whole-goal 完成；“只剩 NV pipeline”不准确。** 除 NV 普通流水关键关系的保持证据外，尚有三项实质缺口：Ascend/GCU 自动有限 source/loop boundary 链、独立数学原 kernel 的 State 写者实际 lowering、GCU 原超预算 cohort 的逐登记修复闭环。最后两项可以先只读已有对象或对保留 bundle 做 CPU 处理，不能用新数学、全矩阵或重复 TP/UI 代替。

最小顺序如下：

1. 从原登记/已执行对象补 **State 存储的合法唯一写者依据**，并将 GCU 原 budget failures 与已有 13 个修复调用按 case ID 连接；只对尚无闭环的原 bundle 无损重排并计量。这两项不需要应用重放。
2. NV 继续当前有限 ordinary/default/sparse 对应分析；R075 已补的 matrix 输入 word/raw generation 绑定应计入，剩余控制根/slot/group/wait/reuse 对应不能由“相同指令数”替代。
3. Ascend/GCU 在现有真实纵向样本上补通用的有限源区域、runtime loop 和适用原 wait 边界检查；先读已有最终对象，不扩大为任意 ISA 或所有端点形式化证明。不能只再增加 debug-location/positive-count 检查。
4. 用这些规则对原资格登记补各门结果。只有确实需要改变生成代码、且旧对象不能支持所需结论的部分才做受影响采集；不预设重跑 72/96 次。完成对应有限复核与最终交付收据。

本轮没有新确认的错误输出、崩溃或安装代码缺陷。下面把**可定位的实现能力缺失**与**尚缺证明**分别列出；不将保守返回 unverified 本身称为错误时间线。

## Confirmed findings

### C1 — Major acceptance / implementation gap：Ascend、GCU 尚无合同要求的自动有限区域/循环边界放行链

**位置与触发。** 普通用户从 `Profiler/python/flagtree_profiler/profile.py:1579` / `:1589` 启动 Ascend/GCU timeline 后，现有自动后处理能得到 raw、单位、导航及有限依赖；但未形成 design §0.5–0.6、§8.14 / testing P03、§0.2 所要求的 source 区域、实际控制路径和 runtime loop 的适用规则收据。

- Ascend `timeline_ascend_machine.py:161` 的 `counter_map` 实际核最终 ELF、actor function、DWARF 与 SYS_CNT word；其返回 `region_boundaries_verified=False`（`:266`），没有检查对应 fragment 运算/loop 的实际控制边界。`timeline_ascend_offline.py` 将这条映射用于单位与依赖 provider；没有另一个通用 source/loop checker 补足这个事实。
- GCU `Debugger/lib/Instrumentation/GcuNativeLocations.cpp:126` 输出明确是 `compiler_debug_location_rows`；`:132–133` 保持 source-region / reader-valueflow false。Python `gcu_timeline.py:360` 起严格检查这种位置报告，然后保存 `missing_phase_locations`，没有从实际 caller/operation/loop 到 timer 的边界语义检查。

**实际证据的范围。** R063 对一个已实际执行的 Asc recurrence 原 ELF 给出 site16 的 VMULS/VADDS 与两个 store 的位置；追加检查只覆盖 site16 到 VADDS 的连续无跳转 prefix。原 SDK child139、缺失 CSV rows、外部入口/区域剩余路径都如实保留。它是有用的局部证据，未进入公开自动放行链。R066 的 GCU 实际 helper 证明低/高 word、rollover reread、46-bit 返回上限和 SIPINFO 形状；原结果仍明确 `actual_inline_reader_to_raw_binding=false` / `source_region_qualified=false`。R069 正常新工具、新 wheel、两实际数学及 48/62 个最终 ELF 位置，证明了真实代码位置服务；shared end-block 解释正确关闭了“少独立 row 就是丢 clock”的误判，但不补 caller/运算/loop 的边界事实。

**后果。** 现有 counter bracket 与来源导航可以交付为明确 partial；不能因此把三后端 P01/P03 或原 goal §8(2)(3)(5)(6) 填满。这里依据的是实际缺少语义检查，不是单凭一个保守的顶层 false 字段要求更强资格。NV 的有限 issue/origin/native-loop 规则是独立进展，不能移授另外两个后端。

**最小补项。** 每后端先在已有 runtime-K 纵向原件上：精确绑定 caller/site 与 getter，核至少两个必需真实源区域的实际运算/访存及路径；对实际 loop 核头/回边/出口与配对端点；对该后端专用 async 样本核原 wait 覆盖及相应路径。规则按通用结构而非算子名选择；用字段与身份自洽但运算越界、出口绕过、caller 错配的负例证明确实检查语义。可先离线读取已有对象；不要求所有 ISA、source-exclusive cost、整个协作体 elapsed、busy、所有 marker 独立行或实际不存在的变换。

Confirmed blocker：无新增。Confirmed minor：无新增。C1 是原交付能力尚未完成，不是现有 partial trace 被证实伪造。

Optional：无新增实现要求。现有证据索引的最终引用整理可随交付收尾完成，不应成为再建框架或重复实验的理由。

## Verification gaps

### V1 — 独立数学的 once oracle 尚缺实际 State writer lowering

**位置/触发。** testing §4 明确要求合法唯一写者或独立不重叠写入，并先证明实际 lowering。原 frozen registry 的 reduction 条目也明确写“actual lowering still requires qualification inspection”。三家 `../.timeline-qualification-r052-private/dispatch/{nvidia-ordinary-v2,enflame-ordinary-device-v3,ascend-ordinary-v2}/baseline-freeze-v2.json:9` 都记录 `physical_state_writer_lowering=not_inspected_yet`。

**直接证据。** 当前 R062 的 60 份 `integration/evidence/timeline-affected-repair-r062/math/*.json` 中，48 份 `actual_state_lowering_verified=false`，12 份 `physical_writer_lowering_verified=false`；相应 logical-index / state-count 检查确实为 true。例 `math/000.json:2` 与 `math/048.json:38`。本轮逐文件统计了这 60 个结果；未找到后续关闭这项的实际对象收据。R016/后续的 timeline logger writer、guard、地址与发布检查是采集器写者证据，不能替代原 kernel 的 State store。

**后果。** 真实数学/input/tail/state 值与 host-once 通过的事实保留；尚不能把这些结果概括为原合同的完整、已证合法 device-once oracle。没有据此确认原 kernel 真的有重复非原子写者，也没有确认产品发生 replay。

**最小验证。** 在三后端已封存的 ordinary/profile 编译对象上，定位原 State load/store（与 trace scratch 区分），核地址索引、尾部 mask、物理 lane/subblock/writer 选择、归约后 scalar store 的合法化；若用 atomic，则核实际 lowering/原语语义。对相同通用 lowering 规则可复用证明，但绑定各原登记所用对象/配置；把既有数值与 host-once 收据连接起来。不重新写数学，不先重跑所有调用。若实际发现不合法 writer，修 oracle/通用 lowering 后再决定准确受影响范围。

### V2 — GCU 旧 bundle 超预算失败尚未逐登记闭环

**原分母。** 原六数学 72 次中 15 个完整 bundle 超 64 MiB；补充 24 次中 21 个超限。初始最大分别 75,523,050 / 131,872,860 bytes。这些是冻结硬预算失败，不是 UI/数学失败，也不能因 TP 成功升级。

**已完成。** R055 metadata/compact 的 retained CPU 实证把最大补充原件变为 66,230,992 bytes，恢复后的三个 logical JSON 与原值一致，另 61 文件 SHA 不变。13 个真实受影响调用（原 12 个缺 primitive coverage 的调用 + 最大 q07 cold 一次）全部通过原预算，最大 64,984,633 bytes。它们是有效修复证据。

**缺口。** `.timeline-qualification-r052-private/profile-stage-v1/first-pass-summary.json`、`supplement-profile-v1/final-result.json` 与 `gcu-affected-r055-v1/final-result.json` 的实际范围没有给出其余原超限 case 的新 bundle 大小或严格适用的统一上界。单个 pre-repair 最大包的压缩后大小不是所有布局的 post-repair 上界。本轮与 root 定向核对均未定位到该 cohort-wide 闭环。

**最小验证。** 先按 case ID 去掉已由那 13 个真实修复调用覆盖的项，对其余**原失败 bundle**复用 run055 metadata-test helper 做 CPU-only 无损重排；逐项记录 complete-directory bytes、64 MiB 判定、logical JSON 恢复相等和 raw/trace/编译原件 SHA 不变。保留旧失败。若仍超限，修通用 dedup 再处理同原件；无需重采数学、旧 TP 或 UI。该项未闭合前，不能称 GCU 全独立资格预算均通过。

### V3 — NV 普通流水的关键关系/合法 overlap 机会保持仍未证

**位置/事实。** `timeline-native-inputs-r074/summary.json`、实际普通/default/sparse 最终对象及 R075 原件显示：实际 HMMA/copy issue 排列不同；这不足以证明新增完成依赖/串行化，也不足以证明保持。R074 的 9 个 copy-input cone clean、17 个控制根中 14 clean，默认三个 P2R/PR 来源控制根仍未证；40 个实际 matrix prefix 中 32 存在非空 2048-byte future committed group，是 instrumented prefix 事实。

**本轮已计入的新进展。** `run-075/preflight/receipts-v1/final-suite-v1` 为 actual terminal0，48 个 fixtures normal/-O 通过；matrix 输入检查核 ordinary 四个 HMMA 的实际 load words，以及 default/sparse K3/K7 共 960 个 raw-backed word/generation bindings。不能继续说这些 MMA inputs 完全未绑定。`bounded-register-result.json` 核 26 个 cone，保留默认 PC5360/9264/10976 的 P3–P6 entry definitions 未解析，且 `input_values_fully_verified=false`、`through_memory_dependencies_verified=false`、`ordinary_preservation_verified=false`。`steps.json` 的最后输入检查 rc1 被保留；外层 terminal0 不能抹去该正确 partial。此前 packed-v1 的 terminal1 也保留。

**后果与最小验证。** 专用 NV observed-dependency traces 能解释其 instrumented invocation，不自动代表 ordinary pipeline。继续在现有对象上做 ordinary/profile group/shared-slot、原 wait/CTA cut、已绑定 MMA 读数与 reuse 的角色对应；只解决对所选关键路径确有影响的控制根或说明其不影响所需结论的有界理由。不要求相同 issue 次序、hidden scoreboard 全解码、所有指令输入定义、engine busy 或用户已延期的独占开销认证。只有发现真实新增完成依赖/关键关系失真才修产品并做受影响采集。

### V4 — 全分母的 source/loop 判定与受控解释需在上述事实闭合后连接

原六 + 补二的数学、raw、counter-ns、多正 site/interval、原失败与多数受影响修复都是真实的；它们当时也明确保留 boundary unverified。R061/R069/R072/R073 的开发样本和有限对象规则不能自动升级原全部 case。最小工作是复用原注册表、对象和 capture，列每个必需 source/loop 门的实际规则/失败原因；不能只以 trace 数量或 summary 的 multiple-positive 计数代替。此处不要求新建另一套进度平台，也不要求所有 endpoint source-exclusive。

C1/C2 已有真实干预、重复与普通参照，不缺“再跑两套案例”这个动作。GCU 文档所述 C1 同 binary 的 3/7/11 occurrence 与 1514–1545 / 3496–3570 / 5503–5581 ns，C2 同工作量 BK32/BK64 的 6/3 个 matmul bracket 及对应总和，能解释 **instrumented counter bracket**。Asc C1 的 extent 不单调已如实记录；不能据此宣称工作量更大必更慢。C2 普通/稀疏/默认的 SDK-input primitive ordered projection 是有用证据，但不是最终依赖保持证明；Asc BK64 sparse1 第二 capture 只有一个正 interval 的失败必须继续保留，不计默认成功，也不变成必须重跑的整个 default 矩阵。

完整受控结论仍依赖 C1/V3 中适用的边界与关键关系。将既有 Asc/GCU ordinary 与 repeated-window/noise 原数连同可解释/不可解释范围归档即可；SDK event span 包含 host gaps，不能变成纯 kernel overhead 或普通收益。未提出新的精度阈值、预定加速或 NV 性能要求。

## 原 goal §8 八门逐项判定

| 门 | 已有真实完成证据 | 当前判定 / 最小余项 |
| --- | --- | --- |
| 1 三后端普通默认入口、不改 kernel | `profile.start(detail='timeline')` / CLI 都有实际安装与 ordinary 采集；compiler 自动选 site；首末 program、tail、多调用、部分两流真实收据；当前公开 quickstart 的 cann/ascend 区分正确 | 基础公开采集链已完成，无本轮确认的算子名/shape/hash 特判；完整“合格内部源区域时间”仍受 C1/V4 约束 |
| 2 独立六数学、补充泛化、全 gate 与首次失败/修复 | 每后端 24 ordinary + 72 profile，另补二的 8 ordinary + 24 profile 已执行；原 source/input/config/tolerance 登记保留；NV unit/capacity、Asc affected60 等有准确修复收据 | 不能签全通过：V1 State writer、V2 GCU budget cohort、C1/V4 source/loop；原失败不能改为首次通过 |
| 3 三后端多内部区间/循环、各真实 async 与时钟 | 三家实际 getter/raw/单位/occurrence；NV 真实 shared-byte reuse；Asc recurrence flag generations0/1；GCU tag generations与真实 descriptor 地址；三家有需要范围内的 counter clocks | async/单位事实不能重开为“全无”；完整 P01 仍依赖边界与 ordinary 保持的适用检查。无需跨所有 AIC/AIV/所有物理 counter 建共同 epoch |
| 4 实际 TP/SQL + 实际标准 UI | R059 1740 traces；R062 新168；R069 新8；R070–73 变化的 dependency traces；实际标准 UI 多算法、slice/flow 选择、来源/raw 详情、截图 SHA 与前后 bundle hashes | 已有展示/导入证据可复用，不要求重导同字节或重跑旧 UI；历史失败/撤销 trace 不能因 TP/UI 合格变当前资格成功 |
| 5 两受控解释案例与普通参照/噪声 | 真实 C1/C2，GCU 三重复内部计时解释；Asc/GCU 密度对照和 ordinary/SDK span 原数；NV 保留性能延期 | 采集动作已完成；解释不得超出 boundary/关键关系证据，剩余见 V4；不另要求预定收益或独占性能认证 |
| 6 匹配正常 build/install、故障/兼容、P01–P10 | 三家正常 native target / matching wheel；后续改变的 NV/GCU tool 确实重建；未变 core 源核同复用；normal/-O、真实 raw/guard/recovery/offline 证据 | 工程链有实证，无本轮新安装 bug；P03/完整 P01 与 V1/V2 仍未闭，不用 CPU fixture 冒设备正例 |
| 7 原指定额外三独立代码审阅、修复/有限复核 | R057 原三席 fresh 请求事实保留；本席原五项具体问题已由 source、正常安装与实际受影响收据闭合；本报告是当前整体审查 | 本席不能代签其它席或根处置；本轮三份整体审查与必要修复后有限 closure 仍需收齐，不需要每个小 delta 再 spawn 三个新 reviewer |
| 8 Git/remote exact/clean、记录/终态、不改论文 | run074 `git-delivery-v1.json` 的 fetch/ancestor/ff/push/ls-remote 精确 ea27308；本轮本地正式 clean；runtime 与 R073 安装一致；旧 owned device/browser terminal 收据保留 | 该正式 freeze 已交付。R075 tooling 是新 delta，最终收据/源字节/提交与最后 owned-job 清理另核；未把本次 review 文件或外层0当 whole-goal 完成 |

## 独立矩阵、修复及 SQL 的分母

本轮重新检查了 R057 attempt-index 的九个 local receipt SHA，全部匹配；原 ordinary index 的三家各24组合/8个 runtime-K 辅助调用也有独立终态与原对象绑定。补二是已冻结的 q07/q08，不虚构为 q09/q10。看过失败编译产物的样本及受影响 rerun 必须称修复回归，不能把后来成功重写为“96 次首次全部未见通过”。

| 后端 | 原六 / 补二首次结果 | 已有准确修复范围及仍缺 |
| --- | --- | --- |
| NV | 原72数学均过；12单位缺失、9 writer saturation 保留。补24数学/ns/预算过，q08有12 saturation | 12旧 q04无重放重导；9 saturation + 1 q04 共10 actual calls；q08仅12受影响 actual calls；R061/70–73 后续设备/原件定向回归存在。缺失的是 V1/V3/V4，不能再报这33项仍无修复 |
| GCU | 原72数学/raw/多正区域均过，15 bundle失败；补24均过数学/raw/ns，21 bundle失败；原12 native primitive coverage gap | generic primitive coverage + metadata 修复、13 actual calls全过；最大保留原件 CPU 无损缩减成立。V2 的其它失败 case 仍需逐登记大小闭环，不能用13作为所有失败的替代分母 |
| Asc | 原72数学/raw/ns/observed-writer/预算过，但48 batch有未知 reserved slots；补24中12 batch有未知 slots，增强依赖 unavailable 原样保留 | R060 participant getter/count 协议 + 正常新 plugin/wheel + C1/C2 真机；R062原 q01–q04 48与q08 12，共60 actual calls修复 complete；59 controller0，首项 application0/controller1 的 auxiliary-snapshot helper错误以 retained-only 修复，108旧文件不变，不重数学。其它36原 complete按未受影响范围复用。V1/C1/V4不由此补齐 |

R059 `trace-index.json.gz` SHA `921cd412a8cc4160955b1764a1afe9b95c5d2ca6906991f9a8770b8a8ca6d6a8` 本轮逐1740行重新计算了 `proof_key = SHA256(sorted JSON(kind, input-file SHA set))`，核实际 `receipt_file` 字节 SHA、`receipt_row`、result trace SHA、importer errors；0差异。实际1737个 distinct result files（1735 fresh + 5 exact-input reuse 对应的结果文件复用），每行263个完整 stats，共457620行，没有正 error/data_loss。分母是 NV944 counter、GCU218 counter+194 dependency、Asc336 counter+48 dependency。

这1740是**全部已注册 retained views**，包含历史失败数据，不是当前成功资格调用数。R062 的60 registered repairs /120 counter+48 dependency另有168 actual TP/full stats/1176 flows及原件绑定。R069的新8、R072的72 counter/shared+8dependency、guard的2dependency、R073的2dependency均有现存 actual TP 原收据；相同 counter bytes 复用旧 SQL 正确。此前的错误目录/错 kind/猜分母等 wrapper failures保留，不能冒 device 重放或 verifier 放宽。

## P01–P10 与真实适配边界

| 项 | 当前可接受事实 | 未闭范围 |
| --- | --- | --- |
| P01 | 三家都有公开 raw→canonical→单位→真实专用依赖→共同 exporter/TP；真实复用样本不是 CPU 假后端 | C1/V3/V4 尚阻完整最小纵向放行；不能只凭 trace 打开算 P01 |
| P02 | actual target/compiler/plugin/layout/launch identity 与已知错配拒绝；backend provider唯一匹配；R058 pre-JIT身份修复有正常安装/实际入口收据 | 本轮未发现新的错配 bug；新型号不继承本次证据 |
| P03 | NV已实装 finite scalar/global/matrix issue、独立 origin、native loop路径规则；R073六 actual captures/208 intervals/416 endpoints；conditional EXIT修复的22 loop+13 matrix fixture normal/-O | Asc/GCU C1；全登记 V4；普通流水 V3。source iteration_id未知、source-exclusive false本身不是新增失败门 |
| P04 | program/observer/operation/resource分离；Asc AIC/AIV、GCU issuer/full identity、NV真实线程；公共消费者未读厂商 ISA | 不要求全芯片统一 warp树，也不要求未知物理主体补全 |
| P05 | 三家真实不同物理 layout接共同 schema；raw精确offset/guard/commit/loss；Asc参加者count只在有publisher依据时排除保留槽，legacy不改写 | 采集器 writer证据不能代替 V1 原kernel State writer；无需重新验证所有旧 raw |
| P06 | unit、独立窗口、原 ticks保留、整数/有理数换算、未知精度/epoch分别表示；真实provider及 normal/-O语义负例 | 不把unknown read precision叫比例无效；不要求专用single-observer关系之外的跨域同步 |
| P07 | NV真实物理 shared-byte reuse；Asc当前严格provider仍能重建recurrence两调用各2observer/42edges和flag0/1；GCU真实tag复用最大8/20及submit→wait-return | Asc旧softmax已在R058撤销当前推荐，不能继承。未要求每个独立数学capture都有flow；C1/V3适用边界/保持仍须闭合 |
| P08 | 一个 `timeline_perfetto.py` / `timeline_dependency_perfetto.py`、同一 raw/clock/dependency validator；实际三家TP/UI；common消费者无 vendor ISA分支 | 缺证不填源成本/busy，现partial展示不能代整体验收 |
| P09 | 实际五部件调用如下，复用的 owner/store/validator/exporter有真实三家调用；旧/新schema与provider拆分有正常安装/原件回归 | 建议最终交付把这些定位连到现有索引；无需第四芯片、LOC目标、五套空基类或新平台 |
| P10 | 缓存/工具/SDK/plugin身份；早拒绝及恢复；pause/resume实际修复；原件重导/历史撤销/decoder指纹；旧count/native/ABI normal/-O受影响回归 | 最终规则变化后按受影响项复核；没有证据要求重建所有未变core或重跑整个旧矩阵 |

真实五部件链（路径相对正式 repo）：

- **NV**：公开 `profile.py`→`hooks/timeline_late.py` / `timeline_nvidia_late_compile.py`→packaged `Profiler/Dialect/tools/late-timeline/late-timeline.cpp`（post ordinary O3）→`timeline_nvidia_late_storage.py` / CUDA transport→`timeline_events_nvidia_late.py`→`timeline_unit_nvidia_late.py` / shared counter provider→late async / native boundary / dependency模块→公共消费者。原core正常构建保留，R072原操作marker新native确实构建；R073 efb normal wheel641 members/18 steps0/source核同，264 native源不变明确复用，wheel SHA `1f72d16c08a1d60e6ddfb2875827bd7db17bff7ee9fe8dc700966a8ef4fcc521`。
- **Asc**：公开 `profile.py`→source compiler/handoff与 packaged LLVM15 late observer→`timeline_ascend.py`（真实compiled executable字典、实际NPU stream/event）→`timeline_events_ascend.py`→`timeline_ascend_machine.py` / `timeline_unit_ascend.py`→`timeline_ascend_native.py`→同一公共消费者。R058正常native/Bindings，R060新participant plugin正常CMake+真实opt、437-member matching wheel与实际GET.SUBBLOCKDIM/count；R062复用该准确组合。未要求把LLVM15插件加载到不相容vendor LLVM。
- **GCU**：公开 `profile.py`→maintained FlagTree source patch→`Debugger/python/flagtree_debugger/gcu_timeline.py` / 正常packaged native四TU工具与实际SDK hook→`timeline_enflame.py` / native runtime（原stream初始化、physical guards、完成后fullphysical readback）→`timeline_events_enflame.py`及 delegated `timeline_events_enflame_native.py`→`timeline_unit_enflame.py` / `timeline_enflame_dependencies.py`→同一公共消费者。R058 native guards实际SDK坏字节/保raw/新session；R069新tool真实重建、normal495-member wheel、10 CLI+15 normal/-O fixtures与两actual math，source/native/SDK身份有正常收据。没有把旧共享core冒称重建。

公共 `TimelineOwnerPool.prepare` 用 transport 的 `validate_executable` 与布局方法；Asc/GCU无需伪造CUDA function。二者传入真实队列整数；`num_ctas`为后端交接参数而非公共CUDA语义。共享 `_init_timeline_state` 可接实际transport；offline注册表只选择三个provider，decoder/clock/mechanism仍各自独立。公共 canonical/exporter/store不从厂商 raw/指令补业务语义。schema2、物理bank/paired records、guard-bearing readback、不可变canonical revision等共同修改都有真实第二/第三调用者及已有后端原件回归；这支持三后端边界成立，不构成未来第四芯片成本认证。

## 已闭合、无需重新打开的门

- 原R3五项 confirmed问题（resume、GCU physical guard、cumulative physical预算、counter子进程site参数、delegated decoder指纹）有源码修复、正常安装与对应实际/CPU收据；GCU首composite/第二startup失败仍保留，不能用whole失败抹去已通过resume子项，也不能冒称两次whole成功。
- Asc reserved slots不是永久缺口：R060设备participant字段和R06260重采已补实际所需完整性；旧没有字段的raw仍partial，不离线猜不存在。当前48/补24 unavailable增强依赖不自动是per-capture time失败。
- 三家单位、真实内部counter、真实专用async及实际标准Perfetto不是“未做”；GCU helper/DWARF缺口不能被写成“没有任何真实设备时间”。
- TP/UI不应无差别重复。实际UI证据包括NV原六、后续真实dependency，GCU R05020份counter + R0524份dependency，Asc unit六/mixed六及recurrence dependency；实际event/node ID、原tick/offset、截图SHA、browser/UI身份与前后bundle hashes存在。本轮核GCU20、NV六、Asc mixed六的before/after相同，读取了GCU async与Asc recurrence/softmax实际选择收据。旧softmax被撤销后不再作为当前依赖资格，但不抹掉其历史UI行为或要求其他同编码视图重跑。
- NV exclusive性能/开销认证按用户延期；本报告不重开。unknown read precision、无全部跨主体epoch、无engine busy、无source-exclusive、无完全相同issue顺序，均不能被擅自增加成全goal的新门。

## 阅读范围与限制

读根合同 §8及相关测试/运行规则、current T109与相关阶段的原始收据索引；读 design 的公开入口/语义/clock/async/§0.5–0.6及§8适配合同、testing P01–P10/§0/§3–8.9、runtime/quickstart与三家安装文档；沿公开入口、owner/transport、三个physical decoder/offline provider、clock/mechanism与共同export/store检查实际边界。读取/复核了独立registry及源码中State逻辑、原ordinary/attempt receipt hash、R06260个math结果与注册修复、1740个SQL result/row/stat、R060/61/66/69/72/73相关实证及R075最终原件。使用本席此前已实际审阅且本次未变的R058–73具体源码/原始安装、fault、TP闭环；没有以历史README中的pending或peer结论填当前结果。

未逐行重审全部产品/SDK、未再次检查每个大型原bundle全部文件、未重开独立oracle容差、未执行任何新增验证、未观看全部历史截图或重跑UI；本席不评任意机器码完整性。D01–D06与独立集合使用已有开发/受控/独立对象的结构证据，不额外发明新数学；最终case表需要将实际所覆盖结构明确连接，而不是仅依D编号或算法名断言覆盖。Git远端/设备终态依据已保存的actual收据，未新连接服务器查询；本地正式HEAD/clean另经Git读取。

可交付当前明确标注范围的partial功能及R075有限qualification工具；**按原八门的整体交付尚不成立**。真正下一步是上述四项实质缺口及必要最终审阅/交付收尾，不能缩写为“只剩NV pipeline”，也不需要把已完成的数学、1740 TP或旧UI再跑一遍。
