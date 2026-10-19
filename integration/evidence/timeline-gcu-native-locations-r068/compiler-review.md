R068 有限独立 compiler delta review

审阅快照：`4fbc8e8de8fce40748a1fbb15553f7b5016adfc1`，未合正式分支。本报告只覆盖新增 GCU clock marker / DI bridge 接入，不重开三后端全审或数学矩阵。结论：R067 单快照缺陷已修复，产品桥接、真实 SDK 验证和实际安装调用链成立；但这个快照尚未将跨文件 synthetic marker 导出到实际 ELF 行表，不能称机器码 marker 映射已经完成。

**实际阅读／未运行。** 完整读取新增 `Debugger/lib/Instrumentation/GcuDebugScopes.cpp`、对应 header/main/CMake、`Debugger/python/flagtree_debugger/gcu_timeline.py`、父仓 `flagtree-source.patch`，以及 `GcuTimeline.cpp` 的 clock、site 描述和调用区及完整 delta。读取 `Debugger/test/gcu_native_debug_scopes.py` 和未提交的 `tests/timeline/p01_enflame_native_locations.py`。核对 R068 的 native-install-v2、native-device-v1、scopes-check-v2、patch-check-v1、native-lines-v1 收据与相应安装/检查脚本；另核对安装源包及 formatted-v1 的四个关键文件。只作文本/JSON/归档/哈希读取，并查阅公开 LLVM18 DebugTranslation；未执行产品 import、编译、SDK、测试、数学、设备、SQL/UI，也未访问实验服务器。未读 peer 报告，只新增本报告。实际服务模型未暴露，未知。

**已确认的正确边界。**

- R067 M1 已关闭：CLI `main.cpp` 只读取一次文件，`addGcuNativeDebugScopes(StringRef input)` 的两个原始 parse 使用同一份输入，不再重开路径。located 与 original 都解析进 opaqueContext 后才 `setLoc`，没有把第一 context 的 Location 对象直接挂到第二 context。pass 前后及转移前后的非位置 generic IR 比较仍保留；SDK properties 从 opaque original 输出。
- `GcuTimeline.cpp:162` 仅给原有 clock/identity 调用添加位置：文件 `__flagprism_gcu_clock_v1__`，line=site id，columns 1/2 为 entry/exit timer，3/4 为对应 identity。manifest 使用相同编码。该 delta 没有改变所包围算子的操作数、数学表达式或记录 ABI，也没有新增完成 barrier。
- 父仓 patch 的 timeline 路径先正常 SDK lowering 并打印位置，再调用 bridge，然后必须经过真实 `toolkit.gcu_compiler_opt(scoped, '--mlir-print-debuginfo')` 才返回给 codegen。bridge 本身关闭 verifier 不是最终 SDK 语义验证；父仓没有把这一阶段当作可绕过的可选诊断。ordinary 路径保留原先的 scope-pass 条件。
- identity 版本升至 2；既有 pre-lookup 配置收集 `tool_identity()`，其中覆盖新 native tool、Python bridge、parent compiler 与新增两个 SDK 编译工具。helper 前后重查身份并保留输入/输出哈希和失败诊断。CMake 实际包含新增 C++ 并链接 pass 库，R067 保存副本的文件名问题没有带入产品 target。

**Confirmed major C1：跨文件 marker 只保留到 MLIR，尚未成为实际 native 行表标记。** 位置：`GcuTimeline.cpp:162–181` 只构造裸 `FileLineColLoc`；`GcuDebugScopes.cpp:33–60` 添加函数 DI scope 后直接打印/转移这些位置，没有给 synthetic file 建立局部 DI scope。触发：新增 clock/identity 的 marker 文件不同于所属函数 DISubprogram 的文件，随后经 MLIR→LLVM→SDK codegen。

实际证据：`native-lines-poll-v1.json` 对同两次已执行 capture 的实际 fatbin 校验摘要后提取 ELF。两个 readelf decodedline/rawline 命令均返回 0、stderr 空；两 ELF 的 `actual_marker_rows` 均为空，13 个 manifest site 全部缺失。此前 device 检查只要求 final LLIR 出现 marker 字符串和 `di_subprogram`，因此它能通过而未暴露最终文件标记缺失。LLVM11 objdump 另保留 debug-info warning，不能用于掩盖 readelf 的这个结果。

根因与公开翻译实现一致：裸 FileLineColLoc 生成 DILocation 时取 line/column 和既有 scope，不使用该 loc 的 filename；FusedLoc 中的 DILocalScope metadata 才替换 scope。[LLVM18 DebugTranslation.cpp:302–318](https://github.com/llvm/llvm-project/blob/release/18.x/mlir/lib/Target/LLVMIR/DebugTranslation.cpp#L302-L318)。这是 upstream 行为对根因的支持，实际失败结论来自当前 SDK 的真实 ELF 收据，不把 upstream 源码当 vendor 二进制的替代证书。

后果：当前不能按 manifest 的 synthetic file/site/phase 自动寻找实际 timer/SIPINFO PCs，因而阻止这项 native marker 映射能力闭环；不说明数学失败、raw 损坏，也不把已为 false 的机器边界资格误报成已开放。最小修正方向是在 typed bridge 中使用所属 LLVMFuncOp 的 DISubprogram，给 marker 的 DIFile 建立相应 DILexicalBlockFile/DILocalScope，并以 FusedLoc 传递，再按原 opaque 转移和 SDK 验证路径处理。该未来修复不在本次快照内。最小后续验证应复用现有案例，检查最终对象中的真实 marker file、site 和 phase/column；仅检查 LLIR 字符串或 helper CLI 成功不能关闭此项，无需新增大矩阵。

**真实收据支持的范围。**

- 安装输入源包中的 GcuDebugScopes、GcuTimeline、Python bridge、parent patch 与所读候选 SHA 一致。正常 Release recorder 重新构建了 main / GcuDebugScopes / GcuTimeline 并链接；安装脚本检查其余共享 runtime/core 源未变后复用原对象。495 个安装成员与 wheel 核对，wheel SHA `f06196ef…`，隔离 import 与 allocation-guard feature 检查通过。没有据此声称 runtime/core 被重新编译。
- 五个实际 native CLI 测试及完整保留 IR 的真实 SDK roundtrip 均通过，包含 malformed/missing input、输出 I/O 错误、重复解析和 overflow-property/marker 保留；patch 对真实 pinned parent 的 apply-check 通过。
- 已安装入口的 polynomial 与 weighted_moment 各 ordinary/profile 一次，共四次数学调用通过，input/tail/state-once 检查通过；两个 capture 完整，22/20 events、各两个展示 observer，final LLIR 确含 marker 与 DI。设备运行的测试脚本源与当前未提交测试文件 SHA 相同，测试文件没有被当作安装产品覆盖。

**Verification gaps／接入风险。**

- 前述 C1 修复前，准确表述只能是“自动 site/phase marker 在 LLVM 序列化中保留，真实 SDK 接受并可执行”。即使后续 marker 行出现，也仍需分别处理实际 reader→raw 值流、source/loop region 和 ordinary pipeline preservation；本次不关闭完整 G1 或普通流水保持缺口。
- `formatted-v1.tgz` 的 Python bridge SHA 为 `dd63f545…`，当前与安装输入包为 `47855cb0…`。差异是当前将 `/proc` ownership 与 launch receipt 写入移进 try，保证这些步骤出错也会 kill/wait；这是实际逻辑改进，不是纯格式差异。因此 v1 formatter 收据不能直接描述为当前 Python 字节的检查。当前安装/实际调用链匹配候选；这一格式收据覆盖范围问题不否定正面运行结果。后续冻结时仅补对最终相关文件的检查即可，不需重开数学矩阵。
- `backend-entry-v1.json` 指向旧安装，其 make_llir 还没有 bridge，不能用作当前接入证据；当前接入依据是新 parent patch、安装步骤以及新设备 final-IR metadata。

**Optional。** 没有需要借本次 delta 扩张的通用 ISA/IR 证明器或逐算子规则。保留原有 SDK 验证和失败停止边界，完成局部 DI scope 修复后再核对真实输出即可。

最终意见：支持单快照修复、DI-only 桥接和 SDK/安装接入这些已实际完成的有限结论；当前快照的 native synthetic-file marker 导出仍有具体功能缺陷，机器码映射及其以上资格不能放行。
