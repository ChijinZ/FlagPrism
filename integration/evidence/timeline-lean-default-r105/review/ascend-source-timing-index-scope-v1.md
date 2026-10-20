# R105 Ascend 原96 source/timing事实、旧24 MMA缺观察与当前泛化

**结论：不能仅因旧 q05/q07 各12份没有独立 selected MMA 区间，要求这24份全部重采。原冻结没有“每份 matrix trace 必须单独计时 tt.dot/MMA 或固定 epilogue 行”的条款。** 旧数据的 MMA 覆盖限制必须保留；当前通用选区修复及新数学回归另列，不能移填旧raw。本次facts补齐了此前map A所需的原source/timing事实归并；不把可选static unknown变成runtimeerror或新验收门。新 q11/q12 全部结果仍须按实际终态收齐，不预判 whole 完成。

配置请求沿用独立 R3 GPT-6.1-Sol/xhigh；actual resolved未暴露，unknown。实际candidate为clean `6e78f136214da74254211fa19b90a3f7b7353fa2`。只读原合同/registry/事实/源码diff与已有收据，用stdlib比较JSON/hash；未读peer，未执行产品/import/tests/SDK/SSH/device/TP/UI，只写本报告。

## 1. 原条款究竟冻结了什么

直接读取原 `.timeline-qualification-r052-private/registry.json`，SHA `62d7e63d0c7a66de21fdd7862a9c852959ca1a87a8991c9489877b8d6fa87ee3`：

* **:20 `structure.all`**：`At least two distinct automatically mapped internal source regions with complete intervals, multiple positive durations`，并要求default-selected主体有records、loss为零、raw/object/source/invocation/clock可追溯。
* **:21 `structure.elementwise`**：device-loaded runtime trip、body occurrences≥3、K3/K7同binary。
* **:22 `structure.reduction`**：per-row reduction与dependent post-reduction arithmetic；没有要求两者各自一个独立timer。
* **:23 `structure.matrix`**：`2D program grid; >=3 K tiles; contraction followed by store`，另有tail及不能凭stages猜async。这是实际数学/执行结构约束，不是“contraction和store必须分别被计时”的声明。

补二原registry SHA `1e6a4da3b7b3e4900abb29e03a34bec5c17b12ba5f4e01341ae968038de33f3a`，`:12`规定q07 contraction、row/column summaries、dependent normalized epilogue，q08 broadcast/permutation/reduction和至少三logical Ktile；同样没有逐阶段timer清单。

`Profiler/docs/timeline_testing.md:100–110`对每个eligible组合规定两真实源码区域、多正duration、循环至少三个实际body occurrence及实际端点/身份/单位/完整性；`:112`不强求每条极短操作可分辨。`:94`和root `timeline_goal_prompt.md:109`要求保留原失败分母；它们不能用来把后来提出的逐MMA计时偏好追认为原失败。root goal `:110`、testing `:96`则要求修复样本改称回归，并补独立新数学。**这些要求均保留，不增不减。**

因此，本席先前map中“主数学/必需阶段”应按上述原实际结构和所声明source子区域解释，不能借用R098针对GCU选择的固定math+epilogue行数组，为另一后端事后增加每份tt.dot独立timer门。实际 contraction和store仍须在原执行中存在且数学/副作用正确；观察到的循环body须是真实原body操作，不能用logger或无关忙等代替；未测到MMA就不能报告MMA elapsed。没有放宽这些约束。

## 2. 本次原件核对

读取 `run-105/preflight/phase-receipts-v1-recovered/runs/ascend-source-v1/output/`：

* `facts.json` 791,186B，SHA `eafd9cb1fea68b38bb246bc12e373033ed429532a6773263006ecb0872be6459`。
* `result.json` SHA `2ab94f2fc54730cae7083936ab1792e0a3dbe22482698ea7bd3aa5755470c729`。
* 原R104 `calls.json` SHA `9bd9b3ab666e10dfc86cca6538d8fbca04ef96a18c8ab850429abc46411140eb`。逐96个case核capture/raw/binary身份、positive source ID集合及120条stage candidate的完整observation，差异0；没有新capture、SDK或应用重放。

96个case唯一，q01–q08各12；96/96记录至少两个不同positive source origins，实际最少为4。源路径SHA与原base/supplement冻结匹配。q01/q02各12有真实arith body source及重复；q03/q04各12有实际tt.reduce source。原数学/编译链中dependent post和store的结构/数值证据仍复用，不能因为某个AST行没有独立timing就宣布它们没有执行。

q06各12有actual tt.dot观察，q08各12有actual reduction/Ktile观察。q05/q07各12在本索引的actual contraction候选没有MMA timing witness；该限制不改写。另读原R104完整observer摘要，这24份都存在真实loop内source的重复record：第一shape每observer3次，tail shape4次，并有positive区间；这些是相应source子区域的事实，不把它们改名为MMA耗时。

`original_stage_timing_complete=12`及84条`original_stage_gaps`是这份脚本针对具体AST行/阶段的诊断结果，**不是原硬门只有12/96通过**。尤其固定 `dependent_epilogue_or_output_issue` 行的缺席不能作为原新增失败分母。可保留诊断以便用户知道没观察哪些细阶段，但最终资格表必须另列原两source/完整性/循环等实际要求。

这里接受的是source/timing事实归并及作用域口径，不将raw正数或compiler source坐标单独升成任意native/SSA证明。原实际getter/边界/对象/SDK规则继续按本席已审有限范围复用；没有证据的更强区域成本仍未知。q01 opaque type、q03 duplicate-match等optional static状态不因本次facts变绿，也不构成新增默认采集或Perfetto错误。

## 3. 最终表应分开列这三批

| 数据/产品范围 | 如实可写 | 不可写 |
|---|---|---|
| 原Asc96，含旧q05/q07的24份 | 原默认source/timing最小事实96/96；原数学、调用、raw、预算、State等沿已闭证据。旧24保留“MMA未选/未观察，MMA timing coverage partial” | “旧96都有MMA计时”或用新trace补旧event；也不能把84个固定行诊断称84次原硬门失败 |
| R101通用选区修复及新q05-s0-c0回归 | 原案例暴露后通用修复的受影响实际回归；定位实际MMA及选择/编译对象链 | 未见新数学，或据一个q05新capture声称旧24已重新取得MMA区间 |
| q11/q12真正独立新数学 | 单列8 ordinary与计划24 cold/warm profile、各自source/config/install/binary/raw及原验收结果；说明验证当前generic planner的泛化 | 改名替换原q05/q07、缩旧分母、预判仍运行的capture成功 |

本次归档里可直接核 q11-s0-c0 的cold/warm1/warm2 terminal0及完整result：同 `6e78f136…`、同binary，各7个positive source origins，两个observer各4次positive MMA interval，实际retained MMA call、math/input/guard/host-once与预算通过。8 ordinary终态0，285.457861736s。root另报随后配置已经通过的实时进展不冒充本次归档全部24已齐。剩余只收齐已授权新泛化的真实终态及相应原门，不增加新的旧96矩阵。

## 4. 是否重采旧24及实际用户价值

**本次不要求旧24重采。** 原条款要求的是实际数学/结构和所声明的内部source/loop区间，未强制MMA、store或epilogue逐项独立timing；这些旧capture并非只有整核bar/instant/全零，而已有完整的多源、多positive和实际body重复。当前新增对MMA更有用的默认选区能力，应通过R101实际修复回归与q11/q12独立泛化证明，保留版本差异即可。

如果未来要对这旧24逐份给出“该invocation的MMA elapsed”，那必须取得该invocation真正记录的MMA端点；旧raw没有就不能离线制造。这是该更具体结论的前提，不是本合同新加的24次mandatory采集。

对用户，实际改进是当前默认trace能直接看到真实contraction区间；旧trace仍能解释其已采source子区域与循环重复。这样既不隐瞒历史覆盖不足，也不为一个没有冻结的逐MMA承诺重复整批数学。当前6e78移除的是默认自动生成auxiliary static graphs的三行调用；源码diff没有改timer/producer/ABI。本报告不把可选分析的所有unknown变成发布前阻断，也不借此授予busy/completion/exclusive或一般SSA/ISA资格。

Confirmed blocker/major/minor：此有限复核无新增。必要余项为已授权q11/q12剩余实际结果与最终记录/三席处置/Git终态；不是原24强制重采或所有static绿。此前map A的“原source/timing事实尚无全分母映射”已由本次facts补足；后续应引用本报告更新其状态，同时保留旧24的MMA coverage partial。whole最终结论仍按全部原门收齐后裁定。
