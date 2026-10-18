## T036 NVIDIA 自动边界候选的原件映射与独立安装

- 上一goal turn为progress：R12更新设计/验收、三名独立设计reviewer指出具体缺口并复核文档处置，提交ac8896b；不是实现/设备资格。本轮恢复原完整三后端goal，不改论文，不提前启动最终代码review。
- 补记T035权威结果：native-build-v2完整独立558任务构建成功，controller54145/start17192645，actual wheelSHA26e1881a898db39f360af375c984bbaf9fc3fd8f6d0916eac7d790305a0cae21，目标源码为9d2de1a+明确dirty候选hash；parent只对留存patched archive建立本地snapshot commit，非声称upstream ancestry。第一次native-build-v1因父archive无.git在编译前失败，保历史。
- r021 install-v1 controller56546/start17263423、worker56547/start17263426，真实terminal1；五dtype普通数学/input/state/tail及实际CUmodule global4bytes=0通过，最后机器映射拒绝Unmapped actual globaltimer read。原始对象明确出现CS2UR URn,SR_GLOBALTIMERLO，原mapper/provider只支持CS2R Rn；不需要放宽精确PTX/debugline/ELF范围匹配。原失败与五份raw保留，不重跑应用来修consumer。
- 本轮代码候选补精确opcode/寄存器bank配对，unit provider保持只授sm120单位、边界/precision/epoch未证；增加原失败status下从实际留存PTX/CUBIN/SASS重算map、派生新map且不覆盖首次状态，负例覆盖错误bank/高位/未知opcode/错binary/缺原件。正在GCU已有Docker缓存precommit格式，随后NV匹配新native对象独立打包安装及normal/-O测试。
- NV新preflight确认GPU0为PRO6000、15MiB/0%，旧install worker missing/controllerZ；格式controller384229已启动，root/workers/terminal按r022原件收据核，不重复启动。所有新任务留在已有Docker。

- r022 format-v1（13文件）、v2（15文件）已在GCU已有缓存full precommit固定点通过，Python AST同一；之后仅补显式boundary2兼容测试，format-v3单文件固定点通过。产品C++与实际r021完整native输入逐byte一致；复用匹配native，不重复大构建。
- r022 install-v1实际独立组wheel/安装成功（601成员byte核），最初CPU测试唯一错误是缺json.stdout负例期望OSError，而公共bundle reader正确抛ValueError；仅修测试期望、不改产品放行。保首次terminal1。consumer-v1用同wheel新测试，46normal/46-O全部通过；随后原5dtype捕获在新进程public/normal/-O重导得到40个隔离observer counter-ns trace，原件和首次失败状态不变，actual TP逐条raw引用/ns/importer检查全部通过。未重跑原用户数学；未进行本轮UI验收，不授precision/boundary/epoch/async/P01。
- 核发现instrumentation-mode文字仍写boundary2（实现指纹本已区分新native，不是已证缓存串用），修成3并与文档/plan/native一致。install-v2对应最终独立wheel SHA e4519e14c5acf96c8c50bd26ff78501c115a8f96745109425bf72b2749977fc3；601已安装成员逐byte核，46normal/46-O通过。最终native core 922550904B/SHA467a29d0da809d1c9cf536d640d25b753c6e6068b2655295040453a81241dd56；源输入桥核C++、当前Python与实际安装字节一致。
- final-v1在最终v2安装运行编译绑定普通/-O（14个预期错误版本/type/marker拒绝，legacy interval无新增anchor），owner/finalize/public 31normal/31-O通过，合计77normal/77-O。普通runtime-K递推K3/7同binary、两次正确State、input/tail、GEMM高精度CPU参考均通过，3次明确请求采得真实raw及CS2R/CS2UR映射；未把开发算子当独立资格。另compat-v1用追加的独立测试源码实际核native3显式v2 plan/lowering兼容、普通/-O均通过；产品/native未改。
- 关键未解决项有直接对象证据：同GEMM ordinary编译有12条HMMA和BAR9/DEPBAR4/LDGDEPBAR10，观测对象有4条HMMA和BAR5/DEPBAR2/LDGDEPBAR6；不能仅由静态计数证明/否定动态流水，但尚未取得ordinary关键阶段保持资格。loop-opt-v1为0次用户数学launch、canary未变的compile-only诊断，实际LLVM优化dump46,116,710B；ordinary的LoopFullUnrollPass使原loop invalidated，observed保loop。已将差异定位到LLVM优化阶段，尚未确定负责的合法性/成本规则，不盲目跳常量或强制unroll。
- NV原件artifacts/timeline/run-022/preflight/native-public-evidence-v1.tgz：9,198,175B/1122files/SHA ff1fe79dbb9bec58313a66b6106ad7a64aaac317bf5787893ede56d4539d8d63，包含r021首失败/实际完整native构建/typed原件和r022独立安装、首测试错误、修复离线、最终真实loop/GEMM、显式旧IR兼容、完整LLVMdump。41个自有controller/worker/原生build步骤身份均missing/Z/不同startticks；NV收尾15MiB/0%。GCU格式终态另有身份audit；无新browser或其它后端设备任务。
- stdlib-only留存audit逐byte核1122文件、当前源/installed/native输入桥；8次捕获1696个端点与raw16B记录offset/low/high/sequence逐字段一致，848区间中847正时长、1个真实零值保持不夹断。审计不import产品、不执行数学，也不授时钟/源边界资格。小报告与原件索引保integration/evidence/timeline-boundary-v3-r022/。
- 当前推进的是NVIDIA自动边界机制与可恢复消费链，不是完整时间线交付。仍须修/核通用最终对象边界、ordinary关键流水保持、真实allocation guard范围、precision/跨observer epoch、每后端异步两代物理复用、GCU/Ascend时间资格、独立数学/完整SQL/UI与额外三名最终代码review。没有缩scope或开始最终review；下一实际动作为从已保LLVM pass前后对象定位unroll/布局变化，再修通用compiler路径，不能拿更多raw样本代替。

- format-v4只格式化新增stdlib审计脚本，固定点/AST同一通过；NV没有新增设备任务。GCU最终重新核r021两轮+r022四轮格式任务共12个身份全部missing/Z/不同startticks。小证据保完整初次失败及其范围，未将旧UI当成本轮UI，也不以静态HMMA/屏障计数替代动态阶段证明。
