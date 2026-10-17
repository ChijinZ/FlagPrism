# FlagPrism 内部时间线设计

状态：**实现中的目标设计，不是完整功能声明**。已有原语与构建证据不等于完整时间线通过；当前已实现能力及限制见 [timeline_runtime.md](timeline_runtime.md) 和 [timeline_events.md](timeline_events.md)；§8.8 仅保留历史原语检查点。原始设计基线为 `e6aa804b203d3147925611423c2fcd20cf96bea2`；现有计数能力和历史验收保持原语境。执行合同见 [已跟踪快照](../../integration/plans/timeline/goal_prompt.md)（执行入口为工作区根目录同字节版本），测试设计见 [timeline_testing.md](timeline_testing.md)。产品设计不是论文正文，不修改 paper/Study。

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
| `observations_nvidia.py`、instrumentation hook | 已有 advanced 自动/手工 Proton source-control interval、源关联与 scope pass 接入 | 公开 timeline 路径、优化后执行 manifest、目标 timer/ns 证明、partition/异步观测与动态关联；已有 raw-cycle interval 不等于本轮通过 |
| `observations_ascend.py`、`ascend_compiler.py` | issue/wait/checkpoint 与实际编译 handoff | 通用区域配对、动态迭代、跨主体时钟与生产消费关联 |
| `cann_source_clock.py`、`ascend_clock.py` | 带来源的本地频率/时钟证明 | 相同频率不等于相同 epoch；不能直接合并各 actor/native 时间 |
| Enflame instrumentation | SDK timer 的实际 lowering 与源关联 | timer 频率/范围验证、自动边界、异步与调用隔离 |
| `source_census.py`、各后端 census | 自动选择、源定位、身份、容量与 v3 记录完整性经验 | count 没有 timestamp，不能反推时间段 |
| `_report.py`、`profile.py` | 已有 Chrome trace/native activity 导出 | 完整内部事件、flow、严格 clock partition、Perfetto protobuf 与导入验收 |
| `execution_*`、`fine_grained.py` | binary/source/actor/调用关系、源码快照 | 连接时间事件与可验证动态依赖、以时间语义展示 |

实现前必须实际读这些文件，重核版本和运行中的任务。允许重构、改 FlagTree/SDK 通用结构；禁止逐算子插 LLVM 文本、固定 site 或猜名字配对。

## 3. 用户入口与采集策略

公共入口如下。NVIDIA 已实现显式 `partial_clock_unverified` 的 raw 采集路径；这不等于本设计的三后端 ns/Perfetto 交付，当前限制见 [timeline_runtime.md](timeline_runtime.md)：

```bash
python -m flagtree.profiler.cli --detail timeline --device 0 \
  -n trace-run my_script.py
```

API 提供等价 `detail="timeline"`。不得改变现有无 detail 的 native 模式或 `detail="auto"` 计数模式的含义。接口名称可以经实现核定，但必须只有一个简单基本入口，最终文档只能写实际存在的命令。

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

边界合法性必须核对真实生成的 IR/ISA：begin 支配观测区域、end 处于所声明控制路径；计时读取和 logger 不被提升、折叠、挪出循环或跨越声明边界。必要的数据/控制依赖应来自通用 compiler lowering。只验证插桩 pass 被调用不够。timer/logger 有副作用、volatile 或 memory clobber 本身不证明纯算术不会越过边界；每后端要说明约束止于哪个编译层，并在最终对象中核顺序，不能用额外完成 barrier 代替。

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

丢 begin/end 不补造端点。部分区间保留为 incomplete，超时/异常不把 kernel end 充当所有内部 end。最终化等到原有正确的完成条件后再读记录，不靠额外全局同步改变被观测流水。每 invocation 持有独立的 buffer owner/完成依赖；允许为安全导出在最终化等待本次记录完成，不允许复用旧逐 launch 同步而宣称保留原跨 stream 提交关系。异常/取消也须等实际写者终止或完成后才能复用/回收记录。

## 6. 时钟与 Perfetto 时间坐标

目标是三个后端均具有可用的、经过验证的时间尺度。原始 ticks 永远保留。未知频率的 ticks 不能写进 ns 时间轴；仅有 raw-ticks 页面属于调试降级，不满足完整验收。

三类合法导出：

1. 同一经核验设备时钟：转换为 ns 并使用同一设备相对坐标，允许真实跨 actor 对照。
2. 已有 clock correlation：在保存映射、误差和适用 epoch 后，与 native/host 统一；不能用 kernel 首尾拟合伸缩。
3. 各时钟有验证频率但没有共同 epoch：每个未连接域单独导出 `.pftrace`，在入口明确不能比较。不能在同一图把每个域都人为归零并排，制造同时发生的错觉。必须继续解决目标异步案例所需的域间关系，单独分文件不是完成所有目标的捷径。

时钟证据必须覆盖 getter 的实际机器指令、位宽、频率/换算来源、作用域、复位/回绕、转换误差与跨 actor 可比性。转换先在整数域减 origin，再以整数/有理数比例换算，避免 float 对大绝对 ticks 丢低位。频率已知与 epoch 共享分别证明。截断计数器必须有不超过可判定回绕窗口的独立约束；即使 end≥start，也不能排除完整绕过一圈，不能只在 end<start 时检查回绕。

候选路径：NVIDIA 优先评估实际目标支持的 global timer；旧 SM-local clock 可以保留，但无证明时不跨 SM 对齐。PTX 把 global timer 描述为工具用、行为依目标而定，因此必须核本机编译和实际 getter，不能凭名称默认所有 GPU 可用。[PTX ISA](https://docs.nvidia.com/cuda/parallel-thread-execution/)

Ascend 复用已有 SYS_CNT/SDK 证据链，重核实际 910B SDK 和编译对象；50 MHz 等旧证据只适用于其真实目标。GCU 先核已用 SDK timer 的真实定义；没有公开固定频率时，可以研究 SDK 的同域已知计时源或带误差的独立校准，不能简单用营销主频。校准使用独立留出点验证，不用待解释 kernel 的首尾来拟合。

Perfetto 支持 clock domain/snapshot，前提是生产者真实提供同步关系。Snapshot 不会自动证明设备时钟关系或推导任意 tick 的频率。若先转换了 tick 单位，要明确导出的是转换后的 ns 域，原始计数只放 metadata。[Perfetto clock synchronization](https://perfetto.dev/docs/concepts/clock-sync)

若校准不确定度超过观测区间尺度，该细粒度结果不能用于声称重叠/先后。应选择更粗的真实区域或提供该尺度不可分辨的状态，不给短事件强加最小可见宽度。先后/重叠按端点不确定区间判断，而不只比较误差与总 duration 的大小；例如保守独立误差下，只有 `tA+uA < tB-uB` 才能确定 A 在 B 之前。共享误差项按实际模型处理，无法确定的近边界关系明确显示不可分辨。

## 7. 动态依赖与真正的流水

flow 的身份至少包括 capture/invocation/program、机制实例、producer/consumer 与实际 operation/group。buffer slot 与 generation 在声明物理缓冲复用关系时必需；仅证明逻辑 commit-group 的边必须明确标为逻辑组关系，不要求编造不可观测的 buffer。flag/group 复用必须分代；同地址不代表同一次数据。

- NVIDIA：研究实际 async copy/TMA、commit/wait group、mbarrier 与 warp specialization lowering。记录实际提交组/完成观察者，不把所有 warp 映射成硬件 copy engine。
- Ascend：从真实 AIC/AIV、MTE/compute/set/wait 结构恢复关系；静态 set/wait 类型只能提供候选，动态 token/generation/控制路径给出本次 edge。
- Enflame：核真实 SDK/编译器暴露的 transfer/compute/sync 标识，优先复用已有编译 manifest；不把厂商名称套成 NVIDIA warp 模型。

UI 用明确名称区分“observed dependency”“static candidate”“ambiguous”。只有可验证动态关联且时钟可比较的 edge 才画跨 track 时间箭头。无共同 epoch 的依赖仍可作为图/表保留，但不能偷偷画成同一时间轴。只有硬件活动或有充分完成/启动边界的证据才可讨论真正的计算—搬运重叠；软件 observer 的重叠只标为 observer overlap。

不能把不完整依赖图计算出的链声称为完整关键路径；可显示有证据子图的最长链及覆盖范围。

## 8. 后端实现路径

| 后端 | 第一项工程 | 后续必须闭合的证据 |
| --- | --- | --- |
| NVIDIA | 复用并扩展已有自动 scope/discovery 接入；补晚期 manifest、目标 timer、新事件协议与实际 observer/program 身份，普通 kernel 不写 scope | 同一 binary 的动态重复；实际 async producer/consumer；可用时钟域与源码定位 |
| Enflame | 把既有 interval/timer 路径纳入自动 planner，补 timer 来源及转换，控制代码膨胀 | 原 SDK timer 真读数与 ns 比例；异步 token/执行结构；三类普通 kernel |
| Ascend | 扩展既有晚期 observer 的有界事件协议，保留源码→SDK→实际对象的链和 v3 内存可见性修复 | region/wait 配对、原标量写入语义不破坏、AIC/AIV 动态依赖和可比时钟 |

每条路径先运行普通 baseline，再做通用机制修复及开发样本，最后独立新数学验收。不能复制 Python 文件到旧 native 上算新实现；新增 pass/ABI 真编译，未变依赖只在逐字节证明后复用。

### 8.1 本轮同时形成的适配边界

目标：先把现有三后端做实，再由这些实现检验接口。**本轮不新增第四芯片，不承诺新编译链只需配置，不建立没有实际调用者的庞大插件框架。** 公共语义与输出统一，设备执行结构、合法插桩点、时钟和同步机制由后端保留并提供证据。下面均为待实现的职责合同，不是现有 API 声明；具体类名/模块由实现确定。

```text
普通 kernel / 观测请求
  → 公共区域选择意图（源区域、范围、预算、请求语义）
  → 后端编译实现（合法边界、lowering 后主体、实际同步语义）
  → 执行 manifest + 有界记录 / 时钟证据
  → 后端解码和语义映射
  → 公共事件、身份/配对/时钟/依赖验证
  → 公共 Perfetto / 源码报告
```

不能只在早期 Triton IR 找到区域就宣称该区域的执行主体/完成语义已经确定。优化后可能融合、拆分、流水化或消除区域；必须由晚期 manifest 描述一对多/多对一映射、实际 marker 和消除状态。公共 planner 选择逻辑意图，后端根据实际可观测结构给出执行计划，再以共同预算进行 admission；不合法的边界不得硬插，不能静默换成无关区域。fused 执行区间可以关联多个 source origin，但不能复制同一 duration 当成两个内部阶段满足两区间门槛；split/消除/未知分别记录，不强行给每个源操作分摊成本。

| 职责边界 | 公共部分 | 后端实际交付 |
| --- | --- | --- |
| 能力与注册 | 请求解析、版本化能力合同、选择与明确诊断 | 目标/编译链匹配、能力探测和证据；按注册选择实现 |
| 编译接入 | 源区域身份、采集意图、通用预算、源关联校验 | 实际 pass 接入点、合法区域/控制流、timer/logger lowering、真实源码到执行 manifest |
| 主体与拓扑 | 可扩展主体节点/关系、调用/program 隔离 | 逻辑 program 到实际主体的映射、身份可知范围；不假设所有主体是 warp/SM |
| 运行时与记录 | 生命周期、调用身份、预算 admission、完整性合同 | 隐藏参数/设备缓冲、合法发布/回收、物理 padding/对齐、实际 raw 解码 |
| 时钟 | 整数/有理数转换、误差传播、域隔离和合法对齐验证 | getter、位宽、频率/epoch/相关性证据、适用目标和失效条件 |
| 异步机制 | 动态操作/组/依赖模型、generation 和歧义验证 | 真实 submit/commit/wait/completion 的含义与 token、batch 和复用规则 |
| 展示 | 标准 Perfetto、源导航、统计、损失与覆盖说明 | 描述性名称/层级/附加属性；无需复制 exporter 或按厂商分支画图 |

同一物理 ABI 并非强制：设备可有不同 header、bank、stride、发布协议；解码后遵守同一事件合同，并保留 raw offset/生产者版本。不能为了统一布局破坏 Ascend 独立 cache-line 可见性，也不能让公共消费者承担猜测各厂商物理布局的职责。需要维护的旧格式兼容分支可以保留并明确版本，不能借清理边界破坏旧数据。

### 8.2 执行主体、时钟、异步：统一含义而非统一微架构

**主体**：至少区分逻辑 program、真实记录 observer、被观察的 operation、可选硬件 resource。用有来源的类型/层级和关系表达，而非固定 `block→warp→lane` 树。source region 也不是硬件主体。后端本地 ID 命名空间须绑定 target/device/context/invocation 等实际范围；未知物理位置保持未知，不补虚拟 SM/engine。额外角色可用命名空间扩展，但公共身份、损失和时钟字段不能被扩展属性覆写。

**时钟**：能力记录明确 timer 的 scope 和哪些主体共享 epoch。先有可验证本地域的区间，再证明跨主体比较；不同厂商/型号不继承别的目标的频率或对齐结论。时钟误差、分辨率和读取顺序约束作为显式契约，不以 `supports_timeline=true` 代替。

**异步**：不能用一个 `producer_id→consumer_id` 一对一假设统一所有机制。模型必须能描述多次 submit 被一次 commit 组成 group、wait 只覆盖部分先前 group、批量完成、多个消费者，以及 flag/barrier/buffer 槽的多轮 generation。后端语义规则给出本次实际被覆盖的 operation 集合，公共层检查身份、generation、因果及完整性，再生成有证据的 edge。

动态 token 可以来自实际 SDK/硬件 ID，也可以由编译器在真实控制路径上维护可验证的逻辑序号/状态；必须与原机制的 submit/group/wait 语义对应。不能仅按记录先后编号就断言硬件依赖。日志路径不能新增完成 barrier、改变原有 wait 覆盖集合，或把多个主体的记录全局串行化。不能证明具体 edge 时保留候选/歧义，不强配；三后端异步案例的既有硬门槛仍须满足。

### 8.3 目标能力与缓存身份

按实际 target、编译器/SDK 版本与插件版本探测能力，不只按厂商品牌选择。能力至少覆盖：自动区域/循环、observer 身份、计时器及分辨率、跨主体可比范围、可识别异步机制、记录约束与并发/graph 边界。每项记录状态、理由、证据和适用条件；已验证支持、已知不支持、尚未核验不得混为一个布尔值。

能力可在目标预检及实际编译后两阶段细化，但 profile 前必须基于普通编译锁定资格。事前普通输入资格清单、目标能力证据、本次 instrumented plan/outcome 分开保存并相互引用，后两者不能覆写前者。不能看到 profile 失败再改为 unsupported；没有计时能力不能把 timeline 请求悄悄退化为计数并返回成功。可在请求不支持的精细能力时明确失败，或按文档返回明确 partial，但它们不完成该资格项。

通用缓存身份包含 target/编译链和实际插件实现、能力协议、planner、事件/设备 ABI、timer 实现和依赖规则版本；同厂商不同架构/SDK 不串用。公开安装能定位后端实现，不依赖临时 monkey patch 或开发机 PYTHONPATH。依赖内容身份必须在内存/磁盘缓存查询前取得，不能只在 cache miss 后的 metadata 中计算；本次 capture 的 epoch/clock 证明与编译缓存身份分开，不从旧 bundle 搬用。

### 8.4 以三个真实实现检验复用，控制适配成本

每个后端须有一份适配清单：编译接入、manifest、logger/物理协议、主体、clock、async 机制、安装与设备测试。已有组件可复用并指明来源，不要求人为复制文件凑接口。

第一条真实链打通后冻结一个小的接口版本，再接第二、第三后端。发现遗漏的通用概念可改公共层，但须记录“为什么是公共概念、对已有实现的兼容影响、对应回归”；不能为追求零公共改动把架构事实塞进不受约束的字典或厂商分支。无重复调用者的额外抽象暂不引入。

最终留存逐后端实际改动范围（通用/后端/编译集成/测试与文档）、新增 hook、公共格式变化和构建步骤。这只证明当前三类实现的复用情况，不凭代码行数或 CPU 假后端声称未来芯片已适配、几天可完成或已证明第四架构可行。

验收目标：后端注册允许新增实现；公共 planner、事件验证、clock 转换、依赖检查、Perfetto 和报告不需要按新增厂商逐个添加业务分支。后端特有语义识别规则放在后端模块，公共层只消费经验证的合同。确有新语义时允许显式版本扩展和共同回归；统一不以删掉已有后端细粒度信息为代价。

### 8.5 实现前的可行性检查点

全量矩阵前，三后端各完成一个小的真实数学纵向验证：普通 baseline、实际 timer 指令/单位、有源码的两个区间、合法记录发布、一个真实异步机制及其可比时钟/动态关联、标准 Trace Processor 导入。具体算法可不同，时间模型和公共消费者必须相同。

阶段检查区分已验证/设计假设/硬阻碍，保实际 IR/ISA/SDK 语义来源。若某 SDK 不开放必要插桩点、getter 不能提供时间尺度，或原合法异步机制无法观测，先验证现有通用扩展与可用 SDK 路径，再返回最小技术/环境阻碍；不得先跑大量资格后才承认核心机制未知，也不得把“尚未验证”当作硬件不可能。这个检查点不能替代后续普通算子、独立数学和三后端最终验收。

### 8.6 小版本公共合同的冻结清单

下面是第一条真实纵向链之后、第二/第三后端正式接入前必须形成的可定位 schema/接口与小样本，不要求设计阶段先写空框架。后续真实后端发现新公共概念时可以显式修订版本并共同回归。

| 合同对象 | 至少明确的字段/关系与消费规则 |
| --- | --- |
| target 能力 | target/compiler/SDK/plugin 身份；verified/unsupported/unverified、条件、证据引用；与 ordinary eligibility 和本次 outcome 分离 |
| observation intent | source region 集合、请求语义、program/observer 选择策略及物理预算；不预填未知硬件主体 |
| execution manifest | binary 身份、source M:N origin 集合、preserved/fused/split/eliminated/unknown、实际 begin/end anchors、控制路径/循环映射及证据；时间归属与源码导航分开 |
| decoded batch | schema/producer/物理 ABI 版本、invocation、observer、事件及完整性；begin/end 或 SDK 记录的全部 raw/proof 引用，而非只留代表端点 |
| clock proof | 原 tick、有效位宽、整数/有理数比例、epoch/scope、误差模型、有效窗口、证据和失效条件；转换后 ns 舍入规则 |
| operation/group/wait | 实际 operation 集合、commit 分组、wait 覆盖集合、completion 语义、generation、丢失后的失效/恢复锚点；edge 引用完整性与多消费者关系 |
| export mapping | canonical event→track/slice/instant/flow、重叠处理、稳定 ID、源/clock/loss/proof args、独立域分区；公共 SQL 按同一语义检查 |

必填/可空、字段类型、基数、跨对象引用及未知版本行为要可执行验证。扩展描述性属性使用命名空间和明确类型，公共展示可保留不透明值；未知时间/依赖语义不得绕过 validator 获得 verified，未知必需语义按版本明确拒绝或 partial。扩展不能覆盖 core 字段，不能靠 permissive dictionary 代替新公共概念。

普通输入、事件和源导航分别绑定源 snapshot/hash 与实际编译映射；能打开某行不等于精确执行归属。错 snapshot、悬空 region/group/edge、错 binary、丢 anchor、错误扩展类型都需要明确校验结果。

设计阶段的静态风险清单：NVIDIA 已有自动 scope，但 interval 对 worker partition 的选择、旧 32/43-bit SM clock 与新 timer/ABI 的衔接仍待证；GCU 已有真实 SDK timer，但早期 TTIR 插桩后的实际边界、单位与 async 路径仍待证；Ascend 晚期 observer 仍在 scalar optimization 前，普通操作目前为 checkpoint，动态时间 v1 也不是已修复的 census v3 布局。三者均不能仅换 exporter 就宣称完成。P01/相关 P、E 测试闭合这些风险；最新已取得的有限原语证据与剩余缺口见 §8.8。

### 8.7 可实施的后端交接与采集生命周期

下表规定最小职责交接，不强制新建同名类、独立进程或单一物理 ABI。先复用现有 hook/pass/decoder，再在真实调用边界落实类型检查；公共层不能重新解析厂商指令字符串以补足后端遗漏的语义。

| 交接 | 输入 → 输出 | 责任与失败处理 |
| --- | --- | --- |
| 能力解析 | target 与已安装依赖 → 带条件的能力证据/依赖指纹 | 后端识别型号、SDK、getter 和机制；公共层校验版本及证据范围。缓存查询前确定编译依赖，capture 时另核 epoch |
| 编译计划 | observation intent + ordinary eligibility + 实际优化结构 → execution manifest + 物理记录需求 | 后端给合法 anchors、主体映射、异步机制描述和字节预算；公共层 admission 后才能为捕获分配设备 scratch。编译器产生的静态计划不冒称 runtime 动态身份 |
| 启动准备 | manifest + 本次实际 grid/stream/device → invocation owner | 后端绑定隐藏参数、所选 program 与完成依赖；公共层分配唯一调用身份、核实际 grid 的容量，不能仅凭缓存 specialization 决定首末 program |
| 捕获完成 | invocation owner → 不再被设备修改的 raw bytes + 完整性状态 | 后端完成原 stream 上的安全发布/拷贝；公共层维护 owner 生命周期和超时。异步异常不能仅因 Python 返回就释放设备缓冲 |
| 解码与机制映射 | raw + manifest + 本次 clock proof → typed events + operation/group/wait 事实 | 后端处理位宽、padding、commit、原机制覆盖集合；公共层核引用、配对、generation、loss 和可比较时钟，决定哪些 edge 获得 verified |
| 导出 | 通过验证的 canonical 数据 → pftrace/索引/状态 | 一个公共 exporter；新 observer 角色使用描述字段，不按厂商复制绘图逻辑。未知必需语义拒绝或显式 partial，不放宽验证 |

异步映射规则属于后端，动态状态不属于全局单例：每次调用、每个机制实例维护自己的 group/slot/generation 状态。后端输出有类型的提交集合、wait 覆盖及来源，公共层独立核完整性；不能仅信后端写出的 `verified=true`。共享验证能发现悬空引用或串代，但机制规则是否符合真实 ISA/SDK 仍由设备证据核验。

生命周期的最小状态机：

```text
设备 owner：planned → admitted → armed → submitted → completion_observed
          → raw_ready → 原件与关联快照安全持久化 → released
文件/派生：原件安全持久化 → decoded → exported（失败可由原件重试）
```

设备资源和文件/派生是独立状态，不要求调用者同步等待每条箭头。具备覆盖全部写入的完成证明，且 D2H 和重导所需原件/关联快照安全持久化后，设备 scratch 可回收，不能要求 decode/export 成功后才释放。一个 owner 的派生失败不阻止尝试安全取得、持久化和回收其他已完成 owner；保首个错误、逐调用错误与终态。仍有潜在写者的 owner 继续隔离，不因其它调用失败释放。`armed` 已持有本次 buffer、manifest 快照、device/stream/context、selection、clock/规则版本及 completion owner；实际提交后不可因下一次 launch 覆写。并发 owner 的数量和全部 pending buffer 字节也受 session 总预算限制，不能只限制单调用。预算不足在 launch 前明确失败；禁止通过逐 launch 强同步偷偷满足容量并改变声称支持的跨 stream 行为。

若后端能在原 stream 记录轻量完成 event，host 可继续提交，最终化仅等待本次 owner 的完成并读取记录；若只能借助 SDK 的等价完成条件，必须说明其范围与并发限制。最终化允许等待记录已完成，但不得注入新的设备完成屏障改变被测内部流水。普通编译、launch、设备完成、D2H、解码和导出是不同失败阶段：分别记录错误与已取得数据。超时不等于设备已停；确认本次写者结束前保留或隔离 owner，不能释放/复用，也不能杀其它用户任务。无法安全回收时本 session 明确失败并报告保留资源，不能声称已释放。

已完成且 raw 持久化后，导出失败可以在同一原件上重试；不得为重导图重跑用户算子。只有尚未分配、或能证明没有发生任何设备初始化/提交写入的 owner 才可直接取消并回收；初始化本身可能提交设备写入，armed、submitting 或已隔离的 owner 都按潜在在途写者处理，取得覆盖其全部写入的完成证明后才能回收。分配/初始化中途失败不能仅因用户 kernel 尚未启动而释放记录缓冲。多 stream、异常退出和嵌套 capture 的具体支持范围在资格冻结前明示。两 stream 不新增为每后端无条件必达项：按既有 E03/执行合同，逐后端冻结 two-stream、host-thread、graph 等支持表；声明支持的两 stream 路径必须真实测试交错提交与 owner 隔离，不支持的路径必须在产生本次设备副作用前明确拒绝并验证恢复。不得冻结后缩小范围掩盖失败；不支持路径不能声称已保留跨 stream 行为。

**未来新增芯片的预期工作**：已有执行模型且 SDK 可复用时，主要补 target 匹配、编译接入、timer/logger、物理 decoder 与机制映射，并跑同一套合同和设备验收。新执行模型或 SDK 不开放必要机制时，可能需要新晚期 pass、隐藏参数 ABI、同步模型或 clock correlation；这些是真实工程成本，抽象不能消除。只有发现现有公共模型无法表达的新事实，才版本化扩展公共合同；不能预先承诺仅实现一个 adapter 就能移植。新芯片无需逐算子配置；普通可运行输入因通用编译结构不被支持而失败时，应修通用结构或明确产品限制，不新增按算子名/shape 的修补表。

### 8.8 当前证据与阶段放行

以下为 `b3e4a7f` 工程检查点的事实边界，不是新增验收结果；原件索引见 [原语检查点](../../integration/evidence/timeline-primitives-r001/README.md)。后续证据写工程记录，不把本节维护成重复实验日志。

| 项目 | 已有有限证据 | 仍不支持的结论 / 下一检查 |
| --- | --- | --- |
| NVIDIA timer 与普通异步结构 | 真实数学手工 timer 原语；普通 GEMM 的 PTX 含 copy/commit/部分 wait；新 native 构建、独立安装及 pass 合同检查 | 不是自动 timeline；未证明跨 SM epoch、最终插桩顺序、动态 group 关联及 Perfetto。实际 getter 为 64 位，但现有 packed record 仍为 43 位，不能当成全 64 位记录 |
| Enflame timer | 旧 advanced 自动 interval 的真实 raw 与整数校准边界；约 0.9774–1.0223 ns/tick 的独立界限 | 不是精确 1 ns 或共享 epoch 证明；实际边界、合法发布和异步解释待闭合 |
| Ascend | 现有 SDK/observer、连接及目标已核 | 本轮新 timeline logger、时间区间、actor epoch、动态关联尚无设备通过证据；旧 census 通过不能继承 |
| 公共时钟 | 整数/有理数及误差算术 CPU 正负例 | 算术正确不证明物理频率/epoch；新模块尚不能代表完整安装或三后端集成通过 |

放行顺序区分三层：**原语可继续开发 → 完整 P01 可进入该后端最终资格 → 全验收可交付**。允许在第一个后端做成完整纵向链时，预先调查其它后端原语；这不等于在公共合同冻结前宣称第二、第三后端已接入完成。当前没有任何后端整体 P01 通过。

### 8.9 面向后续芯片的最小接入合同与实施顺序

本节细化 §8.1–8.7 的实施接口，不声明下面的接口已经存在。本轮先服务三个实际后端；接口采用现有 hook/pass 的真实调用点，不要求独立插件包或统一设备内存布局。

| 接入动作（概念名） | 后端输入与输出 | 公共层的责任 |
| --- | --- | --- |
| `probe_target` | 实际 target、compiler/SDK/plugin → 依赖指纹、逐项能力和证据适用范围 | 在缓存查询前校验编译依赖；运行时设备/epoch 证据另行绑定，不要求运行时事实提前进入 JIT key |
| `plan_capture` | 请求、源身份及优化后结构 → manifest、所需记录布局、合法选择策略和机制规则版本 | 校验 source/binary 引用与预算公式；输出计划时区分静态需求和 launch 才确定的值 |
| `prepare_launch` | manifest、实际 grid/device/stream → 本次 owner、紧凑 slot→program 表、物理字节数、完成句柄 | 核当前安装具有匹配 storage/logger ABI，预算 admission 后分配；没有紧凑写址保证的旧 binary 不能配紧凑 buffer |
| `finish_capture` | 已提交 owner → completion 证明、不可变 raw、发布/loss 状态 | 跟踪安全回收；完成等待和 D2H 可由后端实现，共同约束是不能在设备仍写入时复用内存 |
| `decode_capture`（编排动作） | raw、manifest、owner 快照 → 物理 decoder 的 typed raw batch；另组合独立 provider 的 clock proof 与 mapper 的机制事实 | 物理 decoder 不探测设备、不构造 proof；编排层验证引用、完整性及资格，不重新识别厂商 ISA |
| `describe_mechanism` | 声明的机制规则版本及实际记录 → submit/group/wait 覆盖事实与缺失理由 | 检查集合/身份/代际完整性，决定逻辑关联、可比较时间箭头及完成包络的展示资格 |

这些动作可由现有对象组合完成。后端只提供事实与描述；通用验证器和 exporter 不以厂商名选择语义。物理 decoder、目标指令识别、发布协议和机制规则属于后端，并允许复用同执行模型的已验证实现。注册匹配必须检查实际型号/工具链条件；同品牌或相近执行模型不能继承未经验证的 clock/同步证据。

**能力按项递进**：`source_mapping`、`region_intervals`、`clock_scale`、`cross_observer_epoch`、`async_association`、`native_engine_activity` 和并发支持分别声明条件、证据及状态。它们不是单一等级开关：本地域区间可以先开发/导出；逻辑 group 关系在未证跨域时可以查看，但不能成为时间箭头；原生 engine activity 可独立接入。未达到完整目标的有效数据允许明确 partial 留存，不能把 partial 计为 P01 或最终资格通过。异步关联缺失不阻止修复普通区间，却仍阻止本轮完整交付。

**机制闭合**：每种已支持机制列出哪些 lowering/指令会改变其状态（例如 cp.async 的 submit/commit/wait）。manifest 与实际编译对象须说明这些状态变更均被覆盖，或明确排除范围；opaque asm、外部调用或优化生成的隐藏状态变更不能默认为不存在。无法证明闭合的实例保留原始区间并标关联不完整，不生成 verified edge。已知逻辑 group ordinal 不自动等于 loop iteration、物理 buffer generation 或精确完成时刻。

**紧凑选择**：预算要覆盖实际物理布局。若只选两个 program，设备写址使用紧凑 slot、header 仍写真实 program，未选 program 不得触及这些 slot；不能先按全 grid 分配再过滤。实际 grid 的溢出、cluster/多 CTA 映射和零 grid 由 launch 接入明确处理：合法零 grid 不产生伪调用事件；尚不支持的非空映射在设备副作用前拒绝。旧 full-grid ABI 可继续读取，但不能冒充新紧凑存储能力。

**实施顺序**：首个后端先闭合“普通区间→安全 owner→真实时间尺度→公共导出”，并行验证异步机制；完整 P01 仍要求异步和 Trace Processor。形成实际小合同后接第二/第三后端，不要求等待所有独立资格或 UI 检查才开始复用。新后端遇到接口缺口时先给出真实不可表达的事实，再决定版本扩展；不先搭完整插件框架。本轮不适配第四芯片，也不估算其工期。

历史实现对照（`34b0462`，仅表示当时状态）：NVIDIA 已有 64 位 record v2、物理 decoder 及绑定调用/binary 的 cp.async 逻辑组模型；尚无完整公共 timeline 入口、紧凑 storage/owner/clock/Perfetto 链，逻辑事实不具有 verified 时间箭头资格。§8.8 是历史原语检查点，不应读成最新源码仍只有 43 位记录。后续结果仅记工程记录，避免维护重复状态表。

### 8.10 适配成本的落实：组合已有能力，保留架构事实

本节是后续实现约束，不是已实现接口或第四芯片支持声明。当前 NVIDIA 已打通公开 raw 路径、安全 owner 和公共 raw schema；经过认证的 ns/Perfetto 及其它两后端时间 producer 仍待完成。当前可执行入口见 [timeline_runtime.md](timeline_runtime.md)，公共 raw schema 见 [timeline_events.md](timeline_events.md)，设备结果以工程记录及原件为准。§8.8 和 §8.9 的历史检查点不能当最新支持表。

**适配单位是目标及其工具链，不是算子，也不是厂商品牌。** “新增芯片容易”的实际目标是复用公共采集流程、身份、验证和导出，且可独立替换确实变化的设备部件。不得要求每款芯片重写全链，也不能把 NVIDIA 实现改一个设备名就宣称可用。

| 变化情形 | 预期复用 | 必须重新确认或实现 |
| --- | --- | --- |
| 同工具链、同记录/同步机制的新型号 | 原编译接入、transport、decoder、机制规则及公共层可按条件复用 | target 匹配、实际 getter/记录指令、内存可见性、时钟证据范围、资源限制及设备回归；证据明确覆盖的条件可复用，不盲目继承旧型号结论 |
| 相近执行模型、不同工具链或厂商 | 公共合同与消费者；经真实条件核验的算法组件 | 编译接入、timer/logger、隐藏参数、transport/发布、物理 decoder、机制规则；不按“都是 GPU”复用 CUDA 事实 |
| 不同执行模型/多类主体 | 公共身份、时间算术、完整性、源导航与标准导出 | 晚期执行映射、主体/时钟关系、记录发布、异步机制；公共模型不能表达新事实时版本化扩展，已有后端共同回归 |

**采用可组合部件，不强迫整套继承。** target 注册选择一组相容的编译接入、物理 transport/decoder、clock provider 和 mechanism mapper；同一部件可以供多目标复用，但组合必须有明确的 ABI/规则版本与实际目标条件。注册分发可以识别厂商，公共 owner/validator/exporter 不得靠厂商分支补齐业务语义。先用现有对象实现实际调用，不要求预建插件管理器、通用 ISA 或新的完整 IR。

这里统一的是观测合同：源关联、真实 observer、区间/端点、时钟证明、操作集合和依赖。执行 IR 与插桩位置可以不同。公共层保留 typed 的 submit/group/wait 覆盖、buffer/flag identity 与 generation；目标特有指令及其推导规则留在后端。`extensions` 只容纳说明属性；若一个新字段会改变配对、时钟、完成或依赖的判断，它必须进入版本化语义合同，不能藏进不受验证的字典。

**编译与运行时事实分两次绑定。** 编译输出不含自身 SHA 的 manifest 内容摘要，实际 binary 摘要在产物完成后绑定；不能要求编译器提前知道包含该摘要的文件自身 hash。编译阶段确定合法 site、记录 ABI、选择策略及布局公式；启动阶段用真实 grid/stream/device 计算具体 slot 和字节数，先做 admission 再分配。runtime epoch/时钟资格留在本次 capture，不靠旧编译缓存获得。所有产物相互引用并保留证据，不要求把全部信息塞回设备二进制。

**时间视图是派生数据，不改变 raw 合同。** raw ticks、来源和丢失信息不可变；clock provider 提供适用目标、getter、比例/误差、有效窗口和比较范围。公共层由这些证明生成独立的 ns 视图，exporter 只消费通过资格检查的视图与 edge。未验证的 raw 区间和逻辑 group 仍可保留，但不能因 exporter 能读它们就获得 ns 或时间箭头资格。clock 失效时重新验证或明确 partial，不重新运行应用来补数据。

**部件组合要检查兼容条件，而不只检查注册成功。** 每个实际被调用的部件提供版本化描述，至少覆盖下表。描述由已安装实现/实际产物产生，配置不能自行授予 verified。这里是数据合同，不要求新建五套类或实现通用插件系统。

| 兼容轴 | 至少核对什么 | 何时绑定 |
| --- | --- | --- |
| 编译接入 | target 条件、compiler/plugin 内容身份、manifest 版本、边界/marker 约束、隐藏 launch ABI | 缓存查询前绑定实现依赖；编译后核实际 manifest/产物 |
| 记录生产与解码 | logger/storage ABI、完整 timer 位宽、header/stride/alignment、发布协议、物理 program/observer 映射 | 计划中提供布局公式；启动前核当前 grid 的实际容量，解码再核 raw header/commit |
| transport 与 owner | device/context/stream 类型、初始化和完成条件、可回收条件、支持的并发范围 | 每次启动绑定；不能复用上一调用的完成句柄 |
| clock provider | 实际 getter/目标条件、tick 格式、比例与误差、有效窗口、epoch/可比范围 | 静态实现进入缓存身份；本次设备/epoch 资格在 capture 绑定 |
| mechanism mapper | 机制与规则版本、依赖的 manifest/记录字段、状态变更覆盖、动态 token/generation 来源 | 编译对象核覆盖，运行时记录核本次路径和损失 |

组合选择失败必须指出冲突的两端、预期/实际版本和失败阶段。静态已知冲突在本次 launch/设备记录初始化前拒绝；只能从实际 raw 识别的问题保原件并拒绝对应解释，不逆称已在启动前发现。声明兼容的部件仍须通过同一实际设备路径，不能用手写描述绕过检查。跨版本兼容若允许，列出具体兼容规则与正负例；未知必需版本明确拒绝。不同型号可共享 decoder 而使用不同 clock provider，同一目标也可按实际机制选择多个 mapper。

**资格按观测结论授予，不是全 bundle 一次盖章。** 至少区分 raw 完整性、源码导航、最终区域边界、时间尺度、跨 observer 可比性、动态逻辑关联、物理 buffer 复用及原生引擎活动。它们各自绑定所需的 binary/site/observer/clock/mechanism 与 capture 范围。时钟比例正确不证明某源码区域被包住；marker 对应机器 PC 不证明区域内部指令未越界；完整逻辑组不证明物理 buffer generation。一个 site 的合格证明不能覆盖其它 site，一个 clock domain 的证明不能覆盖另一个 domain。

公共层对请求的结论核其全部前提，并输出缺失的具体依据：例如合格时钟下的真实 counter 间隔可显示为 observer elapsed，但没有区域边界证据时不标为该源操作耗时；两端动态身份正确而缺跨域对齐时只保依赖事实，不画共同时间轴上的箭头。`partial` 的有效子集可以查看，但正常完整资格的必需项仍逐项检查，不能挑成功 site 充当全样本通过。以后补充证明只创建新派生视图，保旧 raw 和旧判定/所用 proof 身份；不重跑应用、不原地把旧结论改成已验证。

下表是资格依赖的最小索引，具体证明必须绑定上述适用范围。公共层校验引用、条件和有效性；最终机器/SDK 语义由对应后端的生产者证据证明，不由任意 `verified=true` 字段授予。

| 要展示的结论 | 最少需要的依据 | 缺证时允许保留什么 |
| --- | --- | --- |
| 源码导航 | 实际编译位置及来源身份；若声称快照则有匹配 snapshot/hash | 未保快照时明确仅为位置导航，不声称源码快照或成本归属 |
| counter 间的 observer elapsed | 同 observer 的真实配对读取、完整 raw 引用、适用的尺度/epoch/误差 | raw ticks 和配对状态；未证尺度不填 ns |
| 特定源区域经过时间 | 上一项及该 site 实际区域边界/路径、M:N 来源映射 | counter 间隔与源码导航，不称源操作耗时 |
| 逻辑异步关联 | 本次 operation/group 身份、机制规则/覆盖与完整性、wait 覆盖证据 | 明确 group-only/候选/歧义，不推物理复用或时间先后 |
| 物理 buffer/flag 复用 | 逻辑关联及实际 buffer/slot/flag 身份、路径与分代依据 | 未知物理身份/代际，不以逻辑 ordinal 代填 |
| 跨 track 时间箭头 | 目标动态关联、端点语义/边界与对应时钟可比较证明；先后解释满足端点不确定界 | 依赖事实/独立域视图，不能用公共时间轴暗示未证重叠 |
| 原生 engine activity | 真实引擎生产者给出的 begin/end 定义及本次记录、engine 身份与适用时钟 | observer/issue/wait 等已证语义，不改称硬件 busy |

**先建立可复现的最小证明，再扩大采集。** 每后端的第一份接入清单须明确以下四项：已存在且可复用的代码调用点、尚需实现的通用机制、物理语义的实际来源、能否用当前 SDK 取得的待验证证据。缺少最终边界证据时检查实际 lowering/依赖约束与机器对象；缺少 clock 证据时先做 getter/尺度/窗口验证；缺少物理 generation 时检查真实地址/slot 与控制路径的来源。不得先复制 NVIDIA 路径再靠调展示掩盖缺口；也不预先断言厂商 SDK 无法支持。每项失败保最小输入、命令、产物与失败阶段，区分实现缺失、尚未核验与实际环境/SDK 限制。

**实施和放行分段，完整门槛不降低：**

```text
A 普通数学 + timer/边界/发布原语
  → B 公开自动区间 + owner + 有证据的本地 ns + 公共导出
  → C 真实异步/复用关联 + 所需时钟可比性 + Trace Processor（完整 P01）
  → D 独立数学/故障/实际 UI/代码走查（最终交付）
```

A/B 允许推进下一项开发；只有 C 达到既有 P01，D 才完成本轮。第二、第三后端可先调查 A，不必等第一个后端的全部独立资格/UI 结束。选择真实机制的开发样本时先核 ordinary 编译对象，优先用确实能观察的语义；不得为跨门槛加入额外完成屏障或把逻辑序号冒充物理复用。遇到 getter、插桩位置、发布或关联无法闭合时保留最小复现，区分工程未完成和具体 SDK/环境障碍，不靠扩大测试集合绕过。

每个后端最终交付一份可复现的接入清单，至少包括：实际调用位置与组合关系、目标/工具链条件、各部件及 ABI 版本、复用条件/失效条件及重新核验动作、支持与拒绝范围、构建安装命令、真实 raw→公共事件→ns→Perfetto 证据，以及加入该后端引起的公共修改和回归。清单由现有文档/证据索引承载，不新增重复状态日志。验收见测试 §8.5；没有第四设备实证时只声称已检验三后端复用边界。

### 8.11 本轮落实方式：小部件、明确输入输出、先跑通再抽取

本节补充 §8.1–8.10 的工程落点；这些是目标接口职责，不声明同名 Python 类已经存在。适配成本主要由编译链开放程度和设备机制决定。公共抽象应减少重复实现，不以一个统一硬件 IR 或统一设备记录布局为前提。

| 部件 | 输入 → 最小输出 | 后续型号如何复用 / 替换 |
| --- | --- | --- |
| 编译接入与边界实现 | 普通编译资格、观测意图、实际 target → manifest、布局需求、带记录的实际对象 | 同工具链复用 pass/通用控制流处理；新工具链提供合法 lowering。源导航、执行边界、硬件完成分别声明 |
| 传输与物理解码 | manifest、实际 launch、owner → 完成后的 bytes → typed batch | runtime 相同可复用 transport；layout 相同可复用 decoder，两者不必一起替换。解码失败不丢 raw |
| clock provider | getter/目标身份、本次校准记录 → 有界比例/offset/误差及适用范围 | 同 getter 可复用算法；型号或 epoch 不同重新取证。算法实现与本次 proof 分离 |
| mechanism mapper | 实际对象的机制覆盖描述、本次动态记录 → operation/group/wait/复用事实 | 每种机制有独立规则；可组合多个 mapper。共同验证器检查引用与完整性，不反向猜指令 |
| 公共消费者 | typed batch、manifest、clock/机制事实 → 校验结果、ns 派生视图、Perfetto | 复用身份、配对、损失、时间算术、依赖完整性和导出；新增真实语义才扩 schema |

接口优先以现有函数/数据对象实现，只有两个真实调用者确实共享行为时才抽取公共实现；不为上述每行预建继承层。产品代码按能力及事件语义调用，注册入口允许 target 分发。后端调用后若仍需公共 exporter 解析某厂商 ISA 才能知道含义，说明交接尚未完成。

**边界实现允许不同，证据标准一致。** NVIDIA 当前开发候选包含显式 noinline 设备函数读钟和 SSA 值依赖；手工探针结果只说明该候选值得集成，不证明自动区域已经合格。设备调用不是公共必需 ABI；其它后端可使用合法的晚期插桩、原有 observer 或 SDK 机制。每种实现都要核对最终对象中的区域指令、控制路径和实际读钟关系。调用、memory clobber、volatile 或正 duration 均不能单独证明执行完成；不能为改善时间线注入新的完成 barrier。最终机器解析器必须认识真实函数/代码段/地址范围，不能假定所有指令均在入口函数或所有函数 PC 从零开始。

**把可行性风险先缩到最小输入。** 每后端先用运行时循环的有依赖数学和一份真实异步样本，依次核边界、发布、clock 和机制；某一步失败保原件并先修通用结构，不立刻扩大算子矩阵。clock 比例有界但跨主体 offset 不确定时，保本地域区间并显示误差；因果握手可约束 offset，但不自动证明比例、getter 读取误差或全局 epoch。尺度/offset/误差不足以分辨两个端点先后时，不宣称确定的重叠或先后，保动态依赖事实。物理复用仍须真实地址/slot/flag 与控制路径证据，不以逻辑 ordinal 代填。

**适配交付沿用现有文档和证据，不增加平行台账。** 每后端在接入清单给一条从公开 API 到编译、transport、decoder、clock、mapper、共同 exporter 的实际调用链，以及可重现的最小运行命令。列出复用/新增/公共修正和对应失败恢复测试即可；不要把文件数量、接口数量或测试 fixture 通过当作实际适配成本或设备可行性结论。第一后端纵向样本冻结后接第二、第三后端；需要修订公共合同可以修订，保兼容原因和既有后端回归，不强求设计永不改变。

### 8.12 本次实施合同：独立适配部件与公共数据交接

本节把 §8.7–8.11 落到实现和验收动作，不另建插件框架；下面字段是目标合同，不能理解为当前已提供同名 API。实现仍先闭合三个现有后端，新型号接入留到后续。

**按变化原因拆部件。** 一个后端注册项选择实际 compiler hook、launch transport、physical decoder、clock provider 和 mechanism mapper 的组合；这些可以是现有函数。decoder 不依赖设备执行，clock proof 不由 decoder 构造，exporter 不读取厂商 raw。每个部件或其输入变化时，沿实际依赖范围重核对应证据及结论；例如 getter 变更重核时钟，storage/decoder 变更重核端点身份和发布/解码，不能只盯工具链或自动失效/继承全部资格。同工具链、同物理 ABI、同 getter、同异步机制是四项不同的复用条件，不用“同厂商”代替。新增型号若需要改公共层，记录无法表达的事实、版本迁移和原三后端回归，不要求零公共修改。

**交接产物的最低内容：**

| 产物 | 必须携带 | 产生者 / 消费者 |
| --- | --- | --- |
| 编译 manifest | target/工具链身份、site/source M:N 映射、合法边界与未证原因、logger/storage/隐藏 ABI、布局公式、机制覆盖与规则版本 | compiler hook → admission、transport、decoder、mapper |
| invocation 快照 | capture/session 唯一命名空间、本次 binary、实际 grid 与 slot→program、observer、device/context/stream、选择/预算、owner 和完成条件 | launch transport → 完成回收、持久化、解码 |
| raw batch | 不可变 bytes/SHA、生产者与布局版本、发布/完整性信息、对应 manifest 和 invocation；失败阶段及已取得原件 | transport/原件存储 → physical decoder |
| canonical batch | 真实端点或原生事件的精确 raw 引用、site/observer/domain/epoch、记录顺序与配对规则、有单位的 loss、资格缺口 | decoder → 公共 validator、mapper、clock 派生 |
| clock/机制事实 | 适用 target/binary/site/domain/capture 范围、实际来源与版本、尺度/误差或动态覆盖/代际；未知项显式保留 | provider/mapper → 公共资格检查与派生视图 |

完成条件是运行时持有的实际句柄/条件，不要求序列化设备句柄；持久化部分保存可审计身份和完成收据。transport 在解析前持久化已经安全取得的 raw 及关联快照；失败的 decoder 不得阻止保留原件。解码重试只读同一原件，不重新执行应用。传输尚未取得完整 bytes 时只记实际取得部分和阶段，不能造出完整 batch。分配/初始化失败、取消、超时仍按 §8.7 的潜在写者规则处理。

**公共记录不能强制一种物理写入顺序。** 当前公共 schema 1 保留旧端点流语义；schema 2 支持 `endpoint_stream` 和 `paired_endpoints`（实际合同见 [timeline_events.md](timeline_events.md)）。某后端在区域退出时提交 start/end 一对，外层区域可能晚提交但 start 更早；保物理提交顺序和两字段各自 offset，不为满足单调性排序。配对完成顺序不是循环 iteration。schema 2 的 attempted/committed/retained/dropped/filtered/overwritten 统一以 canonical 端点引用计数；一个物理 pair 对应两个端点，同时另保 native 记录数量/单位。容量溢出是 dropped 还是 overwritten 必须由实际生产者决定。schema 1 的历史语义不改，新 raw ABI 不必等于公共 schema 版本。

**回绕兼容策略明确版本化。** 当前公共 schema 1/2 只接受无回绕的读数关系；它们的保守拒绝不代表物理 raw 无效。实际 timer 发生下降时仍须保原件、布局和关联快照，记录当前 reader 的限制，不能排序、修改 tick 或直接以新值冒充原值。支持短位宽回绕的后续公共版本必须保存 modulo ticks 与物理 sequence，由独立有效窗口/reset 证据决定是否唯一展开，在派生视图中另记展开值、圈数及证明；相同原件可离线升级重读。若本轮实际必需样本跨回绕，须实现该版本与兼容正负例才能过对应门，不能以 partial 绕过完整时间验收。end≥start 的样本也须排除不可判定整圈，沿用 §6。

**离线 adapter 与可用 profiler 分开验收。** 已有 Enflame 物理解码器能读取旧 advanced 捕获，不意味着 `detail="timeline"` 已支持 GCU。接入默认入口还要完成自动 planner、真实首末 program 的紧凑写址、调用 owner/完成、预算、raw 先保留及错误恢复。当前 decoder 只接受其实际支持的 program/actor；扩大范围应先实现并核验生产者/transport，不能只放宽 Python 校验。同理，机器 counter PC 映射不授予源区域边界，clock 有尺度不授予跨主体 epoch。

**先执行可证伪的最小纵向样本。** 第一条链使用普通 load→有依赖 runtime 循环→store，改变 K 证明相同 binary 的动态次数；另选 ordinary 对象中确有异步机制的样本。逐项得到 boundary、publication、clock、mechanism 和 export 证据。NVIDIA 当前普通/插桩 GEMM 的展开及调度差异尚未闭合，必须比较关键依赖和真实 copy/commit/wait/compute 关系，不能仅以指令总数相等放行。不能在无法保持的流水上承诺解释原执行；每组三方对照固定 ordinary 编译配置、输入、grid、数学和异步机制，仅改变观测密度；C2 每个调度变体各自做三方对照。普通 baseline 预登记 commit/group/wait 覆盖、消费前等待、允许 in-flight 的组和 compute 阶段关系；静态保留重叠机会不等于测得硬件重叠。必要时调整通用插桩位置或采样策略。GCU 的 ns 尺度和异步机制、Ascend 的新 timeline 发布协议也分别需要真实证明。没有证明时保 partial 和具体阻碍，不能用抽象合理性替代可行性。

适配成本最终报告回答：此次新增了哪些部件、复用了哪些实际实现、为什么需要公共改动、哪些设备证据必须重做。不给新增芯片固定天数或“写一个 decoder 即可”的承诺。原三后端未通过之前，不以第四后端或模拟注册冲淡缺口。

### 8.13 面向本轮实现的适配决策与失败边界

本节是 §8.9–8.12 的执行索引；不增加第四后端，不要求先做插件平台。新增芯片的适配成本不能由接口数量推断：本轮只验证公共链可以复用，以及硬件差异有明确承载位置。三后端实际资格仍按测试 P01–P10 判定。

**接入时先回答五个问题。** 沿公开入口找到实际调用者，然后依次判断：

```text
现有编译接入能否表达目标的 site/边界与隐藏参数？
 → 现有 transport 能否正确处理该 context/stream 的初始化和完成？
 → 现有 decoder 是否匹配实际布局及发布协议？
 → clock provider 的证据是否覆盖该型号/getter/本次 epoch？
 → mechanism mapper 能否覆盖实际生成的状态变更和动态身份？
```

每项可选择复用、补证或实现替代部件；不把其中一项变化扩大成全链重写。编译/发布/机制证据缺失是明确的接入工作，不承诺任意新芯片只写配置即可。公共消费者按事件语义和证据工作，保留实际角色、时钟域和多对多依赖；不以 CUDA stream/warp/SM 作为所有后端必需对象。

| 交接处 | 现有工程落点与实施约束 | 失败时如何处理 |
| --- | --- | --- |
| 编译 → launch | manifest 给类型化布局参数、指针元素单位、alignment、storage/logger/publisher/launch ABI 和选择策略；实际 grid 后绑定。GCU 当前候选 `i32*` 上的地址增量须由 byte stride 正确换算，不能直接传 bytes | 静态已知不相容在初始化/启动前拒绝；cache key 纳入生成代码的版本。改变 publisher 语义即使布局未变也须明确失效旧生成代码 |
| launch → owner | 复用 `timeline_runtime.py` 的预算和 owner 生命周期；后端 transport 负责实际流上初始化、提交、完成及读取。`hooks/timeline.py` 的 NVIDIA 实现是已有调用者，不是让其它后端继承 CUDA 行为的基类合同 | 在途初始化也属于潜在写者；异常时保留资源至可证明安全。旧 advanced 的逐 launch 同步不能作为默认 timeline 的完成实现 |
| bytes → decoder | `timeline_events.py` 承载公共合同；如 `timeline_events_enflame.py` 的物理 adapter 只解释自己支持的布局与协议。header 初始化、writer 到达、事件提交是三个不同事实 | header 坐标不能证明实际执行。缺 writer 到达、坏 commit 或越界引用时保 raw 并拒绝对应完整性结论；到达但没有选中 site 的合法空记录须单独表达 |
| decoder → bundle | 规范化与最终写文件均须保 canonical、manifest/invocation 和对应原 bytes；AI 视图、原件与 trace 引用同一身份 | 中间 Python 对象存在字段不算交付；落盘后重读并验证 raw SHA/长度/offset。解码失败不能阻断其它已完成调用的原件保存 |
| canonical → 派生视图 | clock/mapper 是独立提供者；共同 validator/exporter 只用已验证的范围和真实端点 | 无尺度不填 ns，无跨域资格不画共同时间箭头，无区域边界不称源操作耗时。raw 可保留，不降低完整交付门槛 |

公共复用的是预算、调用身份与潜在写者状态机，不是当前 NVIDIA 调用签名。loaded executable、execution context/queue 和布局请求可由后端类型化封装并校验；不得为满足当前正整数 function/stream 或 num_ctas 形状编造值。存在第二个实际调用者时才提取输入合同，不预建类层次。owner 在首次可能提交初始化前接管完整资源集合：device scratch、异步 H2D/D2H 所需 host staging、native/context 引用与完成依赖。完成收据覆盖全部异步访问；不能让 legacy init-first 回滚或临时 handle 析构绕过 owner 释放它们。

**取得 bytes 与校验合格分开。** transport 已安全取得的实际 bytes、长度和 guard 原件，即使 guard/header/extent/commit 检查失败，也须交给留存层并标失败，不能仅抛通用 read_failed 把证据留在局部变量中。真正未取得 bytes 的 D2H 失败另记；部分取得的 bytes 不能标完整。完成已证明且原件已持久化的资源可安全回收，不依赖其可解释性；D2H 自身尚在途仍按潜在写者处理。

**收尾在共同 deadline 内优先处理就绪者。** transport 有非阻塞完成查询时，先识别已完成 owner，用剩余预算取得并持久化其原件，再轮询完成未知者；不保证任意数量 ready 都落盘，不无限延长 deadline。耗尽时逐调用区分 completion_unknown、completion_observed_raw_pending、raw_ready_not_persisted 与 raw_persisted（状态含义，不强制同名 API），保恢复所需资源、已有 host bytes 与关联身份，不能报告 all_saved。超时后的显式重试另有有界 deadline、不得重放应用；完成已确认且原件与关联快照安全持久化的 scratch 可回收；后续重试不因保留已有 host bytes 而重新占用 device buffer。

**公开模式必须显式选择，不能悄悄扩范围。** 默认 `detail="timeline"` 与旧 advanced 请求分别测试；一个后端不支持 `runtime_first_last` 等策略时，应在其 lowering 前明确拒绝，不能把 `programs=None` 自动解释成全 grid。旧固定 program/旧 raw reader 可以保持兼容，但不能据此宣称新默认首末采集已经可用。

**真实覆盖由事件证明。** 对首末 program 均经过已选 site 的非空测试，分别核每个 observer 的实际已提交记录、原始字段、数学输出和 guard；一个末尾空 ring 不能被 host 写入的 program ID 掩盖。对控制流确实跳过全部选中 site 的合法样本，允许 writer 到达且零事件，不虚构 duration。设备写入范围须核实际 pointer lowering：byte stride 可整除元素大小，设备 slot 地址差与 host 布局一致，header/payload/commit 的最大 byte end 不超过 admitted extent，索引运算无溢出。保实际 IR/对象及布局推导；guard 是补充实证，跨大跨度越界可能跳过有限 guard，不能仅据 guard 未变证明安全。数学输出 tail canary 也不能代替 timeline allocation guard。仅有进程退出码或正 duration 不够。

**实现顺序不被抽象建设阻塞。** 先修通 GCU 实际 producer 和最终落盘链，再接默认 deferred owner/transport；并推进实际 clock、边界和异步证据。第二/第三后端需要的共同修正按真实调用抽取，已有合同按版本回归；最终仍须完成三后端、Perfetto、独立数学及额外三名代码审阅。本次三名设计 reviewer 只审合理性与可行性，不授予设备或代码交付资格。

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

异步重叠事件不得被强塞成同一 stack 上错误嵌套的 B/E；为独立 in-flight operation 使用独立轨道/协议。记录本身的时间不移动，不为排版把重叠事件排成串行。raw/canonical 保留提交顺序，不妨碍 exporter 生成满足协议的独立时间投影（例如合法排序或独立轨道）；投影不得改变端点、配对、原始 sequence、raw 引用或 occurrence 含义。嵌套 pair 的晚提交外层要通过实际 Trace Processor 验证，不能直接沿物理 append 顺序生成错误 B/E 栈。track/flow IDs 稳定且检测 collision；schema/消费者版本明确。

Perfetto 自身不能自动做源码文件导航的地方，提供可复制 source 位置与配套 bundle 源码页面；事件详情必须直接看见来源，不能要求用户再拼十份 JSON。

## 10. 预算、扰动与诚实比较

资格冻结时把预算按范围分别登记：单调用物理需求与上限、session live pending 字节与 owner 数、session 累计留存及 bundle 上限。初始“总 raw 8 MiB”指一次公开采集 session 累计保留的物理记录额度；每调用及在途额度不得超过它。header/padding/采集 guard 均计物理额度；原件只读重试不重复计数。当前 owner pool 的 8 MiB pending/64 owners 只是其中的在途限制，不证明累计额度已实现。host staging 及额外副本峰值另记，不用 device 字节数冒充总内存。物理 pair 容量和 canonical 端点数量分列，source/manifest 等仍计完整 bundle。预算变更须在开发阶段说明并资格前冻结，不能通过放宽预算处理资格失败。

保留初始小样本工程预算：冷编译 `min(300s,max(120s,3×普通同设置冷编译))`、导出 60s、完整 bundle 64 MiB。内部 trace 初始目标 16 MiB，raw 初始 8 MiB；默认选择和协议开销必须计入总预算。超预算不删除必要原始证据后伪称通过。

默认时间属于插桩程序。核对实际指令、无新完成 barrier、无全局记录锁，并比较疏/密两种观测方案是否改变阶段关系。Ascend/GCU 在可用稳定窗口记录普通与插桩参考和噪声；NVIDIA 允许真实时间线功能和时钟校验，继续不开展此前暂缓的独占吞吐、速度提升或开销比认证。不能借该限制跳过 NVIDIA 时间戳功能。

若时钟或插桩使某个现象不可分辨，按证据报限制。不能把“真实记录”直接说成“无扰动的真实执行”，更不能拿插桩程序变快当优化收益。

## 11. 实施次序与交付判定

实施统一采用 §8.10 的 A/B/C/D：首后端由 A 原语推进 B 公开区间/owner/本地 ns/公共导出，再到 C 真实异步/复用/所需时钟与 Trace Processor，冻结有实际调用者的小合同；第二、第三后端可先调查 A，并复用该合同完成各自 B/C。D 完成独立数学、故障、实际 UI 和三名额外代码审阅，修复并有限复核后 Git 交付。

三个后端均为必达；不等待铺完三后端才检查公共导出，也不以第一个后端的漂亮图替代其它后端。取得真实事件后才完善展示，不能用示意数据代替设备实现。具体通过条件、冻结规则和场景见 [测试设计](timeline_testing.md)，目标执行规则以根目录 goal 合同为准。
