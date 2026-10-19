# R068 build/delivery limited independent review

审阅基线：`4fbc8e8de8fce40748a1fbb15553f7b5016adfc1`、`native-install-v1` 和 device 脚本 `ff2e18d2e861c0b52f69268b8527e68e4e865ffa59f5858bcd268934725d04c8`。只走查本次 GCU native-location 构建、接入、身份与交付证据；没有执行产品、测试、构建或设备操作，没有阅读其它 review。完成时工作区另出现未冻结的 `GcuDebugScopes.cpp` / native unit test 修改，本报告不覆盖这些后续字节。resolved model 未暴露，记为 unknown。

结论：现有源码和实际收据支持本次有限修复：正常构建新的 standalone recorder，复用未变的共享 runtime/core，安装匹配 wheel，并通过公开 API 在两份新数学采集中保留最终 SDK LLVM 的 clock marker/DI scope。未发现本 delta 的 confirmed blocker/major/minor。它不证明最终机器 PC 的完整 marker 映射，也不授予新的边界、clock、schedule、async 或 whole-goal 资格。

## 代码与构建链

- `Debugger/tools/gcu-timeline/CMakeLists.txt:9` 实际将 `main.cpp`、`GcuTimeline.cpp`、新 `GcuDebugScopes.cpp` 编入同一 executable，并链接 `MLIRLLVMIRTransforms`；`FLAGPRISM_PYTHON_DIR` 下的输出位置与 wheel assembler 读取的 `_bin/gcu-timeline` 一致。`main.cpp:7` 的新入口处理输入、bridge 错误和输出 I/O 错误；原 rewrite 入口仍保留。
- `Debugger/include/Debugger/Instrumentation/GcuTimeline.h:10` 的新声明与实现、调用一致。`GcuDebugScopes.cpp:33` 检查 DI pass 未改变非 location IR；随后将 location 转移到保持 vendor properties opaque 的原输入副本，检查 operation 数量/顺序和非 location IR。原始输入使用同一份 immutable bytes；这不是未经 SDK 验证的 typed reprint。
- `GcuTimeline.cpp` 为实际 timer/identity calls 添加 site/phase location，并将对应 marker 描述写入 manifest。该 delta 没有改变 raw record ABI、数学操作或依赖授权规则。
- `integration/patches/enflame/flagtree-source.patch:66` 仅在 timeline 路径启用新 bridge；`:84` 在 codegen 前用真实 SDK 再解析/验证其输出。非 timeline 分支保持旧条件。`patch-check-poll-v1.json` 的实际 `git apply --check` terminal 0，安装流程也实际应用该 patch 成功。
- `Debugger/python/flagtree_debugger/gcu_timeline.py:37` 的 identity version 2 同时绑定 packaged tool、bridge、compiler/backend 和新增 SDK opt/compile executable。`:244`、`:292` 在 bridge 前后重新检查身份；子进程有 30 秒上限及回收，保留输入/日志/收据。代码未把 identity 或 marker presence 当成机器边界资格。

共享 runtime/core 的复用有具体依据：`install_native_scopes_v1.py` 对比旧安装 source，遇到除明确 standalone recorder/其它 backend 文件之外的 native source 差异即失败；该检查先于成功安装。当前 `Debugger/lib/CMakeLists.txt` 和 `Debugger/native/CMakeLists.txt` 的共享 target source 列表也不含新 standalone 实现。本次另检查 `46c23c65..4fbc8e8` 的 Runtime、Bindings、NativeModule、Profiler/csrc 及共享 CMake 输入，未见差异。由此可支持复用这些既有对象，不能把它们称为本轮重建。

## 实际证据核对

根目录：`artifacts/timeline/run-068/preflight/`。

- `native-install-input-v1.tgz` 中本轮八项目标源码/patch 与走查时的冻结文件逐字节一致，包括两项 C++ 实现、header/main/CMake、Python bridge、native unit test 和 parent patch。归档 `run.py` 与 `install_native_scopes_v1.py` 相同，SHA `862da4a994c9c05c03a2815a7f82088cd05dfacac163f5adf066a217afb93669` 对应 terminal 收据。
- `scopes-build-poll-v1.json` 保留 whole terminal 1：正常 configure/build 两步均 0，之后 5 项测试中的 2 项因 custom-form 输入不能进入 opaque parser 而失败。没有把该初版 whole run 改写为通过。
- `scopes-check-poll-v2.json` 使用同一路径下已经构建的 binary，generic-form fixture 的 5 项检查、真实保留 LLVM 输入的 bridge、实际 `/opt/triton_gcu/bin/gcu-compiler-opt` 验证均 0，whole terminal 0。该修正 fixture 与当前 native unit test 的 Python AST 相同。此处是 fixture 修正后的检查，不能冒称初版测试成功。
- `native-install-poll-v2.json` whole terminal 0，64.664 秒。build log 明确重新编译 `main.cpp`、`GcuDebugScopes.cpp`、`GcuTimeline.cpp`，再链接到新 native staging 的 `_bin/gcu-timeline`；不是复制旧 tool 代替构建。新产物经 assembler 进入 wheel，记录 tool SHA `571606a66c7f646f951a886d819c97f4183bcae7b4604b1c009f66b9beec3218`。安装并逐字节检查 495 个成员，wheel SHA `f06196efe24825142aa1b3009d3d0498c65a631128b1f606cf7b376dcf5eebd3`；native unit、guard feature 和 isolated installed-import 均 0。
- `native-device-input-v1.tgz/run.py` 与当前 `tests/timeline/p01_enflame_native_locations.py` 完全相同，SHA `ff2e18d2e861c0b52f69268b8527e68e4e865ffa59f5858bcd268934725d04c8` 与 device terminal 一致。实际 argv 使用上述新安装的 venv。`native-device-poll-v1.json` whole terminal 0，16.941 秒：polynomial 和 weighted_moment 各 ordinary 1 + profile 1，四次数值/input/tail/state-once 检查通过；两 capture 各 13 sites、2 observers，分别 22/20 events，最终 SDK LLVM 的 marker/DI scope 检查通过。结果明确 `final_machine_boundary_qualified=false`。

## Verification gaps / 交付边界

1. **HEAD-only 交付尚缺验收脚本。** 审阅开始时 `tests/timeline/p01_enflame_native_locations.py` 是 untracked 文件，未包含在 `4fbc8e8`。设备证据确实执行了它的当前字节，因此不是运行证据缺失；但只交付该 commit 无法获得同一公开验收脚本。最小补项是把已运行的这份脚本及引用的收据纳入正式交付，无须因此重新跑数学。报告只记录状态，没有替用户 stage/commit 文件。
2. **保留 marker 不等于每个 marker 已绑定最终 PC。** 新数学测试 `:122` 检查最终 LLVM 中存在 marker 名称和 DI subprogram，`:125` 检查 manifest 的 site/line 对应；它没有逐 site 验证四个 phase marker 的最终机器位置、reader/store value flow 或 timing boundary。这是本有限验收的范围，不是已确认产品 bug。若以后声明这些机器资格，需要独立的实际 executable/DWARF/反汇编映射证据；本轮结果中的 false 必须保留。

本轮没有重新覆盖旧数学矩阵、默认选择完整性、其它 backend、SDK 异常全矩阵、离线/SQL/UI、schedule/扰动或全目标门。没有提出新的矩阵要求。仅在上述交付边界内，可以支持 R068 build/delivery delta；不能据此宣称 whole goal 完成。

## Evidence digests read locally

- `native-install-poll-v2.json`: `d4d7b81e3af7bc55734f31a81378d4a44814641a217af305e7d5c2db075e70e9`
- `scopes-build-poll-v1.json`: `04d4942bdc1f7baf4d9b08b8309367a8c3ffd2b8f56cf26e93a7baa0421fad12`
- `scopes-check-poll-v2.json`: `f44462b59e8cdbd45db07888aabb02678fd72136de725869255b394e1aff978c`
- `patch-check-poll-v1.json`: `3ba54a0fcb2d9c274b4bc650e2e89f79f76fd2d2b38efc15eb64bb243253699c`
- `native-device-poll-v1.json`: `88061ea052c2b9c09b0f3b37f09cd8c7e0247ab47e985a9c0ee96fe028a75e6b`
