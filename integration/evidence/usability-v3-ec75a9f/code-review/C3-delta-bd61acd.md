# C3 finite affected-delta review — Ascend census v3

2026-10-16。审查冻结源码 `FlagPrism-ascend-census-visibility` 的完整 commit `2bc91bf36dceeb39a279c3aed4eea22fb34c6d7a`；产品 Python 对应 `e6644ff23d65ad3d6b76944678ba771847bd4aec`，native/parent patch 对应 `bd61acdadc8b9582f243ca1ee5dc1869ed73e4ad`。使用 `git show`/`git diff` 指定版本，未跟随作者之后的修改。开始时工作树 clean。

本次是原独立 C3 角色的有限 affected-delta 复核，请求配置沿用 root 已保存的额外 reviewer 工具记录，不凭模型自述认定实际版本。未读 peer 报告或私有资格数学/IR；未运行产品代码、测试、pip、服务器或设备；未改产品/论文/Study/原证据。旧报告保持原文件。本报告包含 **1 项 confirmed major、1 项 confirmed minor，均在本 freeze 保持 open**；不是新 v3 默认 writer 的硬件失败判定。

## C3-V3-MAJOR-01：新重导出的 reconstruction 仍保留已撤回的 legacy exact 声明

**位置**：`Profiler/python/flagtree_profiler/reconstruction.py:14–17,231–247`，`observations.py:165–170`，`fine_grained.py:120–163,470–489`。

**触发**：用当前导出链重新处理原有 Ascend physical-v1/v2 capture，且保留的原 observation 含 `count_exact: true`。这是真实输入：本席在公开 `artifacts/usability/run-011/public-hardware-regressions/ascend-public-evidence.tgz` 中读取 `result-budget-default/nested_memory-128/ai/reconstruction.json`，含 1 capture、8 counter rows，8 行原字段均为 true。该文件是旧证据；其原 bytes 本来就应保留，问题是新代码重新生成的派生视图。

**预期**：新的所有派生观察视图对已知 legacy transport visibility hazard 使用一致的 `count_exact:false`、`unknown_loss:true`，同时保留原 observations/raw/input/manifest。

**实际/依据**：`reconstruction.reconstruct` 通过 `observation(raw)` 复制原 row，`observation` 不撤回 legacy exact 声明；`reconstruction.write_view` 先在 243–245 行写入新的 `ai/reconstruction.json` 与 `report/observations.html`。之后 246–247 行才调用 fine-grained writer，其 `normalize` 对 deep copy 撤回 exactness。因此 fine_grained/plan/coverage 可以正确报告 unknown loss，同一次新导出的 reconstruction 仍保留 `count_exact:true`，且 reconstruction capture 的 loss 也仍是原 producer claim。新派生 JSON 与新的细粒度/coverage 状态不一致，机器消费者可得到已知不能成立的 exact 声明。

这是历史数据重导出路径的问题；没有声称新 v3 capture 会走此错误，也不要求改原 producer 证据。自动 coverage 最后拒绝 legacy capture，并不能使已经新生成的另一份派生 JSON 的 exact 声明成立。

**有限修复/验证建议**：提取幂等的 copy-retag helper，在写新的 reconstructed JSON/HTML 前统一应用，fine_grained 直接处理旧 payload 时继续自保。由 root 在服务器 Docker 将一个真实公开 v1/v2 capture 重导到新目录，检查所有新 derived views 撤回 exactness/有 unknown-loss 警告；逐字节确认原 observations/raw/input/manifest 不变。无需新 native 编译或设备 replay。

## C3-V3-MINOR-01：direct CensusReader 对明确 v3 shared raw 仍按 logical cells 检查 max_cells

**位置**：`Profiler/python/flagtree_profiler/source_census.py:114–116`；v3 物理定义在 `ascend_census.py:59–80,198–222` 与 `Profiler/docs/source_site_census.md:119–128`。

**触发**：直接 public `CensusReader` 读取由 Ascend v3 `actor_descriptor` 产生的 descriptor/full shared raw，使用紧于 raw 大小的显式 `max_cells`，但 `max_bytes` 足够。最小静态例：P=1、S=1 的 v3 allocation 为 `64 + 3*64 = 256 bytes`，物理预算为 32 cells；一个 actor descriptor 的 logical cells 只有 1。`CensusReader(raw, descriptor, max_cells=31)` 当前只比较 `1 > 31`，不拒绝本应超出 physical-cell budget 的完整 v3 allocation。

**预期**：已明确标记的 Ascend-v3 full shared raw 按 `len(raw)//8` 的完整 header/padding cell 预算检查；旧 generic/NVIDIA/GCU 的 logical-cell 定义不应被泛改。

**实际/依据**：direct reader 仍只使用 `programs * len(actors) * len(sites)`。`plan_layout` 和 native preallocation 已正确按 v3 完整物理存储检查，因此默认 producer/shared decoder 没有这里的运行预算绕过；独立 byte limit 仍存在。本项是公共 direct-reader 显式参数与新 v3 预算合同的小范围不一致，不是新默认设备分配无界。

**有限修复/验证建议**：仅当 descriptor 确定为 Ascend physical-v3/full shared raw 时增加完整 byte-count/8 的 cell-budget 检查。服务器 Docker CPU 回归覆盖等于/小于物理阈值、nonzero/zero grid，保持 legacy/NVIDIA/GCU 原语义；不需要设备执行或 schema 全面改造。

## 已成立的静态链路与迁移边界

- **默认入口未新增 per-kernel 工作**：`start(detail="auto")`/CLI 的公共选择保持不变；此次变更在通用 compiler ABI、metadata 和导出层，不需要用户指定 site、手改 LLVM 或填写隐藏参数。原 C3 replay-policy major 在 1638 已关闭；本次 `_backends.py`/`_capture.py` 相对1638未变，不重新开票。
- **v3 物理协议闭合**：frontend marker 为 `source_census_site.v3`；CompilerBindings 发布 ABI version3、`ascend_source_census_v3`；Python compiler 要求匹配 version3，真实 sites S 与 ABI `3*S` 一致。late observer 按 mode3 接受 marker3，manifest 使用 v3/header64/aligned actor stride；旧 marker2 在 mode3 下拒绝。parent AutoBlockify patch 已显式保留 v3 marker。
- **预算/存储公式**：`plan_layout` 和 native Binding 都使用 header64、`actor_stride=alignUp(S*8,64)`、`program_stride=3*actor_stride`，完整 byte_count/8 含 header/padding。native 扣回通用 allocator 原有32-byte prefix对应的4 payload cells，实际总分配与公式一致。TransferEngine 对 v3 device pointer 做64-byte alignment检查，并纳入正确 stream初始化、census export分支。padding/header reader 检查也已改成版本化布局。未发现这些默认公式之间的静态冲突；真实新包/设备收据另待复核。
- **cache upgrade**：`Profiler.__init__` 注册 `compiler_driver_cache_key`，pinned parent compiler hash 调用它；`ascend_compiler.cache_key` 包括实际 packaged plugin digest 和 codegen-affecting Python source digests（包括本次改变的 ascend_census/ascend_compiler）。新的插件、Python和marker ABI不会仅因旧site数字相同而复用旧cache。缺匹配ABI时有显式错误。没有为“源坐标ABI版本2”常量单独命名做扩大修复要求：其语义与本次physical census version不同，实际新hash输入已改变。
- **legacy reader与细粒度视图**：v1/v2保留原header/stride读取；generic reader通过record_layout或compiler-actor binding识别危险，保留raw/count/overflow但撤回exact，零cell为unknown。shared decoder把unknown loss写入summary/loss。fine_grained.normalize深拷贝并识别capture/physicalplan/compileractor，撤回row/capture loss exactness，避免改原输入。coverage以`source_census_transport_visibility_unknown`拒绝，并提示重新做v3 capture。上述效果成立，但不消除 C3-V3-MAJOR-01 的其他 derived-view 遗漏。
- **文档/安装**：automatic guide和census protocol明确新默认v3、完整预算、legacy unknown-loss/zero含义；后端README也明确v3并说明 `flagtree-source-census-v2.patch` 只是保留的recipe文件名，其内容已含v3 marker。公开 source recipe pins仍为FlagTree0364/AscendIR4c304/FLIRff91，两份完整patch各应用一次；fresh core+frontend tool+两native+独立LLVM15 observer构建入口未被Python overlay替代。parent patch变化时文档要求新workdir，不能拿旧patched snapshot无条件resume。schema guide现有census字段通过protocol链接定义扩展语义，未发现必须整体升JSON envelope版本的破坏性变更。
- **原静态HTML的边界**：文档明确已生成的历史报告不会自行改文字，需用当前reader生成新视图。这个边界合理；本项major要求的是新派生视图的一致性，不是重写原历史证据。

## 实际读取的公开证据

1. `ascend-census-visibility/sidecar-evidence.tgz`、`root-sidecar-paired-audit.json`、归档 `sidecar/paired-audit.json`。本席用标准库直接按原physical plan读取bytes，没有调用产品decoder：相同采集的 aligned48/48 cell为 `(1,1)`，compact只有28个 `(1,1)`、20个 `(0,0)`；aligned SHA `1ba1cc32…1f5201`、compact SHA `d7fb7bfc…d822a` 与公开audit相同，archive SHA也匹配 `50233478…58329`。这是真实compact visibility丢失依据；sidecar是diagnostic logger，会改变执行，不能拿它或state=1证明scheduler/replay结论。
2. 已存 `transport-legacy-hazard-cpu.log` 为116 passed，`report-final-cpu.log` 为38 passed，marker receipt为mode3拒marker2/接受marker3；实际读对应新增transport/source/fine_grained测试源码。`legacy-hazard-cpu-audit.json` 保留真实v1/v2原capture SHA和unknown-loss/exact撤回结果；`reexport-legacy-cpu.json` 保留真实旧reconstruction的8row/1capture、input不变、fine_grained exact全部false结果。这证明现有fine_grained修复，不证明同次其他新derived JSON也一致。
3. 本席未重新执行这些测试，也未把仅有口述的189 LLVM address cases当作本席已核收据。新native/core/plugin/independent wheel+venv和最终hardware receipts尚未由本席打开核对；即使root随后报告构建pass，本报告也先保留实际收据待后续有限delta，不借旧1638包当v3安装证明。

## 阅读范围与本轮终态

实际查看2bc/e664/bd61对应的：source_census、ascend_census、fine_grained、profile raw encoding、ascend_compiler/cache callback；Debugger compiler/API和Bindings、CompilerBindings、AscendProgramAnchor、TransferEngine、Decoder的受影响段；late observer/AscendSourceCensus的版本/布局/manifest关键段；parent patch的marker/cache入口；现有reconstruction与observation导出链；相关三组CPU测试、guide/protocol/schema/backend recipe文档及上述公开archive/日志。没有逐行重审不变native全项目、其他后端机制、peer报告或private资格IR。

本轮先封报告并释放review slot：两项具体 finding open，后续只需新Python freeze及真实公开旧bundle重导/reader-budget回归收据的有限复核，不要求为纯Python处置再重编native。v3新安装/硬件收据后续单列。原Ascend eligible真实state failure仍未解释；不能因当前工程修复、sidecar对照或未复现controls改成整体资格通过。

## 有限复核补充：65c99ab 源码和真实离线重导出

2026-10-16，复核完整 commit `65c99ab6639e2df76503d6758490ffe9877bb3b3`（读取时 HEAD 相同、clean）。相对初查2bc只有四个Python/测试文件改变；native和parent patch相对bd61没有变化。只看本席两票相关差异和公开离线收据，未运行产品/测试/设备，也未修改产品。

**更新状态：C3-V3-MAJOR-01 在65的源码和实际CPU离线重导出层关闭；C3-V3-MINOR-01 的主要路径已修，但 `compiler_actor.layout` 单独给出版本这一小范围识别尾项仍 open。最终65 Python wheel/新venv交付证据 pending，与源码/CPU关闭分开。**

### Major：统一派生标记在序列化前执行，实际新视图一致

`source_census.py:41–83` 将copy/retag逻辑提成 `derive_transport_visibility`：深拷贝输入；按真实capture ID和已有compiler-layout证据撤回legacy counter exactness；增加capture/summary/loss unknown-loss，不改无关capture行。`reconstruction.py:239–255` 现在先调用helper，再compact、写新JSON和render HTML；`fine_grained.normalize` 使用同一helper，直接处理旧payload仍保护。新增幂等和cross-capture测试源码确认不改原输入、重复调用不继续改变结果、不借另一capture撤回未关联行。观察页新增明确的历史visibility-loss警告。

实际打开 `artifacts/usability/run-011/ascend-census-visibility/c3-offline-evidence.tgz`，独立重算 SHA 为 `9720a10a13406bd776350df273de6e74c576c2f2c9bef957ade0c4df76b9c287`。归档的 `full-legacy-reexport-cpu.json` 记录真实入口 `_capture.export_capture`、新目录、原input files unchanged以及预期的legacy incomplete异常；我没有把异常当作成功完整采集。

本席进一步读取新完整产物，并按原observations解析digest-checked refs（未调用产品reader）：

- 新 `ai/reconstruction.json` 与 `ai/fine_grained.json` 各保留8条counter、8条原操作信息；全部 `count_exact:false`、`unknown_loss:true`。
- 两个视图中真实capture loss均为 `exact:false`、`overflow_cells:0`、`transport_visibility:legacy_ascend_cache_line_hazard`、`unknown_loss:true`，不再以无overflow冒充无transport loss。
- `report/observations.html` 确有 “Historical Ascend visibility loss”、counts inexact 和 zero不能证明non-execution的说明。
- `ai/selection_status.json` 为 `incomplete`，reason是 `source_census_transport_visibility_unknown`。新报告保留，未产生完成manifest。
- 将新目录保留的9份原 `raw/native/capture.*` 与旧公开 `ascend-public-evidence.tgz` 中对应源bundle比较，9份逐字节一致；旧source manifest仍在原归档。原输入全文件未变另有实际重导出receipt记录，本席没有声称独立取得了服务器全部before/after文件。

同时实际读到 `c3-final-cpu.log` 的93 passed和 `c3-reader-cpu.log` 的118 passed；前者覆盖source/report/reconstruction相关集合，含幂等与cross-capture源码断言。结合真实完整导出路径和产物内容，原major的派生状态冲突已有具体处置与回归，源码/CPU层关闭。不要求为这次纯Python修复重编native。

### Minor：完整物理计数检查已加，保留一处metadata识别尾项

65版 `source_census.py:159–167` 对识别为v3的full shared raw用 `ceil(len(raw)/8)` 检查max_cells，之后仍保留原logical-cell检查；没有泛改NV/GCU/legacy定义。新增测试对top-level `record_layout` 和 `compiler_actor.runtime_actor_binding.layout` 两个placement覆盖超限拒绝、32cell阈值接受、独立byte limit拒绝。这解决初查主例。

但新 `layouts` 列表只取上述两个位置，未取 `actors[].compiler_actor.layout`；同文件 `legacy_ascend_visibility_hazard:29–38` 的既有识别合同明确还接受该同级字段。对于只在这个位置写 `ascend_source_census_v3` 的descriptor，65仍落回logical cells，原256byte/32cell例可接受低于32的max_cells。因此不把本票完整关闭。只需有限补上这一个metadata位置，并将既有direct-reader测试扩成三个placement；不新增native/设备要求，也不扩大预算schema或并发验证范围。

### 安装/资格边界

root通知e664版本三包/native installed检查和短公开硬件已有终态，但本补充未打开其新收据，且它们不是65最终Python安装证明。65源码/真实离线产物关闭major，不等于65已装成新wheel；后续只核最终Python包/source-stage-ZIP-installed映射、上述minor尾项及对应实际CPU结果即可。原Ascend eligible真实state failure继续保持未解释，不因本轮修复、离线重导出或额外controls未复现而关闭。初查finding和版本记录保留，本补充先结束，不等待下一小commit占用review slot。

## 有限尾项复核：ec75a9f 关闭 direct-reader metadata 识别遗漏

2026-10-16，仅复核完整 commit `ec75a9f0592c76f22d64eff443034ab89442b477`（读取时 HEAD 相同、clean）相对65的两个文件差异：`Profiler/python/flagtree_profiler/source_census.py` 和 `Profiler/test/test_source_census.py`。没有 native、parent patch 或其他产品文件变化。本补充不重复65的major处置或已核离线归档。

**C3-V3-MINOR-01 的最后识别尾项在 ec75 源码层关闭。** `source_census.py:29–38` 新共用 `_transport_layouts` 收集 top-level `record_layout`、`actors[].compiler_actor.layout` 和 `actors[].compiler_actor.runtime_actor_binding.layout` 三个既有placement；legacy识别复用同一helper。direct-reader 在 `source_census.py:165–169` 使用该完整列表识别v3，并按 `ceil(len(raw)/8)` 检查完整物理cell预算，因此原 standalone `compiler_actor.layout` 的256byte/32cell案例不能再借logical-cell数量绕过显式max_cells。NV/GCU/legacy的logical预算语义未被扩大改变。

`test_source_census.py:375–398` 将既有完整物理预算测试参数化为全部三个placement：256byte raw在max_cells=1时拒绝、max_cells=32时接受，且max_bytes=255仍拒绝。实际读取公开 `placement-reader-cpu.log`，记录49 passed；读取 `placement-format-result.stdout.json`，记录 `ast_unchanged:true`、`ruff_exit:0`。本席独立从exact Git对象计算两个改变文件的SHA256，均与该format receipt文件索引完全匹配（source `c557c2c0…80e800`，test `5f3c8068…edd57e`）。未本机运行测试或产品。

状态合并：原 C3-V3-MAJOR-01 在65的源码/实际CPU离线导出层关闭结论保持；C3-V3-MINOR-01 现在也在源码和已存定向CPU记录层关闭。本席两项代码缺陷无剩余open尾项。**ec75最终Python wheel及三后端source-stage-ZIP-installed/新venv安装映射仍 pending**，不借e664安装或不变native收据替代最终Python版本交付证明。原Ascend真实state failure仍未解释，本代码关闭不等于整体资格验收通过。此次有限复核结束，后续仅需最终安装收据的有限delta。

## 最终安装收据补充：ec75a9f 三后端交付层关闭

2026-10-16，仅复核 `artifacts/usability/run-013/ascend-v3-build/final-ec75a9f/` 的REPORT、summary和三份package-evidence归档，并通过原e664 package归档核对不变native桥。产品源码仍以完整 Git 对象 `ec75a9f0592c76f22d64eff443034ab89442b477` 为准；native输入为 `bd61acdadc8b9582f243ca1ee5dc1869ed73e4ad`。本席未运行产品、pytest、pip或设备任务，没有重审既已关闭的源码/离线derived修复。

**上一补充所列 ec75 最终安装 pending 在此次收据复核后关闭。C3两项v3代码票的最终Python包交付已有匹配证据，未发现新的具体交付缺陷。**

| 后端 | 新venv内CPU终端结果 | 官方wheel SHA256（实际收据记录） |
|---|---|---|
| Ascend | 320 passed, 3 skipped；exit 0 | `821b929b9582080b2f2a6996be25ccd7c41a6443dfcd9da39129e10a554d7206` |
| NVIDIA | 314 passed, 3 skipped；exit 0 | `48fd503f5d78dbd83ce8e1b43a8e26e18e172ffde87c1f9282c1217a9cc3c0bf` |
| GCU | 314 passed, 3 skipped；exit 0 | `2dad4c6937a6120de3011d0e249398ad6bbca359bfe3b8ac1d004b58b8f9885b` |

本席独立核对结果如下：

- 三个最终归档的实际完整SHA/长度均匹配summary；逐个重算全部34/33/33个被索引成员的实际长度和SHA，无错误、无未索引文件（索引自身除外）。实际归档SHA分别为Ascend `944a9e690918c55b33c125ee8088e17c984f35a8b0297ff33f22e74325191bf9`、NVIDIA `f7ff3f9d36d38a3dd76f5bbb774fb86d5c1bca606992a3ab3bb9e42b70b791eb`、GCU `79a58a5111fed05685126f096afc339aa6c983c358e471900e2ed9454aa9de63`。
- 每份968项source index的path/Git blob集合与exact ec75 Git tree完全一致；68份component Python源逐份从exact Git对象重算SHA，均匹配package-source及package-file索引。因此本次实际包装的source_census、reconstruction、fine_grained均覆盖最终consumer修复版本，而非只复用旧e664 Python。
- 已读归档内实际执行的audit脚本：逐文件断言source/stage/wheel ZIP/installed字节一致，要求所有68份component Python都在wheel内；native模块和triton导入均要求解析到新venv，且真实compiler binding ABI为3。三个实际audit-result的commit、解释器、6项import路径、wheel hash、文件计数及CPU exit均与summary一致。小归档没有内嵌整份wheel，本席独立重算的是归档/source字节，并实际复核上述安装执行脚本、索引和终端结果，没有将它表述为本地重新安装或读取全部远端wheel文件。
- 每份281项native/CMake/parent-patch bridge的final source SHA与exact ec75 Git对象匹配；其Git blob与exact bd61一致。107/216/63个native package成员的SHA在最终package index、e664→ec75桥和原e664归档索引间逐项相等；原e664归档完整SHA、原native-result/native-commands实际成员SHA亦与最终引用一致。此处成立的是沿用原真实native构建的字节桥，不是ec75再次执行C++编译、依赖图审计或硬件验证。
- 三份commands保留assembly/create-venv/install/audit四步的argv、PID、时间及exit 0，controller exit也为0。安装与audit实际使用新venv的`python -I`；Ascend/GCU借`--system-site-packages`复用既有Torch/SDK，NVIDIA借已记录的依赖symlink复用前置包；所有被审计component/native imports仍位于新venv。这里的干净安装证据覆盖新wheel自身，不能扩写成所有第三方依赖均从零构建。
- 安装后测试副本Ascend9份、NV/GCU各8份，与exact ec75测试源码逐字节比较，仅有audit脚本明确列出的安装目录import-path替换；断言没有更改。三个skip可由已读源码明确定位为`test_untimed_and_unknown_browser`及`test_evidence_browser_provenance[kernel=False/True]`，都由`FLAGPRISM_TEST_BROWSER=1`显式opt-in，没有把关键consumer/native用例写成skip。Ascend还执行了真实frontend ABI3测试；audit在CPU执行前后断言NPU未初始化。
- 额外真实HOST native测试各14项；实际outcome为Ascend14次明确64-byte alignment拒绝、NV11次拒绝加3次对齐完整分配、GCU13次拒绝加1次对齐完整分配。拒绝后均有普通HOST事务成功恢复；测试源码对允许的拒绝字符串、完整物理bytes/全零header-padding及空decode均有断言。这些是HOST admission收据，不替代设备正例。

最终范围：ec75源码、定向CPU/真实legacy离线导出以及三后端最终wheel安装交付证据已闭合。本轮没有新增设备运行，也没有以纯Python刷新冒充新native构建；未重新打开不变设备writer验证。独立v3完整数学资格cohort不属于本席安装审查，原Ascend真实state failure的未解释历史保持。上述关闭不表示整体资格验收通过。有限复核结束。
