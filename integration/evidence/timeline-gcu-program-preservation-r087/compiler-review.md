# R087 GCU execution-transform preservation：有限独立 compiler review

当前 identity-projection / deterministic-reproduction 路线可支持一个有界的 **SDK lowering 之前 IR 变换证书**。审阅中发现的 greedy 匹配误拒已被替代设计消除；本地同名 clock 定义导致副作用调用的 false-pass、AFTER 大小限额遗漏及间接 call 的空 symbol lookup，均已在当前候选源码覆盖。未发现其它本范围的 confirmed false-pass。最终修正版 normal / `-O` matching 执行及历史 actual before/after 绑定尚待收据，不能继承早先版本结果。

本报告不将证书升级为 State 的 SDK/actor/transfer ABI 适用性、allocation bounds、最终 native boundary、ordinary pipeline 或 whole-goal 资格。

## 阅读、源码身份及未执行范围

实际阅读 `GcuExecutionPreservation.cpp`、`GcuTimeline.cpp` 的 default 接入和 producer、header、CLI、CMake、`gcu_execution_preservation.py`，及 build-v1/v2/v3/v4 收据和 v2/v4 fixture 失败原文。有限追读此次修正，没有读 peer，没有本机 import、产品/测试/SDK/build 执行或设备/数学重放。

初读 greedy checker SHA256 `779592eee7db67a3f39c78acbd163c437495a1abea25bb3f67ee0866717338b6`；替代版初读为 `fb2953e303ff6f4526710f12d8486e9f5761537b899d4f0807a1920b99c3b054`。本次最终读取的修正候选为：

- `GcuExecutionPreservation.cpp`：`6c60defb0509c72c132d2fefe0bf38effd05b5fd444e15549ca7dc9b12737644`。
- `GcuTimeline.cpp`：`6cad9fa1a7b28353125bbd2fb9ae57d078e7c4f26217b8e1523ed6edc2f5e39b`。
- native CLI test：`2ff1d883a59b27d348f41422d6f3b35c7c8b090910e7a0f5bc2e36f9d733868a`。

它们是未提交候选的实际观察身份，不冒称已安装包。请求 GPT-6.1-Sol / xhigh，实际 resolved 型号/档位未暴露，记 unknown。

## Confirmed major M1（已由设计替换覆盖）：greedy subsequence 把原常量绑定到 observer 常量

初版 `OriginalProgram::operation` 76–82 行选择第一个 `sameCore` 候选。实际测试 SOURCE 原 `%zero = arith.constant 0:index` 会与 recorder 入口新增的 zero 同形；选中 observer zero 后，原 `memref.load` 仍使用保留的原 zero，其 SSA operand 已无法匹配，正常 rewrite 可被误拒。这个问题不需要扩大数学或 ISA 矩阵；原有真实 rewrite positive 即是必要回归。

当前 producer 在改写前保留同 context 原 module clone 和原 `Operation*` 集合；内部 checker 不再猜测哪一个同形常量是原 op。旧 greedy matcher 已删除，不要求回溯器、新 origin marker 或一般子图搜索。该根因在源码上消除。

需与实际 v2 失败区分：v2 fixture 原文首先显示 `LLVMFunctionType` storage uniquer 尚未初始化，七例都在 setUp abort，尚未实际运行到上述匹配问题。当前 `GcuTimeline.cpp` 在 builder 前显式加载注册 dialect；v3 已实际正常构建并通过 7 normal / `-O` CLI 例，支持这个 lazy-load 修复及初版 identity projection，不能说 v2 已复现 greedy 误拒。

## Confirmed major M2（源码已修，matching 执行待补）：reserved clock 名字可复用本地有副作用定义

替代版初读 checker 只按两个 callee 名字及无参/result type 放行新 clock call；producer 见同 symbol table 已有该名字便复用。原输入可包含合法本地 `llvm.func @flagprism_gcu_clock_identity_v1() -> i32` 定义，其 body 修改原 `@counter` 等全局。LLVMFuncOp 不属于单个定义 `func::FuncOp` 的计数限制；原定义/body 仍在原 identity 集合和投影中，新增 call 反而首次执行这个副作用 body。因此原操作投影相同并不足以证明新增 call 是 observer getter。若原用户在 site 后读取该全局并写 State，数学结果也可改变。

最小修复是拒绝这些 reserved 名字的本地定义或不兼容 ABI，继续只承认外部 SDK getter；不需分析任意 helper body。当前 `GcuTimeline.cpp:450–459` 对复用符号要求 external LLVMFuncOp、非 vararg、无参数且返回类型准确；checker 的 `clockDeclaration` 及新增 call 最近符号解析应用同一限制。测试 143–176 行新增真实本地 identity 写 `@counter` 的 valid MLIR negative，以及 vararg / wrong-return negatives，并要求 reserved-clock 的具体拒绝。它们覆盖这个原因；待最终同版执行结果。

外部 SDK 函数的实际实现及 link/ABI 身份仍是原编译链合同，这个证书没有声称完成 IPA 或 SDK 函数体验证。

## Confirmed minor M3/M4（源码已修）：离线 AFTER 预算与未知 indirect call 拒绝路径

M3：替代公开 API 初版仅由 rewrite 限制 BEFORE 为 16MiB，非字节相同的外来 AFTER 却直接 typed parse，丢失了旧 checker 的 AFTER 上界。大注释或大模块可进入超出原预算的离线 parse。当前 API 在重现/parse 前明确拒绝 `output.size()>16MiB`，恢复既有资源边界；不要求新的大输入矩阵。

M4：加入 callee 解析时，一度在判断 `call.getCallee()` 之前调用 `lookupNearestSymbolFrom(..., getCalleeAttr())`。合法 indirect LLVM call 没有该 symbol，可能导致空属性 lookup 断言/崩溃而不是“未知 helper”拒绝。当前先显式拒绝无 callee，再 lookup。现 producer 只产生两种 direct getter，所以这不是当前输出 false-pass；是内部拒绝路径的有限稳健性修复。当前公开 CLI 的 arbitrary AFTER 会先被重现不一致拦截，不冒称已实际命中这个内部负例。

## 当前身份投影和离线接线的源码判断

内部检查先 verify before/after，并确认所有原 op 仍存在、未被搬入新增 observer control、原 op 的 operand 仍来自原 op 或原 block argument。随后 clone **actual after**，按克隆 walk 的对应身份只移除新增 op；先断开 observer-to-observer 引用，再 postorder 删除。原 op 不消费新增值的检查使该删除不会把一个已改为 observer SSA 的用户 operand“清洗”成合法证书。

去除唯一新增 module version attr 后，以整个 generic typed module core 比较原 clone，保留 SSA 使用关系、region/block/CFG、类型、operation attributes 与 properties；不是只比较 opcode 或数量。原 op 换原 operand、原 block/分支变化、原属性变化、重排/删除，均不能靠删 observer op 隐去。当前 producer 只插入操作，原对象身份来自同一 immutable rewrite session；这不是接收任意调用方提供的“原 op”标签作为外部证明。

附加内存规则按真正新增 alloc 的直接根放行 load/store/dealloc；原 memref 或 metadata/base-buffer alias 并不会因其 SSA 是“新提取的”就被当作 fresh alloc。DMA 源和 private tag 限 fresh allocation，目的限原来未用的最后 hidden argument 的直接 view。允许从原值提取地址位并存入 observer ring，但没有放行 integer→pointer 重构、对原 State 增加 read/write、任意 helper call 或原值反馈。所有新增 region 内操作也被 walk 检查。

公开 `--check-preservation BEFORE AFTER CERT HIDDEN CAP REGIONS` 重现同一已内部核验的 producer，再将实际 AFTER 与该完整输出绑定；不再接受调用者自由插入、但刚好匹配某个子序列的 observer 程序。字节不同时，在同 typed context parse/verify 并比较**完整** core，只忽略 locations。返回 `actual_output_bytes_identical` 与 `actual_output_program_core_identical` 分开。这能接受历史只有导航位置不同的高层 IR，同时不伪称 debug locations 对后续 SDK/native codegen 没有影响；`SDK_lowering_qualified` 和 native timing 仍 false。

该过程验证的是此 producer 的 IR projection 与 memory-root 隔离，**不等于证明所有 observer 索引/容量、分配生命周期、DMA 实际 ABI 或外部 hidden allocation 无别名**。这些没有被本轮授予；bounds flag 明确 false，后续 State 适用性仍须绑定真实 compiler output、实际 loaded LLVM 和既有 SDK/actor 条件。不要把 `observer_memory_isolated` 一项读成已经完成这些物理/SDK 证明。

## 实际证据及 verification gaps

build-v1 的 C++ CallOp accessor 编译错误、v2 的 lazy LLVM dialect abort、v4 的 location-positive fixture 解析错误均保留为失败；不把它们当最终测试绿灯。实际读取 v3：normal release native build 通过，7 个 CLI unittest normal / `-O` 均 0，whole terminal 0 / 19.096045742 s / 180 秒预算。归档 v3 checker 为 `f9bdb661008326ca943ef741eadd94e8dc00e6c0bc50c8f4408a004034c1e55b`，当时公开 API 只接受 output 字节一致；不能覆盖当前 location-only 分支或新的 reserved-clock 限制。

v4 实际构建通过，8 例中 7 例通过；location positive 将已有 location 后再次拼接 `loc(...)`，原文 parser 报 `custom op 'loc' is unknown`。这是非法测试 IR，没有证据指向 core comparer 误拒合法 navigation-only 变化。当前 fixture 仅替换 synthetic filename，保持合法 IR 并检查 bytes false / core true / native false，源码对应正确；最终 v5 matching 尚未读到。

当前几个 arbitrary AFTER negatives 已由公开 deterministic-reproduction mismatch 拒绝，它们有用地证明了公开边界拒绝数据/未知 helper/新增 State 访问变化；**它们没有直接执行内部 isolation guard 的相应 negative 分支**。本文不夸大该执行覆盖，也不要求为此新造全 IPA/SDK 验证器。

最少剩余验证是冻结修正版的正常 native build、现有 normal / `-O` CLI suite（含本地 clock 定义/签名及合法 location positive），并读取 matching 源码/日志。计划中的历史 109 profile before/retained-after 只有在逐原 SHA、参数及 whole core 重现实际通过后，才可形成对应历史对象的派生证书；目前不预判这项完成。它仍只闭合该 IR 变换边界，不独自关闭 State SDK 适用性或 source/native 门。

## 有限结论

当前修正版在源码上覆盖本次确认的问题，identity projection 与受控重现没有发现新的具体结构 false-pass；没有新增 optional 架构要求。最终同版执行/历史绑定仍是 verification gap，不能以旧 7 例替代。只支持继续按这个有界 IR 证书范围完成现有验证，不作 whole-goal 或 SDK/native 资格签字。

## v5 最终同版收据追加

本节更新上述中间进度，仅核同版执行/历史绑定，不重新审源码。已实际读取 `source-freeze-v5.json`、`gcu-preservation-build-poll-v5.json`、`gcu-preservation-actual-poll-v1.json` 的完整 normal / `-O` fixture 输出、批处理摘要和所附失败例，并逐 SHA 比较当前五文件与 input-v5 归档内实际构建/测试源码。

freeze 文件 SHA256 为 `6c3fb61a379e8a8defd590d78582ddb9d3a7cbe71373fc29546402c835e5682f`；input-v5 归档 SHA256 为 `6079ee7a58cb11630b107bc134f0454f49677cd8d58f09d5ccf97db58be52d1e`。checker `6c60defb...37644`、producer `6cad9fa1...5e39b`、test `2ff1d883...3868a` 与本文已读修正版相同；CLI `d5aa34a0f06e2483412ee8d6d11c5d3b1280906bbf46bd51b3b35f7ed855d6b0`、header `4d3fb749e3e93b2b4f2b6893d12e24ef27425e370b8248ce651ccf5148bf111a` 同样匹配 freeze、当前文件及实际 input-v5。没有拿旧 v3/v4 测试覆盖新代码。

实际 release native configure/build、fixtures、fixtures-O、actual-profiles 五步骤全部 returncode 0；whole terminal 0，`wall_ns=28656641720`（28.656641720 s），预算 180 秒。新工具实际收据 SHA256 为 `da3a0392eb85fe0f211028aa5403d62e199b5698d026fd5ec578c50cccea21fb`。完整 unittest 日志为 **normal 10 tests / 0.209 s / OK，`-O` 10 tests / 0.205 s / OK**。

本地同名 identity 函数修改真实 `@counter` global 的 negative、vararg/wrong-return negatives、合法 navigation-only positive 与原 State/unknown helper 变异均已通过所需拒绝/接受检查。因此 M1 的设计替换及 lazy-load 正常路径、M2 的 reserved-clock 修复已有同版实际闭环；M3 输出预算和 M4 lookup 前 null guard 也包含在同一已编译冻结代码中。仍不声称公开 AFTER 变异实际命中过内部 isolation 的每条拒绝分支，也不声称新增了 indirect-call 内部专门运行负例。

历史批处理结果为 **109 registered / 109 checked，37 distinct transforms，97 preserved，12 unverified**。12 项失败保留，不能写成“109 全部 preservation 通过”。所附原 q05 cold/warm 例明确是 `Actual GCU output differs from checked producer`，returncode 1；它们保留原 capture/math、before/retained-after、binary/LLVM SHA 与实际 hidden/capacity/regions 参数，没有为了通过而将 differing core 当 location 差异放行。本文只核读取到的批处理结果及所附例，不声称本机重读或重算全部 109 原件。

至此最终源码/正常构建/10 项双模式 CLI suite 的 matching 缺口关闭，历史绑定的实际覆盖范围确定为上述 97/109；原 q05 12 项继续 unknown。有限源码问题已覆盖，没有新增 confirmed 缺陷。`state_writer_qualified`、`SDK_lowering_qualified`、`native_timing_boundary_qualified` 均保持 false；这份收据也没有正常 wheel 安装、设备执行或 application replay。不能外推 State SDK 适用性、native/source/loop、ordinary pipeline 或 whole-goal 资格。本追加不要求新增门或新执行。

## 正常安装身份闭环追加：本有限 delta 收尾

只读取新增的 `gcu-normal-install-poll-v2.json`、`gcu-normal-native-identity-v1.json` 和 `gcu-transform-reference-poll-v1.json`；未重审源码或执行产品/测试。以下更新上一节尚无正常 wheel 的状态，不改变历史 97/109 的判断。

正常安装实际源码为 `3b65197ad4ef03fdaeb2bc222e365bf63d0055b0`；owned job terminal 0，`wall_ns=71371390568`（71.371390568 s），300 秒预算。收据包含真实 release C++ configure/build、10 项 native CLI fixture normal / `-O`、wheel assemble/隔离安装、500 members 的安装字节验收，以及 installed imports / allocation guard ABI feature 检查，全部步骤 returncode 0。wheel SHA256 为 `45e6811c3685379e0bf3c5e0e00111144506bc77f97074c296fc07b0f28604ff`；沿用原未变 core library，新增 recorder 是此次正常构建。

身份收据中 v5 standalone probe、normal rebuilt native、normal installed 三份 `gcu-timeline` **同为 SHA256 `da3a0392eb85fe0f211028aa5403d62e199b5698d026fd5ec578c50cccea21fb`**。因此上述相同工具的 10 项 CLI 和 109/37 有限批处理证据可复用到正常安装工具身份，无须重复数学、SDK codegen、TP 或 UI。本项正常安装缺口关闭。

独立 reference 比较 job terminal 0 / 4.270746391 s / 180 秒预算：当前已安装 R077 reference tool `f4ada921c65f55e934ab30fdc820eb65b067be4501725de187931e557dad5ce7` 与新工具在 37 份 actual BEFORE 上，输出 **37/37 逐字节一致**，failures 为空。它支持新增 certificate 检查未改变这批当前 producer 的 IR 输出；不把该比较偷换成所有历史 retained AFTER 都匹配。原 12 个 q05 different-core 对象仍 unverified，不能借 37/37 reference 比较转为通过。

本有限 delta 的源码、同版 CPU/native CLI、实际部分历史绑定及正常安装身份链至此收尾。没有新的 confirmed 问题或本 delta 安装缺口。State writer/SDK lowering、最终 native/source/loop、ordinary pipeline 和 whole-goal 资格均未因这些收据升级；无设备或 application replay，不再追加行动或验收门。
