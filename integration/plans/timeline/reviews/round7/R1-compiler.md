# R7 独立设计评审：编译边界、优化扰动与执行模型

评审输入（结论对应下列字节，不对应已提交 HEAD 的旧版本）：

- `Profiler/docs/timeline_design.md` SHA256：`da1cf2ccbc3045a7d9236b139207de4e47dcdfe51509cb669332e1703aed4751`。
- `Profiler/docs/timeline_testing.md` SHA256：`c33395132ae5f0f6d77127f2d4dadd76be07ac89fd068b257c4965f9d1ab616b`。初读时为 `3a6d1405fc1d18066b881153a0172b6a229a4e1397132968dcdf3aeb91645cde`；复核已确认 §8.1 引用更新为设计 §8.1–8.12，最终按本项新 SHA 评审。
- 工作区 HEAD：`7fceb5e41e33359146353edca36e37feb18527c3`；工作区有未提交改动。
- 模型请求配置：父任务转交确认 `model=gpt-6.1-sol`、`reasoning_effort=xhigh`、`fork_turns=none`。这是请求配置；实际服务型号未暴露，不作推断。
- 独立性与操作范围：未读其他本轮 reviewer 报告，未调用其他 agent；只读设计、验收、raw 合同及相关真实源码。未修改产品或设计/验收文档，未 import/运行产品、编译、运行设备或执行测试。本文件是唯一新增产物。

## 判断

**设计合理，可以进入最小纵向实现；未发现必须推翻架构的设计阻断。完整三后端实际可行性仍未决。** 分离编译、transport、物理解码、clock provider、机制映射和公共消费者，与实际变化原因吻合；不同物理 ABI、非 warp 主体、源 M:N 映射、部分 wait 与多消费者都没有被公共模型预先排除。新增 §8.12 和测试 §8.7 进一步关闭了“离线可读即采集可用”“counter PC 即源边界”“时钟正确即所有结论正确”等错误放行路径。

实现风险集中在需要真实机器证据的三处：编译约束是否一直有效到最终对象、约束是否把原本可流水的结构串行化、各后端是否能提供所需的时钟/发布/动态复用事实。设计把它们列为门槛是正确的；它们尚未通过，不能据此宣布设计错误，也不能由接口合理推出设备路径可行。

后续芯片的成本判断应分开：同工具链且 ABI/getter/机制兼容的新型号，有条件地能够复用大部分公共链和部分设备部件；新工具链或新执行模型的接入仍可能需要晚期 pass、launch ABI、发布和机制规则。现有三个后端尚未形成完整共同消费的设备证据，因此“公共重复工作可减少”目前是合理设计判断，“新增芯片已经能以低成本接入”尚未被证明。文档目前没有不当地承诺固定工期或只写 decoder 即可。

## 发现与最小修订

### F1：旧概念接入动作与新独立部件的职责容易混淆

- 严重度/类别：**P2，可改善文本；不阻断设计或最小实验。**
- 位置：设计 §8.9 的 `decode_capture` 行（约 L267），对照 §8.12 首段部件约束（L369）及产物表（L378–379）。
- 可复现的歧义：§8.9 将 `decode_capture` 的输出写为 typed batch、clock proof 和机制事实；§8.12 又规定 physical decoder 不构造 clock proof，provider/mapper 各自输出事实。若把概念动作直接实现为 physical decoder，后续同 ABI、不同 getter 的型号就会把 clock 证明耦合进 decoder，或迫使 decoder 自行选择 provider。两种理解会产生不同的复用边界。也可以合理地把 `decode_capture` 实现为编排 façade，所以这不是无法同时满足的硬矛盾。
- 最小修订：明确 `decode_capture` 是编排动作，可组合独立 decoder/provider/mapper；或把该行拆成“物理解码只产 typed raw batch，provider/mapper 分别产 proof/机制事实”。不必新增类或插件系统。
- 验收对应：测试 §8.7 P02/P09 的调用链应分别列这些实际部件及输入身份，不能只定位同一个大函数后就声称独立替换已证明。

### F2：插桩扰动检查应明确区分固定配置对照与调度干预

- 严重度/类别：**P2，可改善验收精度；不是已发现的产品失败。**
- 位置：设计 §8.12 L387、§10；测试 §5/C2 与 §8.7 P03/P07/C2（L248）。
- 失败情境：C2 合法地改变 tile/stages/buffering；若同时用不同配置的 ordinary、稀疏和较密结果判断“是否因测量串行化”，就无法区分配置本身的 schedule 改变与插桩造成的改变。全量资格的冻结配置要求已限制这种做法，但新增扰动行的“同数学合法配置”没有直接说明这组三方对照也必须固定配置。
- 最小修订：补一句“每个扰动三方对照固定 ordinary 编译配置、输入、grid、数学与机制，仅改变采集密度；C2 的每个调度变体分别做此对照”。再在 ordinary baseline 中登记待保持的具体关系，例如 commit/group/wait 覆盖、同一 buffer 的消费前等待、可同时 in-flight 的组和 compute 所处阶段。无需要求指令逐字节相同，也不新增吞吐或开销比认证。
- 判定边界：静态保留合法重叠机会不等于已经测得普通程序的真实硬件重叠；仍须遵守设计 §7，只在证据允许时声称 engine overlap，否则称 observer overlap/结构关系。

## 必须先取证的风险，不计作设计缺陷

### R1：边界约束与保持流水可能互相拉扯

- 严重度/类别：**P1，设备资格放行风险，当前未决；不是设计阻断。**
- 位置：设计 §4、§8.11–8.12；测试 P03、§8.6 自动边界、§8.7 插桩影响。
- 只读事实：`AutomaticScopes.cpp` L389–408 在所选优化后操作前后插 Record；`ProtonToProtonGPUPass.cpp` L106–132 把输入接到 begin、结果接到 end，并给输入加 anchor；`PatternProtonGPUOpToLLVM.cpp` L162–168 将张量依赖拆成标量；`TargetInfo.cpp` L79–126 为 counter 建带这些参数的 noinline 设备函数。PTX 内的依赖注释和 LLVM 实参是现有手段，不是本评审授予的最终机器顺序证明。
- 可证伪情境：有依赖 runtime 循环的边界仍存在，但操作越过读钟；或者边界确实固定，参数传递、值存活期及设备调用却改变展开、寄存器使用和 copy/compute 的调度关系。数值正确、正 duration、无新增 barrier 以及总指令数接近，都不能单独排除这些情况。
- 最小处置：设计要求本身正确，无需预先改成统一设备调用 ABI。先做同配置 ordinary/稀疏/较密的最终对象对照；逐 site 给出 begin→目标操作→end 的控制/数据约束和函数地址范围，并核机制关系。失败时改通用 lowering 或选择更粗区域；不得将 counter 间隔直接升级为源区域耗时，也不得为稳定边界补完成屏障。

### R2：另外两后端的公开 producer 路径仍需实证，离线 adapter 不能代替

- 严重度/类别：**P1，设备资格放行风险，当前未决；不是因未实现而否定设计。**
- 位置：设计 §8.12 L385–387；测试 §8.7 默认采集、分层资格及恢复。
- 只读事实：`timeline_events_enflame.py` L48–55 仍校验单个 selected program 与 work-item 0；这是既有 raw 的真实支持范围。GCU timer 插入与所选写者分支位于 `Debugger/lib/Instrumentation/Passes.cpp` L3847–3887 的编译路径，不能仅凭旧 pair bytes 证明优化后的区域边界。`AscendLateObserver.cpp` L1002 将其阶段标为 `post_actor_lowering_pre_scalar_optimization`，L993 仍描述动态 v1 记录布局；真实最终对象、后续 scalar optimization 和新发布协议各自要核验。
- 可证伪情境：共同 reader 能读旧单 program GCU raw，但默认首末两个 program 的生产者、紧凑 slot 或 completion owner 未接通；或 Ascend 早期 observer 的 LLVM 区间在后续优化中移动，或借用 census 已修复的发布结果来替动态事件背书。新版公共 schema 可以全部通过，但上述目标能力仍没有通过。
- 最小处置：遵守既有门槛，不放宽 Python 校验冒充生产者扩展。各用一个普通 runtime 循环和一个真实异步样本，取得公开入口→最终对象→安全原件→公共 batch 的新设备链，再接 clock/机制。旧 raw 只证明相应实际旧格式的读取。

### R3：新执行模型的成本主要落在晚期映射和机制闭合，公共角色扩展本身不足

- 严重度/类别：**P1，后续型号可行性需目标设备验证；当前架构选择合理。**
- 位置：设计 §8.1–8.3、§8.9–8.12；测试 P03/P04/P07/P09。
- 只读事实：当前 `AutomaticScopes.cpp` L100–108 对 warp specialization 祖先的例外用 `census` 开关控制，timeline 不能直接继承已有 census 的 partition 覆盖。`hooks/instrumentation.py` L402–421 接入 `ttgpuir_complete` 及后续 lowering。由此能确认存在可复用 hook，但不能确认所有后来拆分的主体或新增机制都已被覆盖。
- 可证伪情境：后续工具链在当前规划点之后才引入搬运主体、隐式 commit 或额外 barrier 状态。若只复用早期 site 和新角色字符串，公共验证器仍可能看到自洽却遗漏状态变更的事实，或逻辑 program 与多 CTA/actor 的映射不完整。
- 最小处置：不必另建统一硬件 IR。每个适配清单列出“规划点之后还会发生哪些 lowering、谁产生最终 manifest、如何逐机制检查所有状态变更、哪些映射必须拒绝”，并以实际最终对象和动态记录闭合。新语义确实无法表达时按现有规则扩合同并回归，而不是把它藏进扩展字典。

## 最先执行的最小实验

本次不执行以下实验；它们复用现有 D/P/C 门，不扩大独立资格矩阵。

1. **先在首后端闭合自动边界。** 普通 load→有依赖 runtime K 循环→store，K=3/7/11；确认捕获之间同 binary，而 ordinary 与插桩对象各自留 SHA。固定编译配置和 grid，做 ordinary/稀疏/较密对照，保存全函数/代码段的最终对象、实际 timer/getter、精确 raw 引用、循环 occurrence 与数值/调用次数结果。先证明两个源区域，不能只证明 marker PC 或手工探针。
2. **立即对一个真实流水样本证伪扰动。** 先确认 ordinary 对象确有实际 async 机制及至少两轮物理复用，保存首轮、steady state、drain 的 group/wait/compute 和地址或 flag 代际事实；再比较同配置三方对象与实际记录。若只剩逻辑组，保留有效结果但不通过物理复用门。若插桩使关键流水串行化，先修通用结构再做 ns/Perfetto 展示。
3. **另外两后端各做相同语义的小链。** 先取最终边界和发布证据；GCU 验独立尺度/误差及实际异步来源，Ascend 验新 timeline 写者/对齐/commit 与所需 actor 时钟关系。用默认两个真实 program 和单 program 分别核 launch 绑定，不能沿用旧单 program raw 作默认入口正例。原件先落盘，再故意令 decoder 失败重读同一原件，确认应用次数不增加。
4. **只在前提满足后验证共同消费。** 三份 canonical 数据经相同 validator/clock 派生/exporter 进入实际 Trace Processor；至少一份分别删 boundary、scale、epoch、动态关联证明作负例。保持有效 partial，但完整 P01 的两源区域、异步/复用、所需时钟和导入门一项也不豁免。实际 UI 与独立数学仍在后续 D 阶段完成。

本评审的放行范围止于“设计可执行，按上述小实验推进”。不授予任何后端 P01、不授予 ns/源区域/跨主体时序资格，也不替代最终实现与设备验收后的三人代码评审。
