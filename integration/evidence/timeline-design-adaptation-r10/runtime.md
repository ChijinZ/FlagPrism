# r10 独立设计评审：运行时、发布、恢复与时钟

评审日期：2026-10-18。角色：独立设计 reviewer；不是实现或代码交付验收。

请求模型：GPT-6.1-Sol，xhigh。当前执行环境未暴露 resolved model，故实际解析模型未知，不将请求值当作运行事实。

## 范围与结论

完整阅读 `Profiler/docs/timeline_design.md`（542 行）和 `timeline_testing.md`（317 行），重点审查 §0；只读核对 owner、NVIDIA/GCU transport、留存、raw schema、时钟算术及 Ascend 旧事件原语。未读其他 reviewer/旧评审，未 SSH、import 产品或运行产品/设备测试；未将未跟踪的 `AscendTimeline.h` 草稿当作实现。

**结论：设计合理，具有条件可实施性；未发现 confirmed P0/P1 设计错误。** transport、decoder、clock provider、mechanism mapper 与 compiler hook 按真实变化原因分工，公共 owner/validator/exporter 不必继承 CUDA 句柄或拓扑（设计:21–37、459–471、483–501）。目标变化不必导致全链重写，也不承诺只改配置即可。

这不是设备可行性通过结论。源区域耗时与异步图仍取决于编译边界、发布、真实复用身份和目标端点所需时钟证据；设计允许保存 partial，但不计完整 P01/交付（设计:292、322、380–393、505；测试:158–169、238、308–311）。

## Confirmed P0/P1

无。Ascend 新 producer、GCU 时钟/guard/异步、NVIDIA 源边界等尚未实现或取证，文档已如实列出；这些不是自动成立的设计缺陷。

## 关键设计判断

1. **发布协议可异构。** 设计:135–137、207、357、461–475 区分 header、writer 到达与 commit，并保留 cache-line/alignment、写址与 loss 单位；无需统一物理布局。

2. **取消恢复有界。** 设计:286–290、467–471 覆盖初始化、kernel、D2H/staging；未知完成者隔离，完成且输入闭包已留存者可回收。共同 deadline 不保证任意数量 owner 全保存，重导不重放应用。

3. **单位不替代时间比较资格。** 设计:143–157、364–378、411、488–495 分开单位、误差、边界、epoch 与关联；近边界按端点不确定区间判定。有限校准不冒称普遍误差上界，补证保留旧原件与派生历史。

4. **无需插件平台。** 设计:29–31、231–235、407、419、503 只抽取真实共享行为，允许因新事实修公共版本。三后端复用证据不等于第四架构可行；现有 §0/P/E 足够，不需新矩阵。

## Verification gaps：实施前后需完成的既有取证

以下是条件可行性的边界，不是 confirmed 缺陷，也不是新增测试要求。

| 待证事项与触发 | 文档依据 | 最小修订 | 复用既有验证动作 |
| --- | --- | --- | --- |
| **发布/读取。** Ascend 新 producer，或 publisher/layout/目标内存语义变化；GCU guard 待证。 | 设计:177、207、357、461–475；测试:162、178、278–280、284 | 无；既有清单填写发布指令/作用域、写者与完成/可见性条件。 | 复用 A/P05/E08 最小 runtime-K：核首末 observer commit、地址范围、guard、实际对象。旧 census/host header 不替代新发布证明；损坏负例用 fixture。 |
| **完整资源完成。** 初始化部分提交、提交不确定、D2H 异常、release 部分成功或 queue/context 变化；kernel event 不自动覆盖后来传输。 | 设计:286–290、467–471、499–501；测试:194、265、283–287、306 | 无；transport 完成收据覆盖真实访问集合，逐子资源恢复。 | 复用 E05/P10 阶段 fixture 和真实正常队列链；A unknown/B ready 保 B 有限 salvage。SDK 阻塞用外层进程 deadline，不能以 Python 线程取消证明设备已停止。 |
| **尺度/跨主体时钟。** getter、epoch/reset/window 或待比较端点尺度变化。 | 设计:149–157、373–377、411、488–495；测试:163、248–249、267–268、299–300 | 无；填 proof 的范围/未知误差，不可分辨时保逻辑依赖、异步门未通过。 | 复用 P06/E09 及每后端真实异步样本：分别核 getter/位宽/比例、独立窗口、epoch/offset、读取误差；保留轮次只支持实际覆盖范围。正 duration/同频率不代替端点资格。 |
| **磁盘闭包/离线恢复。** 关联文件留存失败、reader/provider 升级或原目录消失。 | 设计:431、464、497–503；测试:282、301–307 | 无；沿既有闭包列必需文件，缺失事实明确报错。 | 复用新进程公开重导、原缓存/目录不可访问、摘要重核和 fsync/rename/release 注入；新 revision 保旧结果，只补缺文件/派生物，无应用重放。 |

## 源码交叉核对及其限度

- `Profiler/python/flagtree_profiler/timeline_runtime.py:97–179,199–321` 有预算、先接管后初始化、abort 完成证明与 readback 重试落点。当前整数 stream 限制（:111–114）需要随实际新后端改接口；设计:467 已明确允许类型化封装，不要求伪造 CUDA 值。
- `timeline_cuda_runtime.py:22–70`、`timeline_enflame.py:69–120` 是不同 transport 调用者；`hooks/timeline.py:209–263,377–419` 将留存与 decode 分开并先看就绪 owner。源码支持职责可落实，不认证 SDK 可见性。
- `timeline_clock.py:62–89,107–161` 有窗口/端点误差算术；`timeline_views.py:105–141` 保未知精度、禁时间箭头。`Profiler/llvm/AscendLateObserver.cpp:49–115` 的旧 volatile payload/cursor 与 `SYS_CNT` 不能证明新 producer 的发布。设计:261、302、437–439 已保此缺口。

## 可选建议与已澄清项

§0:7 原“先完成三个后端，再抽取”有顺序歧义。root 已原句改为“先推进三个实际后端的功能，随真实调用形成抽取公共实现”；已复核，与设计:48、231、328 一致，**已澄清，不再 pending**。无需新章节/用例。

没有其它阻止实施的修订；直接按 A/B/C/D 最小链推进，在现有清单补证，按原 P/E 判门。

## 评审快照

- 仓库 HEAD：`8e91da356946263055dfc8ffeae15ff365c78d1c`；评审针对当前未提交文档更新。
- `Profiler/docs/timeline_design.md` SHA-256：`45d9c02808115f2aa71ec7670662a13c3e03e73ecf4c9843bccafb2612f81745`。
- `Profiler/docs/timeline_testing.md` SHA-256：`fa300abc858a268e0f8fbd8ed1cdffa18bb3fdb6caede72ec0a903028af8df87`。
- 只新增本报告；未修改产品、设计或测试。本结论不授予设备/P01 通过，也不替代实现与真实验收之后额外三名最终代码 reviewer。
