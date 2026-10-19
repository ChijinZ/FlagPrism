R068 C1 词法 scope 修复的有限追加审阅

快照：`b4c5f81a6b77f866837e011f93ee054d8c0a0b0c`。本报告保持原 `compiler-review.md` 的 4fbc 快照结论不变，仅评估新增 DILexicalBlockFile/FusedLoc 和已有 CPU native 导出证据。

结论：未确认本次代码 delta 有新的 blocker/major/minor；修复直接针对原 C1 的跨文件 scope 缺失。代码路线及该保留输入上的 CPU marker 文件导出已获支持，但原 C1 的“修复版实际安装、加载并 capture”闭环仍不能据此关闭。

**实际阅读／未运行。** 完整读取当前 `GcuDebugScopes.cpp` 和 native unit，比较 4fbc→b4c 的相关改动；读取 `compile_lexical_locations_v4.py`、lexical-compile-v4 和 scopes-build-v3 收据，核对原 capture 输入 SHA、row 统计及构建输入归档。未读其他 reviewer 报告；未运行产品、SDK、编译、测试、数学或设备，也未连接服务器。只新增本追加报告。实际服务模型未暴露，未知。

**代码判断。** `GcuDebugScopes.cpp:43–64` 只选择 synthetic 文件的裸 FileLineColLoc，取得最近的 LLVMFuncOp 及其 DISubprogram，为该 marker 创建 DIFile 与 DILexicalBlockFile，再把原 line/column 包装为带 DILocalScope metadata 的 FusedLoc。scope 的归属来自函数，文件来自 marker；不是把其他函数或第一个全局 subprogram 硬接到所有 marker。缺少函数或 subprogram 时明确报错，而非静默给出成功。这个构造符合此前核对的 [LLVM18 DebugTranslation 的 FusedLoc scope 规则](https://github.com/llvm/llvm-project/blob/release/18.x/mlir/lib/Target/LLVMIR/DebugTranslation.cpp#L302-L318)。

新增内容只修改 location；非位置 IR 比较位于这段处理之后，单快照解析和 opaque-context 转移保持不变，未见重写数学操作、SDK properties 或记录 ABI 的行为。已有 FusedLoc 不被此段重复包裹，重复解析的 native unit 仍在；新增断言要求词法文件 scope 确实被序列化。该选择器不是覆盖任意嵌套 location 的通用承诺，本次也不授予这种资格。

**CPU 证据判断。** scopes-build-v3 的正常 Release 构建、五个 native unit 和 SDK roundtrip 均返回 0。lexical-compile-v4 使用前一真实 polynomial capture 的保留 final LLIR，输入 SHA `6837d496…` 与原 device 收据一致；新 tool SHA 为 `baa5de69…`。bridge→真实 SDK 验证→正常 SDK codegen→readelf 均返回 0，没有应用或模型重放。

新诊断 ELF 为 `b7402d92…`。报告中共 58 个解析出的 synthetic 文件行表 row：48 个 line>0 row，覆盖 site 1–13；另 10 个 line0 row 不构成 site0。`marker_line_count=81` 统计的是含 marker 名字的文本行（含标题），不能当作 81 个指令或 reader。这些实际数据支持“原先不出现的 synthetic 文件现在能进入该 CPU 输出的 native 行表”。它们不证明 58 个独立 timer，也不证明每个 site/phase/identity 的唯一 PC、reader→raw 源绑定或动态执行次数。

**源身份与剩余范围。** 构建归档中的 C++ SHA 为 `fad8b3c1…`，冻结候选为 `fcc41827…`；实际 diff 仅有两处表达式的换行/空白，没有 token/逻辑变化。native unit 源 SHA `696af921…` 与归档一致，lexical runner SHA 与 terminal 一致。因此可以支持这份代码路线的 CPU 结果，但不将它写成“冻结候选 C++ 字节已由该旧构建原样编译”。修复版 wheel 安装及新 ELF 实际加载 capture 尚未由本次材料验证，后续正常安装链应绑定最终源/工具字节。

此诊断 ELF 没有真机执行，也不是原已加载 ELF；`original_capture_native_mapping_qualified=false` 保留正确。原 4fbc 失败证据继续保留，不能用 CPU 重编副本升级原 capture。完整 C1 闭环、G1/source-loop region、raw 值流和 ordinary pipeline preservation 仍分别开放；无需因此引入新矩阵或通用 DWARF/ISA 证明器。

**后续实际安装／capture 补充：原 C1 的 synthetic 文件缺失已修复。** 本段更新上文在仅有 CPU 材料时尚未关闭的安装/加载部分；原 4fbc 报告和失败证据不变。实际读取 `native-install-v2-poll-v2.json`、`native-device-v2-poll-v1.json`、`native-lines-v2-poll-v1.json`、`actual-column-program-v1.json` 及其读取命令记录，并核对安装输入包；未运行测试或任何 SDK/设备命令。

安装 v2 的来源为冻结 b4c，正常重新构建了三个 recorder C++ 输入，495 个成员与 wheel 核对并隔离安装/import 通过，wheel SHA `25055965…`。包中 GcuDebugScopes C++ SHA `fcc41827…` 和 Python bridge SHA `07d6b927…` 均与冻结候选一致，因此前段提到的 CPU 旧构建与格式化候选的字节覆盖缺口，在这条新正常安装链上已补齐。原共享 core/runtime 仍按已有输入检查复用，未声称重新构建。

同两算子的实际安装入口 ordinary2/profile2 数学、input/tail/state-once 检查通过，capture 的 22/20 events 与两个展示 observer 保持完整。新的实际 binary IDs 为 `142ac782…`、`cdf9ca6e…`；native-lines-v2 从这两个 capture 的 executable snapshot 校验 fatbin 摘要后提取 ELF，得到 `6b69d4a8…`、`a0c0ffc0…`，不是前述 CPU 诊断 ELF `b7402d92…`。

两个实际 ELF 的 readelf decodedline/rawline 都返回 0、stderr 空，synthetic 文件下的非零行分别为 48/62 rows，均覆盖 manifest site 1–13，missing 集为空。10/25 个 line0 row 被单独列入 compiler-unknown 行，不作为 site0。LLVM11 objdump 的 debug-info warning 仍保留，不将它写成无告警。

实际 capture0 的 raw line-program 摘录还显示 file entry2 为 `__flagprism_gcu_clock_v1__`：site10 的 column1 位于 0x3d00，column3 位于 0x3d90，column2 位于 0x3e70，column4 位于 0x3ee0，与约定的 entry timer / entry identity / exit timer / exit identity 编码一致。该摘录的记录读取路径是 native-lines-v2/output/0/line-program.stdout。这补充了一个真实已加载对象中的 phase/identity column 保留示例；行表关联不等于这些地址已经逐一解码为唯一 timer/SIPINFO getter。

据此，原 C1 的准确触发与后果——“synthetic 文件没有进入实际加载对象的行表，所有 manifest sites 因此缺失”——已由修复版 source→正常工具/wheel→实际 capture→原 snapshot 行表的有限链闭合。本轮未确认新的具体缺陷。这个关闭仅针对文件/站点标记缺失；不扩展为全 site/phase 唯一 PC、all-path/source-loop region、reader→raw 值流或 ordinary pipeline preservation 资格。产品的 `final_machine_boundary_qualified=false` 仍应保留，完整 G1 不随此项关闭。
