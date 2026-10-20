# R091 独立最终 delivery / acceptance 闭合复核

**结论：当前不能按原合同签 whole-goal complete。** 原 R075 的 State writer、GCU 预算 cohort、关键 pipeline 及 E01/安装等后续问题已有真实闭环；不能继续把它们列为未做。真正剩余的是 **Ascend/GCU 自动有限 source/loop 边界规则的产品接入，以及原登记集合对适用规则的连接**。单对象实际原生审计、真实 counter bracket 和 source 导航均有用，仍不能代替原合同明确要求的自动规则与完整登记范围。这里没有要求 source-exclusive cost、所有指令解释、所有 endpoint 独占源关联、精确源 iteration ID、engine busy 或完全相同 issue order。

对象为 candidate 与正式 `FlagPrism-method/detailed-profiler` 的完整冻结 SHA **`6ebe9ecb8f13bcd0f32b86fa7a7ab00a44a32107`**；本席 Git 核两树 HEAD 相同且 clean。最新实质产品为 `3b65197ad4ef03fdaeb2bc222e365bf63d0055b0`；其后产品源码/native/patch diff 为空，f7ec2a8 是文档说明。配置沿用原额外独立 R3：请求 GPT‑6.1‑Sol / xhigh；实际 resolved model / effort 未暴露，记 **unknown**。未读 peer 新报告；未执行产品/import/测试/SDK/设备/TP/UI，仅 Git、文本和 stdlib 原件读取/哈希。只新增本报告，不改实现或论文。

## Confirmed findings

### M1 — Major acceptance / implementation gap：原 C1 的自动有限边界能力仍未接入 Ascend/GCU 公开链

**合同位置。** `timeline_design.md:87` 要求边界资格不能依赖人工逐算子批准，本次 binary/site/路径绑定仍须检查；`:93–109` 的 §0.6 规定有依赖直线区域、runtime loop/条件路径、原 wait 三类实际适用模式及实际 observer/参与条件；`:546` 要求规则收据定位最终对象、读钟、区域/块集合、路径及实际约束结果。`timeline_testing.md:45–46` 对普通未见源码的自动规则和字段自洽的语义负例有明确要求。这些是原门，不是本次新增证明强度。

**实际代码及触发。** 普通调用仍由 `profile.py:1579,1589` 选择两 collector。当前实现可以自动保留 raw、来源和单位；但以下代码没有完成上述有限规则：

* GCU `gcu_timeline.py:345–407` 的 `bind_native_clock_locations` 核 final ELF 的 clock debug rows、site/phase 和身份。`gcu_native_values.py:38,205,382` 是有用的 timer/record-tail 检查，但 marker/tail/指令窗口仍由 caller 提供，`:448` 明确尚未自动选择 tail。`gcu_native_control.py:112–215` 只建立有限 packet 边，未知 control/外部 entry 不获得完整路径资格；两者在当前公开采集/重导路径没有 source/loop 放行调用者。
* 新 `GcuExecutionPreservation.cpp:62–214` 确实自动核 whole typed application core 与 fresh observer 内存隔离；原操作不能消费新值，新指针不能碰原内存。它核的是 **SDK 前变换保持**。它没有检查原运算位于最终 begin/end 之间、shared-end incoming tuple 或每次实际 loop 路径经过端点。仅改变新增 clock/record 操作相对原运算的位置并不改变被投影的原程序；因此这个证书的事实不能单独证明时间边界。`:205–214` 的资格划分与此相符，不能删 false 来“修复”。
* Ascend `timeline_ascend_machine.py:161–270` 的 `counter_map` 检查真实 actor/compiler job、ELF/function、DWARF marker 与 SYS_CNT opcode。它不检查两读钟间的计算/访存、caller fragment 的实际边界或循环回边/出口。`timeline_ascend.py:288`、`timeline_ascend_offline.py:34–47` 接入的是这条 counter map。R075 之后该文件变化是 owned-child 清理，不是边界语义规则。

**新增 primary 的真实贡献。** R083 两份 matching ELF/LLVM/native 原件绑定到 R069 两实际 capture；R089 回收的 Asc vector bundle 与 R063 opcode/model 原件同 ELF（`73c2d8d27a949359f22fce1095c56706240d065cad492e73f97653848d682b0d`），site16 的计算 issue 位于实际读钟之间。原 raw 中的多 occurrence 不是虚构。GCU shared-end/source-body/loop 的有限实际关系、Asc vector compute/load/store 的有限位置，允许支持各自被检查对象的真实局部内部解释。Asc induction 在 entry reader 前，并不构成 source-exclusive 产品错误；本报告也不要求把它包回去。

不过，这些 primary 是特定最终对象的审计输入；当前源码没有把相应通用结构谓词变为普通 capture 自动产生的适用收据，也没有相应完整的 self-consistent 语义负例链。Root 本轮明确确认没有未提供的 current96 source/loop 自动规则收据。**不是因为顶层字段保守 false 判失败，而是实际缺少原承诺的检查与调用。** 当前公开 partial 展示本身没有被证实伪造。

**最小实现/验证范围。** 不另建通用 ISA/IPA 框架，也不先重跑数学：

1. **GCU**：在现有 native-location 绑定/离线读取后，把已经分析过的有限 reader→record、共享 end incoming tuple 和 source-body/loop 模式接为机器检查。谓词至少绑定同 ELF/function/site/observer、实际 begin/end 值与 record tuple；声明的 source issue/call 位于该路径的两端内；共享 end 的所有受支持 incoming 保存各自 begin/site；适用 loop 的头/回边/出口逐次经过配对端点。未知 transfer 给具体未证原因。复用现有 `gcu_native_values` / `gcu_native_control` 与 R083 窗口，无需解释整个 native 程序。
2. **Ascend**：在 `counter_map` 之上，针对现有工具链实际支持的 vector 计算/访存子区域建立有限规则，核 actual caller/fragment、SYS_CNT 两端、已识别运算/访存及相关 branch/loop 路径。可用既有 actor LLVM/SDK 约束与 final ELF/opcode 共同形成规则；不要求仅靠反汇编全数学。若只证明 VMULS/VADDS 的 issue 子区域，就只授该子区域，不授整个 source fragment 或 source iteration ID。
3. 冻结这几个实际支持的结构谓词/版本，以真实正例及原计划要求的少量自洽负例核“关键运算越界”“端点/出口绕过”“caller/site 错配”，以及适用原 wait 的覆盖变化。已有正确负例可按同谓词复用；不添加任意 ISA、所有 source member 或所有参与者的额外门。接入后按改变的编译/解释层做正常安装与有限回归；只有生成的实际对象变化且旧证据不适用，才需要准确受影响采集。

## 必要 verification gap

### G1 — 原 V4：独立原六 + 补二尚无完整 source/loop 规则适用连接

**原合同。** `timeline_testing.md:98–110` 对每个 eligible 非平凡组合要求至少两个不同源码区域的真实起止区间，并对适用循环核真实结构；design §0.5/§8.14 不允许一个 site 的证据自动覆盖其它 site。这里不是要求每张导出 view 重新取证：相同 binary/site/路径/工具链规则可以复用。

**实际范围。** 独立集合仍为每后端原六 24 ordinary + 72 profile，补二 8 ordinary + 24 profile；runtime-K 辅助 ordinary 加入后各 40 ordinary。current profile 是每后端 96 个 case。已存在的 State sidecar 是正确的独立门：本席再次核 GCU/Asc 两份 current96 的 q01–q08 各 12、case 唯一且 State 资格全真，但没有从这些 State 判断推出 source/loop。

当前能直接复用的边界材料包括 NV 已安装的 finite scalar/global/matrix issue 与 native-loop 规则，GCU 的具体 tuple/source/loop 对象，Asc 的具体 vector ELF/caller/raw。它们尚未给出 **每个原登记组合至少所需两个真实区域及适用 loop** 的规则/对象/通过或失败关系。没有证据证明所有组合失败；同样没有证据支持把这几份开发对象直接升级为全部 current96。原 raw 中多 site/正 duration 的计数只能证明已观察到端点，不能补足该连接。

**最小补证。** 复用原登记与已封存对象，追加一份有界的按 case 连接结果，记录 actual binary/IR、需要的 source 子区域与 loop、规则版本/适用条件/结果/未覆盖原因；冷暖同对象仅重核身份引用即可。GCU current96 实际只有 **32 个不同 LLVM/binary**，Asc current96 为 **28 个不同 binary、44 个 actor LLVM 输入**，无需 96 次重复同一分析。NV 先把已有 checker 对原实际对象的结果接回该登记，本席未确认 NV 需要新的实现；缺必需输入时先定位可复用原件，不能立即要求重采全部矩阵。

M1 接通后，先离线跑这些实际适用对象。若已有两个充分的可解释子区域，就不用证明其余所有 source site；若普通合法组合仍缺，应记录确切对象/结构并做通用修复。不可删 eligible、换成高级模式、只保成功子集或把人工固定 PC 表变成算子白名单。无需新数学、旧 TP/UI 或无变化 native 重建。

## 已关闭或可复用的事实（按 primary 与影响复核）

| 原项 | 本次核到的实际闭合及界线 |
|---|---|
| **V1 原 kernel State writer** | R078 NV `nvidia-result.json`：ordinary40/profile118 全过，72 distinct partitions，保原失败；这是实际 State 地址/谓词物理 lowering，与 logger writer 分开。GCU/Asc ordinary32 的 SDK/actor/descriptor 审阅可复用，R089 双方补二ordinary8 的 whole-binary 重现与 SDK sidecar各8闭合。GCU R088、Asc R089 current96 sidecar逐 case绑定 math/capture/binary/实际输入与 reviewed SDK；各q01–q08恰12，无重复。Asc1143 transfers/183048 elements，GCU profile的合法地址观察模型仍限定于 source-noescape+preservation，未知写地址拒绝。原历史 false 不改写，V1不再开放。 |
| **V2 GCU 旧预算 cohort** | `timeline-budget-closure-r076/result.json` 全36=原15+补21，逐项 logical metadata相等、原件/raw/trace不变，无应用重放；最大66,230,992B，均≤67,108,864B。已闭，不能再用“只有最大单例”描述现状。 |
| **E01 / storage / reader / child** | R077正常安装及实际一个session10 calls、两binary交错、math/input/tail/State/raw闭合。NV28,846,429B、GCU41,135,845B；Asc原末预算失败保留，cf0ee96正常安装后的原包副本只去JSON空白，完整post-finalize验收66,815,281B，其他原件SHA不变，不冒新设备E01。公共离线三process原trace bytes一致；write/read预算和维护消费者迁移已由本席此前实际审阅/收据关闭。R076四处owned-child修复、normal/-O故障与真实CPU tool smoke复用。 |
| **正常 build/install/source/native/SDK 身份** | NV/Asc R077正常wheel642/440成员及受影响回归可复用；未变native明确复用。GCU R087真正重建 recorder，normal install terminal0/71.371390568s、500成员、14 steps全0；五份source-freeze SHA与当前源码逐项相同。实际37个before的旧installed/new recorder输出37 byte-equal，支持未变采集行为复用，不能称新设备数学。3b65197之后无产品源码变化，不要求无意义重build。 |
| **V3 / 三方关键 pipeline** | NV保既有实际对象、960 raw-backed matrix words/26有限cones及后补ordinary slot/最终对象关系，未再要求隐藏scoreboard。GCU本席R090已直接比较全部444行application core、最终LLVM实际tag/descriptor/ready/reuse与fa9库；真实sparse1和default8保留B先提交后等A、A后续搬运先提交后等B的非空future机会。新增controller初始化、DMA/wait在原State最终wait后返回前；initializer含barrier相关MMIO/intrinsic，不写成“SDK无任何新增barrier指令”。 |
| **Asc C2 BK32 primary** | 本次另读106原件index，全22,631,059B/SHA匹配；ordinary passive codegen产整个npubin逐byte等于原`77d49b1a…`，未借profile original-input当ordinary。actual AIC三方循环均6轮、A/B L1=0/2048，保readiness/reuse flags和同MMA descriptor，AIV独立State不是C消费者。原MMA helper closure SHA`7f4e64f8…`，caller末两event参数-1/-1，对应helper返回前WAIT(2→3,0/1)，不能由较早L1归还误推跨caller未完成M future。未把相同opcode数或无新增barrier单独当preservation，也不制造原本不存在的跨caller overlap。 |
| **单位/真实专用async/语义** | 原三家getter/raw、范围匹配的clock、NV实际shared-byte generation、GCU实际tag复用、Asc recurrence实际flag0/1均按此前本席审阅复用。每capture内部时间门和每后端专用async门仍分开。Asc旧softmax已撤当前推荐，unknown reserved slots旧raw仍partial；participant协议及R06260修复的当前complete身份不撤回。未知busy/epoch/iteration_id不补造。 |
| **SQL / UI / 原件与派生** | 本席此前已逐行核R059 1740的proof_key、实际result SHA/row、263stats及原分母；R062168及后续改变的trace有真实TP原件。R077新增60counter原件已独立读全263stats/trace、exact ns/raw与无正error/data_loss；未变编码可复用旧真实UI。原1740含历史失败，不能称当前成功资格分母，TP成功不消除原资格失败。R087之后QA/SDK定义读取没有新增trace bytes，不要求重跑相同TP/UI。 |

NV性能/开销认证保持用户延期。C1已有同binary runtime-K干预和实际内部重复；GCU已有3/7/11与受控时间数值，Asc不单调事实保留。C2已有三方采集、普通参照/噪声与有限关系；SDK span含host gap，不叫纯kernel overhead或收益。BK64 sparse1一正区间的历史失败保留，不计default，也不据此新增全矩阵重跑门。

## 原 goal §8 与 P01–P10 的最终状态

| 原goal门 | 当前判定 |
|---|---|
| 1 默认普通入口、无逐算子适配 | 实际CLI/API与三家自动采集已通；本轮未发现算子名/shape/hash特判。完整自动合格区域能力受M1/G1限制。 |
| 2 六数学 + 必要补二、数值/调用/完整性/预算 | 原数学/State/调用、原失败与受影响修复、预算已闭；source/loop全登记适用仍为G1。不能称96次首次全部未见通过。 |
| 3 多内部区间/循环、三家专用async、真实clock | 真实事实可复用；完整自动source/loop门仍为M1/G1。不是“没有真实设备时间”。 |
| 4 标准pftrace、真实SQL/UI | 已有实际证据可复用，本轮无新展示层缺陷。无需重复1740或旧UI。 |
| 5 两受控解释案例 | 已有干预、原件与有限关键关系；不冒未证源cost/物理overlap，普通参照与噪声限制保留。完整推广仍受G1。 |
| 6 三家正常安装、故障兼容、P01–P10 | 工程安装/生命周期/恢复链已闭；P03及完整P01的自动边界/适用范围尚未全闭。 |
| 7 额外三席独立审阅及处置 | 本席原具体缺陷已有限关闭，本报告是继续原whole审阅。本席不代签其他席；root应保本轮各独立终态与实际配置unknown的真实界线。 |
| 8 Git/remote/clean、记录、终态、不改论文 | 本席核两本地树6ebe9ec/clean及本轮产品后续diff；root报告已正常push。最终exact remote核与owned任务/record收尾收据由root保留，本席未新连remote或设备。当前剩余判断不能用Git成功豁免。 |

P02/P04/P05/P06/P07/P08/P09/P10：复用本席原whole与后续有限审阅中未变的真实五部件链、target/compiler/SDK/ABI/cache、public owner/transport、raw/guard/loss、clock、typed mapper、共同validator/exporter/存储和故障/幂等证据。本轮没有找到这些项的新具体缺陷。P01/P03仍受M1/G1阻完整验收；不是重新打开其它已闭门。对后续芯片仍按实际部件/target规则复用，不虚构第四设备或量化适配成本。

## 最少下一步与阅读界线

**先实现/接通M1的有限结构规则，再以G1原对象做一次去重的适用连接。** 可复用的已经存在就引用同SHA，只有确切不适用的结构才补通用实现或必要输入；只有真实生成代码变化才决定受影响重采。不要先重跑数学、State、SQL/UI、所有SDK或所有native构建。修完冻结正常安装，相关席只做受影响有限复核，然后root完成原三席处置、record和exact Git交付。

Confirmed blocker：没有新确认的错误输出/崩溃类blocker。Confirmed major：M1，原承诺自动边界能力的未交付；不是对当前partial trace的伪造指控。Confirmed minor：无新增。Necessary verification gap：G1。Optional：无新增实现/实验要求。

本次读原goal全文、design§0/§8.14、testing§0/§4/§8及runtime实际语义；以本席R075–R090已亲自核过且未变的安装、State/SDK、codec、SQL/UI和具体修复证据复用为基础，另看当前Git源码diff、GCU preservation实现/正常安装、实际source-freeze、两家current96逐case及旧36预算、R083最终对象索引、Asc R063/R089 vector原件、R090两家三方实际IR/SDK定义/对象与索引。没有将README的历史pending或别人的结论作现状票。

未重新逐行审全部SDK/所有大型bundle、未重做独立oracle或全部已闭parser，也未对所有current96逐个执行既有checker；后一项正是G1需用已有对象补齐的适用连接，不能被本次局部人工审计替代。**可交付当前诚实限定范围的功能和已闭证据；按原合同整体完成仍不成立。**
