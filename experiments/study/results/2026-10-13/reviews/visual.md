# 独立审阅三：图可读性与证据链

**范围与结论。** 独立读取实验说明、study正文、结果CSV/JSON、五张PNG及绘图参数；未读取其他审阅意见。数据可支持study的三个方法要求，但最终印刷可读性和图的自足性尚未达标，建议修改后作为投稿图。这是局部形成性审阅，不是完整论文或系统准确性验收。

**核对结果。** 216通过用例；原生CSV含108组×15条=1620条。nested共30个区域比较，GCU outer实际为0.4665–0.4960，inner为0.9889–1.0032；CUDA outer为0.9896–1、inner为0.98–1，Ascend均为1。说明中的“0.47–0.51”应改约0.47–0.50。tile16→64无TCU捕获中位数与图一致：GEMM 1615.859→27.119µs，融合1650.585→30.031µs。TCU为4×21次调用；CSV的336行是每次4类指标，JSON确实保留device/die/SIP实例。

## 必须解决

1. **最终字体太小，endpoint最严重。** `plot_deep.py`把endpoint画成9.6英寸宽、9pt正文，`03-study.tex`却用单栏3.335英寸嵌入，缩后约3.1pt。其他10.6–11英寸宽图缩至7英寸双栏后约5.7–5.9pt，8pt脚注更小。原尺寸PNG清晰不能代表印刷可读。按最终栏宽重画，保证文字至少约8pt；endpoint改单栏上下两面板或双栏。精简两行suptitle，把限制放caption。

2. **endpoint图掩盖核心控制。** 线性纵轴到1500/15000，零工作/小工作量几乎不可辨；单栏后两曲线似乎相同。CSV中Ascend 16次为8→25 ticks、64次48→96；GCU零工作0→240 units、16次300→585，是更有解释力的控制。增加小工作量放大图，或画“有结束屏障−无结束屏障”的原生单位差值，并保留原始读数/范围；说明横轴symlog。caption补每条件样本数、点=中位数及范围含义。差值不能分离屏障成本与完成等待。

3. **breadth配置无法单独解码。** `small/large/tail`和`v0/v1`要求读者查artifact；圆/方对应v0/v1缺图例。补尺寸与各算子配置的小表或图注，注明实心标记=中位数、淡点=15条观测、bar=min–max和对数纵轴。README指出GCU GEMM stages1/2对应最终二进制相同；应说明配置标签不是跨后端等价干预，不能以相近点证明“不响应调参”。增加明确后端图例，降低红绿颜色依赖。

4. **native-detail只画调用聚合，丰富实例信息目前在数据中。** (b)(c)是invocation aggregate，并未显示per-SIP。保留“TCU已有丰富指标、exporter保留”的表述；若图要支撑instance preservation，加device→capture-local invocation→die/SIP结构例子或per-SIP分布。明确黑横线=21次中位数、淡点=含warmup的21次调用、(a)bar=min–max。`GEMM + GELU`统一为实际`GEMM+bias+GELU`。

5. **native百分比分母仍不清楚。** “keep SDK denominators”不是定义。图注写清1D/MSF的SDK定义/作用域，或明确正文尚未展开并指向保存的定义；不要推断定义。较快tile64反而1D效率更低，可用一句解释时间变短不意味着每个native指标都上升，不能化为统一利用率排名。两类百分比不能相加或相减成等待占比；MSF不是已证明的矩阵引擎。两轮独立捕获支持配置级对应，不能同调用因果配对。

## 可用但需澄清

- **fused-decomposition最接近可用。** 共同源、编译结构、原生record范围清楚区分；没有虚构时间线，限制正确。为陌生读者解释AIC/AIV、workspace(gm)、MIX_AIC，区分依赖箭头与映射箭头。Ascend底部record从AIC/AIV组合括号引出，避免像仅记录AIV。这里只证明结构/范围不同，不证明重叠、遗漏时间或归属错误。
- **nested是最强经验图。** GCU outer约一半、inner近1，移动内层位置后仍存在，支持nesting协议适配。补括号示意或伪代码展示q/inner128/128−q及both、outer-only、inner-only三个capture；仅API名称不足以重建请求。caption明确ratio=两个独立capture中位数之比，并非逐样本配对。参照使用相同厂商原语，不是绝对物理真值。保留15样本和扰动限制；接近1不等于普遍准确性保证。

**故事判定。** “六probe覆盖→源区域静态映射→同一嵌套请求的后果→位置/端点/tiling控制→映射、协议、native detail要求”整体成立。Case 1是结构案例，Case 2是实际协议反例，建议明示证据类型不同。时长分布仅动机；endpoint说明端点约定改变读数；tile控制证明性能与native family指标随配置改变。图不支持未测内部busy/wait、跨核生命周期、实例归属误差率、方法准确性或优化因果性。结尾应保持设计要求层级，不能写成新机制已验证。

## 修改后复核（仅更新PNG与study正文）

**结论：主要障碍已解决，尚有少量图注和排版遗漏。** endpoint已改双栏、标出零工作0/0与0/240，原先约3pt单栏字体问题消除；其余图字体明显扩大。breadth定义圆/方并在caption列出全部形状及配置，正文明确GCU/V100 stages1/2最终binary相同，配置比较不会再被误读为等价干预。Case 1与独立计时probe的关系已写清。nested保留CUDA尖峰且caption如实定义范围分子/参照中位数，避免把中位数接近1写成每次调用均接近1。TCU黑横线、invocation aggregate与artifact保留per-SIP的区别已说明；仍未扩充实例图可以接受，不应强制以更多面板增加复杂度。

**仍建议修正：**

1. 更新nested和endpoint的长纵轴标题顶端已进入两行suptitle的空间，尤其endpoint右侧`SDK counter units (unconverted)`与第二行标题视觉交叠。这是放大字体后的新障碍。缩短纵轴标题（`Nested / single-region`、`SDK counter units`），把reference/未换算限制放caption，或增高画布/标题留白；勿靠再次减小字体解决。
2. endpoint caption仍未说明点为中位数、每条件样本数，且未说明横轴symlog。小工作量控制仅靠零工作注释得到改善，16/64次的差异仍被大纵轴压缩；可在caption给出一组8→25、48→96的读数，或放大局部，不必再开完整新图。nested caption建议补“logarithmic ratio axis”。
3. breadth实心较大标记为中位数的含义仍未明示；TCU(a)的bar=min–max也尚未写清。native-detail(a)图例仍为`GEMM + GELU`，与真实融合`GEMM+bias+GELU`不一致，caption的“Left:15 native intervals”也未明确该面板点为中位数。
4. TCU caption已解释1D为M/V-slot instruction cycles / total cycles；MSF仍仅称“SDK M-slot instruction-family definition”，对百分比分母依旧不完全自足。可引用具体artifact定义，不应补未经验证的公式。fused图的AIC/AIV缩写解释及组合范围括号仍属可选增强；现有“aggregate”正文限制已避免重大过度解释。

修订后的主要证据边界保持正确，没有新增内部时间线或busy/wait因果归因。完成第1项排版和第2–3项简短图注后，图组可用于呈现这份探索性study；不会因此升级为新机制准确性或系统贡献验收。
