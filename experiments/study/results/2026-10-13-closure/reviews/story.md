# 獨立審閱：故事、邏輯與方法要求

審閱範圍：用戶原始七項驗收、Introduction/Study/Design、region_contract.json/region_plan.py、closure 審計表與選定源碼/LLVM/原始捕獲。未讀其他審閱，未改正文，未 SSH；屬新子代理的獨立任務執行，未宣稱模型誤差相互獨立。採用 academic-research-suite 方法審閱角色，判準完全按用戶要求。

結論：Study 的核心故事已有實證閉環，且沒有用遞推玩具替代真實算子；但不能宣告七項全部完成。内部數值精度仍未核驗，方法狀態與最終實驗記錄尚需收口。這不否定已測得的語義、actor 關聯與協議差異。

| 驗收 | 判定 | 證據與確切邊界 |
|---|---|---|
| 1 固定請求 | 基本滿足 | 同一 logical-region-intervals-v1 的 body/output 控制路徑投影貫穿兩算子三後端；包含 readiness/workspace，保留 actor/launch/端點/單位。Ascend 全局 body 明確不可用，GCU 回放明確不是同一 invocation。需補一張逐後端端點對照表，使「同一邏輯請求、不同投影」可直接審計。 |
| 2 六算子范围 | 滿足 | breadth_reaudit 保留216用例、1620原生區間、1296產物；正文明确速度差異不等於 profiling 缺陷，stages 的實際編譯差異亦有區分。 |
| 3 兩真實案例 | 滿足（研究探針層級） | GEMM+bias+GELU 的 AIC/兩 AIV 映射、源插樁缺失/同槽/錯 wait 邊界，再到晚 LLVM 修復；softmax 單 AIV 成功對照，並與 fused 共同復現 GCU nested counter 問題。兩者沒有被 toy 取代；同一 GCU 缺陷在第二算子重現不等於兩個獨立失效機制。 |
| 4 動態觀測 | 滿足已聲明的量 | Ascend actor-local body/output/wait 及補完成 fence 的分段均有動態記錄；原 issue/gate、靜態依賴與 alias 不冒充 busy time。SDK/global_timer 後續路徑也已嘗試成功。未證實未擾動 busy time 或跨 actor overlap，正文已限制。 |
| 5 受控核驗 | 部分滿足 | 固定16384 NOP、相同 producer fence、相同 AIV 產物與端點，wait 222/367.5/1036 ticks；兩案例端點控制、actor-slot 覆蓋、單 program 隔離及 native 包含檢查支持語義/關聯/粗尺度。内部數值精度無同量獨立真值；GCU 官方頻率也未知，不能把 calibration/containment 當 precision certificate。 |
| 6 方法要求 | 部分滿足 | 三条 requirement 能由 actor 一對多、wait 遺漏和 clock 協議導出；尚缺逐要求完整五段對應與 implemented/validated/pending 標記。Design 仍是 TODO，只能称研究探針验证，不能称生产系统或新 IR 已實現。 |
| 7 交付 | 本審閱不判全滿足 | 新圖和论文 Study 已更新；本審閱已產生。study_experiment.md 仍写「进行中」、global_timer「正在验证」、完成 fence「补对照中」，與現有 final 結果不符。分支提交、另兩份審閱及其問題處置須由主代理最終核驗。 |

## P0：交付前必须修订

1. **明示验收5的未完成部分。** 逐項交付中写「語義、關聯和尺度一致性已核驗；内部區間數值精度未核驗」。列已試路徑：CUPTI/aclprof/TOPSPTI whole-kernel/task、SYS_CNT SDK 單位、GCU train/holdout calibration；失败/不足是参照端点覆盖整个任务，与内部区间不是同量，不能给内部误差上界。无需为了收口捏造额外精度结论。
2. **同步最终实验记录。** study_experiment.md 应记录最后六份 leader-global 捕获、completion-v2 捕获与最终编译/SDK/输入 provenance；移除过时的「进行中」状态，保留失败路径。记录 GCU softmax nested/single-active body=1.239 的扰动与未核验官方频率。结论不得称有用算子优化：固定 NOP 是等待语义控制。
3. **将方法要求写成可审计状态对应。** 至少三行：「fused actor 分裂 → program-only 槽无法识别 subactor → actor/provenance 槽 →64AIC+128AIV 完整覆盖；已实现研究探针、已核验本配置、一般化 provenance 待实现」「wait scope 遗漏 → source boundary 不含 readiness →依赖/完成语义 lowering →固定工作 wait 响应及 fence 对照；通用 pass 待实现」「nested counter overwrite →同一 capture body 丢失 →能力/时钟协议契约 → SDK joint nesting 和扰动/尺度核验；官方频率及跨域关系待核验」。无需扩大到尚未证实的生产设计。

## P1：提高故事可核验性

- 在固定请求后补简短端点矩阵：CUDA/GCU output 的 bias+GELU 或 divide/store 起点，Ascend fused AIV 的原 WAIT 前起点、softmax 的 sum materialization 后 divide 前起点；AIC body 结束于本 actor workspace store 后原 PIPE_ALL，而非整个算子最终输出完成；AIC output 无该区域，明确 N/A。这能避免读者把 actor projection 误读为同一个全局包络。
- 若加入一张结果表，将 generic fused 的 AIC 缺记录、AIV 二写者静态同槽、output wait 遗漏，与 adapter 的身份/边界分别列开。未测混写频率，不能以静态 alias 推导实际 attribution-error rate。
- 保留 softmax 的正面结果：Ascend source 插桩已能满足 body/output；late LLVM 是补细分，不是修复所有后端的共同失败。迁移一个 API 不足的结论与「所有通用 profiler 都失败」应严格分开；当前 caption 已明确未复现 Proton/KPerfIR，保持该边界。
- Introduction 的贡献/Design TODO 仍是计划，不能当新颖性已证据化。设备 AI accelerator 与 profiler 服务对象区分正确；当前正文没有把 AI agent 当测量方法或系统贡献。

审阅未发现需要撤销现有核心实测结果的 P0 证据矛盾。最终可交付为「真实算子 Study 与研究探针的限定闭环」，内部精度、跨 actor overlap、通用生产机制与操作性评估继续明确列为缺口。
