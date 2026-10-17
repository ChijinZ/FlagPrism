# R2：时钟、记录、异步与生命周期设计可行性评审

## 结论

**有条件通过设计合理性评审，可继续按分段路线实施；未发现确认的设计 blocker 或 major。** 条件是保留现有 P01/P03/P05/P06/P07 与生命周期放行门，完成下述设备核验；本结论不授予三后端实现、ns 时间轴、物理复用或 Perfetto 资格。另有一个应修正的生命周期文档 minor，不需等待设备即可处理。

目标不是仅补 exporter：最终机器边界、GCU 尺度、Ascend 跨主体 epoch/发布以及每后端物理 buffer/flag 复用，仍可能要求通用 pass、ABI 或 SDK 扩展。设计明确允许这些工程改动，并在全量资格前设小纵向阻碍检查，故目前没有充分依据判为不可实施，也没有依据承诺三个目标必然取得全部必要证据。

## 阅读与边界

完整阅读 `Profiler/docs/timeline_design.md`（364 行）、`timeline_testing.md`（226 行）、`timeline_runtime.md`（92 行）、`timeline_events.md`（55 行）及 `integration/plans/timeline/goal_prompt.md`（156 行）。实际 SHA256 均与 round5/INPUT.json 的五项一致；INPUT 的 source_head 为 `f5731a08dbeebff633e416233b5faf857f1fc7da`。

为核可实施性，额外完整只读 `Profiler/python/flagtree_profiler/timeline_runtime.py`、`timeline_cuda_runtime.py`、`timeline_storage.py`、`timeline_clock.py`、`timeline_nvidia_async.py`。这些源码只证明存在可落实的结构及保守降级路径，不作为设备正确性证据。没有读其他 reviewer 或历史评审报告，没有 import、测试、构建、SSH、设备或论文操作，没有子 agent。未审计完整 compiler/logger/decoder、Ascend/GCU 实现、CLI 调度树、实际 binary、安装或任何设备产物。

## 确认问题

### MINOR-01：直接回收条件中的“未提交”存在初始化写入歧义

- **位置与矛盾：** design:236 定义 armed 已持有 buffer，design:240 写“未提交的 owner 可直接回收”；testing:176 同样写“未提交可释放”。但 runtime:68–73 明确初始化也可能提交写入，armed 或 possibly submitted 均需完成证明。实际 `timeline_runtime.py:114–131,152–167` 在 initialize 前进入 armed，abort 对 armed 记录完成条件；`timeline_cuda_runtime.py:40–45` 的初始化会向设备写零/guard。因此按“用户 kernel 尚未提交”理解前两处会允许过早释放，当前实现及 runtime 说明则正确避免该问题。
- **最小修订：** design:240、testing:176 将直接回收限定为“尚未分配或能证明未发生任何初始化/提交写入的 admitted owner”；armed、submitting、quarantined 一律按潜在在途写者处理。初始化前分配失败的清理由 transport 的无写入保证负责。
- **验收：** 在既有 E05 中覆盖 initialize 部分提交后抛错、初始化成功但 kernel 未提交、纯 admitted 失败三条路径；前两者无完成证明不能 free/reuse，第三者可立即取消。此条是合同措辞一致性问题，非已确认的实现 UAF。

## 待设备核验风险（不是确认的设计缺陷）

### RISK-01：频率、epoch、有效窗口和细粒度可分辨性必须独立闭合

- **位置：** design:92–108、164、204、298–316；testing:55、96、145、210、214–215。runtime:39–44、events:36–41 正确保留 unverified。
- **判断：** 设计已经区分单位与 epoch，保 raw ticks，要求 origin 后整数/有理数转换、整圈回绕约束、端点误差判序及 proof 适用范围；这些足以支撑保守实现。现有 `timeline_clock.py:48–89,107–117` 可承接算术与域拒绝，但它不能授予物理证明，也不完整实现共享误差模型。GCU 校准界限及 Ascend SYS_CNT 旧来源不能自动成为本次跨 observer 合格证据。
- **最小落实：** 不增加硬门槛；冻结 clock proof 时明确 origin 的身份/来源、尺度与 offset 误差、有效时间窗及设备重置后失效条件。无法处理共享误差时允许保守独立上界，关系保持 unresolved；不要为得到箭头擅自减小误差。
- **验收：** P01 的实际 getter/独立留出校准及所需跨主体对照，配 E09/P06 的过期、错 epoch、完整绕圈和近边界负例；Trace Processor 的 ns 逐条回对原 ticks。不能只以正 duration 或普通 kernel 首尾拟合证明。

### RISK-02：编译边界是时间含义的前提，不能由 timer 正确替代

- **位置：** design:66–68、146、202、314–318；testing:142、159、214；runtime:29–44。
- **判断：** LLVM SSA operand anchor/memory clobber 只提供部分编译层约束，runtime 已明确 PTXAS 与最终机器审计仍待完成。设计没有把 PC/source 映射等同于区域包围，也没有要求添加完成 barrier，因此方案不自相矛盾。困难是纯算术、异步 wait、流水化/fusion/split 的最终对象证据可能需要不同通用 lowering。
- **最小落实：** 按 site 保存最终 begin/end 与被观察指令/控制路径的证据；无法证明的源区域只保导航和原 counter 间隔，不标源操作耗时。现有分项资格规则保持不变。
- **验收：** P03 对真实算术 loop、访存与原 wait 检查最终对象；runtime 输入改变 occurrence，fused 多来源不复制 duration；缺一个 site 证据不得扩散其它 site 的资格。此项由设备编译产物核验，不能先用当前未认证状态判目标设计失败。

### RISK-03：发布协议和 loss 必须与物理写者、缓冲布局一起证明

- **位置：** design:82–88、153、158、203、307；testing:91、95、99、144、160。
- **判断：** “按 program/observer 分区 + 实际多写者发布协议 + 完成后读回”是可实施路线；公共格式与物理 ABI 分离避免强迫 Ascend 共用不安全布局。events:27–34 对覆盖历史保 orphan、不跨洞配对；`timeline_nvidia_async.py:115–132` 遇丢失直接不生依赖，保守方向正确。尚需证明真实 writer election、payload/header 可见性、commit 顺序、饱和及 ring overwrite 的一致快照。
- **最小落实：** 冻结每后端物理协议时为 attempted/committed/dropped/overwritten/saturated 写明定义及守恒关系；区分“无历史”与“本次没有执行”。公共 complete 不得覆盖 clock/boundary 的 unverified 状态。
- **验收：** P05/E04/E08/E12 用真实长数学和 tiny buffer 核 canary、边界残缺与所有选中 observer 的损失，并注入 header/commit/payload 损坏；CPU fixture 只补协议负例。不能从旧 census 发布修复推定新动态 logger 通过。

### RISK-04：物理复用与机制闭合比逻辑 group 序号要求更强

- **位置：** design:112–118、166–168、205、227、274、296、310、314；testing:64–71、146、195–196。
- **判断：** 设计允许一对多/批量/部分 wait、多消费者，要求按 invocation/机制维护状态，且 opaque/隐藏状态变更不默认为不存在。这比按名字配 flow 完整。当前 `timeline_nvidia_async.py:171–225` 只输出逻辑 group、unknown buffer 和未认证时间箭头；文档明确它不能满足物理 buffer/flag 两轮复用门，故不构成承诺矛盾。实际物理 slot/地址与控制路径代际映射可能是下一主要工程工作。
- **最小落实：** 针对先支持的一种真实机制，冻结状态变更覆盖表、operation 集合、实际 buffer/flag 身份来源和 loss 后失效/恢复锚点。缺物理证据时保 group-only partial；另选有真实复用证据的普通样本，或保资格未通过，不编造 generation。
- **验收：** P07 的首轮/steady/drain 至少两轮复用，故意丢 commit/串 generation/引入未覆盖状态变更后拒绝 verified edge；实际最终对象证明状态闭合，CPU fixtures 补批量/部分 wait/多消费者而不冒充设备能力。逻辑关联、物理复用和时钟箭头分别验收。

### RISK-05：完成句柄、pending 总预算及故障保留必须在所有后端保持同一安全含义

- **位置：** design:88、229–240、265–267、308；testing:161、174–181；runtime:46–83。
- **判断：** owner 快照、session 累积 admission、原 stream 完成依赖、超时不代表终止、raw 重导不重跑应用均明确，且现有 owner/transport 有直接实现位置。当前支持单 host thread、多 CUDA stream，nested/graph 拒绝，与“按后端预冻结并发范围”一致；无需为了通过设计评审新增三后端无条件 two-stream 要求。资源无法安全回收时隔离并报失败是诚实的安全选择。
- **最小落实：** 除 MINOR-01 外无须重设计。各后端适配清单写清 initialize/launch/completion/D2H 的 stream/context 与失败状态；outer process deadline 不得被解释为 Python 可以提前 free 在途内存。
- **验收：** E03/E05/P10 交错提交后才读回、反序读取、pending 累积超预算早拒绝、初始化异常、record/query 失败、D2H 失败及后续新 session 恢复。实际两 stream 正例只要求已声明支持的后端；其余在本次设备副作用前拒绝。设备已终止与 host 控制器终止分开留证。

## 可选建议

1. **冻结一个可核对的资格依赖表。** design:314–316 已规定按结论授予资格；可用小表列“source elapsed、逻辑关联、物理复用、跨 track 箭头、engine activity”分别需要哪些 proof。最小改动是复用现有状态 schema，不新增一套认证框架。用 testing:214 的部分坏证样本核输出资格与表一致。
2. **先攻最脆弱的一条证据链。** 按 design:318–329，在扩大普通算子矩阵前先核目标上最难的 getter/边界/物理复用原语。保留失败阶段、最小对象与 SDK 约束即可；不要求设计文档提前提供设备结果，也不降低完整 P01。

总体上，目标、降级语义、阶段放行及验收之间能够对应；风险都集中在有明确验证位置的真实编译/设备事实。修正 MINOR-01 并保留这些门后，可继续实现；目前不能据此宣称三后端最终目标已可交付。
