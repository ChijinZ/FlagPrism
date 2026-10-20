# Ascend关键compute漏采：下一最小干预

**优先为Asc timeline区分选区意图，保留重复body的aggregate代表；先不增加SDK-call operation class。** 然后用新的公开q05验证dot carrier实际如何lower。只有选中dot后仍未包住MMA，才需要回到独立SDK-call bracket方案。

本席只读原件和当前planner/producer，未读peer，未执行产品、测试、SDK、设备或数学。请求GPT-6.1-Sol/xhigh，resolved未知；未复制private LLVM源码。

## 两个根因要分开

- **选择缺口：** `Debugger/python/flagtree_debugger/compiler.py:328` 对Asc census与timeline都传 `census=True`。`automatic_plan.py:120–141` 先按memory优先选重复body两处，再分配scalar/region/class余量。实际旧q05 carrier列表为1/2/6/33/42/50/73/78，不含43；root补充的tracked table将43识别为dot。因而不能先假定dot已经选中、只是LLVM边界尚未证明。
- **片段范围缺口：** 已核 `original-receipts-v1` 18项index全SHA，original-graphs-v1 terminal0 / **0.466411441s**，tool为d0e82b…。q05 AIC block87中MMA call id200在carrier50 id204之前，后者只覆盖iv increment；其它block的carrier33 fragment止于terminator。当前“carrier后同block直到下一marker/terminator”的规则确实没有覆盖这次MMA。选区修补能否消除此第二缺口，要看新actual lowering，不能预判。

## 第一阶段最小改法与身份

1. planner增加明确timeline意图，仅在该模式优先预留实际repeated region中的data aggregate（dot/reduce/scan等IR类别，direct成员优先），随后复用原memory/scalar/region/fair分配。仍遵守max_sites和预算；不用kernel名、op43、shape或位置特判。counter/census策略及其版本不变，已有旧raw不重写。
2. 新timeline选择policy有独立版本/selection_reason，确认它进入实际JIT **pre-lookup** cache身份，而非只写manifest；旧timeline缓存不能继续复用未选dot的binary。source site仍由真实frontend op/carrier标识，不需新provider或semantic code。
3. 预算内未选、被lowering跳过或fragment空的项继续明确报告。不能因为plan多了dot，就把某个相邻index fragment的时间改称MMA时间。

## 定向q05验收范围

- CPU planner回归：相同原tracked table下timeline确有重复body aggregate代表、max_sites不超限；census输出保持原策略；不按特定ID挑选，换序/多个aggregate仍按实际control metadata选择。
- 新正常安装后经**公开入口**取得受影响q05：保实际plan→TTIR carrier→SDK原actor/manifest→adapted tuple→新raw链，核MMA call是否真在所声明fragment/两reader关系中，并核数学/State/input/tail/host-once与重复occurrence。旧raw不能证明新producer，旧current96未选dot的项目不能重新标成新通过。
- 只复核这次改变的默认/sparse选择、cache及受影响关键pipeline关系，复用未变ordinary/helper/clock原件；不重开旧独立数学矩阵。仍保source-exclusive/native busy false，不要求完整ISA或每fragment新模型。

## 第二阶段仅在仍漏采时采用

若dot已选、但actual SDK lowering仍将MMA放到该carrier fragment外，再按**原actor中未覆盖的真实SDK调用**建立独立site。身份应绑定实际call、签名及SDK资源/定义；已有fragment覆盖的call不重复观测，不进入SDK helper定义递归插桩。source用call真实DI，dominating carrier只提供坐标/部分导航，不能冒认source op归属；没有真实source ID仍保unknown。

复用现8×i64协议、不加wait/barrier。默认语义应为 **SDK调用observer elapsed**：MMA helper可能含原有wait，整段不必是纯issue开销，更不是engine busy。届时才为新site加明确operation class/feature版本和相应实际capture验证；当前没有理由先绕过source选择意图扩大观察范围。

这是实现顺序建议，不是新功能或whole通过票。最短下一步是timeline意图区分与targeted新q05；根据真实lowering结果再决定是否需要第二阶段。
