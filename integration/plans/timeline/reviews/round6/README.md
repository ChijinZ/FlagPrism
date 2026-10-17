# 第六轮独立设计可行性评审

本轮响应“更新设计与验收文档，并由三个独立 subagent 评审合理性及实际可行性”。只更新工具设计/验收文档、索引和评审材料，不修改产品代码、论文或 Study，不启动服务器或设备任务。已有实现与设备作业的状态不由本轮授予或改写。

## 本轮设计更新

- 设计 §8.11：把可组合编译、transport/decoder、clock、机制映射和公共消费者落实到输入输出与复用/替换条件。复用现有函数与对象，有真实共享调用者后才抽取，不增加插件框架或统一设备 IR。
- 设计 §8.11：设备函数调用只是 NVIDIA 的边界候选；其它后端可有不同合法实现。最终对象须核函数、代码段及真实地址范围。因果握手不自动授予尺度、端点误差或全局 epoch 资格。
- 测试 §8.6：具体化自动循环/访存、多函数对象、因果校准范围、端点不可分辨、部件复用和阶段推进，复用既有 P/E 与样本，不增加独立数学数量。

## 三个独立意见

三位均以 fresh context 完整阅读同一五文档，不读旧报告或 peer 报告。配置及输入见 [REQUEST.json](REQUEST.json)、[INPUT.json](INPUT.json)。本次使用会话默认模型/深度，不宣称是最终指定 GPT-6.1-Sol/xhigh 代码验收。

| 评审 | 初审 | 确认问题 | 结论 |
| --- | --- | --- | --- |
| R1 编译与边界 | [R1-compiler.md](R1-compiler.md) | 0 blocker/major；1 minor | 可作为下一阶段实施依据，最终自动边界须实证 |
| R2 时钟、发布与 owner | [R2-runtime.md](R2-runtime.md) | 0 blocker/major/minor | 分解及验收可执行，物理时间和生命周期须实证 |
| R3 适配与 Perfetto | [R3-portability.md](R3-portability.md) | 0 blocker/major；1 minor | 抽象与三后端路线合理，不能承诺第四芯片工期或能力 |

R1/R3 的 minor 是同一问题：goal §3.1 的局部索引漏掉新增设计 §8.11 / 测试 §8.6。已同步根目录执行入口与已跟踪快照，只改引用范围，不改目标和验收门槛。初审保持原样；初审文档可从 INPUT.source_head 加 [INITIAL_DOCS.patch](INITIAL_DOCS.patch) 恢复。最终五文档 SHA 见 [FOLLOWUP_INPUT.json](FOLLOWUP_INPUT.json)。

## 共识及结论边界

继续按最小纵向样本、A/B/C/D 分段推进。最主要的未闭合项是每后端的自动最终机器边界、时钟尺度/epoch/误差、真实发布与 owner 故障窗口、两轮物理 buffer/flag 复用，以及共同 ns/Perfetto SQL/UI。它们是实施中的实证风险；设计评审没有发现必然不可行的约束，也没有证明三个 SDK 一定能闭合所有目标。

缺证时保 raw、合法子集和具体失败，修通用机制；不靠新增算子矩阵、伪 generation 或降低门槛来补图。三后端 P01、完整资格、独立新数学及实现结束后的额外三名指定配置代码审阅仍保持原要求。

## 有限复核

索引修复后由原三席分别核对五文件 SHA 与修改范围；报告为 [R1-followup.md](R1-followup.md)、[R2-followup.md](R2-followup.md)、[R3-followup.md](R3-followup.md)。有限复核只检查本轮文档修复，不是新增设备实验或完整实现验收。

三份有限复核均通过：同一索引问题已关闭，无新增确认问题；初审设计结论与实证缺口保持。
