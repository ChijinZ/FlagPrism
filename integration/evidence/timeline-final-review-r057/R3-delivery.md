# R3 独立最终交付审阅（R057）

审阅对象：`85ebb4fce3564769c9ea11636811527a1124cf0c`；运行时代码冻结 `4bc92861bd8665dfd446332f9af63dca7b64eaf0`。我核对了这两个提交间的产品目录差异：后续只有受控测试驱动改变，没有后续 runtime 改动。

角色：额外、fresh、独立 R3，任务名 `/root/timeline_final_sol61_delivery_r057`。请求配置为 GPT-6.1-Sol / xhigh / fresh context；本 reviewer 进程未获得可独立核验的 serving-model 信息，resolved 型号记为 **unknown**。没有读取 peer/旧代码 review 报告，也没有和其他 reviewer 交流。Root 追加的 `ascend-current-retained-async.json` 是同冻结 provider 对旧原件的只读重建事实，已按其实际范围纳入。

这是只读代码与留存证据审阅，没有本机 import、构建、测试、SDK 执行、设备/服务器访问或新增数学。只写本报告，没有改产品、论文、旧 Study 或提交 Git。以下「confirmed」是可由调用链确定的实现问题，不冒称已经设备复现。

**结论：目前不能按原合同最终交付。** 发现 2 个 major 和 3 个 minor 实现问题；此外，完整资格仍有直接证据缺口。现有真实 raw、counter 单位、动态逻辑关系、离线原件保留和标准 Perfetto 工作值得保留，不能据此把尚未闭合的门标成完成。

## Confirmed blocker

未发现需要另列为 blocker 的已确认代码缺陷；下列 major 和验收缺口仍阻止完整交付。

## Confirmed major

### M1：Ascend/GCU timeline 会话恢复后丢失专用 collector

- **位置**：`Profiler/python/flagtree_profiler/profile.py:1750`、`:1793`、`:1885`、`:1925`；`Debugger/python/flagtree_debugger/api.py:1823`、`:1831`、`:1436`。
- **触发**：公开 API 同一 `detail='timeline'` session 中调用 `deactivate(s)`，随后 `activate(s)` 并再次运行普通 kernel。
- **代码证据**：start 先调用 `_activate_instrumentation`，再单独调用 `timeline_collector.activate()`；Ascend/GCU collector 仅存入 `state['timeline_hook']`，没有注册到 HookManager。deactivate 清除 debugger 的 launch-prepare hook；activate 只恢复 `_activate_instrumentation`，它将 hook 设置为 `_default_launch_prepare_hook`，没有重装专用 collector。HookManager 只能恢复它登记的 LaunchHook/graph guard，不能补上该 collector。
- **后果**：Ascend 恢复后的 timeline binary 会在 legacy hook 明确报 `Ascend source timeline requires its dedicated collector`。GCU 恢复后的调用进入 legacy `prepare_launch/finish`，不再走专用 deferred owner、时钟窗口和 timeline 留存链。它可能得到旧式输出，不能当作同一 timeline session 的正确恢复。现有 pause/resume 测试覆盖的是旧 IR 路径，不能覆盖这一新增 collector。
- **最小修复/验证**：在恢复非 NVIDIA timeline session 时重新安装其已保留 collector，保留原 owner、clock session 与已有记录；避免重做训练采样或重放应用。先在现有 Docker 用 fixture 核恢复后的 hook 身份，再用已有一个普通 kernel 做 `start → launch A → deactivate → activate → launch B → finalize`；应有两个独立 retained captures，各自 raw/ns 完整，原数学/一次调用不变。GCU 补查恢复后仍是原 stream 的 deferred owner；NVIDIA 只做受影响公共 API 回归。

### M2：GCU 默认 timeline 没有合同必需的 device allocation guard

- **位置**：`Profiler/python/flagtree_profiler/timeline_enflame.py:125`、`:153`、`:174`；`Debugger/python/Bindings.cpp:966`；`Debugger/lib/Runtime/TransferEngine.cpp:1143`。
- **触发**：任何当前 GCU `gcu_execution_timeline_v3` 默认 capture。
- **代码证据**：collector 的 pool 使用默认 `guard_bytes=0`；native 分配恰为 `ctx.bufferSize`（raw header/records 的总长），没有前后 guard 区；readback 只返回 raw bytes，没有 `TimelineReadback.guard` 或 guard 校验结果。Bindings 将请求直接交给该分配路径。记录里的 commit/tag/unused-tail 校验检查的是分配内部，不能检测分配边界之外的写入。
- **后果**：当前实现无法提供 testing §8.8/P02/P05 所要求的 timeline allocation guard 正例及 readback guard 故障留存。数学输出的 tail canary、地址推导和 raw 完整性不能替代这一项。**未发现已发生越界的证据**；这是明确的必达实现缺失，不是声称现有数学结果被损坏。runtime 文档仍明确保留 GCU allocation-guard qualification separate，不能把新的 v3 成功计数当作已补齐。
- **最小修复/验证**：只扩展当前 GCU timeline allocation/readback：guard 计入 admission，在原 launch stream 初始化，与 raw 一起读回并先留存；坏 guard 明确拒绝解释，完成且原件持久化后仍安全释放。修改 native 后真实重建/安装对应 runtime，不复用旧 so 冒充修复。复用已有单 program/首末 2D/tail 和两 stream 小例，检查 guard bytes/SHA；用 readback 交接 fixture 注入 guard 改变，不执行危险写址。无需重跑不受影响的数学全矩阵。

## Confirmed minor

### m1：累计 raw admission 漏计 allocation guards

- **位置**：`Profiler/python/flagtree_profiler/timeline_runtime.py:138`、`:143`、`:170`；现有 `tests/timeline/test_timeline_runtime.py:60`。
- **触发/证据**：pending 按 `physical_bytes = raw_bytes + guard_bytes` 检查，但累计额度只比较和累加 `layout['raw_bytes']`。NVIDIA late 明确启用了累计 8 MiB，且可能在下一次 admission 前保存并释放已完成 owner。现有累计测试的 guard 为零，因此没有覆盖漏计。
- **后果**：累计物理留存超过合同上限时仍可能接受下一调用。未声称现有 R057 qualification bundle 已实测超额；这是边界算术错误，通常超额较小。
- **最小验证**：在服务器 Docker 复用现有 fake transport：`max_pending_bytes=2048, max_cumulative_raw_bytes=512, guard_bytes=64`，每次 layout raw=256。第一调用计 320，第二调用使累计物理 640，应在分配前拒绝；当前代码会以 raw=512 接受。修复后验证 release/retry 不重置或重复累计原件预算，旧 guard=0 测试保留。

### m2：`--counters` 子进程遗漏 `--timeline-max-sites`

- **位置**：`Profiler/python/flagtree_profiler/_capture.py:281`；`Profiler/python/flagtree_profiler/cli.py:run_profiling`。
- **触发/证据**：GCU CLI 合法组合 `--detail timeline --timeline-max-sites 1 --counters`，或用户显式选定独立 replay 的 CANN counter 路径。外层验证参数，构造厂商 collector 的子命令时转发 backend/device/detail/request，但没有转发 `timeline_max_sites`。
- **后果**：子进程解析为默认 8，实际密度和用户请求不同，额外记录及编译/体积开销也不同。无 counters 的默认路径不受此问题影响。
- **最小验证**：服务器 Docker 的 CPU fixture 截获 `capture_backend(...).collect_counters` 的 argv，核原值 1/4/8 被准确转发；不需要调用真实厂商 counters 或增加设备 replay。显式 None 仍使用默认值，非法范围仍早拒绝。

### m3：GCU 离线 canonical revision 没有记录实际 delegated decoder 身份

- **位置**：`Profiler/python/flagtree_profiler/timeline_enflame_offline.py:26`；`timeline_events_enflame.py:362`；`timeline_reexport.py:65`。
- **触发/证据**：v3 真正的物理解码器是 `timeline_events_enflame_native.decode_execution_capture`，但 `decoder_rules()` 只返回 `timeline_events_enflame` 和 `timeline_enflame_offline`。canonical revision 的 implementation hashes 只来自这一清单及 reexport 文件。
- **后果**：仅改变实际 native-layout decoder、且某原件产生相同 canonical bytes 时，其新执行规则不会进入 canonical revision 输入。输出变化仍会被 canonical SHA 分开，因此这**不是当前 trace 已被误解码**的证据；缺的是合同要求的实际规则身份/升级可追溯性。
- **最小修复/验证**：v3 provider 的清单加入实际 delegated decoder。对同一 retained 原件以同输出但不同 decoder implementation fingerprint 做 CPU-only 重导；新 canonical 输入应记录新规则，原 raw/首次 canonical/trace 不变，完整相同输入两次仍幂等。共同 `timeline_events` validator 的 revision 身份也应在这次窄修复中核清，不需要重跑应用。

## Verification gaps（不能当作 confirmed 数据错误）

### V1：独立矩阵 observed-writer 通过，不等于默认选择完整性通过

- **位置/证据**：`timeline_events_ascend.py:451` 正确将未到达的编译 actor 标为 unobserved、batch partial；R057 `qualification-attempt-index.json`、`ascend-supplement-final-result-v1.json` 保留 original 72 中只有 24 canonical complete、96 个 unknown reserved slots；补充 24 中只有 12 complete、24 个 unknown slots。实际 observed writer 的数值/ns/loss/预算结果可以成立。
- **缺口/后果**：testing §4/§8.8 要求默认所选 program/observer 范围闭合。没有直接证据能把这些 compiled actor slots 判定为本次合法未选/不可能执行；也不能反过来据空槽断定实际 writer 丢了数据。当前资料只足以作 **partial observation**，不支持完整默认资格票。测试驱动显式接受 unknown，并保存 batch 状态，是诚实分类；它没有修改合同门槛的权限。
- **最小补证**：复用每个受影响 lowering 的保留 manifest、实际 grid、最终 actor 调用/分派与一份 raw，给出选中 observer 的实际到达合同及未知原因；确有应该到达的 writer 时修通用 producer/actor 映射并做受影响回归。不能按算法名字排除这些组合或把空槽事后改为未选择。

### V2：专用异步复用已有实物，但完整的调度扰动门仍缺闭环

- **已证范围**：NVIDIA R047 与 R056 retained reuse 数据保留 exact physical shared ranges、producer/commit/covering wait/publication/consumer/reuse；所读四组 program 分析包含多代复用，不能误称只有 group 计数。GCU R052 的真实同 binary K96/K224 具有 tag generations（最大 8/20）、实际 translated buffer addresses、submit→wait return 与标准 SQL/UI。Ascend 同冻结当前 provider 重建两份 R049 recurrence，各 2 observers、42 edges、generation 0/1，证明当前严格扫描仍有一个真实 flag-reuse 正例；旧 Softmax 当前 unavailable，不能继续继承旧成功。
- **缺口位置**：testing §5.6、§8.7/P03/P07；R057 density summaries 自身限定为 SDK-input primitive/operation projection。它们没有给出完整最终执行关键依赖/原有合法并行机会未被测量串行化的闭环。NVIDIA late 已保住 constant-K 展开与真实 byte lifecycles，但不能据旧 early-recorder 的失败认定新 late 必然失败；同样也不能据新 flow 正确认定 ordinary/sparse/default schedule 门已过。GCU/Ascend SDK-input 的有序投影是有效有限证据，尚不等于最终调度证明。
- **最小补证**：只用已有专用异步样本和已保存 ordinary/sparse/default 最终产物，核原机制的提交/等待覆盖、两代复用、首轮/steady/drain 以及新增 logger 依赖的范围；记录能观察与不能观察的调度结论。不要新增数学、重跑无变化全矩阵、要求物理 busy 或开展用户延期的 NVIDIA 性能认证。
- **边界**：original Ascend 48 captures 和 supplemental 24 的 dependency unavailable 不自动使每个普通 kernel 的内部时间门失败；每 kernel 不必有箭头。但它们也不补齐 backend 专用异步门。现有扫描不放过未知 flags、未实施 disjoint-channel exception，是应保留的保守行为。

### V3：当前独立正常资格 trace 的逐条真实 TP/SQL 覆盖没有交付完整索引

- **位置/证据**：testing §7:159 要求所有正常资格 trace 实际 TP 导入，逐 event 对 raw/ns/identity/source/track/flow。所读 maintained `verify_perfetto_traces.py`、`verify_dependency_traces.py` 确有实际 raw word 与整数换算、slice/flow 和 importer-error 检查；R047/R049/R050/R052 开发样本已有真实 SQL/UI，R055 mixed 六份也有新 SQL/UI。R056/R057 独立 collection 总结和 profile driver 明确不授 SQL/UI，补充/受影响条目多处注明没有重复 SQL。没有看到把本次正常独立 traces 与真实 TP 结果逐 SHA 关联的最终覆盖表。
- **后果**：不能以正 interval/trace 数、protobuf 可读、历史开发 UI 或 current offline bytes 相等，代替本次未覆盖输入的真实 importer 验收。该项是验证缺口，不是已发现 Perfetto 时间单位错误。
- **最小验证**：从保留的成功原件/受影响恢复结果生成 SHA manifest，在既有服务器 Docker 的固定 TP 环境运行已有 counter verifier；有 dependency 的 bundles 运行已有 dependency verifier。只读导入，原应用不重放，保 raw/SQL/完整 stats 与对应原件 SHA。字节完全相同且已有 TP 记录的 trace 复用旧结果，不重复旧 UI。对新增但尚未覆盖的 UI，按原冻结覆盖表补最小 delta；不要重开 unchanged 六份历史浏览。

### V4：普遍源区域边界与有限计时解释应保持分级

- **位置/证据**：三后端 canonical 仍保 `boundary_status='unverified'`；`timeline_views.py` 与 `timeline_perfetto.py:253` 如实传播。NVIDIA actual native 边界/值流/地址检查很具体，但并不自动覆盖所有独立标量/归约源片段。Ascend final native flag/getter 定位、GCU SDK-input projection，同样不能单独证明所有源计算留在读钟之间。各 source hint 是导航证据，source cost 权利保持 false。
- **后果**：当前数据可解释 observer 的 elapsed/issue/wait/checkpoint；如果最终交付声称的是合同中的自动源区域时间与 ordinary 流水解释，仍需要 P03/设计 §0.6 规定的有限通用模式收据，不能把 counter 时间资格升级成源操作耗时。无需追求任意机器码证明器或物理 engine busy。
- **最小补证**：复用已冻结非平凡实际对象，逐后端定位至少两个实际区域及 runtime loop 的读钟/区域/控制路径；明确检查器覆盖与拒绝范围，未知优化形态继续保 partial。对本次默认矩阵所需范围给直接证据；不得把普通成功但 profile 未证的组合移出分母。

## 必达门逐项判断与失败历史

| 合同门 | 本轮可支持的结论 | 仍需处理 |
| --- | --- | --- |
| 公开普通 kernel 路径、非逐算子适配 | CLI/API 入口、三条真实 compiler/transport/decoder/provider/mapper 链存在；所读路径未发现按 kernel 名/shape/hash 识别数学的分支 | M1；GCU guard；完整默认 observer 与边界资格 |
| 独立六数学及补充、数值/once/raw/ns/预算 | 原分母和 affected repairs 分开，输入/tolerance 不被更换；NV 12 missing-unit 原件无 replay 恢复、10 affected device calls 与 q08 12 repairs 独立列出；GCU primitive/metadata repairs 有针对性运行 | Ascend unknown 范围不能算 whole-batch complete；V3/V4 |
| 每后端专用真实异步 | 三端均有具体真实关联/复用事实；Ascend 当前 recurrence 正例仍成立；每 capture 内部时间门与专用 async 门分开 | V2；未知机制 unavailable 保留，不凭 arrow 数放行 |
| 标准 Perfetto、SQL/UI | 公共 writer 无逐厂商 ISA 分支；整数减 origin 后换算，孤立域分文件，共同 dependency 消费，实际原件已有标准 UI/SQL | 本次独立 trace 覆盖 V3，不能仅计数 |
| 两个可解释受控案例 | GCU C1 同 binary K3/7/11 的 occurrence 与时间趋势、C2 同数学 BK32/BK64 的阶段数/elapsed 变化有明确有限解释，runtime 文档没有把它们称普通 speedup | 普通/插桩 SDK stream spans 含 host/compile gaps，不能当 kernel overhead；V2 的专用 schedule 门另算 |
| 安装、ABI/cache、旧数据及适配边界 | 三 backend 有明确不同编译/物理 ABI 与 installed wheel 证据；NV R057 重建实际 late tool，core 复用明示；GCU/Ascend 的 unchanged native 复用不是“重编 C++”声明；公开 recipes 区分 source build 与 assembly | M2/m1/m3 与受影响安装/回归；不授第四设备资格 |
| 三 fresh 最终 review 闭环 | 本报告是其中一席，模型 resolved unknown 如实记录 | Root 核实、修复与必要有限复核；其他席状态不由我推定 |
| Git/任务收尾 | 本地所核 candidate HEAD 正确，未在此审阅修改产品；证据指向设备 collection terminal | candidate 尚未合并/push 是正常最终步骤，不能提前报远端完成；最终 clean/remote/owner 由 root 收尾核 |

Ascend sparse1 BK64 的第二份实际 capture 只有一个正区间，是已保留的严格结构门失败；未启动的最后一份仍未启动。BK32 sparse 和两个 default 各三份成功不能替代它。它是**高级一站点诊断的覆盖/分辨能力失败**，不是默认预算8的已证失败；本审阅没有把它计入默认资格通过，也没有据它要求重跑完整矩阵。对用户应说明单站点预算可能不足以提供要求的内部结构。它仍不足以给 sparse/default schedule 控制项全通过票。

NVIDIA 历史一次有效 header/七条零 raw 的记录异常被严格拒绝，三份有限复现没有重现；当前证据没有因果修复，我不把它称已修复，也不在无新复现下建议猜测 barrier 补丁。首次缺单位、容量溢出、GCU 体积超额、Ascend q03 positive fault 测试失败与 unknown native words 均应保持原标签；后续有限成功不重写首次通过率。

## Optional

- `timeline_perfetto._write_committed_index` 已能区分 shared/dependency 链接，但单 observer dependency 文件的通用 clock 文案仍容易使用户把所有 “shared counter groups” 理解为跨 observer。可按 receipt 的 `clock_scope_kind` 展示 single-observer/多个 observer 的 scope；这是可读性改进，不另立硬件资格门。
- 最终文档可把现有散落 evidence 索引汇为一张交付导航表，列当前 wheel/Python、真实 trace/截图、clock/observer/async 限制与原失败入口。不要删除历史 README 或用改写 pending 掩盖旧失败。

## 阅读与未覆盖范围

已读 active goal 合同、live record 的背景及 T074–T080 实际工程记录、指定 testing/design/runtime/quickstart、R057 review 输入与 R056/R057 真实小证据；检查 original/repair attempt index、NV build/offline receipt、Ascend supplemental/density/native inventory/current recurrence 重建、GCU density/stream/native-dependency 结果。按需读取 R016/R034–R052 中上述功能的实现证据 README/小收据，没有用旧 pending 文案直接作当前结论。

代码沿完整公开链读取/走查了：`cli.py`、`_capture.py`、`profile.start/activate/deactivate/finalize`；NVIDIA late hook/compile/layout/unit 路径；Ascend/GCU collector/transport、Debugger compiler/GCU late bridge/native allocate 链；公共 owner/schema 调用点、三物理 decoder 及三 clock provider；native flag/tag/公共动态依赖；公共 counter/shared/dependency view、Perfetto writer、离线 provider registry/reexport/store、decoded codec；三 backend build recipes 与 NVIDIA assembly 身份检查；实际 TP/raw/flow verifier 和 controlled driver。

未逐指令重审所有 NVIDIA symbolic/native-rule 模块、整个 Ascend/GCU 编译器或所有历史 lifecycle/ABI fixtures；未重新验算每个私有 SDK object、每份大原始 archive ledger、每条 qualification numerical output；未亲自浏览设备或 UI；没有重新执行任何测试。R047/R049/R050/R052 的实际 UI/SQL 结果以明确版本/SHA/命令的小收据作为有限证据，未把它们扩展成所有新输入的通过票。没有读取其他 reviewer 的报告或 root 预期结论。

职责划分在实际三条链上是合理且有真实调用者的：后端负责 compiler/physical ABI/getter/mechanism，公共层负责 owner、身份/时钟算术、依赖与 Perfetto；不需要新建无调用者框架。但接口存在与真实局部通过仍不能替代缺失的 default guard、API 恢复和上述最终资格证据。处理确认问题并补齐有限证据前，本席不给完整合同交付通过票。
