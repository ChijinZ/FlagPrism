# Internal timeline implementation plan

These files describe the **target design under implementation**, not a completed
timeline feature. Limited primitive/build evidence is tracked separately; this
document revision starts no device experiment.

- [Execution contract](goal_prompt.md): tracked same-byte snapshot of workspace-root `timeline_goal_prompt.md`.
- [Technical design](../../../Profiler/docs/timeline_design.md).
- [Real-operator and Perfetto test plan](../../../Profiler/docs/timeline_testing.md).
- [Initial record](record.initial.md): immutable T000 snapshot; live execution record is workspace-root `timeline_impl_record.md`, outside Git.
- [Original design review and disposition](reviews/README.md): T001 historical inputs and resolutions.
- [Second design review](reviews/round2/README.md): refined backend handoffs, lifecycle and evidence gates, plus limited followups.
- [Third design review and disposition](reviews/round3/README.md): three fresh independent feasibility reviews of the minimal backend contract, compact storage and capability progression. Design reviews do not replace final implementation code reviews.

- [Fourth design feasibility review](reviews/round4/README.md): component composition, target/toolchain reuse, immutable raw and certified time views, staged acceptance, and three independent reviews.

- [Fifth independent design review](reviews/round5/README.md): explicit component compatibility, per-conclusion proof scope, initialization-safe reclamation, and three independent reviews with limited follow-ups.

- [Sixth independent design feasibility review](reviews/round6/README.md): concrete component handoffs, target-specific boundary strategies, causal-clock proof limits, executable acceptance cases, and three fresh-context reviews.

When the user explicitly invokes `/goal` with the root contract, the agent must
implement, build, test and qualify the feature on all three backends and finish
with three independent requested GPT-6.1-Sol/xhigh code reviews. Proposed CLI
names and example output paths in the design do not claim existing functionality.

The design now requires explicit compiler/runtime/clock/async backend boundaries
and P01–P10 portability checks using the three existing backends. No fourth
device port is included. Interface reuse is assessed from real implementations
and change evidence, not from a dummy backend or a promised porting time.

Copy into Codex when ready to start (this is not a shell command):

```text
/goal 读取并执行 /home/jin-lab-pc/workspace/osdi_flagprism/timeline_goal_prompt.md，沿用 timeline_impl_record.md。按配套设计和测试计划，把三个后端的自动内部时间采集、动态依赖和标准 Perfetto 时间线做到真实可用；完成实际算子、独立新数学、Trace Processor SQL 和 Perfetto UI 验收，最后由三个额外独立的 GPT-6.1-Sol、xhigh subagent 代码走查并闭环确认问题。只做工具工程，不修改论文；以 Git 管理并推送 detailed-profiler。不得用计数、整核时间、示意数据或未核验的时钟对齐替代目标；真实环境阻碍保留证据后返回。
```

- [Seventh independent design review](reviews/round7/README.md): independently replaceable backend components, canonical pair ordering/loss units, public capture integration, and executable acceptance. Documentation review only; no new device qualification.
