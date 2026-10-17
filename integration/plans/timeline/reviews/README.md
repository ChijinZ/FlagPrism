# 时间线设计评审与处置（T001）

本轮仅修改技术设计、验收设计和执行合同，**没有启动实现、连接服务器、构建、产品测试或设备/Perfetto 实验**。本文的“关闭”只表示文档问题修订；真实可行性仍按 P01 及后续验收确认。最终实现后的三个独立代码走查保持必达，不由本轮评审替代。

## 评审输入与独立性

三个 fresh-context agent 均完整读取同一版本的技术设计、测试设计和执行合同，并可只读核必要源码；不读取彼此报告。请求配置均为 GPT-6.1-Sol / xhigh / fork_turns=none，创建工具接受了请求，实际 serving 型号/版本未暴露，记为未知。

- [初审请求、agent 与输入 SHA](REQUEST.json)。
- [修订后有限复核输入 SHA](FOLLOWUP_INPUT.json)。
- [R1 编译插桩初审](R1-compiler.md)；[修订复核](R1-followup.md)。
- [R2 时钟、异步和运行时初审](R2-runtime.md)；[修订复核](R2-followup.md)。
- [R3 适配边界和验收初审](R3-portability.md)；[修订复核](R3-followup.md)。

初审报告保留原文及原输入 hash；复核另写，不覆写初审。报告中的旧行号属于其实际输入版本。

## 确认问题及文档处置

| 初审问题 | root 核实及修订 | 复核状态 |
| --- | --- | --- |
| R3-M01（major）/R1-M02（重叠部分）：逐份 UI 步骤无条件要求循环和 flow | testing §8 改为通用步骤与适用步骤，资格前冻结 UI 覆盖表；普通非异步样本核无伪 flow，每后端真实异步样本仍必须核端点/generation/clock，缺应有 edge 不能 N/A | 三席相关有限复核确认关闭 |
| R3-m01（minor）/R1-M02（重叠部分）：本机 browser 与 server-Docker 约束冲突 | testing §8 明确对应服务器已有 Docker，截图收据记录服务器/容器及 browser/UI 版本 | 三席相关有限复核确认关闭 |
| R1-M01（minor）：NVIDIA 现状遗漏已有 advanced 自动 scope | design §2/§8 改为复用并扩展已有 automatic scope；明确缺目标 timer/ns、晚期 manifest、partition/async 与完整公共交付，不把 raw-cycle 路径当新目标通过 | 三席相关有限复核确认关闭 |

R2 未确认 blocker/major/minor。三席都认为总体边界允许合理实现；R3 要求先处理上述验收歧义。不同席对同一 UI 问题的严重度不同，按具体触发和修订处理，不作多数投票。

## 验证缺口如何进入实施合同

| 风险/条件 | 文档落实 | 当前状态 |
| --- | --- | --- |
| 早期源节点不等于优化后执行边界；有副作用的 timer 也不保证纯算术不越界 | design §4/§8.1/§8.6；P03、testing §8.2；实际 IR/ISA、M:N origins、fusion 不复制 duration、split/消除真实记录 | 未实测 |
| NVIDIA 旧 SM clock/32或43位编码、worker partition；GCU early TTIR/SDK timer 单位和 async；Ascend checkpoint/晚期优化/AIC-AIV epoch | design §8.5/§8.6 明列现状与假设，P01 逐后端真实小纵向检查；不据缺证断言硬件不可能 | 未实测 |
| 时钟端点误差、整圈回绕、跨域比较 | design §6 的不确定区间与有效窗口；E09/P06 | 未实测 |
| 多提交/批量/部分 wait/多消费者及丢记录后的 generation 恢复 | design §8.2/§8.6 集合模型与失效/恢复锚点；P07 明确负例预期，CPU 合同与真实机制分开 | 未实测 |
| 新时间协议不能直接复用旧动态 v1，也不能拿 census v3 结果代替 | design §5/§8.6；P05/testing §8.2 各后端实际发布与物理布局验证 | 未实测 |
| 每 launch 同步破坏跨 stream 提交，或过早回收 pending buffer | design §5 允许安全最终化等待，禁宣称强串行化保持原关系；E01/E03/E05/P10 与 testing §8.2 | 未实测 |
| 能力、事前资格与本次结果混写；缓存查询后才产生依赖 hash | design §8.3 分离三类产物、查询前依赖身份；E07/P02/P10 | 未实测 |
| DTO/扩展过于宽松、导出和规范化共享同一错误、源码导航被升级为执行证明 | design §8.6 冻结类型/基数/引用/未知语义和全部 raw 来源；P04/P08/§8.2；共同 SQL 还须独立对照 raw 与编译对象 | 未实测 |

这些变更是把风险转成可执行检查，不是风险已经消失。只用现有三个后端检验复用；不新增第四芯片、不承诺移植工期、不强制零公共改动或以 LOC 代替正确性。

## 当前结论

三席均已独立有限复核，确认原文档问题关闭，未发现修订引入阻止 P01 的新矛盾；结论为可以从 P01 开始实现，不需再次重写设计。三份最终输入 SHA 与 FOLLOWUP_INPUT 一致。只有用户显式启动 `/goal` 才进入实现；本轮没有启动目标或设备工作，也不构成 timeline 功能验收。

未知必需语义当前采用明确拒绝，可同时满足设计与测试的共同要求；若实现选择保留数据的 partial 路线，小版本冻结必须明确被拒语义、整体 partial 状态与负例预期，不能报 verified 或计作必达资格通过。
