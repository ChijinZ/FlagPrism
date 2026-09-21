# 燧原后端

FlagPrism 的 Enflame 后端通过 FlagTree 联合构建提供 `flagtree.debugger` 与
`flagtree.profiler`。仅安装原始 FlagTree 燧原 wheel 不会包含这些组件。

## 构建

需要 TOPS SDK、TOPSPTI 开发头文件，以及与 FlagTree 燧原分支匹配的 LLVM 工具链。
当前验证环境为 Python 3.12、PyTorch/torch_gcu 2.10、Triton GCU 3.6、TOPS Runtime 1.9.29。

```bash
cd /path/to/FlagTree
export FLAGTREE_BACKEND=enflame FLAGPRISM_BACKEND=enflame
export FLAGPRISM_SOURCE_DIR=/path/to/FlagPrism
export TRITON_BUILD_FLAGPRISM=ON TRITON_BUILD_PROTON=OFF
export KURAMA_LLVM_DIR=/path/to/llvm-fc83c68-gcc9-x64
export LLVM_SYSPATH="$KURAMA_LLVM_DIR"
MAX_JOBS=24 python3 -m pip install -e . --no-build-isolation --no-deps
```

构建从 `/opt/tops/include`、`/opt/tops/lib` 和
`/opt/tops/extras/TOPSPTI/{include,lib64}` 查找依赖。TOPSPTI 的公开 API
链接 `libtopspti.so`，由 SDK 转发到运行时；不是直接链接内部的 `libtopspti_rt.so`。

FlagTree 一侧也需要配套的构建注册、GCU launcher 和编译器改动；仅更新 FlagPrism 不足以完成联合集成。
SDK 二进制是外部构建依赖，不属于 FlagPrism 源码补丁。

统一验收直接运行本仓库的 Triton 算子，不需要 FlagGems。
若另外使用带自有编译缓存的算子库（例如 FlagGems 的 `LibEntry`），其缓存键应包含
FlagPrism instrumentation mode/config，避免复用带不同隐藏参数 ABI 的 kernel。
这类库的缓存与算子调度修复应由对应仓库独立提供。

## Debugger

```python
import flagtree.debugger as debugger

debugger.activate(auto_collect=True, level=1, addr_level=0,
                  record_capacity=65536, output_dir="debug-results")
# 在这里执行 Triton / FlagGems 算子。
debugger.deactivate()
```

`auto_collect=True` 在 TTIR 中自动添加数值/地址采集区域，因此动态生成的
FlagGems pointwise kernels 也能被覆盖，无需复制或修改 FlagGems 源文件。
默认值仍为 False，保留手工 collect markers 的用法。

GCU 调试编译会展开 block pointers；launcher 追加设备调试缓冲区指针，
运行后同步 GCU、回传和解码记录。设备内存与 pinned host memory 由 TOPS
Runtime 分配/释放，默认流和显式流都走对应的 TOPS API。

调试模式沿用 GCU 编译器的默认优化配置。数值摘要覆盖 load 和计算结果；没有其他可用数值摘要的 kernel 会采集 store 输出，
因此 `eye` 和 `zeros` 等纯输出 kernel 也能导出动态记录，同时避免重复归约。
GCU 的大 tile 采用单独上限，常量填充的摘要归约可在编译期折叠。
布尔值转浮点的摘要用一次真值计数精确推导全部指标，避免重复浮点归约导致寄存器分配失败。
调试耗时不能当作原始 kernel 的性能。其他 GCU 架构尚未真机验证。
GCU300 的地址采集仍有 64 位索引编译限制，统一轻量验收默认关闭地址采集。

GCU300 SDK 在部分标量摘要上会产生缺失的 `fabs(float)` libcall。
仅当确认出现该链接错误时，编译器才链接基于 IEEE 符号位清除的兼容函数，
并在编译元数据中标记 `debug_math_compat=scalar_fabs`。其他编译错误正常报错。
这条路径保持默认优化及完整 L2 范数摘要，不通过省略指标来规避错误。
常规算子数值、动态记录以及正/负/零标量的 L2 范数值已有真机回归。
测试入口检测到设备 context/Sip 异常后会阻止后续任务派发；并发中已经启动的任务仍需结束。
完整覆盖结论以对应运行的 summary.json 为准。

## L2 完整张量采集

L2 插桩新增整数和地址的 64 位存储，即使原算子仅使用 float32，也需要开启
GCU `enable_i64`。后端根据调试配置及插桩后的实际 payload 计划启用此选项；
全局 L1 内的局部 L2 区域同样适用。没有完整 payload 的 L1 和普通执行保持原选项。

当前 GCU300 SDK 的布尔向量直接转 int64 路径存在缺失设备符号，完整插桩叠加设备摘要归约
还会触发寄存器分配失败。Enflame 的 L2 lowering 使用 i32 低字/符号高字打包窄整数、连续
写入 64 位 payload，并使用协议允许的 i32 逐元素偏移计算。导出的 int64 ABI 保持一致。

L2 的计数、均值、最值和 L2 范数摘要从**实际回传的完整设备张量**在主机计算，避免设备重复归约；
没有自身完整 payload 的局部 L1 操作仍保留设备侧摘要。完整 L2 报告以 `summary_source=host_from_device_full_dump` 明确标注来源。
混合级别报告标为 `mixed_device_and_host_from_device_full_dump`。
完整张量仍来自插桩执行及 TOPS 回传，不能用 CPU 参考数据代替。摘要按 float32 计算，
不同归约顺序可能产生浮点舍入差异；采集耗时不是性能基准。

## Profiler

```python
import flagtree.profiler as profiler

session = profiler.start("profile", backend="enflame", hook="triton",
                         mode="runtime_base:runtime_host_timing_fallback=false")
# 在这里执行 Triton / FlagGems 算子。
profiler.finalize(session)
```

也支持 backend 名称 `gcu`/`tops`；不指定时根据 Triton target 自动选择。
TOPSPTI runtime/driver callbacks 建立 correlation ID 与 Triton scope 的映射；
kernel activities 提供设备 start/end（ns）、device ID、stream ID 和 kernel 名称。
活动按 API 启动时的会话归属过滤，暂停期间的 kernel 不计入报告。
同一 vendor 暂不支持重叠会话；拒绝创建不会残留无效会话路径。
flush 会同步当前 GCU 并检查 dropped records；无效时间戳或丢失记录报错。

`finalize()` 直接输出以会话名称命名的目录，包含 `ai/`、`report/` 和 `manifest.json`，
不需要额外报告命令。TCU 默认关闭。基础 kernel 时间来自设备，
没有 host timing fallback。此实现没有声明支持硬件性能计数器：必需但未支持的
指标报错，可选指标记录 unsupported 原因。

## 细粒度 Profiler 报告

Enflame 采集器默认请求 TOPSPTI kernel、runtime、driver、memcpy 和 memset
activity。无需修改算子或追加编译插桩；在现有 FlagTree 联合构建基础上重新编译
FlagPrism 即可。建议先完成编译和设备初始化，再开始性能采集。

`ai/events.jsonl` 保留设备时间戳、kernel 名称、grid/block、context/stream、
correlation ID、API 线程/返回码、拷贝方向/字节数和 memset 参数。成功的
`topsMalloc/topsFree/topsHostMalloc/topsHostFree` 回调补充地址和分配/释放事件。
新增 API 和内存 activity 不计入原有 Hatchet kernel 时间，profiler 自身 flush
引发的同步不归入用户 API。用户主动调用的同步仍正常采集。

采集器输出通用 `activity.*` 字段，TOPSPTI 原始枚举/flags/返回码保留在
`enflame.*` 命名空间。交互报告、命令、数据约定与其他芯片接入方式见
[通用活动报告](../Profiler/docs/activity_report.md)。报告层不解释 TOPSPTI 枚举。

解释数据时请注意：

- 活动覆盖是设备首末记录之间的区间并集，不是 SM/Core 利用率。
- 有效 GB/s 来自记录的字节数和耗时，不是硬件实测 HBM 带宽。
- 分配曲线只覆盖捕获期间的成功 API 调用，不等于总显存或缓存分配器中的张量生命周期。
- 当前 SDK 没有可用的 driver callback API 条目，真机未返回 driver activity；
  不应将空数据理解为程序没有 driver 开销。
- 当前接口没有提供硬件计数器、cache 命中率或 kernel 内部 warp/Core 时间。
  这些信息不能由本报告推算，进一步支持需要 SDK 能力或编译插桩。
- 全类别采集有额外开销，长时间运行会增加主机内存和输出体积。性能对比应使用相同
  设备、输入、启动配置和采集设置。API 时间可能嵌套，不能和设备时间直接相加。

专项回归：`python3 -m pytest Profiler/test/test_enflame.py Profiler/test/test_report.py -q`。
统一算子验收仍使用 `test.py --stages profiler`。

## 验收

```bash
cd /path/to/FlagPrism
python3 test.py --jobs 8 --devices 0,1,2,3,4,5,6,7
```

同一份算子与输入依次运行 debugger_l1/debugger_l2/profiler；采集失败后补跑普通执行。
普通执行也失败时 WARNING 放行；普通执行成功则 ERROR。最低覆盖数和完整失败语义见
[统一测试说明](TESTING.md)。WARNING 不代表采集成功。

验收使用清单中的轻量输入；不代表所有 shape、dtype 或完整模型均已验证。

摘要 JSON 中有限值保持数字；非有限值使用字符串 `"NaN"`、`"Infinity"`、`"-Infinity"`，并保留类型与 display 字段，避免生成非法 JSON。

历史 FlagGems 清单的测试记录仅代表当时版本；当前自带算子清单与结果见运行生成的
`manifest.json` 和 `summary.json`，不能直接沿用旧清单的通过率。首次 L2 编译默认允许 600 秒。

## TOPSPTI 接口覆盖与后续价值

以下核对以当前机器 SDK 的 TOPSPTI API v4 头文件为准，不代表所有 SDK 版本。
本机实际调用 `topsptiGetVersion` 返回 4，`topsptiGetThreadIdType` 返回 0（默认 pthread ID）。
五类 activity 中有文档意义的字段已基本保存；reserved/pad 不应采集。
`completed` 虽已保存，但本次 kernel 记录为 0，按 SDK 定义表示未知，不能计算子 kernel 等待时间。

| 可获取但尚未使用的信息 | 入口 | 价值与约束 |
| --- | --- | --- |
| 启动请求的共享内存、扩展启动属性、函数/流句柄、symbolName | launch callback 的 `functionParams`、`topsLaunchConfig_t`、`symbolName` | 高：解释同名 kernel 的配置差异；是请求值，不是实际占用率或寄存器使用量 |
| stream/event 创建、记录、等待、同步和销毁参数 | Stream/Event callbacks | 高：建立主机提交的依赖图，定位同步阻塞；句柄生命周期需跟踪，不能把 API 时间等同于设备等待时间 |
| 拷贝源/目标地址、异步 stream、symbol offset | Memcpy callbacks | 高：关联缓冲区、拷贝与分配生命周期；地址不解引用，需覆盖不同 memcpy 参数结构 |
| SDK/运行时版本与更多设备属性 | 版本接口、Device callbacks/TOPS Runtime 查询 | 高：已有 Device.cpp 查询架构、频率、位宽和处理器数量；仍可补充版本、名称/总显存等并接入报告。静态属性不是动态计数器，避免在 SDK 回调内重入查询 |
| 实际可用/总显存查询结果、host registration 与映射 | `topsMemGetInfo`、HostRegister/Unregister、HostGetDevicePointer callbacks | 中高：补充采样点和 pinned/mapped memory；仅捕获用户查询会稀疏，主动轮询有开销；注册不等于分配 |
| Graph 实例化/执行/销毁句柄 | Graph callbacks | 中高（Graph 工作负载）：可关联重复 graph launch；当前 activity 没有 node ID，不能据此完整重建节点执行 DAG |
| 系统线程 ID | `topsptiSetThreadIdType` / `topsptiGetThreadIdType` | 高：默认 pthread ID，系统 TID 便于和 CPU trace 对齐；SDK 可能不支持，必须在采集前设置并处理恢复 |
| 对齐的时间戳与采集边界 | `topsptiGetTimestamp` / timestamp callback | 高：记录会话/采集窗口，改善首末事件之间覆盖率的解释；暂停区间需单独处理，换时钟必须在启用 activity 前 |
| API 版本、支持的 callback domain、callback 名称 | `topsptiGetVersion` / `topsptiSupportedDomains` / `topsptiGetCallbackName` | 高：能力发现与降级诊断；不保证 domain 内存在实际可采的 API |
| 周期性 flush | `topsptiActivityFlushPeriod` | 中：降低延迟与 SDK buffer 压力；本地事件容器也需流式输出，单独开启不会限制总内存 |

已采集但尚未深入分析的还有 grid/block 配置、memory kind 和 flags；
目前保留在事件详情，后续可增加配置分组、pinned/pageable 等类型解码。
已使用 `topsptiActivityGetNumDroppedRecords` 检测丢失，不能列为未接入功能。
`correlationData` 是客户端保存 ENTER/EXIT 状态的空间，不是新的硬件信息。
当前公开头文件未提供 PMU counter、cache hit、实际 occupancy、指令/warp 采样接口。
优先补启动配置、stream/event 依赖和版本/时钟元数据；它们可在 FlagPrism 的 Enflame
采集器内实现，无需编译器插桩。kernel 内部区域计时仍需另外评估 SDK 或 FlagTree 插桩能力。

## TCU 硬件计数器

`topsprof` 软件包提供的 `/opt/tops/bin/tcu` 可以采集 TOPSPTI activity API 之外的指标。
已在 GCU300 / TCU 1.9.29 上验证 `SIP/BUSY`、三类 instruction efficiency、
L1 instruction-cache miss 和两类 prefetch，共 7 项。它们不包括数据 cache 命中率或 HBM 流量。

TCU 默认关闭。正常使用 `profiler.start()` / `finalize()` 即可采集活动并自动生成完整目录，
无需改变启动方式。只有需要额外硬件计数器时，才使用已有 profiler 命令行入口显式开启：

```bash
flagtree-profiler --backend enflame --name profile-run --counters --hook triton workload.py
```

该路径在同一次进程运行中启动 TCU 和 TOPSPTI，结束后直接输出统一目录。
默认只请求 `SIP/BUSY`，`--replay-mode none`，不会静默重跑应用。
不同分组的计数器可能需要重放；仅对可安全重跑的程序显式设置，例如：

```bash
flagtree-profiler --backend enflame --name profile-counters --counters \
  --counter-metrics SIP/BUSY,SIP/1D_EFFICIENCY,SIP/L1_ICACHE_MISS \
  --replay-mode application --hook triton workload.py
```

TCU 的 CSV/TCD 和日志保留在 `raw/`；结构化计数保存在 `ai/counters.json`。
它覆盖启动的进程，可能包含 activity 会话外的初始化或预热，不与单次执行强制关联。
应用重放时，activity 文件来自最终执行，计数器可能来自多次执行；不作为同一次 launch 的联合观测。

报告新增通用 counter 分组、指标值/单位与逐实例 min/max/mean/sample count 展示。
TCU 数据的 scope 是 kernel 配置聚合；kernel 名称不能用于将它强行绑定到其他 capture 的某次 launch。
该 CSV 没有设备标识，Die/SIP 只是工具内实例编号；不能推断全局设备 ID。
无时间戳时页面只展示聚合观测，不制造时间线。计数器采集影响执行时间，耗时不是无 profiler 基准。
`BUSY` 包括等待；`1D/2D/MSF_EFFICIENCY` 按工具定义展示，不能直接等同于硬件峰值计算利用率；
`L1_ICACHE_MISS` 是指令缓存 miss 请求次数，没有总请求分母，不能计算 cache 命中率。
