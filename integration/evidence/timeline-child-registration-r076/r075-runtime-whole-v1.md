# R075 independent whole-runtime review

请求配置：GPT-6.1-Sol / xhigh；实际 serving model、resolved effort 未向 reviewer 暴露，记 **unknown**。本席延续原独立 runtime reviewer，不读取其它席报告或期望票，不据多数意见授证。

审阅冻结为正式 `detailed-profiler` 的 `ea27308b009427f7137299daa71ae1f09f045c8f`，产品 runtime source 为 `efb23636c2aa3a6e8866875133765c4de3a00f91`。审阅中正式 HEAD 前移到 `1dd2baaf`；Git 核对 `efb2363..HEAD` 的 Profiler/Debugger 产品及 integration/patches 无变化。新增 qualification 工具不充当产品修复或未取得的设备证据。本报告不覆盖随后可能出现的实现修改。

合同：工作区根 `timeline_goal_prompt.md`，以及 `FlagPrism-method/Profiler/docs/timeline_design.md`、`timeline_testing.md`；工程当前事实以 T109 和下列直接收据核实。只使用本地 Git、文本及 stdlib 读取/散列已有文件；未 import 产品、运行 checker/test/build/SDK/TP/browser、连接服务器/设备或修改实现/论文。

## 结论

**不能按原完整合同交付。** 三后端公开自动采集、真实内部 counter 区间、有限动态关联、owner/原件恢复及公共 Perfetto 消费链已有实质实现和直接实证。当前仍有原 P03 的有限最终边界及 ordinary 关键依赖门未闭合；另外确认一项跨几个调用点的 owned-child 清理 minor。未发现新的 confirmed blocker/major，也未发现当前公共消费者把上述未知项升级为 engine busy、source-exclusive cost 或任意跨设备/跨 capture 时间关系。

这里的“未完成”不是要求任意 ISA 证明器、逐算子批准、每个普通 capture 必须有 flow，或 ordinary/profile 指令顺序逐字节相同。observer 的 issue/wait/原 wait 返回 checkpoint 是合同允许的测量对象；单 observer 上有来源的语义泳道也可以满足其相应时钟范围。源区域最终边界和原程序关键依赖仍须有有限、可核验依据。

## Confirmed findings

### M1 — minor：若干实际编译/检查路径仍有 child 登记失败窗口

位置（均相对 `FlagPrism-method/`）：

- `Debugger/python/flagtree_debugger/gcu_timeline.py:167`，`rewrite_execution_ir`：Popen 后的 `/proc/<pid>/stat` 读取及 `launch.json` 写入在 `try` 之前，171–179 行抛错即绕过 181–184 行的 wait/kill/reap。
- `Debugger/python/flagtree_debugger/gcu_clock.py:88`：冷缓存 helper 编译同样在 92–98 行登记后才进入 communicate 的 try。
- `Profiler/python/flagtree_profiler/timeline_ascend_machine.py:309`，`_run`：313–323 行登记在 try/finally 之外；该异常还可能被外层可选分析降级吸收，而实际 child 没有被回收。
- `Profiler/python/flagtree_profiler/timeline_nvidia_late_compile.py:131`：虽覆盖初次登记异常，但异常清理仅调用 `_stop_worker`。`_deadline.py:114` 在持续无法读取该 PID 的 `/proc` 身份时直接返回；本调用点没有 `timeline_nvidia_machine._run_tool` 当前已有的直接 Popen kill 和有界 wait fallback。

触发：已成功启动 child 后，登记 `/proc` 或首次写 receipt 发生 OSError；NV 最后一处需该 PID 的身份读取持续失败。源代码足以确认控制流缺口；本席未执行故障注入，不声称实际正常设备任务已有泄漏。它不会凭空造出 raw/flow，但违背 E05 的自有子进程清理要求，直接 API 调用尤其不能依赖 CLI 外层进程最终退出。现有 R072 NV machine 修复与 GCU `_native_file_stage` 安全路径不能覆盖这些独立调用点。

最小验证：在服务器 Docker 的 CPU fixture 中，将各处 Popen 替为真实的本进程拥有的短 sleep child，保留 Popen 引用；只在该 child 的 `/proc` 读取或首 launch/commands receipt 写入注入异常。核函数有界退出、`returncode is not None`、`os.waitpid(pid, WNOHANG)` 得到 ChildProcessError；测试自身 finally 清理兜底。NV 补持续 `/proc` 失败这一变体。可复用已有 R072 三个 sleep-child fixture 的方法，无需 SDK、GPU 数学或新矩阵。登记/等待应处于同一清理范围；身份发现失败时用仍拥有的直接 Popen handle 回收 child，对无法核身份的其它进程保持保守。

Confirmed blocker：无新增。Confirmed major：无新增。M1 不应与下列原合同 verification gaps 混为一个“硬件故障”。

## Mandatory runtime 门的当前状态

“有限已证”仅指列明对象/安装/场景；CPU fixture 与真实设备收据分开。未把 historical partial、原失败或未执行分母改成成功。

| 合同门 | 当前判定 | 实现及实际依据 / 尚缺范围 |
| --- | --- | --- |
| 三后端完整 P01 / 原整体 runtime 交付 | **未通过** | 下列已有子门不能自动合并为完整证书；G1/G2 原合同门仍开，E01 精确场景缺收据，E05 有 M1。 |
| 公开三后端自动 CLI/API，无用户 scope/site/隐藏参数 | 有限已证 | `profile.start`、CLI、NV `LateTimelineHook`、Asc/GCU collector 和实际 build patch 接入普通编译/launch；自动 source/机制选择，不按 kernel 名称/shape/hash 白名单 dispatch。三后端已有普通数学和公开安装调用。 |
| 每 capture 身份、内部多个正区间、source 导航、runtime 重复 | 有限已证 | raw→canonical 保 capture/invocation/binary/program/observer/raw offset；共同 schema 不推造 iteration_id。独立数学及 affected repairs 有每调用输出，原件/调用分母分开。NV R073 在六份旧实际 capture 上检查 208 interval/416 endpoint；这不是新增设备执行。 |
| P03：实际优化后算术/访存/原 wait 和 loop 的有限边界 | **未全部证明：G1** | NV 有实际 source/matrix issue placement、原操作位置、native loop 路径规则；Asc/GCU 新补证只到其明确范围，不能由 getter/行号/正 duration 补齐 caller/path/operand/writer 范围。 |
| P04/P05：真实主体、raw ABI、发布、损失和 padding | 有限已证 | 三个物理解码器独立于 common schema；NV 校验全部捕获 actor 后选显示线程，隐藏 actor loss 仍使结果 incomplete；Asc pair/commit/64B 段及运行时参与数；GCU pair/header/完整 SIPINFO/真实 descriptor。完整性不由 host 写入坐标或 intact guard 单独证明。R062 关闭原 affected60 的默认未知 slot 问题。 |
| P06：来源/位宽/单位/有效窗口 | 有限已证，资格受限 | NV SM120 full-u64 globaltimer 1ns；Asc A2/c220 返回 i64 SYS_CNT 20ns、独立 host window 另受保守 32-bit 周期限制；GCU 各 full SIPINFO 的 capture-enclosed rational empirical scale，训练冻结、held-out 验证、不用应用 duration 反拟合。GCU 46 bits 只可由 R066 helper 形状解释为返回值上界，不能称独立测得物理 counter 模周期。 |
| 所需 epoch/精度与时间比较 | 有限已证；其它明确未知 | NV 仅实际同 invocation/program 的单 CTA counter epoch；Asc/GCU dependency clock 限同一实际 scalar/issuer observer。公共层检查 identity/domain/epoch、独立窗口、整数换算/回绕歧义；read precision 保 unknown，物理重叠/精确 engine 完成 false。相同 MMIO/SIP 名称不授跨 SIP epoch。 |
| P07：真实异步、动态组及两代物理 flag/buffer 复用 | 关联子门有限已证；完整异步交付仍受 G1/G2 限制 | NV actual shared byte ranges、commit/covering wait/原 CTA cut/consumer/reuse；Asc R049 recurrence 原件在当前规则下两调用各 2 observer/42 edges，真实 flag generation0/1；GCU 实际 tag base/index、原 descriptor 地址和 generation，两个原 capture 每 program 19/43 edges，最大 tag generation8/20。不是 unknown physical buffer 的逻辑组替代品；也不是所有 capture 都获得 flow。 |
| ordinary / sparse / default 关键依赖与静态 overlap 机会 | **未证明：G2** | 机制计数、部分输入 cone 或“有 future group”不足以闭合普通编译角色对应；当前数据也不足以反向判定实际硬件已完全串行。 |
| Owner、预算、完成/readback/安全恢复 | 有限已证 | `TimelineOwnerPool` 在分配前 admission，初始化也视为潜在写者，stream event 完成后读回，原件/编译关联留存后 release；deadline 是 SDK 不可打断调用之外的软界限。NV 提前 drain 时另守累计 8MiB；Asc/GCU 当前不在采集间 drain，pending 同时限制这批累计物理记录。guard 计物理字节。SDK free 非零结果不当成“未释放”：GCU unresolved ledger/quarantine、禁止重试未知 pointer、已成功子资源不重 free。 |
| E05：异常/取消/子进程清理 | **部分矛盾：M1** | 已有真实 readback/guard/decoder 故障及新 session 恢复；CPU fixtures 补 owner 阶段故障。不能据此授予上列四个未保护 child 窗口。 |
| P08：公共 Perfetto 与独立 raw/SQL 核对 | 有限已证，可复用 | 本席直接逐读 R059 的 1,740 行索引和原 receipt archive，receipt/trace SHA 全匹配，每行263 stats，无正 error/data_loss；R062 新168及 R073 新2 dependency 亦符合收据范围。TP 成功不授源边界或 ordinary 流水。UI 原已通过部分直接复用，不重浏览。 |
| P09/P10：适配、缓存/安装身份、恢复及旧模式 | 有限已证 | transport/layout、physical decoder、clock、mechanism 与公共 owner/validator/exporter 分工真实有调用者；Asc 实际 plugin/opt/bisheng/资源进入前置身份，GCU v2 tool/SDK/bridge，NV tool/layout/cache reconstruction；模式/ABI 错配拒绝。当前后端安装按组件匹配，不能把 NV-only 新 wheel 冒为另外两家的新安装。 |
| 不可变输入闭包、离线重导、撤销/历史推荐 | 有限已证 | 原件安全留存后再解码，provider 重解 raw/重核对象而不信缓存 success。内容寻址 canonical/view/receipt、OS lock 和原子 index。GCU canonical invocation 与 physical owner namespace 有意不同、按 validated canonical identity 更新资格。Asc Softmax 旧2flow 撤为 history，原31件不改；新 provider 可再选成功 revision。 |
| C1/C2 解释和扰动参照 | 有限实测存在，ordinary 保持结论未证 | 已有相同 binary 的 K 干预和 tile/BK/density 控制、数学/input/once 和普通参照。GCU/Asc SDK span 明确包括 host 提交/编译间隙，冷首项分开；不能作纯 kernel overhead 比。NV 独占性能仍按用户要求暂缓，不影响真实计时功能门。 |

工程场景的更精确范围：

| 场景 | 本次可授范围与缺口 |
| --- | --- |
| E01 重复10次并交错 specialization | 多调用、两个 binary、跨调用/流隔离有实际正例。**本次未定位“同一脚本10次且交错两个 specialization”的精确完整收据**；不能把多个独立 session 合计成这个场景。先补索引已有收据，不先重矩阵。 |
| E02 首末/单 program/零 grid | 实际不同 grid、尾部及单 program 有原件；零 grid 无 owner/无伪 trace 路径在当前代码可核。本次未逐一核完三后端实际零-grid 收据，保验证范围限制，不据静态路径宣称全 E02 真机通过。 |
| E03 两 stream/thread/graph | 已有三个实际后端 stream-local 多 owner 正例；同 host Thread 的限制、nested timeline 及 graph 前置拒绝明确。拒绝路径以 CPU/既有受控证据为据，不称任意并发组合支持。 |
| E04/E08/E12 overflow/corruption/选择外 loss | 当前 producer/decoder 有明确容量、saturation、commit、extent、unused bytes/guard/loss 检查；真实 overflow 与 guardprefix 失败保留。whole raw 先检查，非只审 UI 中4个 actor；不会补 end 或把 overflow 当默认成功。 |
| E05 | owner 的完成未知/read失败保留、ready-first salvage、新 session 恢复已有有限实证；child 分支存在 M1。库 API 不承诺抢断任意卡住 SDK。 |
| E06/E07 | 原 native/count/advanced 路径与 raw schema1/2 reader 保留；已有正常/-O、公开安装、真实旧原件重导。SDK/plugin symlink/身份变化由 cache 前校验，不能仅按 backend label 相容。未重跑未受影响旧矩阵。 |
| E09 | 共同时钟算术及三 provider 拒绝错身份/单位/超宽 tick/不确定回绕；未知精度不填零。有限原件窗口有直接证据，未授全芯片 reset/全未来频率保证。 |
| E10/E11 | 实际地址/flag/token generation、capture/invocation namespace 与 raw 端点决定关联；缺 commit、并发同 tag、漏 native 机制、跨 invocation 均不靠名字/相邻时间补连。CPU negative 是合同证据，实际机制正例另列。 |

## Verification gaps 与最少接续

### G1 — 原 P03 三后端有限最终边界尚未全部闭合

NV 的进展可以实际复用：R061 的原 FFMA 出 bracket 缺陷已有真实修复；R071/R072 的有限 HMMA placement/member location，R073 的 native loop header/latch/exit 路径（含 conditional EXIT taken 义务）及 actual raw occurrence 已接产品。`timeline_nvidia_late_boundaries.py` 分列这些结果，不授 source-exclusive cost、全参与或 hardware busy；这几项 false 本身不是缺陷。

Asc 的 R063 用已有实际 ELF 获得28/36 marker 解码和有限 VMULS/VADDS/store 连续前缀；SDK child 实际139，外层0不等于完整成功，缺8条不能推断没执行。GCU R066 是原实际 helper 的逐字节形状/声明一致，R069 是 fatbin/ELF/site/phase 的 compiler location：两数学48/62 points，公共 end block 导致 missing phase；没有因此证明 inline caller→getter→raw value 或全区域路径。产品 `source_region_qualified` / `reader_valueflow_qualified` 明确 false。不能由 helper 名字或正 duration 把这些补成完整源区域边界。

最少接续：用已有对象和原 capture，列原合同实际必需的有依赖算术、load/compute/store、原 wait、runtime loop 的有限支持谓词与本次对象证据，核 caller/site/端点/控制路径及实际 observer 范围。只补缺失适用链；遇真正 SDK 无可用输出则保具体限制给用户处理。无需新数学矩阵、任意 ISA 机器证明器或为增强 busy/source-exclusive 指标造门。

### G2 — 原 ordinary 关键依赖保持仍为 partial

直接依据 R074 summary 的实际 ordinary/default/sparse native objects：9个 copy input cone 全部未发现 matrix/clock 结果 register 依赖；17个 conditional-control root 中14闭合，default PC5360/9264/10976 的 packed P2R source 明确 unverified。四份旧实际 raw 的40个 matrix prefix 中32有已 commit、原 wait 未要求完成的非空2048B future group；wait1→wait0 同 opcount negative 失去 witness。这是许可仍 in-flight 的事实，不是测得硬件 overlap；对应 shared reads 尚未绑定到实际 MMA operand。

最少接续：仍针对这些已有对象，闭合必要 P2R merge/predicate 输入，建立 ordinary 与 sparse/default 的 group/shared-slot/consumer/reuse 角色和原 wait/CTA cut 对应，再绑定 matrix 实际 operand 及其所需 shared generation。比较关键依赖和允许未完成集合，不强求 copy 必须出现在最后一个 HMMA 之前，不把不同 PC issue 排列独自当成失败或成功。若新 R075 qualification 后续取得了这些事实，应单独核原收据；本报告未自动继承它。

### G3 — E01 精确10调用交错 specialization 的收据缺口

E01 精确10调用交错 specialization，当前已读材料不足以认证。root 随后定向搜索根 record/evidence README 也没有找到现成精确收据，确认不能以 R056 的10个独立调用替代同 session。最少补证是复用已有小 recurrence、每后端一个有界 session、两个合法 shape/specialization 交错，仍在原 session 物理预算内；不是重新运行独立数学矩阵。绑定 terminal、调用计数/无副作用、raw/index 与安装身份即可。

E02 零-grid 部分属于本席未逐一读完既有实际收据的覆盖限制；先查已有材料，不把“本席未核”自动变为新增实现缺陷或新设备矩阵要求。不能重跑已过数学/1740 TP/UI 来替代具体缺口，也不能因本席未遍历所有历史归档就宣称产品实际必然失败。

## Optional

没有为本次交付提出额外增强门。跨 SIP 对齐、engine busy、source-exclusive cost 和全芯片任意结构支持都不作为上述问题的修复条件。

## 已关闭问题、历史失败与不新增的门

- 原 resume collector 丢失、GCU release ledger 假成功、stale dependency index、canonical namespace 混用、delegated decoder 身份，以及 R072 可选 origin JSON 顶层类型逃逸/NV machine child 清理，在当前代码相应路径仍维持修复；M1 是另外几个尚未覆盖的调用点。
- Asc R060 使用真实 GET.SUBBLOCKDIM 的 cardinality；只有声明新 feature、发布 count1 且 slot2 整段全零才排除 slot2，缺预期 publisher 仍 partial，旧无 feature 原件不改。R062 原48+12 affected60 全部登记一致：60 app0、59原 controller0，首 controller1/app0 是 retained-only summary 修复，不是重数学。新120counter+48dependency/1176flows/263stats 全通过；原另36 complete 未重跑。这个缺口不能继续称“当前60默认 capture 不完整”。
- Asc 原48+24 dependency unavailable 并未被泛化洗白。当前专用 recurrence 可保有限 flag 复用资格，旧 Softmax 不再按历史成功继承。每 capture 的数学/时间门与每 backend 专用 async 门分别判断。
- NV 历史一次7条零值记录被明确拒绝，有限重现未复现不是修复证明。它是仍保留的异常/根因未知，不是已复现的当前新 bug，也不要求无止境跑旧矩阵。
- Asc BK64 sparse1 第二 capture 只有1个正区间，严格测试失败、第三未执行；默认8另跑通过。保留为该稀疏设置失败，不计 default 成功或失败，不加无关计算拉长区间。
- 不要求第四芯片、GPU独占性能、source-exclusive cost、engine busy、精确 engine 完成时间、跨 SIP/跨调用绝对 epoch，或未在原合同出现的逐字节 schedule 相同。

## 实际证据核对和阅读范围

本席本轮直接读取并用 stdlib 核对：

- R059 `trace-index.json.gz` 的1740行与根 `artifacts/timeline/run-059/preflight/receipts.tgz` 内原 result：archive SHA `d52653b3ab7c4183fd0875fab4a2ad97a3aebc5281e4adeff3da9db3cb9efe51`，1740行 receipt SHA、trace SHA 与每份263 importer stats 全匹配，无正 error/data_loss。分布 NV944 counter；GCU218counter+194dependency；Asc336counter+48dependency。是1735 fresh TP+5 exact-input reuse，不声称1740次新 import；也不是当前 provider/边界/新 UI 认证。
- R062 registrations、actual60 receipt audit、首例外、product freeze、actual168 SQL audit：120counter+48dependency、1176flows，无正 error/data_loss。与原60调用/原失败保存范围一致。
- R073 原 `receipts-v1.tgz`，SHA `f4c60be3a79b59d453928fc0acab81d24f0286186d1afa2da9db9d91b2155a7e`：正常安装 runtime efb2363/641members，normal/-O 六实际 retained capture 检查；2个变化 dependency trace 各180nodes/404flows/263stats，无正错误。没有 GPU/application replay，264 native 源核同复用。
- R057 qualification attempt index/补充结果、density 两份原 summary、当前 retained Asc async；R058 resume/guard/retained reexport 与安装收据；R060/R062 participation/repair；R066 clock declaration/helper范围；R069 实际正常 native build/安装495members/15 normal及-O fixture 收据；R074 actual native-input/prefix summary。历史 README 的 pending 仅作当时状态，不覆盖新 terminal。

源代码走查覆盖公开 `profile.py` start/activate/deactivate/finalize/cleanup、CLI 异常和 watchdog；公共 `timeline_runtime`、collector mixin、CUDA/Asc/GCU transport；当前三个物理 decoder/canonical adapter；NV late recorder 的选择、读钟/compute fencing、布局及 compile/cache 重构；Asc 64B paired producer/participation；GCU `GcuTimeline.cpp` 的实际机制分类、full pointer/identity 记录、local ring 及原 return 上 private-tag DMA publication/自身 wait，tool bridge/normal make_llir/make_fatbin patch、native release ledger；clock/calibration/unit/shared providers；三机制 mapper与NV byte-lifecycle/地址/count/native boundaries/loop关联；公共 events/clock/views/dependencies、Perfetto、store/index、offline/reexport。GCU publication 自身 wait 不冒充原 application 完成证据；未看到借 logger 增加跨主体全局完成 barrier。检查的是实际调用链与关键分支，不宣称逐行审完仓库所有文件。

未读取其它 reviewer 报告；未重读全部私有独立 kernel/oracle、每份巨型 raw/SDK 私有源码、所有历史失败归档或每张 UI 图片；未独立反汇编本地不存在的 GCU ELF、未用 simulator 成功外层状态替代子进程139；没有新设备或测试执行。既有 UI/数学只在明确未变化范围复用。因此本报告不能作为全Goal签字；关闭 M1 的有限修复与以上原合同缺口后应按实际受影响范围补 closure，不重新开展无差别矩阵。
