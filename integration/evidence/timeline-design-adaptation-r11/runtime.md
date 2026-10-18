# 时间线设计 r11 独立评审：运行时与整体可实施性

评审时间：2026-10-18。结论：**方案有合理、可实施的工程路径，可以继续按 A/B/C/D 推进；未发现确认的 P0/P1 设计阻碍。** 这不是当前实现通过、三后端设备可行性已证或最终代码验收的结论。唯一确认项是非阻断的验收措辞歧义，见 R11-RT-01；其余均明确列为实施差距或待设备取证风险，不据此否决设计。

## 评审范围与独立性

- 完整阅读 `Profiler/docs/timeline_design.md`（560 行）与 `Profiler/docs/timeline_testing.md`（333 行），重点审查新增设计 §0.4、测试 §0.1，并与 §4–§10、P01–P10、E/C 及测试 §8.1–§8.9 交叉核对。
- 只读核对实际源码：`timeline_runtime.py`、`hooks/timeline.py`、`timeline_cuda_runtime.py`、`timeline_storage.py`、`timeline_enflame.py`、`timeline_ascend.py`、`timeline_store.py`、`timeline_reexport.py`、`timeline_unit_nvidia.py`；按需要查看了 `timeline_views.py`、`timeline_perfetto.py` 的实际接口和消费位置。没有执行产品 import、测试或设备程序，没有连接服务器。
- 未读取同轮其他 reviewer 的报告；没有修改设计、产品或测试。本文仅为独立设计评审。
- 参考工作树 HEAD：`b1024ffcecf2f522a2626310108de385e637e150`。文档身份以实际文件摘要为准，不把 HEAD 当成工作树字节证明：
  - design SHA256：`b5bed8c36a9a7e89470fd422826bba5e91e34e1abe1ce8f590396d23891d7773`
  - testing SHA256：`2aee7dca7b0660dd4284e6f339f3345888f4405bc5ce7054d106d861694d35a0`

## 确认问题及最小修复

### R11-RT-01 — P2 / 非阻断：新验收摘要中的“唯一 writer”应限定到记录所有权

**章节与位置：** 测试 §0.1“布局与主体”（`timeline_testing.md:30`）；对照设计 §5（`timeline_design.md:153`）、§8.1（`:225`）、§0.4（`:60–64`）。

**问题：** 新摘要要求“精确 raw offset 与唯一 writer 有来源”，而设计允许真实多写者采用经证明的发布协议，且不统一各后端物理布局。这里没有说明“唯一 writer”是每条记录/slot 的独占所有权，还是整个 ring/header 只能有一个写者。若按后者执行，会给合法的多写者 ring、原子保留 slot 或共享发布计数器增加与主体设计不一致的限制。现有单写者/actor 分区路径不受此歧义影响，因此不构成当前三后端设计阻碍。

**最小修复：** 将该半句限定为“每条记录/slot 的 writer 所有权及精确 raw offset 有来源；存在多写者时，另有实际 reservation/commit/可见性证明”。复用 P05 的发布证据判定即可，无需新增芯片、数学样本或测试矩阵。

**判定边界：** 这是确认的措辞歧义，不是已发现产品发生多写者竞争，也不是认定现有发布协议已通过。

## 核心职责及可实施路径

| 审查点 | 结论及依据 | 实施验收的最小落点 |
| --- | --- | --- |
| 新型号工作包 | §0.4 的五行是接入工作，不是五套框架。编译/记录、提交回收、物理解码、时间/异步解释、公共消费的复用前提分别列出；与 §0.1 五部件一致。工作包把 clock 与 mapper 合并叙述，没有要求二者一起替换，§8.10–§8.14 明确可独立组合。 | 测试 §0.1 接入清单、P09 的实际调用链与 diff，可由三后端既有证据承载。无需第四设备或空 adapter。 |
| admission 与 owner | §0.2、§8.7、§8.13、§10 区分编译布局公式、实际 launch 值、单次/live/cumulative 额度；admission 先于初始化或 launch 副作用。owner 保持各次快照，不能由后续 launch 覆盖。 | `TimelineOwnerPool.prepare/allocate/mark_submitting` 已有可用落点（`timeline_runtime.py:97–186`）；累计额度和完整资源闭包仍需实施，不能把目前 pending pool 当成已完成。 |
| 异步访问与安全回收 | 初始化、kernel 写入、D2H、host staging/native/context 生命周期都在责任范围内；完成证明须覆盖全部访问。提交不明、超时、异常不等于完成。安全原件持久化后的释放与 decode/export 成功分开，不会强迫导出失败永久占用 device scratch。 | 测试 §8.3 初始化部分成功等阶段、§8.8 资源集合和 ready-owner salvage、§8.9 留存/release 故障已有针对判定；不必新增生命周期框架。 |
| 无逐 launch 强同步 | 主线允许原 queue 上轻量完成条件，host 继续提交；只在收尾等待本次完成。无法支持的并发路径在首次副作用前拒绝，冻结后不能缩分母。设计不把两流强加给所有后端。 | E03 与测试 §8.3 的真实交错提交；记录 launch/host wait 顺序，CPU fixture 只补状态机。 |
| 发布与坏 raw | 字节取得、guard/header/commit 合格、writer 到达、端点存在是不同事实。先留存实际 bytes/guard/关联，再解释；读回损坏不该退化成丢证据的 `read_failed`。 | `TimelineReadback` 已能同时返回 bytes 和 integrity 错误（`timeline_runtime.py:20–38,278–306`）；`_retain_timeline_original` 与 `_decode_timeline_original` 已有先留存后拒绝的实际调用顺序（`hooks/timeline.py:210–288`）。GCU 等具体发布/guard 仍须实证。 |
| 离线和派生版本 | §8.14 的输入闭包、canonical revision、proof 内容身份、不可变结果、完成收据和有界 OS 锁形成可落地方案。更新成功索引允许原子替换，与原 raw/首次结果不变不冲突。合法补证不要求重跑应用。 | `timeline_store.py:68–139,204–274` 已提供有界锁和收据提交原语；`timeline_reexport.py:68–221` 有保存原件重读的实际入口。测试 §0.1 和 §8.9 能验跨进程、无原 cache/source/owner 依赖。 |
| 时钟资格 | 单位、读取/转换精度、源边界、epoch 比较、动态依赖分别授予。整数换算、独立有效窗口、整圈回绕歧义及近边界误差均有规则。当前 schema 的保守拒绝与后续从同 raw 升级不矛盾。 | P06/E09、测试 §8.6/§8.7/§8.9 已区分物理证据与算术 fixture。单位成立的 counter-ns 不能填成源 elapsed 或跨主体通过。 |
| Perfetto | exporter 只消费已获资格的派生数据；未对齐域分文件。晚提交外层 pair 保 canonical 原顺序，导出允许独立投影，避免误用 B/E 栈。SQL、真实 UI、来源可读分别验收。 | 测试 §7、§8 与 §8.7 嵌套 pair 实际 Trace Processor 检查足以验协议；不能以 importer 返回 0、能打开文件或局部 counter UI 替代内容资格。 |

## 当前实现差距与待取证风险

下表的优先级用于实施放行，不是“确认设计错误”。没有真实设备结果时，不将风险升级为芯片/SDK 的硬阻碍。

| ID / 优先级 | 性质、具体风险及位置 | 最小下一步；完成前不能声称什么 |
| --- | --- | --- |
| RT-I01 / P1 实施合同 | 当前公共 `TimelineOwnerPool.prepare` 仍显式收 `function/stream/device/num_ctas`，且 `stream` 必须为非负整数（`timeline_runtime.py:97–122`）。GCU/Ascend 已使用实际 executable 字典和 `num_ctas=None`（`timeline_enflame.py:157–167`、`timeline_ascend.py:190–207`），说明没有必要编造 CUDA function；但尚不能据此声称公共 runtime 接口对任意非整数 queue/context 都已通用。 | 遵守设计 §0.1/§0.4/§8.13：出现真实需要时抽取 executable/context/queue 的后端输入校验和运行时引用，公共 owner 只保身份、预算和状态。用 P09 实际调用审计验证，不预建新层次，也无需第四设备。现设计已经允许必要公共修改。 |
| RT-R02 / P1 设备取证 | 完成 event 是否覆盖初始化、真实全部 actor 写入及 readback，是否保持原 queue 提交关系，取决于 SDK 实际语义。存在 event/query 调用并不证明这一点。GCU 返回旧 bytes 型 readback、默认未附 allocation guard（`timeline_enflame.py:109–125`）；文档已经承认 guard 等仍缺，不应把有限 raw 成功扩成 P05 通过。 | 先用已有普通多调用样本保真实 stream 初始化→launch→完成→读取顺序及 guard，再按 §8.3/§8.8 注入可控阶段故障。无须制造 driver 硬故障。完成/guard 证据未齐时保 raw 与未通过项。 |
| RT-R03 / P1 设备取证 | 三后端的最终区域边界、GCU/Ascend 时间尺度与跨主体比较、真实机制闭合/两代复用仍是核心可行性风险。通用 owner、decoder 或 exporter 不能弥补这些事实。 | 严格复用 A/B→C 最小 loop + ordinary async 样本；先核最终对象，逐项区分实现缺失、待证和已实证 SDK 限制。P01/C 未通过不扩全量资格，不因为两个计数点有正 duration 或 group ordinal 正确而放行。 |
| RT-R04 / P2 收尾验证 | 共同 deadline 的轮询与阻塞 SDK/readback/fsync 边界必须实测区分。当前 runtime 注释也承认 Python polling deadline 不能中断卡住的 driver call（`timeline_runtime.py:45–50`）。`_RETAINED_POOLS` 仅保证存活 Python 进程中的 owner，不是进程终止后的设备资源收据。设计没有承诺恢复硬件挂死，因此不能由此判定方案不可行。 | 在现有 E05/§8.8/§8.9 证据中写清：正常收尾 deadline、外层 CLI 超时、进程退出后的 runtime/context 处置分别由谁负责，逐项报告 actual state。受控 query unknown 只能证明 salvage/隔离合同，不能宣称 SDK 卡死或强杀后的设备恢复已验证。无需增加真实硬故障测试。 |
| RT-I05 / P2 发布实施 | 当前原件留存 `_persist` 与派生 `timeline_store.persist` 是不同路径；原件路径尚不能仅因派生收据原语存在就声称满足 §8.14 的输入闭包提交、全部目录 fsync 和部分 release 恢复。 | 直接在已有 §8.9 捕获留存/fsync/rename/release 注入里验实际完整闭包与重试；补齐缺失机制即可。原件闭包未完成不发布完整收据，不要求 decode/export 才能回收已安全持久化的设备资源。 |

## 整体合理性、过度设计与放行建议

新增 §0.4 和测试 §0.1 改善了实施可定位性：要求真实函数/安装版本、actual source↔site/actor、两调用生命周期、真实保存 bundle 和公共消费证据，不再把一个 adapter 名称当成果。普通输入超出多函数/auto-blockification 范围仍登记产品缺口；没有把一次编译偶然性固化成跨型号 ABI。对未来芯片没有承诺固定工期、零公共 diff 或 CUDA 句柄形状，边界合理。

没有发现要求统一设备物理 ABI、统一 ISA、任意机器码证明器或全排列兼容系统的隐性工程前提。§8.9–§8.14 与测试 §8.4–§8.9 的重复确有阅读成本，但新增导航明确它们是既有门的索引，并要求沿用同一工程记录；执行时不应据每一行再建一套接口、状态文件或独立数学。这是维护成本，尚不足以作为 P1/P2 正确性问题。

建议按当前设计继续实施，顺手修 R11-RT-01。优先关闭 RT-R02/RT-R03 的最小真实证据链；RT-I01、RT-I05 随现有调用共同修正，不等待搭框架。RT-R04 在既有 timeout/cancel/recovery 记录中明确证据强度。三后端、独立资格、Trace Processor/UI 和后续三名最终代码 reviewer 的门均维持原要求，本次不填任何设备通过列。
