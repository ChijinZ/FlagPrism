# R104：实际用户影响与可选结构分析的边界

按最新收紧指示，本报告停止扩展 vector/descriptor/order 实现方案，只完成已有只读审阅并分类影响。候选 HEAD 为 `9c14353a85c5a84ae7f76a3af8c82ef131277670`；本轮未修改产品、运行测试/import/SDK/设备/数学/TP/UI 或连接服务器，未读 peer。请求 GPT-6.1-Sol/xhigh，resolved 未暴露，记 unknown。

## 结论

**目前没有证据表明 q01/q02 的 opaque-type 或 q03/q04 的重复 candidate 导致采集、原始时间、Perfetto interval 或用户源码导航错误。它们首先是新增静态 structural checker 拒绝签认的范围限制，不应笼统称为核心 timeline 功能失败。** 不能仅因旧验收追求更强静态归属，就继续把类型/顺序求证扩成新的必做产品工作。

旧 q05 的实际 MMA 阶段漏选则与用户用途直接相关：看不到该计算阶段是观察覆盖缺口。R101 已用通用 selection intent 修复，并有新公开 q05、R102/R103 实际 dot/member/loop 记录正例；它与上述 checker 未证是不同类别。新证据不修改旧捕获或自动覆盖全部历史组合。

## 实际读取的 R104 结果

已独立核 `inventory-receipts-v2` 全 **8** 项 index 的 size/SHA，无不符。`inventory-v2` terminal **0 / 69.053125922 s**，96 registered/processed/recomputed，无 unavailable。实际为 **32 个 compiler/owner binary ID、28 个 final binary SHA**；worker 字段 `distinct_binaries=32` 是前者。`required_coverage_qualified=false`、`native_schedule_qualified=false` 和无 replay/SDK/device 的字段均保留。`96 recomputed` 只说明分析可运行，不是 required 结构已全部覆盖。

读取了该次 `calls.json` 和结构摘要，以及现有 q01 原 actor/index、当前附加分析与导出调用点。下表区分已观察事实与用户影响，不把未运行 UI 当新 UI 验证。

| 项目 | 实际事实 | 本轮分类及用户影响 |
| --- | --- | --- |
| q01 repeated body | source14/17 因 opaque type 未获 structural 证书；实际记录完整、每个区域两 observer 各三条 interval | **附加静态归属分析未证。** 不是缺少时间记录或循环重复 |
| q02 opaque body | R104 同样给出 opaque-type reason，原 capture 可重算 | **当前 checker 能力限制。** 不能在尚未定位每个具体 type 前认定用户采集错误 |
| q03/q04 flags/barrier | 不同实际候选具有同 signature，当前唯一性策略保守拒绝 | **附加静态匹配歧义。** 还没有实际错误绑定，更没有已观察的时间线失真 |
| 旧 q05 未观察 MMA | 原选区没有 dot43，MMA 在已选 fragment 之外 | **实际观察功能覆盖缺口。** 与用户能否看到计算阶段直接相关；通用修法及新 q05 已有定向正例 |
| q06 checked repeated | 现规则和实际记录已有 repeated checked 结果 | 可复用的局部正例，不外推完整 required 覆盖 |

## q01 必须纠正：当前具体目标是 struct projection，不是 vector

R104 首 q01 失败区域为 source14 / site18 和 source17 / site19。已保留的同链 `q01-0.original.json` 输入 SHA 为 `593cd907a8fee6e0a2005b1960784b1dc73311b139040074542a1c8ee6714af1`。对应原 fragment 分别10/11条操作，首个 opaque 操作是 `extractvalue` id624 / id639，其 operand 为 **kind16 的 struct**，后续也有此类 projection。原 `.ll` 中没有 vector `<...>` 类型。

因此先前“补 vector 就能解除 q01 body 缺口”的分类不准确。仅扩 fixed/scalable vector type 并没有解决这个实际拒签原因。这个纠正也**不意味着必须接着实施通用 aggregate/descriptor 解释器**。

对 `q01-s0-c0-cold`，site18 仍有6个实际 interval、5个正值（两 observer 各3条），site19 有6个 interval、6个正值（两 observer 各3条），capture 完整。当前事实支持“时间和 source-linked observer bracket 已存在，静态操作结构证书尚未给出”；不支持“q01 无法采内部时间”或“extractvalue 导致 Perfetto 错图”。源码导航身份也没有因 checker 返回 unverified 被换掉。

q03-s0-c0-cold 的两个未证区域各有2个正 interval；q04-s0-c0-cold 的对应未证区域也有2个正 interval，capture 均完整。其 candidate2 是分析歧义，不是数据丢失证据。

## 现产品为何不会因这类拒签删掉时间线

`timeline_ascend.py` 先持久化 canonical batch，再把 `inspect_capture_fragments` 的结果作为 `source_fragment_paths` 附加信息保存，随后走原 clock/counter 导出。`timeline_ascend_fragment_store.py:inspect_capture_fragments` 明确是 optional analysis，失败保 raw；`_attach_observations` 给**所有**报告区域附上已有 event/observer 的统计，并不按 checked 状态过滤或改写 canonical intervals。`timeline_ascend_offline.py:85` 也把分析不可用记录为附加状态，不用它替代原解码结果。

本轮静态调用链与实际 raw 盘点没有显示：因为 struct 或 candidate2 拒签而删除原 slice、改变其 tick、伪造重复、换 source ID 或让正常导出失效。未在本轮重开 Perfetto；这里判断的是这类拒签的产品作用范围，不另认证所有 UI 行为。

如果将来某个界面在这些 unknown 上仍宣称“完整 source op 成本”或“唯一原操作身份”，那才是具体误授问题，应修该声明。当前文档/报告保 observer bracket、部分 membership、value/native qualification false，不能把更强证书缺失本身当成已发生的 UI 误导。

## 原先候选方案现在如何归类

有界 vector type、有限 literal 编码以及 corridor 中有序结构 witness，原则上可以增强静态报告；它们不是已确认的采集修复。尤其“unique earliest”最多给规范选择的有序结构 witness，不自动证明唯一原操作身份。相同 opcode/type 但不同 literal 不应被新证书说成已知相等；保 opaque 是诚实且可用的结果。这些都是**将来若选择增强该证书时的正确性边界**，不是本轮继续实现或新增验收矩阵的指令。

依据最新范围，本席不再列新的 descriptor、常量表达式、SSA、ISA、logger alias 或全路径求解工作，也不要求将所有 unknown 改成 checked。已有 R103 正常安装、实际 raw、部分结构报告仍可按其明确范围交付。旧验收中的更强归属证据如未满足应如实保留，不用“whole 仍 open”笼统替代实际用户影响说明。

本轮无新增 confirmed runtime/导出代码缺陷；真实旧 q05 观察缺口及其定向修复历史保留。是否继续可选结构分析，应由产品准备向用户声明的语义和用户价值决定，而不是由自建 checker 尚未签认的类型数量驱动。
