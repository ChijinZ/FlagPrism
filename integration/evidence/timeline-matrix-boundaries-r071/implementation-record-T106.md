## T106 NVIDIA 矩阵边界规则产品化与流水核验（run071，在研）

- 前轮progress：计数生命周期修复baea706正常安装+normal/-O21negative/4actual与公开CLI/2新TP及review闭环，push85f08a8。当前canonical clean；沿原目标继续，无重开sparse计数错误、无新device/application。
- 本轮先读R061实际ordinary/default/sparse native JSON/PTX。实际PTX两者均四MMA→原barrier→下一copy；native普通最后MMA可排在copy后，profile四MMA在copy前。JSON字段只有opcode/operands/predicate/other-attributes，不包含完整隐式scoreboard信息；保留字段/邻域原摘录SHA于run071/preflight/retained-native-order-v1.json。不能据指令数量或相同PTX单独授ordinary overlap保持，也不据native顺序变化直接宣布完成串行化。
- 发现原R062人工4MMA bracket核验还未产品化，native boundary公共报告不含matrix rule。候选新增通用finite matrix issue规则：精确支持实际SM120 FP16 m16n8k16→HMMA.16816.F32 mapping，按实际site members/PTX行/native PC/同一无谓词readers/无额外matrix/单入口无分支区域核边界；未知形状或歧义给unverified，不按算子名/SSA/hash识别。report新增matrix_issue_sites，仍不给exclusive source cost/participation/engine completion/busy资格。
- 新13项有/无效CPU规则fixture＋参数化actual4capture(raw endpoint)脚本已编码，matrix-rule-v1在NVIDIA已有Docker按owned controller启动；仅源码加载检查，尚未核终态，不冒称正常新wheel。下一步检查、修具体问题、格式/正常安装/公开control报告验证；无native改动，不重新编译C++。

- T106 c2224b3正常wheel安装终态0、639members核同，264 native inputs未变且明确复用。normal/-O新13CPU tests通过（-O仅预期pytestwarning），installed actual4capture24/56/24/56共160interval/320endpoint核同。公开CLI control报告自动含matrix_issue_sites及四actual PTX/nativePC，sourcecost/participation/matrixcompletion/busy均false。
- 8counter trace bytes与R070相同，沿用其exact bytes SQL；2dependency因规则证据identity变化而bytes改变，只对该2份新trace运行原pinned实际TP，whole0，各180endpoint404flows，无正error/data_loss，完整stats留存。无新UI、无应用/设备重放，无C++重建。原R1实际读新installed/SQL收据，有限installation gap已闭，未授wholegoal资格。
- native-loop-probe-v1仅CPU原件结构诊断、whole0：default matrix bracket位于nativeheader3056/latch7472的277指令natural loop；sparse位于header3104/latch6032的184指令loop。两端均dominate实际latch及end覆盖exit源；该probe未入产品，不授loop资格。证明可用既有实际CFG补有限结构规则，不必先建任意ISA证明器；后续需产品规则/真正绕过端点与循环多入口等语义negative。
- 另一个明确剩余缺口：当前matrix rule核原PTX/native位置与LLVM members数量，不核每个LLVM origin身份。下一步优先考虑编译阶段给原操作保留独立native debug origin标识（原源码导航先保留）、再核实际生成对象，与现有clockmarker区分；先有限实际lowering验证，不用字符串出现就放行。普通pipeline的关键依赖/overlap机会仍独立开放，不把本轮矩阵issue placement或loop诊断冒称该项完成。
