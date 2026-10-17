# R2 独立设计评审：时钟、记录、异步与生命周期

结论：**有条件合理，可以继续分段实现；不能据此认定三后端已具备完整设备可行性或验收通过。** 本次没有确认 blocker/major 级设计缺陷；确认一项 minor 级状态文档不一致。条件是维持现有 P01、P07、最终资格与 UI 门槛，并用当前三种真实设备闭合时钟、最终边界、发布和复用关联。不能由文档合同、CPU fixture 或 NVIDIA raw 路径推定其它后端已经可用。

## 评审身份、输入与限制

- 席位：独立 R2；agent `/root/design_feasibility_runtime`。
- 请求配置：`gpt-6.1-sol` / `xhigh`。本席上下文没有暴露 resolved serving 型号或实际推理配置，**实际 serving 未知**；不据请求值声称已确认实际型号。
- 时间：2026-10-17；读取时仓库分支 `detailed-profiler`，HEAD `dad8e7c98632ef7cbd2b4677d9c5101a517a88dc`。设计与验收含未提交修改，以下 SHA 才是本次输入身份。
- 完整阅读：`Profiler/docs/timeline_design.md`（347 行）、`timeline_testing.md`（224 行）、`timeline_runtime.md`、`timeline_events.md`、`integration/plans/timeline/goal_prompt.md`。
- 静态抽查：`timeline_clock.py`、`timeline_nvidia_async.py`、`timeline_cuda_runtime.py`，并查看 `timeline_runtime.py` 的状态/操作位置、`ascend_clock.py`、`cann_source_clock.py`、`observations_ascend.py`、`ascend_compiler.py`、Ascend late observer 的相关位置及 Enflame timer 接入 patch。这里只用源码判断接入路径与风险，没有开展当前代码验收。
- 未连接服务器，未运行产品 import、编译、oracle、测试或设备工作，未读其它评审报告；未修改产品、设计、验收、论文或 Study。仅写本报告。文档自述的设备结果没有被本席独立复验。
- 另只读核对 NVIDIA PTX 与 Perfetto 官方时钟文档；这些说明机制合同，不授予本机目标设备证据。

| 输入 | SHA-256 |
| --- | --- |
| `Profiler/docs/timeline_design.md` | `6f433840e0da7938e9201381d85c1a6bcaa785134fed9c69d382ff5d3de930f3` |
| `Profiler/docs/timeline_testing.md` | `456c3cc29588cbfd61754c345b6752bd9b29a740f42752108e6809384db3fdc2` |
| `Profiler/docs/timeline_runtime.md` | `316d2febcdc7439dd504f07109230b4095753f88d72ccda3b1a8f4d5e6d5d9a9` |
| `Profiler/docs/timeline_events.md` | `c41f6949d41f0f5596c358e1a4d0382edda091e2de66a51a1d31184a171527ee` |
| `integration/plans/timeline/goal_prompt.md` | `51db449f2898ad695f8557a3d83459cf476c57cec27198743ba481193e12a054` |

## Confirmed 设计／文档问题

### R2-M1 — minor：当前状态入口仍混用历史检查点和过时 API 说明

**位置：** 设计 L3、L35、L246–255、L280、L285；执行合同 `goal_prompt.md` L67；运行时说明 L3–20。

**触发与实际证据：** 从设计第一段或执行合同进入本轮工作时，会读到“当前工程边界见 §8.8”和“`--detail timeline` / `detail="timeline"` 尚未实现”。但 §8.8 自身明确限定为 `b3e4a7f` 历史检查点；本次设计 L35/L285 和 runtime L3–20 已说明 NVIDIA 有公开 raw 路径，状态为 `partial_clock_unverified`。这属于同一输入集的确定矛盾，不需要把设计当成完整实现来判断。

**影响：** 维护者可能重复实现已有入口、将历史 43-bit 状态当作最新记录布局，或选择错误的后续检查；并不推翻时钟/异步/owner 架构。

**建议：** 设计 L3 指向 runtime/events 的当前支持说明；执行合同 L67 同步为“NVIDIA 公开 raw 路径存在，三后端 ns/Perfetto 尚未完成”。按合同 L30 同步根入口与已跟踪快照并记录新 SHA。历史检查点保留历史身份，无需覆写为新实验结果。

**有限复核：** 比对这些状态描述和入口/快照字节即可；无需运行设备或重跑资格。

## 待实证风险与放行依据

这些是实现后必须回答的 verification gaps，**不是已确认设计缺陷**。文档已保留相应硬门，不建议通过降低门槛处置。

| 风险 | 为什么仍需实证 | 最小闭合证据／已有对应门 |
| --- | --- | --- |
| V1：比例、epoch 与有效窗口分别成立 | 设计 L92–108、L164、L176、L299–301 正确区分尺度、epoch、缓存与 capture；旧 getter 名称、频率或 CPU 算术仍无法证明实际目标的物理时钟。GCU 的有限比例界限也不能自动升级为精确 1 ns/tick 或共享 epoch | 每后端实际 getter/最终对象、有效位宽、独立时间窗口、比例与端点误差、reset/回绕条件；跨 observer 的证据范围单列。原点先相减再整数/有理数换算。P01/P06、E09、测试 L211；同域频率误差的共享项与独立读取误差应按实际模型处理 |
| V2：区域边界不越过最终优化与调度 | 有副作用 logger 或正 duration 不足以约束纯算术；“晚期”仍可能在 SDK 后续优化前。设计 L68 已明确最终对象核序及约束截止层，避免了错误保证，但三个编译链能否做到尚未知 | 普通／插桩最终 IR/ISA 对照，覆盖真实有依赖算术 loop、访存与原 wait；动态 occurrence 随 runtime 输入变化；无新增完成 barrier。P03、测试 L159–160；需要后端各自交证据 |
| V3：记录发布、写者粒度与缓存可见性 | 分区及 commit 字段只有在实际写者、存储顺序、padding 和最终 D2H 路径成立时才有效。Ascend 动态 v1 与 census v3 不能互相授予可见性；GCU 的实际 work-item 写者也不能凭 NVIDIA lane 模型假设 | 新 timeline layout 的实际 actor/work-item 写者证明，header/payload/commit/loss 一致，cache-line 独立性及 canary；完整完成后读取。故障与 overflow 下不产生完整伪记录。设计 L86/L158，P05、E04/E08/E12、测试 L160 |
| V4：逻辑组模型到真实 buffer/flag 复用仍有距离 | 设计 L112、L166–168、L274、L297 区分 group ordinal、iteration 与物理 generation；NVIDIA 当前逻辑 group 模块自身也明确不证明物理 buffer。选择代表 observer 时，还要证明它覆盖的实际 participant/control path，不能把一个观察者的记录外推到全部参与者 | 每后端至少两轮实际 buffer/flag 复用，包含首轮、steady state、drain；实际 slot/flag identity、generation 和提交／消费集合有来源。核机制闭合、predication/分歧及丢 commit 后失效范围；不能仅改 group 字段名过门。P07、E10、测试 L66–71/L146/L195–196 |
| V5：初始化、提交不确定与故障恢复的安全 owner | 设计 L229–240 已把 pending 总预算、完成证明、隔离和重导写清；真实 transport 还须覆盖“分配后初始化已提交写入、kernel 未成功提交”的阶段，不能以 Python 异常推断设备无写者。runtime L51–64 已提出这点 | 每个目标的 stream/SDK completion 范围、初始化与提交前后故障、query/record/D2H 失败、timeout 后同 handle 继续处理；在无完成证明时保留资源并标失败。支持的两 stream 交错提交不逐 launch 等待；不支持组合早拒绝。E03/E05、测试 L161/L174–181 |
| V6：可组合部件真的具有相容条件 | 新增 §8.10 明确 compiler/transport/decoder/clock/mechanism 组合，比整套继承更适合后续型号；但注册通过不能证明组合 ABI、机制规则和设备证据兼容 | 对三后端逐一追公开入口到实际部件；cache lookup 前绑定真实编译依赖，capture 单独绑定 epoch；错 ABI/rule/target 可提前发现时早拒绝，晚发现时不 verified。P02/P09/P10、测试 §8.5。共同消费者按 semantic 和时钟资格处理，不能按厂商补业务分支 |

NVIDIA 的 participant 粒度值得在 V4 中明确检查：PTX 的 `cp.async.commit_group` 按执行线程分组，`wait_group` 的覆盖与特定 group 集合有关；因此源操作／warp 代表记录需要实际 lowering 与参与者依据才能获得更强含义。[NVIDIA PTX：cp.async commit/wait](https://docs.nvidia.com/cuda/parallel-thread-execution/#data-movement-and-conversion-instructions-cp-async-commit-group) 这不否定设计使用 observer 或逻辑组；设计允许保留有限事实，完整资格另要求真实复用证据。

## 三后端落地判断

| 后端 | 本席的设计可行性判断 | 仍不能授予的结论 |
| --- | --- | --- |
| NVIDIA RTX PRO 6000 | **路径具体、可继续。** 公共 raw schema、按调用 owner 与 CUDA stream completion 的职责已有可静态定位的实现；ns 资格可作为独立派生层接入。PTX 对 globaltimer 的目标限制与设计相容，并未要求未来万能计时器。[PTX globaltimer](https://docs.nvidia.com/cuda/parallel-thread-execution/#special-registers-globaltimer-globaltimer-lo-globaltimer-hi) | 当前 raw 不能凭入口存在获得 ns/共享 epoch、最终指令边界或真实 buffer generation；既有逻辑组不单独完成 P07 |
| Enflame C200 | **有具体 timer 接入起点，核心异步可行性仍开放。** 静态 patch 绑定实际 `gcu300` SDK helper、46-bit 输出与未验证频率，说明可以沿实际工具链扩展；这也要求明确 C200 产品与实际 compiler target 的对应证据，而不是复制品牌结论 | 不能从 timer helper 或旧 interval 推出 ns 尺度、共同 epoch、最终边界、正确写者发布或真实 async token／复用。三者中这是需要优先闭合 P01 的明显风险之一 |
| Ascend 910B | **已有 SYS_CNT、actor 和 SDK handoff 的可复用起点，新增时间 producer 仍需实做。** 设计保留 AIC/AIV 与 MTE/compute/set/wait 事实，允许独立布局，没有强迫适用 CUDA 树 | 同频不能替代 actor epoch；动态 v1 不能借 census v3 通过；旧 checkpoint 不能直接升级成多个 elapsed 区间。需要最终 scalar/SDK 优化后边界、新日志发布和动态 flag/buffer generation |

设计 L190–192、L255、L303–312 与测试 P01 的分段放行是合适的：先验证每后端最小真实纵向链，再进入该后端最终资格。A/B 可以推进开发，但每后端 C 必须含真实异步／复用、所需时钟与 Trace Processor；GCU 或 Ascend 的关键能力未知时，不应先跑大量独立矩阵来积累无法解释的数据。Perfetto 的 clock graph 依赖真实 ClockSnapshot 关系，不能补出设备未提供的同步证据；设计 §6 与这一限制相容。[Perfetto clock synchronization](https://perfetto.dev/docs/concepts/clock-sync)

## 可选改进

1. 在第一条真实纵向链冻结小合同（设计 §8.6）时，为每种 mechanism 增一份简短规则表：状态变更、participant 粒度、wait 覆盖、复用代际、loss 后恢复锚点。可复用现有 manifest／证据索引，不新增一套日志。这会降低下一个 target 接入时误用逻辑组或代表 observer 的成本；无需扩大本轮资格数量。
2. 将设计 §8.7 的正常状态图配一张简短错误转移表，列 admission／初始化／可能提交／完成查询／D2H／decode／export 的 owner 动作。现有正文已经规定关键安全约束，图表只帮助未来 transport 实现者避免遗漏，不构成本轮 blocker。

本轮“以后新增芯片更容易”的合理承诺，是复用公共流程与消费者，并按真实 target 条件组合设备部件。设计 §8.10 与测试 §8.5 对这一点的约束适度；它们没有把新 SDK 的晚期 pass、隐藏 ABI、同步或 clock correlation 成本藏进一个 adapter 名称。三后端实证完成后可以声称复用边界经过三种实现检验；没有第四设备证据时仍不能承诺移植工期或新型号支持。
