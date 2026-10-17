# R2 M1 有限复核

结论：**M1 已关闭**。修订清楚区分合法逻辑组数据与完整异步资格，未发现本次两处修订引入新矛盾。整体仍为初审的“有条件可实施”；这次文档复核不证明设备、时钟、owner 或异步机制已通过。

## 冻结输入

核 `FOLLOWUP_INPUT.json`，三个文件实际 SHA-256 全部匹配：

| 输入 | SHA-256 |
| --- | --- |
| `Profiler/docs/timeline_design.md` | `dc26b5fb008bea5e608bb13b19ee08da1037b7fa02a38a4dcef041bb8e3c79f1` |
| `Profiler/docs/timeline_testing.md` | `a55fe77d2ede2671414c7f3127f521d388a29347a1a502251ecc350178400678` |
| `integration/plans/timeline/goal_prompt.md` | `51db449f2898ad695f8557a3d83459cf476c57cec27198743ba481193e12a054` |

设计与执行合同的 SHA 与初审相同。有限复核对象是 testing P07 输入行和 §8.4“身份与证据层次”行，并对照初审已读的 §5、设计 §7/§8.9 与执行合同资格边界。

## 修正判定

P07 现在明确真实两轮 buffer/flag 复用是每后端完整资格必需，只有逻辑 group、unknown physical buffer 的结果不能单独满足该门。§8.4 又明确 group-only 不能豁免，当前样本不足则另取有来源的真实复用样本，或者保留未通过状态。

这保留了设计 §7 的正确性：逻辑组关系可以在不知道物理 buffer 时诚实记录；没有因此强迫实现伪造 buffer/iteration/generation。与此同时，它也保留了 testing §5/P07 原有真实复用验收。逻辑组事实、真实复用资格、时间箭头资格三层不再被条件句混淆。

未新增 confirmed blocker/major/minor。首次报告 `R2-runtime.md` 保留；其中 timer/epoch、真实机制闭合、发布可见性及 owner 的设备验证条件未被此次措辞修订解除。

## 范围

读取 followup 清单、计算三 SHA、定向阅读两处修订与相邻上下文，查看 testing 工作区 diff 辅助定位；未读取 peer/旧评审，未运行产品/import/测试/构建/远程访问。只新增本报告，未修改初审或产品。
