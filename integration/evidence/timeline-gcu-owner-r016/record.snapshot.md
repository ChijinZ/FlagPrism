# FlagPrism 时间线工程记录

## 当前恢复摘要（T023 两阶段收尾已独立安装；真实8capture/1344区间故障恢复通过，三后端完整时间线仍未交付）

- 目标：执行 `timeline_goal_prompt.md` 后补齐三后端真实内部时间、动态依赖和Perfetto可用性；用户已显式设置本合同为 active goal，开始真实工程实现。
- 设计基线：`FlagPrism-method` / `detailed-profiler`，准备前HEAD `e6aa804b203d3147925611423c2fcd20cf96bea2`。当前基础usability已完成，完整新timeline能力未交付、未验收。
- 文档：`Profiler/docs/timeline_design.md`；`Profiler/docs/timeline_testing.md`；根合同与 `integration/plans/timeline/goal_prompt.md` 同字节快照。
- 已做：T000 设计基础上完成 T001 可扩展边界、P01–P10/最小实证和合同更新；三个独立 GPT-6.1-Sol/xhigh 请求的设计初审及有限复核已完成，文档确认问题已关闭。实际 serving 型号未暴露，核心设备机制仍待 P01。
- 当前未通过：三后端完整自动timeline、经过ISA/时钟验证的动态time arrows、Perfetto、独立六数学及最终三代码走查。已有NV完整64bit原始记录、完整相关cp.async IR边界和真实逻辑group/wait事实；GCU clock原语与公共clock算术。没有一个后端整体P01完成。
- T013公共raw schema已接真实API/CLI；21capture/10816物理记录→5400真实区间+16缺失端点，400逻辑组；真实K1021溢出报告12352 overwritten，丢失不推断组/依赖。15新合同normal/-O及既有回归通过，原始字节/配对/namespace/source/manifest独立核验。最新r007/install-v2/source d15933a，606安装成员，native仍与545逐字节相同，parent launcher ABI2。六jobs terminal/worker gone/controllers仅Z；最终GPU15MiB/util0无compute-apps。clock和机器边界未证、无Perfetto/P01，TP/UI代理询问仍待。cuobjdump/nvdisasm仅PATH未找到，下一步定位/安装而非判硬阻碍。
- T015：已取得13.2.86真实nvdisasm/cuobjdump（独立prefix），反汇编r007两cubin及新校准cubin，实际JSON/源码PTX行/完整CFG。新校准先因eager event包含host提交gap失败；改用外部event-node专用graph，捕获0执行、显式9次数学/State1..9，同binary跨K4096/16384/65536、原10us/2%一致性门通过。源码858f5eb7、结果及完整失败保留；不是细粒度误差/跨SM epoch认证，无pftrace/P01。SASS确认K-load能越过源码timer，部分prologue getter非谓词化（再SEL值）；不能由IR位置/采样gating冒称最终边界或全部未选读钟已消除。当前无新增runtime/native代码，r007安装继续有效。原件和下一步见T015。
- T016：已实现自动LLVM SSA begin/operand/end结果依赖、按位类型转发与getter ~{memory}；新native boundary ABI1、版本拒绝和缓存依赖。初始99版本错误保留并修复。最终source/native a9ea010、独立install-v3，26真实timestamp captures（21原回归+5types）、11456raw/5720pairs+16orphans/400logical groups/12352overwritten；FP16/BF16/FP32/FP64/int64精确math/input/tail/副作用/实际LLIR依赖及clobber通过，7最终cubin真实SASS/JSON/CFG，无MEMBAR。仍只是LLVM约束，所有canonical boundary/clock保持unverified，无pftrace/P01，下一步必须补适用clock/error/window与最终per-site/participant/动态buffer复用证据，不能把SSA/memory clobber当机器完成证明。详见T016末。
- T017：native marker ABI1 真构建34fe5e2；f5731a0操作数矛盾负例修复；真实PTXAS首轮5dtype失败定位到marker空白与调试元数据清除，通用修复5d042b0。新install-v3 wheelSHA d41bd2c0f2da1625feeb538415d00878359a2f6e43fd360beef9ac957455faf4，7native byte桥相同、607成员核；machine17/public4 normal-O通过。最终真实26capture/7cubin/140静态getterPC全部exact debugline绑定，11456raw/5720pairs/16orphans/400logical groups/12352overwritten。原失败及新26capture工具/数学原件保留；仍不是源区域最终边界认证，clock/physical generation/Perfetto未完成。恢复按T017末新安装路径，不用T016旧安装。
- T018：880706b共同因果offset区间交集实装；新9/旧27 clock CPU合同normal-O、新独立607成员install-v1、7native字节不变。真实双CTA/64轮×3次公共算法调用，SMID0/1所有训练/留出0offset相容，四GT实际SASS/JSON/完整CFG，GPUtext与前版一致；不是绝对误差/全设备epoch认证。TP57.2已从官方bucket虚拟主机取得并与旧pin逐字节一致，GCU/NV实际version/help通过，NV路径/workspace/chijin-timeline-r011/tools-input/trace_processor_shell；TP下载障碍已解决，不再等用户代理。UI官方API资源469355212/15402304bytes已定位；初流式任务实际terminal1保留7471104bytes，ui-resume-v1已实际terminal1保留13434880bytes；现 ui-resume-v2 owner374818/worker374819（start1004998165/1004998168），实际HTTP206与正确Range，最后live且14286848/15402304bytes。恢复先poll此handle，不重启旧下载。
- T019 新控制对照风险：同源普通GEMM全展开、插桩GEMM保留3轮loop；同步静态数量不等，候选展开后counts相等但copy/wait/dot交错仍不同。unprofiled-objects-v1终态rc1（严格静态数相等检查），原件已存Git索引；不能把它写成普通流水保持通过。下一步优先核关键依赖/实际机制路径及稀疏/较密插桩影响，勿重跑纯数学/26capture来回避本项。
- 保留边界：旧count/SDK/资格/论文/Study数据不改；NVIDIA性能/开销认证仍暂缓，时间线功能与时钟验证为新目标必达。
- 下一步：当前NV正式安装 `/workspace/chijin-timeline-r015/runs/install-v2/output/venv`（product f17071c、native仍4f5b2bf、608成员），两阶段收尾/原件恢复实际8capture通过；7新finalization+16owner+4public normal/-O合同通过。公共reader支持v1/v2，GCU原42区间已规范化。当前GCU还是advanced生产者，新adapter仅纯读取/验证；接入默认采集时必须落实session唯一身份、实际grid/首末program、raw先持久化、生命周期/预算/恢复，不能把离线adapter说成默认入口已完成。继续最终机器边界/扰动、clock单位/误差/epoch与实际复用；三后端P01、Ascend新producer、标准Perfetto SQL/UI、独立六数学及最终三个额外指定reviewer仍必达。没有在途owned任务；不重复未改native/26capture。

## T000 需求与设计准备

用户要求真实、详细、可在Perfetto理解的内部流水线，而不是只看count或整体kernel。设计把observer elapsed、issue、wait、completion和native engine区分，三后端都要时间尺度与真实异步案例；clock未证明不能拼接。

测试要求真实数学开发集合+独立六新数学，每后端两shape×两config/24ordinary及cold一次warm两次/最多72profile；实际raw/clock/SQL/UI门、两项受控时序干预、三个最终独立Sol6.1/xhigh代码审阅。所有执行留待新goal。

后续每次T编号追加：需求/修改类、freeze/commit、实际安装身份、容器设备owner、PID/startticks/argv、预算/日志、原失败/结果、证据哈希、下一步；恢复先poll权威终态，不盲重启。

**T000 文档交付**：设计/测试/合同快照与初始record已提交并推送 detailed-profiler，commit775f7b44c879b515a71d2eb48f1196321d75786b，fetch祖先核、SSHpush与ls-remote精确同值，canonical clean。6个跟踪文档共516行；根执行合同与跟踪快照同字节、PLAN_INDEX逐file bytes/SHA通过、8个本地文档链接通过、git diffcheck通过。这些是文档/离线审计，不是产品测试；没有启动新goal或实验。当前等待用户显式/goal执行。根record此追加不自动进入Git，record.initial.md保持T000初始快照。

## T001 可扩展边界设计与独立评审（已完成文档与复核）

- 用户要求：为后续新增芯片降低适配成本，先更新设计与验收文档，再由三个独立 subagent 评审合理性及实际可行性。本轮仅文档，不是 timeline 实现启动。
- 变更：设计 8.1–8.5 补公共意图/晚期 manifest、编译/运行时分离、主体与异步非一对一模型、target 能力、版本缓存、三后端纵向可行性与实际改动审计；测试增加 P01–P10，合同同字节同步。
- 后续：三名独立设计 reviewer 看同一文档和必要只读源码，不读彼此报告；root 核实并修订，保留初审与处置。最终代码走查仍是未来实现后的独立门槛，不能用本轮设计评审替代。
- 未做：未启动 goal、产品 build/import/test/oracle、SSH/设备/Perfetto 实验；论文与旧 Study 未改。

**T001 评审处置**：三席 fresh-context 独立初审绑定原文档 SHA，初审原文保留；root 合并处理 UI 逐份循环/flow 适用性（R3 major、R1 重叠 minor）、Docker 地点与 NVIDIA 自动 scope 现状，加入编译顺序/全部 raw 引用/端点误差与整圈回绕/group loss 恢复/资格能力 outcome 分离/cache 查询前身份/安全最终化等风险落点。三席对冻结的新三文档有限复核均建议可启动 P01、未发现新增阻断性矛盾；这是设计准备完成，不是设备或功能通过。报告与请求/输入 SHA/处置位于 integration/plans/timeline/reviews/。

本轮文档更新及验收链接/字节审计后进行 Git 提交；未启动 goal、SSH、构建、import/test/oracle、设备/Perfetto/browser 实验。未来仍须三个实现后独立代码走查。根执行合同与跟踪快照保持同字节，record.initial.md 保留 T000。

**T001 文档交付完成**：commit `2932311bd103db9b2eeea8fa8ca0574befc913b7` 已推送 `ChijinZ/FlagPrism:detailed-profiler`，fetch 祖先核与 ls-remote 精确 HEAD 一致、正式 worktree clean。14 个本轮提交文件，仅 Markdown/JSON 文档与设计评审；PLAN_INDEX 覆盖 14 个设计/评审材料（含未变的初始记录，不含索引自身），73 个本地链接有效，三初审 SHA 保留，三复核输入 SHA 与最终三文档一致，root/tracked 合同同字节，diffcheck通过。没有运行产品测试；这些结果仅是文档/Git/离线审计。root live record 的本追加在 Git 外，后续执行以当前文件恢复。

## T002 目标启动与实际环境核验

- 用户显式设置 timeline_goal_prompt.md 为 active goal；平台 get_goal 返回 active，不重复 create_goal。上一目标前工作为 progress（设计/验收/三独立评审及复核已提交推送2932311），不是本轮设备可行性通过。
- 正式 detailed-profiler HEAD2932311，worktree clean。读取当前合同/记录及设计、测试/旧基础能力；三台 SSH 和既有 Docker 实际连通：NV chijin-study-pro6000、GCU flagprism-enflame-dev、Asc chijin_v3.5.x。
- 证据 artifacts/timeline/run-001/preflight/：三份docker-ps、各preflight输出和实际执行脚本。NV GPU0 RTX PRO6000 15MiB/97887MiB、util0、无compute-apps；/workspace16TiB空闲，容器overlay仅3.6GiB，重构建/缓存不得用根分区。GCU /workspace27GiB、overlay651GiB；Asc /tmp450GiB。GCU/Asc容器默认PATH暂无smi工具，继续核实际SDK/工具路径，不据此宣称设备空闲。Asc两个既存python进程399207/399212非本轮owned，不动。
- 本机只做编排/文件字节审计，未import或测试产品。154份既有paper/指定旧Study文件的SHA/大小保留性baseline在protected-baseline.json；不恢复或覆盖用户数据。
- 尚未启动native build、设备数学、Perfetto或独立资格。下一步：核编译源/LLVM与SDK定位、实际设备占用，准备三个后端小纵向样本与首条真实链。

## T003 真实 clock/ordinary-async 原语与首个 native 改动

- 本 turn 为 progress：三后端真实连接/设备状态与源依赖已核，新增真实数学探针并在 NV/GCU Docker 执行，源代码提交 `55119f1e70c23963b215a4231ea831303a7ddc27`（尚未作为最终可用版本推送/验收）。编译器新增显式 timeline getter/版本、目标虚方法 admission、64bit要求和与census互斥；legacy默认SM-clock/count不改。公共CLI/API timeline、动态async logger、Perfetto exporter尚未实现。
- NVIDIA探针：原v1因测试代码把vector value写scalar pointer而编译失败，原source/日志/terminal保留；只改探针pointer shape，新input-v2、新output运行。v2 controller29231/start7526241、worker29232/start7526244，argvSHA6eca6c09，终态rc0/3.520s；13个明确clock-math调用（3runtimeK+6校准+4留出）和2ordinaryGEMM调用，原数学/输入/State检查通过。root直接读原始归档核18编译产物SHA与24个host-bracket约束，`%globaltimer`支持1ns候选。GEMM stage2实际PTX含8copy/8commit/4wait；stage3含10copy/10commit/4wait且有wait_group2，均12mma。未称SASS/跨SM epoch/resolution已验证，也未把单区间手工timer探针当自动profile。
- GCU原语：已有容器driver1.9.10/C200，实际host efsmi DUsed0（不代表独占），无其它进程被终止。旧advanced automatic interval API（非新默认接口）真实recurrence ordinary1次+profile6次，controller374111/start1002712966、worker374112/start1002712970，argvSHA27e14f3a，terminalrc0/14.687s，每份8timed events。6个留出配对给period界限[1745931721/1786266450,1825923767/1786266450]ns/tick≈[0.9774195,1.0222012]；仅校准界限，不宣称精确固定1ns或共享epoch。完整34MiB输出压缩归档enflame-clock-v1-original-evidence.tgz已取回，待root逐raw/manifest审计。SDK helper actualBC SHA1a780215，读取地址/46bit组合的私有SDK摘录仅rootartifacts，不进Git；未来Git只记SHA与必要机制描述。
- Asc只读host npu-smi实际910B4-1/NPU4 healthOK、无运行进程。旧SDKfixed、晚期logger/epoch等仍待新阶段真正验证，未启动NPU作业。
- NV真正native CPU构建：新/workspace/chijin-timeline-r001/source-55119f1/FlagPrism从Gitarchive固定；关键源/controllerSHA在启动时实际核。独立native-55119f1/FlagTree复制已验证旧parent源码（非Gitclone，旧树不改），三个公开parent patch reverse-check全rc0；新build/wheelhouse/ccache/tmp都/workspace，复用LLVM-f6ded0be/json依赖，不复用旧native冒新编译。controller29447/start7607212、build29451/start7607345/PGID29451，argvSHAe0d7a50f，8jobs、nativebuild7200s（不是kernel编译预算）。root实际ps126s live、构建273/558，PatternProtonGPUOpToLLVM新TU已编；后续状态见actual-process-2。当前未安装新wheel、native功能仍未过，必须poll原任务而非再启动。
- 实验代码：tests/timeline/{p01_nvidia_primitives.py,p01_enflame_clock.py,run_primitive_probe.py}。controller为开发基础设施，复用已安装_deadline的owned-descendant cleanup SHA8c70；不是最终独立资格控制器。所有产品/CPU/GPU操作在已有serverDocker，本机只有编辑/Git/调度/原件字节审计。
- 证据根artifacts/timeline/run-001/preflight：各脚本/冻结JSON、所有status/实际PID输出、NVIDIA原失败+成功归档/root-byte-audit、GCU完整原件。未跑设备性能/开销认证、未改paper/旧Study、未完成任何后端P01整体门。

## T004 精确时钟算术、原件审计与 native 布局修复

- 新公共 timeline_clock.py 是纯算术/身份校验，不自行授权物理时钟。整数/有理数换算、舍入误差、独立窗口排除完整回绕（含end≥start和read-error）、不同domain/epoch拒绝比较、端点近边界unresolved。source-level CPU tests在NV既有Docker普通/-O各27通过；实际源输入与两JSON在clock-arithmetic-v1*，当前新模块/test仍待提交。测试包含真实GCU校准界限的精确算术，但不是硬件proof或独立安装资格。
- GCU完整原件root审计：六bundle的228manifest payload逐bytes/SHA过；48实际64byte动态记录按公开C++ABI独立struct解码，header/capacity/loss0/sequence/site/program/start/end/duration/commitTag与normalized逐值对应，未把legacy ticks变ns；6个host-bracket校准配对重算界限同值。证据enflame-clock-v1-root-byte-audit.json；source->最终ISA边界、精确单位/epoch/async与Perfetto仍未过。
- 原native55119f1真正failed：29447最后Z，29451已无，terminal native-wheel-build rc1/568.387s。日志定位parent/bin/RegisterTritonDialects.h include FlagPrism/...缺失：root新parent复制时跳过旧组件位置但漏补新third_party/FlagPrism链接；不是已修改C++ TU报错。原所有日志/terminal/source保持。
- 明确resume-002只在新的parent构建树补canonical symlink→同一immutable55119f1组件；layout-delta记录source_bytes_changed=false。启动前核原失败terminal与原PGID29451无live任务，独立controller/日志/terminal不覆盖原attempt；三parentpatch反向核仍全过，同一匹配对象继续native真实编译/link（18剩余步骤，不冒全重编）。controller31551/start7676574、child31555/start7676577、argvSHA6519d140、预算3600s/8jobs；实际状态文件nvidia-native-resume002-actual-process.txt。
- Asc当前真实SDKfixed工具SHA仍1f5cc505，--version1.1.0/LLVM19.1.7；已安装observer路径.../flagtree/profiler/lib/FlagPrismAscendLateObserver.so，上游opt15存在，CANN9set_env存在。只读/CPU版本检查，无NPU workload。
- 下一步原resume002 terminal后独立venv安装新wheel、实际binding/旧mode检查，再接新自动timeline入口/动态async记录。新测试nvidia_timer_binding_smoke.py仅待执行的installed compiler contract smoke，不能当成已验。仍无任一后端整体P01、新Perfetto或最终审阅通过；goal active。

## T005 首个 native 完成、独立安装与已推送工程检查点

- Native resume002真实terminalrc0/91.608s（此前同源码541/558已编，后补布局18项继续），wheel390470390bytes/SHAeb1f3942ae41a99ebf734eff39b306b9789ee6b19add414c37c3e403ba828ca3。原failed568s与缺Registration头日志不覆盖；新alias只改新parent布局，旧source55119f1不变，不冒全量重编。
- 真实独立venv `/workspace/chijin-timeline-r001/runs/nvidia-native-check-v1/output/venv`，wheel正常pip无deps安装，literal vendor-dependencies.pth复用旧NV已装Torch/CUDA依赖，不执行旧editable hooks，不设PYTHONPATH。597个wheel成员实际installed字节比对。先nativecheck-v1在测试脚本`pm.run(module)`少了FlagTree要求的第二个字符串参数而failed，旧wheel/新安装不改；仅修测试为pm.run(module,'timeline-native-contract-smoke')、新input-v2/output-v2重核。
- check-v2 controller31911/start7716512、worker31912/start7716515/PGID31912/argvSHA8e75ab1b，terminalrc0/9.582s。普通/-O各实际编译真实ordinary-GEMM TTGIR，timer identity/version/getter64/packed43/实际inventory与legacy无timeline元数据通过；各4项（census互斥、site0、site129、timer未知版本）真实拒绝；模块paths全部新venv内部、实际soSHA已留。这里仍无新getter device/顺序/P01/Perfetto通过。
- root取回nvidia-native-clock-contract-evidence.tgz，实际逐源SHA核clock模块/测试/修正native smoke与当前repo同字节，27+27sourceCPU结果、597installed成员及4+4native拒绝逐值核。公开部分检查点 integration/evidence/timeline-primitives-r001/，所有大原件artifacts/timeline/run-001/preflight。SDK私有global_timer摘录只root artifacts，不入Git。
- 本阶段Git：55119f1（native timer原语与真实probe）；bed28f6（精确clock算术/测试与partial证据）；b3e4a7f（原诊断日志包JSON保原空白）。首次diffcheck对原始诊断的尾随空白报错，原commit已形成；随后保持raw原件不改，把公开副本转成带originalSHA的JSON text envelope，整体2932311→HEAD diffcheck与staged diffcheck过。不是静默修改失败日志。
- 当前HEAD `b3e4a7fcb06a4bbf59ee5312c5c4401c11243d5e` 已fetch祖先核、SSH push到detailed-profiler、ls-remote精确同值，canonical clean。只是部分工程检查点，不是goal完成/发布验收。根record此追加仍Git外。

### T005 下一阶段的源码依据（待实现，不当作已做）

NV `InstrumentationProfiler::enterInstrumentedOp` 只分配host buffer，`exit...` 强同步/解析旧ring；Python `_populate_host_buffer` 本来就合成40byte+unitIds外层header。新timeline可以保留既有Proton自动编译/hidden scratch，走独立每invocation Torch buffer/Event+延后D2H，绕开旧native逐launch同步和cycle标签；legacy count/advanced继续原路。需真正实现/验证，不能只改文档。

下一步具体目标：新timeline设备记录/元数据版本（考虑完整uint64 timer，而非把旧43bits假称64）；源区域+真实async copy/commit/wait全必要边界，operation/group/partial-wait/generation动态证据；首末program实际选择与有界物理slots；每invocation buffer/stream完成依赖；共享clock/事件/依赖合同与Perfetto导出。先NV完整小纵向，再三后端闭合、独立数学与三额外指定review。公共clock算术仅消费已验证backend证据，不自行认证硬件。尚未冻结最终公共接口、未实现CLI --detail timeline，不能把当前partial材料当最终可用工具。


## T006 设计与验收交接细化、第二轮三独立设计评审

- 用户要求更新设计/验收后由三个 subagent 独立判断合理性与实际可行性。本轮没有修改产品、paper或旧Study，没有启动新的SSH/设备、构建、import/test/oracle、SQL/UI任务；本轮未改变目标状态。
- 设计增加8.7：六项后端交接与共同消费者、每invocation owner状态机、session pending总预算、完成证明/超时隔离/安全回收、raw重导不重放；增加8.8：b3e4a7f有限原语/构建证据边界与三级放行。新芯片主要补后端机制，但不承诺一个adapter或无需新增晚期pass/ABI即可适配。
- 验收增加8.3，在既有P/E中落实交接、真实两stream（按预登记支持表）、owner累计预算、分阶段故障、安全清理后恢复、raw重导和公共验证负例；不扩大独立数学矩阵或启动第四芯片。
- 三个 fresh-context 独立agent：timeline_design_round2_compiler/runtime/portability；本轮无模型覆盖，不冒充最终规定的额外GPT-6.1-Sol/xhigh代码走查。报告及SHA、请求配置、处置在integration/plans/timeline/reviews/round2/。
- 初审R1/R2无确认问题，R3一项minor：两stream是否每后端无条件必达的措辞歧义。沿用原E03/goal澄清支持表、已支持真实测、未支持启动前拒绝/恢复、不得事后缩资格；三席有限复核确认关闭且无新增矛盾。所有初审保留原输入hash，复核绑定最终输入hash。
- 结论：设计可按P01继续实施，不证明完整三后端可交付。编译最终边界、record位宽/clock/epoch、动态async机制、发布/owner和Perfetto实测仍未闭合。执行合同root/tracked原字节不变；最终独立数学及三代码走查不被本轮替代。
- 文档离线审计：本地链接、初审保留、复核SHA/最终输入、合同同字节和索引通过；Git提交结果随后追加。产品测试未运行，因为本轮只改文档。

**T006 文档交付**：提交 `d109df561eec19704e5018762b217463a5790d79` 已推送 `ChijinZ/FlagPrism:detailed-profiler`；fetch祖先核、SSH push、ls-remote精确HEAD及worktree clean通过。24份文档/报告材料索引、85个本地链接、三有限复核输入SHA、root/tracked合同原字节一致和staged diffcheck通过。15个提交文件全为Markdown/JSON文档；无产品或论文修改，未运行产品测试。本追加在Git外，最终实现验收仍未完成。


## T007 完整时间记录协议、物理解码与真实容量问题

本轮为progress，继续原目标，无环境阻碍；不是P01/完整时间线交付。仅工具/测试，论文与旧Study未改。

- commit a6f7b4c：NVIDIA显式timeline record v2，每事件16字节，独立tag+完整64bit tick+绝对sequence；设备magic与旧ABI不同，index饱和不回零。v2 warp-master单写counter、selection控制global writer、finalize拷完整四words；新模式不继承尾部CTA logger barrier，旧模式仍原协议与行为。全链实际bitwidth/recordversion输出，未知版本/clock32拒绝。compact首末program、动态async及公共入口/owner尚未实现。
- 实际native a6构建：controller31961、worker31965/start7894789，127步实际TU/link，rc0/168.315s；复用前次build目录但新source immutable快照、父组件symlink变化另记，旧source和wheel不改。wheel SHA e5e81d4f8f37a69fe71d31984ac4af44a3cdf964de7ee7bc95647be2020cc0d7，390500187字节。
- 新独立安装native-install-v1：controller32596、worker32597/start7914603，rc0/16.894s；新venv /workspace/chijin-timeline-r002/runs/native-install-v1/output/venv，598个installed members逐字节核，native normal/-O timer/record/legacy/版本负例通过。不是设备资格。
- commit a81d491：产品timeline_nvidia.py物理解码器，保留完整tick/seq/raw offset/所有observer counter/loss；与单位/epoch/因果验证分开。CPU测试27项，在NV现有Docker普通与-O分别通过，controller32571、worker32572/start7911759，rc0/0.115s。decoder初轮为staged source，不冒称a6 wheel含此后加模块。
- 真实普通数学记录v1：无kernel profiling标注，通用automatic compiler pass，独立开发collector，显式同步每次自有probe并声明不是生产延迟owner实现。controller32633、worker32634/start7926531，rc1/2.819s，首次失败保留。K3/K7源码/相同binary、数学/tail/input/State通过；K11 profile在解码complete门失败，未执行后续数学验收或GEMM，不记成功。
- Root原件审计：artifacts/timeline/run-002/preflight/record-v1-original-evidence.tgz，193851字节；384条K3/K7规范化记录与真实16byte raw逐字段相等、14编译产物SHA核、K11 raw独立decode每warp36条/容量32，确定legacy共享内存占用率策略把显式32768请求压成2048。不是unsupported，不能靠改K/删样本/忽略loss解决。
- commit7898549：timeline显式buffer在设备合法shared范围内按请求分配，超限编译拒绝，legacy启发式不变；CPU smoke追加超额buffer和clock32负例；测试增实际capacity门。commit62853ce测试改用实际wheel安装的decoder，不再staged模块。
- 修复native构建已启动，controller32747、worker32751/start7939600/PGID32751，预算3600s，最后实际ps live 127步已link并进入package；root artifacts /run-002/preflight/native-capacity-status-3.txt。不重启。最终安装/设备v2待此任务terminal。
- 产品新自动CLI/API、per-invocation deferred owner、可靠late anchors/clock证书、动态group/flow和Perfetto仍未实现；GCU/Asc新链、独立六数学及最终三代码审阅均未完成，保持goal active。


**T007 终态与实证补充**：修复native789构建rc0/167.563s，wheel390513062字节/SHA088a83bd48754734849e2d803fd48d0d227493ff042251f8d690f5816a899208。新独立venv `/workspace/chijin-timeline-r002/runs/native-install-v2/output/venv`，599成员逐字节核；controller33377、worker33378/start7957075，rc0/16.945s，normal/-O含超额容量与clock32等7负例通过。

设备v2 controller33407、worker33408/start7959831，argvSHA2b6422a8，rc0/3.521s。5ordinary+5显式automatic capture请求，recurrence K3/7/11共用binary f6f59717...，GEMM stages2/3均原数学/tail/input/participation State通过。State仅证明参与，不当作最终独立replay oracle。测试collector每次probe显式同步自有stream，不冒充生产deferred owner。

root独立读原归档逐raw验证1024条full64记录、512对begin/end、30编译产物SHA；8个observer/site组合实际occurrence为3/7/11。原件`record-v2-original-evidence.tgz`400503字节/SHAfba43843d460ea815e529f9e29bbeda22449a0aa5c505ed61ae3ac8c23cea4e8。测试62853ce相对native789只改测试文件，产品文件完全相同；轮子真正含新decoder，不是临时PYTHONPATH。

**下一实际问题已经定位**：两个真实GEMM的automatic inventory中，async_copy、commit、wait全部存在但全部未选；旧策略偏向source arith/control helpers，不能支持本目标异步解释。`next-async-planner-gap.json`逐候选登记。下一轮必须timeline专有选择完整机制边界（独立于8逻辑region预算），保实际wait num/提交集合与源/observer事实，随后实现动态状态/flow；不能对当前8个source框画虚构流水。

小公开证据`integration/evidence/timeline-record-v2-r002/`明确部分检查点，完整P01/单位epoch/late marker顺序/生产owner/Perfetto/其它两后端/独立资格/最终三审阅仍未完成。结束进程核：自有workers均missing、controllers仅Z；GPU无compute-app。不得终止PID1来清僵尸，无新活动作业。Git提交推送结果随后追加。

**T007 Git交付**：本轮native/decoder/测试/容量修复及小证据已提交并推送 detailed-profiler；精确HEAD `13fc54f043a6df2a41d2192c6e69a56e22f3cf75` 与ls-remote相同，fetch祖先核、SSH push和worktree clean通过。证据索引15个小文件全SHA/bytes通过；构建后1434个regular source文件与原Gitarchive逐字节相同。实际产品测试仅server Docker；root只字节审计与编排，无paper/旧Study改动。

后续实现建议：当前LLVM/PTX实际记录完整，但旧planner两个GEMM均漏全部async候选，是已证实的下一工程缺口。先在timeline模式保完整相关async机制边界及wait num，逻辑region仍有界；再动态group/generation与完整owner/export链。不要把正duration当纯算术边界正确，最终对象/SSA依赖约束仍待完成。完整目标、独立资格及三个最终额外Sol6.1/xhigh审阅继续active，不以本轮机制probe结束。


## T008 完整异步候选、逻辑组事实与 Perfetto 工具环境

上一goal turn为progress；本轮同为progress，继续完整目标，不降级为原语交付。产品/测试/构建/实际数学均在已有server Docker；本机仅编辑/Git/调度/保留原件与字节审计；论文与旧Study未改。

### 已实现和真实运行

- `ddbe07e`：timeline选择分为有界逻辑区域与完整相关传统cp.async copy/commit/wait候选；静态机制边界超过128明确编译失败，不偷偷漏采。数据操作优先于索引helper；保实际wait num与角色、plan version1。旧非timeline选择不变。NVIDIA真实GEMM原本全漏的10/14个async候选现已全部记录。
- 真正native构建：controller33610、worker33614/start8014879/PGID33614，127步rc0/167.825s；DD native wheel390537589 bytes，SHAfd3e8f3311a7725f91b08ce095c6741bdbecbc28d4309b8301d7c9d4d6c77775。新稳定source路径`/workspace/chijin-timeline-r003/source-work/FlagPrism`；原Gitarchive不可变保留。matching旧build路径复用后实际编译新TU，不换Python假冒C++。
- `1c228404e15845ccfada04e00e51b08009783a95`：产品timeline_nvidia_async.py，从完整observer记录及真实commit/wait规则恢复identity-bound logical groups/first guarantees；部分wait覆盖、空记录submit集合、多submit、一观察者状态、loss禁猜、capture/inv隔离和线性大小保留。physical buffer_slot/iteration为None，不把逻辑ordinal冒充物理buffer代数；time_arrow_verified固定false，待独立clock与最终编译对象闭合后由公共验证层处理。
- 模型CPU v1为27项normal/-O，增加两类畸形类型拒绝后v2为29项normal/-O，均terminal rc0。v2产品文件hash与实际1c安装文件相同。1000组case证明首次保证边/范围规模线性。CPU fixture不是设备证据。
- 1c相对DD只有三个Python/test文件变化；stable source的全部旧regular files在写delta前逐字节核。Python-only重打包46.395s，Ninja no work，七个native .so members逐字节相同；不是第二次changed-C++ build。package wheel390541367 bytes，SHA7128dc09a1feae71cba11466de82c19ba00bbdae00c2111550f7ff78d8c6c2b9。新安装600 members逐字节核、native normal/-O包括plan未知版本等8负例通过。
- 安装prefix `/workspace/chijin-timeline-r003/runs/package-install-v1/output/venv`。package controller34273/worker34277/start8060482；install controller34417/worker34418/start8070146，rc0/16.893s。
- 真实device-async-v1：controller34453/worker34454/start8074046，argvSHAeac45379，rc0/3.570s。5ordinary+5automatic请求，递推runtime K3/7/11同binary，GEMM stages2/3通过数学、输入与tail。State改为唯一logical program的increment并检查1，最终独立oracle/物理lowering资格仍待完成；开发collector显式同步，不能冒充生产deferred owner。
- 独立raw/fact审计：1952记录、30编译产物SHA、全部async endpoint/member引用。阶段2为64组/32wait/64首次保证边，阶段3为80组/32wait/80边且wait num为0、2；每observer至少两组且最终drain覆盖全部。五组capture/inv身份独立、binary与实际compiled object相同。并非hardware busy/实际传输字节/精确完成时间或verified时间箭头。
- 原件 `artifacts/timeline/run-003/preflight/async-v1-original-evidence.tgz`727945 bytes，SHAec7e4c1150e0d492545684f93d063173a932154392e05d86ad573e76b31cc13f。小公开索引与完整限定位于`integration/evidence/timeline-async-r003/`。未做GPU性能/吞吐/开销认证。

### 工具环境与真实失败

- NVIDIA Docker新tools venv自带pip22.0.2不支持--report，首次install失败保留；尝试从官方PyPI下载新pip，又因NV host网络无外网路由失败，终态rc1/123.085s。没有改变宿主机/daemon网络。
- GCU现有Docker与Asc现有Docker实际PyPI GET都200，Python分别3.12.3/3.11.15。GCU现有pip24为NV Python3.10下载perfetto0.58.2纯py wheel和protobuf7.36.2 cp310-abi3 wheel，controller374496/worker374497/start1003262570，rc0/39.321s。root核SHA后仅转移bytes到NV，依赖安装仍在serverDocker。
- perfetto wheel344338 bytes/SHA024d37db3e1938a0247311337daf419c7204af757fb303cdc1dca46fa8d83cfe，与官方PyPI一致；protobuf wheel343223 bytes/SHA89f23aa53c24553a2416fd4fd1ec06f74fa42b14b546d8883128813f775bbfd2。
- NV已有main build pip26.2.1用官方--python选项在全新tools venv离线安装，不patch产品/不改系统pip。tools-offline controller34730/worker34731/start8140773，rc0/2.819s，TraceProtoBuilder/TrackEvent导入真实通过。路径`/workspace/chijin-timeline-r003/runs/perfetto-tools-offline-v1/output/venv`；不是Trace Processor/SQL/UI验收。
- SDK0.58.2实际内置TP manifest固定v57.2 linux-amd64，native14008280 bytes/SHA55ba613fc6d4f71df81eee2dbfc293020063655c241b3e314bff75345b802684。官方release zip SHAa5354a4a133cc629bb398da53c95515e5a49d4bd96edfebe1ebc3221c85d936f；UIzip SHA3d4043c4451faaddec8f382b1a0efae4c33ca9b168ec037da32e53c1cc308408。
- GCU主Google URL urllib timeout；Google alias+Github备用脚本在首个alias请求卡住被父deadline120s杀掉（374552/374553），后面的Github并未尝试，不能说两项都失败。独立Github-only新job374581/374582也权威timeout120s/-9；只开始linux-amd64.zip，UI未开始。Asc独立官方Google job2439461已终态失败，日志见asc-tp-status-1。原失败与未完成下载不覆盖/不重试同一live handle。
- 已通过request_user_input_async询问可用代理或现成TP/UI路径，问题仅请求环境信息，不是新权限；回答尚待用户。全goal不能因此blocked：仍有大量不依赖工具网络的实现可做。
- 本地准备曾有一次读取尚未完成的传输文件和一次解析被截断的manifest失败，均未启动远端安装；已改为确认传输终态及提取完整linux entry。它们是编排错误，不是产品测试失败。

### 下一工程动作（尚未实现，不是放行）

1. 紧凑采集：现NV按完整grid分配scratch，只有首末写，不能作为一般默认。加显式storage版本；predicate默认按实际grid首末，固定program高级选择可支持。GlobalScratchAlloc按紧凑slot寻址，header仍写真实logical program；所有Init/Save/Restore/Finalize/clock/logger访问要按选择受控，尤其WS的global上下文读写不能碰未选槽。host preallocation验证实际grid/stride/num_ctas并仅分配selected slots，超uint32等边界启动前拒绝。decoder已有(slot,logical-program)映射。当前普通probe4warps/32KiB不是冻结默认；考虑warp0/4KiB等稀疏策略，先以真实证据比较扰动再冻结，勿改数学/容差隐藏问题。
2. 真正per-invocation owner/完成event与deferred D2H：保buffer和metadata/device/stream/selection快照；禁止旧逐launch native exit parser/SM-cycle解释用于globaltimer；完成前取消隔离不可释放，累计budget admission在用户设备副作用前。接公开CLI/API和bundle，别再仅停留在开发collector。
3. 共同时钟/规范化/Perfetto：可以复用同目标getter的原语证据，但重新核target/driver与实际getter/record链、单位、epoch和精度。marker最终指令位置与纯算术SSA边界、opaque asm/未知lowering对完整group闭包的影响仍待验证；当前逻辑facts不能直接当verified时序关系。大ticks先整数减origin；UIrawuint64详情用不丢精度的表示。独立域不能放同图归零；不编造engine busy/精确completion/physical buffer generation。
4. NV第一个完整P01后小版本冻结，再GCU/Asc自动时间/动态机制/clock链；可提前做真实机制可行性调查。现无一后端整体P01通过。独立六新数学、真实SQL/UI、最终额外三GPT-6.1-Sol/xhigh代码走查与所有旧mode/生命周期/缓存回归仍必达。

**T008 收尾进程核**：NV所查workers均gone、controllers仅Z且无compute-app；GCU与Asc所查owned PID均missing（ps仅header/exit1是无匹配，不是环境连接失败）。无新的活动构建/设备/网络下载任务。不得杀PID1清僵尸。源/原件/字节索引均保留；goal仍active，工具网络问题不构成全目标impasse。

**T008 Git交付**：`34b0462` 已推送 ChijinZ/FlagPrism:detailed-profiler，fetch祖先核、SSH push、ls-remote精确HEAD `34b0462` 与worktree clean通过。本轮两个功能提交加证据提交；小索引14个文件全部bytes/SHA核通过，actual源码/原件/wheel与安装位置如上。没有标goal complete/blocked；代理/现成工具路径问题尚待用户，下一轮继续紧凑采集、owner、公开入口与完整导出链，不能因网络工具问题停下其它工程。

## T009 设计与验收更新、第三轮独立设计评审（文档阶段）

- 用户要求：更新设计/验收文档，三个独立 subagent 评估合理性及实际可行性；本次不启动新的设备作业或产品测试。
- 基线：34b04624098b99b2004f9b0e9cf1c602db5509cf。设计新增 §8.9 最小接入合同、能力按项递进、机制闭合、紧凑 storage 资格与实施顺序；验收新增 §8.4，复用 P/E 矩阵，不增加资格数学数量、不降 P01 或最终门槛。同步执行合同引用。
- 评审输入：integration/plans/timeline/reviews/round3/INPUT.json；三位 fresh-context reviewer，独立核相同三文档 SHA、可只读源码、不读 peer 报告；本轮设计评审不替代三个最终指定配置代码审阅。
- agents：timeline_round3_compiler、timeline_round3_runtime、timeline_round3_portability；初审与有限复核均完成。三席“有条件可实施”，无 confirmed blocker/major。R2/R3 同一 minor 为 group-only 与真实复用资格歧义，已在 P07/§8.4 明确：完整资格仍必须真实两轮 buffer/flag 复用。最终三 SHA 与复核输入一致，原报告保留。
- 评审总索引：integration/plans/timeline/reviews/round3/README.md。使用继承默认模型（未覆盖），实际 serving 型号未知；不替代最终三个指定 GPT-6.1-Sol/xhigh 代码走查。
- 尚无新增 build/import/产品测试、SSH/设备/Perfetto/UI。现有功能边界和所有设备证据不因文档更新改变。

T009 文档审计：96 个本地链接有效；三文档最终 SHA/根与跟踪合同同字节/PLAN_INDEX 逐文件字节和 SHA 审计通过；仅文档，不代表功能通过。

T009 文档已提交 `32c1f7a`（detailed-profiler），正式 worktree clean。提交包含设计/验收/合同引用、三独立初审和有限复核、处置索引。未运行产品/设备测试，未改论文或旧 Study；完整时间线 goal 仍未完成。

## T010 紧凑 storage ABI 与实际 grid admission

- 上一 goal turn 为有效进展：T009 文档/三独立设计评审及复核已提交32c1f7a；本 turn 回到实现，不重跑旧成功原语。
- 已提交545bf8a75af369c893ecc7331cb9c157c4151159：timeline_storage_version=1；固定选择映射ordinal slot，默认使用实际运行grid首末；全局header保持真实program；Init/Save/Restore/Finalize/logger与timer均受选择约束。旧无storage格式仍走旧布局。新增公共无分配admission函数和CPU正负例，实际binary不具storage资格不能配紧凑allocator。
- GPU0预检RTX PRO6000/15MiB/util0。新native任务服务器Docker chijin-study-pro6000，controller34797；native build worker34801/start8436326/PGID34801，实际/proc已确认live，非SSH观察文件推断。/workspace/chijin-timeline-r004/native-545bf8a/{controller,terminal}.json，日志同目录；native CPU无设备任务。复用匹配object目录，稳定source-work逐字节核old1c/new545，预登记41文件差异；前序owned workers不存在才变更。15个实际build步骤进行中，已见更改的C++ TU重新编译，无native通过声明。
- root编排/首次状态：artifacts/timeline/run-004/preflight/，新原始archive/controller/expected-changes和SHA均保留。
- 本地随后扩展开发probe，加入同binary不同实际1D/2D/单program/tail、逻辑副作用次数与allocation canary；仅测试脚本增量，不改运行中已冻结native源码。待提交/传输后用脚本SHA标识。
- 仍未完成：production owner/延迟导出、public timeline、真实clock证明/Perfetto，GCU/Asc新timeline，全P01/独立数学/最终三个指定reviewers。当前目标保持active，不改变完整验收。

**T010 结果与恢复定位**：

- 新native545bf8a实际15个Ninja步骤、90.616秒、rc0；wheel390626917bytes，SHA2698327dc5b73fe1b974a53163534e0ede9c28c1066b5c7c0e2aa3c83c0fdcab。独立安装 `/workspace/chijin-timeline-r004/runs/install-v1/output/venv`，601成员逐字节核；native11negative及storage7CPU方法normal/-O均通过。稳定source-work仍为545源码，未因test-only更新重复构建。
- 开发脚本source-only提交984aa15/546a488/3a818c9，首次device-v1 terminal rc1/1.817s：Triton kernel[grid]包装器warmup=False与测试编译预检参数重复。c624342改显式.run，device-v2 rc0/3.921s。bee1f81增加重排三slot真实case，device-v3 controller35328/worker35329/start8458099，rc0/4.021s。失败原件保留，不修改数值容差或旧收据。
- v3共10ordinary+10instrumented、10capture/2528真实record；recurrence K3/7/11共享binary，GEMM2/3保留asyncfacts；grid_map同binary运行(1,1,1)/(7,1,1)/(3,5,1)/(1,1,1)，重排selection(14,0,7)单独binary。首末与固定slot、数值/tail/input/原副作用次数/allocation256bytecanary全部通过。真实stride32896，grid15默认raw65792（旧full-grid请求493440），单program32896，三固定slot98688；这些是物理空间不是性能收益。
- root未import产品，独立读原始bytes核所有header/slot/program、counter/sequence/site/phase/full64tick/offset、原始编译artifactSHA和实际gridbinaryhash。原archive1147214bytes，SHA4f31ae247eb543f5829b3f67fc8e4b4cc57f3dce51e87b2493d98012e59ed017；artifacts/timeline/run-004/preflight/compact-original-evidence.tgz，审计compact-root-audit.json。公开小证据integration/evidence/timeline-compact-r004/。
- T010五个jobs terminal；最终/proc核所有workers missing，controllers仅Z underPID1，不干预PID1。没有活动GPU任务、无GCU/Asc本轮新作业。
- 阶段边界：collector仍显式同步每capture，不能当production owner/并发通过；没有clock/epoch/final marker-order/Perfetto证明；不把真实逻辑cp.async关系升级verified时间箭头；三后端完整P01仍未过。
- 下一动作：在现有hook/allocator边界补逐invocation不可变owner、原stream完成句柄及deferred D2H，pending总预算与异常安全；以当前新安装/545稳定native为起点，不重复已成功storage矩阵。之后接公共timeline入口/规范事件/clock/Perfetto及GCU/Asc纵向链，完整目标和独立资格/三个最终指定审阅不变。

**T010 Git交付**：HEAD `04e82db5640c51e05230735cf158f095a486a7dc` 已fetch祖先核后推送 `ChijinZ/FlagPrism:detailed-profiler`；ls-remote精确同值，正式worktree clean。T009设计文档提交亦包含本次push。新增code/native/tests/evidence均有提交；根live record仍在Git外。全部owned jobs terminal，无活动设备任务；完整目标仍active，未mark complete。

## T011 逐调用 owner 与 CUDA deferred completion

- 上一turn是有效进展：T010紧凑storage实际native/安装/2528raw与Gitpush已完成。本turn不重跑旧storage数学矩阵，补生产可复用runtime模块和真实两stream开发用例。
- 初始实现7c5a7be，文件尾规范56d5716da899f040fd048dd397b0f445f457da47：timeline_runtime.py通用owner/会话预算/独立不可变快照、显式提交状态/完成轮询/读回重试/隔离保留/安全释放；timeline_cuda_runtime.py负责实际CUDA分配、原stream初始化/完成event/D2H/canary。没有逐launch synchronize。规划layout委托实际transport，不把NVIDIA物理格式逻辑塞进公共owner层。旧self.buffer计数/native hook未改变，public timeline接入仍待后续。
- 新CPU15方法覆盖预算/身份/快照/异常初始化/完成句柄失败/超时/提前释放/D2H重试/线程拒绝/丢失外部引用仍保留owner；真实开发脚本排两stream六次连续提交、逆序导出、第七次预算拒绝及释放后恢复。此时均尚未取得通过结果。
- 新Python-only包装：/workspace/chijin-timeline-r005/package-56d5716，controller35523/start8524675，匹配r004545原生构建；稳定source-work旧545归档逐字节验证后仅预登记变更20文件（含两productPython/测试与小证据），无native改动；必须所有native wheel成员与545逐字节相同，不重复C++编译。root artifacts/timeline/run-005/preflight/保存archive/控制器/桥接SHA。新脚本已备好但未据无terminal状态启动设备。
- 完整目标未完成；三后端P01/公开入口/clock与最终marker/Perfetto/独立资格及三个最终指定审阅保持必达。

**T011 结果与下一恢复定位**：

- 56d5716 Python-only包装46.441s/rc0，wheelSHAe3452ec03cec29a38977aa52e230d8cacbcea75dfeeb2c6f7860f41f2bb3a202；独立install-v1 rc0/14.889s，15owner+7storage方法normal/-O及device-owners-v1 rc0/2.819s。没有首次失败。
- 2c5c85c1e0d3068f4ad689a55e43088017298aaf加固线程归属（Thread对象防OS ident复用）及非bool completion负例、runtime文档；delta包装46.445s/rc0，wheel390631260bytes，SHA5406558bf3c36e7fe949d9dbde62bfad2253e3747da7f97c4e1d7ac19768d03e。两轮均Ninja no work，全部7native成员逐字节相同，初始桥接r004545实构native，未重复C++build。稳定source-work现在2c源码。
- 最新真实安装 `/workspace/chijin-timeline-r005/runs/install-v2/output/venv`，603成员byte核，16owner+7storage方法normal/-O通过，14.891s/rc0；真实device-owners-v2 rc0/2.819s，脚本SHA75de2cb8d165c9b7293a94f1fbc137e1938539a13178a82a8dad398644df0db2，源码/installed两模块SHA与当前Git一致。
- 实测7ordinary+7instrumented+1额外预算拒绝请求；同binary不同runtime K/grid3/5，两个实际stream交错提交6次，首次read在全部6次launch返回之后，6个在途device allocation pointer互异。按5/4/3/2/1/0逆序读回、持久化后release；第七次预算拒绝device counter保持0；释放后第7次合法提交/读回成功。数值/input/tail/原program副作用计数/canary全部通过。此为组件/开发collector结果，不宣称旧共享buffer公开hook已支持两stream。
- 原始1536record header/counter/sequence/site/phase/full64tick/offset及7capture调用/stream/binary/grid身份由root仅读保留bytes独立审计。archive142815bytes，SHA699cc426883f81e117fc08b67bd1b5bfc16309878f34d9f4c7c91093c08a7b39；artifacts/timeline/run-005/preflight/owners-original-evidence.tgz；审计脚本audit-retained-owners.py、结果owners-root-audit.json。公开小证据integration/evidence/timeline-owners-r005/，运行时文档Profiler/docs/timeline_runtime.md。
- 最终实际/proc检查：r005两个包装、两个安装、两个device jobs全部terminal；worker全部missing、controller仅Z underPID1，不干预PID1，无遗留live设备/浏览器任务。没有GCU/Asc本轮设备工作；论文/旧Study未动。
- 下一动作：将已验证pool/transport接入真实InstrumentationHook或专属timeline hook及公共detail timeline请求，按实际加载function绑定manifest；不经旧native SM-clock parser、旧self.buffer、逐launch synchronize。需处理load callback缓存命中、编译cache身份、abort/exit/finalize的owner映射与错误阶段，保持旧count/native不回归。然后公共规范事件/clock证明/Perfetto链，GCU/Asc真实纵向/P01，独立新数学和最终三个额外指定reviewers。当前没有任何完整P01通过；目标保持active。

**T011 Git交付**：HEAD `4198c49bb5ff34582361c53faa338265211cddd1` 已fetch/祖先核后推送ChijinZ/FlagPrism:detailed-profiler；ls-remote精确一致，worktree clean。公开证据10个被索引成员/11文件、链接和逐字节SHA核验通过；root live record在Git外。设备任务全部terminal，无活动owned设备工作。完整goal继续active，当前下一步是public hook/CLI及clock/Perfetto接入，不能以本轮owner功能或设计三审替代最终验收。

## T012 公共timeline收集入口与真实hook接入

- 上一goal turn为有效进展：4198c49 owner模块/16normal-O合同/真实两stream1536record已push。本turn实现真实公开detail timeline，不再只在自定义开发allocator里使用pool。
- freeze67322072bb495164b7397fc283920adf4492ee93：profile.start(detail=timeline)、CLI --detail timeline；InstrumentationHook timeline分支使用独立owner、实际function/binary/grid/stream admission，enter/exit绑定原LaunchHook同metadata身份，skip旧SM-clock nativeparser、退出只记完成event；finalize读回持久化raw/decoded/逻辑async/源与编译产物，timeline/index.json明示partial_clock_unverified，不伪造ns/Perfetto/verified箭头。既有count路径兼容，显式不支持nested timeline会话。
- 新preallocation-admission.patch v2：CudaLauncher.profile_admission_version=2，preflight传实际stream；旧CudaAllocator可接受可选stream。公共timeline启用前核version2并把真实libtriton/driver/hook/runtime文件SHA放JIT cache key。
- 配套parent launcher由旧patch反向、再新patch应用；先在单文件隔离副本演练，再精确核原文件SHA后修改实际parent副本。receipt parent-launcher-delta.json保before/after/SHA；仅拥有的FlagTree源码副本，不动系统driver/daemon。
- 包装/package-6732207 controller36096/start8627966；wheel390635643bytes/SHA bd0f484fe0637212a3f607bb5513537a36136b5b98eb38985d5cf35ae14d36da，46.444s/rc0，7native成员与2c/545原生build逐字节一致，Ninja无工作。source-work现在673源码。
- 当前安装检查 /workspace/chijin-timeline-r006/runs/install-v1 已启动，检查owner/storage normal-O、既有automatic_hook pytest及CLI help；先核terminal再启动设备，不以SSH返回认为测试通过。root artifacts/timeline/run-006/preflight/保所有编排脚本/源码archive/原始状态。
- 新真实用例ordinary_timeline_workload.py不含手工scope/site/编译器helper，3runtime-loop recurrence（两stream）+1普通GEMM；p01_nvidia_public_timeline.py准备实际API冷/暖session（同JIT对象/加载handle）与公开CLI、host-once/math/tail/input/原副作用、4capture/2binary/动态逻辑group、standardmanifest；尚未取得设备通过。完整目标/clock/Perfetto/三后端/P01/独立资格/最终三代码审阅仍未完成。

**T012 结果与恢复定位**：

- 6732207包装/安装v1 rc0，owner16+storage7 normal-O、legacy automatic_hook3与CLIhelp通过；真实public-v1 rc0/9.179s（APIcold/warm同JIT对象、CLI共12capture）。
- 发现并修复导出错误分支跳过native.finalize的代码缺陷；新增单元故障注入保证native finalize和cleanup仍发生。3ebf1a276aeb8c58e93446bee0b359507abf2511另补zero-grid allocator None无owner路径。新真实测试包含zero-grid、故意export失败后持有owner离线raw恢复/无replay、后续正常API、旧auto count CLI回归。
- 新package-3ebf1a2/terminal.json rc0，Python-only/Ninja no work/7 native成员与673→2c→545实构逐字节一致；wheel390635688bytes，SHA0600be7e891b177083393a77f1d63c7ed982b6d36ef06716a5e18f09cf146952。source-work现在3eb源码；独立安装 `/workspace/chijin-timeline-r006/runs/install-v2/output/venv`，604成员byte核，安装检查20.401s/rc0。owner16/storage7正常-O、public故障/旧ABI拒绝2正常-O、legacy automatic_hook3、CLIhelp全通过。
- device-public-v2 controller37014/worker37015/start8675285，rc0/14.337s。5组timeline工作负载（APIcold/warm、export失败后同raw恢复、后续API、CLI），每组3recurrence+1GEMM非空调用及1请求zero-grid；20非空capture，6720raw record/400逻辑commit group。zero-grid无数据/副作用/伪capture。另一个旧--detail auto CLI运行同非空数学（明确skip-zero），4count capture/observations保留，没有timeline目录。
- 公开采集完全通过实际start(detail=timeline)/--detail timeline、原InstrumentationHook/LaunchHook与新pool，不用开发collector插scope/site/预编译/replay。普通工作负载与API测试source SHA保存在check-input-v2及工具launch收据；独立auditor核cold/warm实际loaded function handles相同，所有invocation/binary/stream/source/compiled artifact身份与bundle manifest hash。导出故障是测试故意注入，原异常和native中间件保留；已确认缺陷是之前代码跳过native finalize，现已代码/CPU/设备恢复闭环修正。
- 原始archive3016461bytes，SHAd3e6cc4b55116d1496b4a586e6ffd58de8b1728ae884a74c18329fc1030f5448，artifacts/timeline/run-006/preflight/public-original-evidence.tgz；audit-public-raw.py仅读保留bytes无产品import，public-root-audit.json核6720event/400逻辑group及所有compiled/raw/bundle文件。公开小证据integration/evidence/timeline-public-r006/；Profiler/docs/timeline_runtime.md更新实际公开入口及raw-stage限制。
- 可审阅原始目录：/workspace/chijin-timeline-r006/runs/device-public-v2/output/{api-cold,api-warm,api-after-failure,cli}/timeline/index.json；recovered-raw.timeline/index.json为同原调用离线恢复。不是pftrace/ns图。
- r006六jobs全部terminal，实际/proc worker missing、controllers仅Z；最终SMI GPU15MiB/util0/无compute-apps。无GCU/Asc本轮工作，无论文/旧Study改动。
- 下一动作：以最新3eb安装/launcher ABI2继续规范化事件/实际clock单位epoch与最终机器边界证明/Perfetto；Native timeline_selection_policy正确，但init_handle沿用旧automatic_plan.policy/semantics别名，进入canonical模型时需同步为实际timeline策略/未认证ticks语义，不能把旧别名用于性能推论。默认observer预算、公开请求扩展/overflow路径也须在最终资格前冻结并实证。尚缺三后端完整P01、物理buffer/flag真实复用证据、GCU/Asc新timeline、独立六数学/受控优化、真实TP/UI、最后三个额外指定Sol6.1 xhigh代码审阅，完整goal未完成。

**T012 Git交付**：HEAD `97d591dfbc5ee7bb84c2d3144466051237740910` 已fetch祖先核后推送ChijinZ/FlagPrism:detailed-profiler，ls-remote精确相同，正式worktree clean。14个公开小证据文件（13被索引成员）/runtime使用文档逐字节SHA及链接审计通过。根live record仍在Git外。当前无活动owned设备作业，完整goal仍active，尚不能mark complete。

## T013 公共raw事件模型与backend规范化

- 上一goal turn有效进展：97d591d公开timeline真实hook/API/CLI、cold/warm句柄、20capture/6720record/400逻辑组/恢复/旧count已push。本turn新增公共typed raw时间事件模型，仍不假称ns/Perfetto通过。
- 867b0cfa016c9f6f3caaf8ade2afa2d486da779e：timeline_events.py公共schema1/强引用与身份/byte-span/配对/语义/完整性/预算校验；不内置warp/SM树、不认证clock或机器边界。timeline_events_nvidia.py把实际原始记录映射source navigation/sites/observer/interval/incomplete；actual首末program恢复3D坐标，SM只标finalize_header的观测位置。循环occurrence不当iteration；完整流严格nested/连续；丢失保留孤立端点和window内真区间，不补end、不跨gap配对。
- 原机制record ID与公共record ID显式map，便于下游公共依赖/Perfetto，不靠name/proximity。公共runtime IDs绑定capture/invocation/binary；source仅导航，不冒充精确cost归属。解码前额外持久化*.input.json，保raw+metadata原件以便后续解码/预算错误恢复；旧automatic_plan.policy/semantics别名同步实际timeline选择/未认证ticks语义。
- 99c2e308dea889a181a91e0c89ac22476b74dbc5测试增量：普通数学运行runtime K1021，主动超出默认512records/observer环容量；检查数值与原副作用，以及真实incomplete/overwritten/孤立端点/不推断依赖。CPU15合同覆盖nested/orphan/身份错配/source与record引用/大tick/布尔假值/raw越界/伪clock/静默丢弃/重复duration/假iteration/额外role/budget。
- Python-only package99c2e30 controller37471/start8819180已terminal rc0，Ninja无工作/7native成员与3eb→545逐字节相同；wheel390643399bytes/SHA632bdb61f138a4a15ba2428cbdfb7228d1403169c10cfcc6a017e27ce812e641。稳定source-work现在99c源码，parent launcher仍ABI2不变。
- 最新独立安装 /workspace/chijin-timeline-r007/runs/install-v1/output/venv，安装检查19.598s/rc0，新增事件15+owner16+storage7 normal/-O，以及公共合同2 normal/-O、旧automatic_hook3、CLIhelp通过。CPU假后端/合成loss不算GPU证据。
- 真实device-public-v1已启动（同server既有Docker），必须查terminal和/proc状态后收尾；root artifacts/timeline/run-007/preflight保源码archive/桥接/控制器/状态。尚未取得本轮设备通过结论。原有三后端完整P01/clock/最终边界/Perfetto/独立资格/最终三指定代码review仍未过。

**T013 结果与恢复定位**：

- 99c2e30初版真实device-public-v1 rc0/16.892s，正常与实际overflow全通过；随后修解码前journal沿用raw_complete标签的歧义。d15933a777e0be39fabc2d1efa25e8613ba152e0改为raw_persisted_pending_decode并在真实普通/overflow数据中核对。原v1完整保留，未更改容差/损失分母。
- package-d15933a已terminal rc0，Python-only/Ninja no work/全部7native byte同99→3eb→545实际native构建；wheel390643425bytes，SHA85b1e82aeffbef59464bed333db5d7aa113528a6e52a81efd5b6635b98b1b557，controller38282/start8855904。source-work现在d159源码。独立安装 `/workspace/chijin-timeline-r007/runs/install-v2/output/venv`，606成员byte核，19.548s/rc0；canonical15+owner16+storage7 normal-O，public合同2 normal-O、legacy_hook3、CLIhelp均通过。
- device-public-v2 controller38646/worker38647/start8873833，rc0/17.093s。21timestamp capture（20正常+1真实overflow），10816物理record，5400真实配对interval、16孤立endpoint。K1021每observer written2056/retained512/overwritten1544，8observer共12352 overwritten，首个loop-body exit及SCFfor退出只有end，未填造begin；window内仍保2040实际pairs。全部normal20caps有3360pairs；400逻辑group仅来自complete cases，overflow无group/dependency猜测。旧count CLI另4capture继续通过。
- 普通工作负载数值/input/tail/每program副作用、warm loaded handles、两stream/混合binary/zero-grid、导出故障同raw恢复/后续API、真实CLI均通过。公共IDs绑定capture/inv/binary，所有机制record_id有显式map。original*.input.json只表示已持久化待解码；*.events.json.complete仅raw/pair完整，不表示clock或机器边界认证。clock_status和boundary_status均unverified，iteration_id均None，不把occurrence当循环索引。
- 原件archive9139936bytes，SHAdbd58d06e69418306bd7ab98b0607a757e98f962b7c613ef6fd53763dbc5301e；artifacts/timeline/run-007/preflight/events-original-evidence.tgz（913members）。独立audit-canonical-events.py只读保留bytes无产品import，逐条重建rawheader/counter/ring seq/tag/fulltick/offset、nested pairs/orphans、ID namespace、backend record map、source snapshot/编译artifact及standardmanifest hash；events-root-audit.json已保存。第一次本地审计脚本括号语法错误已改，无产品或设备重跑/数据更改。
- 文档Profiler/docs/timeline_events.md；公开小证据integration/evidence/timeline-events-r007/。真实正常/overflow示例 `/workspace/chijin-timeline-r007/runs/device-public-v2/output/{api-cold,api-overflow,cli}/timeline/index.json`，capture JSON里的events_file指向公共事件。
- 最终r007六jobs均terminal、实际/proc workers missing/controllers仅Z；SMI GPU15MiB/util0无compute-apps；无GCU/Asc作业、本轮无paper/旧Study修改。cuobjdump/nvdisasm在PATH未发现（machine-tools-and-final-state.txt）；这只是工具定位结果，先找已有Toolkit或Docker中隔离安装工具，不能当不可实现的环境阻碍。
- 下一实作：优先实际clock getter/周期、分辨率/epoch与误差证据、最终SASS marker顺序/所观测区域合法性，而非继续只做raw展示；有证据的时间视图再喂公共Perfetto。clock证据不从UI宽度/marker名推断，不强求不必要的跨SM epoch；目标async可用有来源语义泳道但仍需实际动态关联/物理buffer/flag复用和真实TP。模型Source fallback的provenance文字在source_sha缺失时应进一步分清仅compiler location与确有snapshot，认证来源时清理此描述，不能据文字声称已有source证据。raw schema1保守拒绝regressing ticks，真正wrap/reset需explicit evidence/版本化模型。GCU/Asc接口、独立六数学/受控case、公开扩大采样参数与tiny-buffer/fault矩阵、TP/UI和最终三个指定Sol6.1 xhigh代码走查仍未完成。完整goal保持active，所有后端完整P01尚未过。

**T013 Git交付**：HEAD `dad8e7c98632ef7cbd2b4677d9c5101a517a88dc` 已fetch祖先核后推送ChijinZ/FlagPrism:detailed-profiler，ls-remote精确一致，正式worktree clean。12个公开小证据文件（11个索引成员）及事件schema文档SHA/链接核验通过。根live record在Git外；所有owned jobs terminal无live GPU任务。完整goal仍active，clock/最终机器边界/Perfetto和三后端资格未完成，不mark complete。

## T014 用户要求：适配边界文档更新与三个独立设计评审

- 用户本轮要求更新设计/验收文档，并由三个独立 subagent 判断合理性和真实可行性。本轮工作限文档与只读静态审阅，不改产品/论文、不以设计评审代替最终代码走查，也不宣称新设备验收通过。完整工程 goal 未完成。
- 基于 dad8e7c 更新设计 §8.10：按目标及工具链组合 compiler/transport/decoder/clock/mechanism；区分同工具链新型号、相近模型不同工具链、新执行模型；分离编译计划/实际launch绑定及 immutable raw/认证ns派生视图，明确 A/B/C/D 推进门。验收 §8.5 复用现有 P/E 样本定义组合错误、共享消费者、真实设备与CPU fixture边界。修正公开 timeline 已有raw入口却写成未实现的过时描述。
- 三个 fresh context 请求均由工具接受 GPT-6.1-Sol/xhigh：design_feasibility_compiler、design_feasibility_runtime、design_feasibility_portability；实际 serving 型号未暴露。初审设计/验收字节冻结于 integration/plans/timeline/reviews/round4/REQUEST.json，三者不读peer报告，禁止连接设备和产品执行。后续留初审原文，确认缺陷修订后有限复核。
- 不重跑旧原始数据/构建；此前 run-008 工具下载属于前序工程上下文，本次未启动或重启下载/设备作业，不据旧记录声称其终态。

**T014 文档评审结果**：三份 fresh 独立初审分别为有条件合理、有条件合理、设计合理，无 confirmed blocker/major。三席确认合同仍写入口未实现，R2/R3还确认设计顶部把当前状态指向历史8.8；均已修正，并同步根/跟踪goal历史baseline及8.10/8.5章节引用。三席最终有限复核全部确认相关minor关闭、无新增矛盾、门槛未降低，最终输入SHA一致；初审原文保留。汇总及报告：integration/plans/timeline/reviews/round4/README.md。后续仍必须实证最终编译边界、逐目标clock、Asc/GCU发布/owner及两轮真实buffer/flag复用；设计审阅不代替任何P01、独立资格、Perfetto或最终代码走查。只做文档静态核验，无本轮产品代码/测试/新SSH或设备工作。

**T014 Git交付**：`197458e7145a90db844dea1659de110ec256f2a9` 已推送 `ChijinZ/FlagPrism:detailed-profiler`，fetch祖先检查、ls-remote精确HEAD及正式worktree clean已核；15个文件仅设计/验收/合同/索引/初审与复核报告。111个本地文档链接无缺失，43个索引文件SHA/bytes及三席初审和最终输入SHA核对通过，根合同与快照同字节。未运行产品测试或启动设备工作，完整时间线goal仍未完成。

## T015 恢复实现：实际SASS与独立时钟验证

- 上轮T014属于有效进展（设计/验收/三独立复核与197458e推送），本turn继续真实工程，不缩减完整goal。正式worktree起点clean。
- 已poll既有GCU工具下载v2：controller374660/start1004102749、worker374661/start1004102753，terminal rc0/1.267s，controller现/proc missing。两官方13.2.86 wheel SHA匹配（nvdisasm53606e71…、cuobjdumpd332c2ff…）；原件archive4762266bytes/SHAa2c039f25b40e501e2f48133aa998c4000653397e14017f85762b374e8f2954a。无重复下载。
- NV实际GPU0空闲15MiB/util0，复用chijin-study-pro6000。隔离tools-install-v1 controller39124/start9039008、worker39125/start9039011，terminal rc0/2.118s；venv路径 /workspace/chijin-timeline-r008/runs/tools-install-v1/output/venv，NVIDIA官方13.2.86工具真实反汇编r007两个原cubin（SHA2e0f758a…与6cb6cada…），不是新跑旧数学。SASS确认实际CS2R GLOBALTIMER、LDGSTS/LDGDEPBAR/DEPBAR和selected-loop timer/FFMA分支，但尚未认证全部边界/参与者/机制闭合。原件保tools-installed-evidence.tgz。
- 新开发primitive p01_nvidia_clock_scale.py真实递推、runtime K、CPU oracle/input/tail/增量State，显式compile-only无kernel warmup；对照内部tick和CUDAEvent。clock-scale-v1 controller39165/start9046584、worker39166/start9046587，terminal rc1/2.619s。首调用K4096内部10528tick、event110944ns，host bracket122474ns，预冻结10us/2%接近门失败。原数值/输入/tail/State1通过，失败原件保留。原因须区分host提交间隙与物理周期不一致，不能由这一次粗bracket断言timer失效或放宽阈值掩盖。下一修验证方法：专用校准graph将事件/数学记录于设备队列，移除host enqueue间隙；显式9次请求、capture不执行数学以state检查，不用于public graph支持声明/资格替代。

**T015 实测结果与下一动作**：

- clock-scale-v2 controller39352/start9056270、worker39353/start9056273，terminal rc0/2.669s。新测试source SHA858f5eb7d6aff42d7bef55b0f3822134a636aa978367baf3ef105171f0e3ab11；捕获State0、9次显式graph启动State1..9；同cubin2cc47b0fd3147bc9f715e2510b870cd81429dbf7f16ccc9d1f81a3dd89bf2ae0，K4096/16384/65536各3次。内部约10.3–10.5us/40.3–40.5us/160.2–161us；外部CUDAEvent与内部差1856–7456ns，预冻结max(10us,2%)一致性门未改。真实CPU数值/input/tail/计数全部通过。专用校准graph不等于公开timeline支持graph。
- object-inspection-v1 controller39455/start9063125、worker39456/start9063128，terminal rc0/3.571s；全部3对象实际nvdisasm JSON、源码/PTX行、完整CFG命令rc0，无no-dataflow降级。实际公共GEMM静态864指令/44timer/6copy/6commit/2wait，recurrence496/16timer，校准104/2timer；静态数不能当动态组数或机制闭合。原产品cubin仍SHA2e0f758ab2caa18da59470e7a5124e23246703242fe2005b77969652c164a735和6cb6cadad81143bb6a2eac5311dbe203982a2ebbb4187ba6f11c28ac385612ac。
- 新发现：校准begin PC0x90、K-load在其后（尽管源在前），纯副作用marker不足以约束其它op；公共recurrence selected-loop PC0xdb0→FFMA0xde0→timer0xe70→backedge0xf40存在，但不能外推所有site已认证。公共prologue PC0x190 timer为无条件、PC0x1c0再SEL；PTX谓词化不等于所有最终machine timerread被选中谓词抑制，不重复旧IR级零读钟开销表述。记录写入隔离/compactbuffer既有证据不被这点否定，完整boundary/perturbation仍未过。
- root原件clock-objects-original-evidence.tgz SHA354952d0678ea328059a5108db6067999a312c4025fd772517a63d4bcf3cbe33，另tools-installed-evidence.tgz和disassembly-tools-original.tgz的bytes/SHA见clock-objects-root-audit.json。audit-clock-objects.py仅stdlib保留字节审计：实际source/原失败source/cubin/工具输出绑定、9请求/时间差重算、完整CFG无fallback及实际终态；不import产品或重跑CPU oracle。Git小证据 integration/evidence/timeline-clock-sass-r008/共19索引成员。
- NV四owned jobs terminal，实际/proc workers missing/controllers Z，无live owned worker group；最终GPU15MiB/util0无compute-apps。本turn没有GCU/Asc新GPU作业（只poll既有GCU工具下载和取bytes），无runtime/native变化，无重打包/无重编相同C++、无论文/旧Study改动。产品实际安装仍r007/install-v2/d159/545 native，工具prefix单独，不混装。
- 下一优先实作：实际可适用的clock比例/分辨率/端点误差/有效窗口（本次10us一致性门不能当read_error），把最终对象位置/依赖/参与者和manifest逐site闭合，必要时修改通用计时约束；再把认证ns派生视图送公共Perfetto。不得仅因现有ticks看似ns就直接认证/出图。仍缺每后端真实buffer/flag两轮复用、GCU/Asc新timeline、完整P01、独立六数学、受控case、TP/UI及最终三额外Sol6.1/xhigh代码走查，完整goal保持active。

**T015 Git交付**：`20cb1dcf946d504464f7da4fa75e40604e88919c` 已fetch祖先核后推送 `ChijinZ/FlagPrism:detailed-profiler`，ls-remote精确相同，正式worktree clean。21文件为1个实际新clock测试+19成员小证据/索引；无产品runtime/native变更。公共证据约63KiB，完整原件和新工具venv留服务器/根artifact，未提交私有SDK/巨大trace/工具二进制。末尾静态核校准State写者：SASS PC0x4f0结合lane0/首warp谓词，PC0x580非该谓词EXIT，后续唯一State load/add/store；单program测试无非法多写者oracle。完整三后端目标未完成，active不mark complete。

## T016 通用compiler边界依赖实现与native重建

- 上轮T015为有效实证进展20cb1dc（真实SASS/9次设备队列时钟一致性及source调度跨界新发现）。本轮实现通用LLVM SSA约束，不改论文、不按算子名/shape/site特判，不把约束或计时原语升级成最终机器/clock认证。
- freeze bc460c8eb6f5aaf9d00b1e0c3aedfe2c6b07c09a：自动scope标记原被观察op，ProtonToGPU按实际operands/results建立begin-counter→逐值bitwise anchor→原op→end-counter的SSA链；tokens/memdesc不伪装寄存器值，异步状态需另证。新增GPU boundary_anchor、read_counter variadic dependencies、后端clockWithDependencies/anchorValue扩展，NV PTX identity/opaque输入约束LLVM，显式pending machine audit。module/native boundary version1，公共hook拒绝旧native，cache加入boundary=1。物理record/storage ABI不改。
- NV native-bc460c8 controller39521/start9151991，buildworker39525/PGID39525/start9152015，实际36步tablegen/变更C++TU/link和wheel构建完成，terminal build_passed_not_device_qualified；wheel390887634bytes/SHA7345f7bcbeeb170349f9d2eb1706bb14850b5a761b8c28ae4927058d7efbb1d3。新source archiveSHA6eb8935db842959c9906422170b34b285c80f8d9e59caf72a20a61014a24cc0b；从remote d159源码逐byte桥接59files（包括近轮文档/evidence/测试），旧archive和安装不动；parent launcher仍v2。
- 新native合同测试nvidia_boundary_binding_smoke.py准备检查真实ordinary TTGIR的依赖链、旧interval保持，以及未知/错类型boundary版本的plan和lower拒绝；接着普通公开API/CLI真实math/原始数据和最终SASS对照。当前尚无本轮设备结果。所有import/CPU测试/构建/设备都在server Docker，root只编辑Git和bytes审计。一次本地打包错误引用旧test路径（实际在tests/nvidia）已修，不涉及产品执行/数据修改。

**T016 中间实证与通用修订**：

- install-v1 controller39810/start9167962、worker39811/start9167965，terminal rc1/19.797s；原canonical15/owner16/storage7 normal-O、public2 normal-O、旧automatic_hook3通过；新native正向34anchor/17dependentRead和legacy路径已过，随后unknown boundary version99的plan未拒绝被新负例实际检出。失败原件保留，未上设备。
- 4280babfddee14518e0ec4167643d399f991121c在plan和lower均拒绝未知/错类型boundary，并新增旧compiler ABI hook早拒绝/恢复测试；native-4280bab controller40042/start9175786，2个C++TU变更实构/链接，wheel390894438/SHAf6bf1bab93004cb747f4de3af22b9d04c59085812477bbc1f62ca651e88752be。新install-v2 rc0/20.049s；canonical15/owner16/storage7、public3正常-O和legacy_hook3，boundary native正负normal-O（34anchor/17dependentRead/4拒绝/legacy unchanged）通过。
- type-math-v1 controller40452/start9192350、worker40453/start9192353，rc0/4.723s；FP16/BF16/FP32/FP64/int64共5次普通kernel，各3program含tail，精确CPU数值/input/tail/State[1,1,1]、首末program[0,2]及实际LLVM begin/end依赖通过。device-public-v1 controller40559/start9195131、worker40560/start9195133，rc0/17.193s，真实public API/CLI/cold-warm/两stream/导出失败同raw恢复/zero-grid/溢出/旧count通过。21timestamp capture原量未变，新types5capture；独立std字节audit核26capture/11456raw/5720pairs+16orphan/400logical groups/12352overwritten，仍全为clock/boundary unverified。
- ssa-object-inspection-v1 controller41003，rc0/8.228s；7个新cubin真实nvdisasm JSON/源码PTX行/CFG成功。GEMM920静态指令/44timer，recurrence392/16timer，5types各344/16timer。recurrence loop PC0x720→FFMA0x800→timer0x830→branch0x8f0；这不是全site机器证明。第一批原件ssa-boundaries-original-evidence.tgz5476914bytes/SHA4e15ebc92e284efe8bc3f62d9b5bb8dcde19470f5eaa9aa0f9827bfb9673fff9，含最初ABI失败；不要覆写。
- 检查实际LLVM后确认尚缺内存clobber（SSA仅值依赖不能单独约束无结果store）。通用修订a9ea010在timeline Boundary v1 getter添加LLVM ~{memory}，不新增GPU完成barrier，仍不认证PTXAS/hardware end；5type真实测试增加逐getterLLVM clobber断言。native-a9ea010 controller41067/start9247020，实际目标TU编译链接完成；wheel390909021bytes/SHA3b2e045f0994abcd60f2cccc1dc64f3b9177b621ee5d2408b3c1471d192d9c1a。新install-v3已发起，必须先查terminal再进行同版new device v2与最终SASS，不复用v1为此代码的设备通过。
- stable component source现在a9ea010；parent仍launcher ABI2，旧r007/r008/r009v1/v2安装与源码archive保留。完整clock/期望纳秒模型、最终per-site边界/异步参与者和真实buffer复用、GCU/Asc新timeline、完整P01/独立资格/Perfetto/最终三代码审阅仍未完成，goal active。

**T016 最终同版验证与恢复定位**：

- 最终native/component freeze `a9ea01042557788e9423673fe0161d454407c681`；新实构wheel390909021bytes/SHA3b2e045f0994abcd60f2cccc1dc64f3b9177b621ee5d2408b3c1471d192d9c1a。install-v3 rc0/20.047s；路径 `/workspace/chijin-timeline-r009/runs/install-v3/output/venv`。全部606 wheel成员实际byte核（精确数见independent-install.json），CPUcanonical15+owner16+storage7 normal-O、public3 normal-O、legacy_hook3、native34anchor/17dependentRead/4版本负例normal-O及CLIhelp均通过。source-work是a9ea010内容，旧r007/r008/r009前版安装/源码archives不动；parent launcher继续ABI2。
- type-math-v2 rc0/4.622s；源 `/workspace/chijin-timeline-r009/type-input-v2/p01_nvidia_boundary_math.py`，公开API5种dtype各1次/3program，精确CPU math/input/tail/state[1,1,1]、首末0/2、actual LLVM SSA及逐getter ~{memory}通过；不是独立六数学资格。device-public-v2 rc0/17.543s，真实APIcold/warm加载handle、runtime循环/GEMM、两stream、zero-grid、注入导出失败同raw恢复、恢复后正常、overflow、CLI及单独旧count全部通过。仍无clock或final-machine认证，状态partial_clock_unverified。
- ssa-object-inspection-v2 rc0/8.129s；7对象实际nvdisasm13.2.86三种输出均成功，无no-dataflow fallback。recurrence392静态指令/16timer，GEMM920/44，5dtype各344/16；全7无MEMBAR。这些不是动态次数/物理group闭合，也不能推断全部未选program没有timerread。实际source/GT周围SASS位置见最终original archive，不用v1硬编码PC。
- 最终root bytes archive `artifacts/timeline/run-009/preflight/ssa-boundaries-final-original-evidence.tgz` 10906722bytes/SHA131a217673aff295a41698585434b57cb9f2227cce746cb58b39e3ecd41417e5。前两个archive保留；中间v2导出脚本字符串替换未覆盖新目录，导致audit缺native-a9 entry，已用新完整export修正，不改原件或重跑产品。`audit-ssa-boundaries-final.py`仅stdlib留存bytes审计：完整26cap/11456records/5720intervals/16orphans/400逻辑组/12352覆盖损失、Namespace/source/compiled/bundle/原生物理ring、warm handle、实际LLVM clobber与7cubin/工具输出SHA/全CFG绑定通过。公共小证据 `integration/evidence/timeline-ssa-r009/`，INDEX22成员（含本段快照），约93KiB。
- 十二owned jobs（3 native构建、3安装、2types、2public、2SASS）全部terminal；实际PID/startticks/groups核workers missing/controllers Z，无live owned worker group。最终GPU15MiB/util0/no compute-apps，无自有live设备作业，不杀PID1/他人任务。没有GCU/Asc新实验、本轮无论文/旧Study改动。
- 下一实作不再重复同版矩阵/构建：补可用于细粒度换算的实际clock比例/量化/误差及有效窗口（r008仅10us/2%一致性不是端点误差证书）；使最终PTX/SASS中的site/phase/受观测执行区间可定位并审计，必要时补通用标记/晚期manifest；再做公共ns视图和标准Perfetto。LLVM依赖和~memory不等于PTXAS或硬件完成；raw source fallback provenance在无snapshot时仍需更准确措辞（T013已记），在clock/source认证前修。仍要完成真实physical buffer/flag两轮复用、GCU/Asc新timeline、完整P01/独立六数学/受控case/TP+UI及最终三个额外Sol6.1 xhigh代码走查，完整goal active、不complete、不blocked。

**T016 Git交付**：阶段提交 bc460c8 / 4280bab / a9ea010 与测试/文档/证据提交878514a已推送 `ChijinZ/FlagPrism:detailed-profiler`，fetch祖先检查及ls-remote精确HEAD、正式worktree clean已核。最终native/安装保持a9ea010/独立install-v3；后续878514a仅文档/证据，无native改动，不需重编。T016不可变快照及22成员INDEX已纳Git，根live record保持Git外。完整三后端时间线目标仍active且未完成，下一步继续真实clock/最终机器manifest与公共ns/Perfetto，不重复已通过的同版矩阵。

## D005 设计与验收补充评审（文档任务，已完成）

- 用户要求更新设计/验收文档，并由三名独立 subagent 检查合理性及实际可行性；本次不启动设备实验或改变产品代码/论文。
- 起始产品 HEAD `f5731a0`，新增设计 §8.10 的五个兼容轴、按结论/范围授予资格、保留原件补证的派生视图；测试 §8.5 增加对应兼容、资格隔离、补证重导判定。没有降低三后端完整 P01/最终验收要求，不新增第四设备。
- 三席 fresh-context 独立评审为 `/root/design5_compiler`、`/root/design5_runtime`、`/root/design5_portability`；使用会话默认模型/深度，未指定或宣称为最终 GPT-6.1-Sol/xhigh 代码验收。输入 SHA 与实际配置请求保留在 `integration/plans/timeline/reviews/round5/INPUT.json`。不读彼此或历史评审报告，仅可写各自报告。
- 后续：保首次意见，root 逐条核实修订，必要席位有限复核；完成后更新公开评审索引和文档 SHA。此审查不替代设备时钟/最终机器边界/异步复用/Perfetto/最终三代码走查。

**D005 处置与复核结果：** R1/R2/R3 均有条件认可，初审无确认 blocker/major，R2 一个 minor 指出初始化写者与“未提交可回收”歧义；已修设计 §8.7/测试 §8.3 并明确 E05 三条早期失败路径。采纳资格依赖小表与复用/失效重核清单。三席最终有限复核均核五文档 SHA，无新增问题；原始报告、精确初审重建 patch、最终输入和处置见 `integration/plans/timeline/reviews/round5/README.md`。五文档冻结未变化、合同快照同字节、本地链接/摘要和 diffcheck 完成。仅设计文档通过评审，不授予设备/实现/P01/Perfetto资格。文档与评审已提交本地 `detailed-profiler`：`50b41166df572c7709aee5f49b9845f62101c151`，canonical 工作树 clean；本次未推送。122 个本地链接无断链，53 个索引文件摘要已更新。

## T017 自动计时位点与最终机器 PC 映射（继续实现）

- 当前正式 HEAD `50b4116`，上一 goal turn 完成设计/验收及三独立文档复核，分类 progress；没有用设计通过替代设备门。
- 已实现 native marker ABI1（34fe5e2）：自动 site/entry-exit marker→PTX→实际 CUDA ELF debug PTX 行→真实 nvdisasm text/JSON PC；新公共可选 postprocess，仍保持 clock/boundary unverified，不称源区域最终边界认证。
- 首次 install-v1 实际 rc1：15 个 machine 合同中操作数矛盾未拒绝被检出，保留失败；f5731a0 修复 text/JSON getter 操作数一致性，未改 native。
- 已独立重核 package-parser 终态成功：controller42336/start9495560 目前 Z，前 install controllers/worker 已终止；source f5731a0，wheel390950953/SHA b27b0affd6663f53aede962a14ecae36eeddf29e36ad47205e0b04546be89bb1。7 native byte equality 在 native-byte-bridge.json，下一步新 install-v2 后真实 types/public，不复用旧失败安装冒充通过。
- 本轮仍须最终 clock/region/物理generation、三后端 P01、真实 Perfetto SQL/UI/独立资格及最终三额外代码走查；完整 goal active。

**T017 首次真实设备检出与通用修复：**

- install-v2 controller42468/start9547167、worker42469/start9547170，实际terminal rc0；独立607 wheel成员字节核验、machine15 normal/-O、canonical16/owner16/storage7 normal/-O、public4 normal/-O、legacyhook3、native34anchors17dependentRead/10版本拒绝normal/-O和CLIhelp通过。工具13.2.86离线安装在新产品同prefix，没有全局SDK修改。
- type-math-v1 controller42730/start9558601、worker42731/start9558604，真实5dtype math已运行并留raw，terminal rc1/8.729s：全部实际PTX/debug比较拒绝。独立读取原件定位：native marker为 `entry ;`（空格），PTXAS将 .loc/.file 及 DWARF .b8/.b32 数据行清空而保留行号。没有因失败重跑原件，初始5份capture/工具输出和数学结果保留。
- 通用修复5d042b0：marker允许合法分号间空白；仅允许确切非执行元数据被清空，保所有执行token/行数/位置强匹配，DWARF数据仅在明确debug section内允许；未知变换继续拒绝。新增正负例使machine合同17项。不是最近PC猜测、不是完整区域顺序/clock认证。
- package-debug-lines controller42872/start9574957已实际构建阶段rc0，正核7 native字节桥并写终态；尚未当新安装/设备通过。后续先poll同owner，不改活跃build源码、不盲重启。新source/初失败/status与launch都在 artifacts/timeline/run-010/preflight。

**T017 最终同版设备实证与下一步：**

- 最终source/产品freeze `5d042b05de8dda800392db10086c9f96fd19310c`（native34fe，7 so桥字节一致）；独立产品 `/workspace/chijin-timeline-r010/runs/install-v3/output/venv`，wheelSHA d41bd2c0f2da1625feeb538415d00878359a2f6e43fd360beef9ac957455faf4。新machine17与public4 normal/-O通过，607安装成员逐字节核。原install-v2已通过canonical16/owner16/storage7、native34anchors/17dependentReads/10版本拒绝normal-O和legacyhook3；后一次Python-only修复仅重跑受影响合同及真实设备公开路径，不无变化重编native或重复全矩阵。
- type-math-v2 controller43207，实际terminal rc0，FP16/BF16/FP32/FP64/int64各一次，math/input/tail/state[1,1,1]与320区间通过；全部5二进制exact timer PC映射成功。device-public-v2 controller43330实际terminal rc0，21captures包括APIcold/warm加载handle、runtime循环/GEMM、两stream、同raw导出恢复、恢复后正常、zero-grid、真实overflow、CLI、单独旧count；机器映射未将clock/区域boundary升级。
- 独立stdlib留存字节审计核26capture/11456raw/5720真实pairs+16orphans/400逻辑组/12352覆盖损失；全部26capture关联7实际cubin/140静态getterPC，48次唯一实际tool命令，78是按capture引用的次数，不能当命令执行数。每个PC实际text/JSON/嵌入PTXline/marker/sitephase和artifact/tool SHA一致，7对象均无MEMBAR；仍不证明源算术/访存/原wait最终在边界内。
- 原件archive `artifacts/timeline/run-010/preflight/counter-mapping-original-evidence.tgz`：6125781bytes/SHA7b84ed777b229752ac29a79402199a9fd7fefcf247308fb7e5570ade505b7f86；包含首CPU失败、首5dtype真实失败、三安装与最后设备数据，不含wheel/venv/cache/SDK私有库。audit-counter-map-originals.py仅stdlib/offline引用，不在工作机import产品或跑oracle。
- 九个owned build/install/device jobs全部terminal；实际PID/startticks核workers missing/controllers仅Z，含所有实际工具命令已结束。最终GPU15MiB/util0/no compute-apps，不清PID1/他人任务。公开小证据和可复现字节审计已写 integration/evidence/timeline-counter-map-r010，22个被索引成员约110KiB。
- 下一优先：用精确PC映射核各site实际区域/路径与participant证据，必要时修通用lowering；取得适用于细粒度区间的clock比例/量化/端点误差及有效窗口，形成不改raw的ns视图与标准Perfetto。还须physical buffer/flag两轮真实复用、GCU/Asc完整timeline/P01、独立六数学、受控case、Trace Processor/实际UI与最终三额外GPT-6.1-Sol xhigh代码走查。TP/UI下载代理问题旧请求仍待，没有把此当当前实现全面阻碍。完整goal保持active，未complete/blocked。

**T017 下一阶段定位与Git交付：**

- 保留原件只读定位 `recurrence-source-boundary-candidates.json`（SHA a115be4489c41dd4ae97858fe518be184ad48605a89beff8a7015fc1cf60dcb9）：6个load/store/FFMA源码位置候选在本次对应entry/exit线性PC之间（例如runtime K-load PC1312在1280..1472内，loop FFMA2048在1824..2096内）。这是源码位置候选而不是完整机器路径/participant/完成证明；下一步可用精确PC与原PTX/ISA扩展通用晚期区域证据，不重采同版26capture只为重复核已有PC映射。未据此升级任何canonical boundary状态。
- 最终证据/运行文档提交 `04265ec2ed0fa9f380b0fd8eea49a6d8a26672bf`，34fe/f573/50b/5d及证据已一起推送 detailed-profiler。fetch祖先检查通过，SSH push 878514a→04265ec，ls-remote精确HEAD已核。正式工作树clean；实际产品仍是5d源码/install-v3，不因后续纯文档/证据提交重建。
- 公开字节审计以显式archive/repo/output参数成功复现，22成员INDEX与新文档本地链接通过；一次离线检查从错误cwd引用路径失败，已从正确workspace重做通过，不涉及产品、原件或设备重跑。完整goal仍active。

## T018 目标时钟与跨主体因果校准（继续实现）

- 上一goal turn分类 progress：自动计时site→实际PTX/SASS PC映射实装、两次真实检出与通用修复、26capture/7cubin/140GT PC同版通过并推送04265ec；没有用raw替代纳秒/P01。
- 本轮先核04265ec clean与既有任务实际终态，复用r010/install-v3；不重复同版26capture。继续时钟尺度/误差/epoch和区域证据，不改论文。原PTX文档定义global nanosecond timer但提示target-specific，仍需本机真实getter与校准，不能直接继承其他目标。
- 计划用专门的真实生产消费数学校准，两CTA在不同实际SM上做有界原子发布/应答，保四端tick/SM/真实数学与调用计数，再由因果约束计算可比较范围；这不替代产品的普通异步案例或公开graph支持。未知clock资格仍保持unknown；测量结果决定后续provider合同。

**T018 实测检出、通用代数与安装：**

- 真实preflight确认Pro6000 SM120/188 CUDA SM、每SM max1536threads、容器原安装有效，T017 owned任务终态/worker missing/controllers Z，GPU无compute-apps。
- 首clock-causal-v1 controller43899/start9679887、worker43900/start9679889，rc1/2.418s：ordinary Triton基线拒绝Break AST，未执行数学校准。改为有界while状态机，不改数学/容差/轮数/终止约束，原件保留。
- clock-causal-v2 controller43998/start9688594、worker43999/start9688597，rc0/2.719s：实际3次数学，每次64轮生产消费，state[64,64]→[128,128]→[192,192]，math/input/tail通过；同binaryf934675b，观测CUDA SMID0/1（实际SASS为SR_VIRTUALSMID命名空间，非跨设备硅片ID）。相对offset因果区间[-480,416]/[-480,448]/[-480,416]ticks，0均相容，观测delta GCD32ticks；不是硬上界quantization/纳秒/全188SM epoch认证。
- object-v1实际工具拒绝未知 --cfg 选项，前text/JSON保留；已使用此前真实工具支持的 --output-control-flow-graph/--print-instr-offsets-cfg 在object-v2取得完整真实CFG，无no-dataflow fallback。实际280静态指令，四GT PC0x480/0x6b0/0xb30/0xe10；发布读取参与release原子输入，接收读取处于acquire轮询成功控制路径后，进一步按最终对象/路径核。校准中的原子/CTA同步属于独立探针，不注入用户kernel。
- 产品880706b增加共同 bound_causal_offset：四端点不等式交集、显式误差扩展、精确整数、有界输入、局部逆行/不相容/类型拒绝，不假定链路对称、不拟合频率、不授予clock资格。新9 CPU合同normal/-O与旧27 clock算术normal/-O在新独立安装通过。607安装成员实际字节核，7native库与r010相同，r011/package-causal wheel见实际receipt；未重复未变native及26capture矩阵。
- 新probe增加对公共代数的真实调用、训练/留出两半条件约束，正准备clock-causal-v3，先核新安装终态rc0再启动。完整目标保持active。

**T018 最终同版因果与工具阶段：**

- 最终源码/公共clock freeze880706b2cee327e71100b8fb99222666523d121d，r011/install-v1独立路径 `/workspace/chijin-timeline-r011/runs/install-v1/output/venv`；wheel390952314bytes/SHA70a799263734b2e4fbe79c037366a4c8576f9e9c8d7d83175ff79618671713aa。真实9因果+27既有clock arithmetic CPU normal/-O通过，607 wheel成员核，7native byte桥一致，旧r010安装不动。
- clock-causal-v3 controller44321/start9730327、worker44322/start9730330，rc0/2.719s；3次显式kernel/每次64生产消费轮，实际CPU参考rtol/atol2e-6、input/tail和state64→128→192均通过，调用公共bound_causal_offset与独立四不等式一致，训练/留出32/32均与0offset相容。scope只观测SMID0/1窗口，GCD32不是分辨率/读钟误差的硬上界。
- 同版四getter实际反汇编/JSON/CFG通过，280静态指令与v2 GPU.text逐字节一致；发布时间戳直接作为两处release原子数据输入；实际acquire控制路径和四读对应原PTX行留存，尚不授予完整物理端点误差/全SM epoch资格。
- 新NV原件archive `artifacts/timeline/run-011/preflight/causal-final-with-tools-original-evidence.tgz` 138922bytes/SHA8f209f27953bdd1e202b5aca6b965550f01cb6b1f8c4781eaab7025743a23920；较早math-only归档保留。独立stdlib审计重新核clock模块实际安装bytes、输入/源码/二进制/数学state、offset/留出、不改GPU.text、getter/工具/进程原件，不在工作机跑产品或oracle。
- TP官方固定工具：GCU tp-rest-v1 controller374697/worker374698（1004875005/1004875008），rc0/4.671s；virtual-host GCS `perfetto-luci-artifacts.storage.googleapis.com`取得14008280bytes，SHA55ba613fc6d4f71df81eee2dbfc293020063655c241b3e314bff75345b802684与既有SDK pin完全相同。GCU真实--version通过，转移bytes并在NV tools-input复核SHA及实际--version/--help，controller44454/worker44455，rc0/64.7ms；实际v57.2-da1d152cf/API14。它不是profile SQL/UI通过。
- UI bucket两候选确认为404；官方GitHub REST metadata可达并定位v57.2 asset469355212/15402304bytes/SHA3d4043c4451faaddec8f382b1a0efae4c33ca9b168ec037da32e53c1cc308408。首API payload40s预算到期失败；新流式150s/父180s任务 ui-stream-v1 已实际确认live PID/startticks和7143424bytes进度，原前次错误不覆盖，按同owner继续poll。GCU无现成Chromium/Chrome/Firefox；未来UI实际browser安装仍待，不以工具下载冒充UI验收。
- NV九个owned build/install/calibration/object/tooljobs已逐PID/startticks终态核，工具子进程已reap；最终15MiB/util0/no compute-apps。终态检查脚本曾因TP command row无name字段而失败，已修异构收据字段兼容并重查，不重启任何设备/工具任务。完整goal active，下一步clock provider有效范围/端点误差、最终区域与真实buffer复用/三后端producer及标准Perfetto/独立资格，未complete/blocked。

**T018 UI后续实际状态（原失败与部分包保留）：** ui-stream-v1实际terminal rc1/约150s，7471104bytes前缀保留，不是观察超时；新ui-resume-v1明确检查旧任务终态及实际worker已结束后复制原前缀，只请求剩余Range。server已返回206和精确Content-Range `bytes 7471104-15402303/15402304`；最后实测owner374793/start1004952132、worker374794/start1004952135均live、已10158080bytes。prefix SHA60d295be60ebaaaef0af374ff06d0d5dccb8700735232712f00d88f575561aba。父deadline280s、传输240s，本阶段未启动browser/UI验收。后续按同实际handle poll，不能看到旧running文件就重启。

**T018 Git与UI续传恢复定位：**

- 正式 detailed-profiler 最终提交01840cf20464b95485cdd45fef3c9d1972965f7e（公共clock实装880706b、探针00e0992/92471ea及证据一起交付）已SSH推送，fetch祖先核通过、ls-remote精确同HEAD。canonical工作树clean；产品仍r011/install-v1/freeze880706b，后续只有文档/证据无需重装重测。21成员INDEX/本地链接/公开stdlib审计复现均通过，无论文/旧Study改动。
- ui-resume-v1实际终态rc1（240s传输预算），writer已missing，13434880bytes原前缀保留。新ui-resume-v2明确检查前件终态和worker身份后续传剩余1967424bytes；prefixSHAe177704d57d54a455cf6d25c44573e75d3c9ad441feac6787abc887ecccca340。最后已验证HTTP206 `bytes 13434880-15402303/15402304`，当前14286848bytes，两进程live（controller374818/start1004998165、worker374819/start1004998168；worker PGID374819），父deadline280s，日志/root `/tmp/chijin-timeline-tools-r011/ui-resume-v2`，脚本 ui-resume-input-v2/resume-ui-stream-v2.py。下一次先poll artifacts/timeline/run-011/preflight/check-ui-resume-v2-command.txt，同handle；未完成时不当安装成功。
- 成功后核完整15402304bytes/SHA3d4043c4451faaddec8f382b1a0efae4c33ca9b168ec037da32e53c1cc308408，再转移/解包到已有Docker，不在工作机执行UI/浏览器。GitHub初API attempt私有原件含带query的临时release URL，公开摘要去query，不原样dump/提交；本轮新流式/resume仅保final_url_without_query。GCU目前无browser，UI资源下载不等于实际UI验收。
- Goal保持完整active；TP二进制障碍已解决，仍需clock provider的有效证明/端点误差/区域和physical buffer代际、其余两后端producer/P01、实际ns/Perfetto SQL/UI/独立资格与最终三额外指定模型代码走查。

## T019 实际设备调用边界原语与UI资源安装（继续实现）

- 上一goal turn分类progress：880706b共同因果区间实装、真实生产消费/留出校准和机器对象、独立CPU9+27测试通过；固定TP已真实可运行并推送01840cf。不把这些当完整clock/区域/P01或UI通过。
- 本轮重核01840cf canonical clean；GCU ui-resume-v2已实际terminal rc0，15402304bytes/SHA3d4043c4451faaddec8f382b1a0efae4c33ca9b168ec037da32e53c1cc308408与官方pin一致，controller374818/worker374819均missing。UI下载障碍已解决，下一步只转移bytes到已有Docker解包，不在工作机执行UI。浏览器/真trace UI验收仍待。
- 新研究实现方向：专门真实数学原语验证 noinline 设备调用是否能保留实际计时边界，先看最终CALL/原计算/读钟顺序，不直接改自动collector或假定LLVM依赖已足够。FP32/int64、3 program/两组runtime K、同binary输入变化、CPU oracle/input/tail/state/原ticks均有检查。手工timer仅用于此原语，不替代普通kernel自动时间线。源码freeze b431f63，使用当前r011/install-v1新产品/既有7native，不为测试文件重编产品。完整三后端goal保持active。

### 用户请求的文档更新与第六轮设计评审（2026-10-17）

- 只做本轮设计/验收文档与独立只读评审；未修改产品代码、论文或旧 Study，未启动或改写任何远端实验作业。本条不更新 T019 构建/安装终态，不把既有运行作业判作完成。
- 设计新增 §8.11，测试新增 §8.6：明确部件输入输出与独立替换、不同后端合法边界、实际多函数对象、因果 offset 证据局限、端点不可分辨与最小样本推进。复用 P/E，不增加独立数学数量或降低既有合同。
- 三个 fresh-context subagent：design6_compiler / design6_runtime / design6_portability 独立完整读同五文档，不读旧/peer 报告。初审均无 confirmed blocker/major；R1/R3 共同指出一个章节索引 minor，已同步根合同与 tracked 快照并由三席有限复核通过。配置为会话默认，不冒充最终额外 GPT-6.1-Sol/xhigh 代码验收。
- 报告和处置：FlagPrism-method/integration/plans/timeline/reviews/round6/README.md；保 INPUT/初审patch/FOLLOWUP_INPUT/六份报告。静态链接、SHA、合同同字节及 git diff whitespace 检查；未运行产品测试。三个后端边界/clock/发布/实际复用/P01/SQL/UI/独立数学与最终代码审阅仍按原目标待完成。

### T019 恢复后的实际构建核验与映射修复

- 上一轮为 progress：文档设计 §8.11/测试§8.6 与三个独立设计报告已提交6491679；本轮继续原完整goal，不用设计通过填设备门。
- 重新远程核 native-outlined 权威 terminal：source4f5b2bff76ec61537bcec6d98075639d7f9ef731、build rc0/94.774s，wheel391069304bytes/SHA8d94918a0a14572a807c7354ecbcf135eacc87683eea48c1928d6514c766b185。controller44904/start9998876仅Z，worker44908/start9998901及三个parent检查worker均missing；没有重复native启动。
- UI资产安装 ui-install-v1 terminal0/0.365s，owner44628/start9916216、worker44629/start9916219；这只是固定版本资源解包，不是 browser/UI 验收。
- mapper61ea330修正实际helper位于父.text且start非零的结构：显式符号与函数实际body定位，验证 ELF 可执行段范围/不同函数body不重叠，保section/function_start/relative_pc；不按最近PC或前缀猜归属，仍不授予区域/clock资格。新三方法补正负合同，总CPU方法20，尚待Docker实际运行。
- source61ea33060f84c0e513107f95ff6992e270f5662d，18个Python/文档变化与4f5桥接，无C++变化。package-multifunction owner45101/start10067017、worker45105/start10067043，预算3600s；使用原build/cache，只打Python增量并核7native必须与新4f5 native wheel相同。最后controller running，下一次先poll权威terminal与实际/proc，不重启。原件/root命令在artifacts/timeline/run-012/preflight。
- 下一步新独立install-v1 + machine/public/native boundary2 normal/-O/旧hook CPU回归，再公开API五dtype/原自动结构真实设备回归；任何失败保原件再通用修复。clock尺度/端点/跨主体资格、物理复用、其余后端producer/ns/Perfetto/独立数学和最终指定代码走查均未完成。

### T019 最终公开自动路径、机器对象与留存审计

- 新native4f5b2bf真实构建及61ea330 Python增量打包成功；新wheel SHA b7c3aaf220dd4e97f2caa867bf5dca110b4e27fd3d3e4bf0843429c519b1f22b，独立安装r012/runs/install-v1/output/venv，607成员逐字节核、7native与4f5构建原wheel一致。正常/-O各20 mapper、4public、12native负动作及34anchors/17reads正路径通过；3legacy-hook通过，原有ABI1插件不能作为新模式使用。
- install-v1 owner45239/start10073790、worker45240/start10073793；boundary-math-v1 owner45479/start10078071、worker45480/start10078074；public-outlined-v1 owner45600/start10081870、worker45601/start10081873；outlined-objects-v1 owner46098/start10096110、worker46099/start10096113，均真实terminal0且worker missing。七个build/install/math/tool/UI资源job最终PID/startticks重核，无owned active写者；controller Z留PID1。最终GPU15MiB/util0/no compute-apps（见实际target原件）。
- 真实五dtype公开API保持精确math/input/tail/state1，320intervals；新native下公开API/CLI/原runtime循环/async GEMM/两stream/零grid/溢出/no-replay导出恢复/旧count全回归通过。独立原始字节审计重建26capture、11456物理记录、5720pairs、16orphans、400logical groups、12352overwritten，source/compiled/raw/identity/offset/marker逐项对照。
- 7真实cubin/140静态GT均经显式非零helper函数定位；额外CPU工具job取得所有实际CFG、直接CALL符号与helperPC，实际text/JSON call target相互核，未见MEMBAR。记录是static evidence，不授予region/clock/physical generation认证。
- 首只读机器输入检查因调度代码换行转义SyntaxError失败，原件machine-input.txt保留；第二版只修打印换行并成功，无设备重放。其余本轮新producer回归无已知math/compiler故障。
- 原件archive artifacts/timeline/run-012/preflight/outlined-final-original-evidence.tgz，6241355bytes/SHA079f43e6f8169a9eebc627a9e16c5ce198beafd100aa336f76485e056c37c7b8、860members。Git小证据与可重现stdlib审计在integration/evidence/timeline-outlined-r012；工作机只审留存bytes，没有import产品/oracle。自动region/clock仍unverified，无pftrace/P01/其它后端新producer/独立资格，完整goal保持active。
- 先前noinline call primitive最终v3原件63483bytes/SHA9035e0249d28d893eb7127b1ec108f9f5b16128377348dd90fc239f4979ce7a1，8实际数学调用/168内区间，forwarded/read-only FP32/int64及runtimeK均通过，机器保call/FMA顺序；不是自动或clock证明。此原语曾有v2编译期字符串错误，原失败仍在旧archive，不改旧结果。

### T019 新增普通编译对照：发现流水调度扰动，未通过的门保持失败

- 已提交/推送d72caf2的自动raw/机器对象checkpoint后，为核同步是否被插桩改变，新增p01_nvidia_unprofiled_objects.py；在同r012实际Docker/独立安装对相同source/config作普通.warmup纯编译。state0/output canary不变，actual_math_launches0，无应用重放。
- unprofiled-objects-v1 owner46140/start10137276、worker46141/start10137279；实际terminal1/4.972s，worker missing/controllerZ。失败是测试最后的静态同步数严格相等门，不是编译或math失败；原stderr/result和普通IR/ISA/CFG全保。recurrence barrier均空；ordinary GEMM commits10/BAR9/DEPBAR4，对照profile static6/5/2。
- 留存bytes继续检查：ordinary数学全展开12HMMA，profile retained loop4HMMA；actual初始化R10=0x40、每轮+0x20、比较0xa0、回边0x2d10→0x1430给3轮候选。按候选展开后opcode数量相同，但copy/wait/dot交错仍不同。因此不能把差异只解释成静态展开，也不能宣布原始流水保持或直接删失败门。后续需核mechanism/control-path、稀疏/较密观测与关键依赖/顺序变化，评估实现/呈现边界。不是环境阻碍，goal保持active。
- 新archive artifacts/timeline/run-012/preflight/unprofiled-objects-original-evidence.tgz SHA见独立unprofiled-artifact-index.json。primary860member成功raw/object原件不变；新增失败作为另外受控对照保留，不覆写任何通过/失败收据。

**T019 Git交付与当前恢复定位：** detailed-profiler HEAD61f6b21b489a648ec1811f34a3818c83cfad294d已SSH push，fetch祖先核及ls-remote精确同值，canonical clean。原始byte audit再复现26capture/7cubin，28个小证据文件SHA/bytes、本地链接与根/tracked合同同字节通过。后续产品仍r012/install-v1/source61ea330/native4f5b2bf；新61f6只加测试/文档/证据，不因这些变化重复native构建或26capture。最新无在途owned GPU/build任务；unprofiled对照是终态failed investigation，不是环境阻塞。完整goal active，所有缺口按前文保留。

## T020 机器调用来源与同步清单的产品化

- 上轮为progress：新boundary2实装/26capture/7对象通过，普通GEMM纯编译对照发现展开与交错变化并完整保留failed门；没有把它算成P01或原始流水保持通过。canonical起点61f6b21 clean，安装仍r012/source61ea330/native4f5b2bf，未启动重复native或26capture。
- 本轮源码71976f4扩展实际mapper输出：static_model_version1、所有精确direct CALL/未解析call状态、counter→完整调用点集合、同步指令PC/predicate/operands；text/JSON调用目标与wait/barrier操作数不一致拒绝。inline getter允许无caller，多个getter/调用者不折叠，不推动态次数、region/clock资格。新4个有意义CPU正负方法（总24）待Docker验证。
- 3b237e8新增实际七cubin原件重新解释driver，零应用重放/零GPU math，使用新已安装mapper核旧真实输入、同counterPC/140getter、直接调用点与sync清单。不是CPU fixture替代设备，原输入由T019实际设备取得。
- r013/package-call-model owner46248/start10192258、worker46252/start10192284最后实际/proc为S，patch检查workers均missing；source3b237e8fb054d4d7b24cef0c2b9c06169fbc0e6f，36个Python/测试/文档/evidence变化与远端source61ea33桥接，无C++变化。增量打包后必须7native逐字节不变。3600s已知builder预算，不能因观察超时重启。rootartifact artifacts/timeline/run-013/preflight。
- 下一步同owner终态核→独立安装与normal/-O24mapper、4public、七实际对象重解码；补五dtype公开真实hook烟测，避免重复不受影响的26capture全矩阵。之后核稀疏/较密观测与实际机制/关键依赖，不删T019失败、不把静态清单当动态或时间证明。三后端/ns/Perfetto/独立数学/最终指定代码审阅仍完整保留。

### T020 最终实际安装、复核与GCU数据

- V1 source3b237e8安装607成员、7native桥相同，normal/-O各24mapper/4public及7个r012真实cubin重新解释通过（0新增GPU数学、140getter/call、13同步位置）。公开5dtype实际smoke owner46560/start10211641、worker46561/start10211644，terminal0/worker missing：5原数学/5capture、320interval/80staticref通过。没有重复26capture未变矩阵。
- Final39e95f4加调用者索引及65536展开引用预算、防潜在非线性扩展；新增一负例。新package-v2 owner46700/start10306089、worker46704/start10306116成功；新install-v2 owner46838/start10318622、worker46839/start10318625，terminal0/worker missing。最终normal/-O各25mapper、4public、7实际对象重新解释通过；607成员与新wheelSHA9a43ee79a78184ac395e57670ea5499b5771276ceba29f0193e5fe1434a996f4一致；7native byte桥均未变，当前正式解释器r013/install-v2。未为预算处理重跑GPU数学。
- GCU flagprism-enflame-dev实际新unannotated recurrence advanced自动采集：1ordinary+3显式profile calls，K3/7/11同binary95a3bba3；10/14/18事件共42、8source sites，所选loop body site实际3/7/11次。原math/input/tail/state1通过；owner374860/start1005368312、worker374861/start1005368315，terminal0，实际/proc均missing。不是新默认timeline路径或P01完成。
- GCU完整32B header/64B pair物理发布原件：每buffer32800bytes、program0/work-item0、46bit ticks、序列/ordinal/commit及decoded区间逐字节复核，无overflow/sample omission。三个当前样本均叶子区间、端点递增；不把“格式存完整pair”推成已观察到嵌套逆序，也不先据此扩schema。现有ir-capture-0/launch-1标签是每次export局部，公共新adapter必须另有session/owner命名空间；不能直接当全局ID。原installed GCU Python/native pins单独存，不冒充newnative。
- 新NV V1原件841142B/SHA56ea7ef9a4d1c13d7064d2b9f8c2fe0e8a34c6ad36c1f0d39e45decd5b713f28。V2首取证误取install-v1模块，被字节审计拒绝；原失败archive/sha不覆盖，仅修collect路径重新取新archive，没有重放数学/测试。Final V2原件85067B/SHA39d07b9133758a23395cbfc70d563f4775bff2018727b0b6f9a07acf113d5fc2。GCU原件2321230B/SHAea3fbe96cf5d8c985dd39c2d54a1d2ddaa59c229ad14c3fe85965bac97afb62b。
- 新stdlib审计同时读r012真实SASS与本轮新模型，独立核140个CALL符号/PC/操作数、13个同步位置，与GCU全部42物理payload。Git源freeze39/3b读取而非假定current测试源码不变。原件/index/receipts/审计在integration/evidence/timeline-call-model-r013，未在工作机import产品或跑math。
- 当前编译源读取证确认NV make_llir在我们的llvmir_to_llvm插桩之后才调用llvm.optimize_module(O3)，可考虑更晚的观察点以降低已有GEMM展开/交错扰动；尚未实现晚期logger，不宣称LLVMModule module-local pybind跨plugin/新增scratch ABI已可用，须实际验证。不要只用新static metadata宣称T019同步/原始流水门已通过。
- 全部NV五个owned jobs terminal，workers gone/controllers仅Z；最后GPU15MiB/util0/no compute-apps。GCU新作业terminal且两owned进程missing。无新Ascend实验，无paper/Study修改。目标完整active；当前无环境阻碍，后续直接继续产品工程，不以这些阶段报告改完成定义。

**T020 Git收尾：** detailed-profiler c4de261已SSH推送并核ls-remote精确HEAD，fetch祖先检查通过、canonical clean。22个小证据文件index/本地链接/根与tracked合同同字节通过，跨四原件stdlib audit复现成功。最新正式NV安装r013/install-v2/source39e95f4；c4de仅文档/证据无需重装native或重跑数学。无pending设备/build/test作业；所有真实时钟/区域/物理复用、三后端公共接入及P01、标准Perfetto、独立数学和最终三个额外指定代码review仍须完成，goal保持active。

## T021 公共raw v2与GCU已发布append协议适配

- 上turn为progress：c4de261发布调用来源/同步清单、25正常/-O合同与GCU同binary三runtime-K样本；原始clock/区域/P01门仍未过。以当前Git/所有任务终态为准继续，没有新环境阻碍或用户权限问题。
- 新公共reader保留v1完整行为，新增v2明确endpoint_stream/paired_endpoints顺序，以及attempted/committed/retained/dropped/filtered/overwritten计数。数量单位为canonical端点引用：GCU每条原子64B pair有两个真实8B时间字段；不能把丢新记录填成覆盖旧记录。nested pair可start早于先追加的inner pair，仍保物理pair完成顺序、拒clock逆行/跨pair配对；不按tick排序造日志顺序。
- 新timeline_events_enflame读取真实原始SHA/32Bheader/64Bpayload、协议2+selected_dynamic_timeline_v1、46bittimer、launch/compiler身份、源/record plan、seq/ordinal/commit；site/scope/actor/采样/容量错类型或矛盾拒绝。旧export局部labels通过caller提供的owning capture namespace隔离，原association保留。只生成observer_elapsed和导航，不授予源成本/clock/engine/iteration资格。
- 初步ace22fd为实现快照及预打包；随后a0ef3c9补compiler scope类型bool拒绝，并补严格endpoint_stream合同；tests-only7fceb5e补全部26实际旧v1读取driver。native源码未改，两次Python增量均核7native字节相同，未重复native重构建。
- 正式product freeze a0ef3c904e076e0f4f1743d16fa4399ea4829288，r014/package-gcu-events-v2 wheelSHA7deb63383bfe57de40103f17b0e3f1911bbe11b891e8bd6e23c9186914c653f0；独立install-v1核608成员；normal/-O各11新GCU/顺序/丢失合同、16旧events合同、25mapper、4public接口合同通过。新public入口/GCU native producer/Perfetto未因此被宣告通过。
- 新安装以实际GCU原件（三个advanced API真实调用）规范化42interval/84raw字段引用；每个引用offset/8B tick逐字节验证，三个capture IDs互不混。新reader重新验证原NVIDIA26capture/11456records/5720pairs/16orphans，原document无改写，normal/-O均一致。全部是CPU重新消费留存真实数据，新增GPU数学0；不把它称为独立新数学资格。
- 初步package owner47031/start10409795、worker47035（见原terminal）；最终package与install等三job均已PID/startticks终态核，workers missing/controllers Z；install owner47295/start10449066、worker47296/start10449069，rc0/21.050s。无新GCU/Ascend设备作业，NVIDIA最终15MiB/util0/no compute-apps，未改论文/旧Study。
- 新原件artifacts/timeline/run-014/preflight/gcu-common-original-evidence.tgz：91559B/SHA8ffba38da8ba13dce98e03d5c44dde7a6911d310756b549620f422e38d5f7a6a。Git小证据/实际安装模块字节/608安装receipt/归一化结果与可复现stdlib审计在integration/evidence/timeline-gcu-common-r014。审计结合r013 GCU原始物理payload，复核全部84端点、native到canonical identity、计数单位及未授予时间资格；工作机不import产品或执行math oracle。
- 新adapter仍是纯函数，调用者负责保存原件/拥有device资源。没有改GCU默认detail=timeline的拒绝、首末program双slot或GCU SDK owner/transport；下一步必须把已验证codec用于实际公开采集流程并实证，不停留于离线转换。P01/clock/async/物理复用/标准Perfetto与最终代码审阅的原要求保持active。

## T022 设计/验收更新与三个独立设计评审

- 用户要求：更新时间线设计与验收文档，三个独立 subagent 审核合理性、实际可行性及后续芯片复用边界；本轮只做文档，不启动设备工作、不改论文。
- 新设计§8.12和测试§8.7定义独立compiler/transport/decoder/clock/mapper组合、最低交接产物、不同物理顺序/计数单位、默认入口与离线reader的区别、真实设备可证伪的最小样本。执行合同§3.1同步章节引用，根/跟踪快照保持同字节，完整验收门槛不变。
- 三位fresh-context设计reviewer请求gpt-6.1-sol/xhigh，不读peer报告；初审均认为合理、无架构阻断，但完整三后端可行性未证明。合并意见后修订六项：decoder/provider职责、固定配置扰动对照、合法回绕版本策略、owner/派生生命周期解耦、安全恢复前提、nested pair到Perfetto的合法投影与实际TP验收。
- 原三席有限复核均确认各自问题文档层关闭，无新明显矛盾。输入SHA/初审/复核及逐项处置在integration/plans/timeline/reviews/round7；不是最终三个额外代码验收reviewer，不授予P01/ns/Perfetto/UI资格。
- 只做文档链接、diffcheck、合同同字节和索引SHA检查；未import产品、build/test/oracle、SSH/GPU/TP/UI。T021未提交events/runtime和r014证据保持原状。下一步工程及真实设备缺口仍沿T021，原active目标不改状态。

- T022文档已本地提交 detailed-profiler 3037f03c220d97023eca2fe472d9b3421f14ddb9；75份索引文件SHA、36个本地链接、根/快照一致、diffcheck及隔离Git index重建初审两文档SHA均通过。本轮未推送，原T021的未提交工程文档/证据保留。

## T023 两阶段收尾、跨调用原件保全与实际解码失败恢复

- 上turn分类progress：3037f03更新设计/测试合同，三独立Sol6.1/xhigh设计评审与有限复核闭环。当前以工作树/服务器实际终态继续，不重新创建或降级active目标。
- r014旧三任务真实PID/startticks再次核terminal、worker missing/controller Z；PRO6000 15MiB/0%/无computeapps。T021文档/原件索引已提交70fd0ed；原件字节保持，final-target-state.txt原始尾空行保留。
- 本轮实现d092f6272d43e7f1bd2196005a954187384a8993：hook先独立读取/保全所有owner原件与源码对象，安全持久化后release，再对原件做decode/export；前一个调用失败不阻断其余原件，设备与派生pending分开。追加不可变attempt记录与可原子替换index，重试沿原目录、不重放应用；readback重试遵守共同剩余时限。
- CPU故障合同6个：首decoder失败全owner先释放/其它照常解码、原件只读重试、read失败仍保owner且其它调用继续、release失败保owner与pending、raw篡改检测、目录与原件持久化合同。16旧owner+4public合同normal/-O通过。
- 新独立package-finalize-v1成功，wheelSHA8cbdabc8f63282966cf047dfaea4fc8a08f3ec73dde8b0b513d585fcbfa566dd，608成员byte核，7native与原4f5b2bf实际build一致未重编native。build owner47498/start10642130，worker47502/start10642157；install owner47636/start10651535、worker47637/start10651538，terminal0。最新安装/workspace/chijin-timeline-r015/runs/install-v1/output/venv。
- 实际公开API故障恢复脚本tests/timeline/p01_nvidia_finalize_recovery.py已提交31f8743及校验字段修正39a601f：普通两stream三recurrence+GEMM、首次decoder失败，验证所有4原件先持久化/释放、其余3可解码、同原件重试无transport动作及新合法session恢复。不授予clock/边界/Perfetto资格。现已启动r015/runs/fault-recovery-v1（180s有界controller）；恢复先poll该handle及PID，不从launch记录推断终态。

### T023 修复、实际验证与收尾

- fault-recovery-v1 controller47803/start10656248、worker47804/start10656251，terminal1/4.322s：测试脚本错用用户bundle路径，修正为公开session真实staging（d06e03b），保第一次失败，不记通过。fault-recovery-v2 controller47971/start10662106、worker47972/start10662110，terminal1/4.322s：真实保存四原件/owner已全释放，但JSON重读的slot由tuple变list被物理解码器拒绝；这是真产品故障，原件/错误不覆盖、不标unsupported。
- f17071ccd6a7514507e583a71b27fe6030752ff9：规范恢复slots tuple，CPU fake decoder同样核tuple对合同，新增journal写入失败不得掩首decoder异常的第7用例。新版package-finalize-v2 owner48145/start10670187，7native仍与原实际build字节一致；wheelSHAa69d9d047c798db2fc768db1ab376bc044313c6a8c50499249464f24b757bb97。新install-v2 owner48289/start10678246、worker48290/start10678249，terminal0/19.697s；608安装成员核；normal/-O各16owner、7finalization、4public合同通过。
- 最终fault-recovery-v3 owner48456/start10681664、worker48457/start10681667，terminal0/9.730s。一次真实公开两stream workload的四数学调用先全raw/关联/编译对象持久化并release，再注入首decoder失败；其余三真实capture正常解码，index/attempt保首错/1pending/0owners。同原件重试后四capture完整，transport新增动作0、raw/input及首错SHA不变。下一正常公开session四调用通过；成功8capture共2688端点/1344区间，原数学/input/tail/合法副作用均通过。初始两失败还各执行四调用，不能当作没有发生；原失败数据一并保留。
- 原件artifacts/timeline/run-015/preflight/finalize-original-evidence.tgz，1951765B/315files/SHA1d861e0b9bd31e6730ad14d2a5eb9016c28d30bb7e53a4868c518d28118fe4eb。stdlib/Git audit核实际安装两模块、5个实际测试脚本与freeze、608成员/7native桥、normal-O日志、全部2688物理tag/tick/seq/offset/配对和两个math结果、原失败/owner终态。小证据和复现命令在integration/evidence/timeline-finalize-r015；工作机未import产品或运行oracle。
- 七个本轮build/install/device任务均真实terminal，所有owned worker missing、controller仅Z或missing；最终PRO6000 15MiB/0%/no computeapps。没有在途任务，不做无变化重复矩阵，不改论文/旧Study。
- 保持active：新路径仍NVIDIA raw-only partial_clock_unverified，边界/尺度/epoch/物理复用与普通流水扰动未核；GCU默认首末program/owner/transport、Ascend新timeline producer、标准pftrace/TP/UI、独立六数学、最终三个额外Sol6.1/xhigh代码review仍必达。重试目前为保留hook的in-process入口，不冒称独立公开cross-process恢复命令。下一步优先接GCU实际公开采集链，并继续最终机器边界/原流水扰动与真实clock/async证据。

**T023 Git收尾：** detailed-profiler 599e1976cc92c8d44c2a590b9ba3a2271e7573ca 已fetch祖先核、SSH push及ls-remote精确HEAD确认；canonical clean。r014/r015小证据INDEX逐文件SHA、README本地链接和根/tracked合同一致检查通过。所有七owner任务已终态核，无在途设备任务。完整目标仍active，未将本轮收尾功能等同P01/三后端时间线完成。

## T024 GCU 首末program紧凑producer、独立native生命周期与公共解码

- 上turn为progress：599e197推送两阶段owner收尾与真实8capture故障恢复，原完整三后端目标保持active。本轮从真实GCU旧advanced路径缺口推进公开timeline前置：旧只能固定一个program且每launch同步，不能直接重命名为默认timeline。
- Docker flagprism-enflame-dev实际核r013 controller/worker均missing、terminal0；Torch/GCU真实提供ExternalStream/Event/query上下文，使用SDK completion而非全局逐launch同步具有工程落点。首次环境读取因容器无efsmi命令失败，改为保留可得API/构建信息，不声称设备空闲或环境硬阻碍。
- dfaf97290d55d8f0277e8c98577221c40fb7208f：新增gcu_first_last_timeline_v2，actual runtime grid首末独立ring（grid1单ring），编译写址/采样选择与实际program绑定；native header reserved1保实际program、stride/capacity有界，非全grid分配。新增allocate_timeline_launch/initialize/read_raw使未提交device写入的分配先交owner；finish旧行为保留。请求runtime_first_last/编译缓存revision4及native版本2，旧fixed advanced布局仍兼容。两项C++ host存储/拒绝测试新增，未把host fixture称设备验证。
- ca702b2：公共GCU adapter解两个真实布局，不构造假legacy metadata；多ring引用whole raw SHA和精确slot+字段offset，原source/site共享、program/observer/clock域隔离、loss逐slot；legacy canonical不额外加属性。新增7个CPU first-last合同，尚未运行。补runtime/compiler layout和index-bit矛盾必须分配前拒绝的native guard（此native delta未进入首个dfaf build）。
- 正在真实新native构建：/workspace/chijin-timeline-r016/native-v1，source dfaf972不可变；controller375448/start1005928296，1800s总deadline，每owned编译/链接900s上限、_deadline cleanup相同SHA8c70cb...。旧/workspace/chijin-r11-gcu-final-source-build/work仅只读拷贝，不覆写旧安装。144实际TableGen命令成功，逐源/实际依赖SHA重用338对象、27TU待实际编译、6链接；现LIVE compiler groups375746/1005929092、375765/1005930122、375769/1005930237、375773/1005930579（以最新controller.json为准，不重启）。原build核心a09e...不同于当前r15安装f3eadb...，只当旧对象基线，不能当最新安装；复用逐输入hash检查，变化TU真实重编。
- 恢复先poll artifacts/timeline/run-016/preflight/check-native-command.txt。后续须完成首build终态、ca702 guard单TU delta/native合规、实际独立wheel安装/CPU normal-O、真实首末program数学/原件/调用隔离；再接公开默认GCU owner/transport（包括取消legacy同步）、真实clock/async/Perfetto。当前尚不宣称新producer已通过或默认入口已开通。论文/Study未改。

### T024 真实验证推翻的假设与 publisher ABI 修复（未完成，先看最新状态）

- native-v1因Bridge.cpp少stdexcept头失败；v2因AddPtr builder缺显式result type失败；v3因迁移object/depfile目录未创建失败。均实际terminal/owned PID missing，非观察超时，失败日志保留。v4实际成功：7新编译+358对象byte匹配复用+6链接，storage两个CPU/metadata/frontend通过。初独立install-v1轮在全RuntimeTest旧CANN EXPECT_DEATH遇到std异常而失败；e72aa29让driver/meta不匹配在SDK probe/分配前throw invalid_argument，更新负例不再要求abort。
- native-v5成功（source e72aa29），6新编译/359对象复用/6link。独立install-v2 source72db8a1/nativee72aa29，全部native19 Runtime/metadata/frontend及normal-O公共16+legacyGCU11+firstlast8通过；venv=/workspace/chijin-timeline-r016/runs/install-v2/output/venv。此为后续发现publisher地址bug之前的安装，不当作当前可用GCU默认timeline。
- producer-v1首个真实数学后自动导出因development prepare未向_exported_runs发布原件报invocation_has_no_internal_capture；源码72db8a1补真实产品attach_enflame_timeline_export/observer_region_elapsed类型及canonical字段的内部normalization。producer-v2脚本terminal0，但它只检查了由host header构成的observer坐标，没有检查每个observer的实际events，结论弱，已撤销“完整双ring producer通过”的判断。新default-export-v1不用customprepare，真实数学/导出source-presence通过，但实际仅program0有14events；末尾program2 ring write/attempt=0。其标准raw/native文件还丢canonical_timeline，需要补capture-document字段保留；不能靠normalization字段已写就声称出最终bundle了。
- 初步推测SDK builtin维度不可靠没有证实；实际源码核对明确根因：hidden ABI是!tt.ptr<i32>，新增slot stride是bytes，直接AddPtr误放大4倍，可能写出所分配的逻辑范围。旧数据不能证明安全发布，全部保留为失败/未资格，不能引用其prototype terminal0给双ring正例。无需此时另造runtime-grid descriptor来回避自己的地址bug。
- 789757f已通用修复stride/4；新增GCU_TIMELINE_PUBLISHER_VERSION=2（storage/layout仍2，物理布局未变），compiler cache revision5，metadata/runtime/decoder均校publisher version，旧beta metadata不获兼容。每个实际selected writer在function-entry给自己的header发布arrival flag32；decoder对未到达ring明确拒绝，区分合法“到达但0选择事件”。CPU firstlast新增负例、device probe要求每selected observer至少2真实events，不再仅核header坐标。
- 当前准备native-v6 source789757f不可变，复用v5已核same-input objects、实际重编受影响CPP；已启动/workspace/chijin-timeline-r016/native-v6。恢复先poll artifacts/timeline/run-016/preflight/check-native-v6-command.txt，核actual terminal/PID，不能只看旧v4/v5成功。之后须新独立wheel/normal-O9 firstlast+11legacy+16common+native units、重新跑强device producer与无hook标准advanced导出，补canonical字段落盘，并验证所有raw字段/两slot实际events后才checkpoint。公开detail=timeline/deferred GCU owner仍未实现，clock/async/Perfetto/P01/独立数学/最终code reviewers均仍未交付。

## T025 更新适配边界设计、验收及三人独立设计评审

- 用户本轮要求更新设计/验收并开三名独立 reviewer 判断合理性与实际可行性。本轮只编辑文档、本地 Git/stdlib 审计；未连接服务器、启动实验或修改产品代码，未改变前序任务实际状态。完整timeline目标仍未完成，T024 native/安装/设备状态须按其既有controller核实，不能因本轮设计通过推断成功。
- 设计 §8.13 增实际部件接入决策与交接判定，测试 §8.8 对应默认入口、逐observer真实writer、地址/guard、publisher/cache、最终bundle及故障恢复。同步根/tracked goal章节引用到设计8.13/测试8.8，合同门槛不降低。
- 三名 GPT-6.1-Sol/xhigh/fork-none独立初审：timeline_design_review_compiler、timeline_design_review_runtime、timeline_design_review_portability。均认为路线合理可实施、无P0；指出两个P1（guard异常丢已取得raw、首unknown owner耗尽共同deadline使后续ready无salvage机会）及具体P2，全部采纳为文档合同与待执行测试。
- 增补实际pointer lowering范围不变量，不以有限guard或数学canary独证timeline写址安全；公共owner复用状态机而非NVIDIA参数签名；完整异步资源涵盖device/H2D/D2H staging/native/context/completion；区分单调用/live pending/累计raw与bundle预算；§11统一A/B/C/D纵向顺序。原reviewer有限复核，原问题文档闭环；另按复核意见把scratch回收限定为完成确认且raw/关联快照持久化后。
- 报告、意见处理及评审输入/最终文件SHA在integration/evidence/timeline-design-adaptation-r8/。设计评审不替代设备可行性、P01、Perfetto或最终三个额外代码走查；无任何设备门因此标通过。后续恢复仍按现有工程记录/真实controller继续，不新增第四后端、不改论文/旧Study。

## T026 GCU 修复后实测、默认 deferred API/CLI 与公共收尾修复

- 上turn T025 为 progress（设计与验收、三个独立设计审阅闭环）。本轮按原完整目标继续实现，未将设计评审当设备通过；不改论文/旧Study。
- 核 native-v6 实际 terminal success，source789757f3725f72f8be3e348a2e52552d3356c99b，controller379009/start1006194433 已missing；7TU真实重编/358对象依赖byte核复用/6links/native3单元可执行通过。没有重启已终态构建。
- 新 install-v3 source9148572/native789，controller379467/start1006281375、worker379468/start1006281378 terminal0，实际storage/publisher均2。producer-v3 controller379592/start1006289348、worker379593/start1006289352 terminal0/23.704s：同binary runtime K3/7/11与3×2/2×2/1×1，逐observer实记录10/14/18；第四cap4真实丢56端点。default-export-v2 controller380172/start1006294287、worker380173/start1006294290 terminal0/15.136s：无custom prepare的advanced路径最终bundle保28区间/56raw引用及canonical。旧beta“成功”不计正例，旧失败保留。
- 234f39d修公共故障：TimelineReadback区分取得bytes与guard/extent合格，保raw/guard后拒绝解释，安全持久化后回收；ready-first非阻塞轮询共同deadline，不因首unknown而阻断后ready。四新增CPU用例覆盖坏guard、错extent、unknown首owner、实际CUDA transport读回函数坏guard carrier；无设备故障冒称。install-v4 controller380452/start1006317977、worker380453/start1006317980 terminal0/53.148s，normal/-O各27owner/finalization通过；原16owner+7finalize之外4新增。
- ea70da7实际产品：新timeline_enflame.py组合既有共同owner/原件持久化与GCU自身transport/decoder；默认真实first-last请求、native先allocate交owner再initialize、原流Event记录、最终化才query/read。Debugger PreparedKernelLaunch显式synchronize布尔opt-out，legacy默认仍同步；不改C++/物理ABI。公共owner允许transport校验真实typed executable identity，不伪造NVIDIA function/num_ctas。编译对象源码/asm/binary、原native元数据、关联与raw进入持久化输入；最终化后再取GCU已发布run走标准bundle。
- install-v5 sourceea70da7/native789，controller380574/start1006351531、worker380575/start1006351535 terminal1/57.713s：新测试错误以dict代替实际compiler metadata对象，尚未调用产品prepare便返回None；794a5f6只修测试为SimpleNamespace，原失败保留，不覆写终态/不热补安装。单独cpu-v5-recheck controller380776/start1006366042、worker380777/start1006366045 terminal0/25.454s，byte核450安装成员与native flags[2,2,2,2]，normal/-O各70（11legacyGCU+11firstlast+16commonraw+5deferredpolicy+27owner/finalization）。wheelSHAdde171bb115abe7e449209e53ce0c240e1181d9a45374289ff6c3587210cf20e；venv=/workspace/chijin-timeline-r016/runs/install-v5/output/venv。
- 默认API真实public-timeline-v1 controller380934/start1006371935、worker380935/start1006371939 terminal0/17.194s：cold/warm共6调用，全部提交后才首次query/read，每轮保3独立owner，无逐launch全局同步，同binary随runtime K实际events10/14/18。原math/input/tail/唯一副作用、最终bundle/canonical/raw字段引用通过。
- c4fc1e7测试脚本。实际CLI public-cli-v1 controller381214/start1006389576、worker381215/start1006389580 terminal0/16.190s，普通无scope脚本3调用，经公开--detail timeline --backend enflame --device0完整导出。owner-recovery-v1 controller381498/start1006394095、worker381499/start1006394098 terminal0/16.140s：两个真实GCU streams交错3调用，first decoder注入失败前已持久化3原件/释放安全owner，其余2正常解码；同目录原件重试0transport动作、原SHA/首次attempt不变；新合法session1调用成功。仅in-process retained hook恢复，不冒称public cross-process恢复。
- 原件一：artifacts/timeline/run-016/preflight/gcu-first-last-original-evidence-v2.tgz，18,393,566B/1605files/SHA5e2e5d0421b2b4752b732b114f0d813f00b9e25803a8de8a0c2c94353dc45e31，含全部native失败/输入audit/producer前后和advanced输出。最初archive cap100MiB因261MiB未压缩输入而拒绝，未视为产品失败；核大小后有界300MiB重采，保第一次空输出。
- 原件二：artifacts/timeline/run-016/preflight/gcu-owner-original-evidence.tgz，10,321,088B/280files/SHA8eab98f1b755e7b0df60d77498dba1366700e8bdfee7fd15e5788608b30e7ec7。stdlib audit核13默认captures/576精确物理端点/288区间、独立namespace、实际安装/全部CPU及恢复SHA；不在工作机import产品/跑oracle。小报告/命令/审核脚本在integration/evidence/timeline-gcu-owner-r016。selected964个declared controller/worker身份均missing/reused/Z，没有该检查范围内live进程；本轮任务全部实际terminal且worker/controller missing，不代表审计其它用户或其它机器。
- 仍active且未P01：NV/GCU均raw-only，clock/ns/epoch、最终source边界、普通流水扰动、GCU allocation guard/真实async两代复用、Ascend新timeline producer、标准pftrace/TP/UI、独立六数学和最终额外三个Sol6.1/xhigh代码走查都未完成。当前NV已安装仍r015，公共Pythondelta尚需真实NV匹配安装与回归；下一步优先clock/ns/标准export和边界/async证据，同时补Ascend producer与guard/公开恢复链。设计reviewer不替代最终review。
