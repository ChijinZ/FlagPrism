# R1：编译边界、自动插桩与三后端可实施性独立设计评审

## 范围与结论

本次为独立、只读的设计合理性评审。阅读了 `timeline_design.md`、`timeline_testing.md`、`timeline_runtime.md`、`timeline_events.md` 及已跟踪 `goal_prompt.md` 全文；本地 SHA-256 均与本轮 `INPUT.json` 一致，输入基线为该文件声明的 `4f5b2bff76ec61537bcec6d98075639d7f9ef731`。没有读取旧报告或其它 reviewer 报告，没有联网、导入产品、运行测试、连接设备或检查额外源码；只写本报告。

结论：**设计可以作为下一阶段工程执行依据；没有发现需要推翻方案的 confirmed blocker 或 major。三后端完整可行性仍是必须实证的开放问题，不能据此宣布已经可实施成功。** 现有设计将高风险假设放在最小纵向样本中提前验证，允许保留 partial，但不把 partial 计入 P01/最终通过，处理合理。发现一项文档导航级 minor，见下。

这不是实现验收，也不是执行合同 §7 要求的最后三个额外 `GPT-6.1-Sol`、`xhigh` 代码审阅之一。本次未核实现代码或设备证据，不能授予任何 site 的边界资格、clock 资格、P01、独立数学、SQL/UI 或最终交付通过。

## 分级问题

| 级别 | 数量 | 结论 |
| --- | --- | --- |
| confirmed blocker | 0 | 未发现设计内部必然无法实现的约束或必须改架构才能解决的矛盾 |
| confirmed major | 0 | 自动区域、晚期边界、主体、物理协议和公共消费职责已有明确交接；剩余设备未知不能无证据升级为设计错误 |
| minor | 1 | 执行合同局部章节索引尚未包含本轮新节；不降低已有全量执行要求 |

### R1-M1：执行合同 §3.1 的局部索引遗漏新节（minor）

位置：`integration/plans/timeline/goal_prompt.md:79`；对照设计 §8.11、测试 §8.6，以及测试 `timeline_testing.md:136`。

合同 §3.1 仍指向设计 §8.1–8.10、测试 §8.2–8.5，本轮新增的具体自动边界、多函数机器映射、校准范围和部件复用检查分别位于设计 §8.11、测试 §8.6。合同 §5 已明确要求完整执行测试设计，所以这不是验收豁免或阻断项；但只沿 §3.1 检查适配边界的执行者容易漏掉最新落地要求。

可行修订：将这一个索引同步为设计 §8.1–8.11、测试 §8.2–8.6，并同步根目录同字节执行合同。无需增加测试数量、接口或验收门。

## 设计合理性与工程落点

### 1. 自动发现与最终边界

设计 §4、§8.1、§8.6、§8.11 把源导航、计数器 PC、真正区域经过时间和硬件完成分开，避免了“早期 TTIR 上插点就获得最终操作耗时”的错误。优化后的 M:N manifest 明确处理 fusion、split、消除；同一物理区间不能复制成两个阶段来满足门槛。公共 planner 选择逻辑意图，后端决定合法锚点，符合三种工具链可能具有不同插桩层的事实。

`timeline_runtime.md` 明示当前 LLVM SSA/memory-clobber 路径仍待机器审计，marker 映射仅定位 counter，不能证明区域顺序。设计 §8.11 也没有把 noinline 设备函数当作各后端共同必需 ABI。这给 NVIDIA 提供了可以试验的具体候选，同时保留晚期插桩/SDK observer 的其它实现路径，合理且没有过早承诺。

本次不能判断该候选经过 PTXAS 后一定成立。最终对象中读钟位置正确，也仍须核所声明操作的实际依赖、执行路径及读钟顺序；不能仅检查两条 timer 指令的静态 PC 大小。测试 P03、§8.2 和 §8.6 已要求自动公开样本、运行时循环、实际指令顺序和多函数对象核对，能够承接这个风险。无需为此另建通用 ISA 或提前要求所有后端使用同一种反汇编工具。

### 2. 普通输入覆盖与编译资格

设计 §8.3、测试 §3/§4 及合同 §2.1/§5 共同锁定 ordinary eligibility 与 instrumented outcome，禁止 profile 失败后改 unsupported、按算子名/shape 特判或改分母。该约束必要；也意味着自动插桩必须真正处理正常优化结构，不能把“边界没保住”包装成用户输入无资格。

两源区域、多次正 duration 是非平凡资格样本的交付门，不是要求每个极短源操作都有独立时间条。设计允许选择更粗的真实区域，同时禁止复制 fused duration；这保留了合法实现空间。如果某个已冻结普通样本最终无法产生两个有证据区间，应按现有规则保留产品失败并修通用边界，不能用漂亮的其它样本替代。

运行时 K 改变但 binary 不变、occurrence 与 iteration 分离、紧凑 slot 按真实 launch grid 绑定、旧 full-grid binary 拒配新 allocator，以及查询缓存前绑定实际 compiler/plugin/timer/rule 身份，均有相应验收场景，未见需要扩大架构才能闭合的缺口。

### 3. 三芯片适配边界

| 后端 | 合理的实施路径 | 当前必须保留的未知 |
| --- | --- | --- |
| NVIDIA RTX PRO 6000 | 在已有自动 scope/raw 路径上完成最终机器边界、clock/ns 与公共导出，再闭合实际 async 及物理复用样本 | LLVM 约束是否保留到最终机器代码；实际 getter 尺度/epoch；逻辑 cp.async group 到本次真实 buffer/slot/generation 的证据 |
| Enflame C200 | 复用现有 SDK timer/interval 接入，补后期边界、真实写者协议与机制映射；允许独立 clock provider | 早期插桩后的实际顺序、timer 比例与误差界、合法异步结构及 SDK/对象是否暴露足够身份信息 |
| Ascend 910B | 基于现有晚期 observer/SDK handoff 做时间区间和实际 AIC/AIV/MTE 同步映射，保留独立 cache-line/发布规则 | observer 之后 scalar 优化的影响；新 timeline 协议的可见性；SYS_CNT 适用范围及跨 actor epoch；动态 flag/buffer 分代 |

这三条是有具体切入点的工程路径，不是三后端可行性证明。文档没有要求把 NVIDIA 线程树或物理 ABI强加给另外两家，transport 与 decoder 可独立复用，clock/mapper 可按目标条件替换；公共层仅核有类型事实并导出。新语义允许版本化扩展而无需零公共改动，这比预建完整插件框架更可实施。

最不确定的目标是各后端真实异步的动态关联、物理复用及所需 clock 比较范围，而不是 Perfetto 绘图本身。设计先 A/B、再完整 C/P01、最后 D；允许另两后端先调查原语。这个推进次序合理，且没有通过分阶段降低最终门槛。

### 4. 时钟、依赖、发布与展示的交接

设计 §6 对尺度与 epoch 分别取证、整数/有理数换算、完整回绕歧义、端点不确定界和不可比较域分文件有明确要求；§8.11 不把有限因果样本当普遍硬件误差上界。这些约束能避免把真实 tick 错变成精确 ns 或伪重叠。独立校准样本不重放用户应用、校准同步不注入用户 kernel，与“一次请求一次执行”不矛盾。

动态模型允许 submit→group→部分 wait、多消费者和多轮 generation；机制闭合要求覆盖实际状态变更，opaque/外部变化不能默认为不存在。公共完整性校验与真实 ISA/SDK 语义证据分工清楚。P07 明确 group-only 不能替代物理复用门；这会增加后端取证工作，但不是要求编造不可观测字段，也没有依赖硬件必须暴露现成 token 的假设，编译器可沿真实路径维护可验证逻辑状态。

owner 设计区分初始化写入、提交、完成、读回与安全回收，承认超时不能证明设备停止；每 invocation 快照和 session pending 总预算能支持多调用隔离。两 stream/thread/graph 按事前冻结范围验收，不强迫每种 SDK支持全部并发；不支持路径须早拒绝，边界合理。

Perfetto 作为派生消费者，只展示资格满足的 ns/edge，并以真实 Trace Processor、逐条 raw 对照和实际 UI分别验证，足以避免“protobuf 能打开即通过”。保留 raw、旧判定和 proof 身份允许补证重导而不重跑应用。预算和稀疏/较密扰动比较已有要求；不需要新增一套状态台账或性能认证来支持这个设计结论。

## 剩余必须设备验证的项目

以下均为 **verification gap，不是本评审确认的实现缺陷**。现有 P/E 已覆盖，不建议额外扩资格矩阵：

1. **每后端自动最终边界**：公开 API 的 runtime-K 有依赖循环与 load/compute/store；同 binary 改 K；核实际 counter、被观察指令、控制路径和 occurrence。若实际对象有 helper/callee，核真正代码段与地址范围；无新完成 barrier，原数学/副作用/canary 正确。对应 P03、§8.6。
2. **每后端物理发布及身份**：NVIDIA完整 timer/record 位宽与 observer 映射；GCU实际写者和完整 payload；Ascend新时间 logger 的独立 cache-line/commit 证据。紧凑存储、真实 grid 变化、未选 program 不写选中 slot，均须实测。对应 P04/P05、E02/E04/E08。
3. **每后端实际 clock资格**：getter 对象、尺度、误差来源、reset/wrap有效窗口和目标范围；凡异步图需要跨主体比较，另证对应 epoch/offset。训练/留出一致不能单独授予普遍误差界。对应 P06、E09、§8.6。
4. **每后端真实异步及两轮物理复用**：普通编译已含合法机制，manifest 与最终对象的状态变更闭合；保本次 submit/commit/wait/completion 覆盖、buffer/flag/slot/generation、首轮/steady/drain 证据，缺失时不生成 verified edge。对应 P07、E10及测试 §5。
5. **真实公共全链**：三后端分别经匹配构建/公开安装、自动采集、owner、decoder、共同 validator、合格 ns视图、同一 exporter与实际 SQL/UI。当前 NVIDIA raw/marker状态不得继承为认证通过。对应 P01/P08/P09/P10及独立新数学。
6. **生命周期与兼容回归**：声明支持的并发真实交错；不支持的早拒绝；初始化/提交/读回失败不提前回收；cache mode/SDK/timer/ABI切换及旧count/native不退化。对应 E01/E03/E05/E06/E07、P10。

这些证据尚缺时，可以继续最小样本开发；不能宣布三个目标芯片已完整适配，也不能用本次设计审阅替代最终指定配置代码验收。
