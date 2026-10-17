# 时间线适配边界设计独立评审

本轮更新工具设计/验收合同并完成三名独立设计评审，不运行设备实验、不改产品源码、不改论文。评审只判断设计合理性和可实施路径，不授予 P01/设备/Perfetto/代码资格，不替代实现完成后的三个额外独立代码 reviewer。

三名 reviewer 均 GPT-6.1-Sol、reasoning_effort=xhigh、fork_turns=none。独立初审，无互相交换报告；协调者随后合并意见，并分别请原 reviewer 有限复核修订。报告文件整理其返回意见、依据和复核结果，源码行号指初审版本。

| 评审 | 关注点 | 初审结论 | 报告 |
| --- | --- | --- | --- |
| timeline_design_review_compiler | 编译、发布、ABI、边界和可移植性 | 有条件合理可执行；1 P1、2 P2 | [compiler.md](compiler.md) |
| timeline_design_review_runtime | owner、stream、预算、异常与持久化 | 总体合理可实施；1 P1、2 P2 | [runtime.md](runtime.md) |
| timeline_design_review_portability | 部件复用、公共语义、时钟与 Perfetto | 有条件可执行；1 P2，无 P0/P1 | [portability.md](portability.md) |

三人均无需要推翻路线的 P0。协调者采纳全部具体文档建议：

| 意见 | 修订位置与处理 |
| --- | --- |
| 编译 P1：guard 失败丢已读回 bytes | 设计 §8.13、测试 §8.8 分离传输取得与完整性合格；真实 readback 边界故障留 raw/坏 guard，拒绝解释，安全持久化后回收 |
| 编译 P2：guard 不独证写址范围 | §8.13/测试§8.8 增 pointer lowering 的单位/整除、slot 地址差、各写入最大 byte end/无溢出；区分 allocation guard 与数学 canary |
| 编译 P2：公共 owner 不应绑定 NVIDIA 签名 | §8.13 复用预算/身份/状态机；后端封装 executable/context/queue，不编造 function/stream |
| 运行时 P1：unknown 首 owner 阻塞后续 ready | §8.13/测试§8.8 共同 deadline 内 ready-first；四类 pending/保存状态、保资源/bytes、有界无重放重试；不承诺任意数量全部落盘 |
| 运行时 P2：异步 host/native 资源生命周期 | §8.13/测试§8.8 owner 在首次异步提交前接管 device/staging/native/context/completion，禁止 legacy 析构/回滚绕过 |
| 运行时 P2：预算范围混淆 | §10/测试§8.8 冻结单调用、live pending/owner 与累计 raw/bundle；保原初始总raw8MiB作为 session 累计physical额度，计header/padding/guard；当前pending上限不冒充已实现累计门 |
| 可移植性 P2：实施顺序歧义 | §11 原位统一 A/B/C/D；首后端先C冻结实际合同，其余可先调查A，不等铺完三后端才核公共导出 |
| 有限复核：scratch 回收措辞 | §8.13 明确完成已确认且原件/关联快照安全持久化后回收，与§8.7一致 |

编译与运行时 reviewer 的有限复核确认原问题在文档闭环；可移植性 reviewer 确认顺序修订，并提出的单句生命周期歧义已按其建议原文修正。没有将文字闭环标为代码修复或设备通过。

评审输入文件 SHA 见 [review-input-sha256.txt](review-input-sha256.txt)，意见合并后最终文档 SHA 见 [final-document-sha256.txt](final-document-sha256.txt)。根目录 goal 与已跟踪快照仍同字节，更新仅补章节索引。

后续最小实证仍沿既有门：每后端公开 runtime-K 数学纵向链及一份真实 async/两轮物理复用样本，再做公共 Trace Processor、实际 UI、独立数学、故障与最终代码走查。新芯片当前不适配；实际成本待真实部件复用与设备证据判定。
