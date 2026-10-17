# 第七轮：时间线适配边界的独立设计评审

本轮只更新设计、验收及合同引用，没有修改产品代码、连接服务器或运行设备实验。用户要求先明确可复用边界，再评判设计合理性和实际可行性。已有实现、设备数据和未提交工程证据保留原状。

## 审阅入口

- [技术设计 §8.12](../../../../../Profiler/docs/timeline_design.md#812-本次实施合同独立适配部件与公共数据交接)：按 compiler、transport、decoder、clock、mechanism 的变化原因拆分，定义最低交接产物；物理 ABI 与公共 schema 独立，允许不同执行模型。
- [验收 §8.7](../../../../../Profiler/docs/timeline_testing.md#87-独立部件与默认入口的可执行验收)：两种记录顺序与计数单位、公开默认采集、失败恢复、固定配置的扰动对照及分层资格；复用既有 P/E，不增加独立资格矩阵。

三席均使用独立上下文，不读取彼此初审。请求配置均为 GPT-6.1-Sol / xhigh；配置记录见 [REQUEST.json](REQUEST.json)，不另行推断服务端模型身份。本轮是设计审查，不能替代最终实现后的三名额外代码 reviewer。

| 评审侧重 | 独立初审 | 有限复核 |
| --- | --- | --- |
| 编译边界与插桩扰动 | [R1-compiler.md](R1-compiler.md) | [R1-followup.md](R1-followup.md) |
| 运行时、发布与时钟 | [R2-runtime.md](R2-runtime.md) | [R2-followup.md](R2-followup.md) |
| 适配、公共消费与 Perfetto | [R3-portability.md](R3-portability.md) | [R3-followup.md](R3-followup.md) |

初审输入身份见 [INPUT.json](INPUT.json)，原稿可由 source_head 和 [INITIAL_DOCS.patch](INITIAL_DOCS.patch) 重建（使用 `git apply --unidiff-zero`）；修订后两文档身份见 [FOLLOWUP_INPUT.json](FOLLOWUP_INPUT.json)。初审保持原文，后续意见单独记录。

## 汇总与修订

三席初审一致认为整体设计合理，没有必须推翻架构的设计阻断，可以继续最小纵向实现；三后端完整设备可行性仍未证明。初审有重合项，合并后六项修订如下。

| 问题 | 文档修订与对应验收 |
| --- | --- |
| decoder 与 clock provider 的边界有两种读法（编译 F1、适配 F1） | §8.9 将 decode_capture 明确为编排动作；物理解码不探测设备或造 proof。固定 raw/manifest 替换 proof 不改变端点与身份 |
| 扰动对照混入调度变量（编译 F2） | ordinary/稀疏/较密固定配置、输入、grid、数学及机制；C2 每个调度变体分别对照，预登记关键关系 |
| 合法回绕与当前 raw reader 的限制未接合（运行时 R1） | 明确 schema 1/2 无回绕限制并保原件；需要时版本化 modulo 合同与独立窗口证明。加入唯一4 ticks正例和整圈/reset负例，必需样本未支持不能放行 |
| 设备资源释放与导出成功耦合（运行时 R2） | §8.7 分离 owner 和派生状态；完成、D2H和原件安全保存后可回收。双 owner 首个解码失败仍尝试保存后者，不放开潜在写者 |
| 下一请求恢复的前提不清（运行时 R3） | 引用安全清理后的新 session 边界，不要求仍有隔离资源的失败 session 原地恢复 |
| pair 提交顺序与 Perfetto 投影未贯通（适配 F2） | canonical 不排序修复；独立导出投影可遵守协议而不改端点/配对/原 sequence。嵌套 fixture 经过公共 exporter 与真实 Trace Processor，不能代替设备/UI正例 |

## 结论范围和下一步

后续新增型号可按独立部件的相容条件复用实现，公共身份、完整性、时间运算和展示有明确复用路径；尚不能声称新增芯片已经成本很低。新工具链或不同执行模型仍可能需要晚期 pass、隐藏 ABI、发布机制、clock 和异步规则的真实工程工作。

下一步仍是三个后端各自的小规模公开纵向链：普通 runtime 循环的最终边界/动态次数，真实首末 program 与安全发布，本地域时间尺度，然后真实异步与两轮物理复用、所需时钟可比性及共同 Perfetto SQL。NVIDIA 的展开/流水扰动、GCU 的默认 producer/尺度/异步、Ascend 的新动态 logger/发布仍需设备证据。接口、CPU fixture 或旧 raw 重读不填这些门为通过。

本轮不授予任何后端 P01、标准 UI 或最终交付资格；完整合同和后续独立数学、最终代码审查要求保持不变。

三个原评审均已完成有限复核：上述问题在文档层面关闭，无新增明显矛盾；结论不扩展到产品代码或设备通过。
