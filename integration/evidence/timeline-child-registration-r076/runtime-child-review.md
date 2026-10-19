# R076 owned-child M1 有限复核

请求配置沿用 GPT-6.1-Sol / xhigh；resolved serving model/effort 未暴露，unknown。只复核 R075 M1 的4个调用点及12个 CPU fixture，不读取其它席报告，不重开整体审查，不运行产品/test/SDK/设备；仅本地 Git、文本和 stdlib 的 JSON/tar/SHA/AST 读取。本报告之外不改文件。

实际读取时 candidate 已 clean，HEAD 为 `61cb831290860655edf2f64eb8c3b395a4c1fc0a`；相对 `1dd2baafd0458a33141702c2c332495be733f66c` 恰为4个产品 Python 文件及 `tests/timeline/test_native_child_registration.py`。本报告绑定此提交，不再按“未提交修改”描述。

当前结论（含下附正常安装 closure）：**M1 的4处修复已由源码、原失败复现及三后端正常安装上的 CPU fault/真实工具 smoke 闭合；未发现本 delta 新的 confirmed bug。** 不授 whole-goal、P03、ordinary pipeline 或精确 E01 资格。下文初审时的 source-loaded 证据保留，安装终态见末节。

## 4处清理路径

| 位置（相对 candidate） | 核对结果 |
| --- | --- |
| `Debugger/python/flagtree_debugger/gcu_timeline.py:174`，`rewrite_execution_ir` | `/proc` 读取、owner 字段更新、首 `launch.json` 写入均已进入 wait 的同一个 try。失败后直接检查当前 Popen，必要时 kill，`wait(timeout=10)` 后才写 terminal/re-raise；不再有原登记 I/O 绕开清理的窗口。 |
| `Debugger/python/flagtree_debugger/gcu_clock.py:93`，`identity_library` | `/proc`/初始收据和 `communicate(timeout=20)` 同 try；异常时直接 kill 未退出的 child，并 `communicate(timeout=10)` 回收和关闭 PIPE。SDK helper 输出仅在成功后继续检查/发布，失败不误发缓存完成收据。 |
| `Profiler/python/flagtree_profiler/timeline_ascend_machine.py:320`，`_run` | receipt 先为 starting，登记 I/O 移入 try；外层 finally 仍用 `_stop_worker` 处理可识别后代，内层 finally 无论其返回/抛错都检查直接 Popen、必要时 kill、`wait(timeout=10)`。持续 `/proc` 不可读不再绕开直接 child 回收。 |
| `Profiler/python/flagtree_profiler/timeline_nvidia_late_compile.py:134`，`LateLLVMTransform.__call__` | 原登记 try 保留；`_stop_worker` 被嵌套 try/finally 包围，直接 child kill/有界 wait 不依赖其 `/proc` 枚举成功，也不依赖其正常返回。原异常在成功清理后继续 raise，编译 metadata 仍只在原验证成功路径发布。 |

直接 Popen child 尚未被 reap 时 PID 不会被系统复用；这些 fallback 不扩大到无法核身份的任意 PID/进程组。未发现引入设备同步、application replay、raw/ABI、clock/dependency authority 或预算语义变化。这里的有界等待不承诺强制终止不可中断的内核/SDK 状态；超时异常也不等于已完成回收。

## 12个 fixture 与直接收据

已实际读取整个 `tests/timeline/test_native_child_registration.py`、`artifacts/timeline/run-076/preflight/child-poll-v2.json` 及 `child-input-v2.json` 中实际执行的 runner/source。12例为4个调用点 × 一次 `/proc` 失败、持续该 PID `/proc` 失败、首次 receipt 写入失败。

- Popen 被替为真实自有 Python sleep child；假的 SDK 文件/identity 只满足前置检查，不执行 SDK 或产品 native 工具。
- fault 只在 child 已创建后触发；NV compile 的首次 pre-Popen receipt 不会错误吃掉注入。`first_receipt` 只匹配实际 launch/commands/compile receipt。
- `/proc` 注入限该 PID；persistent 变体会继续影响 `_stop_worker`，确实覆盖原 NV fallback 缺口。
- fixture 在其自己的最终兜底清理之前检查原 OSError、耗时 <10秒、恰1个 child、`returncode` 非空及 `waitpid` 得到 ChildProcessError。故不能靠测试 finally 先清掉泄漏再误判通过。GCU clock 另核 stdout/stderr PIPE 已关闭。

runner 先用原 installed 模块跑 baseline，再显式 source-load 4个修复模块、执行同一 fixture。收据 terminal0，原 baseline **10 fail / 2 pass**，修复 **12 pass / 0.86s**；`source_loaded=true`、`normal_install=false`、`device_executed=false` 均明确。原10失败的分布与代码一致：3个原 try 外窗口各3失败，NV 只在 persistent `/proc` 失败，另2例本来就通过。没有把 CPU sleep child 当设备正例。

执行 runner SHA `16674c07b26d5215957a3962a27b825ee02b739f5096414512299a30a6725a3e` 与收据一致。本席用 stdlib AST 比较实际 child-input 的4产品+测试与当前提交，5份均相同；再读 `format-receipts-v1.tgz` 的嵌套 formatted archive，5份格式化结果与当前提交逐字节相同。格式收据实际 yapf/terminal 均0。这里只解析源码 AST，不 import/执行源码。

## 初审时尚需的最少检查（现已完成，见下）

初审时正常安装准备中，尚无成功终态。当时所需是：完成既定正常 wheel 安装，核实际4个 installed 模块/成员字节对应本提交，从安装包执行这组 CPU fixture（不再 source-load），正常/-O复用同组12例。未改 native，无需为本项重新 C++/SDK 构建、设备数学、TP/UI 或独立矩阵。

本次无新增 confirmed blocker/major/minor；没有额外 optional 资格门。原整体结论继续未完成，其剩余 P03、ordinary 关键依赖和精确 E01 收据不因本次 child 修复而关闭。

## 正常安装证据 closure

仅追加读取 `artifacts/timeline/run-076/preflight/receipt-audit-v1.json` 与三份完整 receipt archive；没有运行任何测试、产品或设备。本席独立计算三 archive SHA，均与 audit 相同，并读各自原 terminal、安装 result/steps、normal/-O日志、positive-smoke result 和所附5份 tested-source，后者分别与61cb831候选逐字节相同。

| 后端 | 实际正常安装与 CPU fault | 真实工具正向 smoke |
| --- | --- | --- |
| NVIDIA | source61cb831，641 wheel members；安装 terminal0，normal12pass、-O12pass，所有安装 steps0 | 原实际 ordinary LLVM 经当前 installed native transform，43sites，terminal0；记录输入/tool/output SHA，无 device/application replay。 |
| Enflame | source61cb831，497 wheel members；resume terminal0，normal12pass、-O12pass，resume steps0 | 原实际 execution MLIR rewrite13sites；真实 SDK opt 构建 SIPINFO identity bitcode1512B，terminal0；无 device/application replay。 |
| Ascend | source61cb831，439 wheel members；安装 terminal0，normal12pass、-O12pass，所有安装 steps0 | 原实际 retained ELF 经 installed `_run` 调用 llvm-dwarfdump，command及外层terminal0，输入/tool/output SHA保留；无 device/application replay。 |

GCU 首次安装的 `seed-pip` 实际报 `No module named ensurepip`，原 `native-install-v1/terminal.json` 仍为1，未洗成成功。resume 使用系统 pip `--python` 为已经创建的新 venv 安装**同一份** wheel（SHA `f64dbad3618b5c4e6af6a312ffac21905c2c7bb42f187fec91a767526eae95c7`），随后 installed import/成员核同及两种模式的12fixture通过；这足以关闭安装缺口，不需要再编译或重做设备数学。原 warning 与失败日志仍保留。fixture 的10秒要求是每例清理耗时，不是整个12例pytest总耗时。

核对的 archive（相对工作区根）：

- `artifacts/timeline/run-076/preflight/nvidia-receipts-v1.tgz`：227个regular files，SHA `c2db180a08d7d0f01d94f0bf4186bf89f6310cb195543f25514ac437399b4b79`。
- `artifacts/timeline/run-076/preflight/enflame-receipts-v1.tgz`：164个regular files，SHA `34201a0c080fc5463d397fdf49d29ec3973a7842d4b61a13e045a3ac4d4b9c69`。
- `artifacts/timeline/run-076/preflight/ascend-receipts-v1.tgz`：150个regular files，SHA `f58a2f1cd0d47d7abb047f1af02a186e0298af9044e5b7a21177d108a0a27ea7`。

**只关闭 R075 M1 owned-child 四处调用点。** 三份正常安装后的正向工具调用也避免只凭 monkeypatch fault 测试判断正常路径。未改变源边界、时钟、异步/ordinary流水或whole-goal资格；原整体缺口保持。
