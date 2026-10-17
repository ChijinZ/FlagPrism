# Round 7 独立设计评审：runtime、物理协议与时钟

评审日期：2026-10-17。评审请求配置：**GPT-6.1-Sol / xhigh**；此处记录请求，不另行声称已核验模型运行配置。

输入与 `round7/INPUT.json` 的冻结内容一致：

| 文件 | SHA256 |
| --- | --- |
| `Profiler/docs/timeline_design.md` | `da1cf2ccbc3045a7d9236b139207de4e47dcdfe51509cb669332e1703aed4751` |
| `Profiler/docs/timeline_testing.md` | `c33395132ae5f0f6d77127f2d4dadd76be07ac89fd068b257c4965f9d1ab616b` |

独立通读以上两文档，重点检查设计 §8.12、测试 §8.7 及其与旧章节的一致性。为核对合同的实际落点，只读了 `timeline_events.py`、`timeline_events_{nvidia,enflame}.py`、`timeline_runtime.py`、`timeline_cuda_runtime.py`、`hooks/timeline.py`、`timeline_clock.py`、`timeline_nvidia.py`、`profile.py` 的相关路径，以及 `timeline_events.md`、`timeline_runtime.md` 的当前限制说明。未读其他本轮 reviewer 报告，未运行 SSH、产品 import、构建、测试或设备实验；未改产品和设计文档。下文源码引用只证明当前静态约束，不证明相关路径已在真实设备通过。

## 独立结论

**整体方案合理，足以继续按 A/B 的最小纵向链实施；没有发现必须推翻公共层/后端边界的设计阻断。** 单次执行、自动选择、晚期 manifest、逐 invocation owner、物理解码与公共语义分离、raw 与 ns 派生分离，能够组成可实现的工程路径。新 §8.12 尤其修正了把离线 adapter 当作可用 profiler、把 pair append 顺序当作所有读钟顺序、把 physical pair 数当 endpoint 数等容易出现的误判。

有两项公共合同收口问题，应在面向第二、第三后端冻结相应行为前作明确决策；另有一项异常验收表述需与已有安全回收规则统一。它们不是三后端物理可行性已经失败的证据。

**可行性仍然是待取证的、按部件分层的结论。** 代码能表明已有 owner/transport 和两类 raw adapter 的落点，不能由此证明最终指令边界、GCU 的 ns/epoch、Ascend 新动态 logger 的发布可见性，或三后端真实异步复用与 Perfetto 可读性。设计也没有给这些结论预盖章。当前合理的放行范围是继续最小实现与设备取证，不能宣布 P01 或完整交付通过。

未来芯片的复用目标也合理：公共身份、校验、时间算术和导出可以复用；compiler hook、隐藏参数、发布协议、timer 和机制规则按真实条件替换。新增型号的实际成本仍主要在最终编译边界、SDK 可用机制、时钟及发布证明。没有第四设备证据时，不能量化节约工期，也不能把新增 decoder 的工作量当作完整移植成本。

## Findings

### R1 — P2：应明确 raw 合同如何保留可唯一解释的计数器回绕

- **类别：公共合同收口；不是当前 64-bit raw 开发的阻断。**
- **章节：**设计 §6、§8.10 的 raw/派生分离、§8.12 的 canonical 交接；测试 §4、E09、P06、§8.7 的分层资格。
- **具体失败情境：**某短位宽 timer 的实际读数为 `start=2^b-2`、`end=2`，独立有效窗口与 reset 证据足以唯一确定经过 4 ticks。读取本身和 pair 身份都合法，但当前公共 raw 校验在 clock provider 介入前就拒绝 `start>end`；endpoint stream 也拒绝任何下降，paired stream 还要求 completion ticks 不下降。如此一来，合法 raw 无法进入同一 canonical→clock 派生链。若以后只换一个短位宽 getter，却继续沿用该 raw 合同，就会在 rollover 边界上出现与时钟资格无关的整批拒绝。
- **静态依据：**`timeline_events.py:205–219` 对两种顺序都检查原始 tick 单调，`:263–268` 要求区间 `end>=start`；`timeline_events_enflame.py:134–138` 在适配阶段已有相同限制。`timeline_clock.py:62–89` 却具备独立窗口下的唯一回绕算术。现有 `timeline_events.md` 对 schema 1 的保守拒绝有明确说明，故这不是隐蔽的既有支持回归；问题是新实施合同尚未规定未来接入时如何跨过这条边界。
- **最小修改：**在 §8.12 明确选择一种版本化策略：保留 modulo raw ticks 和物理顺序，读数是否可比较/可 unwrap 交给有范围的 clock 派生；或者明确 schema 1/2 暂限无回绕，合法回绕的后续版本与 `partial` 路径必须保原件且可离线升级重读。无需现在承诺所有旧格式支持回绕。复用 E09/P06，加一个“窗口足够、唯一一圈”的正例，与不可判定整圈/reset 负例配对；不要通过排序或改写原 tick 消除下降。

### R2 — P2：设备 owner 的回收条件不应依赖派生解码/导出成功

- **类别：运行时恢复合同收口；不要求改变安全等待原则。**
- **章节：**设计 §8.7 状态机与失败阶段、§8.12 raw 先持久化；测试 §8.3 的分阶段异常、§8.7 的原件与恢复。
- **具体失败情境：**多个调用已在两 stream 提交并完成，首个调用的 raw 和关联快照已安全持久化，随后 decoder 或 exporter 抛错。若按线性 `raw_ready→decoded→exported→released` 把设备资源留到导出成功，首个纯派生错误就能阻止后续 owner 的取证/回收；已不再有设备写者的 allocation 也继续占用 pending 字节与 owner 配额。离线重导本来只需要原件，这种耦合却会把格式/磁盘处理故障扩大成设备内存恢复问题。
- **静态依据：**`hooks/timeline.py:172–237` 当前逐 owner 执行读取、持久化、解码、机器映射和导出，最后才 release；中间异常会退出该次 flush。`timeline_runtime.py:13–20` 有意保活剩余 pool，因而不会由 Python 引用丢失掩盖这一状态。该保活对潜在写者是正确的，但不应成为已安全保存数据的设备资源必须继续存活的理由。设计 §8.12 已要求解析前保留原件，尚缺资源与派生状态解耦的最低约束。
- **最小修改：**说明设备资源生命周期与文件/派生状态分别维护：完成证明、D2H 及重导所需原件/关联快照持久化后，可以回收设备 scratch；后续 decode/export 保留独立失败与重试状态。finalization 在一个 owner 的派生处理失败后，仍应尝试安全取得并持久化其他 owner 的原件，保首个错误和各调用终态；不能因此释放尚有写者的 owner。复用 E05：至少两个 owner，首个在 raw 持久化后解码失败，第二个正常；检查两个原件均可定位，安全 owner 不被无谓保留，重导不增加应用调用次数。

### R3 — P3：新恢复验收行需限定“下一合法请求可用”的前提

- **类别：文本一致性。**
- **章节：**测试 §8.7“原件与恢复”行，对照 §8.3 的隔离资源规则及设计 §8.7。
- **具体失败情境：**初始化后超时或 completion query 失败，原 writer 尚不能证明结束。新表同时要求“不释放 owner”和“下一合法请求可用”，若被读成必须在同一失败 session/同一未恢复 context 立即恢复，会诱导测试把正确隔离判失败，或诱导实现为过关而强同步、重置 context、提前回收。已有 §8.3 实际已明确：隔离资源的失败 session 不要求原地复用；写者结束、安全清理后的新合法 session 才要求可运行。
- **最小修改：**在 §8.7 此行直接引用 §8.3：decode/export 故障验证同原件恢复；潜在写者/隔离故障按安全清理后新 session 的边界验证。无需新增测试或放宽原门槛。

## 无需改架构、但必须先由真实设备回答的问题

1. **最终边界与插桩扰动。** noinline 调用、SSA 依赖、memory clobber 和静态 PC 映射都是候选实现手段。它们不能单独证明最终机器对象中的区域约束和完成语义。新 §8.12 要求核对 NVIDIA GEMM 的展开/调度差异，并以关键 copy/commit/wait/compute 关系判断，这是必要约束；尚无证据说明其已闭合或不可能闭合。
2. **发布与物理布局。** 独立 decoder 能表达不同 ABI 是合理设计；真实多写者的 commit 顺序、cache-line 对齐及 D2H 可见性必须由生产者验证。特别是 Ascend 不能继承 census v3 的通过结论，GCU 旧单 program/actor adapter 也不能通过放宽校验自动获得默认首末 program 的写址资格。
3. **时钟与异步关联。** 比例、epoch、有效窗口和误差是独立条件；logical group、物理 buffer generation、完成观察和引擎活动也应分别授予资格。现有分层设计和端点不确定界判断合理。每后端两轮真实复用及其时钟关系仍是最大的设备验证风险，不能用普通区间或 CPU 关联 fixture 替代。

## 最低先行实验与推进顺序

复用既有 P/E 门，不增加资格矩阵；以下只是建议优先执行的最小取证顺序，本评审没有执行它们。

1. **普通公开入口纵向链。** 每后端先用 load→有依赖 runtime K 循环→store；同 binary 改 K，首末 program 含 tail。一起核数值/调用次数、实际读钟与区域顺序、紧凑 slot、完整 raw、物理提交可见性及本地尺度。先报告 boundary/publication/clock 各自终态，避免一个成功原语遮住其它缺口。
2. **owner 故障链。** 对支持两 stream 的路径交错提交，在初始化部分写入、提交结果不确定、D2H、首个 decoder/exporter 处分别失败。记录全部 owner 的完成范围、原件、保留资源和恢复条件；增加 R2 的双 owner 情形。未声明支持的组合在本次设备副作用前拒绝。CPU fixture 只补状态机，不授予设备并发资格。
3. **最小真实异步链。** 从 ordinary 对象中确有 async 的数学样本开始，核 sparse/dense 两种插桩的关键依赖与原有合法流水，保两轮实际 buffer/flag 复用及 generation，再取得目标 edge 所需的 clock 可比性。最后走共同 ns/Perfetto 消费链与 Trace Processor。只有这些证据齐备才进入 C/P01，随后扩大到独立数学和实际 UI。

设计合理性可以放行以上工作；任何具体 target 的时间单位、发布协议、区域边界、动态复用及标准 UI 门是否通过，仍应由该设备的实际原件决定。
