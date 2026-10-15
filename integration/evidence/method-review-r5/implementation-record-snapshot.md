# Method 实现执行记录

执行指令：`method_goal_prompt.md`。论文：`paper/main.tex` 及引用的 tex。

## 当前恢复摘要

- **状态：授权实现/方法正文/独立审阅与有限修复全部完成，等待最终Git/goal收尾。runtime2d7eb95，final469源/52Python一致；三Docker491/414/477通过(4/5/20明确skip)，99专项/r9隔离wheel通过。最终三报告无剩余actionablefinding；贡献判断为限定范围内plausible Operational Systems，非接收保证。所有自有任务终态/PID不存在；NV性能明确deferred。**
- 用户目标：在实际开发分支实现程序—执行映射、执行语义感知观测、程序关联重建；适配现有NVIDIA/GCU/Ascend；保障质量；按实现写方法；三独立reviewer判断OSDI贡献并迭代，可修则继续，不可修则返回原因。
- 实际分支：`ChijinZ/FlagPrism:detailed-profiler`，不是`detailed_profile`；准备时HEAD `a7a9aca63738c69ef7846b0faf201206b0882a62`，启动需fetch核实。
- 主仓库`FlagPrism/`仍为`study-and-eval`，HEAD `dba2ff9c74f4e4a8063126c554bac1708d6f72d9`；未跟踪pipeline代码/数据必须保留，不能reset/clean。后续实现用独立worktree。
- 只读审计worktree：`/tmp/flagprism-detailed-profiler-audit`，detached `a7a9aca`；不依赖临时目录持久存在，不在其中误提交正式分支。
- 现有容器：NVIDIA `chijin-study-pro6000`；GCU `flagprism-enflame-dev`；Ascend经chijin用户访问`chijin_v3.5.x`。先复用，确需新建名称含chijin。
- 全部依赖安装/编译/单元与硬件测试/CPU参考在远端Docker；本地只编辑、Git、调度、离线分析、PDF构建和review。
- 当前无本任务GPU采集/编译后台进程；Asc owner报告8ownedjobs均exit0/PID不存在。当前仅两位只读reviewer运行，无硬件任务。
- Git HTTPS推送曾缺认证；已验证SSH ChijinZ身份可以推送用户仓库，不能输出凭据。
- 正式worktree：`FlagPrism-method/`，branch `detailed-profiler`，baseline a7a9aca；原Study工作树未改。NVIDIA/Ascend/GCU各一个工程agent独占对应设备；root处理公共协议、重建、Session导出和编译记录机制。
- 已提交并推送 `654cc91`、`8a7beee`、范围格式 `3107c04`、GCU发布里程碑 `c207f6e5f2c511ef5c20f6a25e67a4c106f077c5` 和容量保护 `c659eecc5e8215fbe68c3c2dca8a4b775edef775`（ls-remote精确确认）。CANN single-task/SDK retention、公共任务分类、失败恢复已由0ef0adf阶段提交并实际推送；新MIX上下文/receipt恢复已提交42bd4ae496b21afe981d93c5a349f2c2239f7382并push，ls-remote精确确认；全Asc矩阵仍运行中。
- **下一步**：仅最终证据/评审/记录快照commit、push与ls-remote核对、goal完成并交付。无待补功能/硬件任务；后续性能及更强时钟/局部准确性研究需另行开展，未算本轮通过。

## 进度

| 阶段 | 状态 | 下一项证据 |
|---|---|---|
| I0 审计/冻结 | 完成 | baseline及469文件最终冻结a9a28ba，三个实际native库hash留存 |
| I1 可信采集 | 支持范围通过 | native/raw保留、身份关联、无名称/比例伪时间 |
| I2 编译映射 | 支持范围通过，部分归属明确 | GCUownership；Asc同编译typedchannel与严格源/manifest溯源 |
| I3 细粒度观测 | 支持范围通过，局部时间有边界 | 动态记录/语义选择/原生关联；无sharedclock证书、不假装完整iterationID |
| I4 产品/验证 | final regression通过；成本负结果保留 | 三Docker483/406/469，r7wheel；selected offline regime，NV性能deferred |
| I5 方法/贡献 | 正文及12页PDF冻结；第二轮独立审阅 | 首轮major后已做实际修复/局部敏感性/正式诊断闭环，等待新三报告 |

## 2026-10-14 / M000：建立执行合同

**需求**：用户要求准备可用`/goal`的命令文档，包含三机制实现、三后端适配、质量测试、方法正文、三独立novelty/贡献review及可修复迭代/不可修复停止；Git管理和环境问题返回。

**完成**：建立`method_goal_prompt.md`和本记录。指令明确工程与论文两个验收、T1–T6、硬件测试及支持边界、正式入口替代专用脚本、Git/worktree隔离、Docker复用、审阅盲态、迭代条件、环境停止和最终交付。

**已有审计发现（并非修复成果）**：

- LaunchHook已有source/binary/argument身份；Debugger已有TrackedOpTable/op/scope/source metadata；已有bundle、HTML/Perfetto、TCU aggregate和replay语义。
- 内部时间路径存在按名称顺序关联及cycle-span比例映射；不是实测clock校准，须优先改。
- deterministic record slots不能一般性保存动态循环历史；需快照/动态日志分离。
- 当前Debugger内部timer只覆盖Ascend；新规范活动报告和外部counter扩展主要由Enflame真实验证，其余后端需实际接入。
- 最终worker/actor/buffer/dependency映射及Study joint-SYS机制尚未成为通用正式工具能力。

**边界**：本条只准备指令，没有改变工具分支、安装环境、启动实现子agent或声称通过任何新测试/novelty验收。

## 后续记录格式

每次实质进展追加编号；顶部摘要保持最新。

- **编号/日期/阶段/用户新增要求**：
- **问题与实施前预测**：
- **branch/baseline/commit、源码与实际导入路径**：
- **继承能力/本轮新增机制、支持边界和取舍**：
- **backend/container/device、命令、PID/session、log、timeout、exit**：
- **修改文件/协议/ABI兼容性**：
- **测试组/命令/oracle/预期断言**：
- **实际pass/fail/skip、数值/identity/clock/丢记录、扰动和资源结果**：
- **原始证据与hash、失败/负结果**：
- **正文变更/图/PDF构建结果**：
- **review版本/三角色报告/意见类型/处置理由/下一轮计划**：
- **是否有需用户处理的环境条件及最小操作**：
- **Git提交/push或待推送状态**：
- **最后终态、当前活动任务与下一条具体命令**：

## 2026-10-14 / M001：启动、隔离与真实adapter实现

用户启动goal；fetch确认baseline a7a9aca，建立正式独立worktree FlagPrism-method。三工程agent分别核验NVIDIA/CANN/GCU容器并实现或验证producer；设备0/4/单NVIDIA分别独占，禁止公共文件并行改。NVIDIA现CUPTI仅旧KernelMetric，agent补规范活动；CANN旧关联包含名称/近邻匹配，agent改明确MSTX scope；GCU已有规范活动，agent实现编译产物映射并调查timer。root负责公共可信时间/identity及动态协议、最终集成。原Study未跟踪文件保留。当前不是完成验收，尚无本轮硬件通过结论。

## 2026-10-14 / M002：三后端真实原生smoke、语义合同与编译handoff

**新增**：Cupti规范活动与真实scope/correlation/stream/device上下文；CANN9实际JSON connection_id/task+明确MSTX payload，移除名称/邻近猜测；GCU TOPSPTI真实kernel活动。三backend均实际向量tail数值通过并导出正式bundle，证据 artifacts/method-run/{nvidia,ascend,enflame}，尚需同一冻结源码的最终回归。

**公共机制**：新增observations.py typed semantic/clock合同；移除源内时间按kernel/host时长拉伸和名称关联的默认timeline路径；未校准raw记录单独导出，不自动转换Perfetto；legacy snapshot显式标注重复site可覆盖。新增execution dispatcher与3真实IR adapter，LaunchHook按binary记录manifest，bundle导出ai/execution.json。源op未在最终产物存活时partial，不能称M1完整通过。

**后端技术证据**：NVIDIA独立新runtime通过真实native3调用、同名双stream、嵌套session；ring decoder保留SM-local raw ticks/溢出，不继承假1GHz。GCU真实SDK @_ZN4tops12global_timerEv 的LLVMFuncOp/CallOp合法lowering通过；8次非零46bit tick单调，未知频率，不声称μs。GCU物理身份实际 ZIXIAOC200 / BUS00:23:00.0 / Driver1.9.10，不能继续无核验称GCU300。Ascend实际SDK为LLVM15.0.5，LLVM22不能直接插入；独立opt15 pass成功，SDK直接plugin fork crash139负结果保留。正式per-compilation driver callback+独立pass经真实vector compile/device4通过，实际AIV9 formals/13 sites，源debugloc/opIDs缺失明确保留。

**测试**：GCU此前128 pass/4 browser skip；本轮新增time/observation合同13/13 Docker通过。新core GCU构建已完成；正式finalize暴露root helper丢失NameError，已恢复_op_metric_name，待重跑。api.py正式prepare绕过runtime.py时钟传播，已补两入口，待实际验证。Ascend7 importer+10 mapping unit通过；NVIDIA5 mapping+5 ring unit与actual vector/reduction/matmul数值通过。上述不是最新全部修改的最终验收。

**关键未完成**：GCU snapshot→真正动态append、Ascend explicit hidden pointer final-role映射/动态测试、NVIDIA正式ring导出；public request routing和counter入口；同调用clock proof、source变换归属；T1–T6完整硬件与六算子/heldout/3×30扰动；论文/三独立审阅/Git提交推送。新代码全在detailed-profiler工作树，尚未commit。

**当前活动**：method_nvidia_native负责NV core build/typed ring producer；method_gcu_mapping负责新core正式入口与GCUtimer/动态方案；method_ascend_native负责late LLVM动态64/driver缓存与最终ABI。root公共profile/capture/report/Debugger Python及集成。恢复先查看各agent状态与artifact日志终态。

## 2026-10-14 / M003：真实动态证据与公共接口集成（仍执行中）

- NVIDIA全新独立FlagTree完整build exit0，libtriton ac68af1c…、native7a0894a1…；实际Triton循环3/7/23保留3/7/16区间，23循环丢14 primitive records。继承stderr声称60丢记录有words/event混用，新增decoder按真实协议纠正。正式sidecar SHA/actual scope/unknown ns通过；并发detailed明确拒绝且首launch保留、后hook拒绝rollback与后续launch通过。日志method-instrumentation-nvidia-r3.log、method-lifecycle-nvidia-r1.log。共用request NV lower保留allCTA/all explicit scope成本边界，program/site仅postcapture输出过滤；sample_every!=1拒绝。root已接公开start路由，待最新集成回归。
- GCU新完整core build成功，正式profile入口数学+bundle通过；timer descriptor虽在compiled metadata，native parseRuntimeMetadata会丢未知Python字段。root两prepare入口及finalizer/runtimectx恢复observation_clock，**旧i3-formal-preview实际仍unknown，不能把旧日志当descriptor通过**，新验证进行中。新增动态kind7 64B布局与selected solewriter private cursor、不引入全设备atomic/barrier；header+24=attempted，+16仍recordSize；sampling/drop/saturation显式。Protocol/Decoder/Binding/TransferEngine与C++DecodeTests已集成；agent负责Passes与Binder，实际动态branch测试中。
- Ascend LLVM15动态pass真实device4迭代5/tail257/header[1,12,12,0]/数学与输入保持通过，仍为explicit-extra-source-buffer测试。最终ABI形式位置不能猜：实际SyncBlockLockArgIdx/WorkspaceArgIdx+FFTS intrinsic证据路径正在泛化；新source ABI/driver/cache callback/manifest含original与adapted不同hash。正式产品hiddenptr与同调用clock joint尚未完成。
- 公共bundle保存raw/native/capture.*原始vendor/meta/hatchet/timeline/launches，遗留timeline假clock不默认展示；新增ai/reconstruction.json与report/observations.html，按actual invocation/binary与每actor独立clockframe展示，独立counter replay不拼时间。Debugger static与dynamic raw buffer编码/hash随sidecar。新增portable legacyclock、Hook rollback、typed dynamic、reconstruction反例回归，待Docker执行。CANN external counter注册公开CLI，暂无最新CLI硬件通过。
- Existing CANN tests首次真实回归15fail/7pass/3error：13旧prefix输出预期、2mock生命周期预期迁移，3fixture Triton→torch_npu circular import；agent修公开bundle路径与fixture import次序，不能改为内部模式蒙混。负结果 public_pytest.log保留。
- 已核对当年官方CFP https://www.usenix.org/conference/osdi27/call-for-papers ：Operational Systems track保留；不硬性要求全新研究想法，但须真实operational设计/分析/经验与公共知识贡献。当前三设备研究实验不能伪作真实部署，后续review分别判断技术与运营证据。
- 尚无Git commit/push。本轮未达I4，三novelty reviewer尚未启动，正文尚未改写。继续工程与质量，不提前审阅索要肯定结论。

## 2026-10-14 / M004：泛化回归、真正容量与昇腾hidden-only桥

NVIDIA六算子3shape×2配置与预先RMSNorm3shape×2配置共42case、126实际kernel，CPU参考及正式native bundle通过，原Study输入bytes/hash和数学容差未放宽；operator-validation-r1.json。公开request grid4×loop7/max4实测：实际全4CTA采集，每CTA8primitive容量丢6，全drop24；输出program0四interval，其它12interval后过滤。明确这不降低其它CTA的GPU插桩成本。

GCU动态真实steps0/5/9与双分支数学/次数/clock初步通过，every3采样通过；steps1首次失败是Triton整数1常量特化，修改do_not_specialize保证runtime测试；capacity5首次实际64，是旧Frontend最小容量规范化，不是overflow成功。root已在Bindings仅dynamic layout恢复用户真实capacity；新header一致性保护、snapshot独立布局保留。C++独立Docker harness当前Decoder全部25/25通过，包含新dynamic与窄slot拒绝；最新其他修改仍待完整回归。

same-callidentity首次未关联原因：Debugger.launch_context把actualLazyDict变成新dict。root现私有sideband保留实际对象引用，LaunchHook实际enter赋scope/binary/session_membership，finalizer从同对象读身份。尚需新硬件核验，不提前声称verified。未校准时钟仍只rawticks。删除死的名称顺序/合成kernel helpers；legacy Hatchet IR节点独立capture，不按名称挂到native node；旧IR synthetic IDs0/runindex改unknown None。normalized scope关联不再要求kernel名字相同，新增反例测试待跑。

昇腾automatic source-formal role路径真device4通过：source nonconstexpr参数3→source formal5→final formal6，使用compiler-emitted Sync/Workspace attrs+实际FFTS launcher配置与type验证。开启SDKdebug-info后16/16 primitive有DILocation，但多为kernel入口行，精确source op仍partial（dynamic_handoff_debug2.log / dynamic-final-captures.tgz）。不能称映射完整。

正式产品hidden-only桥实现中：新增 fd.prepare_late_observation_abi 复用实际TTIR func signature追加control ptr并返回真实index，无TTIR日志写；root compiler.py/公开request/Nativeallocation/finalizer已路由 ascend_actor_dynamic_v1。每actor4×u64header与C×64记录、三slot总字节3*(32+64C)；复用TransferEngine size64/capacity3C+1精确分配并只zero初始化，不套RingHeader、不经过旧RingDecoder。late driver依据真实source role寻找final formal，禁止用户需要手改算子签名。需要新Ascendcompiler binding/native实际build和正式请求测试，当前explicit-source-buffer结果不是产品完成。

现旧CANN回归迁移后19pass/6fail；其中真实device选择错误：app在device4而旧collector默认0，正在修actual aclrtGetDevice默认采集设备与测试workload。仍需CI/API/CLI全部、六算子、jointclock、fidelity与3×30开销；暂无冻结/提交/正文/noveltyreview完成。

## 2026-10-14 / M005：真实发布协议、六算子与开销负结果（继续修复）

**GCU**：新core正式入口六算子×3shape×2配置36/36通过、108实际TOPSPTI任务；runtime循环/branch/sampling/capacity/多launch+heldout RMSNorm10/10通过，输入、输出canary、CPU参考容差继承原合同。原动态16×i32 vector record由4work-item协作写，而solewriter条件只允许actor0，导致后12words未发布。改为16个scalar store及末尾64bit commitTag `0x465044594e563031`，decoder核验commit/sequence/attempted/duration。保留前后IR/LLVM/raw的机制反例，不能将数学正确等同记录正确。最新C++ Decoder26/26；portable contracts169pass/4browser skip。证据 `artifacts/method-run/enflame/GCU-I3-evidence.md`、`dynamic-final-manifest.json`、`cooperative4-vector-publication-before.tar.gz`、`dynamic-scalar-publication-after.tar.gz`。物理型号已核验ZIXIAOC200，GCU300 API库名不是板卡身份。

**NVIDIA**：正式42case（六算子36+预选RMSNorm6）与126实际kernel通过；动态循环0/1/3/7/23同binary精确保留0/1/3/7/16interval，overflow14primitive，clock仍SM-local rawtick未知ns。raw exporter复用native已拷贝字节，不新增第二次DtoH；finalize只搬有效prefix，无额外barrier。独立FlagTree JIT unconditional instrumentation_mode覆盖Hook编译模式导致off复用错误scratch ABI，修为setdefault并保留patch/cache反例。实际graph capture-before/during两次replay×2kernel有4原生活动，但graph子kernel缺source/binary身份，不强行join；既有graph-before SDK状态还存在降级限制。新增正式LLVM lowering FileCheck PASS；上游11lit有9继承ABI/fixture不兼容失败，日志保留，不算完整通过。

**开销负结果**：NVIDIA T5-r3保留全部450样本，独立同一CUPTI reference覆盖off/native/detail等阶段；off/native中位1664ns，优化后detail1888ns（+13.46%，仍高于≤10%目标），host约2.05ms，bounded约1.17ms。GCU尾Softmax真实全site25事件：3批×30×3共270测量调用+15warmup全部数学/identity通过；native任务中位117.27–117.35us，detail545.75–546.28us（约4.65×）；host off27us/native75us/detail5.71ms。GCU off仅stream envelope、没有isolated task，不能将其冒充device扰动参照。负结果原样保留在nvidia/overhead-r3-result.json及enflame/tail-t5-tcu-formal-evidence.tar.gz。下一步真设备program/site选择与采样，不能只postfilter或改阈值宣称合格。

**正式counter/Study案例**：GCU尾Softmaxw4/w1动态各3capture、25事件、实际source mapping通过；CLI `--counters SIP/BUSY` replay none真实完成，各配置aggregate2invocations，24SIP原min/max/mean/count保留，cycles6047.6/4988.6来自独立采集，不关联到先前dynamic invocation。计数器cycles不等于SDK global_timer tick。

**公共接口/质量**：actualLazyDict身份引用修复已实机通过，动态capture绑定真实scope/binary/session membership；snapshot/event类型分离、actor-slot clock frame、未知保持unknown。新增已拒绝launch不参与join、kernel name与SDK rename无关、原始native trace不默认冒充校准trace。activate/deactivate无参数改为所有现存session，显式未知ID在Hook状态改动前拒绝；invalid-session测试使用独立bundle并新增无phantom hook/恢复断言，最新修改待Docker回归。NVIDIA旧suite首次32pass/1skip/15fail，含legacy路径、unsupported PCS及后续污染，正在逐项修复；不能称已验收。

**Ascend状态与修正**：M004“debugloc多为入口”需更正：实际debug-info有16/16 primitive、7个不同(file,line,col)，包括loadX12:23/loadY13:21/loop14:19/add15:14/store16:20；保留inlined-at与bounded source candidates，一对多/歧义显式，DILocation origin不代表成本独占。hidden-only public ABI/pass/runtime/routes已实现，但新core编译+正式硬件仍未通过。SDK msopprof公开A2 packet解析与same-call clock proof已接代码，要求实际capture/device/stream/task/connection/scope/packetSHA/counter-domain证据；不能仅以时间containment判关联。新增测试待Docker。

**环境阻碍**：Ascend SSH gateway两次agent和一次root独立检查返回 `no available gateway`，exit0但实际Docker命令未执行；日志 `artifacts/method-run/ascend/root-connect-check.txt`。已向用户请求恢复网关或更新ssh_machines.sh；停止盲目重试，pending命令/恢复顺序在PENDING_VALIDATION.md。这是当前goal回合的真实环境条件，不满足连续三goal回合blocked门槛，goal仍active并推进NV/GCU。

**终态**：NV agent设备selector/legacy/C++回归；GCU agent设备sitefilter及tail/T5复测；Ascend仅静态审阅/恢复说明等待环境。尚无新commit/push，方法正文未根据半验证代码宣布完整机制，三novelty reviewer未启动。下一轮需所有新修改同源码冻结验证再进行正式交付/贡献审阅。

## 2026-10-14 / M006：首个Git里程碑、恢复语义与full-core跨后端编译

**Git**：共享 typed observation/clock/request与保守reconstruction及两组对应测试作为独立提交 `654cc91`，已成功push用户 `detailed-profiler`（a7a9aca→654cc91）。该部分此前GCU Docker合同回归通过，不代表三后端完整产品验收。原Study工作树保持独立；后续实现在相同worktree继续。

**T6修复与待验证回归**：activation纳入start异常域，失败时释放已启动native/session/hook及instrumentation，cleanup失败附原异常note不替换原异常；只删除自己创建的空bundle，不删除已有空目录。PCS真实Blackwell/CUPTI probe可enable但stall reasons=0，旧GetStallReasons(count0)错误1导致半启动会话污染；新增preflight在native start前检查真实SDK支持（非env屏蔽）并显式unsupported。未初始化CUDA context仍真实报错；test只skip确切unsupported而不是所有异常。装饰器现在在函数/停采失败后finalize自身session并保留原异常；CLI内部装饰器不改变CLI拥有的session。新增portable失败恢复与CLI所有权回归，均待新Docker测试。

**完整core构建负结果**：NVIDIA fresh UT-on build-r5在Debugger runtime旧throw与LLVM `-fno-exceptions`冲突；root只为FlagTreeDebuggerRuntime target加fexceptions。r6进一步发现新增GCU setter/Asc hidden helper的throw也进入compiler noexceptions目标；不禁Debugger、不对compiler整体启用exceptions，改GCU setter为llvm::Error、Asc helper为llvm::Expected<uint32_t>，CompilerBindings负责转py::value_error。两个agent共享header/API已协调，重新fullbuild待结果。不能以standalone native build成功替代core通过。

**GCU选择**：真实设备sitefilter和region-free pre-sampled timer已经编译；14硬件case首轮12pass/2fail，失败为C++正确拒绝不存在site但Pythongeneric错误未给可操作site诊断。保留负结果，补编译failure reason attr/getter并重跑。region-bearing嵌套interval起点/末尾ordinal不同，不提前筛timer以免采样伪interval；采样降低成本支持范围明确region-free-sites-only。尾Softmax静态表候选load16/reduce17,22/store29来源真实TrackedOpTable，计划四site及单siteT5对照，尚未承诺低开销达标。

**M1待补强**：NV/GCU surviving source attrs缺失，不能把layout/ownership全partial称完整source映射。NV拟从实际RecordOp、scopeID及FileLineCol/CallSite/FusedLoc提取(binary,regionID,origin)，generatedop仍partial。GCU已查实际公开SDKbridge pipeline printing仅printGenericOpForm而未enableDebugInfo；计划独立FlagTree patch保留真实loc，再以TTIR tracked origin做bounded候选集合，一对多/歧义显式，debug-origin仍非exclusivecostownership。这两个技术补项均需真compile/hardware核验。

**用户文档**：新增Profiler/docs/semantic_profiling.md、method_testing.md，明确公开API/CLI、clock/selection/replay/原始数据含义、T1–T6入口和未验收Ascend边界；原activity文档修改为raw/native实际保留原始输出。Ascend agent继续无SSH静态审阅和README，网关仍待用户恢复。方法正文/三reviewer尚未开始正式验收审阅。

**恢复动作**：NV先同步三公共C++文件和Runtime CMake，freshbuild后同步root profile.py/test_api.py/test_portable_capture.py并跑完整portable与legacy；GCU新Error interface/site诊断14case、tail T5再补loc机制；Ascend按PENDING_VALIDATION.md在用户恢复网关后执行，不能盲目重试。root仅编辑/Git/离线原论文获取，没有本地运行实验/测试。

## 2026-10-14 / M007：真设备选择、构建与会话暂停的进一步修复

**NVIDIA工程**：full UT-on r7暴露Debugger原生compiler plugin与核心FlagTreeDebugger重复编译相同实现；Debugger/native/CMake现复用已存在coretarget，仅UT_OFF保留独立implementation。r8完整链接成功但Pythonimport缺mlir::Pass RTTI，新增selector Pass类错误放在RTTI binding TU；移到既有fno-rtti conversion target，r9完整core+native真实import与selector硬件PASS。选program0/1只有对应CTA14primitive写入，其它CTA计数0，capacity8丢6；请求99超出grid无record/drop，3模式实际binary/cacheidentity不同。

NVIDIA新版T5-r4同一独立SDKreference3×30采样完成、SDKdrops0与exactidentity通过；但他人GPU进程PID786895占38034MiB，GPU100%/温度82，容器NVML没有PID不能证明独占。保留全部受干扰样本，default2272ns(+36.5%)及末bounded1760ns(+5.8%)均不能用来认证达标或优化因果，不终止他人进程。继续correctness/origin，等待真实空闲窗口复测。

旧NV legacy-r2真实41pass/1skip/7fail：PCS test使用backendcupti/modepcsampling绕过仅alias preflight，root现同时检查两合法入口；timeline thread-name metadata不计kernel Xevent，agent已修断言。warp specialization真正数据缺失来自active-prefix finalizer仅master partition运行，worker只有SaveCtx；新增worker不复制导致错误。修为WS总warps与普通numWarps不同时复用继承firstCTAthread全ringcopy，普通路径保留prefix优化、无新增barrier；需新build/实际WS回归，不掩盖成fixture变动。其他tree层次旧断言在迁移，非最终通过。

**GCU工程/开销**：新Error接口/sitefail诊断最终14/14硬件通过（11dynamic+预选RMSNorm3），486.23s冷编译。四真实site(load16、reduce17/22、store29) T5全部270calls数学/identity通过，真实task约288.53–288.76us vsnative117.46–117.67us，仍约2.46×；单store约219us，仍1.87×，高开销结果保留。发现record lowering无条件让所有program/workitem读两全局header字段，agent已把两读移动到selected predicate内并完整core重建；下一轮guarded单site/no-selected-program ablation尚待结果，不能先称解释全部成本。

GCU真实LLVM leak审计：off/native6phase binary/TTIR/GCU/LLVM完全一致、没有globaltimer/动态cursor/layout；detail不同binary且包含真实timer/cursor。原native117us非observer缓存污染；off仍只有stream envelope，不能据此认证native≤5%。审计在i3-evidence/t5-softmax-w4/ir-observer-leak-audit.json，待新archive索引。

**公共T6与错误回归**：新增test_report首次187pass/4skip/12fail，其中1为root插入test时把旧test结尾out断言移错位置（已修）；11是旧GCU API多session不适用导致状态污染。现在vendor多session测试实际验证active/paused拒绝及同路径恢复，不只跳过；direct inherited InstrumentationHook仅CUDA/HIP，GCU正式Debugger路线另测；test_api autousefinally释放自身sessions，cleanup error不吞。raw Enflame路径旧断言改实际raw/native保留。

进一步发现IR publicdeactivate只停native/LaunchHook而Debugger仍采样，可能把paused调用作为unknown IR塞入bundle。root新增state.active，最后activeIR暂停Debugger，resume恢复同request且clear_runs=False保留以前数据；same-output同配置start复用已有session/hook，不构造重复InstrumentationHook；改变已存在session backend/mode/hook/request明确拒绝。pausedIR另start失败不清旧records；HookManager .get避免phantom空session/hook键。新增portablepause/resume、original BaseException与CLI装饰器所有权回归，GCU agent将跑真实detail→pause→plain→resume→detail，要求仅2dynamic/2native调用。所有最新生命周期修改仍待Docker验收。

**原始编译证据**：LaunchHook按实际binary首次保留kernel.asm文本；bundle新增raw/compiler/的TTIR/TTGIR/GCU/LLVM/PTX全文及ai/binaries hash/relative链接，report JSON不inline重复文本。新增IR-byte/hash/manifestroundtrip，需修正后完整回归。只有source/binaryhash而临时编译文件已消失的bundle不足以离线核验实际映射，故该改动属于可复核工具输出。

**Ascend pending与边界**：README/恢复script/hash已生成（未执行），恢复应保留0364ed4独立worktree与实际FLIR HEAD，初始driverpatch缺后续cache callback已准备幂等恢复但新完整patch尚未生成。ABI/helper与decoder静态修复均未实机：隐藏formal必须末尾且真实type/role/index有效，SDK特殊roles不得重叠/越界；zero actor header改no_records/execution unknown，不推断actor未执行。root还发现align_same_call仍是独立函数，正式finalize尚没有raw SDK program anchors→真实invocation/domain proof的自动producer；**这是实现缺口，不只是测试待跑**。已要求agent沿旧Study joint成功路径整理一般化正式collector入口与SDK冲突验证；网关恢复后必须补真正端到端连接，不能传任意proof dict声称自动对齐。

**原文材料**：已保存KPerfIR官方PDF及hash、原文sections/figures和原公开代码locators于artifacts/method-run/prior-work/README.md；明确NVIDIA+AMD、多级插桩/regionloop/circularbuf/hidden scratch/异步校正为先前工作。Proton官方abstract与作者页已核对，其官方preprint现404，不能从访问失败推断缺能力。未来独立review须核原文与继承代码，不把重命名/接口适配当新算法。

**当前终态**：goal active，首个commit654cc91已push；其余代码仍未冻结提交。NV WS/origin及legacy、GCU header-ablation/生命周期/sourceorigin、Ascendjoint正式producer与恢复说明继续；三reviewer与正文仍等待工程证据。AscendSSH待用户恢复；NVIDIA性能受真实外部占卡限制。没有本轮完整成功宣称。

## 2026-10-14 / M008：实际源码origin、全构建回归和64位成本归因

**NVIDIA冻结证据**：r11完整UT_ON core/native构建成功，compiler SHA256 `6f8ac1fea0df5a13bb9084b332cf0492d441f8ff3adadd681e44eef4b725ad0b`，native `aab4b8d2b98c2a6ed19b9943ab585ae856f3ee8b60b9ee8c0111ede3517a3b32`。最新legacy47pass/2skip，TraceDataIO13/13，适用LLVM FileCheck通过；contracts166pass/4browser skip，另外observation/internal-time/rollback/latestreconstruction22pass；正式六算子+RMSNorm42/42、126kernel CPU原oracle通过。旧失败和PCSampling硬件不支持证据仍保留，不改成全部SDK功能支持。source-origin新真实binding从RecordOp实际loc+scopeID构造entry/exit候选，NVunit17/17；相同scope名称的不同ID和不同shape binary不误合并，旧无loc三参调用unknown。当前文件byte snapshot与compiled text alignment不是同一证据，后者未独立验证。root最新reconstruction实际离线bundle3/3正确关联source_region_origin且duration_ns仍None，三个错误binary/site反例拒绝。详见nvidia/I4-evidence.md及full-source-manifest-final-r3.json；之后公共Bindings/GCU writer变更需新最终hash与适当fresh compile，不复用r11声明最新源码全验收。

**Ascend CPU与真实缺口**：在NVIDIA远端Docker上，Ascend ABI/clock/compiler/importer与真实MLIR hidden-only helper合计32pass、0skip；这是CPU/compiler契约证据，不是NPU硬件验证。Ascend网关仍未恢复。JOINT_CLOCK_AUDIT.md核查旧Study：SDK单次application-replay campaign和输入/binary provenance真实；packet对应其中三source调用仍依赖common SYS epoch下唯一containment，不能据此说正式API已自动取得独立same-call identity。独立align_same_call函数之外缺正式SDK scope/API connection→device task→raw counter-domain producer/wiring。需要恢复CANN9环境验证actual TASK_TIME/RUNTIME_API/MSPROFTX raw schema、单collector所有权与SYS counter-domain证明，不能传人工proof字典替代机制。现PENDING/README明确此项为实现缺口。

**GCU origin**：公开SDKbridge加入debug-location打印后7target构建成功，实际loc alias/callsite/fused/function/cycle等CPU测试9/9。正式M1硬件15/15（505.91s），14份bundle审计通过；partial+exact associations0，候选source IDs均存在真实TrackedOpTable，exclusive_cost=False。动态loop origin候选2716，其中unique1204/ambiguous1512/missing7；RMSNorm3shape实际数学通过。origin表示编译位置来源，不表示成本独占。证据m1-source-origin-final-hardware.tar.gz及enflame-timer-location-origin.patch。最新source_origin_association_count已经公共导出，最终冻结需同步。

**GCU成本归因**：移动header reads到selected predicate后单store约213us vsnative117us，仅小幅改善；无selected program999实际90calls仍约228.9us，header无事件/丢记录，说明timer/store不是全部成本。独立native(enable_i64=True)约199.25us；最新同进程随机配对False/True共180samples+10warmup，False117.405–117.428us、True199.236–199.604us（约+70%），两模式数学正确且无SDK timer/trace。不能把True人为改称同baseline以凑≤10%。实际LLVM clock probe8/8验证仅LLVM i64 carrier可在enable_i64=False下取得单调46bit ticks；故成本源为当前writer引入TTIR i64运算/控制，而非不可避免的SDK timer条件。

**有限修复正在验证**：GCU writer改4×i32 endpoint words、duration低字减法+借位、i32 cursor/flat program/offset；只有LLVM clockcarrier为i64，移除强制整个kernel enable_i64。metadata明确debug_dynamic_index_bits=32/debug_clock_carrier=llvm_i64_words。root PreparedLaunchHandle加分配前真实launch guard：grid维度≤INT32_MAX、product≤UINT32_MAX、32+64*capacity≤INT32_MAX、selected program≤INT32_MAX但可超grid；必须真实非空grid/layout64/carrier一致。新core writer已编译，native guard/动态/heldout/矩阵/T5正在跑，尚未通过验收，不提前宣称开销目标达成。

**公共生命周期**：真实GCU detail→pause→plain→resume→detail 1/1通过（25.8s），数学三次均正确，bundle只有两个detailed和两个native调用，first/third同instrumented binary，中间plain无timer/cursor且binary不同。最近合同199pass/5skip（四browser和继承GCU不支持direct InstrumentationHook），真实test_enflame3/3；不同批次测试计数不合并伪作同一冻结batch。

**终态**：goal active，654cc91已推送，其余里程碑待最终冻结分批Git提交。当前GCU engineer独占device0验证i32路径；NVIDIA正确性冻结但外部进程负载阻止性能认证；Ascend须用户恢复网关，停止重复无效SSH。三formal reviewers和方法正文尚未达到I4启动条件。没有将环境阻断写成novelty否定，也没有将三机器研究实验写成生产运营经历。

**用户最新环境回复与复核（M008续）**：用户表示昇腾可能恢复；已授权有限重试，工程agent使用正式连接执行带Docker sentinel的readonly检查，实际仍只返回no available gateway/exit0，没有运行到Docker。日志gateway-restore-check.txt，已向用户反馈并请求核实连接或更新ssh_machines.sh；没有盲目重复尝试。用户同时明确Pro6000开销先保留待验证、继续其它工作；不再等待/打断外部占卡进程，继续正确性/编译/交付，T5待办和负结果原样保留。此授权不等于性能目标已通过。新增integration/patches入口保存外部FlagTree可复现修改，NV combinedpatch先归档；GCU需新bounded32实际patch，Ascendpending恢复入口不冒称实测combinedpatch。

**M008恢复状态更正**：用户说明昇腾间歇可用并授权再试。第二轮首个有限probe实际成功，gateway-restore-check2.txt有FLAGPRISM_ASCEND_RESTORE_SENTINEL_R2和container hostname chijin-v35；stderr额外提示不允许npu-smi info，但Docker请求确已执行。停止重复probe，Ascend agent核现有后台任务/依赖后恢复真实构建和M3实现。不能因禁止宿主诊断命令误判整个Docker不可用；也不能因连接成功把未跑硬件改为通过。NV开销继续遵守用户回复保留pending。

## 2026-10-14 / M009：真实边界、代码质量与昇腾恢复

**GCU bounded32验证**：新25case首次24pass/1fail（428.23s），唯一失败为legacy grid0 out_of_range对应Python IndexError，与invalid-value契约不一致。12dynamic+3RMS均真实数学/metadata enable_i64=False/TTIR arith+scf无i64/protocol/count/identity通过，其余9bounds拒绝通过。root将非法维度值异常改std::invalid_argument/PythonValueError，required selected program禁止缺失猜0；最新native11/11 bounds通过（0.04s）。旧失败保留，不宽化测试接受IndexError。新core36native矩阵已36/36、108actual TOPSPTI tasks通过；新增36selected_detail program0/cap64/allsite每case3launch检查原math/input/Y前后32canary/committed record/headerdrops/actual identity，正在执行（逐case900s总90min有限冷编译）。T5随后执行，未宣称低开销通过。测试源码manifest bounded-i32-tested-source-manifest.json，enflame初始state标superseded指向current-state.json。

**实际compiler补丁**：NV integration/patches/nvidia/flagtree-source.patch SHA2568590231de799333ca2e3623daa8dbd7607250e6e499473937277dbf2918df075，baseline57d348b。GCU新enflame/flagtree-source.patch SHA25625eae310e7fdfb43f55a2aec9752c187234b3a0afc8c1558faf13f8ed69889ce，baselineadd842f；bounded dynamic保持原enable_i64 option，旧snapshot路径仍可能开启64bit，二者不混。SDK库只记录hash不打包；旧enable_i64=True patch保留历史不作为安装配方。

**NV实际shared编译与新增CPU**：r12完整core/native成功，新的32bitguard定向31case首次30pass/1fail同上述grid0错误类型；r13 freshnative使用root修正和requiredprogram后32pass/0skip，实际bootstrap是新Debugger native不是Study旧库。编译前后sourcehash一致，证据final-shared-delta-postbuild-r13.json；不得用r11旧hash替代新CPP。Ascend compound行ruff修复后NV Docker真实Asc/CANN/MLIR+execution静态contract37pass/0skip（不含NPU执行）。NVIDIA性能按用户指示保留pending，不新增受干扰测量或终止他人进程。

**质量工作**：远端Docker使用repo固定ruff0.9.1/yapf0.43.0/clangformat19.1.6；71Python AST无错、33CPP+71PY无conflict/privatekey/trailingwhitespace。ruff最初20E701/E702均新Ascend模块，拆分compound行后全Debugger/python+Profiler/python检查exit0，baseline本来无ruff错误。未用旧代码问题掩盖新增lint。格式只新文件full、existing按a7a9aca新增/修改行范围，范围幂等及Python AST等价已验证；root/NV scopedpatch尚待最终两Decoder文件refresh后统一apply。后续pureformat按新sourcehash/actualbuild和实际source-origin微测核验，不重复全部矩阵，更不把格式变化当新机制。

**Ascend恢复真实情况**：用户授权有限重试第二轮首probe成功，原有chijin_v3.5.x容器实际sentinel/hostname通过，无既有cmake/ninja/clang/bisheng任务。恢复读取FlagTree0364ed4、NPU-IR4c304921、FLIR516ad3110cbf6112bbed8f927ae606c627a193f2且依赖tracked-clean。最新含cachecallback/two driver paths的实际combinedpatch已导出integration/patches/ascend/flagtree-driver-handoff-complete.patch SHA256a0d612e6ca1d7d30728c3dec1b901d2a282c8190dc65912248c04a91f8a1ff92；不是先前未执行恢复脚本的假产物。当前core仍baseline待独立commit。SDK实际help确认range replay/MSTX开关可用；正式M3 singleowner rawidentity/clock probe尚未完成。

**新编译负结果与修复**：Asc fresh后台PID4030553 configure成功/build exit1，LLVM22 -Werror,-Wswitch拒Debugger compact decoder未覆盖新增DYNAMIC_TIMELINE enum（restore-build-state1.txt），未到完整corebinding。root新增明确case拒将dynamic套deterministic compact snapshot，并加RejectsDynamicKindInCompactSnapshotPlan测试；不关Werror、不虚构staticheader。agent仅同步这2functionalfix重建并记录snapshotdelta。原负日志保留。此前各backend宽松warning编译成功不等于更严格SDK构建也通过。

**当前终态**：GCU独占device0矩阵/开销，Ascend独占device4恢复构建/SDKproof；NV完成共享编译/CPU检查及scopedformat建议，待root应用后必要freshcompile。尚未formal三review或方法正文，工程仍在推进。首commit654cc91已推送，整体第二里程碑随后按真实freeze/test边界提交，恢复资料与补丁已纳入用户Git工作树而不是仅临时目录。

**M009 Git与格式续**：功能里程碑8a7beee已commit并push至ChijinZ/FlagPrism:detailed-profiler，132文件/约9.4k新增行；提交明确Ascend产品/M3、GCU扩展detail/T5未完成、NV性能按用户保留待验证，不标三后端完整验收。外部compiler补丁只包含公开源码diff及pins；.gitattributes/precommit trailing-whitespace仅针对integration/patches/*.patch保留unified diff空context的必要空格，不放宽实际源码空白检查。root/NVIDIA r4 scopedformat68文件已一次应用，AST等价/范围幂等预验证，通过diff--check；NV agent执行actual freshcompile/27Decoder/CPU和源码origin硬件微测，GCU受测核心未格式化。根命令文档已记录用户明确NV性能延期例外：其余机制和贡献审查继续，但待办/旧超标及受干扰结果必须如实交review，不扩大到CANN正式机制或三后端正确性。

**M009已验证格式提交**：3107c04已push，root/NVIDIA68file scopedformat从8a7beee独立提交；NV Docker r14 fullcore/native39targets构建通过、27/27 Decoder、CPU定向32/32及37/37、Ruff/AST/范围格式全通过，真实CUDA两shape新cache source-origin微测通过。r14记录85/85源码bytes与已发布3107c04逐一hash匹配（r14-style-commit-mapping.json），不是只把commit字符串写manifest。首次Decoder runner PATH缺cmake负日志保留，修runner环境后实际编译/执行27pass。未跑任何新性能实验或重复42矩阵。用户进一步明确允许NVIDIA功能开发/调试、先不跑性能，与现执行一致；NV agent engineering idle，后续必要短功能与公共CI可继续。

**2026-10-15 / 当前继续项**：GCU fullsite GEMM128³两配置实际detail通过，第一case每launch281attempted/cap64/retained64/drop217，全部数学/input/canary/3actualSDKtasks正确；首次SDKllc约7min。IR实际native471行 vsdetail24739行、1321stores/5079calls/414branches，保留编译cost证据，当前逐case900s/整体90min有限上限+watchdog避免遗留无限jobs；完成后T5串行。没有将前2/36当全36pass。Asc actualcore恢复又发现gluon_ir.cc无条件需要AMD generatedheaders，按official amd后端/TableGen配置修构建而非拷header/关Werror，fulltriton继续。M3 externalmsprof-op scope多次真实失败/0range，无receipt不算SDKpass；preferred nativeACLprof singleowner TASK_TIME+RUNTIME_API+MSPROFTX实际成功、range1+device4数学+SDK导出有效。SDKworker线程与caller不同，不按同TID硬join或source SYS containment认证，正在寻找actual SDK/launcher queueflow和tasktoken；正式hidden-only/automaticproof仍未完成。日期跨日后继续同一goal，不重启任务。

## 2026-10-15 / M010：异步SDK worker的实际身份桥（实现中）

Ascend成功native singleowner probe确是实际Triton native_probe_kernel（compiledhash0342c907…），不是Torch数值参考算子。实际source caller TID4047500 vsSDKlaunchworker4047791，SDK MSTX与TASK/rawSTARS有效，但不能通过同TID或SYS窗口猜join。installedCANN9.0正式header包含aclrtGetThreadLastTaskId/aclrtStreamGetId。新技术路径：唯一source request token经versioned PyCapsule→纯C++retain/release context→实际OpCommand worker在原launch返回后立即query(task,stream,device,pid,tid)，publish原rc和值，finalize既有syncExport后drain；无workerPython/GIL、不新增完成同步、不改用户kernel formal。0 task/session/scope可合法，用query状态决定存在。late/cancel/duplicate/epoch等要真实测试。

**所有权与活动**：Asc agent实现CannLaunchReceipt.h/.cpp registry、actualFlagTreelauncher callbackpatch与SDK exactidentity/rawclock producer模块；root Profiler.cpp nativebindings、Session.cpp/h liveactive session check、LaunchHook attr、public finalize/rawartifact/proof调用集成。root已新增make/cancel/drain/supports绑定和activeSessionForProfiler shared锁验证；capsule释放仅release(ctx)，driver需retain确保queued callback寿命。新active-capture bool接口向agent请求，用于区别旧IR-only nativeSDKinactive与正式jointmode，不能默默skip后宣布同调用proof支持。Hook已加入actualascend target+sessionowner capsuleattach与before-launchcancel；这些新代码**尚未编译/测试**。nativebindings后续还需active bool expose、finalize drain/export/proofwire，以及对应真实native registry/epoch/asyncfailure/SDKidentity反例。

GCU当前固定snapshot扩大detail矩阵仍在执行，首次两GEMM配置通过；编译cost大，已经给工程agent一轮有限publication优化授权：先完成当前budget-bound/T5，再独立snapshot尝试真实workitems重复vector16 publisher，w1/w4/w8的真实wordownership/tag/math证据通过才接入；保留scalarcounterfactual，不把减sites当全site通过。拟新llvm::Error setter/metadataactualworkitems，未知不猜。核心共同文件变更前协调NVfreshcompile。NVengineeringidle允许GPU短功能CI、禁止新性能；已经push3107c04且r14 85文件hash对应。

**恢复下一步**：root读取CannLaunchReceipt最终header与agent registry API，补active binding、raw receipt最终导出（保留SDKepoch/path/全部原rc），等actual task/clockproducer后接finalize重建；remoteDocker编译/测试。Asc core正在official amd TableGen之后排查FLIR516ad3引用旧TLE不存在SymmAtOp版本兼容，不关Werror/抄header。CANNhidden-only正式硬件和3noveltyreview均未完成；goal保持active，不因跨日重启。

**M010公共接入续（全部待Docker验证）**：root make/cancel/drain/active绑定与Sessionlivecheck齐；Hook将capsule绑定真实同个LazyDict并在before-launch失败取消；public finalize在native finalize后保存.cann-launch-receipts.json，source-binding要求唯一未拒source scope、实际session、publish1/无late、worker v1/64B/四query+launch rc0/有效PID/TID和非负IDs。0task/stream/scope/session合法；source token绑定不等于SDKtask关联或clock证明，明确分开。_capture保留raw/native/capture.cann-launch-receipts.json（无自动绘制校准时间）。test_cann_launch_receipts.py新增18contract；测试import已用importlib明确module而非package同名decorator。NV engineer同步并真实CPU/NVbuild，另准备直接实际CannProfiler.cpp gc-sections的纯CPUregistry/lifetime/concurrency测试，不能算NPU/SDK成功。

注册 _ProfilerComponent.get_cann_launch_receipt_abi，CMake COPYONLY authoritative C++header至Python输出，agent ascend_launch.py优先packagedheader/editor-source fallback、missing显式拒；generated launcher缓存必须纳入实际headertext。helper3资源contracts等待Docker，wheel打包*.h还需真实确认。Asc SDK网关此后又连续3次tar/text读取失败，仅gateway文字（gzip校验拒绝）；停止盲SSH，没有重开jobs。fullcore已经真实失败于未pin FLIR新API/oldTLE Symbol，待official兼容revision；actualdriver source可从official immutable0364取得但远端patch前必须核SHA，SDKwrapper特殊差异不能猜。

**M010实际质量回归进展**：NV Docker最新r17完整native13targetbuild exit0，新ProfilerNative b1716fd0…（仍非最终源码冻结）；新公共CPU176pass/3browser skip，含18workerreceipt、3headerresource以及portable/launch/rollback/reconstruction/原定向32/37集合，计数按此次实际pytest不累加历史。完整actualCannProfiler.cpp独立-ffunction-sections/linkgc纯CPU17/17=registry14+ProfilerBase启动恢复3，无实现抽取/SDKstub、不是SDK/NPU采集。14覆盖零IDs/query与launch失败/错ABI/重复/取消/晚到/epoch-session复用/保留callback寿命/32worker/concurrentclose和有限4096epoch-cap恢复。Base3验证原异常/失败后retry/idempotence/restart/reentry。actualNVDocker compiledguardFalse检查PASS，四CANNcapsuleexports不存在、不制造scope或phantomSessions；packagedABIheaderbytes与canonical一致。该回归验证公共集成不破坏NVIDIA，不验证Ascend实际driver/SDK。

启动恢复还补两项：C++Session.activate成功后才标active，防未注册interface因failedstart被逆向减计数；_native.start内部activation抛错时先finalize/remove nativeSession/path再重抛原error（Python此时尚未拿SID不能清理）。CANN doStart新RAII在SDKstartsuccess后Registrybegin失败/0时清理SDK/MSTX并明确抛错，不把资源耗尽记作正常inactive。CPP/资源生命周期所有新变化需最终sourcehash回归，不能称旧r14库验证了这些新机制。

**GCU scalar实测结论**：原native36/36；扩展allsite detail6个GEMM配置通过，首融合GELU128³v0 SDK llc900s超时exit124，实际有限评估62.35min，原请求未缩、超时子树已清理。新Falseone-store T5三批×30实际native116.6095/117.03/117.209us、detail120.772/120.63/121.02us，+3.57/+3.08/+3.25% device-task；host仍5.18–5.23ms、stream5.24–5.29ms，不能称端到端≤10%。off缺isolatedtask，native≤5未认证。授权有限新vector publisher独立试验：4fileexactpatch接canonical前通过applycheck，保留scalarlibs/sourcehash；实际workitems形状、64B/tag/ownership/math w1/w4/w8及同JIT共享cache scalar→vector→scalar必须验证。publishermode已进入真正pre-JIT-cache instrumentation_mode JSON，独立CPU2tests通过但不能替代hardware/cacheoracle。default仍scalarcounterfactual直至vector实际有效，原GELUfullsitetimeout不能被toy成功抵消。

**M010后续硬件与接口状态**：GCU vector共享同JIT/cache三相scalar→vector→scalar w1/w4/w8实际3/3（100.83s）通过，first=thirdHash/LLVM、vector不同；unknownmode真实ValueError。独立实际GCU SSA ownership3case审计：actor0拥有16distinct indices，memref有效16、scatter_count16，内部vector128寄存器不能称128都写；真实mfence296→100、dma_wait339→115、barrier0→0，无新增observer barrier。vector完整dynamic/RMS15/15（369.41s）通过，scalar仍默认。原GELU fullsite/cap64/input/config/canary/3launch同case正在vector重试，900s上限不变；未提前声明全36通过。

Ascend cann_joint.py exactSDKtask producer新增5CPU合同（未在Docker跑），只实际workerID/TASK/HostTask唯一连接，不把SDKconvertedtime作为SYS域证书；SDKepoch→实际PROFdir因果seal正在Cpp落地，Rootdrain已加sdk_capture_path/sdk_capture_binding_status/sdk_capture_binding_evidence JSONstr。必须explicitseal合法实际目录/evidence，不接受调用者任意capture_root当proof；新增wrong/old/missingseal等反例待补。CppWorker64/Sink80 ABI未变，Receipt内部字段变需新freshsourcebuild。旧176/17CPU和formatter4ownedpatch是preseal snapshot，暂不apply，待最终stableapi/hash刷新。workerdriver installer尚未在Asc机器应用/核SDKSHA，hidden-only/clock仍未完成，三个formalreviewer尚未启动。

## 2026-10-15 / M011：按用户指示先完成功能、保留性能边界

用户明确允许Pro6000 GPU调试/开发，暂不跑性能；不终止他人进程，不以外部占卡作为功能工作的阻断。NV agent已恢复新快照fullcore/native build、actualCannTU/SDKseal与commonCPU/formatter验证。此前r17不是新source全部通过。

GCU vector原同输入GELU128³-v0/allsite/program0/cap64实际PASS360s，3真实task/192retained/711declared drops，mathmaxabs5.96e-8/canaries/False通过；原scalar相同请求SDKllc900s timeout保留。vector单GEMM231s亦数学通过，但该单例命令遗漏canonical inputdir，input_hashes[]，不得当同输入配对；统一vector36全family矩阵将explicit canonical inputs下重验该case。vector SDK LLVM34074行vs保存scalar20687行，不能宣称普遍缩小生成代码。统一vector36每case900s/整批5400s，失败保存LLVM/exit且清理自己进程组后继续，不缩sites、不重试掩盖失败。

vector one-store29 controlled3×30 T5实测detail148.958/148.733/148.6645us vsnative117.337/117.5995/117.472us，+26.95/+26.47/+26.55%；scalar相同请求+3.57/+3.08/+3.25%，故scalar默认不变，vector显式编译可行性选项。两者host约5ms，均不能称端到端低扰动；所有270调用math和90trace通过不等于性能达标。原证据vector-gelu-fullsite-audit.json、t5-i32-vector-controlled-audit.json及完整tar留在artifacts/method-run/enflame。

Asc SDKseal/provider稳定：native SDK init前/stop-export后完整扫描，唯一newPROFdir、实际collector PID/device、owned root和metadata snapshots作为因果seal；缺/旧/多/不同PID-device不按latest猜。cann_joint exacttask producer现13 CPU合同待Docker，clock永远unverified，worker ABI64/sink80未变。Root补public成功nativefinalize后的.cann-task-identities.json自动producer调用，只unique sealed ownedroot，missing/multiple显式unassociated，invalidproof错误不隐藏，bundle raw/native保留。新增4导出合同待Docker；这不意味着actualAsc driver或SYSclock验证已成功。

**M011正文与环境推进**：按实际当前实现写入唯一paper/sections/04-design.tex（三机制）与05-implementation.tex，不新建tex副本；未完成的Ascend hidden-only/actualworker/end-to-endSDK identity/rawclock和最终版本冻结继续显式TODO，不将实施设想冒称验收。make paper最终exit0，main.pdf8pages；现有float-onlypage警告保留。尝试本地渲染审页因pdftoppm/fitz均未安装不可用，没有安装本地依赖，PDF视觉审阅尚未完成。

Ascend本轮有限retry实际sentinel+chijin-v35成功。actualworker driver/shim已安装到独立0364source（3files78insert5delete），新SDKseal/rootbindings/Session/startrollback真实Asc Docker nativebuild exit0，_native423a1c…，尚未验证actualworker运行。新sink80static_assert刚追加需重build。FLIR unpinned516ad3(2026-09-17)与FlagTree0364(8-13)TLE不兼容，定位8-20引入SymmAtOp依赖；正在尝试官方历史ff91e64b6042a27e0db053f28ea3741be65d24d0(8-03)独立dependency revision，不关闭feature/WARN。SDK rawACSQ_TASK_FMT=4HQHH11L第4field为task SYS，仍需核actorlogger计数器同域，不能由task窗口推actor成本。

**M011质量入口补缺**：检查正式Profiler/test/unittest/CMakeLists仅TraceDataIO，新增CannLaunchReceiptTest/ProfilerStartRecoveryTest此前只由artifact独立runner运行。已要求NV工程agent接正式可复现CMake目标（或确有平台限制则版本化runner与命令），实际wholeCannTU/function-sections策略不得实现抽取或SDKstub；新增SDKseal字段/错epoch/close-drain状态合同。先前17CPU证明仍有效但不冒充已注册CI。

**M011审阅原文包补充**：取得作者正式LLVM25/HPCA25演讲PDF（不是CGO全文），保存prior-work/proton-author-primary-sources.json及两PDF/hash。LLVM25 pp5--9已有跨平台/自定义metrics/Proton+ProtonGPU通用到target lowering，pp11--14已有sampling/granularity/circular records，pp15--17已有producer-consumer intra-kernel pipeline及compiler关联；HPCA25明确NVIDIA+AMD。故共用多backend接口、细粒度插桩、动态buffer和流水线图本身都不可当新增novelty；需要具体映射/语义/identity-clock机制和实证差异。会议officialCGO preprint新URL实际HTTP404；不能以slides未提某功能证明全文没有。正式review包将包含该比较边界，尚未启动formalreview。

## 2026-10-15 / M012：实际恢复核对与全矩阵终态

恢复时发现旧Asc工程agent已不在live树，NV/GCU为pending_init；已恢复两角色并新Asc接替角色，先查既有进程而非重复启动。NV实际SSH/Docker可用、无ownedbuild/pytest在跑，只有r17成功终态，r18从未启动；前轮“正在回归”仅为已派发工作，不能当实际运行证据。现补SDKseal C++3case/CMake并准备formatter后才启动r18。

GCU实际controller终态EXIT0，36executed/36passed/0failed/0unexecuted，总4251.0187s（70.85min）；无own controller/llc活进程。全部六family3shape2config、canonical输入/allsite请求未缩。工程agent正提取原始archive并独立audit math/meta/input/binary/SDKidentity/drop，尚不把agent口头36pass替代原始审计；审计后format及freshfocused回归。无新性能。

Asc新工程角色接手actual core5 PID4093490与official FLIR ff91候选构建，需先查真实终态。新role=method_ascend_resume，旧method_ascend_native非当前live。三formalnoveltyreview尚未启动。

**M012 root审计与真实新验证**：root顺序读取84MB原始vector-full36 archive，独立核36唯一case=6family×3shape×2variant、记录原CPU pre/postpass/输入immutable/canary/固定allsite-program0-cap64/False，108rawbase64 bytes逐份SHA一致，4599observations/21996declared drops与原结果和agent审计一致。保存root-vector36-artifact-audit.json，archiveSHA f31414ea2728927c81e99cb463570cb5144a3908403333450170ecd8403ce808。该离线复核不在本地重跑CPU参考或设备测试。

NVIDIA r18实际fullcore/native17targets exit0，新正式CMake CannLaunchReceiptRegistry实际CTest20/20=Registry17(新增3seal状态机)+Base3通过。公共CPU实际193passed/3browser skip exit0（含22receipt+13joint），不是预期计数。真实FlagTree bdist wheel复用已编译库zip检验header与source/CMakebytes一致，isolated helper+header离开sourcefallback可用；zip/headerSHA和script_name初次失败保存在wheel-header-r2-result等。Ascend格式仍待core6终态，当前r18为functional preformat-CANN source，不伪称最终全部hash。

ROOT5固定formatter在apply前/后精确核每filehash并gitapplycheck，5/5成功。GCU15file候选已由owner apply并freshGCUcore（Passes/Bindings/link）exit0，DebuggerNative/ProfilerNative实际输出/overlay核验。最新合并contracts/API/realEnflame/bounds247pass/5skip（4browser+1CUDA/HIP-specific旧hookskip），Decoder新27/27。硬件focused9仍在执行，不重跑无新语义的整36矩阵。GCU默认scalar，不自动切换；explicitvector可用但扰动更高。

Asc core5终态1后仅新增ASCEND oldCTALayoutAttr API兼容分支，num_ctas/selector与其他backend语义不改；core6 PID160340实际184/274，无新错误，新失败对象已通过。native_receipt_smoke正式public4launch/2binary/2streams runner已写，尚未执行，不能计硬件支持。真实SDK StructDecoder前缀'='，stars_soc_profile混合records，不能把前128B全局套作actor128B schema；raw clock producer仍独立缺口。

**M012正文与视觉验收**：06-evaluation.tex补已审计GCU36boundedtrace与scalar/vector受控成本，显式区分regression/预先RMSheldout和全部待验收项；04修改避免把每backend均断言统一commit-marker格式。make paper exit0；本地无renderer，按远端Docker约束独立安装PyMuPDF1.26.5到/workspace/chijin-paper-render-lib（初venv缺ensurepip失败保留，不装宿主依赖），实际渲染8pagePDF（SHA c9bb68213fddcdbb2f43c221e5768d3021bac4792e3e3ed15091ca1282f5cbf6），root视看pages5/6/7，学术双栏文字/图无重叠裁切，TODO均明确可见。保留现有latex floatpage警告，但page5实际有figure+bodytext，不误称PDF纯空白。无undefined refs/Overfull。阶段记录/脚本/渲染图位于artifacts/method-run/paper，不新建tex副本。

**M012 Git里程碑**：核GCU15文件当前SHA与owner afterhash精确一致，选择仅15GCU功能/格式源及8份immutable JSON证据，gitdiff--cached--check通过，commit c207f6e5f2c511ef5c20f6a25e67a4c106f077c5（23files）并实际push detailed-profiler exit0。证据目录integration/evidence/enflame-publication-20261015；不包含SDK bc/库或大raw；保留defaultscalar、vector高扰动、clockunknown等边界。CANN/公共身份桥及论文最终快照仍未提交，不假称root论文随此commit。

NV r19实际最终CANNformatter增量build exit0（5targets，actualCannTU/native/registry），CPU193pass/3browser skip、formalCTest20/20、Ruff整个Python包及scopedformat/AST/whitespace质量通过；短GPU功能PID68785/Decoder27/newheaderwheel复核尚在执行，禁止性能。Asc fullcore实际libtriton4fa158e2…已核实位于compiler-build，native23targets/latepass编译exit0（Profiler73f70a31/Debuggerfa0247db/Late6acb4f2b）；core6脚本尾sha路径错误exit1原记录保留，不能抹成job0，但实际编译链接经实物hash可证明。当前正在contracts+4actualcall worker test，尚未pass。

## 2026-10-15 / M013：按用户要求完成功能、原始记录生命周期修复

**用户授权**：NVIDIA占卡不阻断调试/开发与短功能验证；性能实验先不跑，不干扰他人进程。

**实际新证据**：NV r19短GPU native/multistream/nested/CUPTI、selected program/overflow、source-origin257/513/different binaries通过；正式CTest20/20和Decoder27/27通过。r21容量修复实际编译新的DebuggerNative6118c720…后11/11合同通过，448源文件pre/posthash一致。r22解码失败原始buffer恢复2/2及既有193pass/3browser skip通过，最终449源文件hash8c59e123b7f86c1ba08102c01e39a6dc31a5257eaaba13ac547f35cb34fb015f；168Python AST、包Ruff与改动范围固定格式通过。无NV新性能。

**容量与失败恢复问题**：Asc每actor256请求应分配3*(32+64*256)=49248B，但postpass metadata.update把总capacity覆回256而得到16416B。ROOT改compiler postpass setdefault保留派生ABI，Bindings在分配前校验3*peractor+1、64B及对称layout，拒绝旧ABI而不尝试危险kernel。Asc真实native新库244bc4a6…/11合同通过，实际零buffer分配49248；随后hidden2真实Softmax32×256四调用数学/input/canary通过、32动态事件，AIV actor1/program0，tick instance_local。另修native finish释放设备buffer后decoder抛错丢raw的问题，保留raw/error+decode_failed、屏蔽伪解码事件并在重建HTML提示，原始异常不被secondary handler错误覆盖。以上源改动尚未Git冻结。

**Asc实际worker与新core**：官方历史FLIR ff91e64b…与0364旧TLE兼容后完整core链接libtriton4fa158e2…，原core6尾部sha路径误写导致exit1保存，实际build成功实物已验证。新增standalone opt正确include/link后native-r3正式四调用/两binary/两stream通过；实际worker thread/task0合法，SDK TASK+HostTask和sealed capture绑定4/4，时钟仍unverified。native-r3 archive及source/native manifest已保留。不能把4proof等同跨actor时钟对齐。

**新发现和当前修复**：default hidden2最终SDK taskproof全部unassociated，原因native Session finalize在Python producer前remove_all临时SDK root；显式output的native-r3不触发故先前没有暴露。ROOT已把native改为deferred_to_python_bundle_export、retained=true，待Asc真实重编译/默认路径复验。新增cann_artifacts helper先复制SDK session所有文件与逐份SHA，再完整bundle后验证copy才清理owned临时session；显式用户路径不删，导出失败保留源。ROOT接_capture；helper与roundtrip合同由GCU工程agent在Docker验证中，尚不记通过。

**M3公共报告缺口**：现native-r3四task legacy视图有6kernel行且task0变unknown、缺source关联，raw proof存在还不是完整服务。ROOT给cann_joint additive输出当前sealed capture ids、全部TASK inventory与唯一HostTask候选；NV工程agent实现cann_native以真实SDK身份生成canonical task并严格去重旧view、typedzero/directinvocation报告与负例，不按名字/顺序/时间猜。Asc工程agent独立实现实际ACSQ SYS anchor producer（clock仍unverified），MIX与共同clock尚需实证。三正式novelty reviewer未开始。

**当前分工**：ROOT Session/_capture/cann_joint/记录/Git/正文；method_nvidia_native cann_native/_report/新tests；method_gcu_mapping仅cann_artifacts与新tests；method_ascend_resume rawSYS producer/Asc driver与真实device4。旧method_ascend_native不是当前工程owner。新文件/SDK生命周期修复均待真实回归，不提前算完成。

**M013小里程碑**：容量保护三文件与r21实际sourceSHA逐份相同，保存正式integration/evidence/observer-allocation-20261015证据后提交c659eec（5files）并push成功，未连带提交待验CANN/report。cann_artifacts最终40新case加现有portable/report总144pass/4browser skip（GCU Docker CPU，无新GPU）；新两文件固定formatter/Ruff通过，实际temp/nontemp/publicexport/末端manifest与reconstruction失败保源覆盖。发现outer manifest误排除所有basename=manifest.json的SDK嵌套文件，已交NV report owner修为仅排除根manifest。Asc Session延迟cleanup增量native实编exit0、新Profiler896b9c4b…；default hidden新复验在跑。原始时钟producer与canonical source关联仍进行中，未记完整通过。

**M013默认SDK复验进展**：Asc hidden-r3实际exit0，数学maxabs1.39698e-9、32动态记录，修复cleanup后4/4 taskproof均verified_task_identity。此轮远端尚用旧scope-only report，不能计完整native报告贯通；默认SDK根仍保留，等待新版canonical/retention正式入口复验。新ACSQ producer11合同初步通过但真实文件func26/28，传统0/1端点不适用；按已安装SDK定义继续研究，不能编造端点或共享域。论文当前04/08更新后的实际make -C paper paper成功9页PDF SHA49057f0aaf84bb158060f737b3d6025a7a37e787bc831afc489d9134a5c8caea，无undefinedrefs/Overfull，既有floatpage5警告保留；新九页尚未视觉复审，不冒充旧八页的审阅结论。

## 2026-10-15 / M014：公共TASK报告、rawSYS与导出恢复

**已核证**：NV Docker cann_native新40合同及既有report31合71pass/1browser skip；正式builder读取实际native-r3 SDK与receipt后4TASK/4source/2binary/2stream，2个合法task0，6legacy导出view经完整inventory唯一tuple去重，原row/source/index保留。ROOT独立读canonical-document与events核计数及clock仍unverified，保存cann-native-audit-r23-r2/root-independent-audit.json。新module只按installedSDK RTS_TASK_TYPE_MAP五个exact kernel类分类，数字TASK.type保持opaque；非kernel/unknown保留unclassified，unknown_fields mask优先。

**rawSYS实际数据**：Asc producer实际SDK schema六sourcehash，stars_soc.data.*才是64B ACSQ taskchannel（stars_soc_profile26/28是PMU采样，首轮错误日志保留）。actual native-r3与hidden-r3均4/4 unique原SYS start/end；hidden-r3 source区间在预先独立task身份绑定后落入对应task envelope，作为sanity而非身份选择/共同offset证明。11rawSYS+8acceptanceexactidentity共19合同在Asc Docker通过；新schema discovery按实际installed alias去重且缺/歧义拒绝。acceptance修为invocation+binary+retainedproof，不再scope truthiness排除0；主矩阵六族36，RMS单列heldout。

**正式服务接线（仍待combined验收）**：ROOT在profile任务producer后自动导.cann-raw-sys.json；已安装SDK缺/unsupported schema显式unavailable且不擦原生身份，unexpected错误仍失败。增强receipt测试三param验证这条边界。_capture先canonical native再analyze，原始SDKtree经helper保留，全局manifest仅排根manifest，不漏SDK嵌套manifest；原.observations.json保raw，ai可附局部rate并重建；只在完整bundle完成后允许清理temporary owned session。显式relative SDK root改为start时absolute，支持app正常chdir，待真实相应smoke。

**新发现的真实恢复缺陷（正在修）**：GCU只读CPU复现finalize已结束ID变KeyError、native observation take先drain后sidecar解析/写失败丢raw。授权其修peek→durable owned recovery journal→atomic sidecar/fsync→精确ack，失败保原队列及可跨进程读journal；未知finalize no-op，samecaptureID不同payload冲突不得去重。ROOT另读出nativehook decode_proton_ring失败在append前丢raw，交同owner补raw/error留存，不输出伪执行事件。均尚不记通过。

**局部rate与offset分开**：官方GetSystemCycle A2 50MHz/PIPE_S文档，实际c220 GetSystemCycleImpl与adaptedLLVM均MOV SYS_CNT，capture hwts_frequency=50.000000，支持有完整source/native/compiler证据时局部duration换算，不能证明跨actor零offset。Asc owner新增cann_source_clock/test，计划函数copy-return严格重核actualtask/receipt/binary/LLVM/header/deviceinfoSHA/target/rate，仅tick_ns与duration_ns，alignment保持actor_local/instance_local且不设absoluteorigin；缺证据保持unknown。新module与真实r3正例/负例尚在实现。

**质量冻结进展**：ROOT apply r23 fixedformatter两file前后SHA精确；Session最终a25bb766132b19d8e8aca4129da668d346ea7c4a02481a7cfc5407497ae66cde，testreceipt3e02194ff036381f0b95fd0b626a1b5bde51f983d8f91f4bbaf596acf2ccd447。NV/Asc将据此增量nativebuild；GCU-owned profile/hook及Ascsourceclock纯PY待freeze再共同CPU质量与一次短NV功能，不跑性能。三正式OSDI reviewer仍未开始。

**M014新验收结果**：Asc cann_source_clock最终15/15（新增已独立shared-clock原样no-op）及actual hidden-r3 32/32局部rate通过；最终module f9c2048c4d672995561e3e3cbe66bf185355db18cc81cd27cf3a2ded3e3f754f，原32输出JSON SHA21dfedf…，ROOT独立逐event核tick/rawrecord/invocation/actor/site/occurrence不变，duration=(end-start)*(1000/actual50MHz)，无origin/shared升级，root-audit已存。NV final Session实际build0，251 C++/header/CMake source pre/post一致，ProfilerNative73cadbefc0b4412b2e319ff4970dd751684e5fdf9dab49b8ab393dbad2c91634，Ctest20/20及Decoder27/27通过。Asc同Session实际build0，ProfilerNative893fc61b…。

**M014恢复补齐**：GCU nativeobs恢复最后扩展native finalize/launch snapshot/taskproducer早失败三case：17new+40helper+既有portable/report总161pass/4browser skip，原异常cause、跨进程可读原bytes、失败stage留存且无假bundle均过。原nativehook截断decode异常也保raw、原exception，不生成observations。当前profile/hook/newtest待NV固定fmt候选由GCUowner apply后整体CPUfinal；ROOT及NV/Asc不抢写这些ownerfile。

**下一设备门槛**：Asc已准备native_receipt_smoke可选relativeSDK+start后chdir正式四call测试，runner新格式候选待ownerapply；源码全部freeze后完整sync，先default hidden-r4(4canonical/4proof/rawSDK/rawSYS/localns/origrawobs)，再relativepath/chdir，再小GEMM+Bias+GELU MIX，才36主矩阵/RMSheldout/Study正式case。NV最终commonCPU+一轮selectedrequest短硬件功能，禁止新perf。Asc source_op_id在旧row smoke实际全missing，M1不冒充独占源操作归属；MIX将实际审计mapping层级。轮到贡献审阅时必须给出这一限制。

**packaging实际未决**：Asc bdist old0364 setup offline manager无条件读取NVIDIA ptxas-blackwell JSON不存在key，metadata KeyError原失败保存。可做仅Asc不构造无关NV dependency的隔离官方hook兼容，不能关闭offline/虚构JSON/下载无关CUDA作为捷径；先r4/MIX，wheel随后。NV旧actualwheel/headerisolated验证仍有效但不能冒充Asc wheel通过。

## 2026-10-15 / M015：最终NV功能通过与实际Asc报告分类缺陷

**NV阶段通过**：最终共同CPU实际336pass/4opt-in browser skip，463source SHA01684692deaff1eaa8784b47d40c576fcbcf771ac52be34cd0f8fac88d329e15；加载Profiler73cadbef…。一次selectedrequest/overflow实际GPU终态0，program0/1/99/overflow/cache/CANNguardFalse、peek→save→ack→bundle通过，无性能比较。继承acceptance.py88格式诊断保原log，仅本轮changedrange检查，不借机改baseline风格。final质量额外发现漏格式CTA兼容CPP/launch receipt patchhelper，ROOT按精确pre/posthash apply，CTA最终ba02c06e…/patchhelpera24be6e…，后续小core重链；此前功能证据是pre-extras格式，不伪称新core已经做硬件。GCU格式后161pass/4skip，9小证据文件22802B已准备integration/evidence/cann-retention-recovery-20261015，尚未stage。

**Asc hidden-r4真实完整路线**：数学/input/canary通过、32动态事件、4/4canonical独立source身份、sample3/3严格匹配、4rawSYS、32局部duration且instance_local/noorigin；原raw observation+完整SDKdb已保bundle，默认retention完成。完整archive40b4f47e01f2453918f9d59eb7b063c37a89c4aeac9c5cd1f737c900338cde82已下载extract。relative+r4运行确有4worker/4nativeproof/绝对原cwdSDKpath，但新runner把collectorpath错误当用户root，忽略session子目录，在math前assertfail；原fail保留，仅修测试并fresh r5重验，不能记整轮pass。

**发现需修的真实分类bug**：r4主报告除4canonical还保留14legacy kernel，已严格SDK inventory核明不是4kernel重复，而是8 PROFILER_TRACE_EX、4 MEMCPY_ASYNC（raw TaskType PCIE_DMA_SQE/device-to-host/49248B）、2 EVENT_RECORD。legacy C++importer以args.contains(Task Type)当kernel（CannProfiler.cpp1421），会误计热点。NV owner正在cann_native新增normalize_legacy_activity_kinds，按明确SDK原TaskType分类而非name/时间/顺序；ROOT_capture对所有CANN document无条件先调用（包括无sourceproof），拷贝原raw不改。copy应变memcpy，marker/sync进原生扩展并明确counts/reason，不当kernel热点；unknown类型不猜kernel。需actualr4原bytes离线publicbundle regression+negativecases，不为纯分析更正重跑内核；小MIX随后用新正式pipeline自然验。

**当前恢复位置**：ROOT停止其它源码修改，等NV normalizer功能/格式/CPU；Asc当前relative5 runner修正后测试（不在job运行时换core），需先CTA纯格式core增量，再新MIX。NV新增normalizer+new tests会使原463source快照成为前阶段，不拿旧336替代新回归；不重跑已通过数学GPU，除非新代码确有影响。新CANN里程碑Git仍待最终公共分析与Asc小MIX，正式三reviewer未开始。

**M015最终core同步纠正**：Asc只同步PY/test时也带入CompilerBindings.cpp新GCU publication函数而旧include/lib未同步，CTA纯fmt增量首次exit1（CTA本身已过），原failure保留；完整canonical Debugger include/lib补齐后只重编CompilerBindings/Passes并actuallink exit0，新core4eb0684188f8e7bd55221d54d073dab4ac667430d5867ffbed64ba68d30a281d。接续native一致性与原6hidden/11capacity门槛，不能混用新binding/旧header或把旧4fa core证据标成新core。14legacy原SDK exacttuple audit14/14唯一HostTask已机读hidden-r4-legacy-summary.json佐证，全部真实非compute，非重复source。

## 2026-10-15 / M016：阶段Git里程碑与MIX上下文关系

**实际commit/push**：ROOT精确核r24 canonical463源SHA全部一致、最终共同346pass/4browser skip、固定format/Ruff/AST完成后提交0ef0adf（61files），push实际成功；新增public-single-task及retention-recovery工程证据，明确MIX/nativeidentity/fullmatrix/clock/wheel仍pending。历史pytest负log原bytes含尾空白，Git证据改lossless gzip并原SHA验证，artifacts原log不动，不关闭全局whitespace；去掉重复quality JSON/log。没有SDKheader/DB/版权PDF/大raw入库。论文仍唯一workspace paper正文，最终snapshot尚未冻结。

**实际MIX数据**：原gemm_bias_gelu128³variant0/math maxabs1.34e-7/input/canary通过，232动态记录=192AICslot0+20AIVslot1+20AIVslot2；两实际LLVM actor module cube/vec，static sites24/27、dynamic16/7，全部source_op_id/debugorigin缺失，M1明确partial。taxonomy正式路由kernel4/memcpy4正确，marker/sync不入kernel热点；但当前四proof均unassociated、source localrate未知，所以不启动长矩阵。

**SDK真实结构与修复方案**：四worker同pid236634/tid236766/dev4/stream3，task1/4/6/8，SDK connection23/57/84/111。每call有2HostTask/context_ids UINT32_MAX与0、2TASK/contextId对应；旧joint只按connection/stream/task找peer因此2拒绝。installed SDK cann_analysis_gear.py::get_context_ids明确MIX类在默认UINTMAX外加0，COMPUTE_TASK_INFO按globalTaskId外键识别唯一compute context0，blockNum64/mixBlockNum128；另层dispatch envelope，三个AIC/AIV属于同compute context，不能把两层当两kernel相加。证据mix-context-rows.txt/sdk-context-join-source.txt，基于SDK结构，不用名称/时间挑。

**当前ownership更新**：method_ascend_resume现在获授权own cann_joint.py/test_cann_joint.py及cann_raw_sys模块/tests，先提出schema后实现严格context join+compute membership，v1兼容恰1compute成员native=该task，保完整dispatch/context证据；多个compute先明确compound/unsupported不任挑。UINTMAX在普通AIV可能本身compute，不能全局排。method_nvidia_native被followup恢复，own cann_native/_report/其tests适配、parent/context扩展不计kernel热点、新MIX实际SDK离线publicbundle与单task兼容CPU，不重NVGPU/perf。ROOT不再写joint，处理协调/Git/正文/审计。rawACSQ无context只证明whole_dispatch envelope，不能伪作computechild/actorwindow。

**额外真实性检查**：ROOT独立校验hidden-r4 bundle retention116原SDK files逐SHA+size一致、4exactproof/4rawSYS/32actor-local20ns/ns数据；旧主报告taxonomy误标14已在audit中明确，新r24 CPU公开路由纠正不伪称重新kernel。relative-r5实际完整数学/inputs/canaries/四call两binary两stream+chdir输出路径通过，6hidden+11capacity门槛也在new4eb core通过，实际正确49248零allocation无kernel。

**审阅原文补齐**：PASTA全文primary arXiv2602.22103v1 HTML已本地archive SHA d9b1dd85…，III-G明确semantic/timing normalization/vendor-specific handlers皆既有设计，不能称新。Proton CGO全文有限8组primary来源未得；作者页无PDF/DOI工具不可达，slides仍非CGO全文，不据缺全文推断缺机制。小JSON记录在prior-work，版权原文不push。三正式OSDI reviewer仍未启动。


## 2026-10-15 / M017：用户确认NVIDIA功能优先；MIX上下文身份闭环

**最新要求**：英伟达显卡可继续调试/开发/短功能验证，性能相关实验先不跑，先完成功能。沿用现有Docker，不终止他人进程；不把旧受干扰性能算新验收。

**实际进展**：Asc strict context/COMPUTE_TASK_INFO FK producer的24joint+11rawSYS共35 Docker合同通过；原MIX-r1 SDK bytes离线恢复原seal路径后4/4 verified，各保留两个contextview，唯一compute globals0/1/2/3；NV consumer对同一真实包4source关联通过，初步98pass/1browser skip。仅离线分析修复，未称fresh硬件r2通过；完整candidate还包含marker/copy，不假设8总数或2binary。两次新增fixture错误oracle失败日志保留。

**当前功能问题**：rawSYS原拒绝MIX文件，已查installed StarsCommon bit13非expand模式会swap stream/task：encoded stream0x2001/2004/2006/2008和task3实际对应stream3/task1/4/6/8。Asc owner按官方stream_expand_spec及芯片分支扩decoder，不盲mask；ACSQ无context只能whole_dispatch，不能作computechild/actor窗口。ROOT独立LLVM审计只有AIC SET.CROSS.CORE(10,33)→AIV WAIT.FLAG.DEV.REG(0)单向边，其余flag为intrapipeline，不能假定双侧causal offset。

**receipt恢复与回归未决**：GCU owner在native drain后、LaunchHook snapshot前保原receipt+SHA到owned atomic/fsync journal，失败有路径，成功sidecar落盘才删journal；局部44pass。NV全common r25真实369pass/4fail/4browser skip，4fail是Py3.10 fallback包装RuntimeError改变原异常type/object，与既有负例不兼容。已要求保原异常直接raise、路径用stderr/属性，原失败日志留存，不放宽oracle。新的最终公共CPU尚未通过，MIX/journal暂不提交。

**正文**：04-design以SDK context membership+compute表外键说明唯一compute关联/多compute保留未绑定，default SDK retention/report已实测不再留过时TODO；05明确hidden-r4的四任务/32局部duration，但fresh融合及全矩阵仍pending。此轮文本未新build，不用旧PDF冒充。


**M017最终功能里程碑**：NV最终382pass/4browser skip；最后rawSYS官方StreamExpandSpec表增量53/53（未重GPU/性能），464source全部与canonical逐SHA相同，aggregate62429a678a07bdbef5a393fa04b913a91c9e8178a97142a7e29737631e1b9d64。181AST/42pinnedformat/无新增Ruff，原88继承diagnostic留存。Py3.10原异常包装已修，测试未放宽。提交42bd4ae496b21afe981d93c5a349f2c2239f7382（18files），push成功且ls-remote精确匹配。wheel未验patch未连带commit。

**fresh MIX-r2实际成功**：数学maxabs1.3411e-7/input/canary通过；4canonical compute/4copy/4exacttask/4whole_dispatchSYS；232动态=192AIC+20AIVslot1+20AIVslot2，全部20ns局部duration，仍instance_local、源码originpartial。ROOT独立逐151manifest/118SDK文件SHA+size一致，232raw identity/ticks保留、duration公式全一致，audit已随42bd4ae入Git。完整archive9550b1c8bfd2ed6d92c6224a5f0291a30c9c1fdc5bbfbc99af1a2df0e85b9c91保workspace未入Git。MIX原包和fresh都只有1binary/1stream3，另native smoke2binary/2stream是独立证据，不混为一轮。

**当前活动**：Asc full-functional-matrix PID262120六算子36配置×off/native/detailed=108请求，随后RMS/T5；已至少15请求过无fail，恢复先查terminal不重起。长KStudy512²×4096三配置正式入口需矩阵后补。wheel-r2已terminal1（setup试图FLIR重建），不能声称wheel通过；限定repack复用已编库继续修。Asc原始counter数值与dispatch envelope相容的sanity不是共享时钟证明。

**正文更新**：Intro不再留“选择新IR/未来机制”的过时措辞，按实际manifest/typed instrumentation/identity reconstruction写清并保贡献/运营经验TODO。04/05已补fresh融合实际记录及局限；这些最新修改未新build。上轮make paper实际9页成功但不等于当前文本PDF。


**M017正文构建/图形核查**：最新Intro/04/05/08实际make -C paper paper成功，9页PDF SHA471bf0ff35af7578ba40822ed975234e1085737f7e0162309dfb2e6774de826c，无undefined/Overfull。复用GCU Docker既有PyMuPDF1.26.5 CPU渲染，ROOT实际查看第6页双栏方法排版无重叠/裁切；不将单页查看称全稿最终视觉审阅。build/render证据在artifacts/method-run/paper/*m017*。官方OSDI27 CFP于2026-10-15重新查验：Operational Systems不要求新研究想法，但仍需系统设计/分析/经验和公共知识增量；当前研究机器测试不等于部署经验。review packet仅preparation未冻结/未启动formalreview。


**M017用户文档与provenance澄清**：ea5ced1补既有semantic_profiling.md公开API/CLI、backend/hook、三机制产物、raw/ai/report与journal失败边界；1c5edc5将旧CANN最小适配验收页标为历史记录，不改历史结果。两docs commit ea5ced1/1c5edc5已实际push成功；仅文档，不改变已验runtime。GCU agent只读证实搬移完整bundle仍可读已有HTML/ai，无需原SDK绝对路径；不存在公共read_bundle()，重新生产proof的原seal约束不是跨路径读取既有结果。未扩无关离线重建功能。

**selection维度澄清**：原api.py selection_stage=semantic_output_filter_after_capture对于语义类型确实成立，不能称其错误raw。实际Asc LLVM编译侧blockIdx==0筛的是record publication，MOV SYS_CNT读取在predicate前，不能声称其它program零插桩成本。矩阵后最小增program-publication/semantic-output两维描述，保原字段兼容；不为metadata补充重跑108数学。独立LLVM位置AIC adapted-0.ll L44/AIV L349已记录于agent消息。当前保持运行源不变。


## 2026-10-15 / M018：完整矩阵后半、保留任务与功能优先

**实际状态**：Asc矩阵90/108完成、零失败，五族全过，Transpose运行中，之后原RMS固定T5九请求自动继续。job仍PID262120，source/runtime沿42bd4ae不改，root只读sentinel状态与agent审计交叉确认。跨actorclock不因相容sanity升级。

**验收计划补正**：ROOT核真实acceptance.py发现原README“operators含RMS3shape×2config”不符合plan；operators实际六族108请求，t5只有固定127×769/variant0三批。已预记录heldout-functional-preregistered-r1.json，原T5不变，之后补真正RMS3shape×warps1/4×off/native/detailed=18功能请求。与longK通用config override在一轮最小runner修改/CPU plan合同实现，先等当前job终态，不热改正在用的runner，不换容易任务。

**有限M1调查**：原M005受支持开关TRITON_DISABLE_LINE_INFO=false在两SDK路径加入--enable-debug-info=true；当前默认MIX没有开启，不是“开了仍丢”。矩阵、longK及wheel后只做一次freshcache MIX选项probe，核source candidates/lineinfo cache identity/数值，不回写原默认数据，不把旧vector16/16当MIX证据，不无限追FLIR。

**wheel边界**：R3将复用已验core/native三库，标准skip_build方式repack；metadata阶段USE_FLIR=OFF不能用于重编或关闭现已验core的FLIR。CMake/Ninja/Make build尝试拒绝，wheel ZIP bytes必须与已验lib逐SHA相同，随后Python-I隔离header/ABI/binding探针，不以源码fallback假过。尚未实际运行/未记通过。

**正文**：07-experience写真实三机器工程经验（writer ownership发布缺陷、worker/context/cleanup关联边界、bounded trace非低开销），明确非生产采用；08承认PASTA normalization等prior。不新增另一份维护tex。最新07/04文本实际构建终态待查。

**下一步**：查原full-functional-matrix终态→所有原job/RMS结果审计与archive→Asc最小runner heldout18+longK3及CPUplan→wheel实际repack/一次M1选项probe；ROOT selection provenance两维metadata仅解释追加，不称消除其它program计时成本；冻结最终代码/正文/失败证据，再三个独立fresh reviewer（未启动）。


**M018恢复检查点**：ROOT独立SSH sentinel读取原matrix97/108完成、无failure；当前state脚本已包含SUITE区分（operators/t5），继续用scripts/study_remote.py zhiyuan_ascend --command-file artifacts/method-run/ascend/full-functional-matrix-state.sh核终态，不重起。下一轮仍goal active，Asc agent独占device4并继续原job；其它agentcompleted/idle。本轮已实际push1c5edc5（含ea5ced1 docs），无新NV GPU/性能。07与04最新稿实际make成功，当前PDF SHA226b19780f00ff9f8861eff01fc31e7f796fac719cc57df202e8aba63fa5394d，未做这版全稿视觉复审。正式三review必须等可接受的功能freeze，当前仅artifacts/method-review/packet-preparation.md，不能称已审阅。


## 2026-10-15 / M019：主矩阵及固定T5终态；选择维度说明与静态依赖核验

**终态核实**：ROOT新轮读取真实SSH sentinel、full-functional-matrix.exit=0，operators108 receipts和t5九receipts全部completed/returncode0；原PID262120已不活跃，不重启。状态轮询脚本新增ps检查实际parent（不以receipt/lock单独当live）。Asc agent严格能力审计：36 detailed共7788records=6444AIC+1164AIV1+180AIV2，216raw各49248B/base64SHA/decoded/attempted==committed/zero dropped/无saturation，native+detailed72请求exact身份。大包待ROOT进一步独立离线复核；不以agent口头报告替代最终审计。

**metadata实际修改/验证**：Debugger api保持旧selection_stage兼容，仅加program_selection_stage=device_record_publication_predicate、semantic_selection_stage=semantic_output_filter_after_capture、program_selection_limit=counter_reads_may_execute_for_unselected_programs。真实MIX LLVM读counter在publication predicate前，不声称其它program零插桩。NV Docker PY3.10固定YAPF0.43 AST等价/幂等/Ruff0，现有decode/reconstruction/lifecycle相关18CPU通过，新api SHA25b66f69afce3f1b04d3b10c0957ad9e90c056d7722f029496b6412f41073d76；无新GPU/性能。提交898938b含小证据；尚未push。原117使用旧api，保持原raw，不热改；Asc新runner下一轮才同步此描述增量。

**依赖关系有限调查**：三机制要求实际actor/dependency，原MIX dependencies保SET/WAIT但peer unresolved。GCU只读installed SDK得GetffstMsg=1+((mode&3)<<4)+((flag&15)<<8)，33为mode2flag0，PIPE_FIX10、WaitEvent→wait_flag_dev(flag)。尚缺builtin→LLVM桥和mode2角色scope确证，未升级verified；已授权一次独立tmp CPU-only SDK emitLLVM（flag0/1+mode0/1/2）验证，不GPU/不改原kernel。若能验证只建静态readiness-channel，不按timestamp/occurrence配动态代际，不把signal_issue当completion/共享clock。

**平台agent槽**：尝试followup completed NV agent返回threadlimit；live列表有旧method_ascend_native pending_init占位（interrupt仍pending）。已发勿执行旧任务/结束消息，当前唯一Asc GPU owner为method_ascend_resume。ROOT代做NV元数据CPU；Asc自行在隔离quality目录固定formatter其runner/newtest，不把平台槽当技术阻断。正式三fresh reviewer可两并发后一席，均独立上下文、同冻结包、无互看，不复用工程agent来冒充独立审稿。


## 2026-10-15 / M020：变动保留任务、长K正式入口与时钟域审计

**实际功能终态**：Asc agent报告heldout18/longK详细3/native短控制3均terminal0；heldout18数值/input/canary全过，12native+detailed身份、6详细非空；长K512²×4096三配置均原CPU容差maxabs2.8610e-6，P1624记录/两R各280，无drop。AIV等待局部中位数P55.80/53.98us，BK25612.76/11.48us，tile64 15.96/14.16us；并非engine busy/共同时间轴。新native短控制各3样本：P308.00/BK256160.64/tile64 61.58us，相应detailed313.98/159.82/61.18us，方向一致；不当3×30性能验收，原小RMS61–68%负开销结果保留。全部rawarchive待ROOT独立复核。

**代码/证据Git**：c66fc80增通用heldout计划与显式matmul配置、9新合同，和原identity共17CPU通过；原108+9逐plan精确相等，固定YAPF AST等价/幂等、无新增Ruff（原60项继承）。ROOT本地逐sourceSHA与质量记录一致，提交11files并push实际成功；898938b亦已push，不再沿M019未push状态。

**clock审计**：只读审计定位ACSQ args[4]→_sys_cnt→单device/capture affine converter，实际dev_start/hwts anchors，函数无actor/core offset。支持SDK native packet reportedframe；installed c220 getter MOV SYS_CNT与ACSQ起源/reset/epoch同域仍无契约，不能仅同名同频或containment升级。保存reported-counter-domain-audit.json并随c66入Git。缺的是域关系证据，而非要求物理振荡器证明。

**当前工作**：wheel-r4首次Python-I受torch_npu自动加载/导入顺序失败；按正式runner torch/torch_npu在triton前，现agent报告ZIP43profiler+7debugger/三库/header逐SHA、公开import/ABI皆过，待小JSON及ROOT核。HIVM保原source CPU replay-r1 terminal0，剔ModuleID后LLVM与原未插桩逐字相同但通用printflag无dump；有限r2尝试SDK专用bishengir-printflag，保持旧证据不变。ROOT HTML添加zero tick不等于零成本说明，NV Docker仅CPU focused和pinnedquality正在验，不跑GPU/性能。正文05/06已补18保留任务与真实范围，当前构建中。


**M020 ROOT补验**：0501487b10bace185371040fc593655779971866提交HTML zero-tick说明，NV Docker无GPU16现有reconstruction/plan合同通过，固定formatter不变/AST等价/Ruff0；push和ls-remote精确一致。native3小JSON各原始三样本median/percentage、输入及mathhash一致经ROOT离线重算，完整raw审计仍另计。wheel-r4记录50py与canonical49精确、唯一ROOT新增HTML差异（旧857465…→2c4b36…），所以为旧功能runtime repack通过，非最终sourcefreeze；待HIVM模块后统一最终打包。

**M1真实进展**：SDK实际graph-sync-solver dump46.8KB包含typed CUBE PIPE_FIX→PIPE_S set(flag0)、VECTOR对应wait及源码loc；两个inject-block-sync打印无dump的失败证据保留。Asc owner获授权把实际SDKargv stdout/stderr handoff/parser一般化到execution_ascend及测试/cachekey，不借私有LLVM数值猜测、不伪造dynamic代际/clock；ROOT不并写这些文件。一次lineinfo opt-in MIX编译失败，有限修复保日志，不将CPUdump当GPU成功。

**正文构建状态**：实际make已成功10页、无undefined/Overfull，存在float-only page5警告，最终冻结后仍需完整视觉审阅；04随后清除已过heldout旧TODO，该小文本后PDF再次过时，不冒充最终PDF。三正式review待新静态映射/最终回归/独立raw审计freeze后启动。


**M020完整raw独立审计通过**：ROOT经Docker只读dd分4MB取得原117包87625573B SHAed0efdf320c3c87d54d975979167a8be8de2cdcba56dcaf0391110438b0b6a6d、新24请求包27129904B SHAc1eb1a84698a81f2f1e6421bf52da0270c83c4c7ba16aa10eabf54e3e3cd45e3，均实际校一致；不是重新运行实验。安全解包后独立不导入工具的离线分析逐manifest所有size/SHA、base64原buffer/SHA、原actor header/cursor/attempt/drop/record→export身份与tick、局部20ns公式核一致。第一包117 results/78bundles/11232manifestentries/8976obs/315raw；第二包24results/18bundles/2584entries/2520obs/48raw。所有retained decoded、declared drop0、counter unsaturated、instance_local且native task verified；记录的数值通过在Docker执行，不把离线检查说二次数值实验。审计脚本/小证据随a0bd3f3里程碑，脚本另加下一提交；大包/重复解包留workspace不入Git。三正式review仍待HIVM正式路径和最终质量freeze。


**M020当前唯一活动实现/恢复**：method_ascend_resume独占Asc device4，正编写并验7个HIVM handoff文件（ascend_compiler.py/execution_ascend.py、新ascend_hivm.py/ascend_sdk_driver.py及三测试），不是已提交通过。打印只改变diagnostic，必须actualLLVM等同+正式MIX/input/canary/manifest静态peer闭环。ROOT已只读指出SDKstream文件写失败仍需drain否则管道deadlock、channel ID纳完整typed pipeline key、通用function/新dump不能继承旧actor，owner负责修测。ROOT不并写。原GPU任务均terminal0，下载/离线审计session均terminal0，b8b9a94push亦实际0。新wrapper/parser后需要最终三后端公共CPU/质量（NV全在Docker不跑性能），Asc focused实际capture、新wheel一次最终sourcefreeze，以及正文/PDF/正式3fresh review。平台旧pendingagent仍占槽，三review可两并发后一席；不要复用工程上下文伪独立。


## 2026-10-15 / M021：正式typed HIVM静态依赖及真实lineinfo闭环

**上一轮分类**：progress（完整117+24数据包ROOT独立raw审计、b8b9a94流程已push），非无进展/环境阻断。

**实际M1完成**：新正式MIX lineinfo-r2 terminal0，128³原mathmax1.3411e-7、input/canary、4exactTASK、232动态records（192AIC/20+20AIV）、zero declared drop/20ns local；不开全局TRITON_DEBUG，仅TRITON_DISABLE_LINE_INFO=false走真实SDK debug-info。实际graph-sync-solver stream输出typed AIC PIPE_FIX→AIV PIPE_S flag0，公开mapping.static_readiness中有真实actorIDs。23/23动态site有DILocation；public origin计34verified_origin/27ambiguous/13unassociated，explicit source_op_id仍0，不作exclusivecost。

**独立复核与Git**：完整小包4695052B SHA4672eff062c1d67c062b705ed1ac47182725a74a89d2029cc3aed5a74cbba63b已ROOT取回精确校SHA、安全解包；逐149manifestfiles、actual source.mlir/SDKstderr/originalLLVM hashes与compileIDs、typed edge endpoints、4rawbufferSHA/localformula、7canonical源码等qualityafterSHA全通过。27DockerCPU合同格式后通过，包括流写失败仍drain、保childexit9、新函数/IRdump清actor、完整pipeline channelID。print-onlyCPU原actorLLVM剔ModuleID后逐字相等。提交7375d39含7source/test、smallproof、两准确README、完整FlagTreepatchpins；push进行中。前docs d769647也随推。

**外部FlagTree**：实际独立6文件commit00650233fcaa9c55134e8aae690067a32d97ad45，fullbaselinepatch SHAd18294b2e01805de1f18d395bf5ef88e95763499883957b1db56c17ec7cb68c3。官方FLIR ff91e64…与AscendNPU-IR4c304…trackedclean，实际core/native unchanged。

**有限M2后续**：授权Asc owner在当前已验M1之后单独delta：latepass编译semantics筛选（wait/issue/checkpoint），保稳定siteIDs，未选site无MOV/record，metadata/env/cache有效集明示；不扩任意sites/sample/新IR。原RMS input/config的wait-only+native3×30，保全site61–68%负结果，若无wait如实记录不换容易任务；可融合wait-only短功能额外证有wait。只重LLVM15插件、不换core/native，之后最终wheel/quality/正文freeze。

**GCU有限功能补验**：method_gcu_mapping恢复为GCU device0 soleowner，原进程全terminal、12相关source/nativehash全等，正在两个实际nondefault torch.gcu.Stream交错6calls（4同binary+2另一SCALEspecialization）。初次test task_id非null失败，SDK gridId0未知而correlation/scope/stream实际有效；ROOT允许按真实SDK correlation domain/ID+process/context+scope/sourcebinary+stream一对一oracle验证，unknown task保持null，保失败并注明oracle初始假设，不用name/order。尚未称finalpass。

**正文**：03修正物理ZIXIAOC200；旧study sharedframe解释改为conditional reported-counter placement，唯一campaign窗口匹配非独立域关系/运行身份certificate。04补实际typed channel算法/源origin边界及GCU publisher ownership；05补继承/新增实际边界/3baseline。最新文本尚待新build+完整render。最终公共CPU/包/sourcefreeze和3独立review仍未完成，goal继续。


**M021 GCU双stream补验终态**：实际Docker1pass/4.92s，6交错calls/6native/6dynamiccaptures/80events、两个binary及不同inputexactCPU+guard全过；torch非默认handle848736000/837745600，SDKstream0/1交错，correlation34/62/90/118/155/183。SDKgrid/task未知原值0，不假定taskID非空；原两个oracle错误失败已保留，无product模块为此改动。ROOT下载包5129023B SHA4d4b30bac6d9bac0db77657a75d90b8052485ef5986b2c379bc92a6e67934d46精确核、48filehash/34bundleentries/6source-native-dynamictuple及80events核一致；安全提取跳过3pytest绝对current symlink，不作为数据。新可复用hardwaretest与小证据提交c9b0ad4；实际终态/格式/nativehash日志另e9eb64c已提交。GCU ownerfinish，无ownGPU进程；不称并发重叠或sharedclock。

**M021当前M2进程**：Asc PID397400只跑原RMS六phase（native+wait-only各三批30）及融合wait-only短功能，原矩阵/原M1不重；新LLVM15插件46f420c4…实际重编，12opt/compiler/cache合同过，1旧cacheenv遗漏负日志保后修。不热改运行源码。语义选择按实际latepassmanifest证明升级API描述，Asc owner获授权负责Debugger/api.py小helper及CPU；ROOT不并写。预计M2终态/最后wheel后冻结并启动3freshreview，当前未启动。


**M021 M2实际终态与后续边界**：ROOT原进程独立m2-root-state-r28.txt sentinel核parent not_live/terminal0；六原RMS phases全passed_math_and_native/verified，detailed三批各198=33calls×6wait，融合短case100。agent严格审计native中位6.62/6.39/6.00us、wait-only10.60/10.78/10.68us，+60.12/+68.70/+78.00%；hostnative216.7/220.3/215.7us、wait-only1708/1761/1723us。不优于旧全site、不称低成本。runtime有效sites稳定1/4/6/8/9/11，每actor对应MOV只选中语义，原math/input相同、zero drop/localns。新的allsite/sourcepartial数据不覆盖旧M1或原T5。

**最终有限成本证据**：为给“实用范围”而非只凭各3样本，ROOT授权在API/helper源码冻结后额外一次原longK P32_K32 512²×4096、原input/math/grid/program0/cap2048/allsite，native+detail各3批30随机phase。保全部时间/导出/tracebytes/math/raw/identity，绝不替代原RMS负例，不扩R配置/全矩阵或新机制。尚无PID时不称live。只重late LLVM15插件，其余三库保持；新API由Asc owner负责，ROOT不碰。

**正文/构建与Git当前**：e9eb64c实际push0包含c9b0ad4 GCU实际stream测试和终态/格式/nativehash。M021方法稿与03较短caption实际build10pages，Overfull0/undefined0，PDF24848…那版之前有5.96pt Overfull已通过缩短caption修正；当前06新增M2负成本段后还未重新build。全文视觉审阅及paper/journal不可变快照入Git待finalfreeze。


## 2026-10-15 / M022：最终同源候选、全raw与封包，进入独立审阅

**源码/提交**：M2 7source/24真实合同与GPU选择功能先1cb15d729e4bed52d27c19b996f97b7ab88ffa80提交；CANN最终52PY/3库/header/I隔离wheel-r5与全部成本证据221d8cd；三Docker源/import与最终短功能fa302bb。runtime code不再变，后续doc/证据commit不伪称native重编。当前3backend各自实际core/nativeSHA在final-common-20261015 logs及backend manifests，CANN新lateplugin46f420c4…和CPP376a8222…对应，FlagTree独立commit00650233…/官方依赖pins不变。push待最后packet一并。

**最终source/import验证**：原487trackedsource/fixtures snapshot含README，改为code-only468排除Markdown，runtime52PY。NV Docker421passed4opt-inbrowser skips；最终实际3个publicrequest调用program0/1/99、动态scope/math/overflow/cache identity通过，native三库仍48ced…/6118…/73cad…，无性能测量。GCU350passed5skip=4browser+1继承CUDA/HIP instrumentation，最终新API共同源下两实际stream6calls2spec测试1pass43.03s（冷编耗时非性能）。Asc407passed18skip=4browser+11GCU-onlynativeguards+3可选CANNrawfixtures（已在NV另跑actualfixtureCPU），实际CANN52chosenPy/468code/native逐hash过。24late-opt/API合同、全部实际矩阵/保留/longK另有真实硬件证据，不用CPU代替。

**harness失败保留并正确修复**：GCU最初以为runtime是source symlink，guard拦实际copy旧api；backup后逐52Python精确同步真实runtime、原native不动，再350pass。NV最初bootstrap重复预载profiler与原脚本注册，原guard拒绝发生在GPU调用前；改只预载Debugger、原脚本/oracle不动，3真实调用过。Asc最初普通namespace合并找不到dev overlay的profiler包；改用已验worker source+built-native loader，并逐真正模块选择path52byteSHA验证，407pass。所有原失败明确为启动harness，不吞失败/不放宽数据oracle。

**独立完整M2/longK审核**：ROOT下载M2包14118987B SHA5a18249352bbc73566d114fa0a27416c40d9a09b83cd7a31d76ac54bc608341e与longK包22712496B SHAb20bdaa1a8e4376279c43d9b360f185a5582e6c315485e26cdf8070b3db48cee；所有manifest size/SHA、rawbuf SHA/actor原记录/identity/tick公式全验。M2 7results/7bundles/1029fileentries/694records/103raw；longK6/6/873/40194/99，无declared drop/saturation。额外从6原result逐180device/hostsample与summary核一致，数学/input/source/canary与30个独立nativeinvocationIDs对应，所有median/percent/exportns/tracebytes重算一致。此前117+24/M1/GCU两stream所有raw审计均仍成立，版本不重标。

**成本边界**：小RMS wait-only三批60.12/68.70/78%高成本不改；原P32_K32 longK native311.19/309.74/309.88us，detailed310.94/313.76/312.58us，−0.08/+1.30/+0.87%。仅该case device目标满足。host detailed12.33–12.46ms、native267–272us，export15.62–17.21s，bundle221–229MB/33call。无native-off独立task证据，不称native≤5%或端到端低成本。

**最终包/进程**：r5wheel SHA405e2919f16be7f0fe58b9698a08e87965b6ac23eb0dc1ed8115f25a6641cfee，actualZIP52Python等canonical、三库/receipt header等已验、Python-I公开import/hiddenABI/preallocguard通过；是accepted binaries repack非clean-source重编。ROOT独立52源码及header与其记录SHA全等。agent final-state-r29.txt核397400/410703/418345/419285均NOT_LIVE；ROOT后来短GPU及CPU工具均terminal0。工程agentsfinish，无环境blocker。

**论文**：唯一main.tex/引用tex按实际M1/M2/M3重写，06负成本和longK全成本、07真实工程经验、08承认KPerfIR/Proton/PASTA prior；03共享epoch改conditionalreportedframe且物理名改ZIXIAOC200。Overview plot原代码只替换legend GCU300→ZIXIAOC200重新从原saveddata绘制，CSV前后SHA逐字相等，原Study源码工作树不改。最新reviewPDF c25d39e13696bbcb552b64b493a88f844cb987517f737f5748843fb5eb291ad0、11页、无undefined/Overfull/floatonlypage；GCU DockerPyMuPDF1.26.5全11页真实渲染，ROOT看全contact并高分辨率page6/9，无裁切/重叠，PDFtext无GCU300。背景/abstract等非方法稿仍有明确TODO，非完整提交成稿。正式review接下来启动，不能把这些工程通过视为OSDI贡献通过。


**M022正式审阅已开始（同包）**：frozen packet b5e6f27（runtime1cb15d7/evidencefa302bb/Ascclosure221d8cd）已提交，含PDF SHA c25d39e13696bbcb552b64b493a88f844cb987517f737f5748843fb5eb291ad0、唯一维护tex的不可变diff/hash、记录/合同快照与primary/evidence索引。root实际spawn fresh fork_none R1 /root/method_review_r1_novelty、R2 /root/method_review_r1_systems，独立default模型，不给peer报告不要求肯定；各自读实际源码/证据/primary。由于旧pending_init占槽，R3正确性待任一完成后freshspawn，不复用工程agent。评审期间保持code/manuscript/PDF不变，root只维护本记录及审阅流程/证据。三review尚未全完成，不complete。b5e6f27push运行中。


**M022独立首轮进展**：b5e6f27 push session31131实际exit0。R1-novelty、R2-systems已独立完成major revision，无结构性不可修结论；第三fresh /root/method_review_r1_correctness已spawn，读同一冻结包，不看peer报告。R1具体缺口：ascend_hivm importer只复制source_ir_sha256、不重hash保留源及核enclosing compileID。R2具体缺口：正式服务输出到优化决策/disabled测量未形成自包含闭环；原buffer身份/字节/频率验证不等于局部wait语义和扰动稳定性。拟先用原GCU四/一workitem及Asc三longK正式capture离线提取证据，再仅补必要有独立oracle的有限实验。不将更多pass数当贡献。不跑NV性能。Asc owner只读准备方案，R3结束前code/manuscript/PDF不变。


## 2026-10-15 / M023：首轮三审处置与有限第二轮

**三审终态**：R1/R2/R3均完成major revision，认可实质工程，均未证明结构性不可修；原报告已复制Git证据目录reports。R3按原packet误读live记录M022时接触R1/R2简短结论，未读peer报告，已主动披露并改读旧不可变snapshot。不能声称完全blind。下一轮freshcontexts只读冻结工程材料，不读livejournal或含peer结论的记录，避免重复。

**ROOT采纳及修复预测**：
1. R1-1/R3-1实现缺口：SDK readiness source/enclosingcompile绑定，保真实源bytes并重hash，成功phase、receipt/actor/manifest/enclosingID核一致；oldhash-only不能certify。Asc owner独占hivm/compiler/execution/observations及测试；API仅允许decode调用传expected_program一行，ROOT不并改。CPU负例missing/mutated/swap/stale，以及新正式MIX/math/staticedge/raw/identity需通过。
2. R3-4实现缺口：authoritative knownsite语义与actualdescriptor/program矛盾拒绝，rawfailed保存；未知/ambiguous继续partial。无需native/core重编，按实际变更决定。
3. R1-3/R2-W1/R3-3证据：先离线接正式输出→决定→无源内插桩收益，保每capture版本。ROOT已从原formal三Ascconfig精确用samples.invocationIDs排warmup，AIVlocalwait55.80/53.98→12.76/11.48→15.96/14.16us；GCU实际mapping四item2barrier/10sharedsite与一item0/0。extraction和输入hash在artifacts/method-review/round1/preparation。离线分析不是新实验，detailedtasktime不当disabled结果。
4. R2-W2/R3-2证据：Asc owner拟最小独立fixedcount既有wait/readinessdelay、readycontrol、emptybracket/resolution及allsite/wait-only稳定性，不增加完成barrier，不认证sharedclock，不用wholetask低扰动替代局部waitfidelity。方案待ROOT审后启动硬件。
5. R1-2/R2-W3表达/证据：经验节以failedassumption→repair→validationboundary重写，凸显ownership/workercontext/selectioncost的可复用系统知识，不靠三adapter或测试数称novel。相关工作去笼统“已有工具不懂语义”区分。不做跨设备Proton/KPerfIR比较。
6. R1-4/R3-5成本与R1-5/R2-W4旧状态：publicdoc清除Ascfullmatrixpending等矛盾、区分oldmatrix/currentfocused；正文补默认scalar6cases后GELU900s编译timeout/vectorfullmatrix70.85min。保smallRMS高成本及longKhost/export/space负结果；NV性能继续deferred。

**执行/所有权**：Asc owner已获代码修复+CPU及一次freshMIX授权，后续timing方案未批不跑。GCU owner只读整理canonicalinputs/实际sourceconfig/observer-disabled90samples链并提出2tinyfinalcapture方案，未授权新长采集。ROOT方法/经验/相关工作/publicdoc，不改owner文件；无NV新硬件或性能任务。原冻结b5e6f27实际lsremote精确相等；当前round2修改未提交/不称通过。

**新发现的表述边界**：GCU原90samples是nativecollection开、源内observer关，不能说所有profiler关闭。应称uninstrumented/source-observer-disabled，并保原nativecollector开销边界。最终三个case均同样区分。无需要用户处理的环境blocker。下一步：等Asc CPU/新MIX和GCU最小提案，ROOT核准有限fidelity实验→实际证据→唯一正文更新→新freeze三fresh独立复审。


**M023具体授权/进行中**：GCU仅新test_enflame_softmax_diagnostic_hardware.py参数w4/w1、site29实际trackedtt.store、program0/cap64、canonical127x769，单次publicstart/launch/finalize；每case240s/批600s，数学/input/canary/1native1dynamiccapture/actualmapping/rawclock不可转ns。还原90sample每个worker原nativephase证据，明确nativecollector开。Asc程序记录错义/错program的rawretention回归获批，api.py仅decode_dynamic64传expected_program的一行由Ascowner写；sourcebytes要求read_bytes().decodeUTF8避免CRLFnormalization，旧cache失效。最终源码需r6同已验native库wheelrepack，不冒称clean-sourcebuild。ROOT当前文稿补默认scalar6case后900stimeout、vector70.85min、finalcommon实际范围、4compute/4dispatch经验及原nativecollector边界；新独立fidelity仍TODO，不预写正结论。


**M023 GCU补采与ROOT独立核验完成**：新正式test两case均1pass4.41s，当前52actualruntimePy对应1cb/native三库不变。完整raw3790078B SHA0249bf9e672e442ae8dbafe278dd869bcd8ad8677ad6d6e7caa6bfd671309744已ROOT精确SHA核；首轮安全检查拒绝archive里两个pytestabsolute current symlink，后明确skip这两个link、仅提取安全regularfiles。ROOT不导入profiler的独立脚本逐110bundleentries/hash、2原rawheader/record64/tag/identity/ticks、270历史nativeevents所有30call批/median/input/config/sourcehash、数学rows AST全等核通过；还核原native及当前capture enable_i64=False，oldallsiteTrue继续只作负成本例。w4三median114.8685/115.064/115.209us；w1 71.145/71.1245/71.055；ratio1.61457/1.61778/1.62141。w2仍2barrier且73.553/73.653/73.777us，禁止barrier-only归因。新capture w4actual2sharedbuffers/2barriers/10IRstorageops，w1零；10不是物理message。正文06已写真实retrospectivediagnostic，明确不是首次发现/新source性能重测。仅新GCUtest及小证据提交adc57e7，HTTPS默认push缺交互认证按既有SSH路径推送exit0；无需用户新授权。rawlogEOF空行原样保留，代码/说明gitwhitespacecheck通过（检查排除不可变*.log），不改原日志凑format。

**M023 Asc首轮实际状态**：source-first65CPUcontracts pass、0skip，暂无新GPU/无native重编；之后format/rerun+1freshMIX尚待owner执行，不把65首轮当最终freeze。额外一次120s CPUonly标准Triton两MOVSYS_CNT inlineasm编译actual成功，纯AIV两个reads在两个stores前但无显式subblockguard，GPUfloor未授权。后续assemblyinspection先遇hashlineageassert失败，发生SDK调用前、保日志。ROOT要求优先finalformat/CPU/freshMIX，optionalprobe不得阻塞主线；counterpair必须同actualactor输出、无写者竞争才可测floor，checkpoint0不能代替。六longK requests(3configs×allsite/wait-only，warm3+10calls)已条件授权在CPU+newMIX通过后，固定shuffle、完整source/raw/counts/IQR/全部点；25%仅敏感性flag非准确性认证，nativeSDKreplays不同scope不并钟。无NV性能任务。


### M024 — Final provenance repair and diagnostic-stability evidence (2026-10-15)

Final runtime commit a9a28ba258fb95056447c451de262824b5f04392: exact retained source/manifest UTF-8 bytes, typed JSON consistency, successful enclosing/SDK compilation and per-artifact LLVM/job validation shared by readiness and source origins. Invalid/legacy evidence remains raw/unverified. Six changed source/test hashes independently matched final Docker 91-case focused proof; changed-range formatting idempotent/AST-equivalent, no new Ruff diagnostics. Final 469-file freeze is artifacts/method-run/final-r32/code-freeze-r32.json; 52 Python modules unchanged from isolated r7 wheel proof. NVIDIA final CPU regression: 483 passed, 4 opt-in browser skips, no kernels/performance in this run. GCU and Asc final CPU checks pending.

Fresh Asc MIX retains 34 unique/27 ambiguous/13 unassociated origins and one typed readiness channel; exact 37,819 retained manifest bytes. Old bundles without retained manifest text degrade by default; offline sidecar revalidation is derived-only. Six controlled all-site/wait-only captures pass math/input/canary/identity/counts, but original AIV waits differ by +76.8/+83.4 percent. First BK intervention direction survives both modes; subsequent output-tile step does not support a further wait-reduction claim. Independent minimal 64-call two-read control has 64 zero-tick differences with advancing start values and intact canaries: unresolved resolution, not zero cost or fusion accuracy bound. ROOT independently audited 1,030 manifest entries/82 raw buffers/7,759 records plus minimal raw pairs; committed 8a3c82c evidence.

Asc r7 actual repack/isolation PASS, exact final52 Python files, accepted native libraries unchanged, receipt header retained, no source fallback; wheel SHA b3d95af3a35e93877c2b92810247c954e7c38e302d1e312acf33b501b111aa8e. Reused verified native builds, not a clean toolchain build. No NVIDIA performance request; existing unrelated GPU process untouched. Remaining finite work: final CPU proof, manuscript/PDF freeze, three fresh independent reviews without live journal or earlier peer reports, bounded disposition and Git delivery.


**M024 final freeze and independent review launched**: final-r32 Docker regressions NVIDIA483/4skip, GCU406/5skip, Asc469/20skip all exit0. Asc fullCPU began against explicit working-tree469 snapshot; independent per-file comparison proves exact a9a28ba final469bytes, no duplicate run. Three native libraries unchanged, final52 runtime Python also exact r7isolatedwheel. ROOT read and independently reran fresh origin data-only audit151manifestentries/4raw/232records, source372244B/manifest20236+17583B, exact samecompile/job/3measured native identities. Asc owner reports8ownedjobs terminal0/no remaining PIDs.

Evidence/docs commit5e5c953. Frozen manuscript/review packet commit53cdae1: sole maintained paper/main.tex/includes,12page PDF, final log no Overfull/undefined/float-too-large; all12pages rendered and contact reviewed, page9 full-size checked. PDF/source hashes in integration/evidence/method-review-r2/source-manifest.json. Includes measured collection-mode sensitivity and restrained recovery interpretation; no invented shared clock. Original abstract/background/conclusion TODOs remain separate from method task. Fresh reviewers correctness and novelty started from empty contexts, explicitly forbidden livejournal/priorreports/peerconclusions; third systems reviewer must start once a slot frees. Defaultmodel independent contexts, no claim of three model families. Runtime remains frozen a9a28ba; no owned GPU experiments running, NVIDIA performance deferred.


### M025 — Finite presentation/evidence repair and fresh review (2026-10-15)

Round2 three independent reports all identify plausible Operational Systems contribution under bounded selective offline scope, no demonstrated supported-path blocker/structural deficit; major requested repairs are self-contained prior comparisons, practical operating regime, counterexamples, decision boundaries and exact document provenance. Reports+root item disposition committedff68f1d. Not acceptance proof. User rejected capability matrices earlier, so used concrete bounded-request/cost paragraphs and one single-column evidence-to-decision table instead.

ROOT independently derived retained counterexamples: oldGCU59records onlyfirst4of16u32published, first[7,8,1,0,0…], failed nonzero-clock oracle; freshAsc4canonicalcompute+4dispatchviews, offlinecount-all8wrong (not measuredlegacyjoin). Data-only two GCUbinary inventory replay verifies actualstore29independently for each differentbinary,1associatedrecord/no loss/unknownfrequency/mathcanaries. Scripts+hashes integration/evidence/method-counterexamples-20261015. No new runtime features/tests or GPU/perf.

Sole paper updated: precise KPerfIR5.2collaborative publication/5.3waitdistortion+conditionalcorrection overlaps; no general novelcorrection claim. Abstract/background/conclusion completed from actualscope; no substantive TODOremaining. Firstpage/casecaption distinguishes retrospective service from richer researchprobes; firstBKmode-stable, secondcardinality/nativecheck. Versiona9a28ba final vs1cbprior explicit. Publicdoc adds bounded inventory→request→fieldinspection→changedbinary inventory→independent recovery walkthrough, explicitly knownsitefixture/notautomaticsitediscovery/notmeasuredonboarding.

New packet5e04a04 runtime469hashesstill exacta9a28ba; publicdocumentationseparately hashpinnedff68f1d to avoid oldruntime-docambiguity. Frozen PDF8b897aabedb3426b3cbd461a9960523f3fed82e818939e8097578161f6746fde,13totalpages, noOverfull/undefined/largefloat; fullrender13/contact+page10checked. ROOT subsequently verified officialCFP12bodypage+refs; currentdraftbodycontinuespartwaypage13, so finaldeduplication/layoutrequired afterfrozenreviews (do not change candidate duringreviews). No measuredclaims need change. FreshR3novelty/correctnessstartedemptycontexts, thirdsystemsnextwhenfreeslot; forbiddenearlierreports/livejournal/peeroutputs. Nohardwarejobs, noenvblocker.


### M026 — Concrete final-review partial-readiness fix (2026-10-15)

Fresh round3novelty: no blocking/majorcontribution defect,2minor expressionrepairs. Systems: no substantiveblocker, minorprior/workflowclarifications+known12bodyformat. Correctness foundactualM1gap: unassociated competing typedset/wait could vanish from uniqueness test. ROOT accepted concretecorrectnessfinding regardless2otherpositiveassessments. Reviewer localinmemoryexploratoryrepro is not officialDockeracceptance; Asc owner reproduced pre-fix in actualDocker with a9moduleSHA (3rawsites/1channel incorrectlycompiler_static).

Only2filesfixed/committed8fffdf681989388de02b591d52806e1f57500184: retain all rawtypedcompetitors inchannelgroup, requireexact1set/1wait bothuniquelyverifiedcrossactor. ActualDockerpostfix3rawsites/0channels/partial, allrawsitespreserved. 8negativecases missing/rejected/duplicate/ambiguousactor×set/wait, focused99pass0skip/.50s. FixedYAPF0.43ranges/ASTequivalence/idempotence/newRuff0. Genuineoriginal128³MIXdatareparseunchanged1channel34/27/13/232records4buffers, noGPU. Final469r33freezeavailable; threefinalCPU/repackr8currentlyinprogress. No newperformance.

ROOT appliedminorpriorclarification (NVIDIAstudyreference, priorcomparisonincludesAMD); contributionframeconcretefailures/repairs/survivingdecisions; explicitretainedinventoryworkflow+pytestfreshmktemp outputretention. Trimmedduplicatedintro/implementation/evaluation/threats only, preservednegativecosts/counterexamples/decisiontable/researchsetting andclocklimits; awaitingfinalrenderbodyboundary. Need third/final targetedindependentverification againstnewfreeze, thenGit/report/goal.


**M026 finalactual closure before scoped verification**：NVIDIA491/4skip12.99s、GCU414/5skip6.82s、Asc477/20skip4.49s，exact469runtime8fffdf6，各actualnativehash不变。Ascfinalparent513979exit0/PID不存在，无GPU任务，isolatedr8wheelSHA e7e06e5534b613d35bb9f9c30ca80bdfe87b77491a6d52bc9ed411bc41173a59，52PY/header/3native/IpublicABI无sourcefallback通过。新PDF91b57f5d1da1ef62005a348f5155604b776c7b266aae1807790184e5af4f062e：12页body，References/Conclusion均page12，page13仅refs；13全页render/contact/page12视觉核验，TeX无Overfull/undefined/largefloat，宏文本空格修好。新packet32628f0源码/公共docs712eeae分别exactSHA；raw/正式性能campaign仍原version，无新GPU。fresh最终novelty/correctness两席已从空context启动，只读当前技术packet，不读旧review/root/livejournal；thirdsystems下一个freeslot启动。


### M027 — Final public summary consistency (2026-10-15)

Round4 correctness finds no blocker/major, one minor actualexport inconsistency: Asc kept34originassociations incombinedlist but omitted separate source_origin_associations, generic publicsummary reported0. ActualDockerprefixed publicentry reproduced0/combined34/site34-27-13; notignoredasmerelycosmetic becauseupperconsumersneedcorrectsummary. Onlyexecution_ascend.py returnfield plus existingpublictests changed; 99focusedpasses/casecountunchanged, publicunique2/ambiguous0/unverified0 verified. Exactgenuinepublicderivedexportpostfix top34/combined34/sites34-27-13/1channel, originalresult/rawhash unchanged; nooriginalbundlerewrite/noGPU. FixedformatYAPF0.43/Ruffnew0/ASTeq/idempotence. Runtimecommit2d7eb9565bb339fdfd6e6413ed8aedd6c7eda76a; final469r34freeze prepared, finalthreeCPU/r9inprogress.

Round4systems no actionableblocking/major/minor scopedfinding. Round4novelty no blocking/major but disclosed overbroadsearch accidentallyprintedlegacyreview/journalsnippets; notperfectblind, ROOTpreservesdisclosure ratherthanclaimall3perfectblind. Finalpostfixcheck will replace noveltywithfreshrestrictednamed-inputcontext; correctness/systems independentsubagents may issue targetedown-reportaddenda withoutpeeropinions afternewsource/PDFfreeze. Not restartingresearchorhardwarecampaign foroneadditivefield. Finalpapermeasuredclaims unchanged; implementationhashonly2d7eb95update, body12pages+refs13remains, buildclean. Allruntime/C++/measuredoldcampaignversionsexplicit; NVperformanceunrun/userdeferred.


### M028 — Final engineering, method and review disposition (2026-10-15)

Finalruntime2d7eb9565bb339fdfd6e6413ed8aedd6c7eda76a,469source/52runtimePyexact. ActualDockerNVIDIA491/4skip13.07s,GCU414/5skip6.82s,Asc477/20skip4.53s. Focused99cases unchangedcount with publicunique2/ambiguous0/unverified0 assertions. r9isolatedwheel SHA66fb52002e8463a1439712cd2e8a410849eaa2526c651f3c1d6a136a197a40d7 exact52/accepted3natives/header/IpublicABI/preallocationguard/no sourcefallback; acceptedbinaryrepacknotfreshcompilerbuild. Parent525617terminal0/PIDabsent; no ownedGPU/backgroundtestjobs. Runtime/codequality/artifactsareinfinal-r34-20261015. Actualpublicderivedexport34/combined34/sites34-27-13/channel1 preservesoriginalresult/rawSHA, ROOTindependentdataaudit passed.

FinalsolepaperPDF98ea4e6d125a5ab87b791f9387f66a2b8cb3fd3b1002bc5322b475dd559c2625; body12/refs13totalnormaltemplate,noOverfull/undefined/largefloat,all13rendered/contact/body-referenceboundarychecked. Method/study/implementation/evaluation/experience/related andfront/backmatter consistentwithimplementedselectiveoffline scope. No extra maintainedtex tree; GitcontainsimmutablestagePDF/sourcehash/snapshotonly.

Finalr5packet/source/doc hashes pinned. R1freshrestrictednamed-inputreview no contribution/inheritance repair; R3correctness andR2systems independentown-reporttargetedaddenda noremainingactionablefinding afterminorfieldfix. Nopeeropinionsshared; twofollowupsarenotmisrepresentedastwofreshcontexts,defaultmodelnot3families. Earlierround4R1incidentallegacyexposure disclosed/preservedandfreshfinalR1replacesit. ROOTreviewedallconcreteissues,includingactualreadinessfalseuniqueness/publicsummary0,implemented+Dockerverifiedratherthanmajorityvote. Allreports/rootdispositions preserved.

Outcome: usablepinnedthreebackendprofilerwithM1partialexecutionmapping/M2typedboundedobservations/M3evidence-basedinvocation/raw/localclockreconstruction; tworetrospectivediagnosticchains remainqualifiedwithoriginalnative-collected/source-observer-disabledrecoveryversions. PlausibleOperationalSystemscontribution fromspecificownership/worker-context/fidelitycounterexamplesandrepairs,notnewgeneralIRoracceptanceguarantee. LimitsNVperformanceuserdeferred,unknownGCUfreq/compilecost/drops,Ascsmallkernels+localwaitsensitivity/host-export-storagecost,unverifiedglobalepochs/dynamicgenerations/completeorigins remainexplicitnotpassed. Noenvironmentblocker, no requiredunfinishedworkbeyondfinalGit/goalbookkeeping.
