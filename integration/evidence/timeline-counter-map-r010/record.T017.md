# FlagPrism 时间线工程记录

## 当前恢复摘要（T017 自动计时位点→真实PTX/SASS PC映射及26capture回归完成；clock/区域边界/Perfetto仍待补）

- 目标：执行 `timeline_goal_prompt.md` 后补齐三后端真实内部时间、动态依赖和Perfetto可用性；用户已显式设置本合同为 active goal，开始真实工程实现。
- 设计基线：`FlagPrism-method` / `detailed-profiler`，准备前HEAD `e6aa804b203d3147925611423c2fcd20cf96bea2`。当前基础usability已完成，完整新timeline能力未交付、未验收。
- 文档：`Profiler/docs/timeline_design.md`；`Profiler/docs/timeline_testing.md`；根合同与 `integration/plans/timeline/goal_prompt.md` 同字节快照。
- 已做：T000 设计基础上完成 T001 可扩展边界、P01–P10/最小实证和合同更新；三个独立 GPT-6.1-Sol/xhigh 请求的设计初审及有限复核已完成，文档确认问题已关闭。实际 serving 型号未暴露，核心设备机制仍待 P01。
- 当前未通过：三后端完整自动timeline、经过ISA/时钟验证的动态time arrows、Perfetto、独立六数学及最终三代码走查。已有NV完整64bit原始记录、完整相关cp.async IR边界和真实逻辑group/wait事实；GCU clock原语与公共clock算术。没有一个后端整体P01完成。
- T013公共raw schema已接真实API/CLI；21capture/10816物理记录→5400真实区间+16缺失端点，400逻辑组；真实K1021溢出报告12352 overwritten，丢失不推断组/依赖。15新合同normal/-O及既有回归通过，原始字节/配对/namespace/source/manifest独立核验。最新r007/install-v2/source d15933a，606安装成员，native仍与545逐字节相同，parent launcher ABI2。六jobs terminal/worker gone/controllers仅Z；最终GPU15MiB/util0无compute-apps。clock和机器边界未证、无Perfetto/P01，TP/UI代理询问仍待。cuobjdump/nvdisasm仅PATH未找到，下一步定位/安装而非判硬阻碍。
- T015：已取得13.2.86真实nvdisasm/cuobjdump（独立prefix），反汇编r007两cubin及新校准cubin，实际JSON/源码PTX行/完整CFG。新校准先因eager event包含host提交gap失败；改用外部event-node专用graph，捕获0执行、显式9次数学/State1..9，同binary跨K4096/16384/65536、原10us/2%一致性门通过。源码858f5eb7、结果及完整失败保留；不是细粒度误差/跨SM epoch认证，无pftrace/P01。SASS确认K-load能越过源码timer，部分prologue getter非谓词化（再SEL值）；不能由IR位置/采样gating冒称最终边界或全部未选读钟已消除。当前无新增runtime/native代码，r007安装继续有效。原件和下一步见T015。
- T016：已实现自动LLVM SSA begin/operand/end结果依赖、按位类型转发与getter ~{memory}；新native boundary ABI1、版本拒绝和缓存依赖。初始99版本错误保留并修复。最终source/native a9ea010、独立install-v3，26真实timestamp captures（21原回归+5types）、11456raw/5720pairs+16orphans/400logical groups/12352overwritten；FP16/BF16/FP32/FP64/int64精确math/input/tail/副作用/实际LLIR依赖及clobber通过，7最终cubin真实SASS/JSON/CFG，无MEMBAR。仍只是LLVM约束，所有canonical boundary/clock保持unverified，无pftrace/P01，下一步必须补适用clock/error/window与最终per-site/participant/动态buffer复用证据，不能把SSA/memory clobber当机器完成证明。详见T016末。
- T017：native marker ABI1 真构建34fe5e2；f5731a0操作数矛盾负例修复；真实PTXAS首轮5dtype失败定位到marker空白与调试元数据清除，通用修复5d042b0。新install-v3 wheelSHA d41bd2c0f2da1625feeb538415d00878359a2f6e43fd360beef9ac957455faf4，7native byte桥相同、607成员核；machine17/public4 normal-O通过。最终真实26capture/7cubin/140静态getterPC全部exact debugline绑定，11456raw/5720pairs/16orphans/400logical groups/12352overwritten。原失败及新26capture工具/数学原件保留；仍不是源区域最终边界认证，clock/physical generation/Perfetto未完成。恢复按T017末新安装路径，不用T016旧安装。
- 保留边界：旧count/SDK/资格/论文/Study数据不改；NVIDIA性能/开销认证仍暂缓，时间线功能与时钟验证为新目标必达。
- 下一步：按修订后的设计8.7/8.8及验收8.3继续NV完整自动时间链；实际记录v2位宽已验证。T008已修真实GEMM async候选漏采并得到完整逻辑group/wait事实。T010已完成NV紧凑首末program采样及实际grid/canary/数值验证；T011已补独立owner/延迟读回模块和真实两stream开发验证；T012已接入公共hook/API/CLI原始时间戳阶段；T013已形成canonical raw schema/实际NVIDIA规范化和损失语义；下一优先实际clock单位与最终机器边界证明、规范ns视图/Perfetto；逻辑事实尚不能当verified time arrows；GCU clock/async、Asc真实区间/actor时钟/logger；公共时间模型/Perfetto及全目标。同版构建/安装/数学不重复运行。具体当前source/installed/wheel见T013，最新时钟/工具证据与下一动作见T015。

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
- 九个owned build/install/device jobs全部terminal；实际PID/startticks核workers missing/controllers仅Z，含所有实际工具命令已结束。最终GPU15MiB/util0/no compute-apps，不清PID1/他人任务。公开小证据和可复现字节审计将写 integration/evidence/timeline-counter-map-r010。
- 下一优先：用精确PC映射核各site实际区域/路径与participant证据，必要时修通用lowering；取得适用于细粒度区间的clock比例/量化/端点误差及有效窗口，形成不改raw的ns视图与标准Perfetto。还须physical buffer/flag两轮真实复用、GCU/Asc完整timeline/P01、独立六数学、受控case、Trace Processor/实际UI与最终三额外GPT-6.1-Sol xhigh代码走查。TP/UI下载代理问题旧请求仍待，没有把此当当前实现全面阻碍。完整goal保持active，未complete/blocked。
