# R1：编译插桩、源到执行映射与时间/异步可行性独立评审

结论：**有条件可开始实施**。设计的分层、语义限制及阶段放行合理；没有发现可由本次输入直接确认的 blocker、major 或 minor 设计缺陷。这里的“可开始”只允许继续原语开发及真实纵向验证，不代表任一后端已通过 P01，也不代表三后端完整目标已经证明可行。若把问题理解为“现在能否直接进入最终资格/交付”，答案是否定的。

## 输入与评审边界

- 基线提交：`b3e4a7fcb06a4bbf59ee5312c5c4401c11243d5e`；实际 `HEAD` 与 INPUT.json 一致。
- `Profiler/docs/timeline_design.md`：SHA-256 `51ee7333e3f8eb5ca51ce3d1ba6730ed98f29926e55e018b4af5f433d060ec99`。
- `Profiler/docs/timeline_testing.md`：SHA-256 `e534528b554ea516bbebbe1e1dd9515b0d1f6bbde6c1c9c82d0086b6969511cc`。
- `integration/plans/timeline/goal_prompt.md`：SHA-256 `08b854213cd214105932e94ff8f2c328ba7ab9b5d4f6a4c46b9f0c80b042ba40`。

三份文件完整阅读，三项实际文件 hash 均与 `round2/INPUT.json` 相符。设计及测试文档属于该提交之上的评审工作区内容，故结论绑定以上 hash，不能仅用 HEAD 代表输入。

另只读 `integration/evidence/timeline-primitives-r001/README.md`，并有限核对现有 `AutomaticScopes.cpp`、`hooks/instrumentation.py`、`observations_nvidia.py`、`ascend_compiler.py`。没有阅读旧评审或其他 reviewer 报告，没有连接服务器、import 产品、运行产品测试或设备实验，没有修改产品或设计文件。此次为独立 agent 静态设计评审，非最终实现代码验收；未检查全部后端实现或原始设备档案。

## 已确认问题

- **Blocker：无。** 未发现合同要求之间存在必然无法同时满足的矛盾。
- **Major：无。** 未发现已被现有输入证明错误、且会必然造成错误时间/关联的设计规则。
- **Minor：无。** 以下项目均是待验证机制或建议强化的交付表达，不将未实测本身计为设计缺陷。

## 编译与时间/异步的实际可行性判断

### V1：纯算术边界及晚期执行归属是首要机制风险，尚非已解决事实

触发条件：优化将所选纯算术跨过 timer/logger，融合、拆分或消除源区域，或者 worker partition 改变实际执行主体。此时正 duration 和早期 scope 元数据都不能证明计时覆盖了宣称的区域。

设计位置：设计第 68、146、202、212 行；测试第 142、159 行。文档已正确要求最终对象顺序与 M:N 映射，不接受 volatile/memory clobber、pass 被调用或源行本身作为充分证明，也允许扩大到真实可观测区域。

有限源码依据：`Profiler/Dialect/lib/ProtonToProtonGPU/AutomaticScopes.cpp:83` 起按编译操作选择候选，第 95–100 行的 partition 放行仍限定 census；`Profiler/python/flagtree_profiler/hooks/instrumentation.py:394–409` 从 `ttgpuir_complete` 接入自动 scope，第 528–563 行获取源 scope/inventory。这些是可复用的插桩入口与源信息，但不能独立提供设计要求的最终执行 manifest 和调度约束证明。

最小建议：不必改合同；首条 P01 在实现记录中明确“约束止于哪个编译层、之后各层如何保留”的具体机制，保留普通/插桩最终对象对照。若只能对较粗区域成立，则把合法 anchors 与 fused/split/unknown 写进 manifest，不能保留更细名称暗示细粒度归属。现有 P03/§8.2 已覆盖所需验证，不需要增加整套资格矩阵。

判断：通用编译扩展有合理实现入口，但三条编译链的最终顺序约束尚待真实对象证明；不能仅接上 exporter 宣称实现完成。

### V2：已读到 timer 不等于已具备目标时间坐标

触发条件：NVIDIA 64 位 getter 落入旧 43 位记录；GCU 校准范围不足以分辨目标阶段；Ascend 两 actor 虽有同频计数但不同 epoch；或截断计数跨越不可唯一解的回绕窗口。

设计位置：设计第 92–108、164、204、250–253 行；测试第 55、96、145、160 行。设计将频率、epoch、位宽、误差及有效窗口分开处理，要求整数域减 origin、保守判断端点关系，方向正确。分域文件明确是降级，不被用来满足需要跨域对比的异步门槛。

有限源码/证据依据：`observations_nvidia.py:18–29` 的旧 decoder 只接受 32/43 位、per-warp ABI；第 132–147 行仍描述 SM-local clock。原语 README 只证明有限手工 NVIDIA timer 与 GCU 约 `0.9774195–1.0222012 ns/tick` 边界，不证明新自动路径、共享 epoch 或精确固定频率。

最小建议：不必调整设计；P01 优先完成实际 getter→记录字段→decoder→clock proof 的整条位宽/单位核对，再选能被误差区分的真实数学区域。跨主体 epoch 未闭合时继续保留单域有效结果，但该后端异步时间比较保持未通过。

判断：这是决定某后端完整目标能否闭合的实证风险，目前没有任何理由把它当成已成功或已不可能。

### V3：普通 Triton 异步 lowering 能被观测，仍需逐机制证明

触发条件：软件流水把 submit/commit/wait 重排或合并；部分 wait 只完成部分 group；buffer/flag 复用；多消费者；又或者普通 Triton 候选根本没有生成异步机制。

设计位置：设计第 112–118、166–168、205、227 行；测试第 29–31、64–71、146、178 行。设计允许编译器逻辑 token，但要求它对应实际控制路径及机制覆盖集合，不用日志顺序猜硬件依赖；对 group、部分 wait、多消费者和丢失恢复的要求足以避免一对一模型强套不同架构。

有限证据：原语 README 中普通 GEMM 的 `cp.async`/commit/partial wait 只证明有值得继续研究的真实结构，不证明动态 token 关联；Ascend 新时间区间和 GCU 异步仍无此次通过证据。`ascend_compiler.py:74–88` 的既有请求接受 issue/wait/checkpoint 语义，也不是新配对 interval/operation-set 已实现的证明。

最小建议：无需新增测试类别；每后端 P01 的普通 baseline 先登记真实机制与覆盖规则，随后展示至少两轮复用及 drain。候选没有异步时按测试第 29 行预登记另一个合法普通算子；若机制确实无法观测则保留最小阻碍，不能靠手工 marker 或扩大术语含义满足门槛。

判断：设计对异步的表述可实现且没有过度承诺具体 ISA 能力，但三后端都成功属于尚未成立的工程假设。

### V4：逐调用缓冲区与延迟完成是必要重构，不能沿用同步导出行为

触发条件：下一 launch 覆盖同一缓冲区；旧逐 launch 同步改变两 stream 提交行为；取消/异常时写者尚未结束；或 pending owner 累积超预算。

设计位置：设计第 86–88、221–240 行；测试第 161、174–177、181 行。新设计给了调用 owner、session 总预算、完成证明、超时隔离和重导不重放规则，已足以形成可审查实现合同。状态机无需强制每次 launch 在 host 同步等待。

有限源码依据：`hooks/instrumentation.py:722–730` 的现有 census 路径在导出前显式 `ExternalStream(...).synchronize()` 并读共享 `self.buffer`。这是旧路径行为，不能因此断言新设计有缺陷；它说明新 owner/延迟导出确有实际工程工作，不能只复用导出函数再声称跨 stream 语义保留。

最小建议：按已有 E03/E05 验证实际 launch/host-wait 顺序、owner/buffer 标识及 completion 证据。已提交未完成时不能释放；明确隔离并失败的 session 依测试第 176 行在安全清理后以新 session 恢复即可，不必为“可恢复”强行原地重用。

## 可扩展边界及整体合理性

新增芯片的职责已经清楚：设计第 150–158、218–225、242 行将 target/SDK 匹配、合法编译 anchors、隐藏 ABI/logger、主体映射、物理解码、clock 和机制规则交给后端；公共层处理请求、admission、身份/引用/损失验证、时间算术及 Perfetto。设计没有承诺一个 adapter 或配置即可支持新架构，也没有掩盖新晚期 pass/同步模型/clock correlation 的成本。

该合同**不会在设计上迫使逐算子适配**：源区域意图依通用 IR/控制流，晚期 manifest 负责优化后结构，产品禁止按名字/shape/site 修补（设计第 31、146、242 行；执行合同第 34–39 行）。不过“普通可运行即必须满足本轮时间线门槛”是严格产品承诺，具体 lowering 失败仍必须作为产品失败处理。不能把实现尚未覆盖的结构事后变成资格外输入。

公共层**没有明显过度抽象**：允许不同物理 ABI 和后端语义规则；只统一消费者真正需要的身份、时钟与因果事实；第一条真实链后冻结小合同，第二/第三后端可以用新事实修订，禁止无调用者框架和以零公共改动压倒正确性（设计第 158、180–186、194–210 行）。重要的是继续执行第 227 行的双层验证边界：公共层能核完整性，真实机制含义仍需后端对象/SDK 证据，不能把公共 validator 的通过当成硬件语义证书。

入口、缓存、Perfetto 及资格计划与这些边界一致：缓存查询前取得实际依赖身份、capture epoch 不从旧 bundle 继承；未知必需语义显式拒绝/partial；多对多源导航不复制时间成本；Perfetto 不强制把重叠事件嵌进单栈；冻结前普通资格与 profile outcome 分离。这些约束足以指导实施，具体 API/schema 在首条真实链后冻结是合理安排，并非当前缺少空类或空接口的缺陷。

## 放行意见

可继续实施首条真实纵向链并调查其他后端原语；必须保持设计第 255 行的三级放行和测试第 183 行的分阶段结果。三个后端分别取得完整 P01 后，才进入各自最终资格；最终仍需全矩阵、实际 SQL/UI、安装回归及独立代码走查。当前不建议因本次无 confirmed finding 而跳过任何机制验证，也不建议为预先证明第四芯片扩展性增加抽象或新的设备范围。
