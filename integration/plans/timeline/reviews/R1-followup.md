# R1 有限独立复核

本次复核的最终三文档 SHA256，与 `reviews/FOLLOWUP_INPUT.json` 逐一相符：

| 文档 | SHA256 |
| --- | --- |
| `Profiler/docs/timeline_design.md` | `0b119149db183388c58da6119f7079f13602170eb75d8951019eddced97ae7d0` |
| `Profiler/docs/timeline_testing.md` | `3f2785b024c6430188c39af749462b20af4a67fa93f956d1fbbc0c7a5532946e` |
| `integration/plans/timeline/goal_prompt.md` | `08b854213cd214105932e94ff8f2c328ba7ab9b5d4f6a4c46b9f0c80b042ba40` |

日期：2026-10-17。评审任务：`/root/timeline_design_compiler_review`；指定模型请求仍为 `gpt-6.1-sol` / `xhigh`，实际 serving 版本未知。

本轮仅复核本席原问题及相关文档 delta：设计 §2、§4–5、§8.1–8.6，测试 §8–8.2，以及合同 §3.1 和完成条件。没有读取其它席报告或处置记录，没有开展新一轮全仓审计，没有运行产品 import/build/test、SSH 或设备任务。原初审 [R1-compiler.md](R1-compiler.md) 保持不变，其 SHA256 为 `18b58ebc35728b00684cb1928a59f5bd8adfb48211d69ec3bb48450161626651`。

## 复核结论

**设计层面可以启动 P01，不需要再追加文档修订作为先决条件。** 执行按 goal 合同的启动授权和环境约束进行。本轮未启动实现，也没有新增设备可行性结果。

原有两项 confirmed minor 均关闭；本次有限范围内未发现新的 confirmed blocker、major、minor 或相互排斥的设计要求。原 V01–V06 中的实际编译器、计时与异步可行性仍未验证，不能因补齐文档而改为设备通过。第一条真实链后冻结小合同、第二/第三后端检验并显式修订、全量资格前各后端通过 P01 的次序合理。

## 原 confirmed 问题处置

| 原问题 | 复核状态 | 最终文档依据及判断 |
| --- | --- | --- |
| R1-M01：NVIDIA 现状遗漏已有自动 interval 路径 | **关闭** | [设计 L23](../../../../Profiler/docs/timeline_design.md#L23) 现列明 advanced 自动/手工 Proton interval、源关联和 scope 接入，同时明确公开 timeline、优化后 manifest、timer/ns、partition/async 仍待补；[L126](../../../../Profiler/docs/timeline_design.md#L126) 明确复用并扩展现有自动 scope/discovery。它符合初审源码事实，没有把已有 raw-cycle interval 冒充新目标通过。 |
| R1-M02：逐份 UI 要求普通 trace 点击不存在的 flow，且浏览器地点含混 | **关闭** | [测试 L120–130](../../../../Profiler/docs/timeline_testing.md#L120) 指定对应服务器已有 Docker 中的标准 Perfetto UI；L122 要冻结每份适用性；L127 对有 flow 样本核端点，对无异步普通样本核无伪 flow，同时禁止应有 edge 的异步样本用 N/A 逃避。L125/L130 也按循环适用性检查真实内部结构。每后端真实异步/UI 门槛没有因此降低。 |

两项关闭均是文档问题的关闭，不需要为文字修正额外启动设备测试；实现后的真实 UI 和异步正例仍按原资格执行。

## 相关 delta 是否解决本席的设计层风险说明

| 原风险 | 本次文档变化 | 尚未完成的实现/实证 |
| --- | --- | --- |
| V01：优化后源身份、M:N origin 与时间归属 | [设计 L146](../../../../Profiler/docs/timeline_design.md#L146) 明确 fused 多 origin 不得复制 duration 凑两个阶段，split/消除/未知分开；[§8.6 L202、L210](../../../../Profiler/docs/timeline_design.md#L202) 明确 manifest 状态、binary、anchors、控制路径/loop 及源 snapshot 关系。**所需合同清单已经明确。** | 三后端真实源→优化后 site→最终对象→raw 映射，以及源循环经 pipeline 后的真实 occurrence/iteration 关系。schema 列表仍须变成可执行验证器与真实 producer。 |
| V02：timer/logger 副作用不足以证明计算不越界 | [设计 L68](../../../../Profiler/docs/timeline_design.md#L68) 明说 volatile/side effect/memory clobber 不充分，必须说明约束编译层并核最终对象；[测试 P03 L142](../../../../Profiler/docs/timeline_testing.md#L142)、[§8.2 L159](../../../../Profiler/docs/timeline_testing.md#L159) 纳入纯算术 loop、访存、原 async wait 的普通/插桩 IR/ISA 对照。**要求已清楚。** | 每后端真正合法的依赖/插入方案和最终顺序证明；不能仅凭 marker 保留、正 duration 或无数值错误通过。 |
| V03：NVIDIA partition、timer 和 packed ABI | [设计 L212](../../../../Profiler/docs/timeline_design.md#L212) 保留 worker partition 与旧 32/43-bit SM clock 风险；[测试 L160](../../../../Profiler/docs/timeline_testing.md#L160) 要求 getter、packed 位宽、decoder/ABI 一致。 | 普通 async 数学的实际 observer/program/partition 身份、真实 group/wait 覆盖与 generation、目标 timer 单位/可比时钟。已有自动 scope 不自动解决它们。 |
| V04：GCU 早期 TTIR 与晚期合法边界、timer/async | [设计 L212](../../../../Profiler/docs/timeline_design.md#L212) 明确保留实际边界、单位与 async 路径待证；§8.5/P01 仍要求真实纵向样本。 | 实际 SDK 可用插桩层、最终边界、真实写者与发布、可验证 ns 比例/epoch，以及 ordinary async submit/wait/completion 的动态关联。没有由文字证明 SDK 必可接通。 |
| V05：Ascend checkpoint 与通用多区间、动态 v1 与 census v3 | [设计 L212](../../../../Profiler/docs/timeline_design.md#L212) 明确 scalar optimization 前的 observer 和普通 checkpoint 状态；[测试 L160](../../../../Profiler/docs/timeline_testing.md#L160) 要新 timeline 独立证明 cache-line/commit。 | 通用两个真实区域、同一 binary 的动态循环、最终对象边界、AIC/AIV/flag generation 与所需共同 epoch，以及新记录协议设备可见性。 |
| V06：真实 grid、admission、host-once 和缓存依赖 | [设计 L174–176](../../../../Profiler/docs/timeline_design.md#L174) 区分 ordinary eligibility、target capability 与 outcome，并要求查询缓存前取得依赖内容身份；[测试 L162](../../../../Profiler/docs/timeline_testing.md#L162) 纳入同 specialization 改 grid、首末坐标/admission 和内存/磁盘缓存。 | 真实 launch 上的首末 program、零 grid/tail、先 admission 和无重放，以及 SDK/timer/plugin/rule 原地改变的缓存行为。新字段要求不等于 hook 已实现。 |

[设计 §8.6 L196–210](../../../../Profiler/docs/timeline_design.md#L196) 选择在第一条真实纵向链之后形成小版本 schema/接口与实例，列出类型、基数、必填/可空、引用、扩展与未知语义规则，同时允许后续真实后端有理由地修订版本。它回应了本席对“可执行小合同”的建议，没有变成设计阶段空框架，也没有要求用同一个物理 ABI 消除后端差异。

[测试 §8.2 L157](../../../../Profiler/docs/timeline_testing.md#L157) 明确复用已有 P/E 检查而不另扩大资格矩阵；L159 只核实际出现的优化变换，避免为满足表述强迫某后端产生本来没有的 fusion/split。它保留三后端真实 producer 的证据要求，没有用 CPU fixture 替代。

[合同 L79–83](../goal_prompt.md#L79) 已同步要求设计 §8.1–8.6 与测试 §8.2，仍要求每后端真实两区间、异步及可比时钟和 Trace Processor 后进入最终资格；[完成条件 L145–150](../goal_prompt.md#L145) 继续保留三后端普通 kernel、多区间/循环、每后端真实异步、标准 Perfetto SQL/UI 和旧数据兼容。未发现此次相关修改降低交付目标。

## P01 的明确判读

可以开始普通 baseline 和必要通用编译器/协议实现，以取得三后端各自的实际 timer/单位、两源区域、合法发布、一个真实 async 机制及其动态关联/可比时钟、Trace Processor 证据。它们都成立才叫对应后端 P01 通过；缺失项保持未验证或以实际证据确认阻碍。

本次确认的是文档处置已闭合、实施顺序合理。**不是 P01 已通过，不是三后端完整工程可行性已证明，也不替代最终实现后的独立代码、硬件及 Perfetto 验收。**
