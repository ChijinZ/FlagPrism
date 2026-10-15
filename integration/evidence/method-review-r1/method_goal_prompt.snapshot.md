# Method 实现与论文长任务执行指令

本文件仅在用户通过 `/goal` 指定执行时生效。准备文档不代表开始实现、实验或审阅。

## 1. 目标和结束条件

**2026-10-14 执行补充（用户明确回复）**：Pro 6000 被其他用户任务占用，用户选择“先保留开销待验证，继续其它工作”。因此 NVIDIA 的独占性能复测保留为公开待办，不阻止其余实现、正文和贡献审查；审查包必须包含此前超过目标和受干扰的全部结果，不能将待办算通过或低开销结论。该例外仅适用于这项性能复测，不放宽三后端正确性、正式入口、身份/时钟机制或其余硬件验证。后文 I4→I5 条件按此例外执行。

在用户的 FlagPrism 开发分支上实现一个真正可用的三后端 profiler，支撑三个方法机制：

1. **程序—执行映射**：将源区域/操作关联到实际后端执行组织，并保留编译变换产生的拆分、融合与实例关系。
2. **执行语义感知的观测与插桩**：将 profiling 请求转成目标上有明确语义的观测，区别 issue、wait、completion、原生计数器与 source-control 时间。
3. **程序关联的观测重建**：用可靠运行身份和经过核验的时间关系关联记录，保留后端细节、统计粒度、replay 与测量边界。

完成真实实现、三后端测试和质量检查后，依据实际机制重写方法正文；由三个独立 SubAgent 评判 OSDI 级系统贡献、novelty、证据与表达。对有可执行修复路径的问题继续实现/测试/写作/复审。若贡献不足且当前授权范围内没有可信修复路径，结束本轮并向用户说明具体原因、已完成成果和缺失条件。

**工程验收通过与论文贡献通过是两个独立结论。** 不以 reviewer 的赞同替代运行证据，不以多后端数量、接口统一、报告美观、代码行数或新 IR 名称单独充当 novelty。不得为了得到通过而降低验收标准或反复向 reviewer 索取肯定答案。OSDI 接收不能由本任务保证。

若确有绕不过去的机器/SDK/权限/磁盘/宿主配置问题，按第 11 节返回用户处理；不得伪造通过、用 mock 替代硬件验收或把任务标记为实现成功。

## 2. 启动和恢复

工作区：`/home/jin-lab-pc/workspace/osdi_flagprism`。依次读取：

1. `method_impl_record.md`：状态、已确认决策、活动任务、下一步。
2. 本文件；`study_exp_record.md`、`study_experiment.md` 的最终研究边界。
3. `paper/sections/03-study.tex`、`04-design.tex`、`05-implementation.tex`、`06-evaluation.tex`，必要时 Introduction、Background、Related Work。
4. `existing_works.md` 与相关论文；novelty 判断必须进一步阅读支持比较的原文、公开实现或官方资料，不能只相信综述条目。
5. 对应仓库的适用 `AGENTS.md`、实际代码、已有测试和构建说明；使用研究技能时遵守用户已经明确授权的实现与迭代范围。
6. `ssh_machines.sh` 仅用于连接，不回显凭据；复用 `scripts/study_remote.py`。

恢复时先核实已有进程、日志、终态和 Git 状态，不能重复启动成功任务。更新记录再跨上下文继续，不从头调研或重新建立 Study。

用户说的 `detailed_profile` 对应已发现的远端分支 **`ChijinZ/FlagPrism:detailed-profiler`**。准备时 HEAD 为 `a7a9aca63738c69ef7846b0faf201206b0882a62`；启动时 fetch 并核实最新 HEAD。不要另建错误拼写的空分支。

`FlagPrism/` 当前是 `study-and-eval`，存在用户/前期工作的未跟踪 pipeline 文件和数据。保留它们；不 reset/clean/stash 覆盖。用独立 worktree 在实际 `detailed-profiler` 分支开发；已有 worktree/本地分支先检查，避免冲突。

Study 最终提交 `dba2ff9c74f4e4a8063126c554bac1708d6f72d9` 已推送。优先借鉴其中经验证的研究代码和数据，不能把专用 LLVM 修改脚本直接包装为通用工具。不要为了移入几段代码把整个 Study 数据历史合入开发分支。

## 3. Git 和源代码管理

- 工具实现提交到用户仓库 `https://github.com/ChijinZ/FlagPrism.git` 的 `detailed-profiler`。按可评审的机制/修复/测试分批 commit，记录 baseline、commit 和差异；阶段通过后 push，禁止 force push、擅自 merge main 或改写用户历史。
- HTTPS 曾缺少登录凭据；已验证现有 GitHub SSH 身份为 ChijinZ，可用 `git push git@github.com:ChijinZ/FlagPrism.git detailed-profiler`。启动时重新核实可用性，不输出 token/私钥。
- 若需要修改 FlagTree 的 pass 管线、编译事件或后端 lowering，这属于本任务实现范围。用独立分支/worktree 管理，记录 baseline、patch/commit 和三后端所用版本。未确认上游写权限时先保存可复现 commit/patch；不把缺少上游 merge 权限误当成无法开发，也不擅自 merge/push 上游 main。
- 区分继承的 Proton、Debugger、FlagTree 功能、已有 FlagPrism 适配和本轮新机制。记录贡献来源，不能将继承能力重新命名为新贡献。
- credentials、SDK 私有库/头文件副本、环境缓存、构建产物不入 Git。提交可公开源码、必要小型 fixtures、测试入口、复现说明、证据 manifest 和审阅处置；大数据保存在持久化目录，以 hash 和路径追溯。
- 工作区根不是 Git 仓库，不能声称根目录论文已经随工具 commit。论文保持唯一维护位置；将正文 diff/hash、PDF 快照、记录快照和 reviewer 报告按阶段随实现归档，不维护第二套 tex 源码。
- `method_impl_record.md` 是唯一现行实现记录；仓库内可保存自动生成的不可变阶段快照，不人工维护两份状态。

## 4. 三后端 Docker 环境

| 后端 | SSH 别名 | 已有容器与路径（启动时核验） |
|---|---|---|
| RTX PRO 6000 Blackwell，sm120 | `zhangquan_pro6000` | `chijin-study-pro6000`；`/storage/Ext_01/chijin-study-pro6000/workspace` → `/workspace`；已有 Torch2.8.0+cu128、FlagTree PR1262 构建 |
| 燧原 ZIXIAOC200（已实机核验；gcu300为SDK API库名） | `zhiyuan_suiyuan` | `flagprism-enflame-dev`；`/root/chijin_workspace` → `/workspace`；已有 torch_gcu 与 FlagTree/Profiler |
| 昇腾 910B4-1 | `zhiyuan_ascend` | 经 chijin 用户复用 `chijin_v3.5.x`，通常 `sudo -n -u chijin docker ...`；`~/workspace`/已挂载目录；已有 CANN9、torch_npu、Triton3.5.1；此前用 device4 |

**全部依赖安装、编译、单元/集成/硬件测试、CPU 数值参照与性能实验均在服务器 Docker 内执行。** 本地只做代码编辑、Git、调度、同步、已有结果的离线分析/绘图、论文构建与审阅。宿主只做连接、容器管理、中转和状态核验。

优先复用用户容器；先检查 `docker ps -a`、挂载和已有进程。只有核实无可用容器时才新建并记录原因，新名称必须含 `chijin`；不能因已有名称不同或容器停止就替换它。容器内用独立源码/构建/venv/cache，保留用户现有环境。不得默默用旧 `_native` 库搭配新 Python 包。

三后端测试进程必须打印并保存：工具/FlagTree Git commit、实际导入路径、native 库路径/hash、版本、设备物理身份、可见编号、容器/镜像身份。不同后端可以有不同受支持编译器版本，但测试必须明确来自本轮相同工具源码版本。

PRO6000 Docker 根盘曾只有约6.3GB空闲，已有绑定盘充足；重依赖/缓存/LLVM/构建放绑定盘，不重新拉巨型镜像到根盘。复杂 SSH 传输优先 `/tmp` 中转或 stdin。不能修改宿主驱动、daemon、权限，也不能结束其他人的任务。

同一设备的 GPU 测量串行；三个服务器可并行。记录自己的设备预约、PID、日志、timeout、退出码。连接断开先查远端终态，不能盲目重试。

## 5. 已发现问题：启动时复核，不能直接当作已修复

在准备时的 `detailed-profiler` 代码中：

1. `Profiler/python/flagtree_profiler/profile.py` 的 `_find_kernel_event` 按名称/顺序匹配，`_internal_timeline_events_for_run` 按 cycle span 比例映射到 kernel/host 区间。这是相对示意缩放，不是实测时间校准。正式实测模式必须移除这类无证据匹配/缩放；旧视图若保留，显式隔离并标为示意，不能默认进入诊断证据。
2. `Debugger/lib/Instrumentation/Passes.cpp` 的 `reserveDeterministicRecordSlot` 按 instance+静态site定位。一般动态循环会重复写同一槽位，不能据此输出完整迭代历史。固定快照与动态事件日志需分离；检查实际 lowering 后再确认各受支持情况。
3. Debugger 的内部时间路径使用 Ascend `SYS_CNT`，`_kernel_internal_timeline_supported` 仅允许 Ascend；不能宣称已泛化到所有后端。
4. 新 `_report` 要求规范化 `activity.kind`，旧 producer 记录会进入 rejected/原生 trace fallback；现有 `_backends.py` 的外部 counters 扩展主要为 TCU。需要核实 NVIDIA/CANN 的实际接入，不把通用 mock 测试当硬件适配。
5. 已有 LaunchHook 的 source/binary/arguments、TrackedOpTable 的 op/scope/source 元数据、bundle/TCU/replay边界可以复用；它们尚不等于最终 actor/worker/buffer/dependency 映射。

## 6. 三机制实现合同

先审计代码和编译流程，记录具体设计、字段语义、支持边界、预期测试，再逐步实现。可以选择现有 IR metadata+passes、dialect 扩展或其他最小充分方案；不得先宣布必须新建 IR 再寻找理由。

### M1：程序—执行映射

- 源 region/op 有明确身份；记录实际 binary 与编译配置。保留 source→lowered operation→logical program→backend actor/work-group 的对应，并处理支持范围内的拆分、融合、复制、流水化。
- 映射可使用符号/范围表达，不要求枚举所有数据元素。静态 ownership、逻辑请求字节、编译资源和实测活动分开标记。
- NVIDIA：受支持归约/矩阵族的 program、warp/lane或协作组布局与源区域关联。
- GCU：向量 work-item、元素 ownership、partial exchange/同步及可取得的资源信息；不将其误标为 NVIDIA SIMT。
- Ascend：tile→AIC/AIV、workspace、readiness event、循环/缓冲及生产消费边；明确哪些来自编译产物、哪些在运行中观测到。
- 编译变换后无法保持精确归属时显式返回 partial/ambiguous/unsupported，不能用名称或猜测填完整图。所有受支持承诺必须有一般化实现，不允许依赖 `softmax`/`matmul` 名称、特定shape或Study代码行号。

### M2：执行语义感知观测

- 定义 typed observation：对象、事件语义、采集位置、来源、单位/时钟、粒度及条件。共用请求可lower到不同原生机制，保留厂商扩展。
- static snapshot 与动态 occurrence trace 使用不同记录策略。动态记录支持 invocation/program/actor/event site/occurrence；能识别iteration或buffer时显式记录，不能把 occurrence 序号冒充源循环变量。
- 动态记录支持选择实例、事件及采样/容量限制；保留截断/丢记录统计。不要为低开销模式引入全设备共享原子争用或强制同步。
- GPU reuse现有instrumentation路径须审计其继承语义；在受支持Triton编译路径上验证，而非只用手写Gluon例子证明全支持。
- Ascend 在实际producer/consumer、既有wait/event、loop issue处采集；优先复用Study验证过的SYS关联思路，移除特定kernel的LLVM文本替换依赖。
- GCU 支持后端映射和TCU/SIP观测，并实现可用的动态细节。计时有已核验clock时才转换单位；只能获得原始tick时保留tick/domain，明确不能得出微秒阶段成本。若真实SDK没有某种事件，报告具体限制，不能借静态示意补实测。
- 时间戳围住异步发射不自动表示completion或enginebusy。不得新增完成屏障后把改变的程序当原程序；必要同步测量独立标注并核验扰动。
- 外部TCU/msprof回放由正式入口管理，保留每个replay身份、工具版本、命令、scope、原始数据；不自动重放有副作用的应用，不把末次活动和多次计数器伪装为同调用。

### M3：关联、时钟与重建

- 用实际scope/correlation/launch身份连接native records、instrumented invocation和编译manifest。device/process/session/stream/task等可用身份参与消歧；未知身份保持未知，不用0占位。
- 支持相同名称不同binary/shape、重复调用、多stream和混合kernel；不以名称或出现顺序作为可靠关联依据。
- clock记录domain、tick/unit、origin、wrap策略、转换依据、对齐状态和适用scope。仅在同调用及核验关系成立时画跨actor对齐；不强行把所有backend时钟统一成一条全局轴。
- Ascend joint验证应成为工具可调用机制；NVIDIA/GCU用各自实际支持的时钟/原生关联。独立replay不可拼接为同时执行。
- 共用分析允许backend-specific事件与计数器。TCU配置级/SIP aggregate保留其scope，无证据时不关联到单launch；PMU可重叠activity不堆成互斥wall-time。
- 用户报告贯通 source/config→执行映射→动态观测/原生counter→可核验对照。source-control、native lifecycle和enginebusy不同图层，不制造自动因果结论。
- 统一bundle保留原记录、缺失原因、映射、动态events、clock证据和collector provenance；schema版本兼容/迁移明确，文件不可覆盖，采集失败仍可恢复诊断。

## 7. 代码质量和测试定义

测试必须验证外部行为与语义风险，不写仅镜像实现的测试。复用既有Python/C++测试和实际编译管线；新公共合同/解析器/动态协议/身份与clock处理需对应回归。所有测试在Docker内跑，mock只能验证契约，不能算硬件通过。

启动时写清测试文件/命令、oracle、预期断言、设备、必要依赖；阶段完毕记录实际结果。按下列合同建立测试入口，不以“全量pytest退出0”替代覆盖解释。

现有离线契约回归的起始命令如下，**仍须在远端Docker内运行**。`METHOD_SOURCE`设为该容器内本轮源码目录；安装依赖和核实实际路径后执行，不能直接使用本地audit目录或旧包：

```bash
python -m pytest -q \
  "$METHOD_SOURCE/Profiler/test/test_report.py" \
  "$METHOD_SOURCE/Profiler/test/test_portable_capture.py" \
  "$METHOD_SOURCE/Profiler/test/test_launch_metadata.py" \
  "$METHOD_SOURCE/Profiler/test/test_tcu.py"
```

这些测试是解析/合同基础，不替代native、编译、内部观测和硬件验收。检查已有`test_api.py`、`test_profile.py`、`test_instrumentation.py`及各backend测试，针对实际改动记录适用命令。新增T2/T3/T4语义与三backend硬件测试应放正式测试目录，给可重复命令或测试runner，并明确依赖/设备选择；不能只留一次性shell实验结果。C++记录/decoder/pass修改需运行相应现有unit/lit或新增回归，实际target从CMake配置确认后记入记录。

| 测试组 | 必测情况 | 通过证据 |
|---|---|---|
| T1 协议/导入/导出 | 缺字段、未知事件、单位、NaN/无穷、截断、未知schema、不同replay/统计scope、完整原记录和relative paths/hash | 可靠输入可解析；坏记录拒绝或明确降级；不默默丢弃、填0、改计数单位；bundle round-trip保持身份与语义 |
| T2 编译映射 | inlining、支持的fusion/split、循环复制/unroll/pipeline、条件分支；同源码不同配置；不同源码同名 | 与真实最终编译产物及人工/独立oracle对应；保留一对多/多对一；无源的生成op和丢失映射显式可见 |
| T3 动态记录 | 不同循环次数、runtime branch、多个实例、buffer轮转；小capacity、采样、多次launch | 选中执行的occurrence数量与编译/控制oracle一致；不覆盖历史、不混launch；overflow/截断计数可核验；未执行分支不伪造记录 |
| T4 时间/身份 | 相同kernel名不同binary/参数；重复调用、多stream、并发、异步API、未知IDs、clock wrap、无/有校准 | 可唯一关联的才关联，ambiguous留显式状态；已知clock转换遵守实际分辨率/独立校准误差预算；不按kernel时长缩放，issue不冒充busy |
| T5 正确性/扰动 | native off、native capture、selected detailed；数值、额外输出/workspace、编译资源/同步变化 | CPU或独立成熟参考检查数学输出；插桩控制的新增同步/资源可解释；输出错误、race、越界、静默漏记录为阻断 |
| T6 产品/恢复 | API和CLI、不需手工后处理；异常退出、SDK缺失、权限、finalize异常、输出冲突、嵌套session、支持范围内的graph replay | hooks/buffers/进程释放，原应用异常保留，错误信息可操作；失败/部分结果不冒充成功；旧公开入口兼容或提供明确迁移 |

### 三后端真实硬件验收

1. 三后端均完成从本轮源码的真实编译、模块/native路径核验、向量加法smoke、native活动、source/binary/argument关联及正式bundle输出。SDK要求不同可以，不能一台只用mock。
2. 原六算子至少三个shape，数学语义/输入固定，CPU参照在对应Docker内。覆盖tail、不同配置和多次调用；数学容差继承已有合同，改动须给理由，不放宽来掩盖错误。
3. CANN融合长K和GCU尾部归约两个Study案例经**正式工具入口**重现所需诊断信息；不再运行专用kernel改写脚本才获得这些能力。比较旧研究原始证据，容许合理测量变动，禁止硬编码旧数值或ID。
4. 至少一个预先选定、非Study kernel 的保留验证任务（例如RMSNorm或另一融合），加变动shape/config，证明不是针对两个名字写的实现。测试前记录任务与oracle，不按成功结果换测试；失败后修机制或缩小承诺并报告。
5. 按T3/T4做真实动态循环和身份压力microbench；支持多stream的backend必须验证，真不支持的执行方式显式拒绝而非伪成功。没有kernel图层而只有host API数据不能算native采集通过。
6. NVIDIA至少取得选中实例的有语义内部观测；GCU至少取得实际ownership、动态记录及TCU/SIP的真实导入；Ascend至少取得实际actor/dependency、动态迭代及同调用source-control时间关系。不强制三backend都有相同counter或hardwarebusy，但每个“已支持”观测必须真实。若关键能力无法安全实现，记录未完成，不用通用unknown结果替代验收。

### Fidelity、性能和重复测量

- 静态关系用最终产物/独立oracle检查；动态identity/count要求精确（采样/overflow除外，但须满足声明的规则）；时间误差预算由实际tick、SDK精度和独立校准测试预先确定。不能以固定宽松百分比掩盖伪关联或伪时间。
- 同设备固定输入/配置，随机或交错native off/native/selected detailed，至少3批×30调用，预热、profiling、传输和CPU参照分开；保留全部样本。记录共享设备与clock条件，不声称精确性能普遍值。
- 同时报告device-task扰动、host开销、编译时间、buffer/trace空间和分析时间。默认采集与用户显式选择的完整trace分开，不能用最重模式代表所有模式。
- 工程目标：原生默认模式device中位扰动争取≤5%，选中实例的默认detailed模式争取≤10%。这些是优化目标，非时间精度保证或跨设备硬阈值。超出时先查采样/记录/额外同步，给具体可用模式及代价；不得删异常或改阈值宣称达到。无法给出实用模式时属于产品未完成，返回原因。
- 复现旧P/R的方向与内部机制，但不强求旧绝对微秒数；若新测量揭示旧解释错误，记录并修正文，不强行保持故事。
- 原有C++/Python相关测试、三backendbuild和集成回归通过；失败不吞异常，不把skip计pass。运行修改文件的格式/静态检查，必要时编译期检查ABI/内存安全；不凭覆盖率数字宣称质量。

## 8. 实现顺序与技术证据

| 阶段 | 交付物 | 转入下一阶段的条件 |
|---|---|---|
| I0 审计/冻结 | baseline、三环境、继承/新机制清单、具体设计和测试命令 | 实际路径清楚，已有工作保留，无空泛新IR承诺 |
| I1 可信采集 | 修名称关联/比例缩放；三backend规范native records与bundle | T1/T4/T6相关通过，真实native smoke及身份一致 |
| I2 编译映射 | 编译manifest、source/actor/ownership/dependency关系及变换规则 | T2支持范围通过，两Study映射从正式机制导出 |
| I3 细粒度观测 | 动态日志、语义lowering、clock关联、TCU/CANN采集入口 | T3/T4通过；三个backend有各自真实观测与明确边界 |
| I4 工具与证据 | 单一入口、三backend回归、保留任务、fidelity/overhead与机制对照 | T1–T6完成，产品行为能独立复现 |
| I5 正文/独立审阅 | 实现相符的方法、实现/评价段落、冻结包、三报告 | 技术验收与贡献判断分别完成，进入第10节迭代或停止 |

阶段可按依赖交错实现；不为表格串行化三个独立backend。并行工程子agent可使用用户本任务授权，但明确代码写入边界和设备所有权；不能同时修改共享文件或在同卡测性能。根agent负责集成、测试和结论，不把“子agent已完成”作为验收。

至少为三个机制各保存一项具体证据/对照，避免方法变成适配列表：

- 映射：编译变换或actor展开后，缺少执行映射会留下哪个归属问题；新机制如何保持/限定归属。
- 观测：同一程序级请求在两个后端如何选择不同site/primitive；在一个异步/依赖案例中验证语义而非只数记录。
- 重建：可靠身份/clock与名称顺序/比例视图的区别，由受控重复/并发或跨actor案例证明。旧不可信路径只作为明确标注的回归/对照，不进入用户可信结果。

不需要另开Proton/KPerfIR跨设备移植或工具benchmark；比较novelty依据真实原文/实现。通用schema扩展、编译pass基础和已有provenance思想不能直接当独有新技术。

## 9. 方法正文

用户要求完成实现后按实现写一版正文。唯一维护 `paper/main.tex` 和其引用tex；不要创建 `method_design/`、额外方法tex或另一套正文。

- `04-design.tex` 用三机制作为主体：程序—执行映射、语义感知观测、程序关联重建。profiling请求/合同是共用入口，可放节首；collection按机制3展开。
- 每节交代Study引出的具体困难、抽象/数据模型、算法/变换/验证规则、后端特化及设计取舍；给至少一个贯穿例子，不只介绍模块、接口、文件名。
- 如实现只是metadata+passes，如实写；如新dialect，解释为何需要、继承什么、怎样保持观测语义。讨论partial映射、异步语义、动态次数、replay/clock约束，避免“统一接口解决异构”空话。
- `05-implementation.tex` 写真实组件、版本与现有/新增边界；`06-evaluation.tex` 写已经完成的验证及限制，未做内容留准确TODO。同步Introduction贡献和Related Work的具体比较；不把尚未实现方案写成结果。
- 优先简短逻辑和可核验机制；保持用户希望的简洁Study，不把工程日志塞进正文。方法图由实现生成/准确描述，不用假时间或能力矩阵当实证。
- 不扩大Study因果：A成本联合变化；B program0不是全launch；TCU/PMU独立回放；逻辑payload不是physical DRAM；bounded N不是全局最佳。
- 改写后构建PDF，检查undefined refs、Overfull、float/page溢出；渲染实际单栏/双栏尺寸审阅图文。需要图时优先矢量学术图，不用AI生成科学数据。

## 10. 三位独立 reviewer 与迭代

工具核心和I4通过后，冻结同一包：Git commits、设计正文/PDF、实际代码入口、测试/失败摘要、完整证据索引、nearest prior-work原文locators、继承/新增清单、限制。独立上下文，不给peer报告，不要求肯定结论。最多根+三席并发；记录实际模型，不冒称三个不同模型或真实会议审稿。

| reviewer | 主要责任 | 必须回答 |
|---|---|---|
| R1 技术novelty | 对照最接近compiler-assisted/instrumentation/profiling工作，核查具体机制 | 新的是哪项机制？为什么不只是已有机制的backend移植？哪个技术差异缺证据？ |
| R2 系统贡献与OSDI故事 | 跨backend服务、用户问题、一般性、operational/evaluation证据 | 贡献是否与真实问题相称？三机制是否必要且连贯？当前材料距OSDI标准缺什么？ |
| R3 正确性与证据 | 时间/身份/编译语义、动态日志、回放、测试和开销，以及正文是否超出实现 | 技术结论可信吗？泛化和代价有何缺口？具体应补哪个实验/实现还是改表述？ |

每席输出：blocking/major/minor，主张→代码/证据/原文锚点，支持的贡献与不支持的贡献，限定可接受否，以及每项问题的分类：

1. **实现缺口**：可补的算法/编译机制/关联策略/后端语义；给明确技术工作及验证要求。
2. **证据缺口**：可取得的保留任务、fidelity、对照、overhead、实际使用记录；不能用改文代替缺失证据。
3. **表达缺口**：机制已经实现和验证，表述/比较/归因错误；改文后复审。
4. **结构性不足**：结果只有工程适配，nearest work已覆盖机制，或核心主张需要当前无条件取得的真实operational经验/设备；明确原因与最小新增条件。

根agent审阅每项意见，记录采纳/不采纳及依据。不能把“投OSDI一定够”设为硬要求，也不能按三票多数忽略一个有证据的正确性阻断。

**可修复则继续**：形成有限、具体的下一轮改动与测试预测；实现、回归、采证、改文、冻结新版本，并再次三席独立审阅。每轮至少有解决明确问题的新机制、新证据或实质文本修正；不能重复无变化审阅、扩大无关功能或换reviewer碰运气。

**不可修复则结束**：说明哪些工具成果仍成立、哪项论文贡献不足、closest work与失败证据、为什么继续加adapter/计数器/换术语不解决、需要什么新条件/研究突破。保留可用代码与负结果。若只是不清楚，先查原文或做能够区分的有限实验，不把reviewer一句否定直接当结构性不足。

若存在实际operational track要求，启动审阅时核对当年官方CFP，并区分技术novelty和真实运营经验；不伪造用户数量/部署时间。当前Study不等于生产部署，不能靠实现工时替代使用证据。

## 11. 环境问题、记录和最终交付

遇到问题先在授权容器内做有限排查：保存命令、日志、PID/exit、实际缺依赖/ABI/权限与已经尝试的修复。能安全修复源码、容器依赖或使用独立构建就继续。

确认需要用户操作的宿主配置/权限、不可获得SDK或机器、磁盘资源等时：停止依赖该环境的任务，保留原始状态；完成不依赖它且有意义的工作后返回用户，提供最小操作和验证命令。不请求已经获得的普通实现/测试授权，不更改宿主配置，不无限重试。不把环境失败解释为novelty不足。

按平台goal规则更新状态：未达到工程验收不能标成功；暂停只依用户请求；blocked遵守重复阻断阈值。允许结束的贡献否定是本任务约定的负结果交付，必须把原因与未达项说明清楚，不能称“profiler和OSDI方法均完成”。

`method_impl_record.md` 顶部始终包含：当前目标/阶段、branch/HEAD、各backend/container/device、活动PID/log/timeout、最后终态、最近测试、review轮次/意见处置、下一条具体命令。每次实质需求、实现、失败、实验、论文修订和审阅追加一条记录。凭据不记录。

最终交付：

- 用户仓库分支与commit/push结果，FlagTree必要patch/commit、安装/运行/复现入口。
- 三backend真实支持的观测、支持边界、测试通过/失败/skip及fidelity/overhead结果。
- 实现对应的唯一方法正文与PDF，以及三独立review报告/处置。
- 工具工程验收和论文贡献判断两个结论；不足或环境阻碍的具体原因、需要用户处理的条件。
- 无遗留自建GPU采集进程；用户容器/原有代码和数据保留。

开始后持续执行上述闭环，不在给出方案、接口骨架、mock测试或首轮review后自行结束。
