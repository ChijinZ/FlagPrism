# 第七轮独立设计评审：后端复用与可执行验收

评审日期：2026-10-17。请求模型配置：`GPT-6.1-Sol / xhigh`（调度配置为 `gpt-6.1-sol`、`reasoning_effort=xhigh`）；实际服务身份未独立暴露，本报告不推断实际模型。

审查输入为工作区当前文件，未读取本轮其他评审报告。最终核对的 SHA256：

| 文件 | SHA256 |
| --- | --- |
| `Profiler/docs/timeline_design.md` | `da1cf2ccbc3045a7d9236b139207de4e47dcdfe51509cb669332e1703aed4751` |
| `Profiler/docs/timeline_testing.md` | `c33395132ae5f0f6d77127f2d4dadd76be07ac89fd068b257c4965f9d1ab616b` |

测试文档最初读取时的 SHA 为 `3a6d1405fc1d18066b881153a0172b6a229a4e1397132968dcdf3aeb91645cde`；主审通知只同步了测试 §8.1 对设计章节范围的引用。本报告结束前已重新核对当前引用为 §8.1–8.12，并以上表当前 SHA 为准。仓库 HEAD 为 `7fceb5e41e33359146353edca36e37feb18527c3`，评审对象包含工作区未提交文档。

完整阅读两份文档，重点设计 §8.12 和测试 §8.7，并只读核对 `timeline_events.md`、`timeline_events.py`、`timeline_events_enflame.py`、`timeline_runtime.py` 以及 `hooks/timeline.py` 的相关路径。没有执行产品 import、build、test、设备采集、SSH 或浏览器；没有改设计或产品，只写本报告。

## 总体判断

**设计整体合理，可以据此继续最小纵向实现；尚不能宣布三后端完整时间线在设备上可行。** 未发现必须推翻架构的 P0/P1 问题。下列两项为 P2 的合同表述和验收落点问题，宜在冻结第一条实际公共合同前解决，不要求设计中尚未落地的能力现在已经实现。

对“未来芯片适配简单”的判断是：当前方案有合理的减重复路径，但不构成低成本移植已经得到验证的结论。同工具链、记录布局、getter、运行时和同步机制的复用条件分别登记，可以避免只更换 clock provider 却被迫重写 transport/decoder/exporter；不同执行模型仍可能需要新的晚期 pass、隐藏参数、发布协议和机制规则。这些成本在设计中已有诚实边界，不应再增加“一个 adapter 即可”或固定工期承诺。

## Findings

### F1 — P2／合同文字一致性：`decode_capture` 与独立 clock provider 的职责尚有两种读法

- **章节**：设计 §8.9 的 `decode_capture` 行（第 267 行），对照 §8.7 的解码交接、§8.11 的独立部件和新 §8.12（第 369、378–379 行）。
- **问题**：§8.9 将 `clock proof` 列为 `decode_capture` 输出；§8.12 又明确“clock proof 不由 decoder 构造”，并把 decoder 的产物和 provider 的事实分开。这可以解释为高层编排动作与物理解码器不同，并非不可调和的架构矛盾，但文档尚未明说这一区别。
- **具体失败情境**：新增型号沿用物理布局而更换 getter。实现者若把 §8.9 的输出当作物理解码合同，就可能在 decoder 内探测设备/构造 proof，导致旧 raw 离线解码依赖设备，或更换 clock provider 还必须修改 decoder；另一实现者则只返回无 proof 的 canonical batch。两种实现均能引用现有文字，却无法稳定组合。
- **最小修改**：将 §8.9 明确为“`decode_capture` 是可选编排动作，物理解码只返回 canonical batch；clock provider 独立提供或引用 proof，公共层组合验证”，或者直接把该行输出拆为 decoder 输出与独立 provider 输入。不要求创建新类。补一个既有 P06/P08 用例的判定：固定 raw/manifest，缺失与替换 clock proof 不改变物理解码所得端点及原始身份，仅改变 ns 派生资格；物理解码本身不执行设备工作。
- **性质**：职责名称的文字澄清，非硬件阻碍，也不是要求未来接口当前已经存在。

### F2 — P2／验收落点：成对提交顺序应贯通到 Perfetto 导出投影

- **章节**：设计 §8.12 第 383 行、§8.6 的 export mapping、§9 第 406 行；测试 §7、§8.7 的“两种记录顺序”行（第 244 行）。
- **问题**：新合同正确要求保留 pair 提交顺序，且禁止按时间排序来修复原始记录；Perfetto 部分要求合法嵌套/重叠，却未明确这一禁止与导出投影的关系。测试 §8.7 对合成嵌套 pair 的明确判定目前停留在顺序、offset 和配对合法性，没有明确要求同一 fixture 经过公共 exporter 与实际 Trace Processor。
- **具体失败情境**：物理 append 先提交内层 `[20,30]`，后提交外层 `[10,40]`。decoder 保原顺序是正确的。如果 exporter 沿 endpoint-stream 的旧假设直接输出同 track 的 B/E，或者认为任何时间投影排序均被禁止，就可能得到错误嵌套、拒绝合法 pair，或错误拆散 source/identity。反向改写 canonical 顺序又会违反原件合同。这里指出的是有明确反例的交接缺口，本次没有运行 Perfetto，不能声称某一工具版本已实际失败。
- **最小修改**：补一句“保留 raw/canonical 提交顺序不限制 exporter 为合法协议生成独立时间投影；投影不得改变端点、配对、原始 sequence、raw 引用或 occurrence 含义”。具体采用合法的事件排序还是独立轨道，由选定协议核实后冻结。将已有嵌套 pair fixture 同时送入共同 exporter 和锁定版本 Trace Processor，逐条核 `[20,30]`、`[10,40]`、source/event/raw 对应及正确父子/轨道关系，不能只验证文件可解码。该 fixture 只验证导出合同，不替代 GCU 真实设备或 UI 正例，也不增加独立数学数量。
- **性质**：可执行验收的补充说明，非架构否定。

## 公共与后端职责的判断

当前分工能够落地，关键是继续按事实交接：厂商侧负责真实 lowering、主体映射、物理发布/解码、getter 和机制覆盖；公共侧负责身份/引用/损失、资格依赖、时间算术、动态集合完整性以及统一导出。公共验证能拒绝悬空引用和串代，不能独立证明厂商规则符合机器语义；设计 §8.7 已明确这一点，因此没有把“公共 validator 通过”错误当成硬件真实性证明。

允许不同物理 ABI、非 warp 主体、M:N source origin，以及同目标组合多个 mapper，均有助于接入新执行模型。注册入口可以识别 target，而消费者按 typed semantic 工作，也能避免厂商展示补丁扩散。合理的新公共概念允许版本化修改并回归旧后端，比硬性要求零公共修改更可行。第一条真实链后再冻结小合同、以第二/第三实现检验复用，也避免当前先造没有调用者的插件框架。

只读代码提供的是工程落点，不是设备通过证据：

- `timeline_runtime.py:70–132` 已存在 admission、transport 与 owner 分工，`read/retry_read/release` 也区分完成、读回和回收。说明复用现有 seam 有现实基础，不能由此推论 Ascend/GCU transport 已满足相同语义。
- `timeline_events_enflame.py:19–165` 是读取 retained raw/metadata 的适配器，输出明确的未验证 clock/boundary 状态；`timeline_events.py:205–219` 实际区分 pair completion 顺序与 endpoint stream。这支持新合同的表达能力，不能推论 GCU 默认入口、ns、epoch 或异步映射已经完成。
- `hooks/timeline.py:185–217` 可见 NVIDIA 先持久化 raw/input，再做解码与 canonical 化的现有路径。它仍是厂商集成路径，不能拿当前文件布局当作未来三个后端均已公共化的证据。

## Perfetto 与验收是否真正可执行

**计划是可执行的。** 它要求固定真实 UI/Trace Processor 版本和 SHA、保存 SQL 与完整 importer stats、逐事件比对时间和 raw 证据，再实际缩放、选择 slice/flow 并保存截图。既检查所有正常资格 trace 的导入，也对每后端至少六份 trace 做 UI 检查；这比“protobuf 可解析”更接近实际用户要求。源导航允许配套 bundle 页面而不虚构 Perfetto 自带功能，也没有明显工具能力的硬性冲突。

SQL 的具体表结构和 TrackEvent 编码留到选定工具版本后核定，是合理的实施任务，不是本轮设计必须先提供可运行 SQL 的缺陷。F2 是应在该阶段明确纳入的小反例。当前未运行这些工具，本报告不确认工具依赖已安装，也不确认三后端已有合格 `.pftrace`。

测试矩阵虽大，但 A/B/C/D 与 P01 将核心风险放在全量资格前，新增 §8.7 复用 P/E 而非继续增加数学数量，执行顺序基本受控。旧 raw 重读、CPU fixture、默认公开采集与设备正例分别标注，且不允许把失败改成 unsupported，能够防止复用和成功率的错误结论。

## 尚未证实的风险与先跑的最小实验

以下是设备/实现取证项，不属于通过修改文档即可消除的 findings：

| 风险 | 应先取得的最小证据 | 失败后应做什么 |
| --- | --- | --- |
| 自动边界在最终对象中仍合法 | 每后端一份普通 load→有依赖 runtime 循环→store；同 binary 改 K=3/7；实际最终对象、两源区间与动态 raw 对应 | 先修通用 lowering/约束，或明确可观察范围；不以 marker PC、正 duration 代替边界证明 |
| 默认选择和发布真实可用 | 同数学的多 program/tail 与单 program；首末 slot、未选写入隔离、header/padding/commit、canary 与数值 | 先修 producer/transport；旧 raw adapter 成功不能放行默认入口 |
| 时钟尺度与跨主体比较成立 | 实际 getter、完整记录位宽、尺度/误差/有效窗口；单独校准及留出验证；目标 edge 所需的 epoch/offset 证据 | 保合法本地 partial；不能靠同频或 exporter snapshot 授予共同时间轴 |
| 插桩保留欲解释的异步结构 | 每后端先选一份 ordinary 对象确有机制的数学样本；至少两轮真实 slot/flag 复用，保 submit/commit/wait/compute 与稀疏/较密对照 | 若关键结构失真，先调整通用插桩/采样；不拿插桩图解释 ordinary 流水 |
| 恢复不重放且 owner 安全 | 同一完成 capture 的 raw/manifest/invocation 先落盘，再注入 decoder/exporter 失败并重导；初始化异常按潜在写者处理 | 保首次失败与原 SHA，无法安全结束写者时隔离并失败，不提前回收 |

建议每后端依次完成上表前两项和本地 clock，先形成 B；再接真实异步/代际及所需可比时钟，并使用同一公共 exporter 实际导入 Trace Processor，才记 C/P01。只在这些最小输入闭合后扩大独立数学和 UI 矩阵。三后端可以调查各自原语，公共小合同仍应由首条真实链形成，并在第二/第三实现中检验。

因此，本轮可认可的是抽象边界与执行路线；尚未认可的是具体芯片 timer/epoch、最终编译边界、发布可见性、真实复用代际及 Perfetto 通过。未来适配是否确实省事，仍须由三后端的实际部件复用、公共变动理由与设备回归来支持。
