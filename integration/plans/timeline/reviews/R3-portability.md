审阅输入 SHA256（完整阅读下列三文件，以下位置均指这些字节）：

```text
ef6d20936e0a879e1b9bde36c7cbf81e37d98ce3dd680c2388070bc7274327fc  Profiler/docs/timeline_design.md
224a1c94c7748510a68054f1fa4a58b3e3ef34185dd168c64e2d86e6177786e4  Profiler/docs/timeline_testing.md
567234333175566f4056dc6b09db4a7ad7e3c4e5684f59d7d19dc5bc6b1d69b1  integration/plans/timeline/goal_prompt.md
```

# R3：可移植性、公共消费边界与可执行验收的独立设计评审

- 日期：2026-10-17。
- Reviewer：`/root/timeline_design_portability_review`。
- 请求配置：`gpt-6.1-sol` / `xhigh`。本 reviewer 可见上下文没有暴露实际 serving 型号与 resolved effort，实际值记为**未知**，不声称已独立验证请求配置兑现。
- 仓库读时 HEAD：`775f7b44c879b515a71d2eb48f1196321d75786b`；三份被审文档均为工作树修改，审阅绑定上列内容 hash，不把 HEAD 当作其内容身份。
- 方法：文档全读，必要源码静态核对。没有产品 import/build/test，没有 SSH、设备、Trace Processor 或浏览器实验，没有读取其他 reviewer 报告；只新增本报告。

## 结论与启动意见

**意见：先修订下述两处验收文本，再启动受约束的 P01 可行性工作；无需推翻总体设计。不能凭本次静态评审承诺三后端必能按某个工期完成，也不能跳过 P01 直接冻结全量资格方案。** 本报告不构成启动实现或设备工作的授权。

未发现已确认的架构 blocker。确认一项 major 级验收适用范围歧义、一项 minor 级执行地点冲突。三后端计时与异步机制、公共 schema 和 exporter 的主要剩余问题属于 **verification gap**：文档已要求实现它们，但当前没有实际新实现与设备证据，不能包装成设计已被证明可行，也不能由缺证推导硬件不可能。

架构方向合理：公共意图、晚期执行 manifest、后端物理记录与语义映射、公共校验/导出的拆分，能把未来适配中重复的配对、时钟转换、loss 解释、Perfetto 与源码展示工作集中维护。仍必须逐目标完成的工作包括编译接入、优化后边界、主体映射、timer、发布协议、原有异步机制及安装。当前三后端完成后，最多可证明这三种实现的公共部分复用；不能证明第四种芯片的适配时间或“只改配置”。设计 134、180–186 行对此表述准确。

## Confirmed findings

### R3-M01 — major：UI 操作清单把循环与动态 flow 无条件施加到每一份样本

- **位置**：`Profiler/docs/timeline_testing.md:120–130`，尤其 122 行“每份操作与截图”、125 行“zoom 到一个真实循环”、127 行“点一个有证据的 flow”；对照技术设计 12、118 行、测试设计 29、64–71 行及合同 48、59、116 行。
- **触发**：每后端只有一个真实异步算法，其余合法普通资格样本包含没有循环或没有异步依赖的融合/归约算子。它们有多个真实内部区间，诚实地不导出 flow，满足主目标中“每后端至少一个异步案例”的边界。
- **证据与影响**：主目标不要求每种算法都产生异步结构；测试 29 行还明确要求没有异步结构的候选保留真实结果。可是按 122 行逐份执行清单，选择的六份 UI trace 都必须具有真实循环和动态 flow。若六份又要满足两个不同算法（120 行），会额外要求至少两个算法都能提供这些结构，或者迫使合法同步 trace 被判失败。严格执行者与按算法语义执行者会得出不同完成结论；若为过门而画静态箭头，还会直接违反既定真实性要求。这是文本的适用范围问题，不是确认某设备做不出第二个异步算法。
- **最小修改**：保留每后端六份、两个算法、cold/warm、program/occurrence 等覆盖要求；把逐份项拆为“每份必做”的打开/时间/来源/identity/范围/raw 导航，以及“适用样本必做”的循环与动态 flow。冻结 UI 覆盖表，明确每后端至少一份真实异步 trace 必须逐项验证 flow、generation 与目标时钟；非异步样本明确核验没有伪 flow，非循环样本核验实际区域结构。没有应有 flow 的异步样本仍失败，不能借 N/A 逃避三后端异步门槛。
- **建议验证**：用一份合法同步非循环真 trace 和一份合法循环异步真 trace 对照该表；前者不得被要求造 flow，后者缺 edge/循环或 clock 证据必须拒绝。

### R3-m01 — minor：真实 UI 的“本机”地点与服务器 Docker 约束冲突

- **位置**：`Profiler/docs/timeline_testing.md:120` 对照该文件 14、105 行及 `integration/plans/timeline/goal_prompt.md:94`。
- **触发**：执行者依 120 行把三个异步案例拿到工作机浏览器验收，或因不准工作机 browser 而认为 UI 门无法执行。
- **证据与影响**：14 行把浏览器纳入服务器 Docker，105 行再次限定现有 Docker；120 行却要求“分别在本机真实 Perfetto UI 打开”。“本机”没有定义成对应服务器容器，会造成无必要的权限/环境争议，也可能产生与执行合同不一致的验收收据。
- **最小修改**：将 120 行改为“分别在对应服务器已有 Docker 中的标准 Perfetto UI 打开”，与合同保持一致；交付后普通用户在自己浏览器打开产物另当别论。
- **建议验证**：UI 收据记录服务器/容器、浏览器与 UI 版本、trace SHA；无须为此改产品。

## 可移植性与三后端验证是否成立

### 现有三种实现足以检验什么

三条实际路径有不同的关键约束，能有效检验本轮接口，而不是三次换名字的相同实现：

| 路径 | 本次静态所见 | 能检验的公共边界 | 尚不能据此声称的能力 |
| --- | --- | --- | --- |
| NVIDIA | `observations_nvidia.py:132–147,227–234` 保留 SM-local、无 ns 换算的时钟；`340–373` 仍区分显式 scope 与所需自动编译接入 | 自动意图与实际 observer/program 的分离、原始配对、旧格式兼容、全局 timer 新证据的接入 | 普通无注解 kernel 的新时间线、目标 global timer 可比性、真实 async group 完成均未由这些源码证明 |
| Enflame | `Debugger/lib/Instrumentation/Passes.cpp:3805–3869` 真正调用 SDK `_ZN4tops12global_timerEv` 并声明 ticks；`integration/patches/enflame/flagtree-source.patch:9–33` 限定实际编译架构 `gcu300`、保存库 SHA 并显式标记频率未验证 | LLVM/SDK 特殊 clock carrier、与 NVIDIA 不同的主体模型、不同物理记录/解码与统一单位证明 | timer 名称不证明频率、epoch 或 async；C200 设备名称和 gcu300 编译目标应按实际清单绑定，不从品牌推能力 |
| Ascend | `observations_ascend.py:91–98,205–255` 保留 actor-local 记录和原始语义；`ascend_clock.py:77–90,120–144` 要求 same-call/packet/counter-domain 证据后才标 shared | actor 发布/对齐、晚期 manifest、源→SDK→实际对象、局部频率与共享 epoch 的分离 | 现有函数能验证声明与收据，不代表本轮所有目标 actor 已取得共享 epoch 或动态生产消费证据 |

设计 146、158、162–168 行允许晚期 fusion/split、后端不同物理 ABI 和多种异步 group 语义；这正是三后端共同验证所需要的边界。P03–P08 也让真实 producer 数据走同一公共身份/依赖/导出路径，验证思路成立。

P07 用真实样本证明每个后端实际机制，用 CPU fixtures 补批量/部分 wait/多消费者合同，是合理范围。不能要求三种硬件各自拥有全部机制，也不能把 fixtures 当作该设备实现了这些机制。文档 146 行与 136、151 行已经明确这一点。

两个有来源的 submit/wait **语义泳道**可以满足既定异步案例边界，不必额外发明第二个硬件引擎或强求 engine busy。对应 edge 仍必须来自原有合法 async 与实际 generation 记录；同一 observer 的合法共同本地时钟也可以支持该例子，不应为了“跨主体”外观强造不同物理 actor。真正跨 observer/域比较则另证 epoch。

### 对新芯片成本的实际判断

当前方案降低的是公共消费者的重复开发风险，尚无计时或移植工期证据。P09 的逐后端 diff、公共变动理由、安装链与回归，比代码行数或一个 adapter 类更有证明力。不能把后端新增的 compiler/SDK patch 隐藏到“通用层之外”来宣传零成本；适配清单需要包含这些依赖。

“公共消费者不添加逐厂商业务分支”应解释为消费相同的明确语义合同；允许依据公共能力/事件类型作通用处理，也允许有证据地扩展新合同版本。不得把新语义塞进任意属性然后宣称 exporter 完全通用。设计 182、186 行和 P08/P09 已给出这种正确取舍，没有必要再搭第四芯片或庞大插件框架。

## Verification gaps：需在明确检查点关闭，未算 confirmed defect

### R3-V01 — 三后端核心计时/异步闭环尚未证明，P01 是必要决策门

- **位置**：设计 100–108、114–116、124–128、188–192 行；测试 P01/P07；合同 81 行。
- **现有证据边界**：上表源码证明存在可复用的局部原语、manifest 或校验逻辑，没有证明本轮实际 timer 单位、两个源区间、动态 async、目标可比时钟和标准 Trace Processor 的整条新链。
- **最小关闭材料**：每后端一个普通真实数学纵向样本，绑定 target/compiler/SDK、实际 getter 指令与编译对象 SHA、单位/误差/epoch 证据、两个源区域正区间、原有 async 的至少两轮 generation、raw 发布/解码及 Trace Processor 输出。可以使用两个有依据的语义泳道；如比较不同 actor，须给对应对齐证据。完整图以前不宣称重叠或引擎 busy。
- **判断**：目前不能给出“必可行”或“硬件不可能”的证据票。尤其 GCU 频率/异步和 Ascend 目标 epoch，属于先核事实的高风险项，不应拖到 72 次资格矩阵之后。

### R3-V02 — 职责合同足够开始 P01，尚不足以审核“接口已经冻结”

- **位置**：设计 74–82、148–176、182 行；测试 P04–P08、153 行。
- **缺口**：字段现在是建议列表，能力与注册为职责描述；尚无规范化事件/manifest/group/clock 的必填、可空、基数、引用完整性与版本行为。单个 `producer_token/consumer_token` 字段不是 166 行多提交/部分 wait/多消费者集合关系的完整编码。P08 要求 core schema/未知字段策略固定，但当前没有给出最终策略。
- **静态对照**：旧 `observations.py:165–210` 复制任意 dict，再检查有限字段；旧 clock 入口 `120–146` 接受证据声明，转换 `187–196` 直接使用数值 period。它们可作为旧格式兼容入口，不能直接充当本轮“严格扩展/整数有理数/证据绑定”合同。`_backends.py:7–10,41–50` 则只是旧 capture/counter 别名路由，不是新 timeline 注册边界。
- **最小关闭材料**：在第一条真实路径之后、第二/第三适配前，冻结一份小的可定位公共合同与示例，至少定义能力三态和目标匹配、观测意图、晚期 manifest、解码 batch、clock proof、operation/group/wait 覆盖集合及 edge 引用。规定 core 字段不能覆写；扩展角色/属性有命名空间和类型，未知可展示属性保持不透明，未知或未支持的时间/依赖语义不得绕过 validator 获得 verified。新增必需语义通过明确 schema 版本/能力拒绝或 partial 处理。
- **验证**：三后端真实 decoder 输出走同一套校验器；角色扩展、错类型、核心覆写、悬空 group 引用、未知必需语义分别有明确结果。无需提前冻结设备统一 struct，也无需另造大型插件系统。

### R3-V03 — 两阶段能力细化与资格身份需要分开保存

- **位置**：设计 172–176 行；测试 39–44 行、P02/P10；合同 38、81 行。
- **缺口**：允许普通目标预检和实际编译后细化能力是必要的，但尚无产物结构区分“事前普通输入资格”“目标级已验证机制”“本次 instrumented plan/outcome”。若把它们都写进可变的 capability 对象，编译后发现失败时容易无意改写资格分母，或把某个样本成功误推广到同品牌全部配置。
- **最小关闭材料**：资格前保存不可改写的 ordinary eligibility 清单；本次 manifest/采集结果另写并引用该清单。新编译发现的未知/不支持/错误只决定明确拒绝或 partial，不能把原 eligible 失败删除。目标/SDK/plugin/timer/rule/ABI 的实际依赖身份绑定同一版本，并覆盖内存与磁盘 cache。
- **验证**：对普通可运行、插桩失败的冻结输入保留失败；换 SDK/plugin/target 后不复用旧能力或旧 cache；早拒绝后下一合法调用可用。这也符合脚本每次只执行请求次数的要求，无需 profile 内预跑。

### R3-V04 — 通用 exporter 的可追溯映射与真实工具规则仍需冻结

- **位置**：设计 196–211 行；测试 54、105–116、124–130 行、P08。
- **现有证据边界**：旧 `_report.py:518–585` 是按现有 activity lanes 导出 Chrome JSON，用已有 API/device correlation 画 flow；不能把它当作已经存在的内部 TrackEvent protobuf/async 导出实现。新 trace 的 track/flow 规则与 SQL 在文档中仍是意图，尚无实际工具结果。
- **最小关闭材料**：固定实际 UI/Trace Processor/protobuf 版本，规定 canonical event→track/slice/instant/flow 的映射、ns 舍入与误差、clock 分区、重叠事件处理，以及不靠名称 join 的 event/edge/proof IDs。每条 slice 或 checkpoint 能回查原 raw/SDK event；begin/end 分离或 group 多成员时保留全部证据引用，而非只保一个方便展示的代表记录。
- **验证**：三后端都走同一 exporter 与 SQL 语义检查；从 raw 独立核对转换、端点、ID 集合、loss 与 importer stats；循环、部分事件和动态 flow 在实际 UI 中可选择并解释。只对规范化 JSON 和导出文件相互一致作检查，会遗漏二者共享的上游错误，不能代替 raw/编译证据对照。

### R3-V05 — 源码“可点开”与源→实际边界证明不能混为一层

- **位置**：设计 68、81、146、207–211 行；测试 52–54 行、P03。
- **现有证据边界**：`source_view.py:29–68,122–159` 已有 snapshot digest、行范围与导航保护，值得复用；其中 file snapshot 的 `compiled_text_alignment` 仍明确为 `not_independently_verified`，位置在范围内不等于这个 late marker 就来自该逻辑区域。`fine_grained.py:125–143,165–179` 的源候选/located 展示也不能替代新 manifest 证明。
- **最小关闭材料**：使事件引用 manifest 中可核验的 source region→实际 marker/对象映射，并引用 bundle 内 snapshot/hash；fusion/split 的多来源、已消除区域和歧义分别保留。UI 展示来源状态，不把“能找到一行”自动升级成精确执行归属。
- **验证**：除正常源导航外，核错 snapshot/hash、错 region/marker 引用、优化消除、fusion 多来源和旧路径缺失；不应凭当前工作机同名文件恢复成 verified。该项没有要求每个机器指令都唯一对应源码行。

## 实现依赖与排期建议

这不是“现有 timestamp 加一个 exporter”的工程。最短关键路径是：真实 timer/作用域与原有 async 语义可访问 → 合法通用插桩及有界发布 → 动态 token/generation → 可比时间与规范化合同 → Perfetto/SQL/UI。公共 CLI 和漂亮轨道不能消除前面的依赖。

建议保留现有阶段门，具体执行时这样安排：

1. 修订 R3-M01/R3-m01；准备三后端普通 baseline 和明确目标身份。
2. 选择一个后端打通最小完整链，同时尽早核另外两个后端 timer/async 的关键未知，尽早暴露 SDK 或时钟硬依赖。无需等第一后端图完全美化后才发现第三条路缺原语。
3. 用首条真实链冻结小版本公共合同；第二、第三接入记录公共新增概念及对已接入实现的回归。三份 P01 各自满足才进入对应最终资格。
4. 才扩大 D01–D06、故障/并发/cache/旧数据回归，冻结资格版本、SQL/UI 覆盖与预算，再做独立六数学。正常、overflow、未知机制分别计入原先规定的分母与状态。
5. 最后做冻结版本的三位独立代码审阅、必要修复及受影响复核，不把本次设计评审当作该终审替代。

在 P01 前给精确人日估计缺乏证据。P01 后可以按真实未闭合项估计：compiler/SDK 改动必须真构建安装，cache/ABI/source-chain 改动会牵动旧数据回归；独立资格失败触发新数学补充，最终 timer/native 改动也会牵动受影响设备复验。这些依赖在合同中已有依据，不能靠重复导出旧数据绕过。

## Optional improvements

- **O01**：为三后端各放一张 P01 状态表，逐项写“已验证/设计假设/硬阻碍”、证据文件和下一步。它有助于工程排期，不应把表里的假设当成支持声明。
- **O02**：P09 除 diff 分类外，记录公共调用链与依赖箭头，检查 exporter/validator 不 import 设备 SDK 或解释厂商 raw 布局。该审计可证明关注点确实集中在后端，不必设置 LOC 指标。

## 阅读与未覆盖范围

完整阅读三份主文档。必要静态源码阅读覆盖 `_backends.py`、`observations.py` 的请求/时钟/事件合同、`observations_nvidia.py` 的时钟/计划、`observations_ascend.py` 的解码输出、Enflame 实际 SDK timer lowering 与公开 compiler patch、`ascend_clock.py` 的 shared-epoch 接入、`cann_source_clock.py` 的来源检查、`profile.py` 的旧自动请求路径、`_report.py` 的旧 trace exporter，以及 `execution_enflame.py`、`fine_grained.py`、`source_view.py` 的相关静态/源码映射。其余大文件仅通过相关符号检索定位，不声称全仓代码审计。

未查外部 SDK/PTX/Perfetto 文档的当前在线内容，未验证设备实际 IR/ISA、频率、发布可见性或跨 actor epoch，未执行独立数学、SQL、UI、安装与缓存试验。上述事项必须由授权后的真实工程证据关闭；本报告没有虚构任何实验通过结果。
