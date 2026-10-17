# R2 有限复核：状态说明与合同引用

结论：**R2-M1 已关闭；本次修订未引入新的状态矛盾，未降低验收门槛。** 初审的“有条件合理”结论保持，设备与实现风险仍按原 P/E 门闭合。本复核不授予产品、P01、独立资格、Perfetto 或新增芯片支持结论。

## 输入与范围

- 席位：独立 R2，agent `/root/design_feasibility_runtime`；请求 `gpt-6.1-sol` / `xhigh`，resolved serving 未暴露，实际 serving 未知。
- 日期：2026-10-17。按 `FOLLOWUP_INPUT.json` 仅核状态修订、合同引用、空行清理及原门槛保持；未读 peer 报告，未连接服务器或运行产品／设备，仅新增本复核文件。
- 原初审 `R2-runtime.md` 保持原文，SHA-256 为 `aae63967b977a6b86c46f9d4b178dbd73c606d06d36ec70acfbd31aee89d409d`，与落盘时一致。

| 最终输入 | 实测 SHA-256 |
| --- | --- |
| `Profiler/docs/timeline_design.md` | `8c4014188a6033145075446e75061c52a3027e26555d0b31061f84b8e539652f` |
| `Profiler/docs/timeline_testing.md` | `193b60a0c643622af39642e6792e6d3c7d6a0852b6468e8d4fd618f28a8d35c7` |
| `integration/plans/timeline/goal_prompt.md` | `7f1e288720694faa702262080298f8efd9caa62d5bffc4af80095f918cff4932` |
| `Profiler/docs/timeline_runtime.md` | `316d2febcdc7439dd504f07109230b4095753f88d72ccda3b1a8f4d5e6d5d9a9` |
| `Profiler/docs/timeline_events.md` | `c41f6949d41f0f5596c358e1a4d0382edda091e2de66a51a1d31184a171527ee` |

五项实测 SHA 均与 `FOLLOWUP_INPUT.json` 匹配。工作区根 `timeline_goal_prompt.md` 与已跟踪快照均为 18399 bytes，逐字节内容相同，SHA 均为 `7f1e288720694faa702262080298f8efd9caa62d5bffc4af80095f918cff4932`。

## 判定依据

1. **当前状态入口一致。** 设计 L3 已指向 runtime/events 并明确 §8.8 仅是历史原语检查点；设计 L35、§8.10、合同 L67 与 runtime L3–20 一致限定为 NVIDIA-only 的 `partial_clock_unverified` raw 采集。认证 ns、Perfetto 和另两后端时间 producer 仍未完成，raw 不等于完整交付。原 R2-M1 的两处触发已消除。
2. **历史基线与后续实现不混用。** 合同 L20 将初始设计基线标为历史，恢复工作转向实际 HEAD、工程记录和 runtime/events；不再声称之后只有设计文档提交。
3. **接入引用完整。** 合同 §3.1/L79 已引用设计 §8.1–8.10 和验收 §8.2–8.5，覆盖初审已读的部件组合、raw/ns 分离与实际三后端复用边界；不新增第四芯片要求，也不把 fixture 升级为设备证据。
4. **门槛没有降低。** 将最终设计中的 L3 改回初审原句并恢复 §8.10 前删除的空行，重建结果 SHA 恰为初审设计 `6f433840e0da7938e9201381d85c1a6bcaa785134fed9c69d382ff5d3de930f3`；将最终验收恢复 §8.5 前空行，SHA 恰为初审验收 `456c3cc29588cbfd61754c345b6752bd9b29a740f42752108e6809384db3fdc2`。因此两文相对初审的实质 delta 仅是已说明的状态入口修订；P01/P07、两轮真实复用、时钟／发布／最终边界、独立数学、SQL/UI 等门均保持。合同相对初审仅变更 L20、L67、L79 三段，完成／资格条款未变。

本轮没有新增 confirmed blocker/major/minor；原 V1–V6 仍是待实现后实证的风险，没有因本次文档修订变成已通过项。无需为这一状态与引用修订重跑设备或扩大审阅范围。
