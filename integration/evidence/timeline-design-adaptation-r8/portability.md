# 独立评审：抽象、适配与 Perfetto

评审者：`/root/timeline_design_review_portability`；GPT-6.1-Sol / xhigh / fork none。只读审阅，无设备运行。以下为评审返回意见，协调者修订见 README。

总评：**有条件可执行**。未发现已确认的 P0/P1 设计阻断问题；条件是三后端须用真实纵向样本证明边界、发布、时钟及异步机制，设计评审不能授予这些资格。

- P0：无。
- P1：无。未把尚未实现的 ns 视图、Perfetto exporter 或 GCU/Ascend 默认入口当作设计缺陷。
- P2-01：实施总顺序有轻微歧义。设计 §11 写成“三后端自动采集→动态依赖→Perfetto exporter”，容易理解为先铺三后端、最后验证公共导出；而 §8.9/§8.10 要求先完成首后端纵向链，再复用到其余后端。建议原位引用 A/B/C/D，明确首后端先到 C、冻结实际小合同，其余后端可先调查 A。

抽象边界合理：compiler、transport、decoder、clock、mapper 按实际变化原因拆分，允许函数组合、不同物理 ABI 和合理公共版本扩展，没有统一硬件 IR、预建插件平台或第四设备要求。主体模型保留 program、observer、operation、resource 及多对多依赖，能容纳非 warp 架构。适配成本仍包括编译开放程度和设备取证。

数据交接总体闭合：manifest、invocation、raw、canonical、proof 及最终落盘要求覆盖主要交接；raw 先持久化、owner 安全回收与解码成功分离合理。抽查 timeline_events.py、timeline_events_nvidia.py、timeline_clock.py，现有实现保持未认证状态和独立域，未偷偷继承共享 epoch。首条真实链冻结 schema 时仍须固定 raw 域到派生 ns 坐标的映射实例。

Perfetto 方案可执行：独立时钟分文件、嵌套 pair 晚提交、独立 in-flight 轨道、稳定 ID 和源码详情均已有处理；嵌套 fixture 要求真实 Trace Processor，真实设备 trace 另需 SQL 和 UI，不以 protobuf 可解析代替可用。

验收区分 fixture、旧 raw、advanced 与新默认 producer；默认首末 program、逐 observer 实际事件、guard、最终磁盘引用和失败恢复独立判定。P07 物理复用证据与既定目标一致，不要求原生引擎 busy 或第四芯片。

建议最小验证（复用现有门）：

1. 每后端一条普通 runtime 循环纵向链：首末 program、真实区间、发布/guard、本地 ns、公共 pftrace 与 Trace Processor。
2. 每后端一条普通异步样本：两轮真实复用、动态覆盖及所需时钟，未知保留 unknown。
3. 嵌套 pair fixture 验导出投影，三后端真实 canonical 走同一 exporter/SQL。
4. 固定原件测试错范围 proof、首 decode/export 失败与重导，核 SHA、后续原件、owner 和应用次数。

## 修订后有限复核

原 P2 顺序歧义已闭环，§11 与 §8.10 一致。另发现新增“已确认安全的 scratch 可回收”与 §8.7 持久化后回收策略有歧义，建议限定“完成已确认且原件与关联快照安全持久化的 scratch 可回收”。协调者已逐字采纳，并明确后续重试不因保留 host bytes 重新占用 device buffer。其余补充未见明显新矛盾，预算范围与未实现声明明确。仅只读复核，未运行测试。
