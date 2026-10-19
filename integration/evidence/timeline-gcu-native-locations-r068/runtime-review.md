# R068 independent limited runtime delta review

审阅对象：`4fbc8e8de8fce40748a1fbb15553f7b5016adfc1`；新增设备脚本 `tests/timeline/p01_enflame_native_locations.py` 的 SHA256 为 `ff2e18d2e861c0b52f69268b8527e68e4e865ffa59f5858bcd268934725d04c8`，与实际 device controller 记录的脚本一致。审阅中出现的未冻结 `GcuDebugScopes.cpp`、`gcu_native_debug_scopes.py` 后续修改不在此结论内。未读取其它 reviewer 意见，未运行产品、checker、测试、编译或 SDK，未访问设备/服务器；仅写本报告。

**结论：本 delta 未发现 confirmed blocker、major 或 minor。** 可以按“自动保留 SDK LLVM 序列化中的 native clock marker/DI scopes，并重新经过 SDK 验证”的有限范围交付。现有实际收据不能授予 final machine boundary、实际 inline reader→raw 绑定或 ordinary pipeline 保持资格，也未见本 delta 向产品消费者授予这些权限。

## 代码核对

- `Debugger/python/flagtree_debugger/gcu_timeline.py:37` 的 identity 升为 v2，并增加实际默认安装位置的 `gcu-compiler-opt`、`gcu-compiler-compile` 哈希；原有 native recorder、Python bridge、backend compiler/driver、libtriton、SDK clock library 等绑定仍保留。`Debugger/python/flagtree_debugger/compiler.py:60` 将 identity 放入冻结 instrumentation config；prepare 比较冻结值，launch collector 亦重新比较。它能使本次工具/bridge/backend patch 变化产生新的 timeline cache 身份，而不靠 marker 字符串冒充旧缓存的新编译。
- `gcu_timeline.py:236` 接受内存中的 SDK IR 字符串，写入独立临时目录；输入有 16 MiB 上限。native helper 的 stdout/stderr、launch、terminal 和 input/output 留在该目录。`/proc` owner 读取和 launch receipt 写入位于 `try` 内；异常/超时先 kill 并 wait 此无子进程 helper，再抛出。非零退出、超预算、输入字节改变或工具身份改变均拒绝返回有效结果。marker metadata 只在这些检查通过且 output 读回后设置。未发现新增 owner 丢失或悄悄退回无验证输出的路径。
- `Debugger/tools/gcu-timeline/main.cpp:7` 的新模式先读入并完成转换，成功后才打开 output；缺失/解析失败不会先产生新 output。写出后显式 close，并用 `has_error()` 报告晚期写失败。`GcuDebugScopes.cpp:21` 对同一输入缓冲做两次 parse，不重新打开输入路径；DI pass 前后比较无 location 的 IR，再将 locations 转移到保留 vendor opaque properties 的原始 parse，并检查操作数量/顺序及非 location IR 不变。公共 LLVM parser/verifier 不能代替 SDK 验证，代码也明确保留这一边界。
- `integration/patches/enflame/flagtree-source.patch:66`、`:76` 的 hook 仅在 `debug_execution_version == 1` 的 timeline 路径启用。顺序为 SDK lowering → native DI bridge → 实际 `toolkit.gcu_compiler_opt(scoped, '--mlir-print-debuginfo')` → 保存该返回值的 SHA → 返回给后续 codegen。没有 SDK 拒绝后继续用 `scoped` 的 fallback。SDK 验证的输入仍保留在 bridge output；SDK wrapper 的失败通过异常返回编译调用方。
- `Profiler/python/flagtree_profiler/timeline_enflame.py:245` 从同一次 launch 的 compiled kernel 取得 binary 与 `kernel.asm`，并核对 kernel hash，snapshot 包含最终 `llir` 等字符串 artifact。新 metadata 因而随原有 per-launch snapshot 留存，不需要导出阶段重新读取 live 编译临时路径。
- `Debugger/lib/Instrumentation/GcuTimeline.cpp:162` 仅为现有 timer/identity calls 增加 synthetic FileLineColLoc，并向 site descriptor 增加 marker 对照。返回值、raw record ABI、发布/容量、46 位声明、clock unit/epoch、依赖匹配规则均未在此 delta 改动。搜索新字段的消费者未见它们单独开启 clock/source/dependency 权限；marker 是后续机器码核对的线索。

## 已有证据的实际范围

实际打开了 root `artifacts/timeline/run-068/preflight/` 下三份指定 poll JSON，并读了对应 install/device/scopes-check 输入脚本。install 归档中的 bridge、DI 源和 patch SHA 与本次冻结源一致。

- **构建、安装与 CPU 检查：** `native-install-poll-v2.json` controller terminal/0，明确重建 standalone recorder，复用经源文件比较的未变 core/runtime，生成并逐成员核对安装后的 495 成员 wheel，再执行 matching import。wheel SHA `f06196efe24825142aa1b3009d3d0498c65a631128b1f606cf7b376dcf5eebd3`。其“pending_device”是该安装步骤当时的状态，设备结论另取下面的独立 receipt。
- **真实 C++ helper 的 CPU 测试：** `Debugger/test/gcu_native_debug_scopes.py` 五项检查通过，覆盖 marker 与 SDK overflow 编码保留、重复 parse、畸形输入、缺失输入、output 打开失败。它们不调用设备 kernel，也不是最终 ISA 证明。
- **保留 IR 的实际 SDK 验证：** `scopes-check-poll-v2.json` terminal/0；native unit、原 R061 `input.llir` 的 DI bridge、真实 `gcu-compiler-opt` roundtrip 三步各 0；SDK stderr 为空。`actual_native_mapping_qualified` 明确 false。这是 retained IR 验证，没有数学重跑。
- **新实际数学与公开 API：** `native-device-poll-v1.json` terminal/0；脚本先完成 polynomial/weighted_moment 的 ordinary 两次，再以新输入完成 profile 两次；检查 CPU reference、输入不变、输出 tail 和每 program 一次的 state 副作用。两 capture 各 13 sites、2 observers，分别 22/20 events，canonical complete，并检查至少一个实际正区间。snapshot 中出现 synthetic clock marker 与 DI subprogram，工具 identity 为 v2。此处的 `guards` 指应用输出 tail；不把它单独提升为新的 profiler allocation-guard 故障资格。

## Verification gaps（与 confirmed defects 分开）

1. **最终机器码与 ordinary pipeline 仍开放。** 位置：设备脚本 `:120`–`:137`。当前只确认保存的 LLIR 包含 marker/DI、manifest marker line 与 site ID 一致；没有逐 site/column 对照最终 executable line table、实际 reader 指令和 raw record。脚本及 receipt 的 `final_machine_boundary_qualified=False` 正确。最小后续验证是对这两份已保留 executable 做独立的逐 marker 机器码核对；无需为此再重放数学。ordinary/profile 数学相同也不能替代 ordinary pipeline/调度保持证据。
2. **Python bridge 故障生命周期主要由静态检查支持。** 位置：`gcu_timeline.py:260`–`:301`。上述五项 native 测试和成功集成没有专门注入 owner receipt 写失败、helper timeout、身份变化或 SDK 拒绝。未据此确认代码缺陷，也不要求扩大设备矩阵。若要单独声称这些故障分支已实测，最小补项是 CPU fixture 注入这些失败，检查 child 被 reap、输入/诊断保留、没有有效编译结果且未进入 codegen。

## Optional

设备脚本可在保留件离线核对中补 `sha256(compiled_snapshot.compiler_artifacts.llir) == debug_execution_native_ir_sha256`，并检查每个 site 四个 marker column，而非只检查字符串存在。当前数据路径和有限结论不以此建议为 blocker。

## 已读与未读

已完整读所要求的 Python bridge、make_llir patch、新 native main、native unit、设备脚本；另读 `GcuDebugScopes.cpp`、recorder delta/header/CMake、冻结 config 与 collector snapshot 的有关路径、三份指定 receipt 及对应输入脚本。为理解 SDK wrapper 的异常返回，额外只读本地已有 FlagTree toolkit/compiler 源；该旧本地副本不作为当前安装身份凭据，安装身份依据本次实际 receipt/归档核对。

未读其它 review 报告；未审正在修改的下一版 C++/unit；未重审全部三后端/runtime；未自行取得或检查本轮最终 ELF/行号表，也未重跑旧 qualification 矩阵。本报告不能用于关闭这些未读范围。
