# 时间线设计独立评审 r11：编译与整体可实施性

日期：2026-10-18。评审对象为当前工作区 `Profiler/docs/timeline_design.md` 与 `Profiler/docs/timeline_testing.md`，重点为新增设计 §0.4、测试 §0.1；同时检查其依赖的 §3–§8.14 与最终验收门。本文是独立设计评审，不是最终代码验收，也不授予设备资格。

## 结论

**建议通过本轮设计合理性审查，按既有 A/B/C/D 顺序继续实施。未发现新增章节引入的 P0/P1/P2 确认设计阻碍，也未发现必须继续增加公共接口或测试矩阵才能解除的合同冲突。** 普通无 profiler 标记的 kernel 可以通过通用编译接入获得 site、隐藏记录 ABI 和观测对象；现有源码能支持这一工程方向。三后端完整源区域时间与异步解释的可行性仍须由各自的最终对象和真实设备证据决定，本报告不能把它们填为已通过。

新增 §0.4 把后续型号接入表述为具体工作包，而非“写一个 adapter/配置即可”。测试 §0.1 要求真实调用点、安装身份、实际 writer、离线重读和受影响回归，与这一边界一致。其后应优先完成最小纵向样本中的未证项；不建议再为本次评审扩大设计合同。

## 范围与方法

- 完整阅读上述两份设计/测试文档；未读取本轮其他 reviewer 报告。
- 只读核对 NVIDIA 自动 scope、counter/anchor lowering、最终对象 counter 映射，以及 GCU 物理 writer、Ascend late observer/source timeline 的相关实现。
- 未连接服务器，未 import 产品、编译或运行产品/设备/浏览器测试；未修改设计或产品。
- 下述源码只用于判断接入路径是否具体、设计是否错误依赖某个原语；当前实现缺口不直接判成架构不可能。

## 确认问题

### C1 — P3：仍有无历史标签的重复“当前状态”，容易混淆 producer 原语与完整资格

位置：设计 §0.3（第 51 行附近）与 §8.10 首段（第 352 行）。

§0.3 已区分已提交的 Ascend paired producer/runtime-K 数学/raw/guard，与尚未完成回归和交付的默认 collector；§8.10 首段仍写“Ascend 新时间 producer 仍待完成”。后一表述没有像 §8.8/§8.9 那样标注历史检查点，单独阅读时不能确定是 producer 尚不存在，还是其完整时间资格未完成。这是工程状态导航的歧义，**不是两个规范合同互相排斥，也不阻止实施**。

最小文字修复：将 §8.10 首段中从“当前 NVIDIA 与 GCU……”开始的重复状态句替换为：

> 当前已提交、在研及未通过项统一见 §0.3 与 `timeline_impl_record.md`；本节规定适配边界，不另列当前支持状态。实际入口与公共 raw 合同分别见 `timeline_runtime.md`、`timeline_events.md`。

无需新增状态文件、接口或验收项。

## 编译侧关键判断

### 1. 普通无标记 kernel：设计可落地，自动源标记不等于要求用户改 kernel

设计 §0.1/§0.4、§3、§8.1/§8.14 将用户观测意图、后端实际 site、最终区域资格分开，允许 compiler hook 插入内部 carrier/marker 和隐藏参数。公开输入不需要用户提供 scope/site/SSA/ABI；内部编译器自动标记与此不矛盾。

只读依据：

- `Profiler/Dialect/lib/ProtonToProtonGPU/AutomaticScopes.cpp:139` 起按真实编译元数据选择 statement/data/control 候选；第 237–284 行处理数据操作与 cp.async 机制边界；第 389–408 行自动插入 start/end `RecordOp`。这说明已有通用接入点，不需要逐算子手写 probe。
- `Profiler/Dialect/lib/ProtonGPUToLLVM/PatternProtonGPUOpToLLVM.cpp:162` 起处理实际依赖、site/phase marker 与 target counter lowering。
- `Profiler/llvm/AscendLateObserver.cpp:503` 起使用真实 source carrier，收集非空 lowered block fragment；第 569–585 行生成 paired 时间记录和具体 manifest，并明确 `boundary_status=unverified`。

这些代码不能证明默认入口、所有合法 lowering、循环 body occurrence、source M:N 或完整资格已通过。新增 §0.4 对固定 actor 数量、auto-blockification、多函数范围要求如实登记，并禁止算子白名单；测试 §0.1 第 29–30 行把不同源码、实际布局/主体和未覆盖合法范围纳入检查，已给出正确的失败出口。无需为“无需用户标记”增加另一套前端语言或统一硬件 IR。

### 2. 边界证明：要求足够具体，没有要求任意机器码形式化证明

设计 §4、§8.11、§8.14 已明确：memory clobber、volatile、noinline、正 duration 和 counter PC 映射均不独立授予源区域资格；边界收据定位 binary/function/section、读钟位置、区域指令/基本块集合、控制路径和约束生效层。公共 validator 核绑定，后端核有限支持模式，陌生形态保未证。测试 P03、§8.6、§8.9 有普通 runtime-K 数学、最终对象、错误范围与缺字段负例对应。这是一条可执行的取证链，而非要求公共 exporter 证明任意 ISA。

只读依据尤其支持保留这一门：

- `Profiler/Dialect/lib/ProtonGPUToLLVM/ProtonNvidiaGPUToLLVM/TargetInfo.cpp:53` 明确区分 LLVM inputs 与机器寄存器消费；第 79–127 行建立 noinline helper/call，第 130–139 行给出 anchor lowering。不能从这些代码本身推导全部机器边界已成立。
- `Profiler/python/flagtree_profiler/timeline_nvidia_machine.py:352` 输出 `counter_mapping_complete_region_unverified`，第 360 行仍为 `region_boundaries_verified=False`。当前 counter 映射没有被设计误当成边界证明。
- Ascend manifest 位于 `post_actor_lowering_pre_scalar_optimization`（`AscendLateObserver.cpp:1111`），并在第 1124 行保留未证边界；后续优化仍须按设计核实。

**R1 — P1 级放行风险，尚非确认设计阻碍：** 某后端的自动边界 lowering 能否在最终对象中覆盖实际 live-in/live-out、循环和路径，并保持所声明的 observer 语义，当前本地静态阅读无法证明。尤其不能将调用实际保留下来直接解释成源操作或异步完成已经被包住。

最小下一动作：只执行原有 P03/P01 的普通依赖循环与实际异步样本，保存 ordinary/稀疏/默认的最终对象与已有收据字段；不能闭合的 site 维持未证，修通用 lowering。**设计已包含该动作，不建议再加新合同或要求设备生成并不存在的优化形态。**

### 3. 扰动检查：可操作，结论范围是插桩程序

设计 §8.12 第 457 行要求每个调度变体固定 ordinary 配置、输入、grid、数学和机制，仅改变观测密度，并预登记 commit/group/wait、消费前等待、允许 in-flight 的组和 compute 关系；测试 §0 第 14 行、§5/C1/C2 与 §8.2/P03 对应。这个判定比“指令数相同”具体，也没有强求字节相同或零开销。

设计 §10 明确默认时间属于插桩程序。ordinary/sparse/default 的静态依赖和阶段关系检查可判断是否还具备原流水结构；它不能单独证明真实硬件重叠或无扰动运行，文档也未这样承诺。NVIDIA 暂缓性能认证与仍需时序功能/结构证据的边界没有冲突。

**R2 — P1 级放行风险，尚非确认设计阻碍：** logger/call/新增依赖可能改变实际流水和资源分配，已有对象结构或 timer 原语成功都不能替代三方对照。最小动作就是既有三方对照；失败优先改通用插入点/选择策略，不能加入完成 barrier，不能重命名插桩产生的阶段为原流水。无需本轮追加吞吐或开销比认证。

## 三后端与后续芯片

| 后端/范围 | 设计上可复用的具体路径 | 仍须实际证明的关键事实 | 本次判断 |
| --- | --- | --- | --- |
| NVIDIA | 自动 scopes、target counter lowering、实际对象 counter 映射、公共 owner/消费链 | 真正源区域边界、ordinary 流水保持、async 完整覆盖、物理复用与所需时钟比较 | 工程路径具体；源码不能授予完整 P01 |
| Enflame C200 | 原自动 interval 与 timer 接入、后端物理 writer/decoder、公共 owner/消费链 | 最终对象边界、真实 work-item writer/payload、guard/发布、尺度/误差和真实异步机制 | 不能由 SDK timer 名称或旧 interval 成功推出全部成立；未发现设计要求它伪装成 CUDA |
| Ascend 910B | source carrier→late observer、paired producer、后端 actor/布局、公共消费链 | scalar optimization 后边界、cache-line/commit 可见性、实际时钟尺度与比较、set/wait/复用动态关联及通用 lowering 范围 | raw/producer 与 clock/boundary/async 被正确分级；新 timeline 协议不能继承旧 census 的通过票 |
| 后续型号 | 五个可替换部件、manifest/canonical/owner 交接合同 | 逐项复用条件、目标/toolchain/runtime、getter/epoch、发布和机制证据；必要时公共版本扩展 | 适配工作包合理；没有第四设备时只可评价现有三后端的实际复用，不能证明额外型号可行或给固定工期 |

GCU 的 `Debugger/lib/Instrumentation/Passes.cpp:3066` 起明确区分 work-item 完整向量和 sole-writer，且注释要求核实际 ownership/raw；Ascend 的片段边界仍显式未证。两者都说明必须按设备对象和 raw 取证，不能凭“架构相似”授予资格。本次不掌握新的硬件证据，因此不把某家 SDK 未验证的异步、尺度或边界称为“硬件不能实现”。

**R3 — P1 级三后端交付风险，尚非确认硬限制：** 三个必达后端是否都能在普通合法 kernel 上取得完整两代 buffer/flag 复用、对应动态关联及所需时钟比较，必须先通过设计 §8.5/§8.14 和测试 P01/P07 的最小样本。若未取得，应继续区分实现缺失、证据未齐和已实证 SDK/环境限制；后者才形成可报告的硬阻碍。当前设计已要求保最小复现并停止扩量，没有用 partial 绕过该门。

## 过度设计与合同一致性

本轮新增工作包未要求五套类、插件平台、通用 ISA、统一物理布局、零公共 diff 或第四设备；源 M:N 与 actual actor 保留了后端事实。manifest/canonical 是交接数据，公共 owner/validator/exporter 是共享行为，不与“两个真实调用者再抽取”冲突。

版本、输入闭包、派生 revision、原件先留存和有界锁属于已有离线重导/失败恢复合同；它们不应阻塞 A 的 writer 原语开发，但 B/C 的实际链必须逐步落实相关身份和留存。文档已给阶段边界，未发现新增 §0.4 把所有恢复机制变成首次 raw 的先决条件。

测试 §0.1 复用已有 P/E，不增加数学数量；设备正例、旧 raw 重读、合成 fixture 和最终代码审阅分别处理。普通合法输入 profile 失败保留为产品缺口，与陌生形态不授边界资格一致：可以诊断 partial，却不能通过缩资格分母来宣称完整交付。

设计文本的主要维护负担是 §0、§8.9–§8.14 与多张测试索引的重复。除 C1 的状态措辞外，此轮未确认影响实施的冲突；建议后续维护只改权威合同并保索引链接，避免再重复扩写。

## 本轮处置建议

1. 设计可继续实施；C1 是低优先级的单段文字澄清。
2. R1–R3 使用现有最小纵向样本和原件收据解决，未取证前保持未验证；不新增矩阵、第四设备或抽象层。
3. 本报告不构成任何后端的 raw/clock/boundary/async/Perfetto/独立数学/最终代码审阅通过结果。
