# Round 3 R1 有限复核：真实复用资格门

## 结论

**本次澄清与原合同一致，未引入新的设计矛盾。初审“有条件可实施”结论保持。** 完整资格每后端仍必须具备真实两轮 buffer/flag 复用及代际证据；只有逻辑 group、物理 buffer 未知的结果可以保留为有限数据，不能单独豁免或满足该门。

本次没有新增 confirmed blocker、major 或 minor；也没有形成设备通过结论。初审报告保持原件，不覆写。

## 冻结输入核对

实际文件 SHA256 与 `round3/FOLLOWUP_INPUT.json` 三项均一致：

| 文件 | SHA256 |
| --- | --- |
| `Profiler/docs/timeline_design.md` | `dc26b5fb008bea5e608bb13b19ee08da1037b7fa02a38a4dcef041bb8e3c79f1` |
| `Profiler/docs/timeline_testing.md` | `a55fe77d2ede2671414c7f3127f521d388a29347a1a502251ecc350178400678` |
| `integration/plans/timeline/goal_prompt.md` | `51db449f2898ad695f8557a3d83459cf476c57cec27198743ba481193e12a054` |

design 和 goal 的 SHA 与初审输入相同；本次只对 testing 的指定两处文字及必要上下文作有限复核。

## 一致性判定

1. 测试 P07 现在直接写明“两轮真实 buffer/flag 复用”为完整资格必需，group-only/unknown physical buffer 不单独满足。它重申原 testing §5 第5项和原 P07 的每后端真实复用要求，未新增独立资格数学数量，也未将 fixture 变为设备正例。
2. 测试 §8.4 的 P07/P08 身份行现在将“保留逻辑 group 事实”和“完整异步资格”明确分开。当前样本无法证明真实复用时，另取有来源的真实样本，或保持该门未通过；这与初审 A2 所述需另有真实复用路径的解释一致。
3. design §7 允许逻辑 commit-group 关联而不编造 buffer；§8.2 允许可验证逻辑 token；§8.9 禁止把 group ordinal 自动视为物理 generation。这些是单条事实的证据规则，并不承诺任何一份 group-only 数据足以完成全套资格。新文字保留这些规则，没有要求未知 buffer 的事件填造物理身份。
4. goal §2.2 要求每后端实际异步生产消费、动态关系及支持目标比较的时钟；本次澄清没有放松这些门，也没有用复用证据替代真实 submit/wait/completion、最终编译边界或 clock/epoch 证明。

## 剩余验证与范围

每后端仍须以真实数学样本核首轮、steady state、末轮 drain 的 buffer/flag 身份与 generation，并将真实记录、机制状态和最终编译对象对应起来。逻辑 group 事实本身保持其有限语义；若没有真实复用样本，此资格项保持未通过。这里不推断三个目标已经具有该证据。

本次只阅读 FOLLOWUP_INPUT、指定 P07/§8.4 行及 design §7/§8.2/§8.9、testing §5、goal §2.2 的必要上下文，并核对本地 SHA；未重审全文、未读 peer/旧评审、未运行产品/import/测试/构建/SSH 或设备任务，仅新增本复核报告。
