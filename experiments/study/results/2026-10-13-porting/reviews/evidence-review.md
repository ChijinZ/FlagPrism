# 最终 Study 证据复核

结论：**维持对限定 Study 范围可接受的判断。新 Blocking 0、新 Major 0；round 2 提出的三个 Minor 均已解决。无必须补做实验。** 此判断不扩展为完整 OSDI、设计机制、通用 profiling IR 或生产映射能力验收。

本次只核验最终冻结 tex/Actor PNG、compact README、holdout sidecar 和 Actor data JSON 的最后修订；未阅读 peer review，未重跑全量原始审计或 GPU/远端实验。此前独立核对的 9,720 native 区间、输入/配置身份、两案例恢复、joint SYS 与 PMU 边界继续作为判断基础。本地 PDF 抽取组件缺失，仍不对 `main.pdf` 排版或内容一致性作独立认证。

1. **README 同步因果措辞已修正。** 现在写明 two-item control 只说明 barrier presence alone 不能解释 slowdown，并保留 worker-dependent synchronization cost 未分离。消除了“所有同步成本已排除”的过强解释。
2. **LLVM 一致性层级已修正。** 现在写 `P/R_K saved AIV LLVM is byte-identical`，与已核对原始 LLVM 哈希对应；没有扩展为机器码一致。
3. **holdout 引用已修正。** README 直接链接 `ascend-diagnosis/holdout-provenance.json`，明确原始 stale exploratory scope 保留及 sidecar 不重建精确冻结时间。sidecar `identity_reference` 已采用实际 `frozen_N_provenance` 字段。原始 scope literal 和 SHA 引用仍保留。它是身份审计，不是 freeze-before-capture 精确时序证明；当前 Study 没有提出后一项额外主张。
4. **最终 Actor 图没有扩大证据含义。** 标题现在为 `one call/config`，更准确表达 P 与 +K 分别来自各自一次 joint capture。轨道空白避免迭代标签与 actor lane 混淆；footer 将较大 MN tile 的 logical programs 256→64、source A/B 128→64 MiB 对齐到第二阶段。图中 latency、PMU 和迭代计数与此前核对值一致；图标题保留 program 0、independent PMU 与 no probes。未引入“占用率”“同调用 PMU 拼接”或 launch critical path 主张。
5. **数据口径明确。** compact `figures/study-actor-case-data.json` 的 `latency_statistics` 明确 NVIDIA 为三批中位数的中位数，target 为 pooled 90-call median；这解释 NVIDIA 17.728 μs 与 pooled 17.696 μs 的区别。`derived_source_work` 保留每配置 program/actor 数和逻辑 A/B bytes，且 `scope` 明确 source control、warm-up 0 joint replay、独立 PMU overlap 和 uninstrumented heldout latency。无需为了统一这两个描述统计量补实验；后续引用应沿用已声明口径。

冻结 `final/03-study.tex` 与 round 2 tex 字节一致，故 barrier presence、worker-dependent sync、LLVM 非机器码保证、program 0 非 launch critical path、PMU 独立 replay 等关键正文限定未被最后 polish 撤销。当前证据足以支持“后端执行细节产生配置假设，目标 native 复测验证恢复”的限定结论。
