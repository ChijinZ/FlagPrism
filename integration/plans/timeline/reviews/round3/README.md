# 第三轮设计可行性评审与处置（T009）

本轮更新设计 §8.9、验收 §8.4，并同步执行合同引用。只做文档及源码只读核对，未运行产品测试、SSH/设备、Trace Processor 或 UI。三席为新的独立 context，同一份冻结输入，不读彼此或历史报告；使用继承默认模型，未请求模型覆盖，实际 serving 型号未暴露。这三份是设计评审，不能替代实现结束后三个指定 GPT-6.1-Sol/xhigh 的最终代码审阅。

- [初审输入 SHA](INPUT.json)、[请求与 agent 标识](REQUEST.json)、[修订后复核输入](FOLLOWUP_INPUT.json)。
- 编译/边界：[R1 初审](R1-compiler.md)、[有限复核](R1-followup.md)。
- 时钟/异步/运行时：[R2 初审](R2-runtime.md)、[有限复核](R2-followup.md)。
- 适配/交付/验收：[R3 初审](R3-portability.md)、[有限复核](R3-followup.md)。

## 结论与处置

三份初审均为“有条件可实施”，没有 confirmed blocker/major；R1 无必需修改，R2-M1 与 R3-MIN-01 指向同一资格措辞歧义。root 核实：允许物理 buffer 未知的逻辑组数据，本身不能豁免每后端两轮真实 buffer/flag 生命周期验收。

修正 testing P07 主条款及 §8.4：完整资格仍必须有真实两轮复用与代际证据；只有 group 关联的结果合法保留，但不能单独满足该门，须另取真实复用样本或保持未通过。没有编造 buffer/generation，也没有放宽原合同。初审和初始 SHA 保留，复核绑定 FOLLOWUP_INPUT 的最终文档。

三席均完成有限复核：最终三文档 SHA 与 FOLLOWUP_INPUT 一致；R2-M1/R3-MIN-01 已关闭，无新增确认问题，三席保持“有条件可实施”结论。最终机器边界、clock/epoch、发布与异步机制等真实验证条件仍未解除。

## 需要真实实证的条件

| 条件 | 实施检查点 |
| --- | --- |
| 计时边界在优化后保留，软件区间与实际语义对应 | P01/P03：依赖算术循环、load/compute/store、原 wait；最终 IR/ISA 与 raw 对照 |
| 紧凑 slot 与真实 program 分开，所有 logger 写者正确受控 | E02/P05/P10：不同 grid、未选 program、canary、旧 ABI 错配早拒绝 |
| 时钟尺度、epoch、误差及有效窗口可证明 | P01/P06/E09：真实 getter、独立尺度证据及跨主体所需时钟证明 |
| 动态异步机制闭合、复用不串代 | P07：最终状态变更覆盖、真实两轮复用、缺 commit/opaque 负例 |
| owner 安全发布/回收且导出保留语义 | E01/E03/E05/P08：已支持并发与阶段故障，真实 SQL/UI |

这些是条件和最小实验方向，不是通过记录。新增芯片仍需目标特有的编译、logger、clock 和机制适配；本轮只要求在三个现有后端形成可复用的小合同，不新增第四芯片、不承诺移植天数、不建设没有调用者的插件框架。
