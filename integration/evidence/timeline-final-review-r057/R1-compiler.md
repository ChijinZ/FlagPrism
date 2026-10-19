# R1：编译、插桩与适配边界最终工程审阅

结论：**目前不支持把这份冻结版本按完整 timeline 合同交付为 complete。** 三后端已接通真实的公开采集、counter-ns、原件留存和公共 Perfetto 链；专用异步样本也有实际动态证据。这些进展成立。另有两项可由源码确定的 Ascend cache 身份缺陷，以及下列尚未闭合的验收资格。后者没有被我改写成已发生的数据损坏或假 flow。

审阅对象为 HEAD `85ebb4fce3564769c9ea11636811527a1124cf0c`，runtime implementation `4bc92861bd8665dfd446332f9af63dca7b64eaf0`。我实际核过 HEAD。请求配置为 `gpt-6.1-sol`、`xhigh`、`fork_turns=none`；任务名 `/root/timeline_final_sol61_compiler_r057`，与 `accepted-spawn-configurations.json` 的工具返回任务名一致。**resolved 实际型号及 reasoning effort 未由工具暴露，未知。**

只做离线读取和源码走查，没有本机 import/build/test、服务器或设备访问，没有启动子 agent，没有读取 peer/旧 reviewer 报告。唯一写入是本报告，没有改产品、论文或提交 Git。文中运行结果来自已留存实际收据，不是我新执行的结果。

## Confirmed blocker / major / minor

没有另行确认 blocker 或 minor 代码缺陷。以下两项为 **major、静态确认**；建议 root 用现有 Docker 的 CPU 边界 fixture 补最小实际复现。它们不意味着当前冻结安装的每份原件都失效，但会破坏合同明确要求的升级/旧 cache 隔离。

### M1 — Ascend 晚期插件身份未进入进程内 JIT 查询

- **位置**：`integration/patches/ascend/flagtree-source-census-v2.patch:309–312,343–350,869–877,884–892`；`Debugger/python/flagtree_debugger/compiler.py:94–121`；`Profiler/python/flagtree_profiler/ascend_compiler.py:461–509`。
- **触发**：同一 Python 进程已编译一个 timeline specialization，关闭 session 后改变 `FLAGPRISM_ASCEND_LATE_PLUGIN`，或替换同路径 plugin bytes，再以相同 source/input/config/request 打开新 timeline session。
- **证据/推理**：`ascend_compiler.cache_key()` 确实读取 plugin SHA，但其注册回调只在 `NPUOptions.hash()` 中使用。两个 JIT 入口先以 binder 的 `options` 查询 `kernel_cache`；查询前新增的 `normalize_launch_options()` 仅冻结主 compiler executable 与 AutoBlockify，没有 plugin/callback key。公共 `apply_compile_options()` 构造的 Ascend instrumentation mode 也没有这个指纹。已有真实 JIT CPU fixture 的边界正是先查缓存、miss 后才 `parse_options`/`options.hash()`。因此 plugin key 的变化不能使已存在的进程内条目 miss。
- **后果**：新请求可能直接运行旧 plugin 生成的 executable 和 manifest；新插件的 publisher/timer/选择规则没有实际应用，违反设计 §8.3 与 E07/P10 的“内存/磁盘查询前绑定实际依赖”。当前 Ascend launch 校验本次 loaded binary 与其自带旧 manifest 相符，不能替代与本次所选 plugin 的比对。
- **最小修复/验证**：把同一份冻结的 Ascend observation compiler 指纹放入查询前的有效 options，并在编译时重核，不能仅在 miss 后再追加 hash。复用 `integration/patches/ascend/test_auto_blockify_cache.py` 的两个实际 JIT fixture：固定相同参数做 warmup → 改 plugin path/bytes → warmup → 恢复原 plugin；应有两个编译结果且第三次复用原结果。记录未初始化 NPU。再核两个 session 间同 specialization 的实际 installed 路径；无需重跑数学矩阵。

### M2 — 实际 late-pass/codegen 可执行文件没有进入 Ascend 持久 cache 身份

- **位置**：`Profiler/python/flagtree_profiler/ascend_compiler.py:153–168,461–509`；`Profiler/python/flagtree_profiler/ascend_driver.py:58–66,137–148`；父补丁 `compiler_identity.py`（同 complete patch `:536–572`）。
- **触发**：主 `TRITON_ASCEND_COMPILER`/CANN version 文件/plugin 不变，改变受支持的 `FLAGPRISM_ASCEND_OPT`，或改变 `PATH` 中实际选中的 `bisheng`，继续使用同一持久 cache。默认工具同路径原地升级也属于该条件。
- **证据/推理**：`prepare()` 实际从 override/PATH 解析 opt 和 real bisheng，随后由它们运行 pass/codegen；`cache_key()` 没有这两个路径或内容身份。父层 `compiler_identity` 绑定的是所选 `bishengir-compile` executable，不能绑定另一个 `bisheng`/opt。编译发生后的 command/input 收据很有价值，但 cache hit 时不会发生本次编译，不能补查询前身份。文档 `compiler_identity.md` 也明确其 executable-only 范围。
- **后果**：在不同实际 pass/codegen 工具之间复用同一旧 binary；工具链条件、能力和来源记录仍属于旧编译。该问题独立于 M1，即使改用新 Python 进程仍存在。
- **最小修复/验证**：绑定实际解析并会执行的 opt/bisheng 内容，或绑定能覆盖它们的不可变工具链 material manifest，再把它纳入 M1 的同一查询前指纹。此处不要求无界扫描整个 SDK。现有 Docker CPU fixture 固定其它条件，只切换两个合法 opt 路径、两个 PATH codegen 路径及同路径 bytes，核有效 key 改变并恢复复用；仅改 `FLAGPRISM_ASCEND_OPT` 时当前 `cache_key()` 不变，是最小隔离检查。相关工具/SDK材料的既有 build 收据可复用。

## Verification gaps

这些缺口阻止我给出完整合同通过票；其中 partial 数据本身可以继续使用。没有据此要求逐算子 adapter、任意 ISA 证明器、第四芯片或新的数学矩阵。

### G1 — 默认源区域与循环的最终边界资格尚未闭合（P03）

- **位置**：NVIDIA `late-timeline.cpp:177–181,517–528`，`timeline_nvidia_late_boundaries.py:17–18,200–213`；GCU `GcuTimeline.cpp:447–465`；Ascend `AscendLateObserver.cpp:672–696`；共同 `timeline_views.py:130–157`。
- **触发/证据**：普通 compute/load/store/runtime-loop 源区域被选中。NVIDIA O3 后插入带 memory clobber 的 inline timer，后续仍有目标 lowering；native boundary checker只覆盖有限 async/shared 指令，保留 `source_region_qualified=False`，没有由此覆盖一般 compute/global 区域及循环路径。GCU 在 SDK 执行 IR 放置读钟，其 manifest明确 `source_cost_verified=False`；Ascend 原 basic-block fragment 明确 `boundary_status=unverified`。R057 Ascend supplemental 24 份 canonical 的 boundary status 都仍为 unverified。源码导航、实际 getter PC 和真实重复均有证据，但不是最终声明区域未越过端点的证明。
- **后果**：目前可读的是插桩执行中两个真实 counter reader 的 bracket。不能把“多源码位置 + 多正 duration”直接计为设计 §0.6/P03 的完整最终源区域/loop资格。公共 view/Perfetto 如实保留未知，未发现它们把这些区域普遍伪称为 exclusive source cost；我也不要求后者。
- **最小验证**：复用现有普通依赖循环和 load/compute/store 原件，每后端针对实际出现的有限结构给 binary/site/function/路径绑定与端点覆盖收据，检查关键运算/原 wait 是否在所声明控制路径内，并给字段/身份均自洽而语义越界的最小负例。Ascend native map 的 getter bracket（`timeline_ascend_native.py:149–162`）目前主要依赖 PC 包含关系，亦需说明其支持模式如何排除绕过 native 指令的路径；未知模式保持未证即可。无需扩成所有机器指令的证明器。

### G2 — ordinary / sparse / default 的关键阶段关系保留，仍只有部分实证（C2/P03/P07）

- **位置/证据**：`timeline-independent-qualification-r057/gcu-density-both-summary-v1.json` 与 `ascend-density-summary-v1.json`；设计 §8.12，testing §5、§8.7。GCU 两 tiling、两 density 的 ordered primitive 名称投影一致，12 次 profile的数学、writers、ns、dependencies及预算通过。Ascend两 default setting共6次也通过；原/adapted LLVM 的 native primitive 名称投影一致。收据明确这些仅为 SDK-input 投影，未证明最终硬件调度。名称列表不能单独核 wait 覆盖集合、参与条件、跨迭代 buffer/flag 使用和允许 in-flight 的关系。NV历史 early recorder 的不同展开不能当 current late recorder 的已知失败；同样不能借 current late recorder 的正 duration自动关闭这一门。
- **后果**：受控 GCU C1/C2 数据能够说明插桩程序的重复次数和 bracket 变化，但还不能给出合同所需的完整 ordinary关键流水保持结论。这不是要求证明无扰动或性能开销比；NVIDIA 暂缓独占性能的边界继续有效。
- **最小验证**：先对现有三方对照保存的实际对象做有限 read-only核对，列原有 submit/group/wait/consumer 的关键依赖与允许重叠机会及插桩后的对应关系。静态不能判断的范围如实说明；需要设备补证时只补该现有结构，不重跑资格矩阵，不用 host-gap 很大的 SDK stream span计算 kernel overhead。
- **explicit sparse1范围**：Ascend BK64 density1 第二个真实 capture只有1个正区间，raw SHA `92076215ac5c3e21da79dce039dbbd1d8135b3356b4641b715d41ea2fcde90bc`；driver按原两正区间检查停止，第三次未启动。它是公开低密度诊断的实际分辨能力限制，**不是默认8站点失败**。BK64 default的23/27/24、BK32 default的29/32/30不可借给该 sparse call；反过来也不据 sparse1给 default记缺陷。当前文档已提醒小 budget会省略细节，该失败应继续留存，不以busy loop或人为加宽slice修复。

### G3 — Ascend默认请求中的 reserved actor槽仍有实际未证覆盖（P05/§4）

- **位置**：`timeline_events_ascend.py:422–452,543–553`；`timeline_ascend.py:25–45`。原72及最终supplemental收据见 R057 attempt index、`ascend-supplement-final-result-v1.json`。
- **触发/证据**：编译 manifest有该actor，但已选 program的相应 segment未到达。原72份中48份保留96个unknown槽；supplemental24中12份保留24个unknown槽，只有12份batch complete。所有已观察 writer loss-free、数学/ns/预算通过。这两个事实同时成立。decoder没有把空槽升级为完整，这是正确的保守行为。
- **后果**：“observed writers全部完整”不等于当前请求/manifest声明的observer范围全部闭合，也没有证据说明这些槽对应的实际actor必然不存在或未选择。不能通过忽略两空槽就把原默认资格分母改为全部完整。也不能反向断言空槽必然丢失了执行。
- **最小验证**：复用一份现有partial原件，核实际 task/launch配置与actor lowering的可达/所有权范围；若槽是静态不可参与的预留容量，由真实映射把“预留”与“已选observer”分开。若实际应参与，则修通用writer/mapping。不要按kernel/shape白名单排除，不需要重做其它已闭合样本。

### G4 — GCU allocation guard 的合同正例未见落实

- **位置**：`timeline_enflame.py:153–162,171–174`；`Debugger/lib/Runtime/TransferEngine.cpp:1143–1151`；testing §8.8明确“device guard证据缺失则本项未通过”。
- **触发/证据**：公开GCU timeline采集。native allocation为实际layout extent，readback返回这段raw；collector没有NV/Ascend那样的guard carrier。runtime文档也明确GCU allocation guard qualification仍独立。已有地址/stride检查、数值tail canary和valid raw不能替代guard正例。我未发现实际OOB证据。
- **后果/最小验证**：P05的相关guard门不能由数学/input/canary通过补齐。先定位是否存在本报告未索引的真实allocation guard输入/结果；若不存在，实现通用guard布局/留存并只做一份受影响实际默认采集、对应安全fault fixture及地址推导复核，不重做未变数学矩阵。

### G5 — 独立数学全部真实Trace Processor覆盖的证据闭包未在本索引中给出

- **位置/证据**：testing §7要求所有正常资格trace实际TP导入；R057 supplemental的limits明确“no repeated UI, SQL, SDK or machine-code verification in this collection stage”。R047/R049/R050/R052以及R055混合actor的实际TP/UI收据可信地证明了具体展示路径，不自动证明后面所有独立数学trace均实际通过该门。
- **后果**：不能仅由导出文件数或harness所数正区间给独立数学补TP通过。我没有断言其它未索引目录绝无这些结果。
- **最小验证**：先补齐已有逐trace SQL收据与最终trace SHA的映射；确实缺失时，仅在现有Docker对留存 `.pftrace`运行既有 verifier/固定TP，保错误stats、raw/身份/时间及flow比对，不重放应用、不重复未变UI。六trace UI门可继续复用实际同字节trace的旧UI证据，不要求为证据日期重开浏览器。

## 已核实的有效范围与适配评价

公开 CLI 的 `--detail timeline`、API `start(..., detail='timeline')`最终落到三个真实后端；`cann`与compiler `ascend`没有混为同一名字。默认8逻辑站点与显式 `timeline_max_sites`确有校验；mandatory机制站点另外保留，低密度不是总事件上限。旧native/auto入口没有被这一分支直接替换。发现/分类依据通用IR/原语与来源位置；所读实现中没有按资格kernel名、shape或固定site/hash选算法。

| 后端 | 实际编译/记录接入 | 实际解码、clock与机制 | 复用与限制 |
| --- | --- | --- | --- |
| NVIDIA | `LateTimelineHook` → `LateLLVMTransform` → packaged `late-timeline`，普通LLVM O3后插桩；实际LLVM/manifest重建再admit | late raw decoder → canonical；SM120 getter检查/单位与同CTA epoch；full-CTA shared-byte生命周期及native规则 | 复用CUDA stream/event/guard与共同owner；完整CTA参与与最多4个展示observer分开。target资格没有仅凭NVIDIA品牌扩散 |
| GCU | `gcu_timeline.prepare_ttir/rewrite_execution_ir` → packaged `gcu-timeline`；实际SDK执行IR、local ring、原return处private-tag发布 | execution v3 decoder；完整physical counter identity与session训练/留出scale；真实tag/index代际mapper | 实际queue/executable描述，未伪造CUDA函数。工具/桥接/backend/SDK材料进入查询前config；单observer时间域，buffer descriptor不等于alias-safe消费者就绪 |
| Ascend | source-coordinate carrier → `compiler.driver.v1` → LLVM15 observer →实际SDK actor/output收据 | paired cache-line decoder；910B/c220 final SYS_CNT与20ns单位；精确已编译flag word/marker与单scalar issuer代际 | 复用共同owner/输出；保持AIC/AIV/预留槽和未知身份。当前cache问题见M1/M2，源边界及未知槽资格见G1/G3 |

共同 `TimelineOwnerPool`承担admission、调用隔离、潜在writer状态；后端transport负责真实分配/初始化/完成/readback。原件保存先于decode/export；公共 `timeline_events`、`timeline_views/shared/dependencies`与 `timeline_perfetto`消费规范事件和proof，不自行解析三家ISA。`timeline_offline`是小注册入口，三个provider实际重建raw/clock/mechanism；R057已给三后端真实fresh-process retained-only回归。离线不能恢复从未读回的bytes或释放仍活跃的原owner，文档没有承诺这种能力。

三种后端的物理ABI、执行主体和机制没有被强压成warp/SM或一对一硬件engine模型。这个分工有实际调用者，具备可继续扩展的工程基础；新增型号仍需重新核target/getter/发布/机制条件，不能由三个adapter的存在推断第四芯片低成本已验证。没有要求建立新插件框架或统一机器IR。

专用异步证据应按如下范围保留，而非要求每个普通kernel都有箭头：

- NVIDIA R047及R056 retained reuse摘要实际包含shared base、精确字节范围与consumer/wait/publication/reuse链；如 `[0,2048]` 的 `async-1→3→5`，长K继续复用。它超过“只有group ordinal”的证据，不应因后续非async资格调用的0 dependency exports被抹去。
- GCU R052两runtime-K GEMM同binary，tag最大代际8/20，后续两个非默认stream的实际owner绑定通过；其flow描述submit到原wait-return，保持consumer readiness/engine busy未知是正确范围。
- Ascend新增 `ascend-current-retained-async.json`是在当前R057 provider下重建R049原raw：两recurrence调用各2 observer、42 edges，实际flag generations0/1仍可重建；旧Softmax在当前严格规则下unavailable，**不继承旧Softmax通过**。这是实际同flag复用的正证据，不必再编造physical buffer。它并未单独关闭G1/G2的最终路径/扰动要求。
- Ascend原72中的48个、supplemental24全部dependency unavailable应继续明确显示，不能改为“no async”，也不是要求每份数学trace必须有flow的理由。当前40个实际reference tuple及未知final-image指令的保守拒绝，优于按disjoint channel猜测放行；额外CPU SDK reference只识别encoding，不授动态资格。

NV原12 missing-unit/9 capacity失败、q08原12饱和，以及相应原件无replay重导/受影响10与12调用修复都保留在索引；没有据旧README的pending抹去R056/R057终态。一次历史零raw记录被拒绝、有限复现未再出现的事实仍存在，不能称已有cause/fix；本审阅没有新证据把它升级为当前可稳定复现代码缺陷。

## 阅读范围与未覆盖项

已读active goal、live record当前T074–T083、四份指定主文档、R057 review README及索引的R056/R057实际JSON；沿上表读取公开CLI/API、编译/hidden ABI、实际writer、目标/缓存绑定、decoder、clock/mechanism、共同Perfetto、owner留存和offline恢复的相关实现。另核相关维护测试、三家build/patch recipes，以及R047/R049/R052的实际TP/UI/原件/安装收据与R056 retained physical-range reuse内容。阅读方式为完整公开调用链及重点实现逐段核查，非所有历史文件逐行重审。

没有重新独立执行服务器收据中的命令、逐个解包/hash全部巨型历史归档、重新观看所有UI截图、对所有资格binary做机器码全审计，或验证所有历史P/E fixture的执行覆盖。没有把静态review当新设备正例。上述G5尤其保留“可能已有但本索引未闭合”的证据范围，而非要求重复已通过原件。

建议root先确认并通用修复M1/M2、冻结受影响版本，执行小的cache边界回归；其余以现有原件补齐/判断G1–G5。若某项受SDK机制限制无法闭合，应返回具体限制和partial能力，不能以本报告或多数review票代替原合同完成条件。
