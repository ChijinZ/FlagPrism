# R2 独立设计评审：runtime / clock / 发布 / 生命周期

结论：**设计可继续实施，未发现已确认 blocker、major 或 minor；设备可行性仍有明确未验证项。** 本结论只认可目标合同、分阶段路线及验收判据的合理性，不认可当前代码已实现这些合同，也不保证三个 SDK 最终都能提供所需证据。尤其不能把本报告记为 P01、最终资格或最终代码验收通过。

## 输入与边界

- 完整独立阅读 `Profiler/docs/timeline_design.md`、`timeline_testing.md`、`timeline_runtime.md`、`timeline_events.md` 及 `integration/plans/timeline/goal_prompt.md`。
- 五份输入实际 SHA256 与 `round6/INPUT.json` 全部一致；输入所记 source HEAD 为 `4f5b2bff76ec61537bcec6d98075639d7f9ef731`。本次未把该 HEAD 当作实现通过证据。
- 未读旧报告、其它 reviewer 报告或其它工程证据；未读产品源码、联网、import 产品、运行测试或访问设备。文档中的已实现/已有证据陈述在此只作为文档状态边界，未独立复验。
- 本次是设计合理性与工程可实施性评审，**不是合同 §7 所要求的额外三个 `GPT-6.1-Sol / xhigh / fresh context` 最终代码验收**，不得顶替其中 R2 席位。

## 已确认问题

| 级别 | 数量 | 结论 |
| --- | --- | --- |
| blocker | 0 | 未发现设计内部矛盾或必须新增架构才能推进的缺陷 |
| major | 0 | 未发现会迫使实现产生伪时间、错误关联或不安全回收的设计要求 |
| minor | 0 | 无必须先改文档才能执行的具体缺陷 |

无已确认问题并不意味着物理事实已证明；下述缺口属于必须执行的验证项，不能用多数赞成票消除。

## 重点判断与依据

**新增 §8.11 / 测试 §8.6 可落地。** 设计第 345–363 行将编译边界、transport/decoder、clock、mapper 与公共消费拆成职责，允许用现有函数/对象组合，且明确只有真实共享行为才抽取公共实现。这能分别替换设备特有部件，不要求先建无调用者继承树。测试第 228–233 行沿用现有 P/E 和数学样本，核的是实际公开调用链、最终对象及数据，并未额外增加独立数学矩阵。多函数/非零 PC 检查针对真实对象，允许等价后端证据和负例 fixture，没有强迫三家都使用 NVIDIA 工具。没有需要删除的不可执行硬要求。

**时钟证明没有被校准算法替代。** 设计 §6、第 100、108、300–328、361 行与测试第 230–231 行分别要求尺度、epoch、窗口、端点误差和适用范围。因果握手只限制 offset，独立保留轮次只检验一致性；两者均不能自产生物理误差上界或证明所有 SM 共 epoch。整数减 origin 后换算、完整绕圈歧义、按端点误差判断先后、未知域分文件及原 raw 不变，构成可执行且相互一致的规则。若实际只能证明本地域尺度，仍能推进局部区间，不能因此通过跨主体异步门。

**最终机器边界是风险，不是已解决前提。** 设计第 68、359 行及 runtime 的 `llvm_ssa_pending_machine_audit` / `counter_mapping_complete_region_unverified` 都明确：调用、SSA、memory clobber、marker PC 和正 duration 不单独证明区域边界或完成。测试第 228–229 行要求公开自动样本核最终对象，没有把手工 noinline 探针提升成产品证明。该路线值得实施；是否能约束选定真实区域须逐 site 核验。observer elapsed 与 issue/wait/completion/engine activity 的区分，使路线不必追求所有异步指令的精确硬件完成时刻，也不需新增完成屏障才能产生合法结果。

**记录发布和损失责任明确，物理协议仍需后端冻结。** 设计 §5、§8.6–8.10 要求后端负责 layout、commit、padding、真实写者与发布协议，公共层核 raw 引用、配对、丢失、身份和版本。events 文档仅将 `complete` 解释为 raw 覆盖，保留缺端点、覆盖窗口和 unverified 状态；不会由 ring 中“有一对时间戳”自动授予完整时间解释。设计阶段不冻结三家相同 ABI 是合理的，不能把尚未给出的具体发布顺序当作已通过。后续小合同必须实际确定计数、提交和丢失后的失效/恢复规则。

**owner 生命周期覆盖了主要危险窗口。** 设计 §8.7 的 admission、实际 grid/stream 快照、pending 总字节限制、初始化即可能有设备写者、提交不确定时隔离、超时不等于终止，以及测试 §8.3 的逐阶段故障注入，足以指导安全实现。不能以“kernel 尚未启动”或 Python 返回作为释放条件。runtime 文档进一步明确 host-thread 边界、graph 早拒绝、blocking D2H 的进程 deadline 与 retained owner。允许最终化等待记录完成，同时禁止逐 launch 强同步冒充跨 stream 保真，两者没有矛盾。隔离 session 失败后允许安全清理再建 session，亦避免要求在未知设备状态下原地恢复。

**异步门槛严格但有明确观察对象。** 设计 §7、§8.2、§8.9 与测试 §5/P07/§8.4 明确 group ordinal、loop iteration、物理 slot generation 是不同证据，要求机制状态变更闭合及丢 commit 后不平移身份。每后端两轮真实 buffer/flag 复用是完整资格的既定要求，不是本轮新增架构。选样前先核 ordinary 编译对象，再取确有来源的真实复用案例；若 SDK 不能观测则报告最小阻碍，不能补造 buffer。此门有实际失败可能，但不构成逻辑上无法执行的测试。

**整体负担可控，完整通过仍取决于硬件。** A/B/C/D 阶段和每后端最小循环/异步输入把高风险验证前置；不必先跑完整资格矩阵。P/E 补充项重用已有样本，fixture 只补负例和非该设备机制的合同覆盖；two-stream/host-thread/graph 支持表可事前明确，并非每家都必须支持所有并发形式。最终 SQL/UI、独立数学及指定代码走查各自检查不同失败面，未被设计评审替代。当前设计无需再扩一层公共 IR、全局 logger 或统一物理 ABI。

## 剩余必须设备验证项

以下均保持未验证，不是本报告确认的代码 bug；直接复用已列 P/E，不再扩矩阵。

1. **每后端自动边界（P03、测试 §8.6）**：公开 API、runtime K 同 binary、有依赖算术与 load/compute/store 的实际最终对象；核控制路径、目标指令、实际 getter 与动态 occurrence。包含真实 helper 时核函数/代码段和 caller 关系。失败时先修通用边界，不以 marker 映射替代，也不添加完成 barrier。
2. **尺度及可比范围（P01/P06/E09）**：本机 getter 位宽、记录有效位宽、比例来源/有界误差、reset/wrap 与适用窗口；需要跨 actor 时另核 offset/epoch 和端点误差。因果样本的顺序、训练/保留分离与目标主体覆盖需要设备证据。不能把未覆盖 SM、旧 epoch 或有限采样外推成已证范围。
3. **发布可见性（P05/E04/E08/E12）**：Ascend 动态 timeline 自己的 cache-line/payload/commit 可见性；GCU 实际 work-item 写者及完整 payload；NVIDIA logger/decoder 有效位宽与 ring 覆盖、损失计数。保存真实 raw/canary，故障或溢出不能只检查 UI 可见 subset。
4. **owner 安全（E01/E03/E05/P10）**：声明支持路径的多次交错提交、初始化部分失败、提交结果不确定、完成记录/查询失败、D2H 失败与 cancel；核全部设备写入完成证明、隔离资源和下一合法 session。故障注入及进程清理只作用于 owned 作业；不支持路径须设备副作用前拒绝。
5. **机制与物理复用（P07/E10）**：各后端普通编译生成的实际 submit/commit/wait 覆盖、两轮 buffer/flag generation 与首轮/稳态/drain；失去状态记录后的边界与恢复锚点；无 logger 全局串行化。完整逻辑组模型单独不满足物理复用门。
6. **公共 ns/Perfetto 闭环（P01/P08、测试 §7–8）**：真实 raw 经范围匹配 proof 派生 ns，Trace Processor 逐条对应时间/来源/identity/flow，实际 UI 检查误差与泳道。验证不可分辨关系、独立域、partial 及补证重导；不重跑用户应用、不原地篡改旧 raw/判定。

建议维持当前实施顺序。每个最小样本先给出已证、未证和具体失效范围；无法闭合某项时返回具体输入、对象、SDK 限制及最小后续动作。无需为本报告增加接口、测试数量或新的状态台账。
