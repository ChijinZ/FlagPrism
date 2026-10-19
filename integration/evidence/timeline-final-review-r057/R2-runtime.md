# R2：最终独立静态代码审阅（R057）

结论：**不能按当前完整工程合同交付。** 本席确认三个 major 代码问题；另有默认覆盖、最终边界/调度及 GCU allocation guard 的合同证据缺口。已有真实 raw、局部 ns、真实原生机制和标准 Perfetto 工程能力成立的部分值得保留，但不能用这些部分覆盖未满足项。本报告不是设备验收证书，也没有据失败推断硬件不可能。

## 身份与方法

- 审阅对象：`85ebb4fce3564769c9ea11636811527a1124cf0c`；runtime freeze `4bc92861bd8665dfd446332f9af63dca7b64eaf0`。本席未修改产品源码，未构建、import、运行测试、访问服务器/设备或启动子 agent；唯一新增文件是本报告。
- 独立任务：`/root/timeline_final_sol61_runtime_r057`。请求配置 `gpt-6.1-sol`、`xhigh`、`fork_turns=none`；`accepted-spawn-configurations.json` 记录工具返回任务名，但实际 resolved 型号与 effort 未暴露，均为 **unknown**。未读 peer/旧代码审阅报告或预期票。
- 先核对根目录 `timeline_goal_prompt.md`、四份要求的 timeline 文档和 R057 review README；随后读 R056/R057 当前索引、资格分母与有关原始阶段证据。历史 README 中的 pending 不是当前事实。根目录/祖先未发现适用的 `AGENTS.md`。
- 下列 confirmed 是由源码执行路径确认；本席没有把建议 reproducer 写成已运行结果。root 告知的当前安装只读重建结果另外标明，不能当新设备执行或新的 SQL/UI 结果。

## Confirmed blocker / major / minor

未确认 blocker 或另列 minor。以下三个 major 均应在合并前通用修复，并在受影响路径有限复核。

### M1 — 公开 deactivate/activate 丢失 Ascend/GCU 专用 timeline collector

**位置：** `Profiler/python/flagtree_profiler/profile.py:1885`–1897、1925–1928；该文件 88–105、1754–1755、1793–1794；`Debugger/python/flagtree_debugger/api.py:1432`、1823、1831；`timeline_ascend.py:145`、`timeline_enflame.py:218` 附近的 collector `activate()`。

**触发：** 一个合法 API timeline session 中，先启动普通 kernel，再 `profiler.deactivate(s)`、`profiler.activate(s)`，随后继续启动普通 kernel。

**代码证据：** 初次 start 先激活 debugger，再单独安装 collector 的 prepare hook。非 NVIDIA collector 没有注册到 HookManager。deactivate 清掉该 hook；activate 只重新调用 `_activate_instrumentation()`，其 `debugger.activate()` 无条件安装 `_default_launch_prepare_hook`，没有重新调用原 `state['timeline_hook'].activate()`。HookManager 只恢复其已登记的 launch/graph hooks，不能补回 collector。

**后果：** Ascend 默认 prepare 对 `ascend_source_timeline_v1` 明确抛出“requires its dedicated collector”；GCU 则能进入历史 debugger prepare/finish 路径，绕过本 session 的 deferred owner、原 clock 窗口和默认 timeline capture 汇总。后者尤其不能把第二次合法启动默认为完整 timeline 已捕获。没有发现一个更早的公开限制拒绝这个 API 序列。

**最小验证：** 在现有各后端 Docker、匹配安装中，复用已通过的普通小 kernel，执行 `s=start(..., backend='cann'/'enflame', detail='timeline'); launch(); deactivate(s); activate(s); launch(); finalize(s)`。核两次原数学与 side effect、两个独立 invocation/raw、第二次仍走原 collector/pool，且没有同步 legacy collector。另以 CPU spy 核 hook 恢复顺序和 owner 连续性，不能只测 start/finalize。无需新增数学或重跑全矩阵。

**边界：** 同 request nested timeline 不是另一问题。start 的 1563–1567 在构造 collector 前拒绝任何已有 session 下的新 timeline，也拒绝已有 timeline 下的另一 start；不会进入后面的 existing-session 复用分支。

### M2 — native release 部分失败后丢失资源身份，重试可假成功

**位置：** `Debugger/lib/Runtime/TransferEngine.cpp:1307`–1340；`Debugger/python/Bindings.cpp:933`–945；`Profiler/python/flagtree_profiler/timeline_enflame.py:161`–163；`timeline_runtime.py:329` 附近的 pool `release()`。

**触发：** GCU timeline 已确认完成、读回且持久化原件；native release 中 `topsHostFree` 或 `topsFree` 返回错误。可以由 CPU SDK stub 确定性注入，不必制造真实 SDK 故障。

**代码证据：** RealTransferEngine 在调用两个 free **之前** 已 move/erase `allocations_` 中的唯一记录。无论哪一步抛错，仍把 ctx 两个指针、长度、stream 等清零，再抛首错。PreparedLaunchHandle 因异常暂时保有 prepared 对象，但下一次 release 查不到 allocation，直接成功；其后 Python transport 清空 resource、pool 移除 owner。失败 free 的实际指针及各子资源终态已不在 ledger 中。

**后果：** 若 SDK 在失败时没有完成 free，资源泄漏且无法受控恢复；若 SDK 结果本身不确定，也不能把第二次无操作称为安全释放。这里没有证明提前释放尚在写的 buffer；问题发生在完成后的部分释放及恢复声明。当前公共 fake-transport release fixture 不覆盖这个 native partial-success 路径。

**最小验证：** 扩展现有 `Debugger/test/unittest/EnflamePrepareFaultTest.cpp`/`Profiler/test/test_enflame_native_prepare_faults.py` 的 CPU TOPS stub：分别让 host/device free 首次失败且保留分配，另一个 free 成功；重试核只处理未成功项、无双 free、无遗留分配、owner 只在确实闭合后移除。错误若不能保证 free 的原子结果，应保 unresolved 子资源和失败，不盲目重试并宣称 released。真实正常 GCU completion/readback/release 做一份受影响回归即可。

### M3 — 当前 provider 拒绝旧依赖资格，打开入口仍无区别推荐旧成功 flow

**位置：** `Profiler/python/flagtree_profiler/timeline_ascend_offline.py:66`–82（GCU/NVIDIA 有同类 unavailable 返回）；`timeline_store.py:188`–201；`timeline_perfetto.py:495`–530；`timeline_reexport.py:157` 附近的追加 reexport report。

**触发：** 一份 bundle 已有旧 provider 生成的 dependency receipt/trace；新版合法规则从相同 raw/最终对象发现机制不闭合，当前重导只能生成 counter views、依赖 unavailable。

**代码证据：** provider 仅在本次返回 JSON 中放 unavailable reason；没有追加旧资格的撤销/替代关系。`committed_exports()` 枚举所有历史完整 receipt，`_write_committed_index()` 把每项统一标作 `observed dependency timeline`，只附 revision 前缀，没有 current/historical/rejected 标签。counter 重导本身会刷新这个入口，所以旧成功条目仍作为普通可打开结果出现；原 capture `index.json` 也不承载本次 provider 失效状态。

**实际适用证据：** root 新增的 `ascend-current-retained-async.json` 记录：当前 R057 安装从 R049 recurrence 两原件仍各重建 2 observer/42 edges、generation 0/1；R049 Softmax 则因 instruction/getter bindings incomplete 返回 unavailable。该收据明确是 retained raw 的 CPU-only 只读重建，未持久化，所以它证明触发前提，尚不是本次 index 症状的运行复现。R049 旧成功不能因此继续直接继承。

**后果：** 用户执行当前公开重导后，仍可从默认打开入口选择已被当前机制检查否定的旧资格，并在旧 pftrace 内看到 `dynamic_dependencies_verified=True`。保留历史字节是正确的；缺少资格状态隔离违反设计 §8.14/测试 §8.9 对撤销/替代后当前推荐结果的要求。

**最小验证：** 在服务器 Docker 对 R049 Softmax 完整 bundle 的副本运行当前公开 reexport（不重放、不改原件）；核本次 dependency unavailable，同时检查 index/当前推荐列表。另用确定性 CPU fixture 覆盖有效→撤销、有效→新规则有效、重试/并发顺序，要求历史 receipt/trace SHA 不变且旧资格明确归为历史/已撤销，不能仅让用户自行比对 stdout 与旧 JSON。无需重新执行数学、SDK 编译或 UI 全矩阵。

## Verification gaps 与合同影响

### G1 — Ascend 默认观测范围仍有 unknown reserved slots，未满足“默认范围全部闭合”

**位置/证据：** `timeline_events_ascend.py:425`–590 对实际编译 admissible AIC/AIV slots 保留 unobserved、`complete=False`；R057 `qualification-attempt-index.json`：原 72 次只有 24 batch complete、96 unknown slots；supplement 24 次只有 12 batch complete、24 unknown slots。observed writer loss-free 72/72、24/24 与这些事实同时成立。

**影响：** decoder 没有把空槽伪造成执行或非执行，这点正确；但只核“已观测写者完整”不等于测试 §4/§8.8 的默认所选 program/observer 全范围完整。必须明确哪些槽是当前冻结选择所必需、哪些只是编译 admissible 空间，并取得合法依据；在此之前相关 capture 和完整批次保持 partial。不能删空槽、把 unknown 改 absent，或把 qualifier 的 observed-writer gate 当完整默认 gate。

**最小验证：** 复用有 unknown 的保留实例及实际 actor/launch 证据，逐槽核选择合同、实际 writer 身份/互斥和必经 site；需要设备补证时只复测代表性受影响 lowering。既有 CPU actor fixture 仅证合同，不能证明真实槽未执行。

### G2 — 每 backend 有真实 async 正例，但完整边界/ordinary 调度保持门尚不能由当前计数与投影放行

**位置：** NV late tool 的 native reads/batched publication，以及 `timeline_nvidia_dependencies.py` 的 native/storage/payload/collective join；Ascend `AscendTimeline.h`、`AscendNativeTimeline.h`、`timeline_ascend_native.py:native_control_map`；GCU `GcuTimeline.cpp`、`timeline_enflame_dependencies.py`。公共 raw validator 有意要求 `boundary_status='unverified'`，单位或动态 edge 不改变这一状态。

**已有有效范围：** NV 当前链并非仅逻辑 group：全 CTA raw、实际 shared base/字节区间、commit/wait/barrier/consumer 和物理范围重用均有独立规则；R056 retained-reuse 原件样本可见 `[0,2048]`、`[2048,2048]` 多代复用。GCU 原生 tag storage/index 与 translated descriptor address 有真实记录及多代 wait-return；Ascend 当前 recurrence 保留真实 channel 的 generation 0/1。两后者是单 issuer/single observer 时钟，不是跨 AIC/AIV 或不同 GCU physical counter 对齐，也未声称 engine busy。**不要求每个普通 kernel 都有箭头**；原 48 与 supplemental 24 的 Ascend dependency unavailable 本身不否定这些调用已取得的局部 counter time。

**仍缺的精确结论：** 当前 R057 GCU/Ascend density receipts 的正面证据是 SDK-input/native-operation-name 顺序投影；它们自己明确不证明最终物理 schedule。相同 primitive 名字顺序、正 duration、无新显式 barrier，不能单独排除 logger 改变普通关键 overlap/等待关系。Ascend final-image map 主要核 exact words、DWARF clones 和 PC bracket；没有在本席所读代码中看到与 NV 原生 wait 路径检查等价的源 fragment/循环/分支边界放行。NV 旧 constant-K 展开差异及 ordinary/sparse/default copy/HMMA 交错变化的历史原件需要当前适用的有限处置证据，不能由后来 raw reuse 正例自动销项。

**最小验证：** 对每 backend 已有专用 async 案例的 ordinary/sparse/default 实际对象，按设计 §0.6 与测试 §5.6/§8.7 的有限结构核关键数据/控制/等待覆盖、两代 reuse 及原有 overlap 是否被测量串行化；列支持模式及不成立原因。复用现有对象和 CPU 语义故障 fixture；只在实际结构失真须修通用插桩时补受影响设备调用。本席不要求任意机器码证明器、逐算子批准或无限硬件矩阵。

### G3 — Ascend BK64 sparse1 的实际时间结构失败不能给稀疏对照授证

**证据：** R057 `ascend-density-summary-v1.json`/README 保留 BK64 density1 第二次只有一个正区间、严格两正区间 gate 失败，第三次未启动；第一次 8 个正区间。BK32 sparse 三次 5/3/5，两个 default 各三次均通过，BK64 default 23/27/24。

**影响：** 这是已暴露的 advanced 一站点诊断限制，**不是 default 原 72/24 次的新增失败分母，也不能计成 default 通过**。它使 BK64 的完整 sparse/default 时序结构对照尚未成功；不得补 duration、加忙等、换 tolerance 或借 default 时间条冒充 sparse。20 ns SYS_CNT 量化与选择密度可能相关，但本席没有确定根因，不称已修。

**最小验证：** 先从这份保留 raw/选择 inventory/实际对象解释哪一个真实 region 仍可分辨以及为何其它 bracket 为零；若目标是通过原严格 sparse 控制，需通用地选择足够粗而真实的区域并保留首错，有限受影响复测。若保留为高级诊断限制，交付说明与密度对照门必须如实未过，不能把它消失在计数摘要中。

### G4 — GCU timeline allocation guard 门未闭合

**位置/证据：** `EnflameTimelineCollector.__init__` 调用 `_init_timeline_state` 时 guard 为默认 0；native `RealTransferEngine.prepare` 分配恰好原 payload extent；`EnflameTimelineTransport.read_raw()` 返回 bytes、没有独立 allocation guard artifact。runtime 文档“Finalization and recovery stages”仍明确 GCU allocation guard qualification separate。host/input/tail canary 不是这块 profiler 记录分配的 guard。

**影响/最小验证：** 未发现此处已经发生越界，但不能把数学 canary 与实际 raw 正确当作测试 §8.8 所需 device allocation guard 的替代证据。root 应先定位当前实际 guard 收据（若有）与生产代码；若不存在，则该门保持未通过，补通用 guard/布局/owner 交接后做真实首末/2D/tail 和 readback corruption 的有限验证。此项与 GCU tag/单位已证的部分独立。

## 已核查的时钟和记录语义

| 后端 | 当前读钟/单位/范围 | 本席核到的限制 |
| --- | --- | --- |
| NVIDIA late | `%globaltimer` 的完整 64-bit record；SM120 实际 marked CUBIN/PTX/双反汇编 getter 核验；1 ns/tick；独立 admission→completion host window | 相同实际 invocation/program 单 CTA 的显式 shared proof；不能跨文件/调用/CTA/GPU归零比较；read precision unknown。getter location 本身不授源 cost |
| GCU | 同 SDK getter、full SIPINFO physical identity、46-bit ticks；training 冻结、有独立 heldout 和 host/raw enclosure 的有理数 scale/uncertainty | 未由用户 kernel duration 拟合单位；相同 rate 不合并 epoch；一个 issuer 文件一个 origin；转换 scale error 不是硬件读误差 |
| Ascend | 实际 final ELF/DWARF SYS_CNT、64-bit returned record；A2/910B/c220 条件与 20 ns/tick；额外保守 32-bit wrap window | 单 observer native flags；非 PIPE_S wait exit 仅 enqueue；PIPE_S readiness 也不是物理 completion instant；unknown flags/clones 不放行 |

公共换算先减整数 origin 后用 Fraction，显式 floor；TickScale 对完整一圈不可排除、逆行/未承认回绕拒绝，raw 不 clamp。schema1/2 不支持的 modulo 情况保持拒绝。raw decode/validator 检查 record spans、paired completion 顺序、observer/capture/binary 身份、attempt/commit/drop/overwrite/saturation 和配对，未用时间排序修复 canonical；Perfetto 另作合法投影。共享依赖层重算 proof 视图、端点引用、DAG 和 nominal counter 顺序，未把未知读精度写成 0。

owner 在初始化前取得资源；completion 事件在原 stream 上记录；只对 completed owner 做 readback，先存原件再 release，decode/export 失败不阻断其它已就绪 owner 的 salvage。API 软截止与 CLI 外进程截止分开，外进程结束不证明设备写者结束。三后端 transport 保实际 executable/queue；共同消费者不需要伪造 CUDA function/num_ctas，公共 exporter 不解析厂商 ISA。M1/M2 是这些既有边界中的具体生命周期漏洞。

历史 NVIDIA 一次 header 合法但七条零 raw 的 capture 是明确失败并安全拒绝；有限三次重现和后续成功没有解释根因，本席不称修复。原 NV 12 missing-unit、9 capacity 及 q08 12 saturation 首错、后续受影响修复分开保留；不把 reexport 计成新设备成功。Ascend 40 immediate tuples 与额外 CPU SDK words 也不授未观测动态边。

## Optional improvements

1. 把单 observer dependency export 的 scope/status 直接保留在 export row/index 标签中。当前 view/node 有单 observer 标记，但统一 row 写 `shared_counter_epoch_precision_unverified`、全局 index 段落讲 shared groups，用户需要再深入文件才能区分。这可随 M3 的状态入口处理，不能因此合并独立 epoch。
2. 增加轻量的公开 activate/deactivate 合同 fixture 和真正 native release 子资源故障 fixture；现有测试大多覆盖 start/finalize 或原子 fake release，故未发现 M1/M2。无需扩大设备数学矩阵。

## 阅读范围与未覆盖范围

沿完整公开链追读了：`cli.py`、`_capture.py`、`_deadline.py`、profile start/activate/deactivate/finalize/drop/export 相关段；HookManager/instrumentation 调用关系；三 backend collector/transport、common owner；三 raw decoder 与 canonical validator；clock/unit/calibration/shared/dependency providers；三 offline provider、reexport/store、共同 Perfetto writer；NV late writer、Ascend paired/native writer、GCU native recorder与实际 TransferEngine/PreparedLaunchHandle。核对了相关 normal/-O、owner/finalize/deadline/native-fault fixture 源码，以及 R047/R049/R052 对应真实阶段索引和 R056/R057 当前分母/补充/density 索引。

详细 NVIDIA native 指令表达式、地址、timer store/payload/reaching-definition 检查模块只按 dependency join 的实际前提和部分实现抽查，**未逐行重审其数千行规则**；AscendLateObserver 仅深入 timeline/actor/control/记录段，未全审旧 census/其它模式；未全读旧 native profiler/SDK 驱动实现、未重审所有数值 oracle、私有 SDK 对象或每份大型归档 ledger。没有实际重开 UI/TP、核服务器已安装每个字节或重新跑独立矩阵；这些已有设备收据是待 root 合同汇总的证据，不是本席新测。

在上述有限范围内，未发现把 count 按整核时间分摊成区间、按邻近时间/名字跨调用连 flow，或用 CPU fixture 代替真实设备记录的产品路径。这个负面结果不消除本报告的 major 与 verification gaps。M1/M2/M3 关闭及必要有限复核之前，本席不给最终代码通过票；G1–G4 未获有效处置前，也不能把本轮 goal 标为完整达成。
