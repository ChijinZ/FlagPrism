# 獨立審閱一：證據與因果支持

審閱範圍：`study_experiment.md`、`paper/sections/03-study.tex`、四份分析/探針程式、結果 CSV/JSON、部分原始 IR/LLIR 與 result.json，以及五張 PNG。此為獨立子代理的本地證據審閱；未看其他審閱意見，未執行設備實驗或外部文獻核驗。

**判斷：可作為有實證根據的 motivating Study；尚不是新 profiling 方法的正確性或完整 evaluation。** 現稿對同一原語的分開捕獲、探針擾動、未取得內部動態時間線、TCU 既有細節等限制交代清楚，沒有把靜態依賴圖冒充內部時間線。若整篇仍承諾 busy/wait 重建、實例歸屬準確率或適配計時精度，這些承諾不能由本 Study 完成。

## 已直接核驗的支持

- `cases.csv` 有 216 列、`kernel_intervals.csv` 有 1620 列。獨立重新計算原始三後端 full 目錄的 1296 份產物 SHA-256，均與每例 result.json 一致；這支持產物完整性，不等於所有物理語義已核驗。
- 30 列 nested_comparison 的 nested/reference 中位數均重新從所指原始樣本算出，與 CSV 一致。GCU outer 比值為 0.4665–0.4960；inner 為 0.9889–1.0032。V100 outer 約 0.9896–1；Ascend 為 1。此結果足以反駁「所有 begin/end 都可當作互不干擾的時間戳」的通用假設。
- 更直接的 GCU 證據被正文和圖省略了：q64 的原始 nested 樣本 outer/inner start 均為 0，outer/inner end 每次完全相同，例如兩者同為 2212；其他 q 的摘要也一致。q64 單 outer 捕獲則約 4682。保存的 GCU LLIR 仍有兩次 `tops_clock_begin`、兩次 `tops_clock_end`，不是僅從 Python 意圖猜測巢狀调用。這是可加入正文的一句具體協議後果；尚不能僅凭這些資料斷言硬體內部 counter 的確切實作。
- endpoint-v2 的零工作控制確實存在：GCU 無/有末端屏障為 0/240 原生單位；Ascend 為 0/0。Ascend 64 次迭代為 48/96，GCU 為 997/1258。支持「端點約定改變讀數」，不支持從差額中分離等待或宣稱有屏障即真值。
- 固定 GCU 128³、BK32 的 counter-free GEMM 為 1615.859→27.119µs；融合算子為 1650.585→30.031µs。TCU JSON 有四個捕獲各 21 次調用及 per-SIP instances，首調用各 metric 有 24 或 16 個實例；有 device、capture-local ID 和原生單位。此為實際工具提供的豐富觀測，不是 FlagPrism 新創的觀測能力。

## 主要缺口（按影響排列）

1. **「兩個執行差異案例 → 同一請求後果」尚未完全連起來。** 融合案例證明 source region、AIC/AIV 函數與單一原生 task 是不同物件，但沒有向三後端提出相同的 GEMM/epilogue 分區請求、再量化缺失或誤歸屬。巢狀案例則換成另一個 recurrence 探針，且沒有融合內部動態結果。現有證據支持「對象模型必須分開」的設計動機，不能說已實測 source-to-execution attribution 錯誤。正文應把該案例的請求具體化，例如「將 GEMM 與 epilogue 分別歸屬到執行單元」並明示此輪只有靜態映射/可觀測範圍核驗。
2. **巢狀比值不是準確率。** 單區間參照使用相同 vendor primitive、不同執行捕獲。刪去內層 clock 调用會改變編譯和執行；固定 recurrence 和輸出只固定數學工作。現稿 caption 已正確限定，必須保留。仍缺少適配後可巢狀機制及其驗證，不能把此圖作為新方法 accuracy 的對比。
3. **V100 的穩定性在中位數圖中不可見。** 原始 both/outer 捕獲各有早期樣本約中位數的 3.71–3.88 倍，q64 both 首樣本 outer=11808，median=3072。中位數接近 1 的結論成立，但「15 個 prewarmed 樣本都近似一致」不成立。建議補樣本分布或提供 min–max 附圖；不用追補實驗即可誠實展示。不能把這些同 process 樣本畫為獨立實驗的置信區間。
4. **TCU panel 不能給出性能因果歸因。** 目前把約 60 倍改善與效率改變並列，讀者易推斷某 instruction family 是瓶頸。tile 改動同時改變 grid、資源與編譯路徑；TCU 和 counter-free 是分開捕獲，且首 21 次含 warmup。只能支持配置介入與不同原生細節的共同觀察，不能用 MSF 或 1D 百分比差額證明等待、利用率真值或速度改善原因。現稿最後一句「not a complete bottleneck attribution」合理，但建議正文直接給出可回答/尚不能回答的具體問題。
5. **breadth 中的配置不等價。** README 已承認 Ascend stages 改變雙緩衝，而 GCU 三組 GEMM final binary pair 相同。六面板可以展示各完整 backend stack 的差异，不應以 v0/v1 視覺平行性暗示相同硬體控制干預。主文/圖注可增加一句配置屬 source request，實際是否生效由產物核驗。

## 故事及圖形

- 六算子分布圖完成「不是單一孤例」的工作；它沒有證明 profiling defect，正文已守住這條界線。但 large/shape、v0/v1 的具體含義全在 artifact，正式正文最好留一行緊湊配置說明。
- fused-decomposition 是清楚的靜態映射圖。AIC→AIV 箭頭表示已見 set/wait 依賴，不應再加未量得的 busy/wait 長條或並行時間軸。PNG 中 sync 文字與箭頭略重疊，可小幅排版改善。
- nested-semantics 是五圖中最強的問題證據。可加一個 GCU raw start/end 小註解，讓「通用 subtraction」具體可理解；應同時交代 V100 尖峰。
- endpoint-control 的 1024 點把低工作量和零工作差異壓縮到軸底，建議用差值 panel 或 inset 突出控制結果，仍保留原生單位。
- native-detail 大部分 21 點重疊，per-SIP 異質性沒有在圖中展示。保存 per-SIP 結構是優點，但圖目前只展示 invocation aggregate。若以此支撐「保留 instance detail」要求，最好增加一個實際 per-SIP 分布例子；不能說這張圖本身已顯示實例歸屬機制。

## 下一步的邊界

可立即透過文字/排版改善完成：給融合案例加具體請求、加入 GCU raw 值、呈現 V100 波動、說清配置生效差異、突出 endpoint 控制。要升級為方法/evaluation 則需新的實作與測量：適配巢狀機制及參照、融合內部動態/映射驗證、跨記錄關聯與歸屬誤差。三個現有設備不證明同 SIMT 多廠商，TCU 既有能力不應被寫成新方法貢獻。
