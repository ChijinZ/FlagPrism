# 第四轮设计合理性与可行性独立评审（T014）

本轮响应用户关于未来新增芯片适配成本的要求，更新设计 §8.10、验收 §8.5，修正过时状态说明，并同步执行合同。只做文档、源码静态核对和文档审计，未改产品或论文，未连接服务器、构建或运行产品/设备/Perfetto 测试。完整工程目标仍未完成。

## 输入与独立性

- [请求、三个 agent、初审输入 SHA](REQUEST.json)。三个 fresh-context reviewer 均请求 `gpt-6.1-sol` / `xhigh` / `fork_turns=none`，创建工具接受配置；实际 serving 型号和推理配置未暴露，记为未知。
- 每位完整阅读同一设计、验收、合同与 runtime/events 文档，可静态核源码；不阅读 peer 报告。三位均评价总体设计，分别重点看编译、运行时、适配与展示。
- [最终有限复核输入](FOLLOWUP_INPUT.json) 保留最终 SHA；初审不覆写。设计评审不能代替最终三个额外代码走查，更不能填设备 P01、资格或 SQL/UI 通过。

| 席位 | 初审 | 结论 | 修订复核 |
| --- | --- | --- | --- |
| R1 编译、源执行映射 | [报告](R1-compiler.md) | 有条件合理；无 confirmed blocker/major | [有限复核](R1-followup.md) |
| R2 时钟、发布、异步与 owner | [报告](R2-runtime.md) | 有条件合理；无 confirmed blocker/major | [有限复核](R2-followup.md) |
| R3 适配边界、Perfetto 与验收 | [报告](R3-portability.md) | 合理（设计层面）；无 confirmed blocker/major | [有限复核](R3-followup.md) |

## 确认问题及处置

| 问题 | 影响及修订 |
| --- | --- |
| 三席均指出：合同仍称 timeline 入口未实现（minor） | 改为已有 NVIDIA raw 的 `partial_clock_unverified` 公开入口，ns/Perfetto 与另两后端 producer 未完成；根合同和跟踪快照同字节同步。顺带更新历史基线措辞及设计/验收章节引用 |
| R2/R3 指出：设计开头将当前边界指向历史 §8.8（minor） | 改指当前 runtime/events 文档，明确 §8.8 为历史原语检查点，保留历史证据，不把旧 packed 位宽状态混作最新实现 |

修改没有降低三后端、真实时间、每后端异步两轮复用、P01、独立数学、Trace Processor/UI、最终代码走查的门槛。原始风险不靠多数表决豁免。

## 仍须由实现证明的可行性条件

1. 每条工具链的最终计时边界：有副作用的 timer/logger 不足以证明纯计算不会跨界，须有实际最终对象和通用约束。
2. 每个真实目标的 getter、比例/误差/窗口及所需 epoch 关系；时钟算术和 timer 名字不能替代物理证据。
3. Ascend/GCU 的实际写者、布局、发布可见性和完整 owner 故障恢复；公共 owner 不得要求它们伪造 CUDA 身份。
4. 真实异步机制状态闭合、参与者范围及至少两轮 buffer/flag 代际；逻辑组、iteration 和物理复用分开。
5. 三后端真实数据通过共同验证/导出和实际 Perfetto，不能以 fixture 或空 adapter 宣称适配完成。

可以按 A/B/C/D 分段推进；三后端真实接入验证公共边界，未来新芯片仍需目标特有部件和设备验证。无需为本轮新增第四芯片、另造完整 IR 或预搭插件框架，也不承诺新芯片仅改配置或几天可完成。

## 最终复核状态

三位均已完成最终有限复核，实际文档 SHA 与 FOLLOWUP_INPUT 一致；确认各自 minor 项已关闭，无新增矛盾、门槛未降低，分别维持原设计结论。初审报告与初始 SHA 保留。以上仅关闭文档问题，所有未完成的设备、时钟、发布、异步、SQL/UI 和最终代码验收继续保持未通过/未验证。
