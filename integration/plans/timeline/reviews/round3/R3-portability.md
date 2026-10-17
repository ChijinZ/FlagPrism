# R3：适配边界、Perfetto 与阶段放行独立设计评审

结论：**有条件可实施**。三后端共用观测语义、身份、时钟算术、完整性验证和导出，把合法插桩点、物理记录协议、目标时钟证明和异步机制映射留在后端，这个划分合理。文档给出了能逐步推进且能明确停下的工程路线，没有发现必须推倒架构的设计阻碍。条件是各后端用真实纵向链闭合时间尺度、最终编译边界、安全发布和一个合法动态异步机制；这些目前只能列为待验证假设，不能从设计或已有原语推出设备可行性已通过。

本报告是设计评审，不是实现验收、最终代码走查或设备通过证明。未把缺实现直接判成设计错误。

## 1. 输入与独立性

完整阅读以下三个文件；逐字节 SHA-256 与 `reviews/round3/INPUT.json` 相符：

| 文件 | SHA-256 |
| --- | --- |
| `Profiler/docs/timeline_design.md`（313 行） | `dc26b5fb008bea5e608bb13b19ee08da1037b7fa02a38a4dcef041bb8e3c79f1` |
| `Profiler/docs/timeline_testing.md`（205 行） | `ab727c20da1e2907d8be77302850bc293407b15e212291edba35e58224b6cb87` |
| `integration/plans/timeline/goal_prompt.md`（156 行） | `51db449f2898ad695f8557a3d83459cf476c57cec27198743ba481193e12a054` |

清单 baseline 为 `34b04624098b99b2004f9b0e9cf1c602db5509cf`；评审对象是上述锁定文档，而非把工作区当前状态当成已完成产品。未阅读 peer 报告、旧轮评审或处置意见。未 import、运行测试、连接服务器或访问设备；未修改产品文件。

## 2. Confirmed findings

**Blocker：无。Major：无。Minor：1 项。** 下述文字歧义不证明异步设计不可行，也不豁免已有两轮生命周期验证。

### MIN-01：异步案例的物理缓冲代际门槛与逻辑组例外应在主验收条款直接对齐

- **位置**：testing §5 第 3、5 项（68–70 行）、P07（146 行），对照 testing §8.4 身份与证据层次（196 行）和 design §7（112 行）。
- **已确认问题**：P07 的输入明确写“每后端真实异步样本至少两轮 buffer/flag 复用”，而后面的针对性条款允许没有物理 buffer 信息的逻辑 group 关联，且仅对“声称 buffer 复用”的案例要求两轮物理代际证据。逻辑组记录本身不能证明物理 buffer 复用；两个条款没有直接说明“只证实逻辑组生命周期”的案例是否已满足每后端最终异步门槛。
- **触发**：某后端能完整观测多轮 submit/commit/partial-wait，具备可比时钟和动态逻辑组关联，但无法给出物理 buffer identity。实现者可能按 §8.4 认为已通过，验收者按 P07 要求另一个 buffer/flag 案例。
- **修正**：在 §5/P07 原条款给出唯一规则，并引用 design §7：若逻辑组案例可满足门槛，明确要求至少两轮真实 operation/group 生命周期和首轮/稳定期/drain，物理 buffer/flag 复用声明另须其代际证明；若本轮要求每后端额外证明物理复用，直接写明该要求，说明 §8.4 的逻辑例外只允许保留 partial 数据。两种选择都能实现，不能靠填造 buffer/generation 消除歧义。
- **最小核验**：资格冻结前用一份“完整逻辑组、unknown physical buffer”的注册表样例，由规则明确得出最终门槛通过或不通过，不留到设备全矩阵后裁决。

## 3. 新增芯片成本与公共/后端边界

design §8.1–8.9 的边界足够具体，可以指导实现；不是只写一个 adapter 名称。尤其值得保留的约束是：

- 源区域是公共选择意图，实际 anchors、主体和 M:N manifest 来自优化后的后端结构；融合不复制 duration 来凑区域数。
- 不强迫三种设备采用同一物理 ABI；后端负责 padding、发布、位宽和 decoder，公共层检查标准事件及其完整 raw 引用。这能容纳 Ascend cache-line 可见性要求。
- public validator 不解析厂商指令补语义，后端也不能用 `verified=true` 绕过公共身份、引用、generation 和时钟验证。
- operation/group/wait 模型允许批量提交、部分等待和多消费者；逻辑 program、observer、operation、resource 分开，避免把新执行模型强塞进 warp/SM 树。
- target/compiler/SDK/plugin 的编译依赖在 cache lookup 前确定，capture 的 epoch 单独绑定；紧凑 allocator 需匹配 storage/logger ABI，不能把旧 full-grid binary 配小 buffer。

新增芯片的主要成本仍在编译接入、合法顺序约束、logger/发布协议、实际拓扑、时间尺度及异步闭合证明，公共 exporter 复用不能消除这些成本。design 242、270、278 行已明确这一点。仅对同执行模型、同机制且证据适用条件匹配的目标复用后端实现是合理预期；“同品牌”不能继承时钟/同步结论。没有适配第四架构，就不能估算接入天数或宣布第四架构可行，当前文档没有作这种过度承诺。

最小六个概念动作可以用现有对象和调用点组合，不要求六个新类或独立插件包，这避免了无调用者框架。真实三后端 diff 分类、公共版本变化理由和共同回归，比 LOC 或 adapter 数量更适合作为可移植性证据。

## 4. Perfetto 与验收合理性

标准 protobuf、实际 Trace Processor、逐事件 raw→ns→slice 对照，以及真实 UI 操作分三层验证，能分别发现编码可读但单位错误、语义错误和实际不可读的问题。要求合理，且 UI 只抽每后端至少六份，SQL 覆盖正常资格 trace，成本没有被无条件扩大到每份 trace 人工截图。

时间域未连通时分文件、未知频率不进入 ns、端点不确定性决定先后资格、observer overlap 不冒充 engine overlap，都与可解释时间线目标一致。独立 in-flight 操作不能用错误嵌套 B/E，稳定 track/flow ID 要查 collision，源码从详情和 bundle 页面定位；这些要求足以指导公共 exporter，而不必预先承诺特定 Perfetto SQL 字段或浏览器控件。

验收矩阵较重，但它同时承担三后端通用性、普通输入而非手工 marker、同 binary 的 runtime 重复和冷暖 cache 隔离验证；不是单纯重复计时。P/E 复用和 §8.2–8.4“不再扩大独立数学数量”的规定应落实到一个注册表，避免同一证据被不同章节机械重跑。CPU fixture 只补合同负例，设备正例不可替代，这个界线清晰。

两项实施注意不列为 confirmed defect：第一，SQL 应按导出事件种类核对规范化集合，不能对正常 instant/completion 强套正 duration；第二，最终 UI 冻结版本应尽早用一份真实 trace 试一次，防止最后才发现 source/clock/loss args 过长难读。现有分型和 UI 门槛已允许正确实现这两点。

## 5. 阶段放行是否可操作

design §8.8–8.9 与 testing 183、197 行已经区分：

| 阶段 | 足以放行的工作 | 不代表什么 |
| --- | --- | --- |
| 原语/基础链开发 | 普通区域、安全 owner、时间尺度、公共导出逐步实现，其他后端独立调查 | 不是 P01，不要求一开始所有事实全知 |
| 第一条真实链与小合同冻结 | §8.6 的字段、基数、未知版本处理及真实小样本可定位 | 不是固定永不变的插件 API；真实新公共事实可版本化修订 |
| 该后端 P01 | 普通数学、至少两源区间、实际 getter/单位、安全记录、动态异步、目标时钟、实际 Trace Processor | 只允许进入该后端最终资格，不能代替独立数学/UI |
| 最终交付 | 三后端完整矩阵、P/E、UI、安装/回归、受控案例、三份最终代码审阅与 Git/生命周期收尾 | 不能由局部构建、CPU 算术或本次设计评审代签 |

这允许异步修复与普通区间开发独立推进，也允许先调查第二/第三后端原语，不存在必须先过最终验收才能实现的循环依赖。P01 保留异步硬门槛能较早发现设备路线失败，不必等独立资格全部跑完。某后端暂阻时继续其他不依赖工作也已写明。

建议工程记录直接采用“后端×阶段”的结果表，每格只填写证据 ID、依赖版本和未闭合条件，合同冻结另外记版本；这是执行组织建议，不是新增门槛。普通输入 eligibility、目标能力、本次 plan/outcome 三者不得互相覆盖，应在同一注册表中分别可见。

## 6. 待设备验证的假设与最小实验

以下均未在本次评审运行；不能称已通过。

| 假设 | 最小设备实验与保留证据 | 失败时的含义 |
| --- | --- | --- |
| 三后端都有可解释且不越界的真实区间 | 一个有依赖纯算术 runtime loop 加 load/compute/store 区域；普通/插桩最终 IR/ISA 对照、两个源区间、至少三 occurrence、raw offsets | volatile 或正时长本身不够；需通用 lowering 修复或缩为诚实 partial，不能交付完整门槛 |
| NVIDIA 新记录/计时器链匹配实际 binary | 64-bit v2 logger→raw→decoder，两个 program 的 timer/epoch 证据；实际机器 getter 与对象 SHA | decoder 支持 64 位不证明生产者已写 64 位，也不证明跨 SM epoch |
| GCU timer 具可用尺度和误差 | 独立计时源校准与留出点，覆盖实际测量窗口；记录 actual getter、位宽、频率区间和同域范围 | 原语约 1 ns/tick 界限不可直接变成精确 1 ns 或共享 epoch |
| Ascend 新动态记录发布正确且 actors 可比较 | 两个真实 actor 的新 timeline ABI/padding/commit，在实际完成条件后读全 payload，另核 epoch/频率与顺序 | census v3 可见性通过不能继承；同频不能推出同 epoch |
| 每后端都有普通数学生成的合法动态异步结构 | 从 D04/D06 或预登记替补选一份，普通编译先证实真实机制；至少两轮，核全部 submit/commit/wait 状态变更与动态覆盖，留原 IR/ISA/SDK 来源 | 没生成异步应保留事实并另登记合法候选；观测失败不能改 eligibility |
| 首末选择可紧凑、安全且调用隔离 | 同 specialization 改合法 grid，含未选 program；核 slot/program 表、allocation canary、真实物理字节；累计 pending 越预算在 launch 前失败 | 不允许大分配后过滤，不允许旧 ABI 配紧凑存储，不允许强同步清队列冒充预算控制 |
| owner 可在公开支持范围安全存活 | 对支持的并发路径交错调用；提交前/在途/完成后故障分别注入，核完成句柄与释放时机；不支持组合启动前拒绝 | 超时不能当完成；隔离失败资源可 session 失败，写者结束清理后新 session 应恢复 |
| 一个共同导出器实际保留三种语义 | 每后端第一份真实 pftrace 做 Trace Processor 对照，并选一次 UI 点击 source/clock/raw/flow | 可解 protobuf 不足；应在扩大矩阵前修公共映射 |

上述实验复用 P01/P03/P05/P07/P10 与既有 E 场景即可，不建议再建第四套资格集合。

## 7. 过度设计与遗漏

没有确认需要删除的公共模型：完整 raw 引用、带条件时钟证明、operation/group/wait、owner 生命周期都对应明确错误风险。应避免把“概念动作”机械实现成新插件框架，也不应为尚无真实设备需求的角色/机制建额外抽象。

文档重复规范较多：适配边界在 §8.1–8.9，测试在 §8.1–8.4，执行合同再复述。当前总体一致，但 MIN-01 表明后续容易发生门槛漂移。建议以测试注册表和冻结 schema 承担执行细节，文档后续修改按同一规范定位同步；不建议再增加一套验收清单。

未发现缺失到足以阻止开工的设计项。尚待落地的 schema 必填/可空、引用基数、未知语义、设备支持表、clock 误差有效范围和具体完结句柄，已分别由 §8.6、小合同冻结及 P/E 规定；设计评审不应要求它们现在全部作为空实现存在。真正风险在后端编译/SDK 能否提供这些事实，必须由上表小实验决定。

## 8. 阅读范围与限制

除三份完整文档和 round3 INPUT 外，只为核现有接入形态读取了 `timeline_nvidia.py` 全文（物理 decoder），`timeline_nvidia_async.py` 前 165 行（逻辑事实与身份/完整性边界），并对 `observations.py`、`hooks/instrumentation.py`、`observations_ascend.py` 作符号/入口检索。源码只用于确认设计确有可衔接的 decoder、机制模型和 hook；没有据此签署实现正确性。未细读全部 C++/SDK/pass、GCU 生产者、完整 runtime 和 exporter，没有检查服务器安装、真实原始产物、Perfetto SQL/UI 或设备时钟。

本次仅新增此报告。设计可继续分阶段实现；最终交付仍须以三后端真实证据满足原合同。
