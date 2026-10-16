# 通用性与正确性：最终有限 delta

审阅者 `/root/r16_product_generality_delta`；2026-10-17。本席是独立产品第二角色，不计额外三名指定 Sol/xhigh 代码走查。未请求模型覆盖；实际 resolved 模型不能由本席自述确认。本次实际 canonical HEAD `07fbc59`，Python 组件 `a829a3312af69c1b961919025053829d7096a2b1`；最后实质 native 变化 `bd61acd`，当前默认 Ascend 物理协议 v3。只读自己 run-011 报告定位 V1/D1，未读 peer 报告、root 结论、PRIVATE 数学/IR/case 映射。

最终有限审阅未确认 blocker/major/minor 实现缺陷，未发现逐算子功能白名单、伪造源关联或基本模式隐式应用重放。原 D1 已在 run-011 的 test-only/device 补核关闭，本次不重开。原 V1 已由下述唯一终态补证在本席允许的SAFE证据层关闭：三后端当前完整资格终态、Ascend独立新mixed样本及实际报告浏览均已到达。本席未重新运行设备或访问PRIVATE原件，不将有限静态审阅外推为任意程序保证。

## 实际源审范围与判断

这是 ce00→ec75/bd61/a829 的有限差异检查，不是无变化全量重审。实际阅读 `git diff ce00df6..HEAD` 的 runtime/native/Python 变化，重点为：

- `Debugger/lib/Instrumentation/AscendProgramAnchor.cpp`、`Debugger/python/{Bindings,CompilerBindings}.cpp`、`Debugger/python/flagtree_debugger/{api,compiler}.py`，以及 `Debugger/lib/{Runtime/TransferEngine,Decode/Decoder}.cpp`。
- `Profiler/llvm/{AscendSourceCensus.h,AscendLateObserver.cpp}`，`Profiler/python/flagtree_profiler/{ascend_census,source_census,fine_grained,profile,reconstruction,_capture,_backends}.py` 的差异与相关上下文。
- Ascend FlagTree 完整 patch 中 compiler identity、两个 JIT 入口的 option 绑定、compiler selector/capability probe、driver identity receipt；`sdk-scalar-tiling-legality.patch` 和 `tools/ascend_sdk_legality/check_pass.py`、tileable/mixed scalar/conditional/multifunction 公共 fixtures；v3/legacy 相关 census 回归断言。

**v3 actor 隔离是实质 transport 修复。** `AscendSourceCensus.h:14` 的地址式为 `64 + ((program*3+actor)*ceil(S/8)*8+column)*8`，相邻 actor 与 program 各占完整64字节行，保留 count/flags 两个32位 word 的饱和 visit 语义。`TransferEngine.cpp:1122` 检查实际设备基址64字节对齐；初始化仍用真实 launch stream。`Bindings.cpp:580` 与 `ascend_census.plan_layout` 对完整64字节 header、actor padding 和全 grid 计算预算；native 的 shared32字节 allocator prefix 用 `cells-4` payload 抵扣，不是截短 raw。late manifest 记录相同 header/actor/program stride；Python 校验全部 header、reserved/unassigned cells、padding，未只校验展示 program。

**源/执行映射未被新布局替换为物理 block 猜测。** `AscendLateObserver.cpp:350` 后仍检查每个实际 side-effect marker 的六个i64 operands、version/column、def-use/dominance，由 marker 自己的三轴坐标/extent 生成逻辑 program。`ascend_census.compiler_actor_views:354` 后继续核 original/adapted LLVM 与 manifest SHA、compile_id、actual function、actor kind/slots/expression、布局和 source ID→column。SDK 同列 clone 仍合计为 source-control visit，不声称数学 loop 次数、有效 lane、完成访存或 busy time。实际源码位置继续来自编译位置/保留 snapshot，而非 basename 猜测；snapshot 与编译输入逐bytes独立一致性的原公开限制没有被本次修复升级为证明。

**legacy 计数已明确撤回 exact。** `source_census.py:29` 后通过保留 transport layout 识别旧 v1/v2，包括 compiler actor binding 和 capture physical plan；decoder、既有 decoded report 的 normalize/reconstruct 均保留原 bytes，派生输出置 `unknown_loss=true`/`count_exact=false`。旧 zero 不能解释为未执行。`fine_grained.py:518` 的默认门控拒绝 unknown transport loss，不能用旧结果补齐当前资格。v3 保留全物理校验和 overflow拒绝，不靠隐藏严重 loss 达标。

**SDK ordinary scalar store 修复按结构工作。** 32行 patch 在 `TileAndBindSubBlock.cpp:730` 将任何带 tileAndSliceFailure 的外部 store 视为整体 tiling 不合法；不再仅 atomic 才触发 fallback，也不允许成功 sibling 掩盖失败 store。`:910` 在 fallback失败后return，在成功后continue，逐函数继续处理。没有 kernel名、shape、SSA/site/hash分支。普通可tile store仍可双subblock，mixed scalar RMW 走原唯一writer fallback；fixture 明确保留 load/add/insert/store SSA和conditional控制，并检查后续函数仍处理。这是 compiler能力边界的通用修复，不是 profiler按算子绕行。

**compiler identity 不由可执行文件 basename 决定。** patch 的 identity 为 resolved路径+SHA，in-memory与persistent JIT key在lookup前绑定；parse/实际compile再次检查，receipt保留同一 fingerprint。有限64项inotify/stat cache失效或overflow时重新hash；fork清空。能力探测依赖实际help，30秒有界，失败明确报错，不默选旧产物名。只指纹所选executable，未声称覆盖整个SDK依赖；并发更换compiler可能显式retry，属于文档已声明边界。基本 capture 未增加执行；Ascend外部counter replay现在需要显式independent参数，非法参数在应用执行前拒绝。

## 已读原始证据与 V1 有限闭环

只做本机Git/留存bytes/JSON离线读取和hash；未import产品、运行测试/oracle/编译器、CPU数学或设备命令。未连接服务器。安装桥读取允许的 `usability-r15-python-alignment` 的源/native/wheel/installed索引和实际安装/公开smoke原件，不把330 CPU测试或native字节复用说成新native构建。NV current wheel `7d95df6950a2419a85186d2e654bca952b0b955c8c4825549e4b422822988f18`、GCU `f24cd4cb39dc411c7c1e04ab3f7d6797a0628ae9284d3cb267b4e8e9b1645c30`。此处未自行重读远端所有安装字节，远端当前全量bytes桥由安装审计证据承担，本席不冒充再完成了一次。

NVIDIA读取 `usability-r16-nvidia-current` 的 actual terminal、SAFE_CURRENT_MATRIX/NATIVE_IDENTITY/CURRENT_BROWSER、controls normal 与相关 gate/冻结摘要。24 ordinary、48 profile终态pass，24 cold/warm同binary对，未移除eligible，原输入/canary/tolerance与每program requested-call副作用检查保留。逐profile有raw/source gate名、capture IDs、qualification SHA、完整物理cell数、source-linked内部记录、requested calls和immutable bundle。第一profile两个实际调用同binary、160物理cells、14 source-linked记录；不是只看selection_status。最大bundle2,026,437字节、export0.520085秒。六个实际报告浏览器source/backlink/raw-link/actor/program/invocation/count exact均通过，首次字体配置崩溃保留，修正环境后原报告bytes不变；没有新设备执行/性能主张。

Ascend读取 `usability-r15-ascend-main24` 的 FINAL_VERDICT、完整匿名48行aggregate/receipt、immutability/ownership/native inventory与manual machine binding，以及公开postcapture v3证明源和normal/-O负例结果。24 ordinary、48 profile，466 terminal raw义务；32 standalone、16 mixed，全部明确区分writer proof。standalone不是伪称SUB0 guard：实际SDK AIV非mixed、AIVEC注册与cached launcher机器乘法/grid closure补证，两个admissible bank都必须保留，sum=1；没有dynamic SDK packet就明确没有。mixed则绑定实际State formal/原RMW SSA、SUB==0支配、无循环、terminal CFG和每actor raw。CPU适配只补原件证明，不重放设备、不改数学/记录；all-zero、duplicate、缺bank/program、假standalone、改blockDim均拒绝。最大bundle22,082,976字节、export1.060979秒、读到的最大compile/launch/sync24.913530秒。

新增 `artifacts/qualification-r15-safe-preparation/NEW8_CLOSEOUT_SAFE_V3/` 读取匿名16行、FINAL_VERDICT和SHA索引：2个独立新数学程序对应8 ordinary/16 cold/warm profiles，全部mixed_explicit_SUB0_guard，96 terminal义务；原数学/State/input/canary/source/object/binary闭环receipt与negative拒绝均保留。最大bundle20,499,086字节、export1.058235秒、compile/launch/sync23.950681秒。它覆盖本次修复触及mixed结构，不能把曾用于修复的main24重新叫未见。浏览器四报告终态此刻未读到，单独pending。

这些SAFE摘要和proof脚本能审查oracle的结构/身份约束，但本席没有访问PRIVATE raw/IR重新独立推出每个数学或全部原cell数；完整实际raw核验由独立资格owner证据承担。公开摘要内哈希是可追溯原件索引，不能当作本席已读取该PRIVATE原件。

## 可复核 bytes 锚点

以下SHA256均为本席从实际本地留存bytes计算：

| 原件（相对FlagPrism-method） | SHA256 |
| --- | --- |
| `Profiler/llvm/AscendSourceCensus.h` | `e76313457cbdbd497cd1df15b7dbea3b0dc18eb7a7741aa2f4ab295571e7dee3` |
| `Profiler/llvm/AscendLateObserver.cpp` | `43031d521108bfc7b2bdb0145e4e1af65f01bfba5cc0ace92515c348ef782ea6` |
| `Debugger/python/Bindings.cpp` | `61ea476d6d6fd24d987e35466582743804fbe8e27f93b4d02926ee8cc540ec86` |
| `Profiler/python/flagtree_profiler/source_census.py` | `c557c2c04d7f01aa11d6713b0a9da8a011763c992ac6a8432fe38630b580e800` |
| `integration/patches/ascend/flagtree-source-census-v2.patch` | `46d354d2c183a619f2b5494f22efc8f1cd3ac743520d9afbba745194afb89959` |
| `integration/patches/ascend/sdk-scalar-tiling-legality.patch` | `7ce7f7c116b9beade493b6473337e73cedff230a62b1b180d26d6f591e30a4db` |
| `integration/evidence/usability-r15-ascend-main24/SAFE_COMPLETE_AGGREGATE.json` | `9b66d019594b6ce3ae3cb1cb20cb359f9d73a90dc22d256b83229331cff2c588` |
| `integration/evidence/usability-r16-nvidia-current/SAFE_CURRENT_MATRIX.json` | `a4c21a7894aeef702a1a2bb9d996ab160e32ac8439e4d7e11d26c40fd534a238` |

新增8的workspace-relative `artifacts/qualification-r15-safe-preparation/NEW8_CLOSEOUT_SAFE_V3/SAFE_COMPLETE_AGGREGATE.json` SHA256 `db438ff95f52e6eeecc3003d1ed266ec93a6fdcf42759aa087491ba9c57d3572`。

## 未覆盖与补证前状态（历史）

没有新cohort/性能实验要求，没有可选愿望清单。未重审所有旧advanced timeline/SDK内部路径，不认证任意多流/并发/graph，也不改变公开eager限制。pending仅：GCU当前24 ordinary/48 profile终态和具体失败/无替换证据；Ascend新8四报告原定CPU浏览器终态。到达后仅补一轮有限证据delta，不重开无变化源审。若出现实际失败，按具体trigger/oracle分类；不能由本报告“未确认缺陷”覆盖它。


## 唯一终态证据 delta（2026-10-17）

仅按原计划补读当前GCU终态及新8报告导航，不再改产品或扩大cohort。实际原件：workspace `artifacts/usability/run-015/gcu-current-qualification/{SAFE-final-aggregate.json,SAFE-browser-results.json,SAFE-browser-owned-processes.json}`，以及 `artifacts/qualification-r15-safe-preparation/BROWSER_NAVIGATION_V2_SAFE.json`。未读root结论/PRIVATE截图或源IR。

GCU完整原24 ordinary/48 profile均resolved/pass；48个原capture逐行保留full_gate_receipt SHA、complete gate pass、source-linked内部记录、physical cells、process returncode、cold/warm和原bundle不变。汇总2944物理cells与逐行求和相等；16同binary runtime pairs、six-kernel specialization隔离通过，eligible移除0、first failures0、hidden retry false、原数学/input/tolerance不变。实际wheel为原已审a829 fresh wheel。最大bundle23,212,507字节、export0.514895秒、cold完整process16.182182秒，均在原门槛内。保留原v2 gate SHA `c1a71e1cfe00835a21515ecaba8d0de668daadfdece456ea1c125ec6bd674412`，未因当前版本重新造宽松oracle。

GCU浏览器原件现已终态pass：12个原bundle覆盖六数学kernel cold/warm，source anchor/backlink、过滤、execution mapping、raw evidence link均真，page_errors空；所读结果全部count exact，展示8个distinct sites，实例按实际1/2次调用。browser-owned survivors为空。该操作CPU浏览原报告，不是重跑device。新8浏览器V2四个实际bundle各24条records，两个不同source sites有anchor、backlink、count exact及逐program/actor raw_offset/SHA查询，execution mapping可展开，page_errors空，original bytes不变，device_execution=false。没有打开私人截图；浏览原件中的匿名line/hash只是导航证明，没有读取数学内容。

本席离线核算SHA256：GCU final aggregate `68521c05ef4b8bb070ea38b96d17c2685bfc1ceb4d25a6745ca9a7a185586cfb`；GCU browser `55021e4029d4b3a011362e5f9c2f00ce5c0dd66dd82825716a5aad988f126ebb`；GCU browser lifecycle `e640c9a192aaa7622019be9623ed7492421171c0fdfa58f8a4a281751dd10699`；Ascend新8 browser V2 `0797dc9f7cf541298f6767f81add808e569eaf9d825548ff719a0738c87cf498`。

**原V1关闭，限定本席角色与允许证据范围。** 原问题是新冻结资格及实际身份/记录/源关联缺证，现有当前三后端完整终态、raw/source/数学身份gate与真实报告导航补齐该缺口；不是只依据多份reviewer意见或单个status字段。没有新确认blocker/major/minor，没有新增验证或功能愿望。仍保留前述PRIVATE独立oracle委托边界、snapshot编译输入逐bytes限制、legacy不exact、SDK动态packet缺失及eager/时钟限制；不再因这些公开且未声称具备的能力重复全量审阅。
