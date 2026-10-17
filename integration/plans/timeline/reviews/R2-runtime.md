# R2 独立设计评审：时间、动态依赖、记录与运行时

主文档 SHA256（完整阅读前后复核一致）：

| 文档 | SHA256 |
| --- | --- |
| `Profiler/docs/timeline_design.md` | `ef6d20936e0a879e1b9bde36c7cbf81e37d98ce3dd680c2388070bc7274327fc` |
| `Profiler/docs/timeline_testing.md` | `224a1c94c7748510a68054f1fa4a58b3e3ef34185dd168c64e2d86e6177786e4` |
| `integration/plans/timeline/goal_prompt.md` | `567234333175566f4056dc6b09db4a7ad7e3c4e5684f59d7d19dc5bc6b1d69b1` |

评审日期：2026-10-17。评审 agent：`/root/timeline_design_runtime_review`。请求配置：`gpt-6.1-sol` / `xhigh`；本席收到该请求，但不能从当前工具反查父席 spawn 回执；实际 serving 模型版本未暴露，记为**未知**。仓库阅读时 HEAD 为 `775f7b44c879b515a71d2eb48f1196321d75786b`，上述三份文档含未提交修改，本报告以上述字节为评审对象，而非仅以 HEAD 为对象。

## 结论

**建议可进入实现，先严格完成设计 §8.5 / 测试 P01 的三后端纵向验证；无需因已确认合同矛盾而先重写设计。** 本次未发现达到 confirmed blocker、major 或 minor 标准的设计错误。这个结论是“设计允许形成合理实现”，不是“三后端技术可行性已经证明”，也不是设备、时间线或最终验收通过。

设计对软件经过时间、异步提交、wait 和完成观测的区分合理；没有把内部时间线要求偷换成硬件引擎 busy。`timeline_design.md:11–16,59–68,118` 与合同 `goal_prompt.md:43–60` 的必达目标一致：三后端仍须有真实内部区间和真实异步动态解释，未知频率、独立域分文件、partial、count 均不能替代它们。两个有来源的语义泳道可以构成合法案例，不必强求两个物理引擎的精确 busy 边界。

最重要的执行条件是：不能将现有各后端的旧 timer/动态日志直接包装成新 timeline 协议。下列静态事实说明需要真实改动，而设计已允许这些改动并设置相应验证点。目前没有源码证据足以断言 C200、910B 或 RTX PRO 6000 的完整路径必然成功或必然失败。

## 已确认问题

| 类别 | 数量 | 说明 |
| --- | --- | --- |
| Confirmed blocker | 0 | 未发现使目标无法按合同启动的内在矛盾。 |
| Confirmed major | 0 | 尚未证明的硬件/SDK 条件列为 verification gap，不冒充已确认缺陷。 |
| Confirmed minor | 0 | 本席未确认需要阻止实施的文档错误。 |

以下每项均为需要关闭的验证缺口或实施冻结条件；不是已确认的新产品实现 bug，也不降低任何资格项。

## Verification gaps 与最小闭合路径

### V1：三个 timer 的“可读”与“可用于本轮时间坐标”尚未等价

**文档位置：** 设计 `92–108,164,190–192`；测试 `54–55,69,95–96,140,145`；合同 `47–48,81`。

**源码事实：**

- NVIDIA 的实际 getter 目前选择 `%clock` / `%clock64`，源码明确它们是 SM-local cycle：`Profiler/Dialect/lib/ProtonGPUToLLVM/ProtonNvidiaGPUToLLVM/TargetInfo.cpp:13–33`。旧 ring 把 64-bit clock 只保留低 43 位：`Profiler/Dialect/lib/ProtonGPUToLLVM/Utility.cpp:150–173`；decoder 只接受 32/43 位，导出的 `tick_ns` 为 null：`Profiler/python/flagtree_profiler/observations_nvidia.py:23–25,132–147`。因此不能只换 exporter 就获得全设备 ns 轴；若改用另一 getter，记录位宽和 ABI 也要一起核定。
- Enflame 已通过 LLVM 调用 `_ZN4tops12global_timerEv`，不是从整核时长反推：`Debugger/lib/Instrumentation/Passes.cpp:3805–3843,3849–3869`。实际编译补丁只允许 `options.arch == "gcu300"`，链接 SDK `llvm11/lib/krt/gcu300_api_profile.bc`，并明确 `debug_clock_frequency_verified=False`：`integration/patches/enflame/flagtree-source.patch:9–34`。`Debugger/python/flagtree_debugger/compiler.py:432–437` 同样保留频率未知。C200 这次实际 target/SDK 是否满足该限制，不能由品牌名证明。
- Ascend 使用 `MOV SYS_CNT`：`Profiler/llvm/AscendLateObserver.cpp:112–115`。`cann_source_clock.py:104–143` 将本机 SDK 频率与文档频率和 getter header 关联，但仍写 `clock_epoch_status=unverified`；`249–254` 明确去掉共享坐标证据。`ascend_clock.py:77–148` 的共享 epoch 入口需要调用者提供同次调用及 counter-domain 证明，函数的存在不是该证明已经取得。

**具体触发：** 新实现直接保留旧 NVIDIA 编码、给 GCU timer 填入主频，或把 Ascend 频率相同当成 AIC/AIV 同 epoch，会分别造成截断/回绕错误、错误单位或伪跨主体对齐。设计已经禁止这些做法；本次未观察到新 timeline 实现实际采用它们。

**最小闭合：** P01 每后端留一份实际 getter 指令/对象 SHA、返回值有效位、频率比例及适用 target、分辨率、复位/回绕窗口、共享 epoch 范围。GCU 若走独立校准，校准与留出验证必须独立于被解释 kernel；取得的只是哪些主体、哪些生命周期内的比例/epoch，就只开放该范围。Ascend 可以先以单 observer 内 submit/wait 语义泳道推进实现，但这只是阶段结果，不能据此免除设计 `128` 要求的 AIC/AIV 动态依赖与可比时钟证据。未关闭者继续是该后端未完成，不能用 raw-ticks 页面或 partial 代替。

### V2：误差与回绕需要成为可执行的比较规则

**文档位置：** 设计 `100,108,154,164`；测试 `55,96,145`。

**源码事实：** 旧 `observations.py:120–146` 主要验证声明字段，并明确不声称物理验证；`149–162` 仅在 `end < start` 时要求单次回绕证据。`190–196` 使用 `tick_ns` 乘法产生 ns。新设计要求整数/有理数换算及误差传播，比这段旧实现更强。

**具体触发：** 两个很长区间的边界只相差小于端点误差的距离。虽然误差远小于“区间尺度”，仍不能仅凭中央估计判断边界先后。另一个负例是截断 timer 恰好绕过完整一圈后 `end >= start`，看起来正常的差值同样可能不唯一。设计已有 fail-closed 原则，但尚无新比较器和具体 oracle 可审计。

**最小闭合：** ABI/clock 模块冻结时明确读钟误差、转换误差、域间相关误差及适用窗口，按端点不确定区间判断先后/重叠，而非只用“误差是否小于 duration”判断。独立误差的简单先后充分条件可写为 `tA + uA < tB - uB`；共享误差项的处理应按实际模型说明。补“长区间近边界”“`end >= start` 但整圈不可判定”“大绝对 tick/小差值”的参数化负例。此项是将已有设计落实为规则，不要求硬件时间绝对无误差。

### V3：异步关联的通用方向正确，但真实状态机尚未建立

**文档位置：** 设计 `112–118,155,166–168`；测试 `66–71,97,146`；合同 `48,79–83`。

**源码事实：** Ascend 当前静态 readiness channel 只在唯一 set/wait 条件下形成候选，并明确 `dynamic_generation=None` / `dynamic_pairing=not_established`：`Profiler/python/flagtree_profiler/ascend_hivm.py:220–265`。LLVM 执行映射也明确不解码 undocumented flag encoding、不推导动态 iteration：`execution_ascend.py:50–57`。旧 Ascend 记录的 buffer/iteration 两字写 `UINT64_MAX`：`AscendLateObserver.cpp:85–92`。GCU 现有动态 record 写 site、program、ticks、actor、slot、ordinal 等，没有 operation/group/generation 集合：`Debugger/lib/Instrumentation/Passes.cpp:3168–3185`。日志 occurrence 不能直接升级为动态依赖 token。

**具体触发：** 多个 submit 属于一组、一次 wait 只覆盖旧组、多消费者共享同一个完成事实、buffer/flag 下一轮复用，以及其中一个 commit/producer 记录丢失。按“最近生产者”或每 site 第 n 条记录配对均会出错。文档 §8.2 已准确识别这些问题，因此不是模型仍然强制一对一的设计缺陷。

**最小闭合：** 第一条纵向路径在实现内部冻结一个小的状态转移规则：真实 submit 的 operation 集、commit 如何构成 group、每种 wait 覆盖哪个集合、completion 能证明到什么位置、generation 从何处推进、漏记录后何时失去/恢复配对资格。返回公共层的证据应能表达集合和多条 edge，不靠单个 `producer_token/consumer_token` 字段暗中限缩成一对一。

P07 的 fixture 应给出明确预期集合：部分 wait 后尚未覆盖的组不能产生完成 edge；第二消费者不能因第一消费者已读取而丢失；丢一条 commit 后不能将后续 group 自动平移补齐。真实硬件只需证明本后端确实存在的机制；其它 fixture 只证明公共合同，不冒充三后端都支持全部机制。

### V4：发布、loss 与配对恢复必须一起设计，旧物理协议不能原样复用

**文档位置：** 设计 `76–88,153,158,168`；测试 `91,95,99,144,146`。

**源码事实：**

- Ascend 旧动态 v1 以 `actor * (4 + capacity*8)` 个 64-bit word 定位 actor，依次写 payload、version、committed cursor，使用 volatile：`Profiler/llvm/AscendLateObserver.cpp:49–110`。其 actor stride 为 `32 + 64*capacity` 字节，不能由此得到 actor 之间 cache-line 独占。对照已实现 census v3 的 `header_bytes=64`、actor stride 向 64 对齐和计入 padding 的预算：`Profiler/python/flagtree_profiler/ascend_census.py:59–73`。设计要求保留 v3 的可见性修复，因此 timeline 需要新的物理布局或等效证明，不能把动态 v1 名称改成新 schema 后继续使用。
- GCU 的动态 publisher 在选定 sole-writer 分支更新 attempt/sample/cursor，按实际 work-item 布局选 scalar 或 vector 记录发布：`Debugger/lib/Instrumentation/Passes.cpp:3097–3219`。注释解释了逻辑 `tensor<16xi32>` store 在 GCU 分布式 work-item 下可能只写记录片段，不能将其视为天然的普通 64-byte scalar store。
- 旧 Ascend decoder 把全零 header 解释为 `execution_status=unknown`，不是“actor 没有执行”：`observations_ascend.py:113–125`；这是一项应保留的诚实区分。

**具体触发：** 扩展为首末 program、多 observer 后共享 cache line、header/record 发布顺序不匹配、计数饱和、异常发生于记录中间、或丢失 group 状态记录但后续 interval 完整。只有 `attempted == committed + dropped` 并不足以独立证明每条 payload 的发布完整性，也不足以恢复异步语义状态。此处尚无新 protocol，不能报告它已经出现上述故障。

**最小闭合：** 在新 ABI 实施时同时冻结物理 stride/header/padding、实际写者、commit 的含义、主机何时可读、计数饱和、异常/取消后 buffer 隔离和回收规则。每份“complete”状态须说明覆盖的是哪个调用/program/observer 及哪些必需记录；不能只看 UI 当前可见事件。对受 loss 影响的 group/generation 继续拒绝 flow，直到有可验证恢复锚点。P05 应包括真实设备多 actor 可见性验证；CPU 修改 commit flag 的 fixture 只补消费者拒绝逻辑。

### V5：无新全局同步的生命周期路径尚需真实实现，现有 hook 不能直接保证它

**文档位置：** 设计 `86–88,153,168,217`；测试 `70–71,90–92,149`；合同 `96–100,115`。

**源码事实：** 现有 NVIDIA census exit 会立即 `ExternalStream(stream).synchronize()` 后读取共享 buffer：`hooks/instrumentation.py:690–729`；旧 interval 导出依赖 native buffer 同步：同文件 `820–824`，以及 `Profiler/csrc/lib/Profiler/Instrumentation/CudaRuntime.cpp:35–49` 的 D2H 和 stream wait。GCU runtime 的 backend adapter 支持 stream synchronize：`Debugger/lib/Runtime/TransferEngine.cpp:217–250`。另外 Enflame native activity flush 使用 `topsDeviceSynchronize()`：`Profiler/csrc/lib/Profiler/Vendor/EnflameProfiler.cpp:329–341`。这些都是现有路径事实，不等于所有同步都必然破坏单次 kernel 内部流水，但它们不能被直接宣称满足两 stream 的时间观测合同。

**具体触发：** 复用每次 launch 的同步导出，使原本可在两 stream 交错提交的调用被 host 等待串行化；或者为避免同步，在应用异步返回后过早解码/回收仍被设备写入的记录。关闭 profile、异常和 cancel 是最容易暴露后一问题的位置。

**最小闭合：** 实现时明确每 invocation 的 buffer owner、原 stream 上的完成依赖、采集 D2H、host 解码和回收终态。可利用不改变原设备执行先后关系的完成事件/延后最终化；具体机制要由实际后端提供，不能只写“异步”。若某 SDK 仅能以强同步导出，保留其实际影响并按支持合同处理，不把记录导出延迟当作原程序内部 elapsed。E03 要真运行支持的两 stream；不支持的 thread/graph 可以按合同早拒绝，但不能仅为绕过已承诺能力而把失败改记 unsupported。

最小生命周期设备验证可复用 E01/E03/E05，不需另建大矩阵：普通脚本在两 stream 交错提交多次、返回前不主动同步，核每次最终化都来自自己的完成依赖且没有逐 launch host wait；在自有记录仍 pending 时触发关闭/异常/cancel，核设备未写完的 buffer 未被下一 invocation 复用；注入一次 D2H/导出失败后启动下一正常 capture，核调用身份、raw、完成与释放终态不串联。保 API/调度证据，不能只以最后数值正确推断不存在强制串行化。

### V6：缓存合同覆盖面合理，但“声明进入 key”尚未证明运行中的两级缓存都失效

**文档位置：** 设计 `53,172–176`；测试 `94,141,149`；合同 `73–75,81`。

**源码事实：** 现有 Ascend `ascend_compiler.py:412–460` 已将 plugin bytes、trace 配置及若干 capture 源码 hash 加入 key；GCU `Debugger/python/flagtree_debugger/compiler.py:12–14,34–75` 为 publisher、lowering revision 和 planner 等冻结编译配置。GCU timer library SHA 在实际 lowering 中才写入 metadata：`integration/patches/enflame/flagtree-source.patch:14–30`。该 metadata 有 hash 并不单独证明 SDK 原地换库时，现有内存 JIT 或磁盘缓存命中前已经计算这个 hash。

**具体触发：** 同进程、同 kernel 从 count 切 timeline；SDK/plugin/timer library 保持路径但换字节；symlink 目标变化；已缓存的 capability 从 verified 变为未核验。在后端编译已经被缓存跳过后才产生新身份，无法防止旧 binary 被重用。

**最小闭合：** 为两级 cache 分别列出“key 在什么阶段形成、实际依赖 bytes 从何处取得、如何传入 compiler/runtime”，并用 E07/P10 的原地升级、symlink、模式切换及失败后恢复验证。编译 artifact 身份与本次 capture 的 epoch/时钟证据分开管理，后者必须每次绑定，不能从旧 bundle 搬用。保留旧 cache 作为负例正是合理做法。

## 三后端实际实施判断

| 后端 | 静态判断 | 第一条可执行工程路径 | 不能提前宣称的部分 |
| --- | --- | --- | --- |
| NVIDIA | 路径最明确，存在 compiler scope、程序选择、旧 raw 解码和实际 getter 接入点。 | 在通用 lowering 引入适用目标 timer 和版本化足够位宽记录，先打通两源区间及真实 runtime loop，再把实际 async lowering 的 group/wait 状态接入。 | global timer 的本机行为/范围、logger 边界未移动、真实 async group 和跨 observer 语义尚无本轮证据。 |
| Enflame C200 | 有真实只读 timer 调用与发布经验；时间比例和 async 仍是最大未知点。不能由缺公开频率推出不可能。 | 先核实际 target/SDK helper，再做独立单位验证；核 SDK/晚期编译是否能保留或提供可插桩的真实 submit/wait 标识。语义泳道可来自真实同 observer 的机制，不必捏造 copy engine。 | C200 对应的当前 target 能力、timer 单位/epoch/误差、合法 async 普通 Triton 算子、晚期 hook 可用性都需 P01。 |
| Ascend 910B | 有 SDK handoff、晚期 observer、SYS_CNT、源码和 actor binding 起点；动态 v1 与 census v3 是不同协议。 | 新建保 cache-line 隔离的事件协议；保留原标量写语义；先成对记录真实区域与原 wait，维护真实控制路径上的 flag/buffer generation。 | AIC/AIV 共享 epoch、跨 actor 动态 edge 及新协议设备可见性尚未证明；旧 static channel 或频率证据不能替代。 |

设计 `190–192`、测试 P01 与合同 `81` 已把核心未知放到全量资格之前，安排正确。若 P01 暴露 SDK 封闭或必要机制确不可观测，应以最小技术事实返回，继续其它不依赖工作；不能将该后端从三后端完成目标中删除，也不应在尚未尝试允许的通用 SDK/compiler 扩展前宣布硬件不可能。

## 适配边界与工程规模

本轮没有明显过度工程。公共 intent → 晚期执行 manifest → 后端物理解码 → 公共事件/clock/依赖验证 → 同一 Perfetto exporter 的边界，对现有三条不同编译/记录路径有真实调用者；主体与硬件 resource 分离、域隔离、many-to-many group 模型都直接服务已列出的正确性问题。

测试规模很大，但六新数学 × 两 shape × 两 config 的冻结资格，与 timer/发布/async 尚未证明之间并没有执行顺序矛盾：应先完成三个小纵向样本，再冻结最小真实接口并进入全量。不能先花精力构造完整插件生态、所有未来异步机制或第四后端，文档 `134,178–186` 已主动限制这类成本。

Optional 建议（不作为启动前置）：

- 为每后端保一张短的 timer/epoch/发布/async 证据表，直接给证据 ID、适用 target 和失效条件，避免同一个“verified”状态在不同层被重复解释。
- 在第一个接口冻结提交中附一份小的规范化异步集合例子及对应 raw offsets，帮助第二、第三后端检验公共模型，不必提前制定所有物理 ABI。
- 实现时把区间比较和证据覆盖规则写成小的纯函数合同；不把设备未证明的事实藏在 permissive metadata 字典中。

## 阅读、执行与未覆盖范围

已完整阅读本报告列出的三份主文档。静态核对了报告逐条引用的 NVIDIA getter/编码/decoder、Ascend 晚期 logger/clock/census/静态 channel/编译 cache、GCU timer/publisher/compiler patch，以及相关 runtime 同步路径；源码按问题定向阅读，没有将“所有产品源码均已审完”作为结论。

没有读取其它本轮评审报告；没有 import 产品、build、运行测试或 oracle；没有 SSH、访问设备或打开 Perfetto；没有校准任何 timer，也没有产生实验结果。仅新增本报告，未修改设计、产品、论文或旧数据。所有设备、SQL/UI、实际安装及三后端 P01 结果仍为未验证。
