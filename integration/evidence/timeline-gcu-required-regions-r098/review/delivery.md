# R098 required derivation 有限审阅

**结论：派生流程方向正确；v1不能直接作为资格收据。** 它确实先由原源码/producer成员确定required-plan，再读checker结果，没有按成功site挑分母。v1的raw关联校验不足及额外observer/positive门，在本席读取的最新v2源码中已修；v2新增复用cache还缺实际结果文件的字节绑定。constant Ktile的适用资格仍须另按原scope处理，不能把它们改称runtime-input证明。

范围为root `run-098/preflight/derive_required_v1.py` SHA **`837e9067de1364db741fd5b2ecbe983d03254dba3477d2254789f98f3dafea7d`**，以及后续明确提供的v2 SHA **`ed280a7530a09ce055534dcdd42babe9cfd2eca06c97750278720288901edb8d`**。读到candidate HEAD `be3aec778114d866dba0db23bafeba281ee88419`；不重审其产品实现。请求沿用独立GPT‑6.1‑Sol/xhigh，实际resolved model/effort unknown。仅Git/文本/stdlib读取，未执行这两个脚本、产品/import/测试/SDK/设备，未读peer。无产品修改。

## 原义务与派生阶段

本席核input tar的原两registry与kernels字节：原六registry仍为 `62d7e63d…87ee3`、kernels为 `d2c5edd0…02b`；补二registry `1e6a4da3…33f3a`、kernels `4d3109e2…324f`。rows是96条唯一 `(case,captureSHA)`，与R088 current96集合精确相等，objects是33份；没有删困难case或增加数学分母。

v1:58–115在import checker之前完成AST阶段→原census→original producer membership/site匹配，排除synthetic captures、保source成员和enclosing controls、确定性rank/site排序、chosen不重复；落盘并取plan SHA。末尾重核plan字节。这满足R096所要求的“先定义义务及见证，再看规则结果”。原registration没有具体site数组，本轮输出应称**从冻结结构派生的见证计划**，不能改写成原资格前曾冻结这些具体site。

v1读出的owned终态为0、40.526950051s；状态文件真实报告covered36/96，不是96资格通过。原件显示q01按site24而q02按site26取runtime body，未用q02的hoisted site25补循环，这一点正确。矩阵v1用整段loop body行，rank偏好kind5，可能取summary/准备融合而非要解释的收缩阶段；原注册的收缩与依赖后算术不能被任意loop中数学片段冒充。v2改以AST的dot行，无dot时最后sum；无loop归约也改最后sum。这是独立于checker成败的、可复算的保守QA见证选择，可以接受，不是新增全部指令门。

仍须如实限定：AST行/成员交集只定位source stage，不自动证明整个dot/reduction已被该区间完整覆盖。尤其一条源码表达可能lower成多个不同操作；最终plan应保所选site实际kind/operation/member IDs和region的body refs。若实际只核到该表达的一个子区域，就按该子区域解释，不能仅以`reduction_body`/`Ktile_body`标签升级成完整源cost。这里不要求每个source成员都单独计时，也不要求逐ISA解释；原checker已有的typed primitive/body规则仍须真正命中。

## 已确认的v1问题及源码修复状态

### F1：raw字节相等不等于event与这些端点、site、observer相连

v1:136–164读取外部events JSON，只核raw SHA与所引用record offset处tick；未核event.start/end等于这两tick、record的site/observer等于event，未用共同validator，events文件本身也未绑定原sealed SHA。保raw/capture不变，修改events端点或借其它site的record_ids，便能影响positive/occurrence/所选site的见证，原代码没有相应拒绝。这是**QA证据关联缺陷**；不是声称原96份数据已被篡改，更不是产品raw输出有错。

最新v2:149–156改为从SHA已绑定capture的owner/launch派生identity，用原raw、compiler manifest和grid调用真实decoder，不再读取events JSON授资格。该decoder内部调用共同`validate_raw_batch`；v2:179–183还显式核pair phase、原raw offset tick、event/record两端值和site/observer一致。因此**F1的源码缺陷已修**；实际v2终态/原输出尚未在本报告读取，不把代码修复说成运行已过。无需新数学或设备采集。

### F2：非runtime stage的逐observer出现及逐stage正duration是额外门

v1:156要求每个选中stage在每observer都有event；:165要求每个stage至少一个正duration。这强于原“default选定observer的整体记录完整、必需阶段有真实区间、非平凡case多个正duration”。原合同允许极短真实区间量化0，也不保证每个条件阶段在所有selected observer执行。

v2:172–187现在要求该stage至少有真实见证、default observer本身complete；只对原q01/q02 runtime body保每observer的K3 occurrence，positive改case级至少两个。这一修正符合原合同，**F2源码已修**，不是放宽原门。当前GCU固定first/last真实writers适用；不得把其它后端unknown reserved slots直接套入相同observer断言。runtime body的K3来自这次冻结主调用，不能把它写成所有合法输入都必须3。

## 最新v2尚须的最小cache修正

v2:134–140复用v1的 `N.regions.json`。它核新的plan与previous plan五个输入SHA，以及previous result登记的implementation SHA；但**没有核实际被读取的N.regions.json字节，也没有将该结果文件绑定到v1终态/回收索引**。`analyze_regions`的返回本身只有rule/regions/qualification字段，不携input SHA。保持plan及implementation不变，仅改缓存某site或loop的status，当前v2就会消费修改后的值。先落required-plan不能防止这个缓存结果被改写。

这是本范围剩余的具体QA复用缺口，不要求重复40s分析或新证明器。最小修法：引用v1实际terminal0收据及独立回收的sealed per-file index，对previous required-plan/result和33份region结果逐size/SHA核同，再消费；保当前before/binary/LLIR/manifest/origin-index及implementation身份检查。也可重新计算，但不是必须。只有在读取结果前核某个任意cache文件自己的新hash而没有原收据参照，不能完成绑定。

最低受控验证只需一份原cache副本：合法复用通过；改一处region/loop status、替换另一对象结果或改原index引用时拒绝。此为该新增cache路径的必要验证，不扩独立数学或全矩阵。

## 其余有限界线与交付建议

* **constant Ktile。** v1/v2把q05–q08 AST loop记`loop_required=True`，但统一要求status `llvm_runtime_iteration_checked`；当前checker仍明确拒绝constant trip。原Ktile确实需要其实际执行/端点结构，但无需新增同binary改K要求。以后接constant-bound scope时，接受的必须是实际constant-trip/路径结果，并按原math.shape/config的K/BK与原raw核相应occurrence；不能只改这个status字符串或用另一个runtime loop的结果填空。优化消除/unroll须如实另记，不造loop事件。
* **源身份。** 现有payload四份源/registry均已核为原字节，current96也已核同；这不是发现输入错配。正式归档宜把这些SHA、rows/objects SHA和plan联存，避免以后将`source_spec_sha256`误作源码与原registry已经自动校验的证明。v1/v2的stage行号筛选忽略文件部分，当前单原kernel来源可按已有SHA范围使用；不可宣传为任意多文件/重名source的泛化规则。
* **组合界线。** 此QA只连接required结构、实际LLVM规则与本次原raw；输出native_schedule=false正确。原after/core preservation、实际SDK family/最终对象/clock事实仍应在后续组合收据中引用已存在的相应SHA；不用State通过票或本轮local covered计数代替。无须因此重编33个SDK对象或重采原数学。

**有限建议：保v1原36/96及具体失败；v2修cache绑定后核其实际终态、required选择与未覆盖原因。** 本席接受其先派生后评估的方案，以及已落实的raw/observer/positive源码修复；尚不接受未绑定cache结果支撑资格。没有新增逐site/逐指令/全ISA门，不授current96、native family或whole通过。

## 追加：v4主阶段与producer split family

本次仅读 `derive_required_v4.py`，SHA **`e926ea3194a864cb6409752d6771c5722a113a06b19a45633d912748e7d43f49`**。观察candidate HEAD `d91f63b17e435c35d064f16d308dccf82010ec33`，产品两个region文件有工作区修改；本席未混入或审阅这轮产品优化。root告知v3 fresh33+96终态0、51/96为中间诊断；本追加只作v4源码判定，不将该转述当成v4实际收据。

**v4两项QA模型修正符合原结构义务及有限split范围。** `stages():46–52` 标记原AST的dot主阶段；`:100` 进一步要求actual `gcu.matmul`，因此不再用同一源码行的cast/add/summary fusion冒充contraction。这里是原注册收缩阶段的实际结构选择，case名只留QA，不是新增产品算子白名单，也不要求所有数学指令独立计时。

`:115–124` 在读取规则结果及raw之前，按确定性候选中的kind/operation固定 **整个同stage producer family**，保成员/source/control引用，而不是最后根据成功或events挑最低ID。`:163–189` 对全部实际观察到的family成员都要求region及适用loop通过；任一个已观察成员失败会进入uncovered。未观察成员仍逐项保 `not_observed_in_complete_selected_scope`、原rule及空witness，不被删除或改成checked。family完全无见证失败，数学body还要求每个default observer有见证；整体default observers须complete且retained>0。raw仍重新decode并核端点、site和observer，case级多正duration保留。

这正确区分了**两逻辑source阶段**与其1:M实际lowering：Outstore的某个split branch在选中scope没有记录，不应单凭最低ID使本来有真实见证的阶段失败；也不能只跳过观察到但规则失败的成员。所选operation family的区间按各自真实issue/body语义保留，没有合并、分摊或复制duration。其资格只能描述这次完整selected scope中实际观察到的成员；“未观察”不等于该成员所有路径已证、原程序没有执行它或整个source family全分支覆盖。输出/后续组合应保持这个界线。

`:174–180` 将runtime/constant iteration分开，并按每个实际观察成员核各自occurrence；不能把family成员的计数相加后称源循环迭代数。这个有限做法不新增same-binary改K门。原case的输入/binary及普通数学证明仍引用既有收据，恒定Ktile不冒充q01/q02 runtime-input证明。

**旧v2的region-result cache缺口在v4中已绕开**：`:137` 对33份输入重新调用 `analyze_regions`，不再消费v1的`N.regions.json`。无需为已经移除的复用路径继续要求cache mutation测试。

尚有一个同类、但更底层的最小输入绑定缺口：`:134–137` 仍消费R096缓存的 **`N.structure.json`**，只核旁边`N.mlir`与actual LLIR相等，没有核实际typed-index文件。typed-index内容没有input hash，`_Index`也只验证结构/schema。替换/修改structure文件而不动邻居mlir，仍会影响fresh规则结果；fresh重算region不是fresh绑定该typed graph。

此处不必重新跑native parser或SDK。最小使用已有R096 sealed `installed-actual-v1/output/result.json`（本席已核SHA **`c18ab8855121a87e054d9fe21c4a5f76f77d7957bd0f96e0a034896c8002042e`**）中匹配 `(binary_sha256,llvm_sha256,object_index)` 的 `typed_index_sha256`，对实际读入的structure bytes核同后再parse；连同该result的原index/terminal引用保存。该原件已经存在，不能仅计算当前cache的新hash充当既有证明。

**有限结论：接受v4的主阶段和split-family派生模型；未发现它新增任意site/ISA或全分支门。** 补上述现有typed-index SHA连接并取得v4终态/逐case结果后，才能评价实际覆盖数。当前不授current96、native family或whole；不重开State/预算/SQL/UI或新数学。

## 追加：第二个区域是否必须单独计时output

**原合同不强制store/epilogue单独获得timed见证。** 原六registry `structure.matrix` 的“2D program grid; >=3 K tiles; contraction followed by store”规定真实数学及实际执行结构；补二规定原依赖计算/归约、transpose/broadcast结构。testing §4:104另要求每个eligible非平凡case至少两个不同源码区域真实区间和多个正duration，没有将第二个区域命名为Outstore/epilogue。R096也明确允许load/store或issue子区域，且必需循环不能被两条无关DMA掩盖。保主mathbody后，把QA自己指定的output timer当成原冻结必需项，会增加原门。

因此，可以对**全部Ktile类**采用同一新版派生策略：主阶段仍为实际contraction/last-reduction，第二个阶段取原AST数学loop内第一个真实 `tl.load` 对应的input issue family。它与主数学阶段是不同原源区域；按实际issue/准备子区域语义解释，不声称整个load完成或engine busy。须由原source-op/member关系确定该load及同operation family，在读取新checker结果/occurrence之前固定；不能按9个失败case、成功site或现成raw个数选择。q01/q02原runtime-body门不改，全部原source/core/输出store/数值与调用义务不改。

这个改动是**修正派生见证策略的版本**，不是原资格前已列明的site清单，也不能把新结果改称v4或原首次通过。保留v4的87/96及9个output-family无见证结果，另存新plan、策略/输入SHA和全部96的结果。1:M family仍按既定完整selected scope规则处理；每个实际观察成员都需实际规则通过、缺席成员显式保留、family全无见证失败，不能复制/合并duration凑两区域。

root正在查9份output缺席原因，这仍应保留事实：若是合法split/实际参与主体或未计时子区域，单独output timer并非原门；若发现真正loss、错site、writer/身份错误等独立缺陷，换第二timer不能掩盖它。这里没有要求为所有source或所有物理actor补独占计时。

root报告更新后的v4已加typed-index原c18 ledger及preprofile source身份核验，actual终态0、87/96；本节仅作上述合同判定，未重读该新版字节或完整终态，不据转述授其交付闭合，也不把前一节e926字节的旧缺口直接说成新版本仍有。允许上述统一input见证方案，**不预判新96结果，不授native family或whole通过**。

## 最终有限追加：同source-stage不同operation分支与v5实际join

**接受v5统一的source-stage branch family修正；不需要改用input策略。** 原AST仍是主mathbody和dependent epilogue/output两阶段；`:120`只对第二阶段将family从同kind+exact operation改为同kind的原stage candidates。主contraction的actual `gcu.matmul`筛选、主阶段exact operation、实际loop和全部observed成员规则检查均保留。family在plan中先固定，不读成功/occurrence作选择；没有改数学分母或挑9个case单独放行。

本席读 `output-branches-result-v1.json`（SHA `b323b51616d9a354b9757d762d26c726f81c4bec623f2e4755ac271be60e0c47`）的原before片段与真实raw解码记录：object20为site40/41、object21为32/33、object29为34/35；各组前者 `slice_deslice_start` 无事件、后者 `deslice_start` 有2个事件。原IR是同source location、相同source/destination memref operands的外层if then与else内if实现选择，不是仅名称相似。对应wait另有2个事件，没有把wait与issue混成一个family。因而v4按exact operation遗漏实际执行的输出实现分支，是派生family模型过窄；保其87/96历史后统一修正，符合原source 1:M/split合同。

新版v4脚本SHA `61379114d4a5433f556d475e8a35e54763be0c81118dadd9ec2cabbba9f7ccd1` 与normal-install-input-v3中的required.py精确相同，已核源码prepare manifest及原c18 typed-index ledger连接。`installed-receipts-v2` 127项size/SHA全同，normal-install-v3实际terminal0、64.663610745s；正常installed source `0baa23e947f10680c0cad8d3d598e3e35fdb164c`、503 members，原87/96和9个output无见证缺口如实保存。本席先前的typed-index输入SHA缺口在此实际版本/收据范围**闭合**；没有要求重parse或重SDK。

v5实际受测 `required-input-v5/required.py` 与root `derive_required_v5.py` 精确同字节，SHA **`2e71d4d78469d8c554ef7bda2381abbc41291abaf2a7d7a9ca28959ec7b126fe`**。本席逐项核 `required-receipts-v5` 108个文件的size/SHA，全同；archive SHA **`e251b5ef45ffa450a53856051d30e8c9be23ea8abbe0b24f9d791f27a2980e45`**。actual terminal0、8.728341245s；先落盘的plan SHA **`01d43bf102300630876f4bcfbb2663058c987ce7f6722f2b6012a174012d79b6`**，source/两registry均核回原冻结SHA。仍用正常installed helper `d4e8d11009a0dcf23af281052991267ebb2a6067c714e1df11c0569d46f0d5a0` 重新分析33份typed输入与96份原raw，不消费未绑定的region结果cache，不重放应用。

逐结果核到96条唯一case与原current96 `(case,captureSHA)`集合完全相同，q01–q08各12，covered96/96且uncovered为空：24个runtime-body、24个reduction-body、48个Ktile-body以及96个第二源阶段。实际observed site-bindings共255，全为 `llvm_observer_boundary_checked`；其中24个runtime iteration、48个constant iteration，其余183无enclosing runtime loop。另9个未观察alternative成员继续显式保留，未升成已执行或全分支覆盖。每case见证中没有复用同一event ID给两个stage。

三个原缺口的实际family现在分别固定 `[40,41]`、`[32,33]`、`[34,35]`。原无事件成员仍not-observed，实际有事件成员分别checked且有2个raw区间；主body仍真实通过，q06两例各6个原body区间、q08例12个，按各observer/member保原循环次数，没有按family相加伪造源iteration或复制duration。

**本报告关于required派生、raw关系、额外门及缓存/typed-index绑定的具体QA问题，在上述实际v5限定scope内已闭合；该required结构→typed region规则→current96原raw applicability join可以交付。** 这只证明所选两逻辑源阶段及实际selected scope/loop的该层连接；未观察成员仍未观察。`native_schedule_qualified=False`保持；实际SDK/native family与其它whole组合门不由这份结果自动获得通过。未执行本机产品/测试/远端/SDK/设备，未读peer；不新增测试或数学矩阵。
