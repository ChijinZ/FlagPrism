# R2 runtime 独立设计评审（round3）

结论：**有条件可实施**。公共意图→后端晚期 manifest/物理记录→公共验证→Perfetto 的划分合理；没有发现必须推翻该架构的 confirmed blocker/major。timer、epoch、真实异步及发布可见性仍有决定性的设备验证条件，不能将本结论读成三后端已可交付。现有缺少 timeline 入口、紧凑存储或 owner 实现本身不是设计错误。

本评审是设计可行性评审，不是最终代码验收；没有运行测试/import/build、SSH、设备或浏览器，也没有读取 peer/旧评审。仅写本报告。

## 输入冻结

完整读取三个输入，计算 SHA-256 均匹配 `round3/INPUT.json`：

| 输入 | SHA-256 |
| --- | --- |
| `Profiler/docs/timeline_design.md` | `dc26b5fb008bea5e608bb13b19ee08da1037b7fa02a38a4dcef041bb8e3c79f1` |
| `Profiler/docs/timeline_testing.md` | `ab727c20da1e2907d8be77302850bc293407b15e212291edba35e58224b6cb87` |
| `integration/plans/timeline/goal_prompt.md` | `51db449f2898ad695f8557a3d83459cf476c57cec27198743ba481193e12a054` |

INPUT 标注基线 `34b04624098b99b2004f9b0e9cf1c602db5509cf`。以下判断以冻结文档为对象，源码只用于检查候选路径是否有落脚点，不把源码阅读当作设备证明。

## Confirmed findings

- **Blocker：无。** 未发现合同要求在逻辑上无法同时满足或必须采用伪时间/伪关联才能实现。
- **Major：无。** 三后端是否实际满足硬门槛尚未知，但文档已将这些情况定义为 P01 前置条件，而非提前承诺通过。
- **Minor M1：逻辑组数据合法性与完整异步资格之间，仍有一句可造成验收歧义。**
  - 位置：design §7、§8.9（尤其第274行）正确允许逻辑 commit-group 缺少物理 buffer；testing §5 第68–70行及 P07 第146行明确要求每后端真实两轮 in-flight/buffer/flag 复用；testing §8.4 第196行却写“声称 buffer 复用的真实案例仍须两轮代际证据”。
  - 触发：后端仅有完整 commit/wait 逻辑组流，buffer/flag 生命周期不可观测，实现者据后一句将两轮复用解释为只有主动声称时才需要，进而把逻辑组图直接计入完整 P07。
  - 影响：无法从同一套文字唯一判定该样本是合法的阶段性逻辑组结果，还是已经满足真实复用验收。不是说逻辑组边错误，也不是要求给不可观测 buffer 编造身份；问题是资格等级的措辞。
  - 修正：明确区分两层：逻辑组数据可独立合法保留；完整异步资格仍须满足既有 §5/P07 的真实两轮 buffer/flag 生命周期门，若同一例子缺少该证据则另取真实样本或保持该门未通过。若原意是允许逻辑组单独替代此门，需要显式修订执行合同，不能由“可空”字段或 conditional 句隐式获得豁免。
  - 最小验证：资格表分别列 `logical_group_association` 与 `real_reuse_lifecycle`，给 group-only/unknown-buffer fixture；前者可通过，后者不得自动通过。真实设备复用证据另验。

## timer、epoch 与时间语义

设计 §6 的原 tick 保留、先整数减 origin、独立回绕窗口、单位与 epoch 分证、端点误差判定是正确的。尤其 end≥start 仍需排除整圈回绕，防止常见的“看似单调便安全”。未连接域分 trace 是诚实降级，并且文档没有把降级当作完整异步资格。

`timeline_clock.py` 明确只证明算术，不证明物理时钟；`TargetInfo.cpp:13–37` 的 `%globaltimer` 分支只是候选 getter；`timeline_nvidia.py` 保留完整64位记录并不证明它的频率或跨主体 epoch。这些边界与设计一致。`ascend_clock.py` / `cann_source_clock.py` 也明确没有凭频率建立共享 epoch。

设备条件及最小实验（均未运行）：

| 条件 | 最小实证与失败处理 |
| --- | --- |
| NVIDIA getter 的目标语义 | 在实际 RTX PRO 6000 上编译带真实数学的两区间/运行时 loop，保 PTX 和最终对象 getter、位宽、边界及 raw；以独立计时锚点检验尺度/分辨率。若 async 例子只用同一真实 observer 的 submit/wait 两语义泳道，可先证明所需本地域；只有画跨 SM/observer 比较时才必须证明对应 epoch，不要把“全卡任意时钟全对齐”无端变成额外门槛。 |
| GCU timer 的尺度、连续性与漂移 | 现有 `p01_enflame_clock.py` 是有界校准候选，不是固定1ns/共同 epoch 证明。独立运行更长与更短间隔、留出验证点，并覆盖实际目标/运行状态；记录最坏界与有效窗口。误差不能分辨细事件时用更粗真实区间或 partial，不 clamp/拉宽图。 |
| Ascend SYS_CNT 及跨主体关系 | 同实际910B/SDK/对象核 getter和位宽；本地 actor 区间先通过。对目标异步边实际涉及的 AIC/AIV/其他 observer，以 SDK 明确计数器域证据或有界相关性实证证明关系；同频率、同调用或事件落在 native kernel 窗口内均不足以单独证明同 epoch。 |
| reset/截断/回绕 | 每条 clock proof 给出适用起止窗口和失效条件；构造 end≥start 但完整绕圈可能、边界接近误差的负例，必须拒绝比较。另核真实 getter/记录编码位宽一致。 |

共同 origin 应按已连通时钟域统一选取；一个域中的各 owner 不能分别归零后再并排。该要求已可由 §6 推导，建议冻结 clock schema 的实例直接展示此情形。

## 异步 group、代际与机制闭合

§8.2 的多 submit/commit/部分 wait/多消费者，§8.7 的每 invocation/机制实例状态，以及 §8.9 的 manifest→最终对象状态变更闭合，可以表达需要的三类机制，不必强制一对一 producer/consumer。

`timeline_nvidia_async.py` 对完整记录流生成 logical commit ordinal，对不完整流停止生成组关系，不把序号叫 loop iteration 或物理 buffer generation；当前返回 `time_arrow_verified=False`。这是一条可复用的逻辑层起点，不能单凭它认定真实异步流水通过。设计已经正确要求晚期机制闭合，opaque/外部状态变更降级；数一遍早期候选或两份共享同一识别错误的 metadata 互相一致都不够。

尚需设备/编译证据闭合：

- NVIDIA 必须核实际机制的拥有者粒度和参与者。若记录者是 elected lane/warp，须证明它能代表哪些真实 submit/commit/wait；遇到 predication、分歧或不同参与者组时，不能自动推广到整个 warp/CTA。先选目标普通 kernel 实际生成的机制；cp.async 的验证不自动覆盖 TMA/mbarrier/其他异步族。此项是 observer/机制合同的具体落地条件，未发现设计强制错误粒度。
- GCU 的 `execution_enflame.py` 包含 `memref.dma_start/dma_wait` 等静态候选，但这不证明最终机器上的真实机制或动态覆盖集合。最小 P01 先用普通编译产物找到真正的 submit/wait/同步标识，再决定计数 token、buffer 或 flag 代际来自哪里；不能直接把 IR 名称导成 verified flow。
- Ascend 的 set/wait 类型需与真正执行的控制路径、flag实例及复用轮次结合；至少首轮/稳态/drain 的真实记录证明代际。原 wait 后的 checkpoint 是完成上界，不能被写成精确引擎 end。
- 对每个已支持机制注入一次遗漏 commit/未知状态变更/串 invocation 的负例，再验证明确恢复锚点。正例需保全部组成员和端点 raw proof，而非一个“代表提交”。

机制闭合应只覆盖明确声明的实例/机制范围，无需先识别所有厂商指令后才能产生合法的本地 elapsed。设计的 partial 与 capability 分项提供了这个合理的开发顺序。

## owner 生命周期、发布与预算

§5、§8.7–8.9 和 testing §8.3 足以形成可实现的安全合同：admission 在提交前；owner快照隔离调用；原 stream 轻量完成句柄允许 host继续提交；最终化等待本 owner；未确认写者结束的超时路径隔离而非释放；不可变raw可重导而不重跑算子；所有 pending owner受session预算。

当前 NVIDIA hook 的 `self.buffer`、launch enter/exit锁和 census逐launch stream同步（`hooks/instrumentation.py:90–125, 595–735`）不满足新 owner 目标，恰好说明不能只改decoder/exporter；设计已经明确允许runtime/隐藏ABI改造，所以不将此列为设计缺陷。

最小实验应独立检查：

1. 同 binary 不同 grid交错多次启动，保 buffer地址/owner ID/stream完成句柄/host提交顺序；支持的two-stream必须在提交完才显式等，无逐launch host wait。
2. 让单调用合法但pending累积超session预算，在被拒调用发生设备副作用前拒绝；先前owner仍完成。禁止靠隐藏同步清空预算。
3. 提交后、完成句柄建立/查询、D2H、decode/export各阶段故障；无完成证明保留/隔离内存，写者终止后再回收。记录runtime/context销毁或不可恢复错误时资源实际归属，不能把host异常当作完成。
4. Ascend timeline新布局独立验证actor cache-line、commit与payload可见性；GCU验证真实work-item写者与完整payload；NVIDIA核环记录/计数/发布顺序。旧census通过不能替新ABI背书。

不支持two-stream/host-thread/graph时可按冻结能力早拒绝，但必须在本次设备副作用之前；拒绝后恢复和pending owner安全性仍须实测。设计没有无条件要求三后端实现所有并发形式，范围控制合理。

## 整体合理性、过度设计与遗漏

整体规模大，但目标同时要求三后端、自动源区域、异步、真实Perfetto和独立数学，因此多数合同不是装饰。保留各后端物理布局、只统一规范事件，避免了为统一格式破坏实际可见性；先首条链、再冻结小合同、再另外两后端的顺序合理。P01在全量矩阵之前能及时暴露GCU/Ascend机制或时钟硬阻碍。

不建议扩大：第四后端、通用插件包、一次覆盖所有异步族、强求所有observer跨域全对齐、完美busy图或完整关键路径。文档已经合理排除或降为增强。实施时也不应为每项概念造一个未使用类。

需要在小合同freeze时落实、尚不能称confirmed缺陷的细节：observer代表粒度/参与mask；clock连通域共用origin与证明有效期；提交成功而完成句柄失败时的保留策略；计数饱和后的loss下界/unknown区分；同一依赖的后续多个消费者究竟是重复完成保证还是独立数据消费边。现有§8.6字段/基数、§8.7失败阶段、§8.9闭合要求允许表达这些，无需现在新增大框架。

最大的未知不是Perfetto能否画slice，而是GCU/Ascend实际编译链是否开放足够的可排序边界、可比较timer与异步动态状态。现有源码为候选路径提供依据，不能消除此风险。保持三后端各自P01放行，未通过保持未验证；不能以本设计票或NVIDIA局部进展替代它。

## 阅读范围与未覆盖范围

完整：三个冻结输入、round3 INPUT。

必要源码只读：`timeline_nvidia.py`、`timeline_nvidia_async.py`、`timeline_clock.py`；NVIDIA `TargetInfo.cpp` getter；`hooks/instrumentation.py` allocator/enter/exit/census导出相关段；`tests/timeline/p01_enflame_clock.py`；`execution_enflame.py`开头及timer/异步候选搜索；`ascend_clock.py`、`cann_source_clock.py`、`observations_ascend.py`的clock/actor/布局相关段；`ascend_compiler.py`相关搜索和实际SDK产物关联段。只对完整读取的模块作全模块判断，其余是定向读取。

未读peer/旧评审、未审完整编译器/SDK/native实现、未核服务器安装字节、未执行任何设备/CPU测试、SQL/UI或真实发布验证；不宣称时钟/异步/owner已通过。没有修改产品、输入文档或其它报告。
