# R097 compiler：原source成员连接与预复制预算有限审阅

结论：**支持本轮有限source-membership连接；先前指出的重复长文件名预复制预算问题已修复并有对应实际负例。** 在本次阅读范围内没有剩余confirmed blocker/major/minor。q01/site24与q02/site26的unknown border保持原样，真实原body成员可补其source导航与有限LLVM region/runtime-loop事实；本报告不把这些事实提升为最终native source边界、source-exclusive cost或whole资格。正常安装仍待matching终态。

## 身份与实际阅读范围

冻结 **726ab3176c74881c92d5098a8de490f49feb21a4**。沿原请求GPT-6.1-Sol / xhigh；resolved型号/effort工具未暴露，记unknown。未读peer报告，未执行产品、import、测试、SDK、设备、数学、TP/UI或SSH；只读源码、Git、归档、日志及校验数据，仅写本报告。

实际读：`GcuTimeline.cpp`共享site collector、membership提取、正常producer接入与origins入口；header/CLI；Python `_membership_origins`、body来源及结果接线；六个native origin fixtures和两个新增region fixtures。读取 `run097/preflight/phase-receipts-v1` 的v4 terminal/result/完整normal/-O日志、两个actual origins/regions、runner及输入源码；83项index的size/SHA逐项核同。只复用既有LLVM region/loop规则，没有重新走查该轮所有structured-loop或native family实现。

冻结源码SHA：

- `GcuTimeline.cpp` **7d1edb157d3e79065401bf2824865c94dbcc0feee17032a0278c00ae4c7b6bc0**；header **32633cf05eea3517233d13bd183f1b64ef13736b465af5e72b18d2fb7f75d8e4**；CLI **dde4ed57e169cfea0b2e4bc77a215fc738ef3d0169e70ec3983f6cd5eb5851e8**。
- Python helper **bedaffeeada707ae07615f0ed9a914397a9598810670b82067c63c58e6db5a7d**；origin tests **c3d615226d83ba309313232554b6d60eae03289575bec0bd4fa5c7686149a6b1**；region tests **1e5ec7c016eb3a3ab3d2298e0f42913406be95e5cadd03682bed98e08b09d331**。

## 有限实现判断

**共享收集没有改变原site身份。** `collectSites`沿原primitive遍历，再沿同block的enter/leave嵌套深度配对fusion border；正常rewrite与只读origins调用同一函数。maxRegions只限制已配对的fusion region，未配对border不获得无关成员。正常producer原始Operation快照与origins的原module索引用同类module walk；正常producer在插clock前统一收集membership，且只接受original索引内的操作，因此新增observer操作不能混入原成员。未观察到因新接线改变primitive/fusion site编号或配对顺序的路径。

**成员范围是原实际执行IR的静态词法成员，表述边界合理。** fusion仅从原enter之后到同block匹配leave之前逐operation收集，包含其中嵌套region的原操作；primitive只描述自身。它记录原operation index/name、有效source op/scope ID及一个真实FileLineCol坐标，不制造border location。enclosing_controls仅列实际包围该site的scf.for/while/if，不据此声称每个member在每条动态路径都执行。source op ID缺失或无效时为0，Python不会把0作为已知source op ID输出。

**Python没有由membership替代计时/record核验。** `_membership_origins`检查schema、成功status、8192成员上限、唯一非负operation_index、严格整数ID及坐标路径/行；placeholder坐标不产生origin。真实成员坐标与原site坐标合并后，原有primitive callee/body家族、fresh begin、实际完整record tuple和loop条件继续执行。unknown border可以取得成员来源，但原border location仍不改；未索引/超预算membership不提供来源。输出保留 `producer_source_identity_required=True`，并非仅凭任意metadata里的坐标就独立证明其来自该capture。

**legacy补件的必要组合前提在实际runner中有落地。** runner先核retained before字节SHA等于该capture的 `debug_execution_input_sha256`，再要求origins与原manifest所有site的 **id/kind/operation/location及顺序** 完全相同，才copy-enrich原manifest。实际typed图复用R096已经绑定的对象索引，原capture只读并再核未变。此处所支持的是“这个原producer site确实包围这些原成员”的来源连接；最终lowering/native关系继续由既有外层组合核验，不把membership当新的DI或native证书。

## 先前资源finding与修复闭合

初版每成员允许4096B文件名、8192成员，跨site最多100000 work，但仅在完整JSON/formatv后检查8MiB输出；共享长loc alias可在很小原IR中复制远大于输出上限的坐标字符串。该问题已经向root给出明确触发，未要求新SSA/ISA或应用矩阵。

冻结版 `sourceMembership`在复制operation/file字符串与push JSON前，先限operation名1024B/file4096B，再用JSON转义后的长度加固定字段余量估算；所有sites共享 `detailBytes` 的 **4MiB** 预算。减法使用饱和剩余量，避免无符号下溢；control每项先预留128B，另保64项/100000work/8192members边界。超限membership明确unverified及 `source_member_text_budget_exceeded`，Python不使用其部分坐标。正常producer与只读入口都使用相同累计预算。此修复关闭本次指出的坐标复制放大路径；不声称它为所有既有MLIR parser/location打印建立了新的全局内存证明。

对应实际native fixture使用 **1024原arith操作共享一个4096B文件名loc alias**，要求得到上述特定reason、少于1024已复制成员和未授source-exclusive资格；不只是以任意CLI失败为通过。该fixture包含在v4六项normal/-O套件，两次均OK。因此本资源finding的源码与定向CPU验证均已关闭。

## 已读matching实际证据

origins-v4 terminal0 / **24.052374891s**，script SHA **3396c68d4ee7eb005895b038cfd564b92bd0f9bde5169c99415ba59bbd4259d8**；正常native configure/build成功，新tool SHA **374ab5f9fd07e2c5c7e8ec32f82365fa5c98e5736fd36648b3ee96b7263bf8d4**。clang-format两轮均0，保留的formatted C++与candidate逐字节一致。

- **6 origin normal/-O** 均OK（0.097s/0.096s）：unknown border原成员及enclosing loop、正常producer与只读提取membership一致、重复插桩拒绝、预算0、孤border不认无关成员、多body/超上限及长loc预算。
- **10 preservation normal/-O** 均OK（0.206s/0.203s），包括真实rewrite certificate、原State读写与callee逃逸/保留getter签名反例；没有因新增manifest分析取消原effect隔离。
- **30 region normal/-O** 均OK（0.188s/0.189s），包含unknown border由原成员补来源及无效/placeholder成员拒绝。v4实际Python helper SHA为 **c92e0556b3e08ebf92749b7b5eb743fd32a056e57ef5e8d9a1ad568ee7d5ab9a**；已逐文本比较它与最终bedaff…版本，变化限formatter排版；不把两个不同SHA称为同字节执行。最终正常包的精确matching仍列后项。

两实际对象的有限表如下；不是仅凭duration正值得出的结论：

| 原对象 | border / 原成员 | 有限LLVM region/loop结果 |
| --- | --- | --- |
| q01对象0，capture `4c42d244…a2135d`，before `163acb5f…7e4a31d` | site24仍 `loc(unknown)`；8成员，source op IDs **15/18**，原arith.mulf位于kernels.py **13/14**，scope1；外层scf.for原index155 | region checked；single-header/latch规则checked，header70/latch76/exit77、initial69、runtime trip829；source_iteration_id/termination资格false |
| q02对象4，capture `e9d6af02…286370`，before `0ed05a0a…6a7650` | site26仍 `loc(unknown)`；12成员，source op IDs **17/20/24/25**，原mulf/divf/addf位于kernels.py **31/32**，scope1；外层scf.for原index175 | region checked；同有限规则checked，header80/latch86/exit87、initial79、runtime trip921；source_iteration_id/termination资格false |

原metadata、raw和capture字节未改。此表补上这两处真实unknown border的原source成员及LLVM runtime重复关系，不代替最终native begin/end/原member issue关系，亦不外推其它未评对象或current96整体。

## Confirmed blocker / major / minor、必要gap及optional

当前本有限delta **无剩余confirmed blocker/major/minor**；先前坐标复制资源问题按上文关闭。

唯一待补的本delta交付验证是 **726ab31正常安装/精确formatted模块接线身份及既定定向检查终态**。安装正在运行，不能将v4 standalone/source-loaded结果冒称正常wheel已通过；后续可复用新tool exact SHA及未变SDK/native，不要求重跑数学/设备或旧矩阵。

无新增optional要求。source/native最终组合、当前96适用性、exclusive cost与whole签字均不在本报告授予范围，也未以缺少通用ISA或一般alias证明另加门。

## 追加：matching正常安装及修正验收闭合

已只读核 `run097/preflight/installed-receipts-v1`，43项index的size/SHA逐项一致；实际读取normal-install-v1和installed-actual-v2 terminal、完整定向日志、原/修正验收脚本、配置与源码输入、result及四份原Perfetto protobuf。未重审实现或执行产品、测试、SDK、设备。

**原normal-install-v1终态仍为terminal1 / 56.556414549s，不改写为成功。** 其正常组装、安装、成员/ABI/import检查及定向验证前23steps全部0，末尾第24步 `installed-real-source-navigation` 为1。实际stderr与脚本表明，失败条件将未JSON转义的单条 `location.encode()` 在protobuf内直接查找；真实annotation承载的是JSON数组，故不是产品丢失source导航。原失败日志完整保留。

安装源码为 **726ab3176c74881c92d5098a8de490f49feb21a4**；正常输入中的C++ SHA **7d1edb…** 与Python helper **bedaff…** 均与本报告冻结精确核同。normal runner SHA **c4c57007b69e81fb33f9305f81750d1c322e88d6708453cb36be2f8731c7ef24** 与terminal/输入一致。installed日志完整确认 **10 index / 39 bindings / 30 region / 6 origin / 10 preservation / 4 source-navigation** normal/-O各自全部通过；-O仅预期pytest assertion warning。其中最后一项是source导航的既定检查，不替最终native/source组合或UI整体资格。

**同一正常安装内的installed-actual-v2 terminal0 / 4.021816430s**，实际script SHA **135c42f977f5753249c167bb4daf20605019b91b2f8bebc8c307755e87e08266** 与terminal和输入匹配。仅修正验收为查完整 `json.dumps(source_locations, ensure_ascii=False, separators=(',', ':'))` 字节；无产品修改、重装、重编或应用重放。脚本再次逐字节核 **503 installed members** 与实际wheel一致，并核installed native SHA为已审v4 **374ab5f9fd07e2c5c7e8ec32f82365fa5c98e5736fd36648b3ee96b7263bf8d4**；因此这次成功确实发生于上述同一正常安装，而非source overlay替代。

该补查直接解两份原raw：q01/body24为34 events / 68 records，q02/body26为36 events / 72 records；capture/raw SHA与原件绑定，legacy无membership输出与旧模块相同。补membership只改变source/site导航，commands及其余canonical timing/runtime字段核同；原capture/raw未变。原unknown source条目仍保留，实际member source IDs分别15/18及17/20/24/25；source_cost_verified仍false。

四份实际protobuf的大小为 **37393 / 37476 / 39711 / 39792B**。本席读取其原bytes，逐份SHA与result相同，且完整source_locations JSON数组实际存在。该结果关闭原错误验收留下的导航检查缺口，不声称重跑TP/UI，也不据字节注释单独证明native source边界。

因此，**本R097 delta的matching正常安装与精确formatted模块接线gap关闭**；先前资源finding及有限成员来源检查继续成立，本delta无剩余confirmed缺陷或必要交付验证缺口。原controller1仍如实保留；current96覆盖、native/source最终组合与whole资格不由本追加授予。
