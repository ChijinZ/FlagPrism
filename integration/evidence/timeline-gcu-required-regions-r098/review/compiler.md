# R098 compiler：constant trip / record pointer cast有限审阅

结论：constant与runtime-input分开报告、record块仅增加typed addrspacecast的方向合理；发现 **1个confirmed major**：constant分支接收一般模运算折叠结果，可能把合法typed、实际为poison的带溢出标志表达式当成已证正literal。建议只收真实constant定义即可覆盖本轮实际literal3，不需要完整LLVM UB/SSA解释器。

## 身份与范围

本次读到candidate base HEAD **be3aec778114d866dba0db23bafeba281ee88419**，两份未提交源码：helper SHA **d4030682354fdff7c0010d5fffd7b6cf33418621d359fd9e26aa34322a5001d7**，tests SHA **7dc4c642a2349bc210170ea5032e02fbd4b69a060e5be68f55f29653ed9094b9**。

沿原请求GPT-6.1-Sol / xhigh；resolved型号/effort未暴露，记unknown。只读本轮 `_trip_fields` / direct与structured接入、record whitelist及新增tests；复核原 `value()` 常量折叠和typed index输出字段。未读peer报告，未运行任何产品、import、测试、SDK、设备、数学、TP/UI或SSH。只写本报告，不改变实现。

## 有限实现判断

- `_trip_fields`输出 `llvm_constant_iteration_checked`，同时 `runtime_input_qualified=False`、不带runtime_trip_value；没有把固定3轮升级成runtime参数证据。允许区间严格在0与signed最高位之间，配原0初值/+1，可保守避免该有限family内induction环绕；unsigned更大但合法的trip被拒是支持范围限制，并非false-pass。
- direct/structured仅由该helper提供分类字段；原selected-path、完整record、latch步长、SCC、reset与额外入口条件没有删除。独立bracket仍可checked而loop unverified，界线保留。
- `_record`新增 `llvm.addrspacecast` 后仍要求一operand/一result，双方类型都为LLVM pointer；它不产生额外load/store/call。32stores、magic/seal、guarded slot、必需tuple与共同alias基准未放宽，cast payload不被当成可凭空证明site/clock常量。cast进入record地址或必需字段时仍必须过原pointer/value检查。本处未发现新增具体false-pass。
- cast的真实CLI fixture把转换后的pointer bits只写非必需payload word12，再分别核错误类型、call/fadd替代及必需site字段改变的拒绝，覆盖方向与本增量一致。

## Confirmed major M1：常量折叠可能把known-poison trip认成literal3

**位置：** `gcu_llvm_regions.py:757–766`，direct接入约823行、structured接入约1006行；关联 `value()` 的llvm.add/sub/mul模运算折叠，以及 `GcuExecutionStructure.cpp` 未输出这些操作的overflow flags。

**触发：** 在原合法runtime fixture中，以两个i32常量 **-2147483648** 与 **-2147483645** 的 `nsw add` 作为header trip（其它begin/end/record/0/+1全不改）。数学和为-4294967293，超出signed i32，故这条合法typed LLVM操作结果为poison；模2^32的位模式却是3。SDK verifier接受合法typed的poison-producing表达式，并不证明它是可用trip。

**实际代码推理：** typed index只记录add操作、operands/results/types，丢失nsw/nuw语义；`value()`按模算术把该表达式折成 `literal(32,3)`。新 `_trip_fields`见无symbolic项且3位于正范围即肯定 `constant_trip_count=3`；constant分支又跳过runtime输入的entry-invariant要求。旧规则会因compile-time constant拒绝此路径，现在可返回constant iteration checked。实际header条件依赖poison，不能据此认3轮有限结构证据。这里不声称本轮真实q05/q07已含此故障。

**最小修正：** constant分支仅接受trip实际definition为 **`llvm.mlir.constant`**（必要时显式支持少量无poison的literal forwarding），其它折叠到常量的表达式保unverified。若一定要支持带flags折叠，可在本必要锥保相关flags并拒已知溢出；本轮没有必要扩到一般LLVM definedness。

**最少negative：** 用真实native CLI解析上述flagged-overflow bound fixture，要求bracket仍可独立checked、loop因不支持的constant-bound表达式而unverified；真实直接literal3继续checked，runtime fixture分类不变。应断言bound原因，不能由其它record/CFG破坏代替此guard。无需SDK/device或新数学矩阵。本席只做静态审计，未执行该反例；已向root提供准确数值与最小修法。

## Confirmed blocker / minor

本有限增量没有另外confirmed blocker或minor；上项是新constant肯定分支的具体false-pass，不重新打开已闭State writer、pipeline或原计时资格。

## Verification gaps与已读证据

- 已读取 `run098/preflight/constant-status-v2.txt` 的实际终态摘录：constant-v2 terminal0 / **7.078731021s**，normal日志34 tests OK（0.242s）；对象16/24中site25均有constant-loop肯定，其余失败site仍保unverified。该摘录没有完整final input/source与normal/-O全部原日志，故不据它声称最终formatted或M1修复版matching通过。
- parent报告constant-v1已实际通过，v2补cast正反例；本报告未把未取得的完整原收据写成已独立读取，也未将旧正例结果用于关闭上述新negative。
- 当前源码尚未冻结，正常安装也待后补。必要下一步仅M1最小修补、该条准确native negative及既定定向套件的matching源码/正常安装身份，不要求重跑旧矩阵或产品数学。

## Optional与有限结论

无新增optional重构建议。支持以独立constant状态补实际固定次数循环、以纯typed pointer conversion容纳原record payload；在M1及同版验证闭合前，不建议关闭该delta。仍不授native/source-exclusive/source_iteration_id或whole资格。

## 追加：M1最小源码修复进度（尚待matching执行）

已只读核后续未冻结修补：helper SHA **35870e410bbc89a93d9cb4f5ca3a8aba7b511419a30c6a5ec27775b0deb659a0**，tests SHA **d6f0f7853e1d133c73ad1b249fe602edb4d371c42bfea31803f99af2dd6a0f0e**。constant分支在肯定结果前新增actual definition必须为 `llvm.mlir.constant`，错误原因明确 **actual literal definition**；原positive/non-wrapping范围及runtime支路保留，rule_version升级v3。新增真实CLI fixture正使用上述两负i32的 `overflow<nsw>` add，并要求loop unverified且命中该具体原因。

该源码修法已阻断M1所述路径，未增加一般UB解释器。实际constant-v3仍在运行，本次未取得matching终态或最终freeze，故当前状态为 **M1源码修复已核、定向执行/正常安装待核**；旧v2的34项通过不用于关闭此新negative或其它尚未证epilogue。

## 追加：单遍legacy discovery有限审阅及confirmed major M2

本追加只读候选base **d91f63b17e435c35d064f16d308dccf82010ec33** 上两份未提交搜索增量：helper SHA **7e54c1d60ed1821fee89d6402e71cea47a950f6334fc6e82100d80b864a165fc**，tests SHA **f04ef05f9b142cd303731fc0a1b3370dd18c3c7d34b1c95e9d4b05498d1a07d4**；未运行其CPU/产品/SDK/设备。原d91 matching正常安装收据当时尚在回收，不将消息中的通过数冒称本席已读。

单遍路线可接受：`_record(..., sites=...)`等完整32fields、magic、相对slot、guard及count校验后才以literal field1反查manifest，并继续逐项核field3 kind及所有必需tuple。`_region`对每selected路径用实际发现site核body，任一坏tuple分支直接失败；所有成功路径必须同site。只有完整通过后才按site聚合，manifest顺序不作身份依据。新增ID/kind/opaque ID、同site双begin、同begin异site及坏tuple分支的测试方向与这些条件一致；显式marker路径保持原检查。

**M2位置：** helper约1220–1240行，`discovery_budget`后聚合。

**触发及推理：** 首个begin A完整成功指向site7；扫描中途在另候选上耗尽共享1m work并break，后面实际还有另一个完整begin B也指向site7，尚未扫描。当前代码只在 `not matches` 时把discovery_budget作为错误原因；site7已有 `len(matches)==1` 便返回checked。于是“不完整扫描只看到一次”被当成“所有候选中唯一”，实际双begin歧义被漏掉。无需改变任何已检查tuple，也不依赖未知ISA；原要求的唯一聚合自身尚未完成。这不是说本轮实际对象已触发该歧义。

**最小修正与negative：** discovery因预算提前终止时，所有依赖此次全候选唯一性判定的legacy site保unverified；保持预算与显式marker路径，不重置work或提高门限。用现有双begin同site fixture，在首个成功后、第二个候选未完成前精确强制budget exhaustion，要求已匹配site也不checked。可定向模拟预算截断以检查聚合不变量，不需要大CFG或新矩阵。未知/失败候选诊断仍可保留，但不能据未扫描部分证明唯一。已向root给出该具体遗漏。

本次单遍算法源码范围没有另外confirmed问题；M2及其matching定向验证关闭前不建议关闭新搜索delta。M1修复、constant/cast安装与此新算法的执行/安装分别记录，不以旧d91通过替代新搜索验证；whole/native/source-exclusive资格仍未授。

已继续只读核M2最小修补：helper **9ce33a1e5c392fd42dd818f2fd2e0bf421ac79da403f4c614d4582d6424745f0**、tests **d3365dd9254140fc4d814dd0f0a921f5a747b31d91be4c0474f564014031eeb8**。legacy聚合在使用任何matches前明确要求 `discovery_budget is None`，故扫描中途失败时先前单匹配也不再升checked；显式marker路径及1m共享预算不变。新增fixture确为双begin指向site7，包装第二次 `_region` 调用前将work置1000001并抛预算错误，要求所有site unverified且reason含budget；finally恢复原函数。该反例直接覆盖扫描完整性，不需大CFG。**M2源码修复已核，dispatch-v3实际matching终态/最终冻结与正常安装仍待补。**

## 追加：0baa23e冻结与M1/M2 matching定向验证

已只读核最终冻结 **0baa23e947f10680c0cad8d3d598e3e35fdb164c**、`run098/preflight/dispatch-receipts-v2` 和原constant/cast版 `installed-receipts-v1`。两个index分别20/142项size/SHA逐项核同，未执行任何实现、测试、SDK、设备或应用。

最终helper SHA **d4e8d11009a0dcf23af281052991267ebb2a6067c714e1df11c0569d46f0d5a0**、tests SHA **29a62299b695d160474778768e404b72995954cb88fa19df99d5d034c890f44f**，与dispatch-v3保留的实际输入及candidate逐字节一致。dispatch-v3 terminal0 / **3.971112624s**，script SHA **bc88dd9e78a36ea2c08835003c05255a18ff58cbd6207a96213908d983c3d3d5**；完整 **39normal / 39-O** 均OK（0.282s/0.273s），包括真实nsw-overflow bound拒绝、typed cast、单遍ID/kind/分支/双begin及第二候选前预算耗尽的准确negative；最终ruff/yapf/check-ast均0。因此 **M1、M2源码与matching定向CPU验证均关闭**，不再按上文在途状态处理。

两实际对象本次执行全量查询，非手挑begin：对象16/site60与对象24/site49均为 `llvm_observer_boundary_checked`、`no_enclosing_runtime_loop`，未再因原sites×begins重复搜索耗尽预算。两者site25仍为明确 **constant_trip_count=3 / llvm_constant_iteration_checked / runtime_input_qualified=False**；它们的其他尚未支持loop形态仍保各自unverified原因，未因局部改进统一变成checked。该结果支持本轮搜索容量修复，不授全部source/native资格。

原constant/cast版 **d91f63b17e435c35d064f16d308dccf82010ec33** 的normal-install-v1另已取得真实 **terminal0 / 98.005470052s**，503members、16steps全0，wheel SHA **80c982a47ec290dad3a581cba9cc40bdb24bd9d4c7159b18488b3d6a35913a9b**；**39 bindings / 35 rules normal/-O** 完整日志均过（rules 0.246s/0.244s），-O仅预期pytest warning。这关闭原constant/cast版的正常安装验证，不把它套给之后改变搜索算法的0baa版。

当前本delta无剩余confirmed源码缺陷；**唯一仍待的交付gap是新0baa23e正常安装/fresh接线的matching终态**。原d91正常结果及source-loaded39项不替代该项，进行中的新normal-install-v3不提前算通过；不要求新设备、SDK或旧数学矩阵。whole、当前96整体资格及native/source最终组合仍未由本报告授予。

## 追加：0baa23e最终matching installed闭合

已只读核 `run098/preflight/installed-receipts-v2`：127项index的size/SHA逐项一致，读取normal-install-v3 terminal/result、完整定向日志、输入源码/配置与required-join摘要；未执行任何产品、测试、SDK、设备、数学或TP/UI。

normal-install-v3实际 **terminal0 / 64.663610745s**，source **0baa23e947f10680c0cad8d3d598e3e35fdb164c**，503 installed members与正常wheel核同，wheel SHA **8123a8f612ebf519eb42e598bfdca66f197578ca6ce92598f1f2a2761cadfdf2**；16steps全部0。runner SHA **c1920e3781f7b6623a8a2b414b07e379609d06b93873e9e584727a7e8be92ae7** 与terminal/保留脚本一致，实际输入helper **d4e8d110…**、tests **29a62299…** 与本最终冻结精确一致。

**39bindings / 39rules normal/-O** 完整日志均过（rules 0.273s/0.270s），-O仅预期pytest assertion warning；规则测试明确加载installed package路径，包括本报告M1 flagged-overflow bound和M2 incomplete-discovery预算截断准确negative。因此M1/M2修复已到正常安装，不再仅有source-loaded或旧d91证据。

同安装内的fresh required-join步骤为0，其结果记录region implementation SHA精确 **d4e8d11009a0dcf23af281052991267ebb2a6067c714e1df11c0569d46f0d5a0**、producer tool **374ab5f9…**、33对象与96原raw，device_executed/application_replayed/native_schedule_qualified皆false。该摘要为 **87/96 structural join covered**，不将剩余9项解释为本M1/M2代码回归，也不把该partial覆盖冒称current96或native/source组合已全闭。本追加仅确认此次规则实际从正常安装接线执行。

**本R098有限delta的最后matching安装gap关闭。** M1/M2源码、定向CPU与正常安装闭合；当前本delta没有剩余confirmed缺陷或必要交付验证缺口。完整goal、当前96覆盖及native/source最终组合继续按原范围独立评估，本报告不授whole资格。
