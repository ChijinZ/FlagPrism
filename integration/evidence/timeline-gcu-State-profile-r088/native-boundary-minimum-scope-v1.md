# GCU / Asc native 边界：原合同内的最小收尾范围

请求配置 GPT-6.1-Sol / xhigh；resolved serving 配置未暴露，unknown。基于当前 `11d9b1f23ee2b623d951937bfba9efa54f45f828`，只读合同、所述源码、原件及小结果；没有运行 Python/产品/checker/测试，没有 SSH、设备或新数学/TP/UI，没有阅读其它席报告。根 record 只用于版本与工作范围，未把其中其它审阅结论作为依据。本次不重新做 whole review，也不裁定独立的 State-writer 缺口。

**可以停止扩建通用 native 证明器。原合同要求的是声明区域/循环及实际异步关键关系有证据，不要求完整 GCU/Asc ISA、一般 def-use、全库 CFG、任意别名分析或 source-exclusive cost。对既有冻结实际对象，手工核实 compiled source/loop 边界并接上已自动绑定的时间/raw链，可以构成本轮有限最终产物的充分补证；无需先把该手工审计全部编成通用 native verifier。** 但“已自动绑定”必须包含本段实际 reader/site/路径，不能用只有 DI 行号或仅相对 end 字段的结果代替。

## 合同如何限定范围

- 根 prompt §2.2 要真实内部区间、source/binary/invocation/observer/raw关联、循环 occurrence和实际异步代际；没有要求完美硬件 busy 图。设计 §0.2 明确 clock、boundary、epoch、机制是独立事实。
- 设计 §0.6 的有限核验内容是：实际端点与区域数据/控制/访存关系；声明 runtime-loop 的头/回边/出口及配对路径；原 wait 的覆盖集合；实际 observer/predicate。文本明确“不要求任意机器码证明器”。
- 测试 P03及§8.7 C2要求 ordinary/default/sparse 的关键阶段与合法预取机会保持，明确“不强求编译调度逐字节相同”。不新增 same issue-order、hidden scoreboard、引擎完成/并发测量门。
- 设计 §0.5仍禁止人工逐算子审批成为用户每次 profile 的步骤。**一次开发/验收手工审计是证据；长期按算子名/固定SSA/site/hash人工放行是另一件事。** 可以组合通用 producer 插入不变量、已冻结 target/SDK lowering规则的实际审计及每次自动 binary/site/phase/适用范围绑定；无需自动从机器码重新推导所有语义。未知结构继续明确未证。

因此，不能因为一个保守小工具的 broad `*_qualified=false` 没有翻转，就反复新建更大的证明工程；也不能仅修改该布尔值来代替缺失的实际关系。

## 已有 GCU 材料的实际含义

实际读了 `gcu_native_values.py` 全部三种功能及 `gcu_native_control.py` 全文：前者 SHA `dcc0d5eb8a5493dc8b2bda43acb4cb9695631d339855299c7badbea4ded42812`，后者 SHA `90a0c4343e0b0193583500bc2bbabacd25a1b74d47e499ca39ea530190a61f83`。

| 已有材料 | 能复用的事实 | 不应继续把它当成什么 |
| --- | --- | --- |
| R083匹配原件 | 原R069实际两对象的 ELF/native/LLIR及48/62 DI rows，已逐文件核SHA | DI row不是运算范围或一次动态begin/end配对证明 |
| R084实际219条tail | 一个非满尾路径的end-low/high-mask/identity到相对record字段，拒绝未知alias store | 不承担完整ring、begin/site、source区域、选择predicate证明 |
| R085 inline结果 | 23个end候选中14个位置匹配已实现reader形状；另有共享end同一reader的重复报告。实际共享end把推得register经32条guard bridge接到tail | 未匹配reader未必错误；不应为凑23/23而扩全ISA，先看其是否属于尚缺的声明路径 |
| R086 control | 实际packet直接边/入边索引、非零可执行字节核对；清楚保留hardware-loop/indirect未知 | 不等于完整CFG；不用因此把所有库函数的未知opcode都实现一遍 |
| R086 DWARF probe | SDK接受相关debug-value表达；部分寄存器位置可见 | probe ELF与原ELF字节不同，不能认证原capture；也没有必须把DWARF覆盖到所有SSA值的合同 |

R083两个实际 ELF SHA分别 `7d56f25f70633d7f0d813a78e8ded073b884a4356d940a4cb48c710794f00500`、`5860432eef0a3004e35740a68b17b10bd9f33d49bf3ab7a30f8cb11be72131f6`；native SHA分别 `a4423a389544cde04466ad381de272754c8c79d3860eabc48dd86898a9015e8b`、`3e15c05637ef8ab999165d5496ebe07e7dff1967aa648828437c65038c063935`。原LLIR SHA分别 `6b8b2e1a95808ec6f924dac1324f449b44f5177e89f5d5e11de6ade3511eb593`、`acdeadcb66fe11896706b9d384e3d4a7dad22c3aafe8f00bd56ac321f71068e7`。

这些文件已在本地，**下一步不是再采一次设备数据，而是把现有证据接成下面的有限表**。本席未完成该表，不能声称GCU边界已闭。

## GCU 最小可操作完成路径

### 1. 对原先声明的必需区域/循环做一张有限 compiled-object 对照表

按既有manifest/验收登记的区域为分母，区分真正source区域与logger/selector/record bookkeeping；不要把48/62个DI点都变成独立新增验收目标，也不要临时只挑易证明的两个点缩掉原必需范围。每个必需区域只保这些列：

`source/manifest site与语义 → 对应LLVM body/caller → 原ELF function/section和begin/end reader PC → 实际body运算或原submit/wait PC → relevant branch/loop head/latch/exit → observer/predicate → raw端点/occurrence引用`。

允许人工阅读实际native/LLIR，直接列必要路径和短instruction摘录；LLVM producer已有的通用边界不变量、source M:N manifest、SDK版本/链接库身份及当前自动site绑定可以组合复用。只需说明声明body没有越过实际端点，若只有issue bracket就按issue解释。循环则说明每轮所声明body路径都经过对应端点、出口不绕过、读钟未被提升出loop，并复用已存在同binary改runtime K的occurrence；不用模拟机器执行或重测数学。

### 2. 共享end只补实际incoming tuple，复用已过的tail

此处有具体资料缺口，不能用“自动raw链”四个字略过：R086对共享end reader packet **43680**列出26794、34234及43674的直接入口；共享record packet **43984**还列出38698的跳入。原 `0.llir` 的 `^bb16`已经明确合并 `site + begin-low/high + identity`，有来自 `^bb15/^bb22/^bb26` 的三组参数；`^bb53`另有两组参数。

最小读取是这些对应native前驱的实际寄存器/有限spill恢复和LLIR block arguments，记录“哪个source/caller的begin tuple进入哪个end/record”，并说明被选择路径与两端observer相符。可手工核这几个真实入口及相关branch，不要求实现全函数自动SSA重建。R084的219条tail和R085的已核reader无需再证明一遍。r16/r28若仍只是`entry`符号，只沿本实际path读其定义/保存来源并接已有SDK timer/helper证据；不扩MMIO全域、SIP共epoch或物理counter位宽的新研究。

这一步完成后，如果表中每个声明端点均能接到现成raw/decoder/clock证据，**这条具体reader→source/loop补证就够了**；不必再追完整ring alias、全模块返回路径、所有DWARF变量或其它未用reader变体。State/分配/发布已有或独立尚缺的合同继续在各自范围处理，不能借机重开或假称已过。

### 3. ordinary/default/真正sparse只补关键stage关系

复用同已登记source/config/input/target的原ordinary与两观测密度对象及实际异步raw，有限检查：

1. submit对应的真实operation/descriptor、实际buffer/flag以及跨两代复用角色；
2. 原wait覆盖哪些operation/group/flag generation，消费在其必要publication cut之后；
3. 覆盖/重用在旧consumer完成所需cut之后，不能把刚读完同槽与下一轮另一槽混淆；
4. 原本允许未完成的非空future work没有被测量新增wait/barrier或显式结果依赖强制全排空。仅有相同opcode数/相同图不够，硬件实际同时busy则无需证明。

可以像既有NV有限结论一样，用真实LLVM/native短路径、原wait/tag/flag参数、已测payload/generation与消费关系联合说明；不要求逐字节schedule相同、所有指令def-use完备或hidden scoreboard解码。某个`l.loop0`/indirect只需先确定是否真的落在声明stage/loop路径上：无关库范围可明确排除；相关者读取该次setup/target/exit即可，不建通用hardware-loop模拟器。

R083两份profile ELF本身不能独自代表ordinary/default/sparse整组三方。若现有索引尚未给出匹配的ordinary/真正sparse对象，**实际最小缺读项就是同一登记样本的两份对象/manifest及现存raw索引**，不是新数学矩阵。若原件确实不存在，应明确该具体缺项；不能拿另一个shape、另一个runtime编译对象或“budget8标签sparse”替代。本次未盘点这些全部三方原件，故不声称其已齐或要求重跑它们。

### 4. 完成后停止，不另建一层总证明器

形成一次绑定source/ELF/raw/规则版本的有限证据收据，注明已证区域和未知范围。现有公开编译/加载链继续自动核本次binary、site/phase、参与条件与规则适用身份，错误/缺证明确降级；不用把手工表变成按算子名或固定PC放行的长期产品白名单。

如果上述自动绑定和通用插入/适用规则已经具备，补这次手工最终产物审计即可，无需新增通用native verifier。若现在只有marker自动定位而完全没有可复用的body/loop适用条件，最小产品工作是把**这次已确认的通用结构条件**接入现有manifest/资格入口；不是要求实现完整ISA。旧有效负例可复用；只有新增放行路径确缺一个敏感负例时才补对应小fixture，不追加完整测试矩阵。单纯文档/原件补证不需要重建native或重跑数学/TP/UI。

## Ascend：同一最低关系，不能继承GCU资格

本次没有独立读取Asc最终对象，不宣布其已闭。所需范围相同，但使用Asc真实执行主体和原语：

- 取既有实际loaded对象、最终SDK IR/汇编/ELF及manifest，核声明begin/end所在AIC/AIV/subblock、实际source/body或原MTE/flag/wait指令；复用已证参与数量/ABI，不要求新设备参与矩阵。
- 对声明runtime-loop只列本实际head/backedge/exit与端点路径，复用原同binary动态occurrence。helper/shared-end则核caller/site及tuple；不要求全Asc ISA或全库CFG。
- ordinary/default/sparse对照列原set/wait flag的真实ID、资源/buffer、两代复用、producer/consumer及原publication/reuse cut，排除观测新增完成同步或强制排空；不从flag号相同或事件计数猜generation。
- 时钟单位/epoch只使用原证据适用范围；observer issue/wait时间足够，不升级为MTE busy、source-exclusive耗时或所有AIC/AIV共享时钟。对不需跨域比较的source bracket，不另加跨域epoch门。

最小缺读取决于现有索引是否已有匹配三方原对象、source-site manifest和对应raw；先读这些现存文件，不先设计新probe/新LLVM证明框架。某条必需实际边界读不出来，再报告具体对象/PC/源码区域/缺少的SDK文本，而不是笼统说“整个native语义未证明”。

## 可明确停止的额外证明工程

- 为所有库/未知opcode建立完整ISA或一般自动def-use/fullCFG、全局alias/IPA、任意hardware-loop/indirect解释器；
- 为让所有broad flags变true而继续追无关reader、所有DWARF值/路径、整份SDK输出字节一致；
- 证明相同issue order、hidden scoreboard、原子级scheduler等价、完美引擎busy/精确completion/source-exclusive cost；
- 无产品/native/time语义变化时重跑既有数学、1740/其它TP/UI或新增普通数学全矩阵。

这些不是本次原合同内的先决条件。实际新发现跨越边界/错site/错generation时当然修具体实现并做受影响验证；本次未确认这种新产品缺陷。当前不能凭R084–R086局部结果签整体通过，但也没有理由把缺一张有限来源/路径表升级为一个通用编译器验证项目。

## 阅读边界

已读根prompt、设计§0.2/0.5/0.6、测试P03/P07及§8.7/8.9相关条款；T122版本/范围；上述两源码全文；R083原件身份、location和LLVM关键合并/循环分支片段；R084/R085/R086所述直接结果、qualified边界和DWARF probe差异；R087 build结果只确认所述certificate属于高IR preservation，不借其授native source边界。没有逐条审完两份约3.4万行native，也没有本次闭合共享tuple/source/loop表、重审Statewriter或审Asc原件。

本报告只给可操作最小范围和停止条件，不是新whole验收票。
