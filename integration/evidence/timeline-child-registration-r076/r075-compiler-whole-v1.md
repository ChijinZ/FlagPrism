# R075 整体 compiler 复核

结论：**目前不支持按原完整 timeline 合同宣布完成。** 三后端公开自动采集链、实际计时记录、来源留存、公共导出、缓存/ABI 和有限扩展边界已有实质实现及真实证据；不是只有 adapter 类或正 duration。本轮没有发现新的 confirmed blocker / major / minor。真正未闭的是：**GCU、Ascend 的自动最终区域/循环边界，以及三后端 ordinary/sparse/default 的关键功能阶段关系**。NVIDIA 的这些边界与依赖证据已大幅推进，不能继续套用 R057 的旧缺口描述；也不能据此替其它两后端放行。

这是原最终 R1 compiler 席的整体复核和剩余清单，不是新一轮数学、SDK、设备、TP/UI 验收。请求配置沿用 GPT-6.1-Sol / xhigh；实际 resolved 型号/深度工具未暴露，记为未知。未读 peer 报告，不以 root 或其它席的预期票判断。

## 版本、合同与审阅范围

以原 `timeline_goal_prompt.md`、当前 `timeline_design.md` §0.5–0.6 / §8.12–8.14 和 `timeline_testing.md` §3–§5 / §8.1–8.9 为判据；复读公开 quickstart、runtime 的三后端、恢复和 native diagnostics 相关章节。原 R057 全链走查及之后本人实际做过的有限 source/receipt 复核沿用，不无变化重做历史全审。

runtime freeze 为 `efb23636c2aa3a6e8866875133765c4de3a00f91`；本任务给定 canonical `ea27308`。本地最后读取 candidate HEAD 为 `1dd2baa`，新增 R075 qualification 工具，不是产品 runtime 变化。Git 对比确认 R069 后 GCU 相关 recorder/bridge/native-map/transport 源码至 efb2363 未变，R060 后 Ascend recorder/transport/decoder 和共用 owner/guard 源码亦未被后续 NVIDIA 改动替换。各后端安装凭据按实际使用部件复用，不声称一份 NVIDIA wheel 安装了另两家 SDK。

本轮重新读取了 CLI/API 分支、compiler hooks、目标/工具指纹、三种真实 transport 输入、owner admission/留存接口、原生插桩和边界规则、公共 view/exporter/offline 分工，重点逐行核当前 GCU/Ascend 边界实现及 NVIDIA 新规则。读取 R058–R075 中有关修复、参与数、source/native、独立 affected repair、SQL 索引及三方 pipeline 的真实 JSON/源码；R075 归档逐 bytes 核六 source，完整读取最终 matrix/input/bounded-register 结果。没有读取 SDK 私有源码或完整巨型 native dump，也没有重新散列所有历史大归档或逐图复看 UI。仅本地 stdlib/Git/文本读取；未运行产品 import、测试/模拟、编译、SDK、设备、数学、TP/UI 或服务器任务。只写本报告与本人有限报告。

原合同要求的是有实际边界依据的 observer elapsed / issue / wait 与动态关系，**不是 source-exclusive latency、所有 ISA、完全相同 issue 次序或 engine busy**。不能因这些未要求的强性质未知而否定已证事实；也不能只用来源导航/同指令数放行原要求的区域与阶段关系。

## 已直接成立的能力

| 后端 | 实际自动编译/记录接入 | 已核时间/来源/机制范围 | 当前边界限制 |
| --- | --- | --- | --- |
| NVIDIA SM120 | `profile.start` → `LateTimelineHook` → normal packaged `late-timeline`，普通 LLVM O3 后插桩；hidden scratch 和首次设备副作用前 admission；full CTA / sampled 布局分别验证 | actual CUBIN/PTX/两种 disassembly、独立原操作 marker、getter→store/record/address/payload/header provenance、runtime group/shared-byte reuse；真实 counter/shared/dependency 导出 | 有限 scalar/global issue、FP16 matrix issue 和 native loop 规则已自动化；未知形态仍 partial，不能将首批支持规则外推全部资格结构 |
| GCU300 | `debugger.compiler` → `gcu_timeline.prepare_ttir/rewrite_execution_ir` → packaged native tool → 实际 SDK lowering；work-item 0 local ring，原 return 处 private-tag DMA 发布 | 实际 queue/executable descriptor；physical identity、捕获窗口内 empirical counter-ns/不确定度；实际 translated device addresses/tag index/generation，same-observer submit→wait-return；最终 ELF DI 位置自动留存 | DI rows 是位置服务；caller/reader/raw valueflow 及最终区域/循环控制边界未因此成立 |
| Ascend 910B/c220 | source-coordinate carrier → `compiler.driver.v1` → LLVM15 late observer → 实际 AIC/AIV SDK object/loaded ELF；paired 64B records/guard、原 stream 完成后读回 | actual SYS_CNT/20ns 有界单位，原始 ticks/marker/actor/binary/call 来源；已支持 flag tuple 的 exact final word + 动态 generation；设备参与数协议 | source fragment 仍明确 boundary unverified；SDK decoding/prefix 只补实际覆盖的位置/局部顺序，没有完整默认 source/loop 规则 |

公开 `--detail timeline` / `detail='timeline'` 不要求 kernel scope、site、scratch 或额外运行。`profile.py:1560–1607,1784–1800` 确实选择三条不同接入；CLI `cann` 与 compiler `ascend` 没有混同。默认 8 个逻辑站点与显式 1 不同，mandatory 原生机制站点不靠这个逻辑 budget 删除。产品按 IR/原语/来源和实际 target 条件选择结构，所读路径没有按资格算子名/shape/hash 放行。qualification runner 的登记案例标签不是产品分发规则。

NVIDIA R061 的 compute fence 修复保留原内部 contraction，实际 release C1 的 FFMA 已位于 reader 之间；R071 原生 matrix group、R072 独立原操作标识、R073 native-loop 自动报告均有 normal 安装/真实原件回归。R073 conditional EXIT 的确认缺陷已修复，35 CPU normal/-O、六 retained captures 及 public reexport/新 dependency TP 闭环，不把旧 d3d freeze 当修复版。

R075 另补本案例普通四 HMMA 的 A4/B2 来源与 default/真 sparse K3/K7 的 **960** word→raw-generation 关联；切当前 natural-loop 返回边并拒其它 cycle，防前轮 load 冒充本轮。profile load 整 footprint 只有一个 producer 才赋各 word 同代际，没有猜 B2 字节置换。**26/26** 显式 register cones 排除本函数 HMMA/clock result 路径；三个 default 控制锥的入口 `P3..P6` 仍 unknown。后者不推翻这个更窄否定性质，也没有被冒充输入定义完整/through-memory/完整 pipeline 证明。它是 QA 工具，非新公共资格字段，详见同目录 `compiler-finite.md`。

## 已处置的旧确认问题和旧证据缺口

以下不能继续作为当前 pending，也不把历史失败抹去：

- **Ascend cache M1/M2 与 bare-opt resolver**：两条真实 JIT 入口均在 lookup 前绑定实际 plugin/tool/SDK/link-resource 身份；`ascend_compiler.py:474–558` 使用 subprocess 一致的 executable resolver 和真实 file identity。parent patch 要求 SDK compiler 是绝对 executable，不能把不适用的 bare SDK path 当当前遗漏。原 CPU real-JIT normal/-O、pinned parent patch 和 normal install/device resume 已有限复核闭合。
- **GCU guard**：`TransferEngine.cpp:1156–1188` 实际分配两侧各64B并保原 hidden pointer；`timeline_enflame.py:93–97,168–171` 版本拒绝/完整 physical readback/guard 检查真实接入。R058 actual SDK prefix corruption 检测、raw 保存无派生 trace、随后新 session 成功；原 composite attempt 1 的恢复子用例亦保留。原 G4 不再开放。
- **Ascend reserved slots**：R060 不是从空槽推断 actor 不存在；实际 GET.SUBBLOCKDIM 发布 flags8–9、AIC=1，只有 count1 且整个排除段为零才排 slot2，旧日志继续 unknown。实际 C1/C2 完整2/6 observers 和 normal plugin/wheel/设备结果成立。R062 原受影响 q01–q04 48 calls + q08 12 calls 全60按原数学/input/config/default 范围修复通过，120 counter +48 dependency 共168新 trace 真 TP/完整stats亦过。原历史96中的 partial bytes没有改写，但当前默认 completeness 不能再因这些旧槽一概判失败。
- **完整 retained SQL 索引**：R059 为1,740 registered traces建立 SHA-linked actual TP 结果（1,735 fresh、5 exact-input reuse），后续 R060/R062/R069/R072/R073 改变的 trace 另有定向实际 TP。R059 的 `trace-index.json.gz` / summary 和 R062 的168逐trace审计填补原 G5 的索引缺口。TP 不授 source boundary 或 ordinary pipeline；本席未据此重新给 UI 完成票。
- **GCU 无可用完整 disassembly 出口**：R065 既有 LLVM11 工具对原 ELF 成功，无旧 LLVM18 fallback/error；R066 补有限 timer/identity helper 实码检查。这一具体工具阻碍已解除，不能继续要求用户先提供不存在的替换工具。它不自动关闭下述边界缺口。

计数生命周期 R070 的 reset-after-record/count update 缺陷同样已通过正确 acyclic conditional-reset fixture、normal install/actual原件回归关闭。R061 full-CTA v4 预算保8MiB且算入128B guard，两个实际调用合计8,380,672B；sampled/explicit 不借此改分母或放宽上限。

## Confirmed blocker / major / minor

**当前无新确认项。** 这不表示完整目标已通过。下面是原合同仍需闭合的 verification gaps；它们主要是实现/证据能力未完成，不能伪称已有错误 native 调度的实证，也不能靠多数票豁免。

## V1：GCU、Ascend 的自动最终 source/loop 边界仍未闭合

**位置与触发：** GCU `GcuTimeline.cpp:449–476` 在 actual SDK execution operation / border 两侧放 clock，`GcuNativeLocations.cpp:110–134` 只读 ELF DWARF rows；Ascend `AscendLateObserver.cpp:666–724` 为 frontend carrier 后原 LLVM block fragment 放端点且保 `boundary_status='unverified'`，`AscendTimeline.h:43–49` 是真实 clock getter，不是区域次序证明。默认 C1 依赖循环、普通 load/compute/store 及已登记 qualifier 结构触发原 design §0.6 / testing P03，而不仅是高级模式需求。

**实际证据及边界：** GCU R068 lexical fix 已在新真实 loaded ELF 得到13/13 sites、48/62 positive marker rows，R069 normal compiler hook 自动提取；这关闭“synthetic file丢失”，没有说明每个 row 精确指向哪个 caller/getter/record value，也没有检查目标计算/访存未越过 timer。共同 end block 合并 site1/2/3 等路径是实际 LLVM 优化，某 phase 无独立 DI row不是没有时钟；不能给每个 site凭空复制PC。

Ascend R063 对未变 hardware ELF 的 retained SDK decoding，有1728 executed PCs、28/36 SYS_CNT markers匹配，8 absent 保未证；SDK child139、内部控制分支保留。site16 entry→VMULS→VADDS 的逐4B连续无 JUMP/END prefix 比 numeric containment 更强，但没有覆盖整个 entry→exit、外部入口或 runtime-loop 返回/退出。源码循环/动态3/7次数本身不证明最终 SDK 没有提升/下沉或绕过读钟。该有限补证不能当 G1 完整通过。

**后果：** 两家目前仍能交付真实、来源可导航的 observer counter brackets及已证机制关系；未满足原要求的完整自动区域/循环边界不能由“每家都有多区间/正 duration”填满。这里要求实际声明的 observer elapsed 区域，不要求 exclusive cost、全部协作主体或 engine completion。

**最少下一步：** 用已保留真实 C1 load→依赖 compute/runtime-loop→store 和原 wait 对象，为实际出现的有限通用模式补 binary/function/section、caller/getter、区域指令/基本块、header/latch/exit及两端路径绑定；支持的直线/loop形态自动检查，不认识的形态保具体 unknown。GCU 可复用现有 LLVM11 解码、actual DI、共享 end-block 的 site/begin 传值，不能把缺行当缺记录；Ascend 可复用现有 marker/decoding/prefix，补本区域结束与实际 loop 路径。只需对应的语义自洽负例（关键操作越界、出口绕过/提升、caller错绑），不要求通用 ISA/all-kernel 证明器或新数学矩阵。如果 SDK 仍无法给该实际模式所需出口，报告这一具体范围，而不是重复已经解除的无 disassembler 阻碍。

NVIDIA 首批规则已覆盖真实有限 scalar recurrence 和 matrix native loop，不能与两家空白等量描述；它仍需把这些规则的真实支持谓词/拒绝结果对应到已登记资格结构，不能以首批两个样本自动给所有原 source groups 放行。

## V2：ordinary/sparse/default 关键功能阶段保持仍需三方有限关系闭环

**合同和位置：** design `timeline_design.md:492`、testing §5/§8.7 要求原 submit/group/wait/consumer/reuse/允许 in-flight 关系，而非 byte-identical issue schedule；实际证据分别为 R057 GCU/Asc density summaries，以及 R073 三对象 / R074 prefixes / R075 word-generation、register-cone 结果。当前公共 docs 的谨慎措辞是对的，不是这个门已通过的证据。

**NVIDIA 已得到哪些关系：** ordinary 四 HMMA PCs2704/2736/2944/3072，body copy3056 在末条之前；default/sparse 四 HMMA 连在一起，body copy分别5200/4576在 exit reader及 reuse BAR之后。变化真实存在，但未证明新增 tensor-completion 串行边。原 ordinary 的四 LDSM2656/2672/2688/2752均在 reuse BAR2800之前；profile 对应四 load也在其 reuse BAR前。本轮 input binding又证明每条 HMMA确实使用这些 load的相应word；不能再仅说“同数、不知道输入”。

原 ordinary PTX 实际保留 prologue 两次copy/commit、body wait1 / publication BAR / 四shared loads / 四MMA / reuse BAR / bodycopy/commit，tail wait0；profile raw具有具体 current sync/async producers、原publication和reuse cut。R074 default/sparse K3各4/6、K7各12/14 prefix有非空2048B future group尚未被wait要求完成，wait1→wait0同opcounts反例全部失去 witness。R075使这些profile shared consumers能关联到actual MMA A/B inputs；26/26必要显式register cones亦排除本函数HMMA/clock结果路径。入口值仍未知不等于这一否定性质未查。

**尚未核完的最小普通事实：** 仍需从同一 ordinary 对象补明确的 shared-slot index/loop推进与 bodycopy future-generation角色，逐项对应 profile已得的 current/future tile、commit/wait覆盖和原publication/reuse cut；例如 excerpt中的 `%r133/%r134` 与当前/下轮slot，不能只靠两个立即数1/0或PC最近认角色。将该表与现有R075输入绑定、R074非空future witness连起来，即可判断原静态机会；没有要求那条bodycopy仍在最后HMMA前。recorder真实独立scratch/global与原shared tile的空间/extent隔离可复用现有来源/分配证据，不需要另造通用alias分析。对于本案例，**没有证据表明必须先改runtime才能开展这份核验**，也不能把未解完整hidden scoreboard当新门。

**GCU、Ascend：** R057 两variant/density的真实数学、原primitive ordered projection和内部时间结果有用，但SDK输入的名称投影不能单独证明最终 wait覆盖、flag/tag参与条件、跨轮buffer复用和原合法异步机会都保留。GCU已有实际tag地址/index/两代以上复用和wait-return，Ascend已有当前provider下recurrence同flag generations0/1；应在各自同一已保留 ordinary/default/explicit sparse 对象上核这些关键角色与原cut，补最终支持模式所需的调用/路径证据。无需按每条ISA逐一证明，也不要求测出硬件重叠比例。

**明确的范围区分：** Ascend BK64 explicit sparse1 第二capture只有1个positive，第三call未启动，是保留的低密度结构失败；不是默认8的失败。BK32 sparse和两variant default通过的数据不能借给该失败，也不能因它而否认default能力。C2普通图不能从计数相等或无新增BAR推出保持；反过来，issue交错不同也不等于已证明合同失败。当前归类仍为可定位工程验证缺口B，不是确认新增完成串行化A。

## 独立数学分母与版本关联

实际读取了原registry/ordinary baseline index、q01–q06三类各二和两shape×两config的冻结条件，以及q07/q08 supplemental registration、实际first/repair summaries。三后端72 ordinary组合和24 runtime-K辅助均有真实基线；后续各72 profile、两新数学24 profile及失败/修复历史确实存在。没有把 prepared registry中的旧状态当今天未运行，也没有因几十个无dependency的普通数学要求每capture都有flow。

NVIDIA原12 missing-unit由原件重导补、原9 overflow及q08十二失败有定向修复；GCU primitive/体积修复及13 affected实际回归已留存；Ascend96个逻辑登记调用中受参与数影响的60已新修复，未受影响mixed记录可复用。旧部分记录/体积/稀疏失败必须继续保留。新增qualification工具和reuse diagnostics不是新的独立未见数学；已暴露的修复样本也不重新叫未见。

**剩余要求不是再造六数学或更大矩阵。** 原数学、raw/单位/身份/预算通过，不会自动把boundary未证填为合格。最少应把已登记的runtime-K、reduction、matrix实际结构与本次支持的自动最终边界/observer条件及原producer版本逐项对应：已由现有不变对象覆盖的复用，确有实质producer变化只补实际受影响范围。V1/V2没有闭合前，不能用这些正常数学/TP总数给整个原最终资格通过。本席没有重新独立认证所有历史case的每个编译/预算数字，因此不另造一个新的总通过分母。

## ABI、cache 与可扩展边界评价

这部分有实际调用链支持，当前未发现新的确认缺陷：

- NVIDIA parent optimized-LLVM callback能力、preallocation ABI2与native版本在hook验证；`LateLLVMTransform.cache_identity`绑定真实tool、site/capacity/布局策略v4，compile时再核tool未变，加载时重建ordinary LLVM与manifest。最终map/单位规则绑定actualtarget、getter和文件内容，不按NVIDIA品牌继承其它型号资格。
- GCU `gcu_timeline.tool_identity:38–63` 在lookup配置前绑定tool/bridge/backend/native及实际SDK工具/库；`prepare_ttir:66–94` 核实际gcu300及matching runtime，rewrite/DI/native stage复核frozenidentity，真实SDK验证opaque bridge输出后才codegen。正常fatbin路径自动提取ELF，旧raw/layout继续独立reader。此路径没有私有未文档化PYTHONPATH补丁。
- Ascend native参数来自实际source carrier/formal→SDK actor绑定，不让普通用户手填finalformalindex；compiler/target/plugin/opt/bisheng/resource内容进入两条JIT查询前身份，prepare重新核相等。same-path替换和bare-opt PATH变化实际CPUfixtures已通过，normal安装和start/profile/deactivate/activate binary恢复有真实收据。
- `TimelineOwnerPool.prepare:105–174` 复用的是调用身份、admission、潜在writer和资源生命周期；GCU/Asc传真实typed executable descriptor及queue，不伪造CUDAfunction/num_ctas，transport独立核layout/target。三家raw格式、clock/domain、机制mapper独立，公共 `timeline_events/views/shared/dependencies/perfetto` 不解析三家ISA补业务；offline小registry有三个真实provider及实际retained-only恢复，并非空类层次。

这种分工保留了异构ABI、AIC/AIV、GCU physical-counter和NVIDIA collective footprint，具备工程可扩展基础。新目标需沿 compiler/transport/decoder/clock/mechanism 五条真实条件判断复用、补证或替换；当前三个后端不证明第四芯片已低成本可用，也不需要因此新建插件平台或统一机器IR。V1/V2是各目标部件必须补的真实能力，不是公共schema可以掩盖的未知。

## Optional 与最少推进顺序

无新增可选重构建议。先闭现有GCU/Asc有限C1最终source/loop模式与三方关键角色表，复用已有对象/marker/raw和刚完成的NV规则；不继续只扩NV同类diagnostic而遗漏另两家必达边界。再将规则范围与原资格结构/版本关联，只有受影响处补验证；保持所有partial、first failures及explicit sparse1限制。SQL旧索引、已确认cache/guard/参与数修复不重复重跑。

本报告支持交付明确范围的阶段性工具能力；**不支持以当前材料给原完整三后端goal完成票**。没有把未知enginebusy、source-exclusive、通用ISA或相同issueorder加入门槛。剩余是否能关闭，应由上述具体有限事实决定，不能用本报告、任一reviewer或多数票替代。
