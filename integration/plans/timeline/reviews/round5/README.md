# 第五轮设计可行性评审与处置

本轮是设计/验收文档审查，不是实现或设备验收。三个 fresh-context reviewer 分别完整读取同一套五文档，独立出具初审；不读取彼此或旧报告。初审输入/源码基线与模型请求见 [INPUT.json](INPUT.json)，修订后的有限复核输入见 [FOLLOWUP_INPUT.json](FOLLOWUP_INPUT.json)。本轮采用会话默认模型/深度，不宣称满足实现末尾指定的 GPT-6.1-Sol/xhigh 额外代码走查。

| 评审 | 完整初审 | 初审结论 | 确认问题 |
| --- | --- | --- | --- |
| R1 编译边界与源映射 | [R1-compiler.md](R1-compiler.md) | 有条件认可；无确认 blocker/major/minor | 无 |
| R2 时钟、记录与生命周期 | [R2-runtime.md](R2-runtime.md) | 有条件通过；无确认 blocker/major | MINOR-01：未提交 kernel 不等于缓冲没有初始化写者 |
| R3 适配与 Perfetto 验收 | [R3-portability.md](R3-portability.md) | 有条件通过；无确认 blocker/major/minor | 无 |

## 处置

- **R2 MINOR-01，已修文档并通过 R2 有限复核：** design §8.7 和 testing §8.3 改为无任何设备初始化/提交写入才能直接回收；armed/submitting/quarantined 均按潜在写者处理，须取得覆盖全部写入的完成证明。E05 明列纯 admitted、初始化部分失败、初始化后未启动 kernel 三类测试。当前 owner 实现已保守处理，本轮修的是合同歧义，不声称发现产品 UAF。
- **R1 O1 / R2 可选建议1，采纳文档索引：** design §8.10 用小表列源码导航、counter 间隔、源区域耗时、逻辑关联、物理复用、时间箭头和 engine activity 分别需要的证据。未新增认证框架或资格矩阵。
- **R3 可选建议1，采纳：** 最终接入清单明确复用/失效条件及重新核验动作。可选交叉索引复用既有 §8.6 和测试 P/E 表，不新增平行状态日志。
- **其它风险，保留为实施门：** 最终机器区域顺序、getter/尺度/epoch/误差、物理 buffer/flag 两轮复用、真实发布与 owner、实际 Perfetto SQL/UI 仍分别由 P01/P03/P05/P06/P07/P08/E03/E05/E09 核验；本轮没有设备新结果，不能填通过。各 reviewer 的风险分析和覆盖限制保留在原报告。

## 设计结论的边界

三席均支持继续按 A/B/C/D 分段实施；这意味着未发现确认的设计自相矛盾或不可实施的必需路径，不是三种 SDK 必能完成的保证。未来新增芯片可复用公共身份、事件验证、时间算术和导出；编译接入、记录发布、clock 和异步机制仍要按实际 target/toolchain 核验。现阶段只检验三后端，不新增第四芯片，不承诺配置即可适配或固定工期。

## 最终有限复核

- [R1 复核](R1-followup.md)：资格表、源码/执行边界与初始化规则一致，无新增确认缺陷。
- [R2 复核](R2-followup.md)：MINOR-01 文档闭环，无新增问题；实际故障路径仍待 E05。
- [R3 复核](R3-followup.md)：适配边界、资格表、生命周期和验收一致，无新增问题。

三份复核均核最终五文档 SHA 与 FOLLOWUP_INPUT 一致，维持有条件认可。原始初审保持不变。初审两份变更文档可由 INPUT 的 source_head 加 [INITIAL_DOCS.patch](INITIAL_DOCS.patch) 精确恢复，已逐字节核对 SHA；其它三份输入未改。

本轮只做文档、只读评审与离线链接/摘要检查，没有启动新设备实验、修改产品代码或论文。完整 timeline 仍未通过三后端 P01、Perfetto 和最终资格，不因本报告更新实现状态。
