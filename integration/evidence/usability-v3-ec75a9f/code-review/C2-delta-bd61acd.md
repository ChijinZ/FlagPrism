# C2：bd61acd Ascend census v3 受影响增量走查

## 对象与结论

确切审查版本为 `bd61acdadc8b9582f243ca1ee5dc1869ed73e4ad`，相对 `1638a899d80c2ff134efbdb703aa695dbb39c39d` 的受影响产品路径。工作树 `FlagPrism-ascend-census-visibility` 实际 HEAD 为 clean `d1b064e725cf02e29fb8361cfe5ba1f1046f6cc8`，它只比 bd61 增加一个公开 vector-loop probe；本席用 `git show/diff bd61acd` 固定读取 bd61，没有 checkout 或评价该后续测试提交。

**发现1项 confirmed major：旧 Ascend census 读取仍将已有可见性风险的数据声明为 exact。** 状态 open，已及时告 root。新 v3 的 writer/manifest/Python/native 容量公式静态一致；未发现另外的确定越界、跨 actor 物理重叠或版本 ABI 缺陷。v3 是否解决真实记录丢失仍需新 native/core/plugin/安装包和真实硬件终态证据，不能仅按静态布局关闭。

原 GCU C2-01 在1638的关闭及其报告保持不变。原 Ascend eligible state 失败仍未解释，本次新的公开 counter 可见性缺陷不自动成为其原因。

## C2-V3-01 — major / open — 历史 v2 可见性风险没有进入 exact/零值语义

**触发**：用新 reader 对合法、未饱和的旧 `ascend_source_census_v2` raw/descriptor 读取。公开 reproduction 已有真实 counter 丢失，而 count/flags 和 raw SHA 均正常。

**代码依据**：

- `Profiler/python/flagtree_profiler/ascend_census.py:252` 按调用方版本保留旧物理布局；257行的 transport 验证只查长度、零 padding、合法 count/flags，不能发现可见性丢失。
- 同文件341行仍仅凭没有 overflow 就返回 `loss.exact=True`，没有 legacy visibility 警告。
- `Profiler/python/flagtree_profiler/source_census.py:185` 接受 `(0,0)`；198行仅以 overflow 决定 `cell.exact`；261行将它复制成 `count_exact`。直接公开 `CensusReader.cell` 路径也没有 legacy 区别。
- `fine_grained.py:519` 的 automatic gate 接受非零 primary 且 `count_exact=True` 的记录。一个损失部分列的旧 capture 仍可能被视为 complete。
- 新 `source_site_census.md:129` 仅说旧布局没有 v3 isolation，没有撤销 machine-readable exact 声明；同文55行仍将零 cell 直接解释为 unvisited。

**已存公开证据的独立核对**：`run-011/ascend-census-visibility/public-reproduction.tgz` SHA 为 `6ce16147c173e09248c6ff419e340ae13d78c211747bb0a30f8370a70faf7eb9`。原 default raw 为416 bytes、SHA `c6e3ce35293bd5020f2b0c53cb3d07c0797918e803f21c9ba20bff2e3dd0ec88`，P=2、S=8、header32、actor stride64。slot1 两个 program 的后4列为零，slot2 的8列均为1；原结构同时保留 `loss.exact=True`、所有导出 event 的 `count_exact=True`。ordinary/default 的1024个 state 元素均为1。

另外只读公开 diagnostic sidecar 的原始 bytes、metadata 和相关镜像调用代码：相同 marker 另写 header64/stride64 的448-byte sidecar，SHA `1ba1cc3216586771e6e3b8388aa2bac4e03e59c7665cdb0f2808c172051f5201`，本席用 struct 离线核对48个 cell 均为 `(1,1)`，零 header 完整；对应 compact raw digest 也与 paired receipt 一致。它支持“合法零值可能是 transport 不可见”，不构成原执行开销、调度或一般无重放证明。没有执行该诊断代码。

**实际与预期**：bd61 对该历史格式的读取路径仍会把无 overflow 当成精确计数、把合法零值作为未访问。既然已有相同格式的反例，就不能把“格式能解析、raw SHA正确”当成计数可见性保证。应保留所有旧 raw、manifest/source/hash和格式兼容性；在新的派生读取中明确标注历史 transport visibility 不可靠/未验证，撤销 exact，并说明零值不能证明未执行。无需禁读、补造丢失 count 或改写原证据。

**有限回归建议**：使用保存的真实 v2 descriptor/raw，经 `decode_shared_census`、直接 `CensusReader.cell/observations`、规范化报告三个入口检查 exact 与零值警告。历史 descriptor 的格式身份可能在顶层 `record_layout`，也可能只在 `actors[].compiler_actor.runtime_actor_binding.layout`；不能只修外层 decoder。另保留 v1旧 stride读取控制、v3/GCU/NVIDIA不受该历史状态污染的控制、原 raw SHA不变断言。v1是否同样需要保守标注，可按其同类非隔离布局说明；本席确认的真实丢失反例是v2，不宣称所有v1 capture都丢过数据。

## v3 物理布局与 native 容量核对

设真实 source site 数 `S∈[1,128]`，`A=ceil(S/8)*8`，program数为P。新 writer、manifest与 reader统一为：header64、actor stride `8A`、program stride `24A`，cell `(p,a,c)` 的地址为 `64+(3p+a)*8A+8c`。指针基址和所有 actor/program bank 起点均按64字节对齐；不同 bank占据的完整 cache lines 不重叠。最后一列的两个u32都在本 bank之内，actor尾 padding不参与写入。

已读 `Profiler/llvm/AscendSourceCensus.h` 完整 helper、`AscendLateObserver.cpp` marker验证/actor绑定/实际插入上下文：v3采用上述header与round-up，原非原子 saturating count/flags逻辑未变。actor仍是AIC0或实际AIV subblock+1，实际marker自己的六坐标仍用于线性 source program，没有用physical block代替。manifest中的header、strides、layout与source binding version都随3更新。这里只验证地址构造，没有据此单独证明任意 SDK lowering 的 writer唯一性或cache可见性。

`Debugger/python/Bindings.cpp:620` 用实际 grid product和 `3A` checked乘法，v3再加8个header cell；超uint64加法、uint32 cell index、INT32_MAX字节和两项预算均在808行prepare/allocation之前检查。v3物理cell budget为 `C=8+3PA`，byte budget为 `8C`。641行设置底层 `recordCapacity=C-4`，而共享 allocator 的固定32-byte前缀加上 `(C-4)*8`，恰等于 `8C`，没有重复或漏算header。759–766行再次保留该Ascend精确capacity，避免原normalize最小容量改变布局。

`TransferEngine.cpp:1122` 在设备allocation后验证基址64-byte对齐；失败走既有catch释放设备buffer，不把失配指针交给kernel。初始化清零包含完整header/padding，并仍在实际launch stream上执行；v3和v1/v2一样跳过普通ring header合成，避免32-byte ring字段污染64-byte零header。`Decoder.cpp` 也将v3挡在普通ring decoder之外。

例：S=8、P=2时C=56、recordCapacity52、实际448 bytes；S=9、P=2时actor stride128、C=104、recordCapacity100、实际832 bytes。两个预算都包括header与actor padding。离线reader允许零grid，v3 plan为64 bytes/8 reserved cells，无actor记录；直接native grid parser在任何分配前拒绝非正维度，这沿用既有native行为，不是v3新引入的下溢。不能声称本次新增了native零grid launch支持。

## 实际版本传递与旧格式兼容

读过 `AscendProgramAnchor.cpp` 完整ABI函数和 `CompilerBindings.cpp` 对应公开函数：新前端marker、module版本、physical layout、native暴露版本均为3，source列数S与逻辑 `records_per_instance=3S`仍是编译库存；物理padding由native/reader另外计算。Python compiler只接受matching version3 native ABI，避免旧compiler假装生成新格式；`ascend_compiler.prepare`向late插件传实际版本/列数；父编译patch的AutoBlockify桥显式接受v3 marker。plugin bytes以及相关Python源参与既有compiler cache key，新版本没有依赖固定operator、shape、源码名或已知binary hash。

API的launch校验、decode分派、raw encoding和回传路径均显式加入v3。reader仍分别按v1固定128列、v2原紧凑stride、v3隔离stride读取，不把旧raw按新offset解释；校验原header、未分配列和新actor尾padding。物理兼容性代码保留，但其语义限制须由C2-V3-01修复，不能把“继续能解码”当“历史计数可靠”。

## 检查边界与后续证据

只做静态/已有公开证据离线复核，没有本机测试、设备访问、依赖安装、产品修改，也没有读peer报告、private qualification数学/IR或论文。实际阅读包含上述writer/ABI/runtime/decoder全相关函数，`ascend_census.py`完整文件，`api.py` prepare/finalize路径，compiler census分支、`ascend_compiler`版本与cache上下文、profile回传函数、通用cell/exact与automatic gate，并检查14个受影响产品文件的diff/对应上下文；没有重新逐行审核全部compiler或所有runtime后端。

已存 `transport-cpu.log` 为68 passed；LLVM地址oracle测试源码枚举3版本×7列数×3program×3actor共189组合，检查实际GEP常量偏移和volatile load/store性质。这些是工程CPU证据与测试设计，不能代替新包实际运行；本席未运行它们。新native/core/plugin全构建、安装来源、真实v3全物理raw、边界/恢复与硬件终态在本报告形成时尚未核到，后续只能另附限定receipt delta。原旧格式raw loss、原Ascend state失败与本项open finding都不因新构建正在进行而关闭。

## 追加源码增量：1f8c6e0 与 58fca85 的 legacy 语义修复

在完成上述bd61初查之后，有限追加读取确切 `1f8c6e01b979dd8c6fde2daf9affa28b2f372757` 及 `58fca857e73313be92b0c867a35600d16dca1259`。两次增量仅改变Python/tests/docs（另含d1b的公开测试），对bd61的native/core/LLVM产品路径无diff。原初查的major/open事实与证据保留；**C2-V3-01 在58fca85源码层面已修复，安装包与实际动态关闭仍待终态receipts**。

`source_census.py` 新的 `legacy_ascend_visibility_hazard` 从顶层record_layout、compiler_actor.layout和nested runtime_actor_binding.layout识别旧v1/v2。它在读取immutable raw、深拷贝并验证原descriptor之后派生状态，不改raw或descriptor/hash。直接 `CensusReader.cell` 对legacy撤exact、给unknown_loss，零cell明确为zero_execution_status=unknown；原visited/overflow bit仍保留为原始存储事实。非零 observations 保留实际count及overflow，count_exact为false并附具体历史visibility限制；generic decode的summary/loss也携带同一状态。`decode_shared_census` 的summary与loss同步撤旧版本exact，不让外层状态覆盖direct reader的保守结果。

58fca85补齐 `fine_grained.normalize` 的transport_visibility/unknown_loss字段传递，并让automatic coverage在capture loss或counter rows存在unknown_loss时返回 `source_census_transport_visibility_unknown`，有明确的inexact/零非未执行/v3重新采集指引。该条件位于“有其他合法primary记录即可complete”之前，旧格式的部分可见非零记录不能掩盖unknown loss。未见v3/GCU/NVIDIA被这项历史状态错误降级：检测集合限定旧Ascend物理layout；溢出仍独立按原flags处理。

读过新增直接reader测试的顶层/nested身份位置、v1/v2与v3/GCU/NVIDIA对照、原raw/descriptor不变及饱和bit保留；读过shared三版本控制。此处评的是静态覆盖设计，不把远程正在运行的测试或新包当作已通过。旧已经生成的HTML/JSON不会自动被改写；上述撤exact适用于当前reader重新解析raw及其新派生视图，不能声称旧静态报告已被修正。此限定与新增文档保持一致。

本席没有发现该两次Python增量引入新的confirmed blocker/major。后续receipt复核应绑定最终格式化freeze及真实installed reader，检查保存的实际legacy v2 raw经direct/shared/generic解码及coverage确实撤exact，并用真实v3 capture作对照；不需要扩大为新compiler研究或重写历史证据。


## 最终有限源码与安装/硬件 receipt 增量：ec75a9f

本节在保留以上 bd61 major/open 与随后有限静态修复历史的基础上，审查 clean `ec75a9f0592c76f22d64eff443034ab89442b477`。相关中间提交为 `e6644ff23d65ad3d6b76944678ba771847bd4aec` 与 `65c99ab6639e2df76503d6758490ffe9877bb3b3`。bd61→ec75 的差异限于 Python/tests/docs，native/LLVM/parent patch 无差异。**C2-V3-01 现可关闭：源码、最终 installed CPU 收据与真实历史离线导出共同覆盖撤销 legacy exact 的受影响路径。没有新增 confirmed blocker/major。GCU C2-01 保持1638已关闭状态。** 关闭的是各自具体缺陷，不能据此关闭原 Ascend scalar state 失败或宣布完整独立 qualification 通过。

### 最终 consumer 路径

实际追加读取 `source_census.py` 的 layout helper、派生视图 helper、完整 CensusReader 初始化/cell/observations/generic decode；`fine_grained.py` normalize、write_view 与 automatic gate；`reconstruction.py` render/write_view；并检查 profile/API、ascend_census 的最终差异、相关测试和协议文档。profile/API 的最终增量仅格式化。

`source_census.py:29` 同时识别顶层 record_layout、actors[].compiler_actor.layout、nested runtime_actor_binding.layout。167行对已知v3 direct reader以完整 len(raw)/8计 max_cells，涵盖header与padding；原 max_bytes 仍先检查。直接读取一个逻辑cell的descriptor不能因此只付一个cell的预算。新增测试覆盖三种身份位置、32 physical cells正例以及cell/byte两个不足边界。此处是静态设计检查，实际测试状态见下文。

`source_census.py:47` 的 derive_transport_visibility 深拷贝输入，通过capture实际layout/物理plan及event compiler binding识别历史v1/v2；按capture ID撤销对应counter exact，并传unknown_loss。它不修造count，也不改变原raw和原descriptor。`fine_grained.py:119` 在normalize入口使用同一helper，避免已有decoded events绕过reader修复。`reconstruction.py:239` 在reconstruct之后、compact及JSON/HTML写出之前调用helper，故reconstruction与fine_grained派生视图一致；原ai/observations.json仍保留原producer证据。automatic gate保留明确的 `source_census_transport_visibility_unknown`，其检查先于“有合法primary即complete”。已读idempotent/其他capture控制、原输入不变、真实格式身份位置、legacy/v3/GCU/NVIDIA控制及直接reader物理预算回归设计。没有看到历史状态污染新v3或其他后端的静态路径。旧生成静态文件仍需重新导出才改变显示，不宣称它们被自动改写。

### 实际 native 构建到最终安装的桥接

只读 `run-013/ascend-v3-build/` 原三份 package-evidence 与 `final-ec75a9f/` 三份终态包收据，不仅采用summary结论。本席独立重哈希原索引 **94/74/76** 项及最终索引 **34/33/33** 项（顺序Ascend/NVIDIA/GCU），无不符；逐条将每机281个 native source bridge SHA 与本地git中bd61/ec75的确切文件bytes比较，全部相同，bridge所指native-result digest也相同。另将每机68个component打包Python源SHA与ec75匹配。三机旧新native-package索引与ZIP字节bridge分别 **107/216/63** members一致。

原terminal命令与日志显示 Ascend7、NVIDIA5、GCU7个真实TU编译，全部exit0。Ascend包含parent AutoBlockify、CompilerBindings、AscendProgramAnchor、Bindings、TransferEngine、Decoder与late observer；新core/native/plugin link输出digest进入实际包native index，debugger DSO link命令含strip。未变化objects/SDK库被复用，不能说所有core/dependencies从零重建。最终ec75没有重复native build；assemble/create-venv/install/audit均exit0，imports均在对应新venv内。已读审计脚本，其检查源→stage→ZIP→installed逐字节相同及actual compiler/runtime binding；本席未本机安装或运行这些脚本，完整wheel未在本席重新执行验证。

最终wheel SHA与实际installed CPU日志：

| 后端 | ec75 wheel SHA256 | CPU终态 |
|---|---|---|
| Ascend | `821b929b9582080b2f2a6996be25ccd7c41a6443dfcd9da39129e10a554d7206` | 320 passed，3 skipped |
| NVIDIA | `48fd503f5d78dbd83ce8e1b43a8e26e18e172ffde87c1f9282c1217a9cc3c0bf` | 314 passed，3 skipped |
| GCU | `2dad4c6937a6120de3011d0e249398ad6bbca359bfe3b8ac1d004b58b8f9885b` | 314 passed，3 skipped |

三个skip来自显式opt-in browser回归，不计作pass。最终测试清单保留5个actual native HOST GCU guard/layout双向拒绝与104cells/6688bytes正例、callback stub及legacy/direct-v3/normalize回归。另有每机14组actual native HOST v3 budget/layout检查：S=1/2/4/8/9/16/128，grid=[1]及[2,3,5]，每组2预算不足、5错误layout。HOST分配若不满足64-byte对齐则必须明确拒绝并成功完成后续普通HOST事务；最终Ascend14组全拒绝、NVIDIA11拒绝/3实际对齐正例、GCU13拒绝/1正例。拒绝不算NPU成功分配，也不代表v3不能运行于设备。

### 真实公开 v3 全物理 raw 与 provenance

硬件archive `run-011/ascend-census-visibility/v3-installed-hardware-evidence.tgz` SHA为 `14614442b75b2aa8518708e494e80bf2808c5edd779f85e0c0e765414276a948`；generated-byte补充archive SHA为 `ca7dde2675eb5e6af00498c184eb32e829b64a21c1cc09c1a2ae521778a9a451`。本席重哈希两capture manifest的38/37项文件、5份source snapshot、补充13个唯一generated bytes及44个metadata引用，均相符。补充明确排除的38个SDK/link依赖引用只保留receipt，不能当作这些库bytes已经留存或重新审计。

本席不调用product decoder，直接base64/struct检查完整raw：

- mixed：448 bytes/56 physical cells，header64全零，P2×3actor×8列的48个cell全部 `(1,1)`；24个展示events的offset/count/value/SHA逐条匹配。raw SHA为 `1ba1cc3216586771e6e3b8388aa2bac4e03e59c7665cdb0f2808c172051f5201`。
- vector loop：832 bytes/104 physical cells，header64全零。4program的slot1每个前2列为 `(4,1)`，其余6列 `(1,1)`，故8个loop cells计4、24个其余非零cells计1；其他两个actor banks的64个physical cells全零。不能把这些零bank统称为非零观察或将其解释成一般调度证明。8个展示events逐条匹配raw；loop源码确有4次循环，state更新位于循环之后。raw SHA为 `3e77ce79a131511cb76823fb0027ffe26f131b287f0af9a3ffda05b20e2ae00d`。

两例S均为8，恰无actor尾padding；没有声称硬件覆盖S=9/128的padding写入情况，其容量/预算由上述静态公式与HOST边界收据覆盖。已检查三份实际公开adapted LLVM与manifest，AIC slot0、AIV实际subblock+1；每份8个v3 marker、16个volatile count/flags load和16个store，header GEP为16个i32即64 bytes，program/actor索引组合对应3×8列；manifest的header64/actor stride64/program stride192与raw一致。original SDK input、adapted、object、final binary的保留bytes与metadata digest相符，最终binary digest与producer association/运行binary身份一致。plugin SHA `164769a1a5fd2666190ee93b24ed421a572e5cb2c0f5396db39cd9bb3593c496` 同新build/package。硬件为e664 consumer包；它到最终ec75的native/plugin/logger字节桥明确，不能冒称设备实际运行的是ec75的新Python。

两例result与实际log均保留数学断言通过、1024个state均1。这是公开正例的实际结果；host launch metadata不是独立的kernel调度/无重放证明，counter也没有clock/timing含义。新v3布局对本次公开compact丢count反例的修复已有有限真实支持，尚不替代完整cohort。

NVIDIA/GCU的e664实际public default功能archive也作有限核对：命令exit0、新venv imports、5/3个bundle manifest共161/115文件重哈希通过；57个导出counter的raw offset/count/value/SHA相符。它们是新native通用路径的功能回归收据，不是性能或全量资格证明。

### 真实历史离线重导出与关闭边界

`c3-offline-evidence.tgz` SHA为 `9720a10a13406bd776350df273de6e74c576c2f2c9bef957ade0c4df76b9c287`。本席直接检查保存的 `_capture.export_capture` 离线结果：原producer observations的8个counter仍保留旧count_exact=true；新reconstruction和fine_grained各8行全部false/unknown_loss=true/legacy hazard一致。对应id的count、raw_offset与raw_sha256没有变化，原raw SHA `6cbe61d884d8731ac2cefca3cfb92b4020b8e8f86828d6c252d0472f5ae808dd` 重算相符；coverage为incomplete且reason明确。该离线收据本身不提供完整最终wheel身份，不单凭它宣称ec75安装；上述final installed suite、确切源码与包桥接才完成当前修复链。

机器可读的本席离线raw/provenance/派生语义复核结果另存 `C2-final-ec75-receipt-audit.json`。本节未读peer报告或private qualification内容，未运行本机tests、product imports、设备job或改产品。有限review完成：**C2-V3-01 closed；C2-01仍closed；原Ascend scalar state失败仍未解释。** 后续v3完整资格正在另行准备，不在本节完成范围内。
