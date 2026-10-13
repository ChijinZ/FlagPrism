# 最终 minor polish 核验：Study 故事

**维持限定 Study 通过；没有新 blocking/major。** 本次只核验最终版 `03-study.tex`、actor PNG 和 `main.pdf` 第 5 页实际渲染，未读取 peer，未重新开启完整审稿或实验。

- 图 4(b) 的 `one call/config` 消除了把 P/+K 当成同一次 invocation 的标题歧义，与图注“每个配置一次实际 joint capture”一致；同配置内部的三 actor 关联仍明确。
- P 与 +K 间新增空白有效。“16 K iterations”现在对应 +K AIC，已经不挤在 P AIV1 上；单栏 PDF 中也能区分两组。此前标签位置的 minor 已解决。
- 图 4(d) footer 把较大 MN tile 与 programs 256→64、source A/B 128→64 MiB（logical）直接关联，能更清楚地提示第二阶段涉及实例数和逻辑 loading 的变化。它没有把 logical payload 冒称物理 DRAM 流量，也没有把第二阶段收益冒归因于进一步降低局部 wait。结合正文“program 0 wait 未进一步显著下降”的明确限定，图内归因提示已足够。

正文的证据与限定保持成立：A 只能支持 worker-dependent mapping、资源及同步成本共同变化的机制，PMU 是 characterization；B 的 program 0 依赖证据与 whole-launch 两阶段恢复分开；普通 timing search 仍可调参，Proton/KPerfIR 是 NVIDIA 信息参考；profiling 服务由后端细节与源程序关联需求引出。以上 polish 没有引入新的因果过度宣称。

此前对提纲式箭头叙事、overview sanity check 叙事重量的建议仍属于可选编辑 minor，不影响本次限定 Study 接受。**无需新增实验，也不因未完成的设计、实现或部署 TODO 撤销 Study 通过。**
