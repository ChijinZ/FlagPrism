# Round 3 R1：编译、优化边界与紧凑采集独立设计评审

## 结论

**有条件可实施。** 这份设计有一条可以落到现有编译 hook、后端 lowering、隐藏启动参数和公共导出器上的工程路径；没有发现必须推翻其公共模型的已确认 blocker 或 major。条件是三个后端分别完成 P01，尤其是最终机器边界、紧凑写址 ABI、真实异步机制闭合和目标时钟证明。此结论是静态设计合理性判断，**不是设备验证通过、实现完成或最终代码验收**。

设计主动区分 source intent 和优化后 execution manifest、observer elapsed 和 engine busy、逻辑组关系和物理 buffer generation，允许后端物理记录布局不同。这样的边界合理；不能再简化成“给现有 scope 两端加 timer，然后换 exporter”。§8.9 的紧凑 slot 与 storage 资格要求也正面解决了旧 full-grid writer 与小 buffer 不兼容的问题。

## 输入冻结和独立性

- 仓库只读核对的 HEAD：`34b04624098b99b2004f9b0e9cf1c602db5509cf`，与 `round3/INPUT.json` baseline 一致。
- 完整逐段阅读三个指定文档；实际 SHA256 与 INPUT 完全一致：
  - `Profiler/docs/timeline_design.md`：`dc26b5fb008bea5e608bb13b19ee08da1037b7fa02a38a4dcef041bb8e3c79f1`
  - `Profiler/docs/timeline_testing.md`：`ab727c20da1e2907d8be77302850bc293407b15e212291edba35e58224b6cb87`
  - `integration/plans/timeline/goal_prompt.md`：`51db449f2898ad695f8557a3d83459cf476c57cec27198743ba481193e12a054`
- 未阅读 peer 报告、旧评审或其处置结论。未执行 import、测试、构建、SSH、浏览器或设备程序；未修改产品文件。
- 以下源码仅用于判断接入路径和旧 ABI 的实际形状；不以缺少目标实现作为设计缺陷。

## 已确认问题分级

| 分类 | 结论 |
| --- | --- |
| confirmed blocker | 无。未找到合同内在矛盾或静态可证明无法实施的必达项。 |
| confirmed major | 无。最终指令顺序、发布、clock/epoch 和异步闭合尚待证明，但设计已把它们列为硬门，而非默认为成立。 |
| confirmed minor | 无必须修改设计文档的正确性问题。下面列出实现前应具体化的假设和实验；不将未验证假设升级成 confirmed defect。 |

## 编译与边界评估

### 1. 早期源区域和最终执行区域的职责已经分开

设计 §4（66–70 行）、§8.1（146 行）、§8.6（202–210 行）及测试 P03、§8.2 对应要求是必要且一致的：源区域提供意图和导航，实际 anchors、M:N origin、控制路径、循环和消除状态由优化后 manifest 交付。fused 多 origin 不复制 duration 的限制可防止人为满足“两区域”门槛。

只读源码可见 NVIDIA `hooks/instrumentation.py` 的 `ttgpuir_complete` 自动 scopes 接口，以及 `AutomaticScopes.cpp` 在候选 op 前后插 `RecordOp` 的现有路径。它们证明有可复用编译入口，却不证明后续 LLVM/机器调度保住了该 op 的边界。Ascend `AscendLateObserver.cpp` 自己报告 `post_actor_lowering_pre_scalar_optimization`；GCU `Passes.cpp` 的 getter 仍经 SDK 外部调用和后续编译。因此三者都需要设计明确要求的最终产物证据。

**待验证假设 A1：每后端存在能形成有用粗粒度区域的合法边界约束。** 触发场景是纯算术跨 timer 调度、load 延迟兑现、循环读钟被提升、异步操作只提交而未完成。仅有 side-effecting timer/logger 或正 duration 不足以闭合这个假设。设计 §4 已明确这一点，无需把它改写成“volatile 即足够”。

最小实验：每后端只选一个普通数学 kernel，含 device 输入控制的有依赖算术循环，K=3/7/11；另保一个 load→compute→store 区域。保存 ordinary 和 instrumented 的优化后 IR、最终可审计对象及 binary SHA，逐 anchor 标出 timer、被声明区域及其输出依赖。对同一 binary 的三个 K 捕获，检查真实 loop occurrence、数值/原副作用、begin 支配与 end 所在路径；排除新增 completion barrier。若某细边界不可保住，选择实际可证明的更粗区域并更新 manifest，不能继续沿用原细 source stage 名称。无法形成两个有意义区域时，P01 不放行。

建议在实现冻结时为每种 anchor 给一个小表：约束在哪层建立、哪些后续 pass 可能改变它、最终证据如何绑定 binary。最终对象人工审计可支撑开发样本；产品不能把这份样本的顺序证明无条件继承给别的 specialization。

### 2. 控制流与异步边界可表达，但不能靠记录序号代替机制状态

§8.2 的 operation/group/wait 集合模型、§8.9 的机制闭合和测试 P07/§8.4 相互吻合。部分 wait、commit batching、多消费者、丢 commit 后不平移 generation 都有对应规则。逻辑 group ordinal 不等于 loop iteration 或物理 buffer generation，设计也已经禁止这种替代。

**待验证假设 A2：目标普通 lowering 暴露可识别且闭合的实际机制。** 具体触发是软件流水的 prologue/steady-state/drain、自动拆分 observer、opaque asm/外部调用带来的未建模状态变更。不能从普通 GEMM 出现若干 async 指令推导“所有动态边已知”。

最小实验：每后端从 D04/D06 选一个 ordinary 编译已证实异步的合法配置，执行至少三轮真实 tile 生命周期。逐条列最终对象中的机制状态变更及其 manifest 对应，保 submit→commit→partial/full wait 的覆盖集合和 raw 引用。若真实机制只有逻辑组证据，就按逻辑组命名；另选确有来源的物理复用路径满足需要 buffer/flag 复用的案例。用一个丢 commit 的受控 raw/manifest 负例证明后续边不会整体错代；负例不冒称设备执行。只有 operation 集合、clock 条件和 completion 语义都闭合的边获得 verified。

## 紧凑选择 ABI 的可行性

设计 §8.7（221–240 行）和 §8.9（265、276 行）把 plan 与实际 launch grid 分开，要求 admission 先于分配和设备副作用；测试 §8.4 明确旧 storage/错误版本的启动前拒绝。这是可实施的小合同，不需要统一三后端的物理布局。

实际旧 NVIDIA `PatternProtonGPUOpToLLVM.cpp` 的 global scratch lowering 使用 `linear CTA id × per-CTA allocation size`；`Utility.cpp` 的 program predicate 也是基于物理 CTA 线性化。`hooks/instrumentation.py` 旧 census preallocation 按 grid×num_ctas×scratch_size 计算。此事实说明只缩小 host allocator 会不安全，但**它不是本设计的缺陷**：设计已要求新 compact writer/storage ABI 并拒绝旧 binary 混配。

**待验证假设 A3：新 launch 和 compiler 能共同提供紧凑寻址，且选择谓词不破坏原执行组织。** 具体风险是首末 program 仍用旧全 grid offset、grid=1 重复占两个 slot、非选 program 的 header/cursor 写入、物理 CTA 与逻辑 program 混淆，以及不正确地将含原同步/集体操作的用户区域整体包进选择分支。

最小实验（逐后端）：用同一可复用 specialization 运行 grid=(1,1,1)、(7,1,1)、(3,5,1)，再运行一个实际合法 tail。launch 冻结真实坐标→slot 表；单 program 为一个 slot，其余只收首末两个。保实际 allocation 字节数、header/padding、writer 地址公式、raw canary、logger/selection ABI 身份、所有导出事件的真实 program 坐标。至少一个 grid 有五个以上未选 program，检查它们没有修改选中 slot，数值和合法 side-effect oracle 仍正确；独立核最终代码中受选择谓词保护的是观测动作。旧 full-grid binary 与 compact owner 故意混配必须在启动前失败。cluster/多 CTA 不支持则早拒绝且恢复；支持则另验 logical program→实际 writer 的映射。宽度乘法和索引上界在 admission 前检查，不以设备端截断处理超界。

实现不必把首末坐标编译进每个 binary。可用冻结的 runtime selection 参数和最多两 slot 的容量，或使用经版本化、对新 grid 正确的其它实现；关键是 manifest 能声明这种寻址能力，owner 保存本次 selection，缓存不把旧 grid 的事实作为当前事实。选中 program 内的多 observer 仍须单独满足主体/写者/容量合同。

## 整体真实可行性和余下假设

**待验证假设 A4：三个目标至少各有一条满足尺度、epoch、发布和异步门的纵向链。** 设计 §8.5/P01 提前验证这点是正确的。NVIDIA 现有 target getter 支持选择 `%globaltimer`，源码不能据此证明实际设备频率、epoch 和最终调度；GCU 现有 SDK `global_timer` 调用不能自行证明跨 work-item epoch；Ascend 的 SYS_CNT 读和 actor ID 也不能自行证明动态 logger 发布或跨 actor 比较。

最小实验应直接复用 P01 的数学样本与 A1/A2/A3，避免四套互不关联的空 kernel：绑定实际 target/compiler/SDK、getter 指令、位宽、原 tick 与 scale/epoch 来源，独立核发布/提交和 loss，再进入公共 decode→clock→Perfetto。若只有本地域可用，保合法 partial；未证跨域的 edge 不画时间箭头，P01 不通过。先把这条链闭合再展开 24 ordinary/72 profile 矩阵，既符合合同也能防止大规模资格耗费掩盖核心未知。

执行合同允许修改通用 compiler/SDK pass、隐藏 ABI、timer 和 logger，因此这里不是被限定为纯 Python 改造的不可能任务。代价主要是三种后端的最终 lowering/发布/epoch 证据，公共接口抽象不会消除它。对于 SDK 不开放足够晚的插桩点或无法取得目标时钟尺度，正确结果是明确的最小阻碍与尚未完成，不是虚构 timeline，也不是静态评审就宣布硬件不可能。

## 过度设计与遗漏

- **没有发现必需删除的过度设计。** `probe/plan/prepare/finish/decode/mechanism` 是职责而非强制六套类；允许组合现有 hook、三种物理 ABI、公共小版本冻结后再演化，避免了空插件框架。多消费者/部分 wait/unknown 状态服务真实机制，不是装饰性泛化。
- **实现前要补具体值，尚不构成设计缺陷：** 新 compact header/selection 字段、logger/storage version、每 observer 预算公式、源→执行 anchor 的后续 pass 约束与 binary 绑定方法。设计已经把这些留给首条真实纵向链冻结，不能在该阶段后继续用“后端决定”逃避可执行 schema。
- **控制证据维护成本：** 一份最终对象/manifest/raw owner 证据可同时服务 P01/P03/P05/P07/P10 和相应 E 项；不必为每项复制全套实验和第二份状态表。独立资格仍保持独立，不能拿开发纵向样本替代。
- **需保持的解释界线：** 优化后保留下来的 observer 区间可以是实际有用数据，不要求精确源指令 latency；真实 engine busy 是增强。采样未覆盖、损失、不支持和异常必须分列。设计对这些界线已足够明确。

## 阅读范围与未覆盖范围

完整阅读：三份冻结文档（design 313 行、testing 205 行、goal 156 行）及 round3 INPUT。

针对性源码阅读：

- `Profiler/python/flagtree_profiler/hooks/instrumentation.py`：preallocation、compiler hook 注册、scope/source/raw 相关检索和片段。
- `Profiler/Dialect/lib/ProtonToProtonGPU/AutomaticScopes.cpp`：候选/控制区域选择、RecordOp 和 partition observer 片段。
- `Profiler/Dialect/lib/ProtonGPUToLLVM/ProtonNvidiaGPUToLLVM/TargetInfo.cpp`：完整 getter 文件。
- `Profiler/Dialect/lib/ProtonGPUToLLVM/PatternProtonGPUOpToLLVM.cpp`：timer/version 检索、scratch lowering。
- `Profiler/Dialect/lib/ProtonGPUToLLVM/AllocateProtonGlobalScratchBuffer.cpp`：完整分配 pass。
- `Profiler/Dialect/lib/ProtonGPUToLLVM/Utility.cpp`：segment、CTA 线性化、selection 及 ring lowering 开头。
- `Debugger/lib/Instrumentation/Passes.cpp`：dynamic writer、clock lowering 及 census/timeline 相关检索和片段。
- `Profiler/python/flagtree_profiler/ascend_compiler.py`：prepare 前半段及相关检索；`ascend_driver.py` 为相关入口检索。
- `Profiler/llvm/AscendLateObserver.cpp`：clock/layout/actor/phase 相关检索和局部上下文。
- `Profiler/python/flagtree_profiler/observations_nvidia.py`：旧 decoder/clock ABI 相关检索。

未覆盖：完整产品实现审计、SDK 私有源码、安装原件、实际机器对象、设备 raw 原件、clock 校准结果、Perfetto SQL/UI、并发故障与完整矩阵执行。文档中的历史证据表只按其声明理解，未据此填入任何设备通过结论。
