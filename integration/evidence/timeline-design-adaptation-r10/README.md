# R10 时间线设计与验收独立评审

本轮只更新工具设计、验收入口、执行合同引用和评审证据。产品参考 HEAD 为 `8e91da356946263055dfc8ffeae15ff365c78d1c`；未运行服务器实验，未修改论文或 Study。先前未跟踪的 Ascend logger 草稿保留原样，不纳入本轮提交或可行性证据。

## 文档入口

- [技术设计 §0](../../../Profiler/docs/timeline_design.md)：五类可替换部件、输入输出、错配阶段、独立时间资格、A/B/C/D 开发与放行顺序。
- [验收 §0](../../../Profiler/docs/timeline_testing.md)：用既有 P/E/C 场景核实际 writer、部件组合、公共消费、编译扰动、owner/重导、异步两代复用及受影响回归。不增加独立数学数量或第四芯片。
- [执行合同](../../plans/timeline/goal_prompt.md)：引用两个入口；与工作区根文件同字节。

## 独立评审与结论

三位均以 fresh context 独立阅读全文和必要只读源码；初审不读取同轮其它人的报告。三位都评估整体合理性与实际可行性，再分别侧重编译、运行时和可移植性。请求配置均为 `gpt-6.1-sol / xhigh`，tool 未暴露 resolved 型号，无法额外核实实际解析结果。

| Reviewer | 主要判断 | 报告 |
| --- | --- | --- |
| timeline_design_r10_compiler | 职责划分合理，有条件可实施；未确认设计级 P0/P1，最终编译边界及 ordinary 关键阶段保持仍需实际对象证明 | [compiler.md](compiler.md) |
| timeline_design_r10_runtime | 无确认的设计级 P0/P1；发布可见性、完整资源访问的完成条件、时钟可比性与恢复须按既有门取证 | [runtime.md](runtime.md) |
| timeline_design_r10_portability | 五部件/非 CUDA 合同与公共消费边界合理；三真实后端可检验复用，不能外推第四芯片已支持或固定适配成本 | [portability.md](portability.md) |

共同结论是**设计合理，具备条件可实施性，可以进入实现；三后端完整功能的实际可行性尚不能仅凭设计确认**。没有已证实的架构性硬阻碍，不意味着编译/SDK、发布或 clock 的风险已经消失。

## Root 处置

- **实施顺序措辞：已修。** §0 首句改为随真实调用形成抽取公共实现，避免被读成三个后端全部完成后才允许共享。与首后端纵向链形成后冻结小合同、第二/第三后端复用的顺序一致。
- **接口和测试膨胀：不再增加。** 本轮只整理 §0 导航和既有 P/E/C 的入口；五类职责可以由现有函数组合，不先建插件平台，不把历史细化当成多套重复门槛。
- **硬件与编译取证：保留为实现条件。** 当前 raw/counter-ns/UI/离线重导的有限成果不填满源边界、epoch、真实异步及 Ascend producer。各项直接落到已有 P01–P10/E/C，不再新建矩阵或进度表。
- **适配成本：按实际复用范围报告。** 不要求零公共变动；公共 schema 不能表达新事实时版本化扩展并回归。注册层的后端分发是合法选择，不等于公共 exporter 解析厂商 ISA。无第四设备不承诺第四设备成本或可用性。

初审输入及请求见 [request.json](request.json)，顺序澄清后的输入见 [clarification-input.json](clarification-input.json)，最终文档摘要见 [final-document-sha256.txt](final-document-sha256.txt)。报告保留各 reviewer 自己的意见；root 不用多数意见豁免任何实现或证据缺口。

**设计评审不授予设备、P01、SQL/UI 或代码验收资格，也不替代实现完成后额外三个独立最终代码 reviewer。** 本轮只做字节一致、相对文件链接及 Git diff 检查，没有运行产品测试。
