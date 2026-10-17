# R2 独立设计评审：运行时、时钟与动态依赖

## 结论

**有条件可开始实施。** 当前设计已给出足以指导实现的小型职责边界和安全条件，没有发现需要先改设计才能继续开发的 confirmed blocker、major 或 minor。条件是严格执行现有 P01：三个后端分别取得真实纵向证据后，才能进入各自最终资格；不能把本报告作为时钟、动态关联、发布协议或 Perfetto 已经可用的证明。

这个判断针对设计合理性，不是代码验收。三后端全部达到完整产品目标仍有实质设备验证风险，尤其是 GCU 异步机制、Ascend 新 logger/actor epoch，以及 NVIDIA 新 timer 与记录 ABI 的一致性。现有原语证据明确没有覆盖这些问题；设计没有隐藏这一点。

## 输入与独立性

基线提交：`b3e4a7fcb06a4bbf59ee5312c5c4401c11243d5e`。实际读取并以 `sha256sum` 复核，与 `INPUT.json` 一致：

| 输入 | SHA-256 |
| --- | --- |
| `Profiler/docs/timeline_design.md` | `51ee7333e3f8eb5ca51ce3d1ba6730ed98f29926e55e018b4af5f433d060ec99` |
| `Profiler/docs/timeline_testing.md` | `e534528b554ea516bbebbe1e1dd9515b0d1f6bbde6c1c9c82d0086b6969511cc` |
| `integration/plans/timeline/goal_prompt.md` | `08b854213cd214105932e94ff8f2c328ba7ab9b5d4f6a4c46b9f0c80b042ba40` |

完整阅读上述三份文件及 `integration/evidence/timeline-primitives-r001/README.md`。另只读抽查 `profile.py` 的最终化、`hooks/instrumentation.py` 的缓冲与逐 launch 导出路径、NVIDIA/Ascend decoder 的记录与时钟声明。没有阅读旧评审或其他 reviewer 报告，没有连接服务器、运行产品 import/测试或修改产品与设计文件。除本报告外不写评审产物。

## 已确认设计缺陷

- **Blocker：无。**
- **Major：无。**
- **Minor：无。**

以下是有明确触发场景的待证假设与实施检查点，不冒充已经确认的设计错误。最小处理均可复用现有测试，不需要增加独立数学矩阵。

## 生命周期与异常路径

设计第 86–88、220–240 行把设备发布、调用身份、原 stream 完成依赖、D2H 和主机导出分开；第 236 行还限制全部 pending owner 的数量和字节，避免“每次调用都在预算内、累计在途分配却无上限”。第 238–240 行明确超时不是写者终止、未提交可以回收、已提交无完成证明不得回收，并允许隔离资源后令 session 失败。这些条款能够形成安全实现，没有要求靠强同步来换安全。

**待证 L1：实际运行时是否确实改成独立 owner。** 触发场景是 stream A 的调用尚未完成，stream B 又启动同 specialization 或不同 grid；随后关闭 capture 或注入 D2H 异常。现有 `hooks/instrumentation.py:124` 将分配结果放在共享 `self.buffer`，第 600–604 行拒绝共享缓冲并发，第 690–711 行在退出 hook 中执行导出；census 路径第 729 行显式同步 stream。现有 `profile.py:1971` 的 finally 继续走 session cleanup。它们说明需要真正改造 owner 和清理的交接，不能仅延后 exporter 调用。设计第 88、236–240 行已准确要求此改造，故这是实现缺口，不是设计自相矛盾。

最小处理：执行 testing 第 174–177 行现有场景，保留每个 invocation 的 buffer、完成依赖、提交/host-wait 顺序和失败阶段；确认 session cleanup 不释放仍在写的 owner。pending 超预算测试必须在被拒调用产生设备副作用前失败，不能通过清空队列来掩盖。异常隔离的 session 不必原地恢复，testing 第 176 行对此已有合理限定。

**待证 L2：后端 SDK 完成条件的实际范围。** 某 SDK 只提供 context/device 范围同步时，最终化可能等待无关工作，且基于主机超时不能安全中断原生调用。设计第 238 行要求说明范围与并发限制，goal 第 98–99 行又区分自有进程清理与设备任务终止，原则上相容。最小处理是每后端记录具体完成 API、保护的 writer 集合、D2H 所属 stream 与不能取消时的隔离策略；采用现有 E05/§8.3 分阶段故障检查。不得把进程已 reap 单独当作设备缓冲已可复用的证明。

## 三后端时钟与 epoch

设计第 94–108、164、176、204 行的方案是可实施的：先整数减 origin，再有理数换算；频率、epoch 与适用 capture 分开；独立域分 trace；截断计数器即使 end≥start 也要求独立回绕约束；先后与重叠依端点不确定区间判断。这避免了本领域最危险的几种伪时间线。Perfetto clock snapshot 也没有被误用为频率或共同 epoch 的来源。

**待证 C1：NVIDIA timer 与实际记录位宽。** 触发场景是把 64 位 getter 接到旧 packed 43 位记录，再对长区间或跨 SM 事件直接导出。`observations_nvidia.py:18–25` 当前只接受 32/43-bit，设计第 250 行已明确 getter 与 packed record 的区别。最小处理是按第 100 行证明完整有效位宽、唯一回绕窗口及跨 SM scope；无法证明跨 SM 时应分域，且不能据此宣告所需跨域异步样本通过。此项是 P01/P06/E09 的硬验证前提，不是已确认的硬件不可能。

**待证 C2：Enflame 的 ns 比例与可比较范围。** 触发场景是依据约 0.9774–1.0223 ns/tick 的现有界限，把短 submit/wait 端点当作确定先后，或把不同 observer 的相同频率当作共同 epoch。设计第 104、108、251 行已经禁止两种推断。最小处理是保留比例界限、独立留出点与有效窗口，证明目标异步例子实际涉及的域关系；短事件分辨不出来时采用更粗的真实区域。无需强求先得到精确 1 ns/tick 的结论。

**待证 C3：Ascend actor scope 与本次 epoch。** 触发场景是将旧 SYS_CNT/50 MHz 资料直接套到实际 910B SDK 或 AIC/AIV 两 actor。设计第 25、104、164、252 行明确拒绝这种继承；当前 `observations_ascend.py` 的默认 clock 也是 actor-local/instance-local，不能当跨 actor 对齐证据。最小处理是 P01 中同时保实际 getter/对象来源及本次 actor 比较证明，P06 验错 target/epoch。旧 census 布局或时钟通过均不能替新 timeline 通过。

## 动态依赖、发布与损失

设计第 112–118、166–168、205、227 行没有把所有异步机制压成一条 producer→consumer。submit 集合、commit 分组、部分 wait、多消费者、slot generation、丢失后的恢复锚点均有位置；逻辑 token 允许由编译器沿真实控制路径维护，而非必须取得厂商硬件 ID。这是合理且必要的可移植边界。

**待证 D1：逻辑 generation 是否真正对应机制状态。** 触发场景是条件分支跳过一次 submit、一次 wait 覆盖若干先前 group，或 commit 记录丢失后仍有后续 wait；单纯按日志序号配对会把后来某组配到错误代。设计第 168、205、227 行已要求沿机制语义维护状态，公共层又不能只信后端 verified 标记。最小处理是复用 P07/第 178 行负例检查，给每条实际 edge 保覆盖集合和全部必要 raw 引用；只有明确恢复锚点才能在丢失后恢复关联。无需让三后端硬件都实现每一种机制，合同 fixture 与真实机制的范围已经正确分开。

**待证 D2：多写者发布与物理可见性。** 触发场景是两个 actor 共享 cache line、payload 尚未可见而 commit/cursor 已被主机看见，或一个选定 observer 实际含多个写者。第 86、128、158 行保留后端物理布局与对齐责任，第 203 行要求全部 raw/proof，而 testing 第 160 行明确新 timeline 不能继承旧 census v3 通过。最小处理是按 P05 验真实 writer、padding、commit 顺序和 canary；仅在 decode 中检查 header 算术不等于设备发布通过。

## Perfetto 可行性与验收

按设计第 259–274 行，标准 TrackEvent、调用/program/observer 层次、独立重叠轨道、稳定 ID、source/proof args 和域分 trace 之间没有看到格式层面的冲突。异步软件 observer 区间与 native engine 活动分开命名，不能证明 edge 时保表格/候选，不要求 Perfetto 替生产者猜测硬件语义。

**待证 P1：实际导入与 UI 而非仅 protobuf 可解码。** 触发场景是两个非嵌套异步区间被写入同一 B/E stack、flow 端点导入时错配，或 source/clock args 在 UI 中不可见。设计第 272 行和 testing 第 105–130 行已分别给出避免办法与可执行验收。最小处理是用固定工具版本核逐条 canonical event→slice/flow 对应，再对每后端真实异步 trace 点击两端、查看 generation 与来源；不以 importer 返回 0 取代这些检查。设计评审没有实际执行导入/UI，故这里不作通过声明。

## 适配成本与整体判断

适配成本描述是诚实的。设计第 134–158、180–186、220–242 行保留目标匹配、晚期 pass、隐藏参数 ABI、物理 decoder、timer、完成条件与机制映射在后端；公共层负责身份、预算、时钟算术、依赖完整性和一个 exporter。没有用统一物理布局或 warp/SM 树掩盖 Ascend/GCU 的差异，也没有承诺第四芯片“加配置即可”。允许发现新公共事实后版本化扩展，且不要求零公共 diff，避免把不可表达的语义藏进字典。

这个工作量明显超过新增 exporter：需要编译、ABI 与运行时联动。现有证据只使继续调查和开发合理，不能使全三后端交付时间可预测。设计第 190–192、255 行的分层放行，以及 testing P01/§8.3 的失败留痕，能够在全量矩阵前暴露核心障碍，故验收在步骤和判定上可执行。

**最小设计修改建议：无必需项。** 实施时把上述完成 API、状态机异常转移、clock proof、机制覆盖规则落实为设计第 194–208 行要求冻结的 schema/接口实例即可；不需要为本轮评审另外增加框架或扩大矩阵。若任何后端 P01 未能闭合，应报告具体设备/SDK 阻碍并继续其余不依赖工作，不能用本报告的设计认可替代实证或降低完成条件。
