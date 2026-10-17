# R1：自动发现、编译插桩与适配边界独立设计评审

本次完整读取的三份主文档 SHA256：

| 文档 | SHA256 |
| --- | --- |
| `Profiler/docs/timeline_design.md` | `ef6d20936e0a879e1b9bde36c7cbf81e37d98ce3dd680c2388070bc7274327fc` |
| `Profiler/docs/timeline_testing.md` | `224a1c94c7748510a68054f1fa4a58b3e3ef34185dd168c64e2d86e6177786e4` |
| `integration/plans/timeline/goal_prompt.md` | `567234333175566f4056dc6b09db4a7ad7e3c4e5684f59d7d19dc5bc6b1d69b1` |

评审日期：2026-10-17。静态源码 HEAD：`775f7b44c879b515a71d2eb48f1196321d75786b`；三份主文档当时均有工作区修改，本报告以表中实际字节为准。评审任务名：`/root/timeline_design_compiler_review`。指定模型请求：`gpt-6.1-sol`、`xhigh`；实际 serving 版本未向本席暴露，记为**未知**，不由请求名称推断。

本轮只读文档和源码，另查 LLVM/MLIR/PTX 官方语义。没有运行产品 import、build、test、oracle、SSH 或任何设备实验；没有读取其它 reviewer 报告；没有改产品或设计。本文不是三后端设备可行性通过证明，也不冒充目标合同第 7 节要求的实现后最终代码走查。

## 结论

**可以开始实现，起点应限于设计 §8.5 / 测试 P01 的真实纵向可行性门。** 不需要推翻公共意图、后端执行 manifest、后端解码、公共验证与 Perfetto 的分层。当前材料没有证明三后端完整目标都可实现，也没有证明某一目标在现有硬件上不可能；把这两种判断分开很重要。

本席确认 **0 blocker、0 major、2 minor 文档问题**。核心困难是下列高风险 verification gaps，不能因文档已经提出正确要求就视为已经解决：优化后的源身份、计算和 timer 的排序、NVIDIA partition 观察者、GCU 晚期边界及异步结构、Ascend 区间与动态 actor 关系。它们应在全量资格前用各后端真实编译对象和设备记录闭合。若某项失败，应返回准确机制/环境阻碍，继续其它后端工作；不能以 count、checkpoint、合成记录或漂亮截图替代。

两处 minor 可在实现准备时修订，不必阻塞纵向原型。开始全量矩阵、冻结用于资格验收的公共接口版本或宣称整体可行之前，至少应交付 V01–V05 的最小证据；第一后端跑通后先定一个小接口版本、再由第二/第三后端修正的次序可以保留。

## 已确认问题

### R1-M01 — minor：NVIDIA 现状描述遗漏已存在的自动 interval 路径

- **文档位置：** [设计 L23](../../../../Profiler/docs/timeline_design.md#L23)、[L126](../../../../Profiler/docs/timeline_design.md#L126)。L23 把“普通 unannotated kernel 的自动时间插桩”整体列为当前缺口，L126 又写成先把 discovery 接到 scope，容易让实现者把已有 advanced 自动 scope 当作不存在。
- **具体失败情形：** 工程实现重复建设 discovery/自动 scope，或错误地把“新增自动 scope”本身当成本轮关键进展，却忽略全局时间尺度、晚期 manifest、异步路径及新版记录协议仍未完成。它影响基线和复用判断，不是现有 timeline 功能的正确性漏洞。
- **实际源码证据：** [observations_nvidia.py L367–373](../../../../Profiler/python/flagtree_profiler/observations_nvidia.py#L367) 已接受 `automatic=True` 并切换到自动 sites；[hooks/instrumentation.py L394–409](../../../../Profiler/python/flagtree_profiler/hooks/instrumentation.py#L394) 已在 `ttgpuir_complete` 注册自动 scope pass；[AutomaticScopes.cpp L295–319](../../../../Profiler/Dialect/lib/ProtonToProtonGPU/AutomaticScopes.cpp#L295) 对普通编译操作自动生成 begin/end。另一方面，[profile.py L1418–1427](../../../../Profiler/python/flagtree_profiler/profile.py#L1418) 说明公开 `detail="auto"` 当前实际走 census；[TargetInfo.cpp L13–33](../../../../Profiler/Dialect/lib/ProtonGPUToLLVM/ProtonNvidiaGPUToLLVM/TargetInfo.cpp#L13) 及 [observations_nvidia.py L132–147](../../../../Profiler/python/flagtree_profiler/observations_nvidia.py#L132) 仍为 SM-local clock、无已验证 ns 换算。因此已有 advanced 路径不等于本轮交付。
- **最小修改：** L23 改为“已有 advanced 自动/手工 Proton source-control interval 及源关联；缺公开 timeline 入口、合法优化后 manifest、目标 timer/ns 证明、partition/异步观测和动态关联”。L126 改为“复用并扩展现有自动 scope 接入”。不把已有 raw-cycle interval 升格为已验收 timeline。
- **验证：** 文档对照上述调用链即可；无需为这条文字修订运行设备。

### R1-M02 — minor：逐份 UI 步骤对没有 flow 的普通 trace 提出不存在的操作

- **文档位置：** [测试 L120–130](../../../../Profiler/docs/timeline_testing.md#L120)。它允许六份 trace 来自普通算法、cold/warm 等场景，但“每份操作”中的 L127 要点一个有证据 flow。L120 的“本机真实 Perfetto UI”还与 [L14](../../../../Profiler/docs/timeline_testing.md#L14)、[L105](../../../../Profiler/docs/timeline_testing.md#L105) 和 [合同 L94](../goal_prompt.md#L94) 的浏览器在服务器 Docker 约束存在文字歧义。
- **具体失败情形：** D01/D02 等合法顺序输入具有多个真实内部区间但本来没有动态 async edge；UI 检查员要么无法完成逐份清单，要么误以为应为它补一条 flow。后者直接违背不猜关联的目标。浏览器位置也可能被不同执行者理解为不同要求。
- **支持证据：** [设计 L118](../../../../Profiler/docs/timeline_design.md#L118) 只允许有动态关联及时钟证据的 edge 画时间箭头；[execution_nvidia.py L223–228](../../../../Profiler/python/flagtree_profiler/execution_nvidia.py#L223) 和 [execution_ascend.py L347–350](../../../../Profiler/python/flagtree_profiler/execution_ascend.py#L347) 明确现有静态结构/记录 sites 不是动态依赖证明。普通顺序输入不应因 UI 清单而产生 flow。
- **最小修改：** L127 写成“对有动态 flow 的 trace 点击并核对端点；无 flow 的普通 trace 核对确实没有伪造 flow。每后端至少一份真实异步 trace 必须执行端点操作。”L120 写“在规定的服务器 Docker 中运行标准 Perfetto UI”，若“本机”原意另有所指则明确。多区间、循环、标准 UI、每后端异步验收均保留。
- **验证：** 冻结 UI 清单时给无 flow 普通 trace 与有 flow 异步 trace 各一条适用步骤；设备正例仍按原目标执行，不由 fixture 代替。

## 当前代码支持的判断

| 链路 | 已看到的可复用事实 | 不能据此认定的事情 |
| --- | --- | --- |
| 公共选择 | [automatic_plan.py L64–219](../../../../Debugger/python/flagtree_debugger/automatic_plan.py#L64) 根据实际 compiler op ID、control ancestry 和有界预算选点，区分控制容器、重复体、直接/后代覆盖 | 这个早期 ID 没有自动成为优化后执行区间、真实 observer 或完成语义 |
| NVIDIA | `ttgpuir_complete` 自动 scope；随后通用 ProtonGPU/LLVM lowering；设备 program predicate；已有 raw ring decoder | scope pass 的运行不证明最终算术被包住；现有 32/43-bit ring、SM clock、固定 warp 0 不自动满足新时间/async 合同 |
| Enflame | [compiler.py L535–575](../../../../Debugger/python/flagtree_debugger/compiler.py#L535) 在 TTIR 建表、自动选点并插桩；[Passes.cpp L3805–3942](../../../../Debugger/lib/Instrumentation/Passes.cpp#L3805) 调实际 SDK global timer，保留 64-bit 读值并拆成两个 i32 | 这是优化前后的边界问题，不是把早期 table 改名 manifest 就能解决；SDK timer 的固定频率/共同 epoch 和异步 token 尚未由此建立 |
| Ascend | [ascend_compiler.py L20–94](../../../../Profiler/python/flagtree_profiler/ascend_compiler.py#L20) 有真实 per-compilation driver handoff；[L250–324](../../../../Profiler/python/flagtree_profiler/ascend_compiler.py#L250) 留存原输入、适配输入与编译作业；实际 LLVM pass 可观察 actor 及既有 wait | [AscendLateObserver.cpp L1002](../../../../Profiler/llvm/AscendLateObserver.cpp#L1002) 的 phase 是 `post_actor_lowering_pre_scalar_optimization`；它仍不是最终机器边界证明。普通 operation 当前是 `tick,tick` checkpoint（[L671–690](../../../../Profiler/llvm/AscendLateObserver.cpp#L671)），不能成为多区间证据 |
| 源来源 | [source_origins_nvidia.py L48–125](../../../../Profiler/python/flagtree_profiler/source_origins_nvidia.py#L48) 保留多候选、partial 和不可用源码；[execution_enflame.py L204–209](../../../../Profiler/python/flagtree_profiler/execution_enflame.py#L204) 区分 exact ID 与 debug location 候选 | 行号、fused location 和二进制登记时文件快照不证明 exclusive instruction/cost ownership；源码文件快照甚至明确标 `compiled_text_alignment=not_independently_verified` |
| 公共合同 | `observations.py` 对 identity/clock/association 做显式检查；`source_census.py` 明确 counts 没有时间；旧 Ascend census v3 有独立 cache-line 布局 | 新 timeline 数据模型、整数/有理数转换、动态多操作依赖和发布协议仍需版本化实现；不能直接沿用旧 float 时间计算或旧 schema 便声称满足设计 |

## Verification gaps：必须用真实链路闭合的风险

这些不是“已发现产品 timeline bug”。主文档本来就标待实现，且 §8.5 / P01 已要求先实证。本席不把“尚无实现细节”直接定为 blocker，也不因允许改 SDK 就假定必能改通。

### V01 — 源区域经过 fusion / split / 消除 / loop pipeline 后的身份及计时归属

**位置：** 设计 L68、L76–84、L146、L151，测试 P03（L142）。

**缺少什么：** 一个可执行的 manifest 合同及至少一个真实 producer。当前路径通常是早期选 op、插带副作用的 marker，再在后期保留/读取它，或从 debug location 提取候选；这两者都不能单独证明“这个最终区间只对应原某源操作”。Ascend census marker 实际携带 source ID 和六个 program/grid SSA 值（[AscendProgramAnchor.cpp L123–140](../../../../Debugger/lib/Instrumentation/AscendProgramAnchor.cpp#L123)），是很好的控制位置证据，但只有 before marker，不能用来推导原 op 的 end 或成本。NVIDIA 目前按实际 TTGIR candidates 的 ordinal 生成 scopes，不是通用的跨优化 lineage 系统。

**具体风险：** `a=x*y; b=a+z` 融成一个执行操作后，两个 source origin 不能让同一个观测区间被算作两份独立内部阶段；一个源循环体被拆到 prologue/steady-state/epilogue 后，site occurrence 也不能直接成为源 iteration。若为保留源节点而过早加入强 marker，可能改变原本会发生的 fusion/pipeline，最终 manifest 描述的是插桩后结构，需明确它与 ordinary 编译的关系。

**最小设计补充/实现交付：** 在第一版接口冻结前写一个很小的 schema：logical region 的 namespace、执行 site 的 binary 身份、M:N origin 集合、preserved/fused/split/eliminated/unknown 状态、实际 begin/end anchor、observer、控制路径和循环映射证据。对 fused 区域导出一个真实执行区间并列多个 origin；不能复制 duration 后把它们当不同内部阶段满足“两区间”。对 split 区域保留实际不同区间；没有边界的源意图明确无法单独计时，不静默更换无关来源。

**最小验证：** 每后端保普通与插桩编译对象，选实际生成 fusion、split/软件流水及动态 loop 的小数学实例，对照源 inventory、晚期 manifest、最终 IR/ISA 与 raw records。至少展示一个真实被消除/合并而不造 event 的源区域。公共 verifier 可用 CPU 负例补 M:N、丢 anchor、错 binary 的拒绝检查，但不能替代这三份真实 producer 证据。

### V02 — timer/logger 的副作用不等于被测计算的顺序保证

**位置：** 设计 L66–70、L146、L151；测试 L53–54、L71、P03。

**已知事实：** [ProtonOps.td L16–18](../../../../Profiler/Dialect/include/Dialect/Proton/IR/ProtonOps.td#L16) 给记录操作声明内存读写；NVIDIA clock inline asm 标 side effect（TargetInfo.cpp L32–33）；Ascend `MOV SYS_CNT` 标 side effect，但没有被测计算操作数（AscendLateObserver.cpp L112–115）。现有 logger 的 volatile store 也只是 logger 存储语义。LLVM 官方规定 volatile 相对于非 volatile 操作仍可重排；MLIR 官方说明纯 SSA 运算可在满足 dominance 时重排、消除和重建。因此“marker 不能消失”与“计算不能越过 marker”是两件事。[LLVM volatile](https://llvm.org/docs/LangRef.html#volatile-memory-accesses)、[MLIR side effects](https://mlir.llvm.org/docs/Rationale/SideEffectsAndSpeculation/)。

**具体风险：** 普通纯算术被移到两次 clock 之外；begin/end 保留在 loop 内而实际被测计算被 hoist；后端 machine scheduler 使源码相邻关系不再是已声明的观察边界。最终 kernel 数值、两条 timer 和正 duration 都可能仍然正常，测试若只数事件无法识别。

**最小补充：** 每后端声明它如何保持“timer 前→被观察路径/工作→timer 后”的实际编译顺序，以及约束止于哪一层。可以在足够晚的合法边界插入，或用真实 def-use/control chain 等通用 lowering；单加 `volatile`、memory clobber 或 begin 支配关系不应成为默认正确性证明。不能用额外 completion barrier 代替所需约束。

**最小验证：** 一个有依赖纯算术循环、一个 load/compute/store 区域、一个原 async wait；普通/插桩 IR 和最终 ISA 逐边界核对，确认不消失、不跨边界、不移出动态循环、没有新完成屏障。再用不同 runtime 次数的同一 binary 检查记录重复。稀疏/密集观测比较保留原计划，不以它代替编译顺序检查。以上必须在真实目标工具链完成，本轮静态评审没有代跑。

### V03 — NVIDIA 现有自动 interval 与异步 partition 路径不能直接等同

**位置：** 设计 L48、L102、L114、L126；测试 P01/P03/P04/P07。

**已知事实：** [AutomaticScopes.cpp L75–85](../../../../Profiler/Dialect/lib/ProtonToProtonGPU/AutomaticScopes.cpp#L75) 只在 `census` 模式允许 WarpSpecialize/Partitions 父结构，普通自动 interval 不会选择该 worker partition 内操作。虽然 [ProtonToProtonGPUPass.cpp L89–124](../../../../Profiler/Dialect/lib/ProtonToProtonGPU/ProtonToProtonGPUPass.cpp#L89) 有 worker record lowering，但“有 lowering”不代表 automatic planner 已为它生成合法 sites。现有 `lower_request` 只选 warp 0（observations_nvidia.py L347–352）；物理 linear CTA helper 还明确处理自己的 CTA/cluster 假设（[Utility.cpp L68–94](../../../../Profiler/Dialect/lib/ProtonGPUToLLVM/Utility.cpp#L68)）。

**具体风险：** 普通矩阵流水的生产者在 worker warps，观察却只来自 default/warp 0，仍画出“producer/consumer”泳道；或将当前 clock64 换 globaltimer 后继续用 43-bit packed ring、旧 decoder/clock 说明，形成 ABI/时钟身份混用。相关设计目前正确地要求恢复实际主体及版本化，尚无落地证据。

**最小实现交付：** 针对本次 RTX PRO 6000 的实际 ordinary lowering 选择一个真实 async 机制，给出 observer 到逻辑 program/partition 的 manifest、对应 logger namespace、timer getter/位宽与新 ABI；不要求为所有 PTX async 机制一次性建完框架。一个实际 observer 的 submit/wait 两条有语义依据泳道可满足设计目标，不必伪造第二硬件 engine。

**最小验证：** 两个 logical program、至少两轮真实 group/buffer 复用的 ordinary async 数学；证明提交/commit/wait 覆盖集合。PTX 的 `cp.async.commit_group` 是每线程建组，`wait_group N` 只保证相应较早 groups 完成，不能按“最近一个 submit”配对；空组、部分 wait、reuse 的状态机负例可合成补充。[PTX async 语义](https://docs.nvidia.com/cuda/parallel-thread-execution/#data-movement-and-conversion-instructions-cp-async-commit-group)。最终设备记录还须证明 actual target globaltimer 单位/作用域和两条目标泳道可比较；不能用 PTX 名称或文档中的 nominal 支持代替本机证明。

### V04 — GCU：需要明确可插入的晚期执行层，而不仅是已有 SDK timer

**位置：** 设计 L104、L116、L127、L146、L190–192；测试 P01/P03/P07。

**已知事实：** 已有 timer 是真实 SDK helper，patch 明确只接受实际 `gcu300` 目标、46-bit tick 且 `frequency_verified=False`（[enflame patch L9–33](../../../patches/enflame/flagtree-source.patch#L9)）。TTIR pass 后仍有厂商 GCU lowering；当前补丁 L38–47 只保留打印位置，不是证明晚期插桩 hook。现有 [compiler.py L486–529](../../../../Debugger/python/flagtree_debugger/compiler.py#L486) 的动态 interval 请求限制为一个 logical program/actor 0。公开 recipe 也诚实限定为无 ns 校准的 advanced raw-tick interval（[README L120–123](../../../patches/enflame/README.md#L120)）。

**具体风险：** 早期源码区域被 SDK 分拆/融合/调度后，现有 TTIR timer 不能包住所声称的执行区域；移到更晚层后 SDK 又不开放合法 call/logger lowering。另一条独立风险是 timer 可读但无足够精度的单位/跨 observer 关系，或 ordinary Triton candidate 根本未产生可观察异步 submit/wait。当前代码不能保证这些能一起成立。

**最小验证：** 在该实际 C200 编译链上先交付一份标清阶段的 hook/SDK 扩展清单，以及两源区间的普通数学纵向样本：源→GCU/LLVM→真实对象→raw。单独确认一个真实 async 机制的 submit/wait/completion、操作集合与两轮 generation；timer 单位/epoch 证据独立留存。频率未知时可继续做其它工程和 raw-tick 调试，但不得宣称该后端满足 P01 或最终资格。若 SDK 确实不给必要层访问，应记录具体缺失接口及已尝试通用扩展；这才是硬阻碍证据。

### V05 — Ascend：晚期控制 bracket 可复用，但通用多区间及动态 AIC/AIV 关系还需实做

**位置：** 设计 L86、L104、L115、L128、L158；测试 P01/P03/P05/P07。

**已知事实：** [AscendLateObserver.cpp L553–590](../../../../Profiler/llvm/AscendLateObserver.cpp#L553) 已在实际既有 set/wait 调用前后读钟；普通操作是单点 checkpoint，loop header 也是 control occurrence，不能自动配成完整循环体区间。Manifest phase 仍在 scalar optimization 之前。旧 census v3 的 64-byte actor 对齐在 [ascend_census.py L59–68](../../../../Profiler/python/flagtree_profiler/ascend_census.py#L59)，但动态 log 的 `header4_record8_v1` 布局是另一条路径，不能以 census 修复经验替代新 log 的发布验证。`cann_source_clock.py` 区分频率和共同 epoch，也没有因此自动建立跨 actor 时间坐标。

**具体风险：** 把两个 checkpoint 连线称“算术执行时间”；用静态 SET/WAIT callee/channel 推断当前 generation；或复用旧动态 header 后误以为已有 census v3 对齐就没有多主体可见性风险。源码/actor split 后 before marker 有一对多，并不表明每个 split actor 都拥有原完整源区域的开始与结束。

**最小验证：** 一个普通有 runtime loop 的数学 kernel，两个实际可计时区域，经最终对象核边界，并有不少于三次真实 occurrence；一个 ordinary 异步样本对齐真实 actor/token/flag 与 buffer generation，覆盖首轮、稳态和 drain。以新 timeline 的真实物理布局检查独立 cache-line、commit/loss/canary；保留 v3 和旧 ABI 回归。用相同 getter/域证明目标泳道所需 epoch，不能用同频率或同 invocation 字符串替代。

### V06 — 首末 program、预算与缓存：要接到真实 launch，不应靠预跑发现

**位置：** 设计 L46–53、L146、L174–176；合同 L36、L79–83；测试 E02/E07/P10。

**已知事实：** 当前 GCU/Ascend interval 编译计划通常固定单个 program；NVIDIA 的 program selection 也使用编译期属性。它们尚不是“实际 launch grid 的首末两个 logical program、按 invocation 隔离、先 admission”的新协议。当前 Ascend 已有插件/adapter 内容哈希 cache key（[ascend_compiler.py L412–458](../../../../Profiler/python/flagtree_profiler/ascend_compiler.py#L412)），NVIDIA/GCU 有模式版本，但不能由此认定新的 SDK/getter/async rule 内容身份都已进入内存和磁盘 cache。

**具体风险：** 同一 specialization 用另一个 grid 再启动，却沿用上次末 program；动态 shape 触发实际多个 actor 后扩张 scratch 超预算；为找到末 program 预跑脚本；更换 timer 实现或原地 SDK 升级后仍复用旧 binary。文档已经正确禁止这些做法，需检查真实 runtime/compiler 分工。

**最小验证：** 同一 kernel specialization 改 grid，包含 1D/2D、单 program、零 grid 与 tail，保存实际选中坐标/计划/admission/raw；用 host-once oracle 证明没有重放。显式测试旧 count 与新 timeline 互切、getter/plugin/SDK 实体内容原地改变及 symlink 切换，分别验证 JIT 内存命中与磁盘命中行为，不清旧 cache。编译可在脚本这一次运行内完成两个纯编译阶段，不必为坚持单次脚本而省掉 manifest 协商。

## 合理可行的部分及适配成本判断

1. **公共意图和后端执行计划分开是必要边界。** 早期选择管“想看什么”，后端管“实际哪些 observer/控制边界能记录”，共同预算在实际物理计划后 admission，符合三个编译栈的现实差异。现有小型 `_backends.py` 只覆盖 capture 扩展，尚不是 timeline compiler adapter；扩展它或另建小合同均合理，不需要先造完整插件生态。
2. **统一解码后事件、保留不同物理 ABI，是实际可行的复用方向。** NVIDIA ring、GCU publication 与 Ascend cache-line 布局不能强行统一。身份、配对、单位换算、loss、依赖集合和 exporter 则适合公共验证。允许公共新概念有理由地版本化修正，比用 permissive dictionary/厂商 if 隐藏差异更可审核。
3. **动态集合模型没有明显过度工程。** PTX 实际 group/partial-wait 已足以说明一对一 producer→consumer 不够。设计没有要求三后端全实现每种机制，P07 也区分真实机制和 fixture；为当前三后端建最小 operation/group/generation 模型合理。具体厂商机制识别与覆盖集合求值必须由后端承担，公共层只做身份/代际/集合一致性验证。
4. **时钟规则和证据门合理。** 不把同频率当共同 epoch、不对未同步域统一归零、不把 count 造 duration，直接避免主要可视化误导。已知频率/未知 epoch 的独立文件只能是诚实 partial，文档没有把它当作跨主体 async 的完成捷径。
5. **三后端目标没有被悄悄降低。** 设计 L11–16、L98、L168、L225，合同 L45–53、L145–150 都要求真实内部多区间与每后端动态异步、共同时间尺度和 Perfetto。允许软件 submit/wait 语义泳道、不强求所有硬件 busy，是可实现的产品范围；若 ordinary kernel 确实生成 async，这不等于把顺序源码框换名。若没有真实 async，则不能借“软件 observer”措辞过关。
6. **资格矩阵很重，但不是编译接口过度抽象。** 单一公开入口、一次脚本执行、三后端/两配置/运行时循环/原数值与旧缓存回归本身会有相当成本。应严格按 P01 先证实机制，再扩矩阵，避免尚未知 GCU clock/async 路径时就进行上百次资格运行。无须为本轮增加第四芯片、通用驱动 DSL 或所有机制的模拟器。

## Optional：可改善实施效率，不作为通过条件新增门槛

- 第一条真实链打通后，把 manifest 和公共 normalized event 各保留一页版本化字段约束及一份真实小样本。不要在第一次真实调用者出现前冻结很大的抽象 API。
- P03 的报告分别列“origin 关联”“执行边界”“是否能分摊/独占成本”；用户最容易把它们看成一个结论。源标签可以多来源，区间时间不能因此被任意分摊。
- 为 capability 使用结构化的 verified/unsupported/unverified 状态及证据引用；可沿用现有数据类型，不必专门引入远程 registry。不同阶段发现的能力细化要留原状态，避免失败后改资格。

## 阅读与未覆盖范围

完整读取三份主文档。静态重点阅读/核对 `Debugger/python/flagtree_debugger/automatic_plan.py`、`compiler.py`、`Debugger/lib/Instrumentation/Passes.cpp` 的 timer/interval 构造、`AscendProgramAnchor.cpp`、NVIDIA `AutomaticScopes.cpp`、Proton→ProtonGPU→LLVM 的记录/timer/program 关键路径、`hooks/instrumentation.py` 的注册与 metadata、`observations.py`、`observations_nvidia.py`、`source_origins_nvidia.py`、`ascend_compiler.py`、`AscendLateObserver.cpp`、`ascend_census.py`、各 `execution_*` 中源/静态语义边界，以及三后端公开 patch/recipe 的相关部分。另定位 `source_census.py`、Ascend clocks 等合同及限制。

未完整审计所有 runtime、allocator、异常/并发路径、源快照生产者、打包脚本或 Perfetto exporter；没有审计历史证据以认定本轮硬件能力，没有读其它评审。真实 SDK 可插桩层、设备 getter 的最终 ISA/单位/epoch、异步机制生成、发布可见性、数值保持、稀疏/密集扰动与真实 Perfetto SQL/UI 均未运行，因此状态仍是**未验证**。

**给实现者的明确建议：可以启动 §8.5 的实现与真实验证；先修两处 minor，先闭合 manifest/边界及各后端最小 async/clock producer，再冻结资格版本和启动全量资格。设计审查通过的是工程方向和验证顺序，不是三后端完整交付可行性的既成结论。**
