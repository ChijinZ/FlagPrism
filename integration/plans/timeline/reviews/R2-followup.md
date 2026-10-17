# R2 有限独立复核

主文档 SHA256（与 `FOLLOWUP_INPUT.json` 一致）：

| 文档 | SHA256 |
| --- | --- |
| `Profiler/docs/timeline_design.md` | `0b119149db183388c58da6119f7079f13602170eb75d8951019eddced97ae7d0` |
| `Profiler/docs/timeline_testing.md` | `3f2785b024c6430188c39af749462b20af4a67fa93f956d1fbbc0c7a5532946e` |
| `integration/plans/timeline/goal_prompt.md` | `08b854213cd214105932e94ff8f2c328ba7ab9b5d4f6a4c46b9f0c80b042ba40` |

日期：2026-10-17。Agent：`/root/timeline_design_runtime_review`。沿用请求配置 `gpt-6.1-sol` / `xhigh`；实际 serving 模型版本仍不可见，记为未知。输入清单 SHA256：`53df15b665cc22086067ec76d5fe373f11887a7627ee7e7e3a0e987a9d15bd55`。初审 `R2-runtime.md` 未修改，其 SHA256 仍为 `f29f9b792814dcbe72acf36413ca5899d414a7992c8f94d07d72565b3ef38ce4`。

## 结论

**可以启动 P01 约束下的实现，无需为本席列出的风险再次修订文档。** 本次有限复核未发现修订引入 confirmed blocker、major 或 minor 矛盾。

初审 V1–V6 已恰当地转成实施合同与可定位的验证条目。这里只关闭“合同没有写清”的问题；不关闭 timer/epoch、机器顺序、动态依赖、发布可见性或生命周期的真实验证缺口。三后端全部必达，partial、raw-ticks 页面、静态关系或旧 census 结果仍不能替代目标。

## 按修订范围核对

| 核对项 | 本次证据 | 判断 |
| --- | --- | --- |
| Buffer owner 与安全最终化 | 设计 `86–88` 要求每 invocation 独立 owner/完成依赖，允许最终化等本次记录完成，禁止沿用逐 launch 同步宣称保留跨 stream 提交关系；异常/cancel 不得提前复用或回收仍被写入的记录。测试 `161` 给出不主动同步的两 stream、pending 关闭/异常/cancel、D2H/导出失败后恢复。 | 正确区分安全导出等待与改变应用提交关系的等待。没有产生“为了不等待而提前读/释放”的反向要求，也没有要求旧强同步行为原样保留。V5 的合同缺口闭合。 |
| 截断 timer 整圈回绕 | 设计 `100` 明确 `end>=start` 也不能排除完整一圈，须有独立可判定窗口；测试 E09 `96` 纳入该负例。 | 不再允许旧的“只在 end<start 检查回绕”路径直接取得完整资格。V2 的该项闭合。 |
| 端点不确定性 | 设计 `108` 按端点不确定区间判断，给出保守独立误差先后条件，同时保留共享误差实际模型和近边界不可分辨状态；E09 `96` 对长区间近边界拒绝过度判断。设计 §8.6 `204` 包含误差模型、有效窗口及 ns 舍入规则。 | 不再以误差小于总 duration 代替边界比较。共享项没有被强制当独立项重复计算。V2 的该项闭合；数值模型仍须实施后验证。 |
| Fusion 与内部阶段计数 | 设计 `146` 允许 fused interval 引用多个 origin，但禁止复制同一 duration 凑两阶段；split/消除/未知分开。P03 `142` 与测试 §8.2 `159` 同时覆盖实际边界、纯算术/访存/原 wait 和实际发生的变换。 | 保留 M:N 源关联，不以源节点数量虚增执行区间。没有要求编译器制造本来不存在的 split/fusion。该合同与两真实内部区间硬门槛一致。 |
| Ordinary 资格、能力和 outcome | 设计 `172–174`、§8.6 `200`、测试 `163` 将事前普通资格、目标能力、instrumented plan/outcome 分开并相互引用，禁止后两者覆写资格清单。 | profile 失败不能追认 unsupported；能力可以细化而冻结分母不回写。这没有阻止实际编译后补充更精确事实。 |
| 缓存前取得真实依赖身份 | 设计 `176` 明确在内存/磁盘 cache 查询前取得内容身份，区分 capture epoch/clock 证明与编译 key；测试 `162` 覆盖 SDK/timer/plugin/rule 的实际身份，E07/P10 保留升级与恢复验证。 | 正确封住“只在 miss 后 metadata 算 hash”的漏洞，同时避免将每次 epoch 塞进编译 key。V6 的合同缺口闭合。 |
| Operation/group/wait 与恢复 | 设计 §8.6 `205` 明确实际 operation 集合、commit 分组、wait 覆盖、completion、generation、失效/恢复锚点、多消费者与引用完整性。P07 `146` 明确部分 wait 不完成未覆盖组、保留第二消费者、丢 commit 不平移后续 generation、仅锚点恢复。 | 新合同不是一对一 token 的换名。V3 和 V4 中 loss 后语义恢复的要求已写实；具体后端状态机不能由文档代为证明。 |
| 全部 raw/proof 引用 | 设计 `203,208–210` 要求全部 begin/end 或 SDK 记录引用、类型/基数/版本及跨对象引用校验；测试 `163` 要求每 slice/flow 保全端点和组成员所需 raw 证据。 | “有一条代表记录的 offset”不再足以给一条完整 slice/flow 验证通过。未强制三个后端共用物理 ABI，保留合法后端差异。 |
| 真实布局与小版本时机 | 设计 `196,212` 明确第一真实链之后再冻小版本，并承认动态 v1 不等于 census v3；测试 `160` 分别要求 Ascend 新时间协议、GCU 实际 work-item/payload、NVIDIA timer/packed 位宽一致性。合同 `79` 已把 §8.6 和最小实证纳入执行要求。 | 旧 ABI 不能仅换 exporter 取得新资格，也没有在真实调用者出现之前新增空框架要求。V4 的实施要求闭合。 |

测试 §8.2 `157` 明确复用原 P/E 场景而不扩大独立资格矩阵，安排合理。它把原来散落的风险组成可核查的最小证据链，没有用额外大矩阵替代核心机制验证。§8.2 `165` 仍明确这些检查待执行；本次复核不读取该行链接的其它席报告。

## 仍须真实 P01 与相关 P/E 关闭的部分

1. **三个 timer 的真实时间尺度和适用范围。** NVIDIA 的新 timer、packed 有效位宽与 decoder 要一致；Enflame C200 的实际 target/SDK helper、频率或独立校准和误差要取得证据；Ascend 的本机 SYS_CNT/SDK 比例不能自动扩展为 AIC/AIV 共享 epoch。跨主体比较只在实际证明的范围内开放。
2. **两个实际源区间和 runtime loop。** 核最终 IR/ISA 中算术、访存及原 wait 的真实顺序，不能以 volatile、正 duration 或 pass 被调用替代。每个 fused 区间只算一个实际阶段；编译后没有的边界不能补造。
3. **新记录协议真实发布完整性。** Ascend timeline 的 cache-line/commit 可见性、GCU 实际 work-item 对完整 payload 的写入、NVIDIA 记录编码及损失核需要设备正例。旧 census v3 通过不能转移给动态 v1，CPU fixture 不能代替设备发布证明。
4. **真实 async 状态机和可比时钟。** 每后端一个真实机制及两轮复用；operation 集、group/wait 覆盖和 generation 有编译/控制路径依据。部分 wait、多消费者和 loss 恢复的公共 fixture 必须有明确预期集合，不能冒充硬件支持。Ascend 表 `128` 的 AIC/AIV 动态依赖/可比时钟要求仍然保留。
5. **生命周期与 cache 命中行为。** 两 stream 和 pending 失败恢复要按测试 `161` 留真实依赖/调度及回收证据；依赖原地替换、symlink 和 count/timeline 切换要在内存、磁盘两级命中路径证明身份更新。文档正确不等于现有 runtime 已改好。
6. **真实导出链。** P01 中标准 Trace Processor 导入及 raw 对照仍须执行；后续独立数学、SQL/UI 和最终代码走查仍是另行必达，P01 不取代它们。

这些不是启动前必须先证明完毕的文档缺陷，而是启动后的早期纵向工作。一个后端不能取得必要证据时，保留已做工作、具体缺口和允许扩展的尝试；其它不依赖工作继续，整体不能标完成。

## 本次范围与未执行事项

本次仅读取 `FOLLOWUP_INPUT.json` 及三主文档的所列修订范围、相邻语义和执行合同交叉引用；没有重新做全仓源码审计，没有读其它席报告，没有修改初审。仅新增本文件。

没有 import/build/test、SSH、设备实验、时钟校准、Trace Processor 或 UI 操作；没有新实验结果。报告判断为**合同修订已充分，可以启动 P01**，不是实现或三后端能力已验证。
