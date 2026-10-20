# R2 最终 runtime 闭合审阅

请求配置 GPT-6.1-Sol / xhigh；resolved serving 配置未暴露，unknown。冻结 candidate **`6ebe9ecb8f13bcd0f32b86fa7a7ab00a44a32107`**，Git实际核对，工作树clean。`3b65197…` 至该freeze的 Debugger/Profiler/integration patches 仅 `timeline_runtime.md` 增16行；最新实质产品变更仍为正常安装过的R087 GCU preservation。本次延续本席R075整体走查及R076–R089已核有限closure，没有重启产品/测试矩阵，没有产品import、checker/SDK/设备/SSH/TP/UI执行，没有读其它席结论。只写审阅文件。

**当前未发现尚未处置的 confirmed blocker/major/minor。原child、release、CAS预算/公共读点、多调用预算及本席已核生命周期问题维持关闭；两家BK32关键pipeline关系的原件现可支持有限保持结论。仍不能签原完整合同已全部交付：G1/V4还缺“当前冻结必需source/loop区域→已审SDK/native family条件→本对象”的适用范围连接。这个缺口只有一项，不是所有机器码语义、所有SSA或每个ELF都须重新人工证明。**

本报告是当前本席最终结论；R090 `boundary-scope-closure-v1.md` 是同一项范围判断的细节，不是另一轮whole审阅或新增门。

## 已闭范围及证据性质

| 原要求 / 问题 | 当前本席判断 |
| --- | --- |
| 三后端公开CLI/API、自动source/site/隐藏ABI、实际调用/observer/raw身份 | 复用R075代码走查和真实普通数学/安装证据。没有按算子名/shape/hash派发的新产品变化。source导航不被解释成exclusive cost。 |
| timer / clock / 动态关联 | 维持既有分项资格：实际raw端点、位宽/单位/窗口、observer epoch及机制关联分开；有限每capture时间证据不代替每backend专用async门。没有新clock或跨域主张。GCU同MMIO不推出跨SIP共epoch，46bit是返回值表示上界；AscAIV参与数按实际feature/getter处理。 |
| owner / release / readback /失败恢复 | 原resume collector、release ledger/quarantine、stale index撤销、namespace等修复维持。非零free结果unknown不盲目重试，不伪成功；CAS pending release重试核完整owner事实及原件闭包，排除项仅error/release_status。没有新增全局同步或逐launch host wait。 |
| R075 M1 child清理 | R076 `runtime-child-v1.md`所核4处try覆盖、直接Popen fallback和bounded reap，61cb831三正常安装/normal与-O各12真实sleep-child故障及真实CPU工具smoke维持关闭。CPU进程fixture不冒设备数学。 |
| CAS、预算、公共读取、release retry | 复用本席R077 codec/release closure：writer/reader预算对称、immutable原件闭包、legacy/公开离线三process读点；ea2c936三正常安装55+11、六类owner/raw/object/metadata/guard negative等实际收据。未变产品不重测。 |
| E01 / whole bundle预算 | 历史NV一session交错两specialization成立；当前NV/GCU actual E01 whole28,846,429/41,135,845B。Asc原67,773,556B terminal1保留；cf0仅JSON空白压缩后的owned-copy post-finalize验收66,815,281B，raw/trace/其它原件不变，无应用重放。没有把原失败改成device pass。E02原“本席未逐完收据”不自动成为新缺陷/新设备门；当前合法零grid不造owner/event路径仍在。 |
| State独立写者 / 当前登记 | R088 GCU当前96身份与SDK/partition sidecar、R089 GCU补二ordinary8、Asc补二ordinary8/current96的直接terminal/row结果可复用。Asc current96 sidecar terminal0、96 qualified、AIV96/AIC36、1143写实例；GCU supplement partition terminal0和8条sidecar。它们明确不授native timing/pipeline，未拿State通过填本报告G1。此项不重开。 |
| 数学、TP/SQL/UI、安装/故障与兼容 | 原实际矩阵、1740及后续TP/UI及本席已核安装/离线closure按原身份范围保留；本次无相关产品变化，不要求重跑。新CPU原件读取不是新的device/TP/UI正例。最终Git push/远端HEAD/所有owner终态仍需root在交付时做实际收尾，本席没有访问服务器核当前live进程。 |

历史事实继续保留：NV一次7条零记录被拒绝，有限未复现不称修复；Asc旧reserved unknown batch partial及48+24 dependency unavailable不被新专用recurrence洗白；BK64 sparse1仅一正区间的严格失败不计default。它们不能被删除，也不能据此无限扩大当前矩阵。

## 本次直接补读的两家BK32 pipeline

没有读取run090的peer review报告。实际读的是 `run-090/preflight/{gcu,ascend}-BK32-pipeline-receipts-v1/` 中ordinary/两密度capture、manifest、SDK输入/观测IR及原件索引，和两份实际SDK helper closure。

GCU primary archive `bbcff87a…`，48文件/26,580,723B；Asc primary archive `3877a60b…`，106文件/22,631,059B。直接收据列全部index SHA核同；本席另核关键helper实际文本SHA。

### GCU：原tag、消费和复用关系可接上

ordinary GCU IR SHA `e038ddb44934841062b068e8083857346c961b7036cafb41d89e5083d8eb384b`；ordinary LLVM `960bb7e5095736daeae4cf536b6030d7e176cc6b7b3a546381d4bb6c2112acd2`。density1/8原execution input同SHA `0f9fd0f84e8e2dfbfcc40671e4469521f9a9f464cd2c6f4fb27ac072315d03f5`。直接读取其loop和调用，并核普通/观测body对应：loop-carried accumulator、A/B staging及shared转换、原wait/barrier/matmul的参数角色一致；没有把单纯opcode数量当证明。

| 关键阶段 | 实际关系 |
| --- | --- |
| 两路原submit | 原 `%24:memref<3xi32>` private tag；A staging `%159` 用index1，B `%170` 用index2。A和B均submit后才开始A的必要wait，保留原先允许两路搬运未完成的阶段；不是要求新增下一round预取。 |
| publication / consume | A原wait覆盖其有效元素数`%163`，然后deslice→shared `%174`，原wait(index1,1)、原barrier，再slice到`%182`；B相同路径用index2到`%183/%187`。最后原wait后matmul使用`%182/%187`和loop-carried accumulator。 |
| 复用 | matmul后才dealloc本round的A/B及shared staging，结果descriptor送回scf.for。后续round复用由原控制/访存顺序与SDK调用语义决定，不从tag号相同推代际。 |
| 观测 / publication | 两密度SDK LLVM均在相同caller/body路径包原调用；timer/record值不进入原matmul operands。新logger DMA/private tag在原return发布，不替代application tag，不在A/B之间插应用完成wait。 |

实际链接SDK `gcu300_tops_builtins.bc` SHA **`fa9d850080258f7cfd3acbdccfdb3485007b9b87c3c5ed34ab187dacbb52944a`**；closure文本SHA **`f09d690912c6b0c357a140e01b2e24a2986fd46633ac6c3bba59f9ba330cd870`**。本席读取 `tops_wait_dte` 的pending-counter维护与最终 `llvm.dtu.l.wait.dec`，以及原`tops_addmm_fp16_fp32`的输入/accumulator/输出角色；不是以helper名字臆测忙闲。

两密度raw均131136B，实际逐文件核SHA分别 `63f94caae4b3caf70ebc9a4e525e3f84700b9ae36c15542ca70bf29b7fc7f601` / `41aaec4fc16499ba6f6508a39cb861da1180a8b37ae48c3d83cf1b3435f937f2`；canonical实际194/196 interval，两个observer各97/98 pair，complete。**这里没有已qualified的dependency flow收据（details列空），本报告不补造flow。** 这些raw和同对象IR支持本例关键stage/原wait/复用保持；每backend完整async关系仍复用先前专用样本及原mapper资格，不能拿C2图代替。

### Ascend：L1租约与MMA helper中的原cut可接上

ordinary passive codegen terminal0，沿原SDK `1f5cc505…`，整包 `kernel.o` SHA **`77d49b1a3f9f67358f72743a68c39e8adef48a4799af591e4b1ad4f484e8d0cd`** 与原npubin逐字节相同；不是只匹配两份mixed child的`.text`。本次没有因此重新运行设备。

直接读ordinary AIC LLVM `f10d3806…`、两密度AIC original/adapted LLVM和实际MMA helper。A L1槽为0、B为2048；每round原MTE1→MTE2 wait(event1/2)后才nd2nz重填对应槽，再分别SET MTE2→MTE1(event0/1)。原MMA caller传入 `(readyA=0,readyB=1,releaseA=1,releaseB=2,kloop,back0=-1,back1=-1)`。

实际SDK library SHA **`94c9885a52c9e4cfdfbc239ad104f0a4d14cd330cff9c51d141eb08e88f9ef4f`**，三方receipt均绑定同库；helper文本SHA **`7f4e64f840da5f1c581754e8e57cfa3f9510ddff57b422fc2f3f05824d70c7e9`**。其真实代码在outer-k start等待MTE2→MTE1 ready0/1，load L1→L0A/B后在outer-k end发MTE1→MTE2 release1/2；L0/MMA ping-pong另有原M→MTE1 wait/set。back事件为−1时helper尾部原来就wait M→MTE1 0/1；**这段drain不是logger新增，也不能把它当测量串行化缺陷。**

两密度保相同L1地址、原flag覆盖、MMA调用参数和loop回边；读钟/record不变成原MMA的data operand，没有新增application completion barrier。原raw complete，density1/8为112/160 interval、各786816B，SHA `3d15be39…` / `617cf28c…`。density8两个AIC observer的循环复用wait1/2各有6个实际occurrence；初始priming和末尾wait分别保为各自site，未按相邻时间猜generation。

**有限G2结论：两家此BK32 ordinary/default/真正sparse的原关键buffer/tag/flag、publication/consume/reuse cut保持有了实际对应证据。** 不授实测hardware overlap、busy、精确完成时刻或逐字节schedule相同；也不从BK32扩大为旧BK64 sparse失败通过。结合本席R083已闭的NV有限对应，R075原G2不再以旧“尚无三方关键关系表”状态保持开放。

## 必要 verification gap：G1/V4只剩适用范围连接

本席R089冻结GCU表是真实肯定证据：ELF `7d56f25…` 中bb16三incoming、site4另一个end→record、bb53两incoming，以及source39 runtime head/body/end/record/latch/exit已闭；两个observer各3条actual occurrence接raw。不能重新报成只有helper/DI行号，也不能升级为所有不同body/SDK结构自动相同。

R087通用preservation和R069自动manifest/binary/site绑定同样可复用。但实际当前代码分别证明的是：

- `GcuExecutionPreservation.cpp`：原高GCU IR SSA/CFG/内存效果恢复与observer隔离；
- `GcuTimeline.cpp:355–406,465–495`：原op/fusion border选择、同block配对及插入；
- `gcu_timeline.py:345–410`：实际ELF DI site/phase/PC身份和missing位置；没有检查声明body/loop属于哪条已审最终lowering规则。

**缺的是这些肯定事实如何覆盖原冻结必需区域的中间条件，不是几个false字段。** 目前本席直接读到的身份索引中GCU current96只有32个不同LLVM/binary；可以按实际结构进一步合并。未读另一ELF本身不算失败；不属于原必需声明的区域也不新增分母。

最短真实补项：复用现有current96/replacement身份表及保留manifest/SDK LLVM，为每个不同实际结构列 `必需source/loop → producer/SDK规则版本和适用条件 → 本次site/caller/selected/tuple/loop范围 → 原raw/occurrence`。冷暖调用只做身份join，不重复编译或人工审机器码。只需读与这些条件相关的已有block/caller/loop片段；固定helper/record尾、实际clock/ABI事实沿原证据复用。若已有等价结构收据，直接引用，不重建一个工具。

可复用条件至少说明：目标/SDK/compiler/library内容身份相容；原producer确实产生同种配对区域/primitive caller/loop形态；实际声明的body和两端路径/observer落在已审规则范围；原冻结两source、多正区间和适用loop的实际commit没有被缩掉。数学源码或ELF SHA不同不自动失效；另一个caller/出口/主体形态不能只凭同primitive名字继承。

**先补这个已有材料的覆盖连接，不预先要求新产品项目。** 若原公开链已经自动确定这些条件，只补一份证据索引即可；仅在它实际上无法检查/绑定必要结构时，把这次已证的有限条件接到现有编译/补证收据入口。无需自动从任意机器码推导全部语义、全CFG、allSSA、逐算子白名单或人工用户批准。成功覆盖原必需范围后，这个G1/V4门即可关闭，不再因其它broadfalse或未知ELF继续扩量。

Ascend按同一最低标准：actual observer compute issue/wait和真实循环重复足够；induction在reader前不等于失败，不要求每条记录恢复source iteration_id。本次不读peer Asc审计结论，故不以其肯定票替代本席适用性判断。适用连接可以引用其原件和规则事实，不要求再做另一份完整ISA审计。

## Optional 与交付判断

没有新增optional工程门。不要求source-exclusive、全参与/协作区域全耗时、hardware busy、跨SIP统一epoch、hidden scoreboard、任意ISA证明或重跑数学/TP/UI全矩阵。

本席当前**不能按完整合同签交付通过**，原因仅为上述必需适用链未在已读组合中闭合；没有确认必须先修的新runtime bug。修复/补证完成时只需受影响有限复核，不重开已经关闭的owner/CAS/预算/State/数学/SQL/UI以及本次BK32关系。

阅读范围：复用本席R075、R076、R077、R083、R088、R089；本轮实际读原合同与相关source，R087直接结果/正常安装/37输出比对，R088/R089 current96/补二ordinary索引与终态，R090两家BK32主原件和SDK closure。未逐条审32份GCU最终对象、未把Asc其它席报告作为事实来源、未重做所有历史raw或1740TP/UI；这些阅读限制不自动生成额外测试要求。冻结后的远端push和当前服务器owner最终清单由实际交付收尾核验。
