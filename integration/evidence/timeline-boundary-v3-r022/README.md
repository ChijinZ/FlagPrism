# NVIDIA boundary v3 候选、原件重验证与真实回归

这是开发检查点，**不是完整 P01、源区域边界、ordinary 流水保持、时钟精度/跨主体 epoch 或异步资格通过**。所有产品构建、导入、测试、真实数学、LLVM 诊断和 Trace Processor 都在已有服务器 Docker；没有修改论文或旧 Study。本轮没有启动最终三名代码 reviewer。

## 代码与安装

自动 NVIDIA 路径改为 boundary ABI 3：实际模块 global 初始化为 0、每函数一次 volatile 读取；begin 用有真实寄存器依赖的 masked XOR 转发，end 通过结果依赖条件分支调用零参数 noinline getter。没有新增用户 kernel 参数或完成 barrier。显式 version-2 IR 保旧 lowering，旧 interval/count 不引入新 anchors；未知/错类型 ABI 明确拒绝。plan、native 检查与 instrumentation cache key 均使用版本 3。

旧向量谓词原语的 end 被实际 PTXAS 降成无条件 CS2R 后 SEL，未取得所需依赖；保留该证伪原件。标量条件分支/call 原语才显示所需候选机器依赖，随后接入自动路径。原语和数学通过不自动授最终区域资格。

[native-build.json](native-build.json) 记录实际独立全量构建：558 个构建任务，native wheel SHA `26e1881a898db39f360af375c984bbaf9fc3fd8f6d0916eac7d790305a0cae21`。parent 对留存 patched archive 建立明确的本地 snapshot commit，不能称其为 upstream ancestry。后续只改 Python 时，[输入桥](native-source-bridge.json) 逐 byte 核 C++/CMake 等输入后复用该 native；没有把重包装称为新 C++ 构建。

最终 Python wheel SHA `e4519e14c5acf96c8c50bd26ff78501c115a8f96745109425bf72b2749977fc3`，601 个安装成员逐 byte 验证。当前源码、真实 native 输入与实际安装的相应文件 SHA 见 [source-proof.json](source-proof.json)。开发容器/解释器：

```text
ssh alias: zhangquan_pro6000
Docker: chijin-study-pro6000
Python: /workspace/chijin-timeline-r022/runs/install-v2/output/venv/bin/python
```

复用已登记的 vendor-dependencies.pth 依赖桥；无开发机 PYTHONPATH 或安装后热补丁。通用构建/采集入口见 [runtime](../../../Profiler/docs/timeline_runtime.md) 和 NVIDIA 既有 recipes。本检查点不声称完整三后端 source-build/独立资格已经结束。

## 原失败与离线修复

r021 首次安装的五 dtype 普通数学、input/tail/State 和实际模块 global 四字节为 0 的读取通过，最后机器 mapper 因 `CS2UR URn,SR_GLOBALTIMERLO` 未识别而失败。保留首次失败、PTX/CUBIN、工具输出、raw 和 canonical；[数学收据](five-type-math.json) 包含 FP16、BF16、FP32、FP64、int64 的实际结果。

新规则只接受 CS2R/R 或 CS2UR/UR 的对应 bank，并保持原有精确 marked PTX、debug line、实际函数/ELF 范围和 text/JSON 一致性检查。wrong bank、HI/32-bit、未知 opcode 不授单位。旧 failed map 可由完整已留存对象重新验证；成功旧 map 仍须与新解析一致。离线输出另存 derived/machine revision，首次 status 不改，不调用工具或重放应用。仅单位证明不授边界、精度或共享 epoch。

首次 r022 CPU 负例把“缺文件”的预期写成 OSError，而安全 bundle reader 正确返回 ValueError；只修测试期望，原 terminal1 保留。随后同一已安装产品的 consumer 检查通过。后续修 cache key 文字版本为 3 后，另组装并独立安装最终 wheel，再做实际受影响回归。

## 实际检查与范围

| 证据 | 实际结果 | 不能推出的结论 |
| --- | --- | --- |
| 最终安装的 machine/unit/store 及 owner/finalize/public | 77 normal、77 `-O` 测试通过；编译绑定含 14 个预期拒绝；另有 explicit v2 正兼容普通/`-O` | 不证明设备边界、全部旧功能或完整验收 |
| 最终安装普通 runtime-K 与 GEMM | K=3/7 同 binary；State/input/tail 与数值参考通过，3 次明确请求均有 raw 和静态 counter map | 不是独立六数学矩阵，不是性能/开销认证 |
| 五个已捕获 dtype 的离线重导 | 三个新进程 public/normal/`-O`，40 个真实隔离 observer trace，原件/首次状态不改，无应用 replay | 不是跨 observer 共同时间轴或 flow |
| 实际 Trace Processor | 40 trace 的 ns、slice、raw 引用逐条对应；无 importer errors | 本轮没有实际 UI 验收；无 source/precision/async 资格 |
| 原始 byte 审计 | 1122 文件；8 次实际捕获的 1696 个端点/848 区间，847 正时长、1 个真实零值保持原样 | 审计不重新计算数学，也不证明物理时钟/完成边界 |

[audit.json](audit.json) 包含安装、实际测试、offline/TP 结果和上述端点审计。运行 [stdlib byte audit](audit_retained_bytes.py) 不 import 产品；CPU fixture 与真实数据明确区分，不能用 fixture 补设备正例。

## 阻止本阶段取得完整资格的直接证据

同一 GEMM 配置，ordinary 对象有 12 条静态 HMMA、BAR9/DEPBAR4/LDGDEPBAR10；observed 对象有 4 条 HMMA、BAR5/DEPBAR2/LDGDEPBAR6。静态计数不能单独证明动态流水被破坏或保持，当前尚无关键阶段关系保持的资格。不能把 observed 图直接称原流水。

compile-only 诊断未执行用户数学，canary 未变；实际 LLVM dump 为 46,116,710 字节。[LoopFullUnrollPass 摘要](loop-pass-summary.json) 显示 ordinary loop invalidated、observed loop 保留。它把差异定位到实际优化阶段，但没有查明具体 legality/profitability 条件。下一步应从保存的 pass 前后 IR、控制路径和依赖定位原因并修通用 compiler 路径；不按算子强制 unroll、不盲目放松边界检查，也不扩大 raw 样本量代替修复。

NV 最终边界/普通流水、真实 allocation guard 范围、precision/跨 observer epoch、动态物理复用仍待完成。GCU/Ascend 时间与机制、三后端完整 Perfetto SQL/UI、独立数学及最终指定三审阅继续按原合同执行。

## 原件与进程收尾

```text
workspace: artifacts/timeline/run-022/preflight/native-public-evidence-v1.tgz
bytes: 9198175
files: 1122
SHA256: ff1fe79dbb9bec58313a66b6106ad7a64aaac317bf5787893ede56d4539d8d63
```

包含 r021 构建与首失败、r022 两次安装、修复前后测试、真实 raw/对象、旧原件新派生、TP、最终真实回归、兼容测试及完整 LLVM dump。native so/wheel 不复制进 Git；其实际持久服务器路径与 hash 在收据中。41 个 NV 自有任务身份已核 missing/Z/不同 startticks；GCU 格式任务另见 [身份审计](gcu-owned-audit.json)。无新 browser 任务，没有终止他人任务或开展独占性能认证。
