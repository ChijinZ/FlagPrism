# R1 独立设计评审：编译接入、执行映射与适配可行性

结论：**有条件合理，可以按分阶段方案继续实现；尚不能据此承诺三后端完整目标一定能够闭合。** 本轮新增的组合边界和 A/B/C/D 放行顺序有实际工程落点，没有发现需要推翻公共模型的 blocker/major 设计缺陷。关键条件是各后端必须取得最终编译边界、真实异步复用与所需时钟证据；这些仍是实证门，不能由现有 raw 路径或文档合同推定通过。

## 评审身份、版本与范围

- 请求配置：`GPT-6.1-Sol / xhigh`；实际 serving 型号/推理配置未由当前工具暴露，**未知**。Agent：`/root/design_feasibility_compiler`。
- 类型：实现前的独立设计评审，不是代码验收、P01 通过声明或最终三个代码 reviewer 的替代。
- 仓库 HEAD：`dad8e7c98632ef7cbd2b4677d9c5101a517a88dc`；评审对象含未提交的设计 §8.10、验收 §8.5 及现状描述修改。
- 完整阅读 `timeline_design.md`（347 行）、`timeline_testing.md`（224 行），以及 `timeline_runtime.md`、`timeline_events.md`、`integration/plans/timeline/goal_prompt.md`。
- 静态参考 NVIDIA scope/pass/hook、raw/async mapper、公共 owner，GCU Debugger 自动插桩与编译 patch，Ascend compiler handoff 与 late observer。未读取其它评审报告；未连接服务器、import 产品、执行测试/编译或改产品/论文。

初审冻结字节：

| 文件 | SHA-256 |
| --- | --- |
| `Profiler/docs/timeline_design.md` | `6f433840e0da7938e9201381d85c1a6bcaa785134fed9c69d382ff5d3de930f3` |
| `Profiler/docs/timeline_testing.md` | `456c3cc29588cbfd61754c345b6752bd9b29a740f42752108e6809384db3fdc2` |
| `Profiler/docs/timeline_runtime.md` | `316d2febcdc7439dd504f07109230b4095753f88d72ccda3b1a8f4d5e6d5d9a9` |
| `Profiler/docs/timeline_events.md` | `c41f6949d41f0f5596c358e1a4d0382edda091e2de66a51a1d31184a171527ee` |
| `integration/plans/timeline/goal_prompt.md` | `51db449f2898ad695f8557a3d83459cf476c57cec27198743ba481193e12a054` |

以下文档行号均对应这些字节。

## Confirmed 设计/文档缺陷

### C1 · Minor：执行合同仍把已存在的公开 raw 入口称为尚未实现

- **位置**：`integration/plans/timeline/goal_prompt.md:67`；对照 `timeline_design.md:35`、`:285`，`timeline_runtime.md:3–20`。
- **触发**：实施者按合同判断当前接入起点时，会同时看到“timeline 入口尚未实现”和“已存在 NVIDIA-only、partial_clock_unverified 的公开路径”。
- **证据**：合同明确写 `--detail timeline / detail="timeline"` 尚未实现；设计和 runtime 则明确描述已实现的 raw 采集。静态源码 `Profiler/python/flagtree_profiler/hooks/timeline.py:90–119`、`:121–143` 存在实际 timeline hook、依赖指纹和 launch owner 接入，符合后者的有限现状描述。
- **影响**：会误导实施顺序和现状声明，属于文档状态冲突；不构成时间模型或适配接口的架构缺陷。
- **建议**：将合同改为“已有 NVIDIA raw 公开入口，完整三后端 ns/Perfetto 尚未实现”，同步根目录执行入口的同字节快照。无需因此运行设备矩阵。

未确认其它 blocker/major 设计缺陷。下面的问题属于尚待取得证据的工程风险，不把“尚未实现/尚未证明”写成设计错误。

## 关键待实证风险

### V1 · 高：最终计时边界仍是最大编译风险

设计 `timeline_design.md:68`、`:146`、`:202`、`:299` 已正确要求晚期 M:N manifest 和最终对象顺序，测试 `timeline_testing.md:142`、`:159` 也覆盖纯算术、访存、原 wait；这不是缺失要求。

静态接点确实存在，但不能直接授予边界资格：

| 后端 | 可复用事实 | 必须闭合的证据 |
| --- | --- | --- |
| NVIDIA | `hooks/instrumentation.py:402–421` 在 `ttgpuir_complete` 自动插 scope，随后有 Proton→LLVM lowering；`AutomaticScopes.cpp:385–409` 在选中 op 前后生成记录 | 这些 op/anchor 经后续 LLVM 与设备编译后的对应、纯计算跨界约束、实际 loop occurrence；不能只核早期 TTGIR 的相邻 RecordOp |
| GCU | `Debugger/python/flagtree_debugger/compiler.py:453–500` 接自动 timeline 请求；`Debugger/lib/Instrumentation/Passes.cpp:3805–3843` 已能注入 SDK timer 并拆 i64 words | TTIR 注入经过不同工具链后的合法顺序、最终 writer 和发布；timer call 和 logger 有副作用本身不足以约束纯计算 |
| Ascend | `ascend_compiler.py:121–140`、`:185–194` 有实际 SDK driver handoff；`AscendLateObserver.cpp:1002` 明示位于 actor lowering 后、scalar optimization 前 | 现有普通 operation 路径仍为单 tick checkpoint（`:671–689`），不能当成通用 interval；需要成对区域和后续优化/最终对象对应 |

**最小放行条件**：沿用现有 P03/§8.2 的开发样本，为每种实际编译路径保留 ordinary→instrumented→最终对象的可定位 anchor/控制流证明，说明约束截止层及失败处理。可以更换通用 pass 或引入数据/控制依赖，不必强求三工具链统一 IR，也不能用新增完成屏障换取顺序。

### V2 · 高：逻辑异步组到真实两轮复用，不能靠现有 mapper 自然升级

设计 `:166–168`、`:274` 与测试 `:146`、`:195–196` 已把机制闭合、动态组和物理复用区分清楚。当前 NVIDIA `timeline_nvidia_async.py:171–187` 将 `buffer_slot` 留空、generation 依据限定为完整 commit 流；文件 `:1–8` 也明确不证明物理 buffer generation。此处诚实保留 unknown 是正确的，但它不能单独满足 P07。

GCU 现有公开 observation 分支仍限定 `source_control_interval`（`Debugger/python/flagtree_debugger/compiler.py:485–492`）；Ascend 现有 set/wait bracket（`AscendLateObserver.cpp:550–590`）也不自动提供本次实际 operation 集合和复用 generation。因此三后端 C 阶段的工作量仍可能显著。

**最小放行条件**：每后端先选 ordinary 最终对象中确有的机制，证明状态变更闭合、真实 slot/flag 与两轮 generation、首轮/steady/drain 和对应时钟；不具备物理复用证据的样本保留 group-only partial。P01/P07 不能因已有漂亮 raw 区间而放行。当前静态材料既不能证明这些机制不可观测，也不能保证 SDK 一定开放足够接点。

### V3 · 高：三种 timer 的资格仍须逐目标取得

raw→ns 派生视图（设计 `:299–301`）与 cache/capture 分离是合理方案。NVIDIA `TargetInfo.cpp:13–37` 已选择实际 `%globaltimer` 读取，但代码中的 timer 名称不是目标认证；GCU patch 将 SDK clock 的 frequency 标为未验证（`integration/patches/enflame/flagtree-source.patch:9–32`）；Ascend manifest 仍将 scope/alignment 标为 actor-local/unverified（`AscendLateObserver.cpp:988–992`）。

**最小放行条件**：按现有 P01/P06，获得实际 getter、记录有效位宽、频率/误差/窗口、目标所需 epoch 关系。先闭合本地域 ns，再授予跨主体关系。此风险会阻止完整交付，但不要求推翻 raw schema 或提前建立通用 ISA。

### V4 · 中：第二、第三后端必须检验“公共 owner/consumer”是否真能复用

设计 `:295` 允许 compiler、transport/decoder、clock、mapper 组合，且 `:299` 把静态布局公式与 launch 事实分开，适合不同编译器。现有 `timeline_runtime.py:70–109` 已把物理 storage 规划交给 transport 并在分配前统计 pending 字节；当前 `hooks/timeline.py:90–99` 仍具体创建 CUDA transport。这提供了真实起点，尚未证明 GCU/Ascend 的隐藏 ABI、发布和完成条件能接上同一生命周期。

**最小放行条件**：按 §8.5/P09 从公开命令追到三份实际部件组合，核 admission→owner→完成→raw 的交接，并用同一语义验证/导出入口消费各后端真实数据。允许后端有独立 ABI、对齐和完成依赖；若遇到真实不可表达的状态，再版本化扩展公共合同。不要为满足“无公共厂商分支”把实质语义藏进 extensions。

## 整体逻辑与实施判断

1. **源执行映射闭合方向正确。** 设计把 source navigation 与时间归属分开，允许 fusion/split/elimination，并禁止复制 fused duration 凑阶段；binary 在完成后绑定摘要，避开自含 hash 的循环要求。它不要求每个源操作都有精确成本，也没有要求一个通用 pass 包办不同工具链。
2. **适配范围足够具体。** §8.10 的复用单位是 target+toolchain，明确哪些部件能条件复用、哪些必须重证；新概念允许改公共版本。因此“新芯片无需逐算子适配”有合理机制，“新增芯片只写 adapter 即可”则没有被错误承诺。本轮用三后端检验边界，不需要制造第四设备证据。
3. **放行次序可执行。** A/B 能继续开发，C 才计完整 P01，D 才交付；允许其它后端先调查原语，避免等全部 UI/资格才开始发现 SDK 障碍。矩阵较大本身不是不可行理由，现有 P/E 复用也没有强制重复新增数学数量。
4. **“有条件”针对物理与编译证据。** 当前材料允许工程继续，并没有证明 GCU/Ascend 的异步路径或全部最终边界已经可行。若小纵向样本遇到 SDK 的实际硬阻碍，应保留最小失败件、继续其它后端并返回具体原因，不能降低门槛后称整体完成。

## 可选改善

- 在各后端接入清单内各加一行“最后能控制优化的编译层 → 最后能审计的对象 → anchor 丢失时状态”。复用现有清单，不另建状态日志；这会使 V1 的实施责任更直观。
- 三后端接入时保留一个很小的“组合兼容收据”，明确 compiler/logger/storage/decoder/clock/mapper 的版本与目标条件。内容已经在 §8.10/测试 §8.5 的合同内，重点是让实际安装能定位，避免只列接口名。

这些改善不需要先搭插件框架，也不应成为开展已有 A/B 工作的前置阻塞。
