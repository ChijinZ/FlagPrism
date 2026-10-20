# R096 GCU current96 required source / loop 的有限合同与 join 审阅

**结论：原冻结没有一份预先枚举具体 origin/site/loop ID 的数组；冻结的是逐 case 的结构义务。** 应从这些义务和原 producer/source census 派生一个与 checker 成败无关的 required 集合，再连接实际规则和本次 raw。不能把 R096 的1013个 local-region 成功当成 current96 通过；也不能反过来要求所有 manifest site、所有 compiler 内部小循环或所有 source 成员逐一获得资格。

请求配置沿用独立 R3 GPT‑6.1‑Sol / xhigh；实际 resolved model/effort unknown。观察HEAD为 `f46cb0cd47bcd733606c96d5889fd4143b899c13`，另有未提交 `Debugger/test/gcu_llvm_regions.py`，本席不修改/执行它。本次仅Git、文本、JSON/tar/哈希等stdlib读取；未import产品、执行测试/SDK/设备，未读peer报告。不重开State、预算、SQL/UI、pipeline或一般native ISA门，不为Asc或whole签字。

## 1. 真正的冻结分母与来源

原goal §5要求 profile 前冻结 source/input/config/预期结构/计时语义；testing §3:91–96 与 §4:100–112 逐 eligible 组合要求至少两个不同源码区域真实区间、多个正duration，以及适用循环的真实body occurrence与runtime输入关系。design §0.6要求本次binary/site/路径绑定和结构规则，明确不要求任意机器码证明器。

直接读到的注册原件为：

* `.timeline-qualification-r052-private/registry.json` 与 `prepared-v1/registry.json` 字节相同，SHA `62d7e63d0c7a66de21fdd7862a9c852959ca1a87a8991c9489877b8d6fa87ee3`。`:20` 的 `structure.all` 是至少两个 distinct automatically mapped internal source regions、complete intervals、多正duration、default selected observers无loss；`:21` 对elementwise另外登记 **device-loaded K、body≥3、每shape/config的K3/K7同binary**；`:22–23` 分别登记实际归约/依赖后算术及matrix K tiles/收缩后store等结构。
* `.timeline-qualification-r052-private/supplement-v1/registry.json` SHA `1e6a4da3b7b3e4900abb29e03a34bec5c17b12ba5f4e01341ae968038de33f3a`，`:12` 登记q07/q08的依赖计算/归约、至少三逻辑K tiles，以及 **ordinary实际GCU IR必须保留transpose_start和broadcast_start**。这不是“每个这样的primitive必须单独计时”的额外声明，也没有登记所有constexpr循环都须同binary改K。
* 原六 profile调度器 `.timeline-qualification-r052-private/dispatch/profile_gcu_driver.py` 由原eligible/source/product freeze登记72个cold/warm调用；补二 `supplement-profile-v1/driver.py` 登记24；`gcu-affected-r055-v1/driver.py` 明确替代原q05的12个和q07-s1-c1-cold一个，不产生新的数学分母。

当前身份入口可直接复用 **已闭State证据的索引字段**，不能复用其State通过票代替边界：candidate `integration/evidence/timeline-gcu-State-profile-r088/current96-State-result.json` 的 `qualification_rows`，SHA `2f17056b10a76e5f4608ebb8bb4c6dcf0fc015880c55254017d14ae81d0c406c`；与 root `run-088/preflight/gcu-receipts-v2/runs/source-partition-v2/output/actual-partition/rows.json`（SHA `43c53a4570fcfac12fd143cc68c7998a6e84c5043e125c1dea5592aa43cbb77f`）按 **case+capture SHA** 恰连96。q01–q08各12；来源是60原六+23原补二+13affected。

这96次对应 **32个binary SHA、33个实际profile LLIR输入SHA**。R096的33对象 `(binary_sha256, llvm_sha256)` 每个都出现在current96中，不能把第33份当历史多余项删除。更正本席R091将LLVM/binary一并写32的不精确表述：最终执行对象与实际输入文本是不同去重键。相同binary也不能跳过第33份输入的绑定。

最低区域数量是**每case至少2个不同源区域的实际见证**，不是192个全局唯一origin，也不是1013个required sites。q01/q02对应8个shape/config结构、24次profile的原runtime-body义务；q03/q04没有注册device-loaded runtime-K义务。q05/q06/q07/q08的Ktile循环若实际保留，须核其声明的执行/端点关系；若unroll/消除则按实际变换记录，不能制造循环。它们的编译期K/BK不新增为q01/q02的same-binary runtime-K门。

## 2. 已定位的关键原件：必须连真实loop，不能用容易通过的site补空

本席直接读取 `.timeline-qualification-r052-private/profile-stage-v1/profile-first-v1-complete.tgz` 中原capture/events。此本地archive实际只含21份capture（q01十二、q02九），不是72/96完整原件，不能据它算全覆盖。

| 实际原样本 | 真正重复的backend site与原来源 | 原raw证据例 | producer/source census连接 |
|---|---|---|---|
| q01-s0-c0-cold，capture `invocation-00fcee482d8c4b7cb9663f5f53e6d7f9.json`，SHA `4c42d244…2135d` | site24，`gcu.border`，`loc(unknown)`；两个selected observer各3次 | raw SHA `d4126e6e…80550`；首observer一次entry/exit offsets **816/824**，ticks34701227951300/34701227951825，sequence12/13 | `debug_execution_source_tracked_table` 的body opId14–19，controlId1、parentOpId20、repeated=true；原 `debug_execution_input_ir` 第191行for内部，第193–202行unknown融合border包围实际算术，内部保留opId15/18及13/14行来源 |
| q02-s0-c0-cold，capture `invocation-240531630b3e40e99d04e4a63c46cc9c.json` | site26，`gcu.border`，`loc(unknown)`；两个selected observer各3次 | 一次entry/exit offsets **1072/1080**，ticks34864309465129/34864309465730，sequence16/17 | source census body opId14–25及capture35，controlId1、parentOpId26；原input第205行for、第209–222行融合border，opId20/24/25等及原31/32行来源仍在 |

q01 input SHA `163acb5f190e1265dce0f200a0a87ad0c408a4dd785f6c11870b747f07e4a31d`；q02 input SHA `0ed05a0a15cf4f31a6e6c19512b32101fbc7306bcd9821bc71ccbf46586a7650`。原capture中同时保 `debug_execution_rewrite_receipt.argv` 的actual input/output/manifest路径及tool/source SHA。q01原server输入在 `/tmp/chijin-timeline-r052-qualification-profile-v1/runs/profile-first-v1/q01-s0-c0-cold/controlled/tmp/flagprism-gcu-execution-rucm8bux/input.mlir`；q02同根下为 `q02-s0-c0-cold/controlled/tmp/flagprism-gcu-execution-sitwu37g/input.mlir`。

**q02的site25虽然有原31:30位置且local checked，却在这个for之前（input第194–200行）。它不是实际重复的site26。** 同样，site24的初始化融合、State increment/store及其它单次DMA的成功，不能填掉runtime-body义务。raw显示3次不是机器loop资格；source census指向13/14或31/32行也不是最终边界资格。需要将二者接到同一个actual producer region及最终LLVM路径，不能直接把canonical的unknown改成凭算子名猜出的源位置。

原K3/K7同binary材料已登记：`dispatch/enflame-ordinary-device-v3/baseline-freeze-v2.json` 指向 `/tmp/chijin-timeline-r052-private-device-v3/eligible-v2-binary-bound.json`；ordinary的 `baseline.json.results[].runtime_K_check` 指向各 `q01/q02-s*-c*-K7/math.json`。`matrix.py:110–120` 核compiled_hash、全部asm与actual binary，且冻结8个auxiliary通过。这是可复用的输入/binary证明，不能把ordinary K7冒称已有profile raw K7。对“次数随输入”的实际动态交叉检查应引用已有相应K变体/C1收据及其范围；current96主调度器本身只传K3，不应悄悄把它改称96份都测过K7，也不应因此额外要求96次新数学。

## 3. required origins / loops 应如何确定

**先派生义务及候选源身份，再看规则结果。** 原注册没有具体ID数组，不能把现在写出的数组称为当初已冻结；可以由原冻结源码、source census、actual before/after及既定自动选择算法确定一个可复算的派生集合，另记派生规则版本/输入SHA。产品规则仍按结构选择；QA的case名字只用于接回原注册，不能进入产品放行分支。

1. 源身份用冻结Python文件SHA、entry/function、scope/op/statement ID、inline/control ancestry和body成员关系，保原line/column作为导航。不能以不同observer生成的canonical ID、同源load拆出的四条DMA或同一fused bracket的多个origins凑“两个区域”。fusion的M:N关系只赋一个真实duration；split也不自动成为多个不同原源区域。
2. 在原数学的数据/控制结构中确定区域见证候选与必需loop。优先包含原注册要解释的循环body/实际计算阶段，再取另一个不同原源区域；load/store或issue子区域可按其真实语义使用，并非强制每个阶段都是完整compute耗时。**不能只选与必需loop无关的两条DMA后宣布整体通过。** 另一方面，原注册没有要求每条算术、每个State操作或每个manifest site都单独有clock，勿新增此门。
3. 用确定性的producer遍历/原selection policy或固定结构优先规则生成候选与最小见证集合，输入不得包含checker的status/成功计数。冻结派生结果后再执行join；失败必须保留为该义务缺口，不临时换两个通过site。允许合同原有的真实粗区域/优化消除说明，但须证明覆盖同一义务，不能删掉loop或改变原结构。
4. runtime loops按source census的 `controlFlowAncestors.{controlId,parentOpId,regionIndex,blockIndex,repeated}` 接原 `scf.for` 及实际bound的SSA来源，再连actualLLVM header/latch/exit/paired-record路径。只把原数学控制结构纳入required loops；SDK实现的填零、copy、logger环等内部循环不自动新增为runtime门。

可用于定位的冻结源码锚点如下；**这些不是每行都要独立timer的新增清单，也不是让产品按这些行号放行**：q01 body13–14/后算术16；q02 body31–32/输出33；q03归约45–48/依赖49；q04能量61–63/输出64；q05收缩82/摘要83–85/输出88；q06收缩110/输出113；补二q07收缩22/摘要23–26/归一化27–30，q08广播差49/能量50/排列51/归约53/输出56。实际融合、消除和hoisting必须由原producer成员关系解释，不能只按字符串位置建立边。

q01/q02的最小源恢复可沿**已有**原before中成对融合border及其包围操作，取保留的 `flagtree.debug.op_id`、实际child locations和census控制身份。用已核producer遍历确定其manifest site，并由原after的实际site/clock/record常量绑定，随后继续核actual LLVM规则。需要的是此处有限、可重复的成员连接，不是给unknown任意补一个最近line，不是要求所有源成员逐条native解释。派生链接写新sidecar，原unknown来源/capture/raw不覆写。

## 4. 最小可编码 join 与复用键

| 层 | 必要字段/连接 | 现有入口 |
|---|---|---|
| 原case/eligibility | kernel、shape/config index、phase、registry/源码manifest SHA、ordinary math/target/config/input引用；affected替代记录 | 原72+24 registrations、affected13 registration；current96两份逐case索引 |
| 本次capture | file/SHA、capture/invocation/binary identity、原math SHA、raw/events file+SHA、default selected program/observer/layout | R088 final rows给96份精确server路径；capture的owner、raw_file/raw_sha256/events_file |
| 原producer core | before/after SHA、recorder identity、实际preservation/core证书及成员引用；保原source census与selection | `debug_execution_input_ir/input_sha256/output_sha256/rewrite_receipt`；R087已绑定原core/preservation材料 |
| 实际编译/SDK family | actual profile LLIR SHA、TTIR SHA、binary/ELF/function、target、实际backend compiler/SDK/library/tool hashes；所用callee/descriptor/observer规则版本 | snapshot的compiler_artifacts/executable；`debug_execution_tool_identity`，R088 actual SDK resources及原已审ABI/有限primitive closure，按真实callee和条件复用 |
| 派生required义务 | obligation_id、来自哪个注册条目、region/loop种类、原source成员/control身份、必需参与条件、候选/见证的确定性选择规则SHA；constant tile与runtime input分列 | 原registry+source census+producer core；**此层目前尚缺统一派生结果** |
| 实际规则 | rule id/version/implementation SHA、actual typed-index/manifest SHA、backend site、body/path/tuple refs、observer/guard、loop header/latch/exit/trip来源、逐条件结果/unknown原因；SDK/native事实另引用 | R096 `objects[].{binary_sha256,llvm_sha256,typed_index_sha256,manifest_sha256,regions[]}`；具体SDK/native既有事实，不由local status自升 |
| 原raw见证 | canonical site→backend_site_id；event→observer/source/record_ids；record→sequence/offset/length/tick；raw身份、完整性、正duration、实际occurrence与注册runtime值 | 原events的sites/sources/observers/records/events及raw_artifact；每capture单独核，不借其它调用补空 |

建议最终输出按case保 `required_obligations[]`、`witness_bindings[]`、`uncovered[]`，每条都有输入/规则/原raw引用。静态分析可按实际LLIR+manifest+producer成员/SDK/规则身份去重；**不同capture的raw、observer覆盖和调用身份不可用另一份cold/warm替代**。R088索引中 `source_sha256` 实际是profile LLIR文本身份、`LLVM_sha256` 是翻译后functions.ll身份，不是Python源码SHA；join应使用明确命名，避免同名字段误连。

R096 source-local checked只授该层有限事实。若结合已有SDK/最终对象/读钟与raw资格形成更强区域解释，应逐项绑定这些事实覆盖的actual family；不从State ABI或同opcode数推导全部native区域，不要求重编所有33份SDK对象，也不要求全ISA/engine busy/source-exclusive证明。

## 5. 当前真实缺口与最少下一步

已核 `run-096/preflight/installed-receipts-v1/installed-index-v1.json` 40项size/SHA一致；actual结果SHA `c18ab8855121a87e054d9fe21c4a5f76f77d7957bd0f96e0a034896c8002042e` 确为33对象、1013 local checked、每对象至少19。它的q01/q02 checked rows全部 `no_enclosing_runtime_loop`；真正body sites仍unverified。这个计数不关闭原Kbody门。

`run-096/preflight/actual-loop-trip-result-v1.json` 的object16/q05和24/q07实例实际entry trip为constant3。它们可另按**constant-bound executed iteration**的有限scope接端点/实际occurrence；不能称为q01/q02的runtime-input证明。q05–q08所需的是原实际Ktile结构/所声明循环路径，不新增所有constant/SDK loops通用证明。

最少顺序为：**先派生并冻结上述required join → 补q01/q02 unknown融合body的真实source/core关系及其actual runtime-loop规则 → 对仍需的Ktile见证接适用constant-trip规则 → 逐case接原raw与已有SDK/native事实，列准确未覆盖项。** 如果现有source、typed object与raw足够，就只做CPU只读派生/规则核查；缺某份原件先按R088 rows的精确capture/rewrite路径读取，不默认重采数学或重编SDK。

本席未逐一取得余下75份本地full capture/raw，也未执行这个尚未生成的coverage join；因此不预判current96 source/loop通过。**本次没有确认新的产品错误；必要verification gap是这份结构义务→source/core/site→actual rule→本次raw的连接，以及上述具体未支持body/loop，非“1013不够多”。** Asc规则仍由后续实现/实际证据处理；其State等已闭门不受本报告影响。
