# R099 Ascend actor只读索引器有限审阅

结论：typed索引方式可作为后续规则的数据源；未发现本冻结中具体SSA身份误绑或显式CFG漏边。发现 **1个confirmed minor**：target_triple绕过声明的统一text预算。随后候选已作最小源码修复，matching新native执行尚待核。此报告不审tuple/loop资格算法，不授自动接线、source/native或whole资格。

## 身份与实际范围

冻结 **7a55d9d5b9db40a58789e322710322f4b6e80e27**；C++ SHA **99907c53281dac61a074155d200d42eebe30629d5be178cf49cca47f57a30aec**，native CLI tests **94f61395ce7b79e0925f0ed373fba2f2763cf4b7debf9fffd839b7eb0841a730**。沿原请求GPT-6.1-Sol/xhigh，resolved型号/effort未暴露，记unknown。

实际读 `AscendExecutionStructure.cpp`、CMake独立target、README及四项CLI checks；读取 `run099/preflight/structure-receipts-v2`，67项index的size/SHA逐项核同。未读peer，未执行产品、import、测试、SDK、设备、数学、模型或TP/UI；仅写本报告。后续未提交的一行预算修补单列，不混入此freeze的执行证据。

## 数据层判断

- 真正IRReader后先verifyModule，再建DominatorTree/LoopInfo；invalid PHI/predecessor在分析前拒绝。global Value*→ID表使指令、operand、PHI incoming block/value和block successor引用一致，不依赖打印SSA名字。
- 所有显式terminator successors按LLVM接口保留，PHI另保每条incoming edge；没有用callee或debug行猜CFG。LoopInfo输出仅为natural-loop membership，不表示不可约cycle不存在或循环次数已证。
- integer以位宽+hex保无符号位模式，宽于64、undef/poison和其它constant明确不解释；aggregate不递归打印，只提供已编码scalar/pointer事实，避免类型DAG展开。直接call、InlineAsm和indirect分开，nsw/nuw及volatile/atomic flags保留。
- CMake建独立LLVM15 executable，不把新程序加载进vendor SDK；没有修改原producer。native_schedule_qualified始终false，工具只写完整成功JSON，没有把四actor索引结果直接变成边界证书。

## Confirmed minor C1：target_triple绕过text预算

**位置：** 冻结C++第229行；`Index::text`第35–40行。

**触发：** 合法IR的target triple设为4097个普通字符，函数仅void return。其余text很短；冻结实现直接以 `module->getTargetTriple()` 写JSON，不调用text，故可成功输出超过README声明的单字段4096B限制，也未计入累计8MiB text。LLVM verifier不负责本工具的文本预算。此问题不涉及实际四actor错误，也不是source资格失败。

**最小修正/验证：** 改为 `index.text(module->getTargetTriple())`；真实CLI以4097字符triple要求非0且命中text budget reason，原短triple继续正常。不需要大输入或新矩阵。

已只读核后续候选确实只有此一行修补，C++ SHA **94a91a1a23f61bdcce95606c825ab4e87231f21a95bd46d3d5d1139fa1fc5db3**；tests **77931de94e8895600a43d2555f4631f4e5569ab49cb32e5da5f59b486eaede8d** 新增准确oversized-triple check并报checks=5。**C1源码路径已修，实际matching新tool与该negative执行仍待补**，旧v2四项通过不冒称该新case已跑。

## Confirmed blocker / major

本限定数据层未发现confirmed blocker或major。没有把尚未实现的tuple/loop规则、packaging或automatic入口当本target代码缺陷。

## 已读matching证据与必要gap

structure-v2实际 **terminal0 / 8.927341815s**，tool SHA **1a0d3ce219976778097a522cb229ff8eb9699bcdc4a95b408109371acbbfe29e**，source SHA精确99907c…；actual retained source与freeze相同。完整normal/-O日志均报 **checks=4 / passed**：real loop/clock/store SSA及overflow/volatile、invalid PHI、poison、indirect call。

四actual输入SHA与原handoff一致：q01 AIV / q03 AIV / q05 AIC / q05 AIV分别索引 **164/163/166/262 blocks**，natural loops **1/0/1/1**。SDK_recompiled/device_executed/source_loop_qualified皆false。这关闭LLVM15兼容性与该四输入的数据通路，不是tuple/loop或最终native正确性。

当前必要gap仅C1修补后的matching native case/源码身份；本工具尚未packaged或接自动入口，报告仅注明范围，不为这份内部数据层另加正常wheel或设备门。

## Optional / 明确限制

- `lshr/ashr/udiv/sdiv` 的 **exact** flag尚未输出。当前四actual输入未见该flag，本索引也未解释整数cone，因此不算当前资格false-pass。后续若支持这些opcode的必要值求解，应输出exact或将该语义保unknown，不能把缺字段当exact=false；无需全LLVM属性框架。
- 32MiB序列化输出上限在JSON构造后检查；work/SSA/text上限仍限制规模，但不能据此宣称峰值内存也只有32MiB。此处仅记录资源界线，不追加内存证明或新矩阵要求。

支持完成C1小修后继续接下游有限规则；本报告不授source interval、record tuple、loop iteration、native issue prefix、source-exclusive cost或whole资格。

## 追加：C1 matching native执行闭合

已只读核修复提交 **add626d5351b63cdf4abc1b4b10f88b0903456df** 及 `run100/preflight/phase-receipts-v1`，92项index的size/SHA逐项一致。实际built C++与candidate均为 **94a91a1a23f61bdcce95606c825ab4e87231f21a95bd46d3d5d1139fa1fc5db3**，即上文已静态核的一行统一text预算修补；未读取同目录其它新tuple helper，也未运行代码。

structure-v1实际 **terminal0 / 8.977988812s**，新tool SHA **d0e82b1fdc5fc322c322bc80c44a9e5e552afc5918174e2ba0f9504cc7a99d61**。完整normal/-O日志均报 **checks=5 / passed**；两份真实oversized-triple fixture确含4097B triple、stdout为空，stderr均明确 **Actor structural text budget exceeded**，没有以其它解析错误替代预算guard。

四原actual输入的SHA及完整index SHA与R099 v2逐项相同，block/loop数保持164/163/166/262及1/0/1/1；无SDK重编、设备执行或source_loop资格提升。**C1源码与matching native运行gap关闭，本有限数据层无剩余confirmed缺陷或必要验证缺口。** 该独立target尚未接公开wheel，不为此次闭合另造安装前置门；tuple/loop算法、自动入口与whole资格仍不由本报告授予。
