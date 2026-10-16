# C2 独立静态代码走查：运行时、native ABI 与记录完整性

## 结论与边界

发现 **1 个已证实 major：GCU census 的 runtime layout 可以让公开 callback 绕过 native 分配前的容量/预算检查**。未发现新的、证据充分的 blocker；另有三个有限风险，不能作为已发生的硬件错误。原 Ascend eligible state 失败仍未解释，本报告不把后续通过控制算成关闭，也不把非原子源码单独当成用户 race 的证明。

审查冻结为 `FlagPrism-usability-r10` 的 `0f6e1da62d6b789c9742e526d6bfc95274b8b649`。实际 `git rev-parse HEAD` 一致、工作树初始无修改。对 `ce00df63828c5e657c0307d7b69c99706dc12d49` 的 diff 只有 11 个 tests/docs 文件；对 native build input `1f914a8b03bc3fe4fe73c1be49f22b91babdc6a5` 的指定 native/compiler 目录 diff 为空。报告的行号均指该冻结源码，不评价 root 此后可能安排的修复。

本席按 C2-prompt-template 独立工作：没有读 peer 报告、产品席结论、method_impl_record 意见、任何 private 数学/IR；没有访问设备、连接服务器、安装依赖、运行测试或执行产品模块。只进行了源码阅读、Git 只读检查、用 Python 标准库离线读取已经保存的公开归档并核对原始 bytes，以及写本报告。模型请求配置由 root 的工具调用保留；本报告不以模型自述猜测实际模型。

## C2-01 — major — GCU runtime layout 冲突绕过 census 分配前保护

**位置与完整触发链**：

1. `Debugger/python/flagtree_debugger/api.py:1463` 将公开 `runtime_metadata_builder` 的返回值直接 update 到运行时 metadata。builder 可以返回 `{'record_layout': ''}` 或其他非 census layout。
2. `api.py:1469` 对编译期 census layout 绑定真实 launch grid，确实防止 callback 缩小 grid；但 GCU 没有与 Ascend `api.py:1497` 对等的 layout/stride 一致性检查。`api.py:1505` 的 `setdefault` 会保留 callback 的冲突 layout。
3. `Debugger/python/Bindings.cpp:632` 仅以 **runtime** `recordLayout == "gcu_site_census_v1"` 进入 GCU guard。编译 metadata 已经有 `debug_record_layout="gcu_site_census_v1"`，却不参与该入口条件。改掉 runtime layout 后，`Bindings.cpp:641` 的编译 S/实际 stride 检查、650 的实际 grid×S、655 的 cell/byte/index budgets 及 660 的实际容量设置全部跳过。
4. `Debugger/lib/Frontend/Bridge.cpp:96` 因此保留原 `debug_record_capacity`；`Bridge.cpp:98` 的 census payloadBytes 为零。`Debugger/lib/Runtime/TransferEngine.cpp:1060` 的另一个容量检查仅处理 Enflame full payload，不能保护 census。
5. 实际已编译 GCU writer 不读取 callback 的 layout，也不按 header capacity 截断。`Debugger/lib/Instrumentation/Passes.cpp:3064` 用真实 `pid*S+column` 计算 cell，3073 读取旧值，3094 发布 64-byte cell，没有容量分支。这正是依赖分配前 guard 的 writer。

**可确定的静态反例**：编译 metadata `debug_record_capacity=64`、S=8，实际 grid `(13,1,1)`，运行时 callback 只覆盖 `record_layout=''`。native 分配 `32+64*64=4128` bytes；真实 writer 需要 `32+13*8*64=6688` bytes，最后 cell 起点 6624，末字节 6687，超出分配边界。即使原容量恰巧够大，预算/索引保护仍会被跳过。之后 `attach_export` 因长度或 header 不符而报错，发生在 kernel 之后，不能替代分配前拒绝。

编译 S 的可信字段已经存在：`debug_records_per_instance`、`debug_census_sites`、`debug_census_version=1`、`debug_record_size=64`；预算是 `debug_max_census_cells` 与 `debug_max_census_bytes`。无需增加逐算子信息或从 padding 推测 S。

**预期**：编译与运行时 layout/stride 不一致时，在任何设备/host buffer 分配及原 kernel launch 之前明确拒绝。native 也应独立从 compiled layout 识别 census，不能只依赖 Python 修正。

**实际**：静态控制流允许 callback 的冲突 runtime layout 关闭全部 GCU census guard；原 writer 与 allocation 继续采用不同 ABI。这里确认的是可达的安全保护缺口及确定的越界地址算术，不声称原公开默认 runs 已发生越界，也没有在本机动态复现。

**最小验证建议（由 root 在授权服务器 Docker 执行）**：

- Python regression：真实 census metadata 或等价 fixture，公开 `debugger.activate(runtime_metadata_builder=lambda *_: {'record_layout': ''}, output_dir=None)` 后，调用公开 `debugger.prepare_kernel_launch(metadata, actual_stream, {'grid': (13,1,1)}, kernel_args)`；使用 recording native stub，断言错误在 `prepare_launch` 被调用之前发生。已有 CompiledKernel.metadata 即可，不需再编译或执行 kernel。覆盖空串、任意字符串、`selected_dynamic_timeline_v1`，并保留合法 matching layout control。
- native regression：绕过 Python，给 `_native.prepare_launch` 原始 census compiler metadata，但 runtime layout 分别为空/其他格式；用 HOST/spy adapter 或既有分配计数方式断言分配次数为零。另测矛盾 `records_per_instance`、compiled/runtime 双向 layout 冲突、合法 exact budget、重复 reset。
- 可复用 `gcu-final/runtime-public-evidence.tgz` 内 `chijin-r11-gcu-boundary/controller.py` 已保存的真实 metadata、S=8、grid13 admission harness。该 harness 本来就做零 kernel 的 prepare/finish/reset；**不要把非法小 buffer 传给设备 kernel 来复现越界**。

## 已读链路与公开证据检查

实际入口链阅读了 CLI 的 supervised worker 与单次 script 执行、`profile.start/finalize` 的 backend/request 选择和异常清理、LaunchHook 的同 metadata 对象 invocation 绑定、native instrumentation hook 的 allocator/preflight/stream 同步/epoch wrapper 恢复、Debugger 的 generic launch context、native prepared handle、TransferEngine 分配/清零/回传/释放、三种 census writer 和相应 decoder、`reconstruction`、`fine_grained.require_automatic_records`、`_capture.export_capture` 的留证/manifest/不完整导出路径。

静态上看到的有效保护包括：NVIDIA 两层 launch/run lock 与图捕获拒绝；NVIDIA preallocation patch 在 global/profile scratch 之前使用实际 function/grid；GCU/Ascend 的逐 launch 新 buffer 和 stream 上初始化；Ascend source marker 自己的六坐标而非 physical block 替代；紧凑物理 v2 的三 bank×真实 S 分配；全 grid 饱和统计，而非只检查显示 program；GCU header/padding、Ascend 未分配 bank/column 和零 header 校验；NVIDIA raw observation journal 在 ack 前持久化；CANN worker capsule 的 retain/release、capture epoch、late/duplicate/query-failed 状态。没有从这些检查推出任意并发、任意 SDK 或所有编译结构的保证。

读取的安装索引是 run-011 `install-audit/summary.json`、`callsite-packages/{summary.json,notes.txt}`、`ascend-public-build/index.json`。三个 callsite refresh wheel 的 source 均为 ce00df6，native input 为 1f914a8；这是对已有原生构建字节的当前 Python 刷新，不能称为这一步重新构建了 C++。当前 wheel SHA 分别为 NV `847d114fa5e322a9a3f44fb9cb58c19e4d48aa3774d1a400998f42983ab3f0c1`、GCU `600209baaa3ba08abaff9f6a5dc4afc17596df46a60eadebeecf2e4392712288`、Ascend `0719b3ee67f2468c19ae615ccf5b63c6da0bd547933644e7cf155c5ff5d8271d`。没有独立重算服务器 wheel 或重做整个 object/link 图，构建来源结论受这些已存索引范围约束。

对 `public-hardware-regressions/` 中五个公开 evidence tgz，独立离线读取了每个原 `ai/observations.json`，逐个复算 raw SHA、全物理 count/flags、descriptor SHA、每条 counter event 的 raw_offset/count 对应，并检查 counter 的 clock/start/end/duration/iteration 为 null。GCU 检查每个 64-byte cell 的 56-byte padding；Ascend 检查完整三 bank 所有选中/未分配 columns 和零 header。结果如下，未发现上述字段矛盾：

| 归档 | bundle | 实际 capture | 扫描物理 slots | 非零 cells | 饱和 cells | 映射 counter events |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| nvidia-public-evidence.tgz | 22 | 22 | 432 | 188 | 0 | 161 |
| gcu-public-evidence.tgz | 12 | 14 | 176 | 172 | 0 | 110 |
| ascend-public-evidence.tgz | 9 | 9 | 216 | 72 | 0 | 72 |
| ascend-mixed-public-evidence.tgz | 2 | 2 | 48 | 32 | 0 | 32 |
| ascend-state-public-evidence.tgz | 16 | 16 | 768 | 448 | 0 | 236 |

NVIDIA 的 432 是包含对齐 padding 的 8-byte slots；不是把 padding 算成 compiler 观测 cells。合计 63 个 capture、611 条 counter event。此检查是对保存字节的审计，不是重新跑 math，也不把 bundle 数误写成 capture 数。

同时读取了 root-bundle-capture-accounting、independent-worker-aggregate、NV/GCU runtime-public-evidence 中的 boundary result/commands/controller 记录。已存 NV negative budget 记录显示 scratch allocation 前拒绝、device calls 全零；四次显式流切换保持相同 binary 与对应实际 state。GCU exact-budget 两次 reset 是零 kernel/所有 cells 清零证据；饱和故障明确是注入记录而非真实 UINT32_MAX 次访问，状态为 incomplete，随后恢复成功。它们支持各自已测边界，未覆盖 C2-01 的 layout 冲突，也不构成 GPU 性能测量。

## 待验证风险与保留失败

1. **Ascend 原 eligible state 失败未解释。** 只读 `qualification-final-safe-v3` 的三 safe aggregate、scope/index，未读 private kernel/IR。NV main48、GCU main48、worker8、Ascend supplement8 及旧36回归的完整 gate 结果有安全汇总；Ascend 原24 baseline 中23 eligible，46 profiles 只有45完整通过，另1实际 state 断言失败且缺 math receipt。两个 exact passing profile 与原失败 loaded binary bytes 相同，仍不能补猜原 state 值或删除失败。公开 state 控制有16 ordinary+16 default，保留日志均 `[1,1]`、math/input/output guards通过；这也是有限控制，不是一般无重放证明。

   在公开 state tgz 首个 bundle 的 AIV **原** LLVM，state load→+1→UBUF→helper 真实存在，外层最终 helper call 有 `GET.SUBBLOCKID()==0` 分支；wrapper 构造 memref 后调用 `_mlir_ciface_store_ubuf_to_gm_1d_int32_t`，该 ciface 仍仅 declare、无实现。不能把此公开控制的分支移植为 private 失败的 ownership 结论，也不能仅据源码非原子 RMW 就断用户 race。普通 actual LLVM 没留的证据缺口仍在。本席没有找到源码中能解释原失败的第二次自动执行；这不是证明它不存在。

2. **NVIDIA impossible-plane/padding 的专用完整性校验不足。** `nvidia_census.py:70` 构造 sites×actors 的完整矩阵，site origin 已有 `census_actor`；`source_census.py:133` 只校验矩阵内的 count/flags，没有拒绝非该 site owner 的 actor plane 里出现合法非零 count，也不读 128-byte 对齐尾 padding。GCU/Ascend 有专用 transport 校验，NV producer 尚无对等原始 bytes 检查。此次保存 raw 未见这种异常。这里列为待验证完整性风险，不声称现有 worker writer 写错或已有报告混 actor；有限补充验证可对一个真实 worker descriptor 的未分配 plane/尾 padding 做单字节故障，再看是否必须拒绝。

3. **legacy NVIDIA interval host-buffer 扩容异常安全。** `Profiler/csrc/lib/Profiler/Instrumentation/InstrumentationProfiler.cpp:232` 先 free 旧 pinned hostBuffer，再通过同一成员地址 allocate；若 replacement allocation 抛错且 SDK 未清空输出，`doStop` 的62–64行仍可能释放旧指针。没有 allocator 故障证据，SDK 出错时输出指针行为没有在本次走查中确认，因此只列待验证风险。默认 ≤8MiB census 走 Python tensor 回传，不走这个 >64MiB interval 分支。可用一次 fault-injected Runtime 验证异常后 cleanup 只释放一次、下一会话可恢复；无需真实大 GPU 负载。

以上风险不要求新增形式证明或无限扩大测试。原 Ascend 未解释失败和 C2-01 是当前结论中必须保留的两项；后续新证据只能附加说明，不能改写原证据。

## 实际阅读模块与未覆盖内容

重点阅读：`Profiler/python/flagtree_profiler/{cli,_deadline,_capture,profile,source_census,nvidia_census,ascend_census,ascend_abi,ascend_driver,ascend_compiler,ascend_launch,ascend_clock,observations,reconstruction,fine_grained}.py`，`hooks/{launch,instrumentation,hook,graph_guard}.py`；`Debugger/python/flagtree_debugger/{api,runtime,compiler,gcu_census}.py`；`Debugger/python/Bindings.cpp` prepared-handle/admission 部分；`Debugger/lib/{Runtime/TransferEngine,Runtime/BufferLayout,Frontend/Bridge,Instrumentation/AscendProgramAnchor}.cpp`；`Instrumentation/Passes.cpp` GCU census writer/dispatch；NVIDIA `AutomaticScopes`、`ProtonToProtonGPUPass` census/partition scratch 与 `PatternProtonGPUOpToLLVM` census lowering；AscendLateObserver 的 census marker/actor/instrumentation 部分和 AscendSourceCensus helper；native InstrumentationProfiler/CudaRuntime；CannProfiler 的 worker receipt registry/lifecycle 与 CannLaunchReceipt ABI header；三后端指定 build/launcher/source-census patch 的相关片段。不是上述每个大文件的逐行全覆盖。

未重新构建/安装、未动态故障复现、未访问厂商库/设备；未验证 ciface 黑盒实现或反汇编最终设备指令；未读取任何 private qualification 数学/IR；worker qualification 只读安全 aggregate；未把公开开发样本当未见资格；没有进行浏览器交互和整套 report renderer/XSS 审查；没有完整遍历 native-only CUPTI/TOPSPTI 所有 SDK callbacks、非本轮三后端、Debugger 数值摘要/L2 及所有编译 pass。安装审计仅按明确已存索引与指定 source diff 核对，不替代整个来源图审计。
