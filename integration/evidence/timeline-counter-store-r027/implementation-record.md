## T041 NVIDIA counter 到日志字段的通用值流核验

- 上轮T040为progress：wait控制路径及实际安装/TP/UI已推送c8656f6。本轮以clean canonical开始，未有在途设备任务；继续原目标，不修改论文/Study、不提前启动最后三reviewers。
- 增强backend control模型至nvidia.cp_async.wait_control.v2：逐word跟踪实际getter→helper/caller MOV/MOV.64→STS.128的tag/tick low/high，按实际predicate generation检查条件写，未知指令/覆盖/错序/错误tag不给事实。MOV.64先快照两输入word，避免重叠拷贝变成顺序模拟；bare opcode family匹配不把MOVM误作MOV。原control检查对未知数据指令清除entry guard事实，写指令与已知sync不伪造寄存器写。
- 新事实明确conditional_on_this_call_and_store_execution，call dominance、raw storage地址/guard/发布链和完整record provenance仍false；不把正确的值进入某条store当成已经绑定到某个raw cell。公共raw/canonical和旧v1报告保留，现有默认postprocess/offline随规则hash生成新derived报告，无新device指令/ABI/同步。
- source-v1既有NV Docker实际normal/-O各25单元测试和保存三capture的fresh对象重验终态0，GEMM两个wait的四个端点都找到正确store值流，recurrence不编造wait。随后补unknown move-family反例，最终安装将跑26项。源码阶段按明确module overlay测试，不冒称最终installed通过；真实原始raw和用户数学未重放。

- 最终installed-v1已实际独立组装/安装并terminal0；wheelSHA95e0eab2fc3d023294156820c26f3f0267c416ad101400e340447b541f511504、602成员byte核。normal/-O各26新旧counter/control/RPC单元方法通过，fresh生产postprocess在实际GEMM上查出两wait四端点全部tag/low/high store值流，global来源/clock/source/participation/call-dominance/raw-storage资格仍false。代码/测试/工具文档提交5317093。
- 原C++/LLVM/logger未改，actual core922771608B/SHA4774dee32ad6a7349a5e7674660dc2ffea3ccc372a15f9b016b3512c59fd39b3与r024相同；271 native源、78 installed profiler Python及1987当前source全部桥接匹配。未声称新native build；未运行不受影响的全量旧矩阵。两真实格式各3fresh public/isolated-normal/isolated-O重导、各3capture/24trace，48 actual TP核ns/raw引用/无importer错误/flow通过，原件与用户数学不重放。
- 本轮48个trace及view文件分别与r026最终UI输入逐byte相同；复用r026六次实际标准Perfetto UI，不冒称新跑browser。只更改独立机器分析报告，图/单位/clock资格未变，具体比对及旧UI输入SHA保collection/reused-ui.json。
- 原件artifacts/timeline/run-027/preflight/store-value-flow-evidence-v1.tgz：6249588B/621成员/SHA541530117e82ef9b67c4a7fa08432f977688b9f28f50ec116a49f39357879159。stdlib逐成员/current-source/installed/native/actual四witness/TP/trace/旧UI输入审计完成，37个已录NV身份inactive，script/deadline-owner扫描无活动自有子树；GCU一轮formatter两身份实际inactive，full precommit固定点和AST同一通过，仅格式无GCU设备数学。见integration/evidence/timeline-counter-store-r027/verification.json。
- 本轮partial checkpoint冻结后，下一步优先补GCU/Ascend最小时间尺度及公共导出；NV call/store条件、raw-cell/主体关联及完整source边界保留为待闭合工作，不继续仅扩展同类静态witness替代三后端纵向交付。三后端P01、真实异步两代复用、独立六数学、受控案例及最后额外三指定模型代码review仍全部必达。没有论文/Study改动、独占性能测试或用户数学重放；完整goal继续active，未complete/blocked。
