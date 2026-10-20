# E01 十调用的 64 MiB 范围复核

**结论：64 MiB 适用于本测试这一个公开 session 的完整 capture bundle；不能改解释成每调用 64 MiB、仅独立数学代表包或单 trace 限额。** 原文没有单列一句“E01 必须 ≤64 MiB”，但已有完整 bundle 数值与累计 session/bundle 范围的明确规定；新增测试只把两项已有要求合在同一次执行里核验。

确切依据：

- 根 `timeline_goal_prompt.md:105`：“完整执行 `Profiler/docs/timeline_testing.md`，不是只跑这里的摘要”。`:112`：“默认预算：raw 初始8MiB、trace目标16MiB、完整bundle64MiB”，并禁止静默放宽或删必要 raw 掩盖超限；`:115` 同时要求 E01–E12。该默认预算没有“仅独立单调用”例外。
- `Profiler/docs/timeline_design.md:585`（§10）：“单调用物理需求与上限、session live pending 字节与 owner 数、session 累计留存及 bundle 上限”；同段还明确“source/manifest 等仍计完整 bundle”。`:587` 规定“完整 bundle 64 MiB”“默认选择和协议开销必须计入总预算”。因此累计 compiler snapshots/observations 属于 bundle，不能因不是 raw 而排除。
- `Profiler/docs/timeline_testing.md:321`（§8.8）明确要求核“单调用、live pending、owner 数及累计 session raw/bundle 预算”，并写明“已释放不再占 pending，但累计保留仍计额度”。这排除了以十次各自合格或中间资源已释放来替代 session 累计门。
- `timeline_testing.md:140` 的 E01 本身核“同脚本重复 10 次调用，交错两个 specialization”以及隔离/无 replay。**E01 的专属语义门与完整 session 的预算门应分别报告。**

上述 design §10 / testing §8.8 条文在先前 `ea27308` 中已经存在，不是 `de69ede` 新测试增加的要求。根合同与 tracked `integration/plans/timeline/goal_prompt.md` 本次字节比较相同。

本测试 `tests/timeline/p01_interleaved_specializations.py:56` 只 `start` 一次，`:58` 在其中执行十次，`:106` 最终化同一 session；`:150` 又核同一 capture ID。`:155–157` 只统计 `output/capture` 下完整 bundle，没有把外层 `calls.json`、host-once 文件或测试控制器目录混入。故按此代码，最后的 64 MiB 断言范围与上述合同相符。此结论不独立核验所报 85.58 / 111.49 MB 的原始目录计量。

判定应保留为：NV 已报全过；Asc/GCU **E01 十调用的数学/隔离/raw/time 等已执行子门通过，完整 session bundle 预算失败，whole test 失败保留**。此前独立单调用的 36 个超限原件已经 CPU 修复，与这次多调用累计失败是不同范围，不能互相替代。也不能把这个预算失败改称十调用数学或隔离失败。

`timeline_runtime.md:474–475` 如实说明 compact HTML 本身不是任意应用完整 capture bundle 的硬 admission 上界；`:847–848` 还区分 derivative tree 的 64 MiB cap 与另行约束的 whole-bundle/session budgets。这些实现范围说明不是取消资格预算的合同例外。本结论不要求任意长度应用都固定 ≤64 MiB、不增设新的设备/数学/SQL/UI 验收，也不据这一项判断具体产品修复方式。

只读合同与测试源码范围复核；未执行产品/测试或读取其他席报告，未修改实现。对象：新增 test `de69ede`，据请求 runtime 仍 `61cb831`。
