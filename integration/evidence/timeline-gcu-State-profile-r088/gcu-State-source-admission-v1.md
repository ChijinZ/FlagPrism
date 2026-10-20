# R088 GCU State TTIR admission：最小组合判定

**这个小组合足够，方向可采用。** 验证实际profile的pre-observer TTIR中，原State地址只能继续构造访问指针或作为load/store的pointer operand；再结合R087完整highGCU新增效应隔离及实际SDK/object链，就补上了“原有地址逃逸不能被observer例外掩盖”这一前提。无需匹配ordinary整程序的常量/操作顺序，也无需再做LLVM ring全alias、IPA或ISA分析。

这是对拟议admission的设计判定，尚未审实现或授新State资格。观察candidate `11d9b1f23ee2b623d951937bfba9efa54f45f828`；请求GPT-6.1-Sol/xhigh，实际resolved型号/effort未暴露，unknown。只读现有JSON/源码；未运行/import产品、parser、checker、测试、SDK或设备，未读peer。12份原q05历史拒绝保持，本报告不讨论whole门。

## 实际输入支持这个有限范围

已读 `run088/preflight/gcu-ttir-pair-v1.json`、`gcu-parser-probe-v1.json` 和LLVM样本。q01原TTIR为7220B、profile为193801B；后者包含较大的debug metadata，不能据文本长度判断数学或State使用不同。实际parser probe中的State类型是 `!tt.ptr<i32>`；State路径为 `tt.splat → tt.addptr → tt.load/tt.store`，其中load返回 `tensor<128xi32>`，不是地址值。SSA身份/operand位置检查可直接覆盖它，不需要从打印位置或debug字符串推断用途。

本报告复用本席R087已审的highGCU证书边界：新增读写只到fresh allocations，新增ptr2memref只能来自unused hidden output，发布fresh→hidden，原操作不消费新增value且整个原SSA/CFG严格恢复。它因此阻断新增observer的保存位再成为原内存写地址；TTIR admission负责排除**原程序本来就有的**同类State地址逃逸，两者职责闭合。

## 需要写准确的最小规则

1. **绑定实际入口和同一个State参数。** TTIR SHA须来自本profile已绑定snapshot/math/编译链，和对应highGCU before/after、实际profile LLVM及loaded object在同一行。选定真实entry和State形参ordinal/类型，不能从任意函数或另一个指针开始证明；应与实际LLVM枚举的State ABI相接。SSA打印名不作为parser中的永久身份。缓存按TTIR SHA、entry/State ordinal及规则版本，不能跨module缓存裸SSA地址ID。
2. **真实parser加有效IR验证。** 使用installed libtriton的实际dialect/parser和值/operand API，确认模块验证成功；不能仅因文本可parse便把未知同名op当成已知语义。State应符合本批已绑定的i32 State合同，不顺便授任意pointee类型资格。
3. **检查每一个OpOperand use。** 对每个State-derived pointer value的所有use逐个判断，包括同一op中的多次出现及多个consumer。transport限于 `tt.splat/tt.addptr/tt.broadcast/tt.expand_dims/tt.trans` 的实际pointer-bearing operand位置；`tt.addptr`只能在pointer operand传State，不能因op名在表内就接受其它位置。将其全部pointer-bearing results加入worklist，继续到所有终点，不能只验证第一条合法load/store。
4. **pointer-bearing包含tensor元素。** `tensor<…x!tt.ptr<i32>>` 仍是State地址，不能用“顶层type不是PointerType”把它当普通data。上述transport的结果要沿这种shaped pointer继续追；load的所有result、store的value须按实际类型确认不携带pointer。本批load出的i32/tensor<i32>是State内容，不是State指针，允许停止地址来源追踪。
5. **load/store按operand角色，而非名称放行。** State-derived value只能处在 `tt.load`/`tt.store` 的pointer operand；若同时出现在value、other/fallback、mask等其它位置，拒绝。普通值写回State是合法终点，不由此授一次写者/范围资格。
6. **其它use保持拒绝。** `ptr_to_int`、存地址值、未知callee/inline asm、return/yield、region/block参数传递及其它未建模pointer transport都不静默接受。仅在region内直接捕获State并通过上述已允许访问使用，与“把State作为iter_arg/yield/branch参数传入新SSA值”不同；前者继续检查实际uses和LLVM CFG，后者按本版有限规则拒绝即可。

这些是将拟议allowlist落实为sound SSA检查的必要细节，并非新验收轴。无需为尚未出现的所有pointer操作增加模型；真实输入若触及其它transport，保该具体case未证，再有限补充。

## 组合后LLVM层能省与不能省的工作

当 **TTIR admission通过＋同对象highGCU证书通过＋实际编译链核同** 时，可把actual profile LLVM中的State `ptrtoint→trunc/lshr→integerdata保存`解释为已验证的observer payload，省去重复证明ring所有load/store/alias用途。这项例外由本行三个前提共同准入，不是无条件忽略同名opcode或给所有profile一个全局boolean。

仍应保留原checker的真实State transfer枚举、地址/descriptor参数、guard/CFG、物理actor/grid与每元素writer计数，以及未知pointer来源/constant-expression pointer/未知callee等既有拒绝。TTIR admission只证明State**地址身份**未被原程序保存/外传；它不证明State内容一定正确，不证明所有其它输入之间无别名，不授任意重构指针资格。原owned输入/hidden allocation及合法调用前提沿既有合同复用，不新增全局pointer alias门。

因此不必再以ordinary counts代替profile，也不必证明ordinary与profile整体IR相同。profile的State访问范围和参与条件仍按真实LLVM计算；source admission仅使新增地址观察不会误触旧escape规则。

## 少量足够的验证与当前结论

实施后最少验证可压为：

- 正例：真实q01的scalar→tensor pointer链，以及原已出现的矩阵shape transport；admission通过但不自行输出writer-qualified。
- 逃逸反例：同一个State值既有合法load/store，又有ptr_to_int或unknown call；必须因额外use拒绝，防只看首个consumer。
- tensor/region反例：State经splat/shape transport后交给未知callee，或作为region iter_arg/yield；仍拒绝，防在新SSA value/tensor类型处丢来源。使用真实parser可验证的IR，不以语法错误代替语义拒绝。
- 绑定反例：换TTIR/entry或State ordinal，不能继续沿用原正admission与证书。

原R087 saved-bits经load/GEP写原内存、unknown helper与shadow getter的反例继续复用，不要求再叠一套LLVM ring/IPA负例。未变的actual TTIR、highGCU/LLVM翻译、SDK资源及数学/TP/UI不重跑；新admission在已有实际输入上按key做CPU验证即可。

**未发现拟议小组合本身的实质缺口，前提是以上operand/类型/身份规则按字面实施。** 目前没有实现与终态，不能把设计可行性写成97份profile State已通过。若实现把allowlist写成只看op名、只看顶层type、只看一个use或不绑定同一State参数，则存在具体漏检；对应最小改动就是上述逐use/角色/typed pointer与身份检查，不需要扩大为新框架。

输入SHA：TTIR pair `cae0b37d70810e48744695ad953f7283313221227df0f6f291f9d8ada135df32`；actual parser probe `e2e1732116d37960d60f335b3511f82c4946c640c6c3f3cce7f588de14ab5406`；LLVM sample `0a39ed5bc14dcc94105f78914924c0a0ef384649c3bbf01c6952b46554f7f89f`。这些是已读取原件，不是本机重执行结果。

## 新实现与实际终态的有限追加

随后已读取新 `tests/timeline/state_source_uses.py`、四个真实parser fixtures、`check_gcu_source_admission_v1.py` 及 `gcu-source-admission-poll-v1.json`。helper SHA `7c3d3f59ec6fb8365cf80a971fb5894441a3fb0184758d64fcbbe3475b9ce152`，fixture SHA `6f8ea0ee8436700e2bfe9fc98eb90f349612b9933376c91a2a07f994dcc4a092`；两者与实际 source-admission-input-v1 archive逐byte相同。初稿“尚无实现/终态”在本source admission子项上由本追加更新。

实现 `:32–65` 对所有actual operand位置扫描，强制State-derived值只在operand0；worklist闭包不会因walk次序停止传播，shaped pointer通过canonical类型中的 `!tt.ptr<` 继续识别。load返回非pointer内容、store value非pointer；未知callee、return、yield/region forwarding均拒绝。新增 `tt.reshape` 同样只是pointer tensor transport，且结果仍须pointer-bearing；这个有限扩充没有引入地址数据逃逸。检查使用显式need，不依赖被-O去掉的assert。

四例已实际normal/-O各4pass；原ptr_to_int反例本身同时含合法State load/store，已覆盖“不能只看第一条合法use”的fanout。另有returned pointer和region forwarding拒绝。本次不把初稿列的所有可选形态重新升为必须追加测试。

actual runner对原capture/math、TTIR compiler artifact SHA、原highGCU before/after文件SHA及正certificate的SHA/范围重新绑定。实际 source-admission-v1 terminal0/`3.570886718s`：原109条、33个不同TTIR全部noescape；只对原97个正transform给 `observer_payload_admitted=true`，旧12仍false。所有State/native资格字段继续false。poll SHA `80a17e552dd6cef437fa841b82f293bf094bc9f949fe6277e83c0f173ac28506`。

**有限结论：这个已实现source admission足以补上R087要求的原程序无State地址逃逸前提，可以接实际LLVM observer payload模式。未发现该原登记范围中的confirmed漏检。** 不必再匹配ordinary整个program，也不必重复LLVM ring全use/alias分析；实际State transfer/guard/descriptor/actor仍应按原model计算，尚未由这份终态完成。

仅一个非阻断的绑定维护建议：runner用“仅pointer参数”的header列表计算ordinal。对当前既有profile wrapper/pointer-formal ABI可复用，但若以后接受带scalar formal的其它输入，应显式核完整formal数量/顺序，或直接取真实完整ordinal，避免选到另一个i32指针。它不是当前109条的新增重跑门，也不改变本次准入结论。

## current96 与 reviewed SDK 的最终有限组合追加

**现有完整证据足以将当前96条profile提升为“actual State writer under reviewed SDK”的新派生判定。没有剩余需要新SDK编译或设备重放的实质缺口。** 只需据下列精确范围生成新的profile-specific contract/sidecar，保留原执行收据的false和历史失败，不把R082 ordinary32 contract原地改成无限范围。这个结论仅是profile State物理writer，不授其它边界/调度或whole资格。

### 分母与替代关系已独立核清

已读完整 `gcu-receipts-v2/runs/source-partition-v2/output/actual-partition/rows.json` 及v1 sibling actual-source rows。109行逐stage/case/capture file/SHA与R059原登记精确相等（仅将supplement标签归一）；再逐行核source admission、before/after、certificate、TTIR/LLVM和binary身份关联。

用case包含phase的原登记键应用affected13替代，得到 **96个当前phase cell**：affected13＋original-six60＋supplement23，q01–q08各12。affected13为q05全部12条及 `q07-s1-c1-cold`。最终12个失败恰是old original-six/q05，与current96交集为空；第97个成功恰是被替代的旧supplement/q07-s1-c1-cold。因此97＝96current＋1旧历史State成功，不能改写成97个当前数学资格。12旧q05不需要另造资格或重跑。

本席还从R083原28份与R087补9份retained翻译中，逐97行重算对应原MLIR/实际LLVM SHA，并对33个有效输入核机械去GPU容器后的每个操作行；全部与rows核同。33份actual LLVM中的所用整数helper集合仍仅为已审的minsi/maxsi/remsi/extsi，没有把未审div/floordiv按名称继承资格。

最终v2 terminal0/`39.676662691s`，normal/-O各42pass；helper保留明确的private destination正识别及其新负例。实际执行helper SHA `867a00b2599c379acfa49bcad0f3295bc05449100d764c308eb1e50c08241c6d`。v2与保留v1的全部actual rows逐byte相同，都是97 partitions/33个不同key；历史v1工具不足没有被改称终态。后续判定引用v2代码/终态。

### 不是仅看partitioned计数

按R082已手工核过的真实SDK公式，本席用stdlib从完整rows的每个descriptor独立重算：97行共2928次实际写回、186705个i32元素，全部恰一writer、目标界内、source窗口有效，无零长度写回。原五种write primitive计数为：deslice1 672、slice-deslice1 24、memcpy 432、deslice2 1295、slice-deslice2 505。2D deslice仍要求完整窗口，不发明min；1D及2D slice-deslice按实际参数顺序裁剪并核source。

当前96子集为 **2892次写回、183048个i32元素**；额外旧q07为36次/3657元素。实际descriptor destination shape最大256、source shape最大32、source offset全0、destination offset最大224；各坐标/typed word/byte范围落在已审规则内。两种4/8物理thread与原grid逐行核对，没有从logger observer个数推State actor。没有出现需要新增SDK State helper语义的primitive或窗口。

### 已有SDK/launcher证据可直接复用

已读R082 `gcu-reviewed-State-ABI-contract-v1.json`（SHA `32c4da9273e4db2608b14f035a209faf56ec449afdf4c83fd3119305b7fd3f42`）及本席原SDK ABI报告。复用的是具体getter、五种搬运及整数helper规则，不是把旧ordinary32资格标签自动外推。

新只读资源和源码补齐了其profile适用性：

- 旧R052与R077两份actual backend.py逐byte同为 `ccd500895c64cf19330071a3da156c113d001391c064beb1a458b93ea82f71e8`；`:475–478` 的gcu300实launch为原grid和 `(num_warps,1,1)`。109行SDK cohort identity的arch均gcu300，num_warps与97行实际partition threads逐项同；不乘12或128。
- SDK compile `1b7e13a7a2888e126a1022de6a129eec1404da5e0f0f0a0c2e702de784855e40`、translate `f93024f7d86828022bc6b61d77c02522195d25df5ad76ac634d909efe74bb361`、State builtin `fa9d850080258f7cfd3acbdccfdb3485007b9b87c3c5ed34ab187dacbb52944a` 与原资源核同；R082完整helper文本/整数定义无需重提取。
- `SDK-resources-v2/output/result.json` 将109原capture SHA逐行连到3个真实backend cohort（72/24/13）。三份实际compiler.py均为原capture记录的 `f21fd9af7125a453e4b34a9c08d81664a17f81a3890e569dbca3c994f73eb95f`，三份toolkit.py均 `2dc19a46d094da39b7682ad6a9b753a1c8ddb4940e562674d5ce56f6af5485d2`；本席重算留存文件SHA核同。compiler `:462–475` 把实际mod交给device-only/is-triton-backend/gcu300/toolkit-path的make_fatbin路径，toolkit `:35–41/:205–206` 将同一文本作为stdin交给该SDK编译器，不另换一份相似输入。
- profile链接的API库为原 `1a780215d7a63e34ce9c8cba6bfb126d222db726f5dca8802f3af0161fce81ec`。已读完整静态decode并独立重算定义集合：**621 definitions、0 aliases，本次所需State getter/transfer/integer helper同名定义overlap为空**，不是仅grep一个timer正例。该库没有为上述fa9 State helper引入另一份覆写定义；不必因此重编37个profile。decode文本 SHA `1ea0d2b221ca3b296823d782069cd66ce313288dda7a0e543626817015406c82`。

结合R087已绑定的actual before/after、原math/loaded fatbin、actual compiler source与本次真实LLVM State调用/分片，上述材料足够把source模型落实为本批实际SDK物理写回规则。没有以一个trace能打开、数学State==1、当前文件路径相同或summary数量代替这条链。SDK静态decode是已有库的只读检查，无profile SDK重编、device/math/TP/UI重放。

### 剩下是范围明确的派生记录

可生成一个新的profile State ABI/qualification sidecar，引用：current96的逐登记选择、R088 source admission、R087正transform证书、v2实际33-key partition及上述原资源/SDK报告。范围写current96；额外旧q07可保单独State分项成功，旧q05十二份保持历史未证。原 `state_writer_qualified=false` / `SDK_ABI_binding_qualified=false` 是执行原件状态，不应覆写；新组合sidecar才表达本次有限审查后的true。它不把SDK lowering所有属性、native timing、allocation容量或其它goal门一起置true。

本追加所需SDK/对象适用性证据现已齐，**无须再增加37次SDK recompile、完整LLVM ring alias、IPA、ISA、新数学或TP/UI门**。补二ordinary等本报告外范围不由current96 profile判定代签。

最终主要原件SHA：actual-partition rows `43c53a4570fcfac12fd143cc68c7998a6e84c5043e125c1dea5592aa43cbb77f`；actual-source rows `45c25c3d0bed4bd01f5e732c8a19a65f2031597183eca9ac0636c91bc38d1c39`；v2 partition result `6cbba5f069f493a0c70994884db2bdad41b9b001a17b5b033ed929a853d443c0`；SDK resources result `feeef922c0ae981411d4bba796f8fa8210461083317532776f44e32340ad2272`；profile API definitions index `5b5b34922c31b4240b00aff51a24dac44a872dda91dfcc1dfd85162a705b5fd7`。均位于root `run088/preflight/gcu-receipts-v2/`，不是本机重新执行。
