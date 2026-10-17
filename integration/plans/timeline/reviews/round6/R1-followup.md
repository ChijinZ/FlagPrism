# R1 有限复核：章节索引修复

范围仅为初审 R1-M1 的索引修复及输入身份核对。没有读取 peer 报告、联网、运行产品/测试/设备，也没有重审实现；只写本文件。

**结论：R1-M1 已关闭；无需重跑初审。** 根目录 `timeline_goal_prompt.md` 与已跟踪 `integration/plans/timeline/goal_prompt.md` 字节一致，§3.1 已正确指向设计 §8.1–8.11、测试 P01–P10/§8.2–8.6。

核验记录：

- 五份文档的实际 SHA-256 全部匹配 `FOLLOWUP_INPUT.json`。
- design/testing/runtime/events 四文件 SHA 与初审 `INPUT.json` 相同。
- 两份合同现 SHA 均为 `70da4b7ff287ab76446bbd3da65cb7f682e6698002c9caabe334420f11ffdbda`。
- 将已跟踪合同中唯一一处已修订索引还原为初审索引，所得 SHA 为 `7f1e288720694faa702262080298f8efd9caa62d5bffc4af80095f918cff4932`，精确匹配初审合同 SHA。这证明该文件全部差异仅为该处章节范围修正，未改变验收门槛。

初审“未发现 confirmed blocker/major，设计可作为工程执行依据”的结论保持；初审列出的设备 verification gaps 全部保留。本次既不授予设备/P01/Perfetto 通过，也不替代最终额外指定 `GPT-6.1-Sol`、`xhigh` 的代码验收。
