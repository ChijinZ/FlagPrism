# 最终 minor polish 图与版面复核

结论：**保留通过；限定 Study 图验收可接受。没有新增 blocking 或 major。** 本次仅核验最终三张 PNG 和 `main.pdf` 的变更及排版，没有读取 peer 审阅，也没有重新开展实验或完整论文审稿。

用 `view_image` 检查最终三张 PNG，并以 Ghostscript 10.02.1、144 dpi 渲染最终七页 PDF，重点检查 Study 第 3–5 页的实际约 3.3 inch 单栏图。

## 变更核验

- **Case B(b) 标题通过。** `one call/config` 明确每种配置各一次调用，解除原来 `one joint call` 可能使读者误以为 P 与 +K 共一次 invocation 的歧义。共同 SYS 起点的轴标签仍是 `of each call`，与每配置调用内三 actor 对齐的含义一致。
- **P / +K 配置间距通过。** P 组三条轨道整体上移后，P AIV1 与 +K AIC 之间有清楚空白；`16 K iterations` 不再挤进 P AIV1 轨道。配置分隔线接近该标签顶部，但不影响字形识别或组别归属，未发现新重叠。
- **Case B(d) footer 通过。** `Larger MN tile: programs 256 → 64` 与 `Source A/B: 128 → 64 MiB (logical)` 把第二步 tile 变更及实例/source-loading 减少直接连起来，比原来的三配置数列更易理解。logical 限定保留，没有新增物理 DRAM traffic 或分离因果贡献的暗示。
- **关键数值与证据层级通过。** 图内仍为 128/16 K iterations、47.52/23.81、46.72/26.40、vector 0.293 (both)，以及 whole-launch 17.7/310.3/164.1/58.5 µs、5.31×。Source control、independent PMU、held-out whole launch 三层标签保留；不要求补不存在的硬件 busy 流水线。

## 最终版面

实际单栏 PDF 中 Actor 图标题、legend、轨道、数值和新增 footer 可读，没有超出列宽、与 caption 碰撞或被裁切。Figure 4 仍位于第 5 页左栏，紧接第 4 页 Case B 叙述；caption 完整，保持 source body/control positions 与硬件 busy 的区别及 independent replay 限定。Overview 与 Case A 图在第 3、4 页的可读性和就近浮动保持稳定，没有观察到新增排版问题。

Overview 的调用散点和 min–max span 在单栏仍细，属于先前已限定的非阻塞可读性建议；数量级和配置中位数比较可读，caption 的实现/配置迁移边界充分。本次不因此撤销通过。

**Blocking：无。Major：无。新增必修 minor：无。** 保留的验收范围是 Study 图对实现诊断和受限调整结论的表达，不包括整篇论文成熟度、原始数据真实性或通用 profiler 方法验收。

Ghostscript 仍报告 recoverable image error，但成功输出七页；Study 第 3–5 页无可见图损坏。本次未推断该警告原因，不作为 Study 图否决项。
