# R096 compiler：legacy clock / tuple / source连接有限审阅

结论：**支持本轮有限连接路线；此前两项源码问题已修复。** 唯一clock owner、无marker的call角色与完整record tuple共同建立LLVM中间事实，不伪造原DI。未发现这几处冻结实现的新具体false-pass。仍有一个必要的定向验证缺口：barrier/getter negative同时破坏record协议，尚不能据它确认compute白名单这条guard已被命中。修复版正常安装亦未在本报告取得终态。

## 身份与阅读边界

冻结 **f46cb0cd47bcd733606c96d5889fd4143b899c13**。沿原请求GPT-6.1-Sol / xhigh；工具未暴露resolved型号/effort，记unknown。未读peer报告，未执行产品、import、测试、SDK、设备、数学、TP/UI或SSH。

实际读本轮 `GcuExecutionStructure.cpp` owner选择delta、`gcu_llvm_regions.py` legacy phase/source/tuple连接及其调用的既有clock/record条件、两份对应测试与runtime文档新增合同；读phase-receipts-v1的实际native build/10CLI日志、phase-receipts-v2的最终28normal/-O日志、代表actual摘要与format-v3链。structured-loop新扩展没有在本报告重新独立走查，不能借其测试数替该规则签字；当前96覆盖及source/native组合亦不在此报告结论内。

最终源码SHA：

- C++ **d57a77e2253b95a114b4402fee7bf06d9805a62639481a1ef4d7428ec5ce7b51**；
- native CLI tests **dfa0e0bb6594c8dc3a343a7bc7bc7653d90b78097fe72acdc2cfdfba74599cf6**；
- Python helper **dc53b79749476bf6be646c8939fad23de5d0cb5c7ce4bd254b0dd53ad7642fe8**；
- region tests **4ae12a7ccfe53cfdb720edec0ad3e7cbc3c8038ae883c478aa93a87ce61ae72f**。

## 有限实现判断及原两点状态

1. **唯一owner选择成立。** C++第28–55行在无显式marker owner时，只把同一函数内同时直接调用exact timer和identity的函数列为候选；多个候选拒绝，原同lexical container限制仍在。只有一个defined函数且无clock时仍可形成结构索引，但不会由此制造成功region。callee名是owner发现条件，实际clock ABI和tuple仍由后续规则核验，不把发现本身当native时钟证明。
2. **角色推导没有改写原图。** helper第163–191行仅在完全没有clock marker时，用每block唯一timer/identity及顺序、实际br/cond_br暂定begin/end角色，存于Index侧表。第1093–1140行逐manifest site检查所有候选，只有一个完整成功结果才接受。既有 `_region` / `_record` 仍核fresh begin三word、selected路径、capacity/count及32word中的site/kind/begin/end/identity/seal；共同end靠forwarded tuple确定动态site，而非虚构end DI owner。无法归类的中途clock明确拒绝。此连接符合有限source-linked observer合同，不需要完整ISA或所有native issue顺序。
3. **placeholder source origin问题源码已关闭。** 第367–371行要求存在可解析origin，且所有路径非空、非 `-` / `<unknown>`，line严格大于0；`loc(unknown)`无origin亦拒绝。对应测试只改manifest location为unknown、空路径、`-`或line0，保原typed图与tuple，其拒绝与本条件直接相关。
4. **非compute `tops_*`误收问题源码已关闭。** 第386–400行不再接受任意 `tops_` 前缀，而限定已观察的mac/floordivf/remsi/vector_step/cvt/select/broadcast/sqrt/extf/truncf/add家族，或实际floatmath+load+store组合。`tops_syncthreads`、`tops_get_thread_idx`不能再单独满足此predicate。该检查只表示此bracket确有有限类型的原body member，不证明整个source fragment的所有原指令都被包括。
5. **producer来源前提呈现准确。** 第1137–1139行用 `clock_binding="typed_timer_identity_call_roles"`、`source_binding="producer_site_and_typed_record"` 和 `producer_source_identity_required=True` 区分legacy事实。runtime文档第610–621行明确外层必须绑定producer/source identity与program-preservation证据后才可称source coverage；helper自身没有重新恢复DI。原图/原location未被改写，native_schedule/source_exclusive仍false。

## Confirmed blocker / major / minor

本次限定源码范围没有新增confirmed blocker、major或minor。上轮设计意见中的两条具体false-pass条件，均已在源码层关闭；下面单列其验证缺口，不把测试缺口说成产品已触发的false-pass。

## 必要verification gaps及最小补项

**V1：barrier/getter negative没有隔离compute predicate。** 位置 `Debugger/test/gcu_llvm_regions.py:246–262`。legacy fixture先把原body的 `fixture.py` location改为 `-`，但parser默认的count load和record stores也使用 `loc("-":line:column)`。本negative遍历全report，将匹配的load/fmul/store全部改成call；这不只替换body，还会破坏end sequence load与32word record。已读取原native CLI typed fixture确认默认count load为 `loc("-":74:8)`、record store为 `loc("-":85:1)`。因此即使旧的任意 `tops_*` 判定仍存在，也可先因record协议错误返回unverified；当前只断言status，不能证实白名单guard已命中。

最小补项：从未改坏的正例结果取 `paths[*].body_refs` 的block/operation，只替换这些原body成员，保持count/record原样，并断言typed compute body原因；或直接以合法body rows定向核 `_body_family(..., legacy=True)`。normal/-O执行这个新增隔离回归即可，不要求重做实际对象/SDK/数学矩阵。此问题已向root给出准确变异范围。

**V2：正常安装尚待matching终态。** 当前仅source-loaded规则、真实native build及格式冻结链；在途normal-install-v1不能预判通过。后续只需本freeze正常包成员/输入身份与既定入口定向结果，原SDK/native未变部分可以按身份复用。

## 已读实际证据与界限

- structure-v1 terminal0 / **22.749834450s**，新tool SHA **dbf87c0b27eee010b88fcd2371002fd1aadf037d9dca4d56fd3b896dccc8ceae**，10 native CLI normal/-O均OK（0.064s/0.066s）。实际built C++输入与最终candidate的d57a77…逐字节核同；owner无marker正例、双owner拒绝位于该同版native CLI测试。
- 最终loop-fixes-v1 terminal0 / **4.921716710s**，28normal/-O各OK（0.174s/0.174s）。实际helper SHA **9ba6e785a46f616ac3c4b53b064e26cbcc8eb9de69652c5666ac9da780707f7e**，tests **4aaaa54a479c8ed5fb7fa2f736936c9a674601ff3fc5db85e3c34f98f0334c9c**，与format-v3输入逐字节核同。格式runner script SHA **2118eee252a677d5e03e7d99c1fc5d91fe79f9e7dba0707a4913d200109b57c1** 与terminal一致，明确比较Python前后AST；terminal0 / **2.818716186s**，最终输出SHA与上述freeze一致。未将formatted bytes冒称另行执行。
- 代表三旧actual摘要为24/26、40/60、31/76；marked两旧actual仍11/13与10/13、loop1/0。它们是有限LLVM结构结果，测试成功不替代V1的精确负例命中，也不授所有current96 source/native或structured-loop资格。
- 33对象/1013区域的regions-v3 inventory对应helper **98538ef36b1d7701e3e2c4fa75a4bfbb0f71b204622530935d4899b59c0eddb1**，比最终source更早；只作已有盘点，不能当最终freeze全对象已重算。此报告没有增加全对象重跑要求，也不把该inventory当whole结论。

## Optional与有限结论

无新增optional重构建议。本轮允许以producer/program-core外部绑定，加typed caller/body/record事实解释legacy source关联；不以原SDK丢失DI为理由强加通用ISA证明门。源码路线及两处收紧可接受；V1精确negative与V2正常安装仍需按其各自实际收据闭合，完整source/native、SDK lowering与whole资格均不由本报告授予。

## 追加：V1隔离负例及V2正常安装闭合

已只读核 `run096/preflight/installed-receipts-v1`，40项index的size/SHA逐项一致；读matching输入归档、runner、完整normal/-O日志、terminal/result及当前测试delta，未执行任何产品、测试、SDK或设备。产品helper仍为f46cb0c的 **dc53b79749476bf6be646c8939fad23de5d0cb5c7ce4bd254b0dd53ad7642fe8**，此次只修改定向测试，未借此重开structured-loop或whole审查。

**V1关闭。** `test_unmarked_barrier_or_getter_is_not_a_fusion_compute_body`现先取得合法positive region，只由 `paths[0].body_refs` 选择三个原body成员再变异；count load及32word record保留。测试直接要求 `_body_family(..., legacy=True)` 因 **typed compute body** 拒绝，同时要求整个region unverified，不再允许其它协议失败冒充白名单命中。两个callee subtest仍为 `tops_syncthreads` / `tops_get_thread_idx`。

installed-actual-v1使用实际f46 installed模块，normal/-O各运行该方法1项，完整日志均OK（**0.015s / 0.014s**）。实际runner SHA **4133c5f133ee547ab655bbb2ecafc077ebdb7809a8bbe5c73f19415b2e9b7792** 与terminal及输入run.py核同；它先格式化、比较前后AST，再执行输出的测试。最终 `formatted-tests.py` SHA **d80a7b0d2da5269c9eac20ba3e1d664cc5789738b5908a62b203d3351e92b7f0** 与当前candidate逐字节一致；未格式化输入SHA **2945d7a056c8a977985d53edcddc1707e760728ad374a32e24091d6062c00b2e** 有同次AST等价链。yapf/check-ast均0；ruff明确因目录配置没有匹配文件而Skipped，不将其称为lint已实际检查。此测试修复当时尚未单独commit，产品源码身份未变。

**V2关闭。** normal-install-v1 terminal0 / **55.644590683s**，source **f46cb0cd47bcd733606c96d5889fd4143b899c13**，503 installed members核同，wheel SHA **7df283276425f632b04813437447bb8317cc0ffbad3988bbe0693a99593862c1**。安装输入中的C++ d57a77…、helper dc53b…均与本冻结一致，runner SHA **76de87f8119eb079c9289e9e58a82c0f2fce03aa518fb9a6b7df11a0bd56eb40** 与terminal一致。17steps全0；**39 bindings / 28 region rules / 10 native index CLI** normal/-O全部过，-O仅预期pytest assertion warning。此安装使用已有matching新tool，不声称再次执行SDK lowering或设备。

同一installed-actual-v1 terminal0 / **39.171288621s**；实际installed tool SHA被runner核为 **dbf87c0b27eee010b88fcd2371002fd1aadf037d9dca4d56fd3b896dccc8ceae**，result的module SHA精确dc53b…。33实际对象均完成本地LLVM规则评估，合计 **1013/1428** 区域checked、每对象至少19；capture/binary/LLIR/index/manifest身份逐行保留，未重放应用或设备。该inventory的runtime-loop checked数仍为0，不能把“各对象有多个局部区域”改写成已完成current96循环/source-native资格。

本报告原V1/V2均已按matching实际收据关闭；本有限legacy owner/call-role/tuple/source前提delta没有剩余confirmed缺陷或必要安装验证缺口。producer/source身份与program-core组合、最终native/source规则及whole资格仍按原外部前提独立评估，不由本追加授予。
