# FlagPrism 时间线工程记录

## 当前恢复摘要（T018 共同因果时钟边界算法/真实跨SMID校准通过；TP已可运行，clock完整资格/区域/Perfetto仍待补）

- 目标：执行 `timeline_goal_prompt.md` 后补齐三后端真实内部时间、动态依赖和Perfetto可用性；用户已显式设置本合同为 active goal，开始真实工程实现。
- 设计基线：`FlagPrism-method` / `detailed-profiler`，准备前HEAD `e6aa804b203d3147925611423c2fcd20cf96bea2`。当前基础usability已完成，完整新timeline能力未交付、未验收。
- 文档：`Profiler/docs/timeline_design.md`；`Profiler/docs/timeline_testing.md`；根合同与 `integration/plans/timeline/goal_prompt.md` 同字节快照。
- 已做：T000 设计基础上完成 T001 可扩展边界、P01–P10/最小实证和合同更新；三个独立 GPT-6.1-Sol/xhigh 请求的设计初审及有限复核已完成，文档确认问题已关闭。实际 serving 型号未暴露，核心设备机制仍待 P01。
- 当前未通过：三后端完整自动timeline、经过ISA/时钟验证的动态time arrows、Perfetto、独立六数学及最终三代码走查。已有NV完整64bit原始记录、完整相关cp.async IR边界和真实逻辑group/wait事实；GCU clock原语与公共clock算术。没有一个后端整体P01完成。
- T013公共raw schema已接真实API/CLI；21capture/10816物理记录→5400真实区间+16缺失端点，400逻辑组；真实K1021溢出报告12352 overwritten，丢失不推断组/依赖。15新合同normal/-O及既有回归通过，原始字节/配对/namespace/source/manifest独立核验。最新r007/install-v2/source d15933a，606安装成员，native仍与545逐字节相同，parent launcher ABI2。六jobs terminal/worker gone/controllers仅Z；最终GPU15MiB/util0无compute-apps。clock和机器边界未证、无Perfetto/P01，TP/UI代理询问仍待。cuobjdump/nvdisasm仅PATH未找到，下一步定位/安装而非判硬阻碍。
- T015：已取得13.2.86真实nvdisasm/cuobjdump（独立prefix），反汇编r007两cubin及新校准cubin，实际JSON/源码PTX行/完整CFG。新校准先因eager event包含host提交gap失败；改用外部event-node专用graph，捕获0执行、显式9次数学/State1..9，同binary跨K4096/16384/65536、原10us/2%一致性门通过。源码858f5eb7、结果及完整失败保留；不是细粒度误差/跨SM epoch认证，无pftrace/P01。SASS确认K-load能越过源码timer，部分prologue getter非谓词化（再SEL值）；不能由IR位置/采样gating冒称最终边界或全部未选读钟已消除。当前无新增runtime/native代码，r007安装继续有效。原件和下一步见T015。
- T016：已实现自动LLVM SSA begin/operand/end结果依赖、按位类型转发与getter ~{memory}；新native boundary ABI1、版本拒绝和缓存依赖。初始99版本错误保留并修复。最终source/native a9ea010、独立install-v3，26真实timestamp captures（21原回归+5types）、11456raw/5720pairs+16orphans/400logical groups/12352overwritten；FP16/BF16/FP32/FP64/int64精确math/input/tail/副作用/实际LLIR依赖及clobber通过，7最终cubin真实SASS/JSON/CFG，无MEMBAR。仍只是LLVM约束，所有canonical boundary/clock保持unverified，无pftrace/P01，下一步必须补适用clock/error/window与最终per-site/participant/动态buffer复用证据，不能把SSA/memory clobber当机器完成证明。详见T016末。
- T017：native marker ABI1 真构建34fe5e2；f5731a0操作数矛盾负例修复；真实PTXAS首轮5dtype失败定位到marker空白与调试元数据清除，通用修复5d042b0。新install-v3 wheelSHA d41bd2c0f2da1625feeb538415d00878359a2f6e43fd360beef9ac957455faf4，7native byte桥相同、607成员核；machine17/public4 normal-O通过。最终真实26capture/7cubin/140静态getterPC全部exact debugline绑定，11456raw/5720pairs/16orphans/400logical groups/12352overwritten。原失败及新26capture工具/数学原件保留；仍不是源区域最终边界认证，clock/physical generation/Perfetto未完成。恢复按T017末新安装路径，不用T016旧安装。
- T018：880706b共同因果offset区间交集实装；新9/旧27 clock CPU合同normal-O、新独立607成员install-v1、7native字节不变。真实双CTA/64轮×3次公共算法调用，SMID0/1所有训练/留出0offset相容，四GT实际SASS/JSON/完整CFG，GPUtext与前版一致；不是绝对误差/全设备epoch认证。TP57.2已从官方bucket虚拟主机取得并与旧pin逐字节一致，GCU/NV实际version/help通过，NV路径/workspace/chijin-timeline-r011/tools-input/trace_processor_shell；TP下载障碍已解决，不再等用户代理。UI官方API资源469355212/15402304bytes已定位；初流式任务实际terminal1保留7471104bytes，现HTTP206断点续传 ui-resume-v1 owner374793/worker374794（start1004952132/1004952135），最后实测live且10158080bytes。恢复先poll此handle，不重启旧下载。
- 保留边界：旧count/SDK/资格/论文/Study数据不改；NVIDIA性能/开销认证仍暂缓，时间线功能与时钟验证为新目标必达。
- 下一步：先poll GCU `/tmp/chijin-timeline-tools-r011/ui-resume-v1` 的实际PID/terminal与字节进度；当前clock源码freeze880706b、NV独立安装r011/install-v1，TP在r011/tools-input（57.2已实跑）。用现有真实PC映射/因果探针补最终site/participant边界、时钟尺度/端点误差/有效窗口与跨主体适用范围，接共同ns派生视图/标准Perfetto及真实SQL/UI；还须物理buffer/flag复用、GCU/Asc producer/P01、独立六数学与最终三额外Sol6.1/xhigh走查。未变化的native/26capture不重复运行；具体冻结、失败和进程证据见T018末。

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
