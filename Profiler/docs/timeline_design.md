# FlagPrism 内部时间线设计

状态：**待实现的设计，不是现有功能声明**。设计基线为 `e6aa804b203d3147925611423c2fcd20cf96bea2`；现有计数能力和历史验收保持原语境。执行合同见 [已跟踪快照](../../integration/plans/timeline/goal_prompt.md)（执行入口为工作区根目录同字节版本），测试设计见 [timeline_testing.md](timeline_testing.md)。产品设计不是论文正文，不修改 paper/Study。

## 1. 交付目标与最低界线

用户以普通 Triton 算子及启动脚本为输入，无需给 kernel 写 scope、填 site/SSA/ABI，运行一次公开命令，得到真实设备内部时间线。时间线必须能在标准 Perfetto UI 中缩放、选择、查看来源、区分计算相关区域、搬运发射、等待与完成，并能检查动态依赖。

本轮必须同时交付：

- **三后端通用时间观测**：NVIDIA RTX PRO 6000、Enflame C200、Ascend 910B 均自动采集多个有源码关联的内部时间段与循环重复，具有经过核验的时间单位，不能只有整核条或瞬时点。
- **三后端异步解释案例**：每个后端至少一个真实、合法的异步生产消费算子，展示实际提交/等待/完成观测及动态关联；必须有两个实际观测主体或两个有来源依据的执行/语义泳道。不能把普通顺序源码框重命名成硬件引擎。
- **可解释的 Perfetto**：不读手工 JSON 就能从泳道、slice 名称和详情理解这次执行。导入正确、内容正确、实际 UI 可读分别验收。
- **可核验的调优反馈**：至少两个受控案例说明改动如何影响重复、等待或阶段关系。未知指标不能填估算值来完善故事；不要求预定加速倍数。

硬件引擎真正的执行起止时间是有价值的增强，取得真实生产者证据后接入。软件观察者区间不得标成 MTE/Cube/Tensor Core 的 busy。只交付软件区间且没有任何可验证的异步等待/关联案例，也不满足本轮全部目标。

## 2. 当前代码可复用什么，必须补什么

| 现有组件 | 可复用部分 | 当前缺口 |
| --- | --- | --- |
| `observations.py` | typed semantics、clock/association/loss 合同 | 自动 timeline 请求、动态配对与新记录版本 |
| `observations_nvidia.py` | 已有 Proton scope 的局部 interval 读取 | 普通 unannotated kernel 的自动时间插桩；当前手写 scope 不能充当默认验收 |
| `observations_ascend.py`、`ascend_compiler.py` | issue/wait/checkpoint 与实际编译 handoff | 通用区域配对、动态迭代、跨主体时钟与生产消费关联 |
| `cann_source_clock.py`、`ascend_clock.py` | 带来源的本地频率/时钟证明 | 相同频率不等于相同 epoch；不能直接合并各 actor/native 时间 |
| Enflame instrumentation | SDK timer 的实际 lowering 与源关联 | timer 频率/范围验证、自动边界、异步与调用隔离 |
| `source_census.py`、各后端 census | 自动选择、源定位、身份、容量与 v3 记录完整性经验 | count 没有 timestamp，不能反推时间段 |
| `_report.py`、`profile.py` | 已有 Chrome trace/native activity 导出 | 完整内部事件、flow、严格 clock partition、Perfetto protobuf 与导入验收 |
| `execution_*`、`fine_grained.py` | binary/source/actor/调用关系、源码快照 | 连接时间事件与可验证动态依赖、以时间语义展示 |

实现前必须实际读这些文件，重核版本和运行中的任务。允许重构、改 FlagTree/SDK 通用结构；禁止逐算子插 LLVM 文本、固定 site 或猜名字配对。

## 3. 用户入口与采集策略

建议新增如下公共入口，**此命令目前尚未实现**：

```bash
python -m flagtree.profiler.cli --detail timeline --device 0 \
  -n trace-run my_script.py
```

API 也提供等价 `detail="timeline"`。不得改变现有无 detail 的 native 模式或 `detail="auto"` 计数模式的含义。接口名称可以经实现核定，但必须只有一个简单基本入口，最终文档只能写实际存在的命令。

默认行为：

1. 原请求脚本仅执行一次；在实际参数触发编译时发现源码/编译结构。没有预跑、自动 warmup、隐式 autotune 或应用重放。
2. 自动选择少量有意义的区域、循环和异步边界。优先覆盖进入、循环主体、发射/等待与消费，而不是连续八个无解释的小操作。
3. 默认选择实际 launch grid 的首、末两个不同 logical program；grid 为一时只选一个。实际 lowering 负责恢复坐标和物理主体，不能直接把 BLOCK/warp 编号当源 program。
4. 对选中 program 记录实际必要的 observer/actor。默认上限建议每 program 四个 observer、八个逻辑区域、每 observer 4096 条原始记录、总 raw 8 MiB；这些是初始工程预算，不是后端架构常数。
5. 选择必须在设备/编译阶段减少记录工作。支持公开参数扩大范围；展示过滤不得冒称低开销采集。
6. 把 `selected/unselected/unsupported/dropped/incomplete` 分开。默认采样并不覆盖全 grid，但不影响旧 census 全 grid 合同；不能把旧计数记录变成虚构 event。

两个 observation 模式、协议/ABI、clock getter、compiler/SDK 身份与 logger 版本必须进入 JIT 内存/磁盘 cache key。旧缓存保留作升级回归，不能靠清缓存掩盖错误。

## 4. 事件语义先于画图

| 类型 | 什么时候产生 | 在 Perfetto 中是什么 | 可以推断什么 |
| --- | --- | --- | --- |
| `observer_region_elapsed` | 观察者在实际控制区域前后读钟 | 有起止的 slice，标注 observer elapsed | 观察者经过该区域的时间，包含其阻塞和插桩影响 |
| `issue_interval` | 异步命令提交边界前后 | 独立 submit 泳道的 slice | 发射经过时间，不能视作异步引擎执行时间 |
| `wait_bracket` | 原程序既有 wait 前后 | wait 泳道的 slice | 此观察者在 wait 区域停留多久，不自动等同全部硬件 stall |
| `completion_checkpoint` | 已有完成/可见性语义之后读钟 | instant；有独立起点且关联明确时可形成完成包络 | 截至该点某操作/组已经完成；不是其精确完成时刻 |
| `native_engine_activity` | 原生厂商记录确实给出 engine begin/end | 明确标注来源的 engine track | 生产者定义的真实引擎活动区间 |
| `counter` | 计数器更新/汇总 | 只有真实采样时间才画 counter；无时间则放 metadata/报告 | 数值，不产生伪时间分布 |

不把相邻 checkpoint 默认连成某条指令的 duration。语义由实际 IR/ISA/SDK 语义决定，发射与实际完成必须分开。GPU 上源码行前后读钟不必然包住该行异步操作的完成。不能额外插入完成屏障让图变整齐。

边界合法性必须核对真实生成的 IR/ISA：begin 支配观测区域、end 处于所声明控制路径；计时读取和 logger 不被提升、折叠、挪出循环或跨越声明边界。必要的数据/控制依赖应来自通用 compiler lowering。只验证插桩 pass 被调用不够。

循环事件保留真实 occurrence。`iteration_id` 只有在实际循环标识/动态索引有证明时才填写；不能把同一 site 的第 n 次出现一律当第 n 次循环。

## 5. 记录协议与身份

建议规范化字段，具体 ABI 大小由实现冻结并版本化：

- `schema_version, event_id, capture_id, invocation_id, binary_id, source_region_id, backend_site_id`。
- `program_coordinates, observer_kind, observer_id, physical_identity_evidence, stream/context/device`。
- `event_kind, semantic, pair_token, sequence, occurrence, loop_id/iteration_id`。
- `clock_domain_id, epoch_id, start_tick/end_tick 或 timestamp_tick, timer_bits`。
- `operation_token, producer_token, consumer_token, buffer_identity, buffer_slot, generation`（可空，缺失不能猜）。
- `raw_artifact_sha256, byte_offset, byte_length, compiled_marker_evidence`。
- `attempted/committed/dropped/sampled/unpaired` 和精确性、缺失原因。

`event_id` 绑定实际一次 event，不复用 across capture。source region 的逻辑身份与 backend site 分开；不同 specialization 不能搬用 site 数字。函数名、时间邻近和裸指针不构成关联证据。

设备协议：按调用/program/observer 分区，真实多写者采用经过证明的发布协议；明确 entry/exit 对、提交标志和错误恢复。保留 Ascend actor cache-line 独立对齐，容量包括 header/padding。选择前完成 scratch admission；不能先大分配再说超预算。

丢 begin/end 不补造端点。部分区间保留为 incomplete，超时/异常不把 kernel end 充当所有内部 end。最终化等到原有正确的完成条件后再读记录，不靠额外全局同步改变被观测流水。

## 6. 时钟与 Perfetto 时间坐标

目标是三个后端均具有可用的、经过验证的时间尺度。原始 ticks 永远保留。未知频率的 ticks 不能写进 ns 时间轴；仅有 raw-ticks 页面属于调试降级，不满足完整验收。

三类合法导出：

1. 同一经核验设备时钟：转换为 ns 并使用同一设备相对坐标，允许真实跨 actor 对照。
2. 已有 clock correlation：在保存映射、误差和适用 epoch 后，与 native/host 统一；不能用 kernel 首尾拟合伸缩。
3. 各时钟有验证频率但没有共同 epoch：每个未连接域单独导出 `.pftrace`，在入口明确不能比较。不能在同一图把每个域都人为归零并排，制造同时发生的错觉。必须继续解决目标异步案例所需的域间关系，单独分文件不是完成所有目标的捷径。

时钟证据必须覆盖 getter 的实际机器指令、位宽、频率/换算来源、作用域、复位/回绕、转换误差与跨 actor 可比性。转换先在整数域减 origin，再以整数/有理数比例换算，避免 float 对大绝对 ticks 丢低位。频率已知与 epoch 共享分别证明。

候选路径：NVIDIA 优先评估实际目标支持的 global timer；旧 SM-local clock 可以保留，但无证明时不跨 SM 对齐。PTX 把 global timer 描述为工具用、行为依目标而定，因此必须核本机编译和实际 getter，不能凭名称默认所有 GPU 可用。[PTX ISA](https://docs.nvidia.com/cuda/parallel-thread-execution/)

Ascend 复用已有 SYS_CNT/SDK 证据链，重核实际 910B SDK 和编译对象；50 MHz 等旧证据只适用于其真实目标。GCU 先核已用 SDK timer 的真实定义；没有公开固定频率时，可以研究 SDK 的同域已知计时源或带误差的独立校准，不能简单用营销主频。校准使用独立留出点验证，不用待解释 kernel 的首尾来拟合。

Perfetto 支持 clock domain/snapshot，前提是生产者真实提供同步关系。Snapshot 不会自动证明设备时钟关系或推导任意 tick 的频率。若先转换了 tick 单位，要明确导出的是转换后的 ns 域，原始计数只放 metadata。[Perfetto clock synchronization](https://perfetto.dev/docs/concepts/clock-sync)

若校准不确定度超过观测区间尺度，该细粒度结果不能用于声称重叠/先后。应选择更粗的真实区域或提供该尺度不可分辨的状态，不给短事件强加最小可见宽度。

## 7. 动态依赖与真正的流水

flow 的键至少包括 capture/invocation/program、producer/consumer、实际 operation/group、buffer slot 与 generation。flag/group 复用必须分代；同地址不代表同一次数据。

- NVIDIA：研究实际 async copy/TMA、commit/wait group、mbarrier 与 warp specialization lowering。记录实际提交组/完成观察者，不把所有 warp 映射成硬件 copy engine。
- Ascend：从真实 AIC/AIV、MTE/compute/set/wait 结构恢复关系；静态 set/wait 类型只能提供候选，动态 token/generation/控制路径给出本次 edge。
- Enflame：核真实 SDK/编译器暴露的 transfer/compute/sync 标识，优先复用已有编译 manifest；不把厂商名称套成 NVIDIA warp 模型。

UI 用明确名称区分“observed dependency”“static candidate”“ambiguous”。只有可验证动态关联且时钟可比较的 edge 才画跨 track 时间箭头。无共同 epoch 的依赖仍可作为图/表保留，但不能偷偷画成同一时间轴。只有硬件活动或有充分完成/启动边界的证据才可讨论真正的计算—搬运重叠；软件 observer 的重叠只标为 observer overlap。

不能把不完整依赖图计算出的链声称为完整关键路径；可显示有证据子图的最长链及覆盖范围。

## 8. 后端实现路径

| 后端 | 第一项工程 | 后续必须闭合的证据 |
| --- | --- | --- |
| NVIDIA | 把自动 discovery 接到通用 scope/事件插桩，普通 kernel 不写 profiling scope；验证 timer 与 warp/program 身份 | 同一 binary 的动态重复；实际 async producer/consumer；可用时钟域与源码定位 |
| Enflame | 把既有 interval/timer 路径纳入自动 planner，补 timer 来源及转换，控制代码膨胀 | 原 SDK timer 真读数与 ns 比例；异步 token/执行结构；三类普通 kernel |
| Ascend | 扩展既有晚期 observer 的有界事件协议，保留源码→SDK→实际对象的链和 v3 内存可见性修复 | region/wait 配对、原标量写入语义不破坏、AIC/AIV 动态依赖和可比时钟 |

每条路径先运行普通 baseline，再做通用机制修复及开发样本，最后独立新数学验收。不能复制 Python 文件到旧 native 上算新实现；新增 pass/ABI 真编译，未变依赖只在逐字节证明后复用。

## 9. Bundle 与 Perfetto 呈现

建议在原 bundle 合同上增加版本化内容，不建立互相矛盾的第二套身份：

- `ai/timeline_observations.json`：规范化时间事件，引用原始 bytes 与源/编译证据。
- `ai/timeline_clocks.json`：时钟域、频率、epoch、转换和误差。
- `ai/timeline_dependencies.json`：动态 edge、静态候选、拒绝原因。
- `ai/timeline_status.json`：逐 invocation 覆盖、选择、损失、完整性和可导出状态。
- `report/internal.pftrace` 或按域分区的 `.pftrace`：标准 Perfetto protobuf，作为必交付。
- `report/timeline_index.html`：不用手配 IDs 的打开入口、采集范围、语义/单位说明和域分区。

可保留 Chrome JSON 兼容出口，但它不能代替时钟证明；其 `ts/dur` 是微秒，`displayTimeUnit` 只控制显示，不能修正错误单位。原生 TrackEvent 方便表达 track/slice/counter/flow；导出要遵守其实际导入规则。[格式支持](https://perfetto.dev/docs/getting-started/other-formats)、[TrackEvent 转换指南](https://perfetto.dev/docs/getting-started/converting)

track 分组层次：capture/device → 实际 invocation → program/实际 observer → region、submit、wait、completion 或有证据 native engine。详情至少给源文件/行/region、实际 observer/执行身份、semantic、begin/end tick、ns、clock/error、occurrence、token/generation、丢失状态与 raw 来源。

异步重叠事件不得被强塞成同一 stack 上错误嵌套的 B/E；为独立 in-flight operation 使用独立轨道/协议。记录本身的时间不移动，不为排版把重叠事件排成串行。track/flow IDs 稳定且检测 collision；schema/消费者版本明确。

Perfetto 自身不能自动做源码文件导航的地方，提供可复制 source 位置与配套 bundle 源码页面；事件详情必须直接看见来源，不能要求用户再拼十份 JSON。

## 10. 预算、扰动与诚实比较

保留初始小样本工程预算：冷编译 `min(300s,max(120s,3×普通同设置冷编译))`、导出 60s、完整 bundle 64 MiB。内部 trace 初始目标 16 MiB，raw 初始 8 MiB；默认选择和协议开销必须计入总预算。超预算不删除必要原始证据后伪称通过。

默认时间属于插桩程序。核对实际指令、无新完成 barrier、无全局记录锁，并比较疏/密两种观测方案是否改变阶段关系。Ascend/GCU 在可用稳定窗口记录普通与插桩参考和噪声；NVIDIA 允许真实时间线功能和时钟校验，继续不开展此前暂缓的独占吞吐、速度提升或开销比认证。不能借该限制跳过 NVIDIA 时间戳功能。

若时钟或插桩使某个现象不可分辨，按证据报限制。不能把“真实记录”直接说成“无扰动的真实执行”，更不能拿插桩程序变快当优化收益。

## 11. 实施次序与交付判定

`现状/能力实证 → 事件协议与时钟 → 三后端自动时间采集 → 动态依赖 → Perfetto exporter → 真算子/Perfetto SQL/UI 验收 → 独立新数学 → 三名独立代码审阅 → 修复/有限复核 → Git交付`。

先以一个后端打通完整链再并行扩展，但三个后端均为必达，不以第一个的漂亮图替代其它后端。取得真实事件后才完善展示，不能用示意数据代替设备实现。具体通过条件、冻结规则和场景见 [测试设计](timeline_testing.md)，目标执行规则以根目录 goal 合同为准。
