# R069 limited independent delivery review

基线：candidate `68faaaf953ff13fd3ef64e7a0351390e8c61a476`，相对 `9232936`。审阅开始、完成前 candidate 均 clean。仅审本次 GCU final-ELF DWARF 位置服务、正常 compiler hook、packaging 和交付证据；没有运行产品、测试、构建或设备操作，没有阅读其它 review。resolved model 未暴露，记为 unknown。

**结论：支持该有限 delivery delta。未发现本次新增的 confirmed blocker/major/minor 产品问题。** 正常构建、匹配安装、自动保留实际 executable 的 DWARF rows 有对应收据；缺失 phase 仍显式保留，没有升级 source/valueflow/busy 权限。下述两个 verification gaps 不等于产品已确认故障，也不构成 whole-goal 签字。

## 代码和正常用户路径

- `Debugger/tools/gcu-timeline/CMakeLists.txt:9` 将新 `GcuNativeLocations.cpp` 纳入包内同一 executable，链接 `LLVMDebugInfoDWARF`、`LLVMObject`；`main.cpp:7` 的 `--native-locations` 分支使用同一输入/输出错误处理。`Debugger/native/CMakeLists.txt:142` 的 enflame native 构建仍会接入这个 target，输出路径与 wheel assembler 的 `_bin/gcu-timeline` 读取路径一致。
- `integration/patches/enflame/flagtree-source.patch:95` 在正常 `make_fatbin` 取得实际 bytes 后、返回编译产物前调用绑定；只在 `debug_execution_version == 1` 时执行。不是只存在于测试脚本里的事后检查；ordinary path 不需要此阶段，测试也覆盖了 ordinary bypass。
- `gcu_timeline.py:310` 检查 bundle 数量、header/target 长度、payload 范围和相互重叠，要求唯一非空的真实 GCU300 target。`:355` 把所选 ELF 交给包内 native 工具；`:399` 同时保留 fatbin/ELF SHA、target、report、缺失 phase 列表和 output SHA。新增元数据没有改变 raw ABI 或 decoder。
- `_native_file_stage` 保留 immutable input、日志及进程收据，检查前后 tool identity，30 秒超时回收子进程，限制输入/输出大小。现有 compiler identity 包含 bridge 和 native executable 的内容 SHA，故没有依赖手工 bump version 才使新 tool 生效的旧缓存问题。
- `GcuNativeLocations.cpp:78` 只收集 synthetic marker 文件的合法 site/column rows，保留 section/index/offset；拒绝无法唯一对应 executable section 的 row，检查 extent overflow，并有 row/point 限额。未知 line/column 被计数，不伪造 endpoint。输出语义明确是 `compiler_debug_location_rows`，source、reader valueflow、hardware busy 均 false。
- `gcu_timeline.py:359` 检查 schema、语义、三项 false 权限；每个 point 的 site、column、phase 要与当前 manifest 一致。`:392` 保留不完整 phase，而不是把 `compiler_locations_mapped` 当作每个 site 四 phase 齐全。新字段没有被 canonical/Perfetto 消费链用作时间或依赖授权条件。

实现沿用 LLVM 的 Object/DWARF parser，没有新增 vendor disassembler 文本匹配或要求普通用户手工运行 readelf；有限 bundle wire format 和 marker/phase 映射有独立故障 fixture。当前未见为本 delta 引入新的安装步骤或公开 API 参数。

## 实际构建、安装及采集证据

证据根：`artifacts/timeline/run-069/preflight/`。

1. `native-install-input-v1.tgz` 中 12 项相关源码/patch/assembler 与 frozen candidate 逐字节一致；安装 runner 也与 `install_native_locations_v1.py` 一致，SHA 与实际 terminal receipt 对上。不是拿原型 source 的成功结果代替当前安装。
2. `native-map-build-poll-v1.json` terminal 0，13.937 秒；正常 configure/build、native scope test、真实保留 LLVM 的 bridge 与 SDK 验证均 0。`native-map-check-poll-v1.json` terminal 0，实际运行 5 项 DWARF CLI fixture，并读取两份保留 GCU ELF；分别得到 48/62 rows，13 个 site，未知 line rows 为 10/25。其 CPU retained-object 检查明确没有执行设备，也没有升级 source boundary。
3. `native-install-poll-v1.json` terminal 0，65.763 秒。日志实际编译 main、GcuDebugScopes、**GcuNativeLocations**、GcuTimeline 四个对象并链接新 staging tool；两个 native test 文件各 5 项通过，共 10 项 CLI checks。正常 assembler、495 个 installed wheel members 的字节检查、guard feature 和 isolated import 均成功。15 项 binding pytest normal/`-O` 各通过；`-O` 的 pytest warning 原样保留，不把 mock binding tests 叫作 SDK 或设备证据。
4. 新 wheel SHA：`471e8a96679f41bc6e90206c3cda468dfcb908faee23c0a7f7b38b8349fa1d13`。安装 runner 在成功路径中检查共享 native sources 没有超出明确 standalone/其它 backend 差异后复用旧 runtime/core；当前 diff 本身也只改变 standalone 工具和 Python/parent hook，没有重建 core 的需求或相反声明。
5. `native-device-input-v1.tgz/run.py` 与当前公开验收脚本完全相同，SHA `ab9441068b40661a977f64bc34b7606cc5f21ebd68b9040b8dad8c4427b4aaf0` 与 terminal receipt 一致；实际 argv 使用上述新安装 venv。`native-device-poll-v1.json` terminal 0，17.094 秒。两份数学各 ordinary 1 + profile 1，通过数值、input、输出 tail 和 state-once 检查；两 capture 为 13 sites/2 observers、22/20 events，实际自动保留 48/62 points，且 final fatbin SHA 与 retained executable snapshot 一致。结果仍明确 `final_machine_boundary_qualified=false`。
6. `patch-check-poll-v1.json` 的实际 apply check 为 0；安装路径也实际将完整 patch 应用到明确 parent baseline，成功走过新 `make_fatbin` hook。

## 必须保留的限制与 verification gaps

**缺失 phase 是实际存在的限制，不能用 rows 数量冲掉。** `missing-native-phases-v1.json`：第一 capture 的 site 2/3/7 缺 columns 2/4，第二的 site 2/3 缺 columns 2/4；其中 site 3、第一份的 site 7 有实际 canonical events。`shared-end-blocks-v1.txt` 显示 LLVM 中互斥 incoming paths 汇入一个 timer/identity end block，可以解释独立 debug location 只剩一份。该证据不直接建立缺失 site 到最终共享 PC 的 valueflow/alias 证明。代码继续保留 missing 列表是正确的；不能宣称所有实际 interval 的两个 native endpoints 均已独立绑定。

**G1：最终 device 脚本的完整格式检查收据差两行。** `formatted-v1.tgz` 与当前 `tests/timeline/p01_enflame_native_locations.py:188` 的差异仅为随后加入 `native_location_points`、`native_missing_phase_sites` 两个摘要字段；因此 AST 也不相同，不能说最终该文件的 exact bytes 已全部由这份 format receipt 覆盖。实际 device run 确实用了当前字节，数学/绑定断言没有因此失去运行证据。最小补项：仅对最终该文件补格式检查，保留差异/收据；不要求重跑设备或新矩阵。这是证据覆盖的小缺项，未据此确认产品功能故障。

**G2：新 capture 尚无新的 TP 导入/SQL 收据。** 本轮没有把旧 1740 retained trace 的成功移植成两份新采集的成功。旧 SQL/UI 证据可支持未改变的既有展示实现，但不能充当新 bytes 的 importer stats、track/event/flow 语义证据。若交付范围以后声称这两份新 trace 的 SQL 接受，应补它们自身的有限输入 SHA/结果/完整 stats；无需因此重采旧矩阵或重复导入完全相同的旧 bytes。该缺项不否定本次 native-location build/metadata delivery。

未重审旧矩阵、全部默认选择、跨 backend、源码区域/valueflow、动态依赖、clock 精度、busy/完成时间、schedule/扰动或 whole goal。无新增 confirmed issue，也没有把 partial marker coverage 或旧展示证据当成全目标通过。

## Local evidence digests

- `native-map-build-poll-v1.json`: `1a690000fb08c96e486364b76b5216dc956732cfc40d3f6ed73f1aed43b4ae42`
- `native-map-check-poll-v1.json`: `4bfbf76e4b4ea1acb2d088bea4b3c89a5072fb1edcd91d40c83c7a2d9bf140de`
- `native-install-poll-v1.json`: `c133e8ecacdf6cac72f7b5b0bc6633d9d4597793fac4a5cd2c8de7e88c3fab91`
- `native-device-poll-v1.json`: `283640a154f5eb62335680f79c795d390f537e3cb7e785998fb12da2320cf921`
- `format-poll-v1.json`: `4b889afa841203afa08ad3a4fbcd967f1a826338cd9161acaf33a3bf9cabbc15`
- `patch-check-poll-v1.json`: `126c53a5e4827a2feaa451f8934fffbe7b8a9beaa205473ab3e2b04ead03239f`
- `missing-native-phases-v1.json`: `bc65d652c82dd6aa62e2d8db966a0e8ee1195dfb2e30cc5bd7b0b4b4d190139a`
- `shared-end-blocks-v1.txt`: `59a5134f0b00b62f72b38dc48697dd3531a8b98ec49db73b6dfc961060d3a099`
