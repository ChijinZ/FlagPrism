# R3 独立设计评审：组合边界、适配成本与 Perfetto

结论：**合理（设计层面）**。本轮新增的设计 §8.10 与验收 §8.5 给出了可实施的组合边界，并如实保留不同工具链、执行主体、物理记录和同步机制的成本。未发现需要推翻方案的 blocker/major 设计缺陷。下列两项 minor 状态说明冲突应修正；真实三后端可行性仍须按既有 P01/最终资格取得证据，本评审不授予任何实现通过结论。

## 评审身份与范围

- 请求配置：`model="gpt-6.1-sol"`、`reasoning_effort="xhigh"`（GPT-6.1-Sol/xhigh）。当前 reviewer 任务：`/root/design_feasibility_portability`。工具没有向本 reviewer 暴露 resolved serving 型号/实际 reasoning effort，二者记为**未知**，请求配置不等于 serving 身份已确认。
- 基准 HEAD：`dad8e7c98632ef7cbd2b4677d9c5101a517a88dc`。评审对象包括当时尚未提交的设计/验收更新。
- 完整阅读 `timeline_design.md`（347 行）、`timeline_testing.md`（224 行）、`timeline_runtime.md`、`timeline_events.md` 与 `integration/plans/timeline/goal_prompt.md`。
- 仅作针对性静态代码核对：公共 owner 的准备/发布/完成路径，raw schema 的身份/配对/引用校验，NVIDIA hook 的真实组合位置及公共时钟算术。没有进行完整代码验收；未连接服务器、运行产品 import、测试、编译或设备/浏览器操作；未阅读其他 reviewer 报告。只写本报告，不改设计、产品、论文或 Study。

评审字节 SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| `Profiler/docs/timeline_design.md` | `6f433840e0da7938e9201381d85c1a6bcaa785134fed9c69d382ff5d3de930f3` |
| `Profiler/docs/timeline_testing.md` | `456c3cc29588cbfd61754c345b6752bd9b29a740f42752108e6809384db3fdc2` |
| `Profiler/docs/timeline_runtime.md` | `316d2febcdc7439dd504f07109230b4095753f88d72ccda3b1a8f4d5e6d5d9a9` |
| `Profiler/docs/timeline_events.md` | `c41f6949d41f0f5596c358e1a4d0382edda091e2de66a51a1d31184a171527ee` |
| `integration/plans/timeline/goal_prompt.md` | `51db449f2898ad695f8557a3d83459cf476c57cec27198743ba481193e12a054` |

## 设计判断

1. **接入单位和组合粒度正确。** 设计 :287–299 按目标及工具链适配，组合编译接入、transport/decoder、clock provider 与 mechanism mapper；注册可以做目标分发，公共 owner/validator/exporter 不补厂商语义。它允许相同机制复用，也允许独立替换真实变化的部件，没有强制完整继承、统一物理 ABI 或先建插件框架。测试 :208–210 要求实际调用与错误组合，足以区分真实复用和空 adapter。
2. **公共模型没有把 NVIDIA 执行树强加给异构主体。** 设计 :162–168 分开 program、observer、operation、resource，允许多 submit/group、部分 wait、多消费者和 generation；:297 限定改变判断的字段必须进入有类型的语义合同。物理发布、指令识别和机制规则留在后端，公共层验证引用/集合/代际及展示资格，这个责任划分合理。
3. **编译、启动和 capture 的事实分离可落地。** 设计 :299 避免 manifest/binary 自身 hash 循环，以实际 launch grid 计算 slot/容量；:301 把认证 ns 作为不可变 raw 的派生视图。生命周期、预算和错误后回收已有明确交接（:220–240），可以从现有 owner/transport 调用演进，无需引入另一套全链结构。
4. **Perfetto 验收同时约束导入、语义与可读性。** 设计 :324–333 规定标准 trace、真实时间坐标、重叠轨道、源信息和稳定 ID；测试 :103–130 将实际 Trace Processor、逐事件 raw 对照、importer stats 与 UI 点击/截图分开。这些是可以执行和留证的条件，没有把 protobuf 解码或自写页面当成功。
5. **阶段顺序可行，适配成本表述克制。** 设计 :303–314 的 A/B 允许先推进普通区间、owner、本地 ns 和公共导出，C 才到完整 P01，D 才最终交付。第二、第三后端可先查原语，而非等首后端全部 UI/独立资格。清单记录实际复用/改动，不承诺第四芯片、移植天数或零公共改动；现有三后端足以检验本轮边界，不需要追加第四设备实证。

## Confirmed 设计文档缺陷

### C1 — minor：执行合同仍把已存在的 raw 入口写成尚未实现

- 位置：`integration/plans/timeline/goal_prompt.md:67`；对照设计 :35–42、:285 及 `timeline_runtime.md:3–20`。
- 触发：实现人员按作为执行依据的 goal 合同判断入口现状。合同称 `--detail timeline` / `detail="timeline"` 尚未实现，而当前文档已明确它是 NVIDIA 可用的 `partial_clock_unverified` raw 路径。
- 影响：误判已完成的入口/owner/raw 工作，且与“最终文档只写实际存在命令”的要求冲突；不会单独破坏时间正确性。
- 建议：把合同中的绝对“尚未实现”改成当前 NVIDIA raw 路径已存在、认证 ns/Perfetto 与另两后端 producer 未完成，并链接 runtime/events。按合同自身规则同步工作区入口与已跟踪快照，不改变完整交付门槛。

### C2 — minor：设计开头把当前边界引向已声明为历史的检查点

- 位置：`Profiler/docs/timeline_design.md:3`；对照 :246、:280、:285。
- 触发：从文件开头追踪“当前工程边界见 §8.8”。§8.8 实际是 `b3e4a7f` 历史原语检查点，其中还描述 43 位 packed record；§8.10 明确要求不把它当最新支持表。
- 影响：读者可能将历史原语状态当成当前产品边界，掩盖新 raw/owner/schema 已完成的范围，或与 :35 的公开入口状态混淆。
- 建议：开头改指向 runtime/events 与 §8.10 的范围说明，将 §8.8 标为历史证据背景。历史内容保留，不必维护第二份 live 状态日志。

## 待实证风险（不是已确认设计缺陷）

- **当前公共 owner 调用是否能自然接第二后端。** `timeline_runtime.py:70–88` 仍直接接收整数 function/stream、`num_ctas`、scratch 等当前 NVIDIA launch 参数；`hooks/timeline.py:90–94` 当前直接组合 CUDA transport。这不否定目标设计，但第二后端接入时须证明无需伪造 CUDA 身份或把厂商规则移进公共 owner。通过现有 P04/P09 与 §8.5 的真实调用审计处理；让后端保留其 launch/storage 描述即可，不要求现在另建大框架。
- **合法边界、单位及 epoch 是最大物理风险。** 源区域融合/消除、timer/logger 对最终纯计算顺序的约束、GCU 校准适用窗口和 Ascend actor epoch 都不能由公共 schema 证明。现有设计 :68、:100–108、:190–192 与测试 P01/P03/P06 已要求最终对象和真实设备证据；这些条件应成为进入全量资格的实际闸门。
- **逻辑 group 与物理复用仍要分别闭合。** 当前 raw 文档明确不授予 buffer generation 或时间箭头资格。测试 :146、:196、:212 要求每后端两轮真实 buffer/flag 复用，不能仅凭 cp.async 等逻辑 group 序号填表。应先查候选 ordinary 编译对象，再选择已有合法复用样本；无法观测时保持未通过，不伪造 buffer，也不降低本轮门槛。
- **标准 Perfetto 的端点和轨道映射需要第一份真实 trace 尽早定型。** 共享 exporter 仍须实际验证重叠 in-flight 区间、flow 两端绑定、clock/error/source/raw args、稳定 ID 及独立域分文件。用首后端 B/C 真实产物冻结 §8.6 export mapping 和 SQL，再让另两后端走同一消费入口；现有 §7/§8 与 P08 足以验收，无需增加资格算子数量。

## 可选改进

可以在现有接入清单中附一张小的“部件实例 × 三目标 × 相容版本/证据”表，帮助看出哪些部件实际复用、哪些必须独立实现。它只索引现有文档和证据，不新增状态系统或通过条件。

本轮可按此设计继续实施；先修正文档状态冲突，再由实际三后端 P01、独立资格和 Perfetto SQL/UI 决定是否达到交付条件。设计评审通过不表示任何未跑项目已经通过。
