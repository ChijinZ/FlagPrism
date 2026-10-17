# FlagPrism 内部时间线与 Perfetto 工程执行合同

## 0. 何时启动，什么才叫完成

只有用户明确通过 `/goal` 指定本文件后，才启动实现、连接服务器或设备实验。**准备/提交本文件不是启动授权，也不要因为本文出现 goal 字样自动创建目标。**

用户目标：普通算子开发者把自己可运行的 Triton 算子和普通启动脚本交给 FlagPrism，无需改 kernel 内部/写 scope/填 site/手改 LLVM，就能采到真实、详细、语义明确的内部时间信息，导出在标准 **Perfetto** UI 中看得懂、可追溯、能帮助调优的时间线。三后端都要完成，不把 count-only、整核条、静态图或可打开的空文件当作成功。

本轮只有工具工程、测试、安装和工具文档，**不改论文、不构建 paper、不动旧 Study 数据**。代码可以超过旧论文或旧工具边界；不用论文 novelty 评审代替产品工程。旧 `usability_goal_prompt.md` 是基础能力/质量标准来源；新时间线目标不能退回旧计数最低线。

## 1. 先读的材料与当前事实

工作区 `/home/jin-lab-pc/workspace/osdi_flagprism`。先读：

1. 本文件、`timeline_impl_record.md`、适用 `AGENTS.md`，核实际 Git 和进程终态。
2. `FlagPrism-method/Profiler/docs/timeline_design.md`：事件、时钟、后端、协议、依赖和 Perfetto 设计。
3. `FlagPrism-method/Profiler/docs/timeline_testing.md`：真实算法、冻结矩阵、raw/clock/Perfetto/UI 门槛。
4. `usability_goal_prompt.md`、`method_impl_record.md` 顶部及当前公开 `automatic.md`、`semantic_profiling.md`、后端 build recipes、真实源码。

设计准备时正式仓库 `FlagPrism-method/` 的 `detailed-profiler` 为 `e6aa804b203d3147925611423c2fcd20cf96bea2`；随后只会新增本设计文档提交，以实际 HEAD 为准。已安装 component Python a829；native 最后实质 changed-source build bd61；SDK/build工具基线 cb968。旧基础功能 goal 已完成，不能把这些结果冒充新 timeline 实现通过。

| 后端 | 已验证容器/解释器定位，执行前再核 |
| --- | --- |
| NVIDIA | `chijin-study-pro6000`；`/workspace/chijin-r15-python-alignment-r2/venv/bin/python` |
| Enflame | `flagprism-enflame-dev`；`/workspace/chijin-r15-python-alignment/venv/bin/python` |
| Ascend | `chijin_v3.5.x`；`/tmp/chijin-r15-compiler-identity-install-v2/venv/bin/python` |

Ascend 已有 isolated fixed SDK `/tmp/chijin-r15-sdk-scalar-legality/install-fixed/bin/bishengir-compile`，SHA `1f5cc5054402e901add18af133b3495b861775d68e2113bb8ba94667eef6cf9e`。先核真实 byte/资源/环境，不凭旧路径假定有效。需要改变源码/ABI/SDK 时使用新明确版本和隔离安装，不改旧收据。

根目录不是 Git 仓库。本合同根目录版本为执行入口；`FlagPrism-method/integration/plans/timeline/goal_prompt.md` 是同字节已跟踪快照。设计阶段只维护同一合同内容，必要更新须同步快照并记 SHA；执行中不能自行降低合同门槛。`timeline_impl_record.md` 是本阶段唯一 live 工程记录，T000 起编号，不覆写旧 usability 完成结论。

## 2. 不能降级的产品要求

### 2.1 无逐算子适配

- 正常启动脚本只执行请求次数。自动发现/插桩/采集不要求 scope、site ID、额外 scratch 形参、维护者脚本或已有 profile。
- 产品不得按算子名、文件名、shape、固定 SSA/site/hash 选择算法。修通用 IR/控制流/布局/后端原语，并用不同数学验证复用。
- 不把普通可运行但 timeline 失败的输入改记 unsupported。编译能力边界在 baseline 前明确，失败原件保留。
- 手工 scope/高级选择继续支持但不代替自动基本模式。

### 2.2 三后端真实时间与流水

三个后端分别必须得到：

1. 多个实际设备内部时间段；非平凡样本至少两个不同源区域、多个正 duration，循环可见多个真实 occurrence。
2. 源码/编译区域、binary、实际调用、program/observer 和原始记录可关联。
3. 可验证时间尺度，原 ticks/位宽/epoch/单位/误差保留。未知 tick 频率不是 ns，未知 epoch 不是共同时间轴。
4. 每后端至少一个实际异步生产消费案例：真实 submit/wait/completion 与 token/group/buffer generation 的动态关系，支持目标泳道比较的时钟证据。
5. 事件类型直接看懂：observer elapsed、issue、wait、completion checkpoint、原生 engine activity 分开；source 位置不等于硬件引擎，issue 不等于 busy。
6. 同次 capture/调用的数据不串联，不跨 replay、不同 GPU 或独立时钟域捏造重叠。
7. 有损/不完整/未选择都可见；没有 end 不补 kernel-end，没有时长不按计数均分。

本轮完整目标不是“所有物理指令的完美硬件 busy 图”，但也不能缩成单一软件框图。只有有证据的 native engine begin/end 才称 engine activity；同时三后端的真实内部 interval 与异步解释案例仍为必达。某后端没有做到，不标整体完成，报告明确的技术/环境原因。

### 2.3 真正的 Perfetto 交付

- 三后端提供标准 `.pftrace` 与清晰打开入口，Trace Processor 真导入、SQL 与原始 bytes 对照、标准 Perfetto UI 真打开；自写网页/JSON 校验/截图示意图不能替代。
- 泳道可区分调用、program、实际 observer、语义；slice 详情包含源位置、begin/end/raw tick、时间单位、clock/error、occurrence、token/generation 和原始证据 ID。
- flow 只能来自有依据的动态关联，静态候选与歧义明确分开。
- 未连接 clock 域可在独立 trace 降级展示；它不自动完成需要跨主体比较的异步案例。不能把所有域归零后放同一图暗示并行。
- 保留旧 count/native/interval 格式与恢复合同，支持版本化新 schema，不覆写历史数据。

## 3. 允许且必要的实现范围

允许改 FlagPrism、配套 FlagTree、必要 SDK 通用 pass/接口、native ABI、隐藏 launch ABI、自动 planner、时钟 getter/correlation、事件协议、源关联、trace exporter、报告和构建集成。以实际实现而不是旧论文为边界。

建议入口 `--detail timeline` / `detail="timeline"` 尚未实现，可以经设计核定；不得把候选名字写成已有功能。旧无 detail 的 native 模式、`--detail auto` 计数语义不被静默替换。

具体工作链：

`现状实证 → 原始事件/发布协议 → timer/clock 证明 → 自动源区域时间插桩 → 异步动态依赖 → Perfetto 导出 → 实际算子 SQL/UI → 独立新数学 → 三名最终代码走查 → 修复/受影响复核 → 交付`。

每次泛化修复都保留源→pass→实际编译对象/驱动输入→wheel→installed 与 raw 输出链。不能新 Python 搭旧不匹配 native、依赖未写入文档的 PYTHONPATH/热补丁、或将旧 so 改包装冒称新 C++ 编译。

源码/依赖都相同可以复用原对象，但记录实际改编 TU、link 和依赖 SHA，不能无变化地重复大构建；反过来，新 logger/ABI/pass 必须真正构建安装。SDK 私有文件不进 Git，公开 patch/版本/资源构建方式必须可复现。不得覆写系统 SDK 或修改 host driver/daemon。

## 4. 环境、权限与生命周期

| 服务器 alias | 复用容器 | 初始设备 |
| --- | --- | --- |
| `zhangquan_pro6000` | `chijin-study-pro6000` | GPU0 |
| `zhiyuan_suiyuan` | `flagprism-enflame-dev` | GPU0 |
| `zhiyuan_ascend` | `chijin_v3.5.x`，`sudo -n -u chijin docker ...` | NPU4 |

- 以 `ssh_machines.sh` 和 `scripts/study_remote.py` 为准，**不回显凭据**；复杂传输用 stdin 或 `/tmp` 中转，不假定 scp 目标任意可写。
- 所有依赖安装、build/import/test、CPU oracle、设备实验、Trace Processor 和 browser 均在服务器已有 Docker。工作机只做编辑、Git、调度和留存数据离线审计。
- 复用已有容器，不因燧原容器名没有 chijin 就重建。确实无可用容器才新建，新名称含 chijin 并记原因。
- 新阶段使用独立 source/build/venv/cache/output；旧可用安装和数据保留。NVIDIA 重依赖放已有大容量绑定盘。
- 同卡同一 owner、设备工作串行；三服务器可并行。工作前核实际设备使用和旧任务，不结束他人任务、不擅自reset设备。
- 每个启动绑定源码/脚本 SHA、PID/PGID/startticks/argv、容器设备、预算、日志、退出码。父控制器 wait/reap 自有子树；取消/timeout 只清理身份核验的 owned descendants，覆盖 setsid 子进程，不动 PID1/daemon。
- 观察超时、SSH断开不是设备任务终止。先 poll 同一 handle 或查权威 terminal，不能直接重启采集/大编译。
- 稳定功能和时钟数据采集是本轮必做。NVIDIA 独占性能/吞吐/加速或开销比认证仍按用户此前要求暂缓；不以此跳过时间维度。Ascend/GCU 可在稳定窗口做受控时间/扰动验证，负载污染要记录，不能删除失败或假称独占。
- 若确实需要用户处理网关、权限、SDK或资源，先完成不依赖部分，再给精确原因、已尝试内容和最小操作。不要为已授权普通开发反复要许可。

## 5. 测试注册、预算与独立验收

完整执行 `Profiler/docs/timeline_testing.md`，不是只跑这里的摘要：

- 开发 D01–D06 是真实数学算子，覆盖访存融合、归约、矩阵/融合、运行时循环、异步、tail。
- 独立 qualifier 另写至少六新数学，三类各二。每后端两shape×两config：24 ordinary，再每 eligible 组合 cold一次/warm两次（最多72 profile）。source/input/config/tolerance/预期结构/计时语义在 profile 前冻结。
- 冻结后所有已 eligible 失败仍在分母，不能换名字、放宽 tolerance、跳过难例或换成高级模式。首次通过与通用修复后结果分别记。
- 修复用过的样本不再叫未见；补至少两个独立新数学覆盖受影响结构。允许为 debug 查看最小失败源，记录暴露；不必用永久遮蔽阻止必要调试。
- 原数值/input/canary、合法 side-effect oracle、host-once、raw/time/source/clock/identity/loss、实际 Perfetto SQL/UI 都要过。时间戳来源与边界必须核实际编译产物，不只信 UI 宽度。
- 默认预算：raw 初始8MiB、trace目标16MiB、完整bundle64MiB；冷编译 `min(300s,max(120s,3×ordinary同设置冷编译))`、导出60s。可以用工程测量优化默认采集，不能静默放宽门槛或删必要raw掩盖超限。
- 选择建议首末program、每program≤4observer、≤8逻辑region、每observer≤4096raw records；实现可在开发阶段给出等价更好策略和有限实证，再在资格前冻结。不能在资格失败后改规则然后称首次通过。
- 所有 verifier/authorization/完整性门普通与 `-O` 都显式拒绝伪造，不依赖 assert。原始 bytes 与第一次失败留存，修复输出新版本/目录。
- 遵守测试 E01–E12，覆盖多调用/两stream/graph拒绝与恢复/overflow/cancel、schema/cache/时钟/重复flag generation负例；已支持的并发真实运行，不支持的早拒绝，不能只写文档。
- 每后端实际浏览至少六trace；含至少一个异步、多occurrence/program、source/slice/flow详情。保UI版本/截图/traceSHA/事件ID和浏览前后原bundle hash。

没有正 duration 的非平凡算子、只有单 kernel bar、只有计数或只有checkpoint点，均不算完成。真实极短事件允许量化为零，但正常资格样本需要有足够尺度的内部时间结构，不允许添加无关忙等来凑。

## 6. Git、记录和可复制交付

- 正式仓库 `FlagPrism-method`、远端 `ChijinZ/FlagPrism` 的 **`detailed-profiler`**。必要时开隔离 worktree/topic branch，最终合回正式分支。不是 `detailed_profile`，不合main，不force push、不覆盖用户变动。
- 原 `FlagPrism/` study-and-eval worktree 的未跟踪七脚本和结果目录保持。paper相对最初baseline已有并行差异，不能为“保留性通过”恢复或覆写用户文件；本任务不写/构建paper。
- 按通用机制/后端/测试/文档提交，阶段freeze记实际commit、installed/native/compiler/SDK/wheel hash。最终push前fetch与祖先核，SSH push `git@github.com:ChijinZ/FlagPrism.git` 到指定分支，ls-remote核精确HEAD。
- 维护 `timeline_impl_record.md`：最新支持/缺口、活动owner/PID/argv/日志/deadline、已完成/失败/下一步，T编号历史追加。定期归档不可变快照进Git，根文件不是自动提交。
- 建议测试代码 `tests/timeline/`，独立资格 `tests/timeline_qualification/`，证据 `integration/evidence/timeline-<version>/`，大产物 `artifacts/timeline/` 或服务器持久目录，来源和SHA明确。具体模块位置可按现有结构调整。
- 最终提供真实source-build/安装/诊断、默认采集/导出、Perfetto打开与SQL命令；三后端运行路径；实际trace/截图/数值/时钟证据；限制与失败历史。不写不存在API、不把SDK私有文件或凭据提交Git。

## 7. 结尾三个独立代码走查（必达）

实际功能/独立算子/Perfetto验收完成且冻结版本后，额外启动三个独立 reviewer，不让实现作者或 qualifier 冒充。沿用用户上一轮明确要求：

- 每位 `model="gpt-6.1-sol"`、`reasoning_effort="xhigh"`、`fork_turns="none"`。同一实际冻结版本/公开文档/测试证据，fresh context，不读peer报告/root预期票或旧意见代替实际代码。
- 工具若不支持指定配置，保实际错误，继续其它工作并返回用户处理；不可静默换模型再称满足。记录请求配置、agent ID、工具确认范围；resolved实际型号未暴露就如实写未知。
- 三位都看完整公开链路，各有重点：R1 编译发现/计时插桩/源关联/控制流/cache；R2 timer/epoch/跨主体依赖/记录ABI/发布/损失/并发与生命周期；R3 CLI/API/Perfetto单位/track/flow/SQL/UI/安装/文档与真实可解释性。
- 只读代码审阅，不改产品，不在本机import或跑测试，不擅自访问设备。需要复现给最小用例，由root排队到已有Docker。
- 输出 confirmed blocker/major/minor、verification gap 与 optional 分开，含代码位置、触发、实际证据、建议验证、阅读及未覆盖范围。不能以“看起来有时间线”给肯定票。
- Root逐条核实。确认的正确性/默认体验/安装/时钟或假关联缺陷要通用修复并回归；其它不采纳有明确依据。修复冻结新版本，相关席独立有限复核，跨边界通知其它席。
- 无变化不重跑全量矩阵/代码审阅；文档/证据补项只做相应有限delta。实质native/time/clock变化则按真实影响重build/安装/设备/独立资格，不能用旧审阅覆盖新代码。

## 8. 完成审计与返回用户

只有以下全部有直接证据才结束为 complete：

1. 三后端普通可运行kernel默认时间路径无需修改kernel，非逐算子适配。
2. 独立六数学矩阵及必要新泛化全部满足原数值、时间、源、调用、完整性、预算门；首次失败与修复版本清楚。
3. 三后端真实内部多区间/循环和每后端至少一个真实异步依赖案例；时间单位、clock比较和语义没有伪造，缺失没有填图。
4. 标准 `.pftrace` 的真实Trace Processor SQL验证与实际Perfetto UI操作/截图通过，源码/主体/等待/依赖可解释。
5. 两个受控案例能说明某个内部时间/等待/阶段关系；未插桩参照/噪声/扰动的结论与实际许可和证据一致，不许用插桩时间冒收益。
6. 配套三后端构建/独立安装/source-native-ABI/关键故障与回归、旧count/原始数据兼容都通过。
7. 三名额外指定配置的独立代码走查完成，确认问题已处置并必要复核；不以多数投票豁免。
8. Git push/remote HEAD/clean真实核，文档/record/证据完整，无遗留自有设备或browser任务，工具任务未写论文/旧Study。

不能因工程难、缺漂亮case、测试很多或旧版本已可用就结束为成功。硬件/SDK确实无法提供某证据时，保留已做工作和具体最小阻碍，请用户处理；其它后端继续。遵守平台goal complete/paused/blocked规则，不能首次环境波动就blocked，也不能因等待真实live job就重启。

最终回复：版本、三后端真实命令/环境、可打开的本次`.pftrace`与截图路径、能解释的两个案例、测试/首次失败/修复记录、时钟/覆盖/扰动限制、三审阅报告与实际配置、Git状态。**不修改论文。**
