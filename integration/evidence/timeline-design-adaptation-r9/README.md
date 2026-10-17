# R9 时间线设计与验收独立评审

本轮响应用户的设计更新及三人独立评审请求。只修改工具设计、验收、goal 引用和评审留存，不修改产品代码、论文或 Study，不启动服务器实验。源码参考基线为 `691846f58ebd7b7ebda1f02c6a73fd1d5ba55370`。本轮不是最终代码验收，未改变任何设备通过状态。

## 更新入口

- [设计 §0 / §8.14](../../../Profiler/docs/timeline_design.md)：五部件交接、资格分离、版本与依赖失效、边界证据、输入闭包、canonical/派生 revision、收据提交/索引/锁恢复。
- [验收 §8.9](../../../Profiler/docs/timeline_testing.md)：部件错配、proof 信任边界、新进程离线重导、幂等/补证、并发/崩溃恢复、持久化与 release 故障；§4 明确 modulo 原值与展开坐标的区别。
- [执行合同](../../plans/timeline/goal_prompt.md)：章节引用同步到设计 §8.14 / 验收 §8.9；工作区根 `timeline_goal_prompt.md` 同字节。

## 独立结论

三人分别完成初审后才汇总修订，没有互相读取本轮初审报告；各自随后对所提问题进行有限文档复核。没有新开第四芯片、逐算子适配或全排列插件平台。整体结论是**职责划分合理，有可实施路径；三后端完整可行性仍须真实设备证据确认**。

| Reviewer | 独立结论与主要意见 | 报告 |
| --- | --- | --- |
| timeline_design_r9_compiler | 无 P0/P1 硬设计矛盾；补回绕判定、机器边界收据和实现内容指纹 | [compiler.md](compiler.md) |
| timeline_design_r9_runtime | 工程可实施；4 P1 补足事务提交/恢复、canonical revision、离线输入闭包、留存/release 故障 | [runtime.md](runtime.md) |
| timeline_design_r9_portability | 无 P0/P1 设计矛盾；明确有限兼容检查、重导锁终态；发现 2 项 P1 现有实施债 | [portability.md](portability.md) |

## 意见处置

| 意见 | 设计/验收的具体处置 |
| --- | --- |
| 回绕原 tick 不能强制 end≥start | 测试 §4 仅对唯一展开/导出坐标要求顺序，原 modulo 不变，不支持的 reader 保原件并拒绝时间解释 |
| 边界证据不能只有状态位或要求通用反编译器 | §8.14 列 binary/function/section、机器位置、区域块/范围、循环/依赖与未覆盖；公共 validator 与后端模式检查职责分开 |
| 人工规则版本漏升 | 派生身份绑定已安装实现内容/构建指纹；测试同公开版本文字但实现指纹变化 |
| 派生提交、锁、崩溃恢复 | 全部文件核验与 fsync 后原子发布完成收据，索引只发现完整收据；有界 OS 锁、退出释锁、不删他人锁；测发布边界及自有持锁子进程终止 |
| decoder 升级可能改变 canonical | raw 不变，旧/新 canonical 各有 revision 和输入摘要，视图引用实际 revision，保两条派生链 |
| 离线恢复依赖原环境 | 版本化输入清单保文件/摘要与必要 window/epoch/编译证据；关闭原进程、原缓存/工作目录不可用时只凭 bundle 和安装工具重导 |
| 留存或 release 失败 | 无完整输入收据不报已保存；保 bytes/身份/必要资源，重试补齐闭包，不重复预算或释放；受控 I/O 故障不耗尽磁盘 |
| 摘要确定性及旧资格撤销 | 规范编码、非语义字段不入身份；追加撤销/替代关系，保历史结果，索引不把已撤销资格当当前推荐 |
| 适配组合检查不要膨胀 | 只核实际消费的依赖边、阶段和失效范围，不建全排列兼容平台 |
| 现有 owner/派生命名代码债 | 记录为待实现：owner 输入仍有 NVIDIA 形状约束；counter exporter 尚无完整 proof/规则摘要目录。本文档修订不代表这些代码已修复 |

最重要的未实证风险是自动区域边界与 ordinary 流水保持、真实两代物理复用、Ascend 发布/回收及 GCU 时钟。按最小循环与实际异步样本逐项验证，再扩独立数学与完整 UI；不以更多同类数据、漂亮图或设计评审票数替代这些证据。

初审输入摘要见 [review-input-sha256.txt](review-input-sha256.txt)，最终文档摘要见 [final-document-sha256.txt](final-document-sha256.txt)。三份报告末尾保有限复核结果；文档问题闭环不授予代码、P01、设备或 Perfetto 完整资格。最终交付仍需额外三个独立代码 reviewer。
