# C1：Ascend census v3 有限 affected 代码复核

日期：2026-10-16。席位：原 `/root/final_sol61_c1_compiler`。原额外 C1 的模型/思考深度配置来源仍为 root 保存的工具请求记录；本报告不根据自述认定实际模型版本。原 `C1-report.md` 和 `C1-delta-1638a89.md` 保留原版本及原范围。

## 版本与结论

本次用 `git show` / `git diff` 精确读取以下提交，未将活动工作树的未提交内容作为审查对象。开始时 `FlagPrism-ascend-census-visibility` HEAD 为 `fbca3cce79cdde0bd53195736123d7667c302d61` 且有继续开发中的改动，因此没有直接读取其产品文件来代替冻结提交。

- native/编译器 v3：**`bd61acdadc8b9582f243ca1ee5dc1869ed73e4ad`**。
- 历史 transport loss reader：`1f8c6e01b979dd8c6fde2daf9affa28b2f372757`。
- report coverage：`58fca857e73313be92b0c867a35600d16dca1259`。
- offline 已解码事件撤回 exactness/格式：**`e6644ff23d65ad3d6b76944678ba771847bd4aec`**。
- 最终文档冻结：**`2bc91bf36dceeb39a279c3aed4eea22fb34c6d7a`**；相对前一项仅改 `Profiler/docs/automatic.md`。
- 未变的历史 closure 基点：`1638a899d80c2ff134efbdb703aa695dbb39c39d`。root 给出的当前 canonical/runtime 标签不等同于本次 v3 设备安装通过证明。

**在本次实际阅读的 v3 变更范围内，未确认新的 compiler/runtime blocker 或 major。** 发现一项 quickstart minor，在 `bd61acd` / `58fca85` 中存在，已于 `2bc91bf` 源码关闭（下节）。新 v3 的真实重建、wheel/venv、安装终态和保留旧 v2 磁盘 cache 的功能升级验证收据 **尚未收到，验证仍 pending**。本报告的源码闭环结论不能代替这些动态证据。

只读代码/Git 与已存公开 tar/JSON/raw/LLVM；仅写本报告。未运行测试、产品 decoder、编译、安装、设备任务；未修改产品、论文或 Study；未读 peer 报告、私有资格数学源码/IR。

## 已确认问题及处置

**C1-v3-M1，minor，源码已关闭。** 在 exact `58fca85` 的 `Profiler/docs/automatic.md:130`–133，普通默认参数段仍给出 physical v2 的 `32 + P*3*S*8` 公式且只提 v1 兼容。用户据此理解当前自动模式会得到错误的 header/stride/cell-budget 规则，并遗漏旧 v2 的 unknown-loss 限定。

本席在审查中报告给 root，随后实读 exact `2bc91bf` 差异：该段改为 v3 的 64-byte zero header、`P*3*alignUp(8*S,64)`、完整 bytes/8 的 cell budget，并明确 v1/v2 原布局可读但 count inexact、transport loss unknown、零值不能证明未执行；链接 `source_site_census.md` 对应实际存在的公共文档。与本次代码和 protocol 文档一致，本项可关闭，无需因这项文档修正另跑设备。原 `1638a89` 的 C1-M1 历史关闭结论不被改写。

## 编译、实际坐标与物理 ABI

实际读取 `bd61acd` 的 19 文件变更清单及其中所有受影响的产品/compiler/build-document hunks；没有运行或读取变更测试来替代代码证明。继续阅读相关完整函数/上下文：

- `Debugger/lib/Instrumentation/AscendProgramAnchor.cpp:65`–153 与 `Debugger/python/CompilerBindings.cpp:87`–105：选择仍要求真实 public entry 中唯一实际 op ID；新 source marker、native capability、ABI/layout metadata 均显式为 3。marker 仍携带选定 source ID、column、S 和六个实际 i64 program/grid SSA operands，位于该 operation 前。用户 kernel 不需要写 marker/hidden ABI。
- `integration/patches/ascend/flagtree-source-census-v2.patch:434` 附近：既有 AutoBlockify source-anchor transport 分支新增接受 `source_census_site.v3:`，仍检查 sideeffect、六 operands 和 constraints，再进入既有 scalar blockify rewrite。历史 patch 文件名保留不等于其内容仅支持 v2。FLIR 的实际 program-role 创建桥没有改变。
- `Profiler/llvm/AscendLateObserver.cpp:168`、206、352–415、455–549：mode/marker 版本匹配，column/S 验证，六 i64 操作数和 def-use dominance 检查保留；线性 program 仍由每个 marker 自己的 `x + grid_x*(y+grid_y*z)` 计算，没有切换到物理 BLOCK.IDX。AIC bank 0、AIV 实际 SUBBLOCKID+1 的 actor expression 未改变。
- `Profiler/llvm/AscendSourceCensus.h:14`–53：新 v3 选择 header64 和 `strideColumns=alignUp(S,8)`；地址为 `64 + ((program*3+actor)*alignUp(S,8)+column)*8`，两个 volatile u32 字仍为 saturating count/flags。不是用 sampler、减少 sites 或展示裁剪来掩盖写入丢失。

`Debugger/python/flagtree_debugger/compiler.py:270` 起的自动选择和 typed ABI 绑定保持原机制，仅升级 native capability/layout/version guard。`ascend_compiler.prepare` 要求 metadata 的 version、actual frontend S/ABI 对应，明确传 `source_census_v3` 和 S 给 late plugin；混装 v2 frontend/new Python 会被 capability guard 拒绝，marker/mode 不一致也会被 late pass 拒绝。

定向查看本次产品 diff 中的名称、shape、site、hash、pointer 条件；没有引入公开 probe 的算子名/shape/hash/site 白名单、具体 sidecar pointer literal 或逐算子文本替换。新增条件是版本、物理布局、容量、编译器 marker 或真实身份关联。此结论限于 affected 变更，未重新研究无关 compiler 特性。

## selected-site、actor bank 与 native 分配

读取 `Bindings.cpp:574`–642、759–766，`TransferEngine.cpp:1101`–1182，`BufferLayout.cpp`，以及 `ascend_census.py` 的 plan/transport/descriptor/actor views。

Python、native admission、LLVM writer 与 manifest 对 v3 使用同一公式：`A=alignUp(8*S,64)`、`bytes=64+P*3*A`、`reserved_cell_count=bytes/8`。native 先验证实际 grid、`records_per_instance=3*S`、ABI/version/S 和 byte/cell/index 上限，再把通用 runtime 的 32-byte prefix 抵扣为 `recordCapacity=totalCells-4`；因此通用分配 `32+8*recordCapacity` 恰为 v3 bytes。以配对证据的 P=2/S=8 为例，bytes448、预算 cells56、native capacity52，公式一致。S 不是 8 的倍数时，bank padding 也进入两预算；不是只计算有效列。

runtime 对 v3 device base 额外检查 64-byte 对齐，在实际 stream 清零整 allocation；不合成 legacy ring header。reader 保留 v1/v2 各自原 header/stride，不按 v3 重解旧 bytes；v3 校验 header、未分配 actor/site 及 bank 尾部 padding 均为零。

`compiler_actor_views` 将 layout/header/actor stride/program stride/version 与 manifest 比对，再按 actual source ID/column/S 绑定真实 emitted markers。actor 分组仍允许稀疏列；缺 emitted column 保留为 padding，不能凭零值合成“该 site 未执行”。原 actor/source/ABI 限定没有因物理对齐被放宽。

## cache 升级及构建集成

实读 `ascend_compiler.cache_key:410`–458、Profiler component callback、parent patch 中的 driver-key callback 与 `NPUOptions.hash`、原 effective AutoBlockify normalization；读取 source recipe 的 source snapshot、patch digest/拒绝错误 resume、core/observer 构建、wheel/install/hash 检查及 assembly 的 source/stage/ZIP 比对段，和相关 native/plugin CMake 输入。

正常新进程使用新安装且复用旧磁盘 cache 时，静态链为：`NPUOptions.hash → _flagprism.compiler_driver_cache_key → 注册的 profiler callback → plugin bytes 与 capture_sources digest`。v3 改了实际 plugin C++，也改了被 key 摘要覆盖的 `ascend_compiler.py` / `ascend_census.py`；故不依赖 triton 版本字符串、清空 cache 或换 prefix 才产生新 disk key。前端 capability 和 marker-version 检查提供混装时的 fail-closed 边界。未把进程内热替换安装解释为受支持的原子升级。

当前 parent patch 仍由公开 recipe 固定 pin 后实际 apply，改变 patch bytes 不能静默 resume 旧 workdir。`AscendProgramAnchor.cpp`/`CompilerBindings.cpp` 属实际 libtriton compiler target，`Bindings.cpp`/TransferEngine 属 runtime target，observer C++ 由独立 LLVM15 module 构建，header 随其编译依赖进入。assembly 复制的是供应的 matching outputs，并校验 Python/native/parent source 与 archive；它自身不声称重新构建 native。

**尚缺实际 closure：** root 已计划以原公开 probe 源路径不变、旧 v2 default cache 不清的方式运行新 installed 默认 v3。应保留 old/new 安装来源、旧 cache 路径、实际 imported native/plugin/frontend capability、原 source digest、effective AutoBlockify option、new compile/layout/marker3 和 bundle/raw 身份。收到实际收据前，本席仅认定“源码具备失效机制”，不写“旧 cache 升级已实测通过”；也未收到三后端本轮 native/wheel/venv 完成终态。

## 历史 visibility hazard 的 reader/report 处理

实读 `1f8c6e0`、`58fca85` 及最新 `e6644ff` 的产品差异。低层 `CensusReader` 从实际 retained layout/actor binding 识别旧 Ascend v1/v2，将 `exact=false`、`unknown_loss=true`，零 count 的 execution status 为 unknown，保留原 count/flags/raw；`decode_shared_census` 的 summary/loss 同步。

`e6644ff` 还覆盖已含 decoded events 的旧 bundle：`fine_grained.normalize` 先 deepcopy，根据 capture/runtime/physical plan 或 compiler actor binding 降级历史 counter exactness，并给派生 capture loss/summary 加 hazard。不是只依靠重新调用低层 decoder。`require_automatic_records` 检查 row/capture 的 unknown loss 并使自动 coverage incomplete，给出重采 v3 的具体指引。原始旧证据不被改写。v3 的 `not_flagged` 仅说明不带该历史格式 hazard，不是对任意 backend 失效原因的全面证明。

## 公开配对证据的独立离线核对

读取 `run-011/ascend-census-visibility/root-sidecar-paired-audit.json` 作为索引，并直接读取 `sidecar-evidence.tgz` 的实际 JSON/raw、原始与 adapted LLVM、诊断源与 plugin bytes。本席使用 Python 标准库独立重算，没有运行产品 decoder：

- archive SHA256：`5023347851ea809430c2050722b3d3590b9cb047bd72477f598c2e272da58329`。
- 同一个 capture 的 compact bytes416，SHA `d7fb7bfc053143bfb8fb7708d7e6d482ffe6b830c47af083dc56479b570d822a`；48 个位置中 **20 个 (0,0)**，其余 (1,1)。
- 独立 aligned sidecar bytes448，SHA `1ba1cc3216586771e6e3b8388aa2bac4e03e59c7665cdb0f2808c172051f5201`；header64 全零，P=2/三 actor/S=8 的 **48 个 cell 全为 (1,1)**，实际 device pointer mod64=0。
- source SHA `c75e4766fc61e86e250093a6db30a28b5fc431e337bedd5790a941e03db7abf2`、plugin SHA `730eaabf0325704d5d40beb45cc22c8af0a54e83f7da63f25b592c3e7991f531` 与配对 JSON/实际 bytes 一致。enclosing compile ID 为 `6f9202c5-babd-41c9-9df4-9849a9895e4d`；retained final binary digest 与 binary 记录一致。
- AIC/AIV 两个 adapted LLVM 的独立文件与 bundle 内文本逐字节一致，其 original/adapted 摘要一致；各有八个真实 v2 marker、32 条 volatile u32 stores，包含原 compact pointer 和独立 aligned sidecar pointer 的两套实际写入。

这证明该公开诊断 capture 中确实出现了 compact 写入丢失及 aligned 保留差异；**它仍是附加 sidecar logger 的诊断，不是最终 v3 installed capture**，也不是原资格 state 断言失败的原因证明、无重放证明或性能实验。最终 v3 使用 hidden pointer 而非诊断 hardcoded sidecar pointer；尚待 installed 功能收据核实完整生产链。

## 仍保留的限制

原 Ascend eligible state 断言失败继续未解释。后续相同 binary 的 profile/ordinary 未复现不关闭原失败，本次 transport 写入丢失机制也不自动解释该 state 失败。旧 v1/v2 “无 saturation 即 exact”的结论必须按新 hazard 限定；本报告不认定原或本轮三后端资格全部通过。

未复核 peer、未扩展到其他新 compiler feature、未重审原不变链路；未验证任意 LLVM/SDK scheduler、完整设备缓存一致性或全部热升级组合。源码审查已有限完成；实际新 native/install、旧 cache 升级和默认 v3 capture 是等待 root 后续收据的验证项，收到后只需相应 receipt delta。

## 追加：最终 ec75 安装、真实 v3 capture 与旧 cache 升级收据

这是上述 pending 之后收到证据的有限 receipt delta，保留前文当时的 pending 状态，不重写时间顺序。最终 Git 为 **`ec75a9f0592c76f22d64eff443034ab89442b477`**；实际硬件 source 为 e664，native/parent patch 输入仍为 **`bd61acdadc8b9582f243ca1ee5dc1869ed73e4ad`**。本次没有进一步 compiler 源码研究、没有执行测试/设备/安装，没有读 peer 或私有资格材料。

### 三后端编译与最终安装：本席相关 pending 已关闭

读取 `run-013/ascend-v3-build/final-ec75a9f/{REPORT.md,summary.json,*-package-evidence.tgz}`，以及摘要指向的三份原 e664 package evidence 的 `native-result.json` / `native-commands.json`。每个原 archive 摘要与引用一致，原 native-result/native-commands 的实际 bytes 摘要与最终 bridge 一致。原命令记录实际 compile/link 均 exit0：Ascend 包括 AutoBlockify、CompilerBindings、AscendProgramAnchor、Bindings、TransferEngine、Decoder、late observer 及 core/tool/runtime/plugin relink；NV/GCU 有其对应 component TU/core/runtime compile/link。原 receipt 明确 `full_core_rebuilt=false`、保留未变对象复用，不能称重新构建全部 compiler/依赖。

本席对最终三个 archive 的 evidence index 逐成员重算长度/SHA（Asc34 / NV33 / GCU33 个）；每后端 68 个 component Python 摘要与精确 ec75 Git blob/package index 一致；每后端 **281 个 native/CMake/parent-patch source** 对精确 bd61 与 ec75 Git bytes 重新比较一致。三组 native package index 与 e664→ec75 wheel bridge 和 package-file index 逐项相符（Asc107 / NV216 / GCU63），无 mismatch。读取实际 audit script，确认其断言逐文件比较 source→stage→ZIP→installed bytes、隔离 import prefix 和 native capability3，未只验证自报版本。未下载或逐字节打开远端整份大 wheel，本席独立核对的是留存索引、执行检查及其相互连接。

最终 wheel/clean-venv 的 assemble/create/install/audit 命令及 controller 均 exit0。实际 installed CPU 日志为 Asc320 passed+3 skipped、NV314 passed+3 skipped、GCU314 passed+3 skipped；这些是保留的服务器结果，本席未本机重跑。import 路径均在各自 `venv-ec75a9f` 中；audit 明确 capability3，Ascend CPU 执行前后 NPU 未初始化。最终 wheel SHA：Asc `821b929b9582080b2f2a6996be25ccd7c41a6443dfcd9da39129e10a554d7206`；NV `48fd503f5d78dbd83ce8e1b43a8e26e18e172ffde87c1f9282c1217a9cc3c0bf`；GCU `2dad4c6937a6120de3011d0e249398ad6bbca359bfe3b8ac1d004b58b8f9885b`。最终刷新复用已实编 native，不宣称这次又执行 C++ 构建。

### 两个公开 installed v3 capture：编译/source/bytes 关联已核对

直接读取 `run-011/ascend-census-visibility/v3-installed-hardware-evidence.tgz`（本席重算 SHA **`14614442b75b2aa8518708e494e80bf2808c5edd779f85e0c0e765414276a948`**），以及补充的实际 generated bytes `public-retained-generated-index.tgz`（SHA **`ca7dde2675eb5e6af00498c184eb32e829b64a21c1cc09c1a2ae521778a9a451`**）。补充包中 13 份唯一 retained bytes 的长度/SHA 均重算匹配。对两 capture 的 binaries/launches/source snapshot/ABI/census/raw/original+adapted LLVM/最终 npubin 进行有界独立交叉核对，没有调用产品 decoder。

- **mixed**：实际 source 路径 `/tmp/chijin-census-visibility/probe.py`，完整文件 SHA `5ccb2d818774fd490aa0e971782491ca65c7fc54aa2453744afbbf63efd00ac3` 与归档 source 和捕获快照一致。新 binary ID `abd3b2fa68e7657ffbb19f5a7d9cd4319d628492b75eeca830533e21a6dd33f4` 与唯一 launch 一致；实际 npubin SHA **`a0114342b638ac4d2b58cff28bf169f86943a48616994aabbc5a0f5ff3dfbf76`** 与保留 bytes/binary record 一致。ABI3/S8/hidden argument5/header64/actor stride64/program stride192；P2 raw448 bytes SHA `1ba1cc3216586771e6e3b8388aa2bac4e03e59c7665cdb0f2808c172051f5201`。全部48个物理 count/flags cells 直接读为 **(1,1)**，header 零；每条对外 count 与 raw offset 的 u32 一致。
- **vector loop**：source 路径 `/tmp/chijin-census-visibility/vector_loop_probe.py`，完整 source SHA `b1f088ee067e95c2f967f4100e6130060f616c533a1f86a96f5365ec8cb2b809` 与归档和快照一致；binary ID `f0b0da7d3bbae21e3c71f0023784440b6bc96e0a19540f7bfb125e057f4628c8` 与唯一 launch 一致。ABI3/S8/hidden argument3；P4 raw832 bytes SHA `3e77ce79a131511cb76823fb0027ffe26f131b287f0af9a3ffda05b20e2ae00d`。直接读取96个物理 cells：24个(1,1)、**8个(4,1)**、64个(0,0)；这8个 count4 对应四个 source programs 中实际 AIV slot1 的两个循环 selected sites。报告 count 与 raw 一致，未把保留 actor bank 的零 cell 合成一次执行。

两份 capture 的 plugin SHA 均为 **`164769a1a5fd2666190ee93b24ed421a572e5cb2c0f5396db39cd9bb3593c496`**，与最终 ec75 native/package index 及原实际 observer link 输出相同。mixed 保留独立 AIV/AIC 两 module，vector-loop 为实际 AIV module；各自原始 LLVM 中八个 **v3** marker 的 ID/column/S 与 source plan 对应，adapted LLVM 各有16条 volatile count/flags store，检查的 marker 前确有这些写入；原始 input、canonical/adapted 摘要以及 supplementary actual bytes 均匹配，未把 manifest 自报作为唯一证明。两次 `selection_status` 为 complete；保留结果分别记录1024个 state 元素全1及数学检查成功。这是公开工程功能检查，不能用 state1 或数学通过替代 trace bytes 核查，也不证明原资格 state 失败原因或任意无重放。

实际 e664→ec75 Git 文件差异仅为三个 reader/derived-view Python、quickstart 和一项测试，281个 native/parent-patch 输入一致。因此本次硬件 writer/marker/compiler 证据可以与最终 ec75 native 字节桥接；没有宣称 ec75 原封不动又跑过这两次设备任务，也不把 reader 后续修改当成重新执行数学。

### 保留旧 default cache 的升级：本席 pending 已关闭

hardware 包的 before receipt 指明 `TRITON_CACHE_DIR` 未另设，旧默认目录为 `/root/.triton/cache/AI7KWUNLMI76GCANA5IAAXBZEVPD23OMUPTKIVRQ53555VEQ4N6Q`；旧 binary ID `023eab51ab623fe3080d0750005c39255e3d6dcca3e6a45630eefbded490e37d`。旧 metadata 的实际 ABI/layout 为2，effective AutoBlockify=false，source IR 保留同一 `/tmp/chijin-census-visibility/probe.py` 位置；before full-source SHA 与本次实际新 capture/probe bytes 相同。after receipt 给出新默认目录 `/root/.triton/cache/VPJ3F6TI45SX765RT5NH3HGUGGOWFBESW5POZKBQKM7CDJW5GP2A`，对应上述新 binary/npubin/ABI3，而非继续取旧 v2 metadata。

最初 after receipt 只给 `old_cache_unchanged=true`，本席明确指出无法独立重算8文件。root 随后仅只读获取这8个已知旧 cache 文件及 fresh after index，归档为 **`root-after-cache-evidence.tgz`**，本席重算 SHA **`3286a7b55a52098f705e5c154cd3d7de1a32ff0732ca6b7035183781ef2dd410`**。逐项读取实际 `.source/.ttir/.ttadapter/.mlirbc/.bcmlir/.npubin/.json/__grp__.json` bytes 后，8个 SHA **全部与 before 列表一致**；旧 npubin SHA 仍为 `544134d9a8d83e9edd9b9ae3319c5942851ae56d0b2a58afda00c8b0db9220b7`。fresh after 的观测时点为 `1792152311.095209`，在两次 v3 设备功能检查之后；不是声称这些 after bytes 在当时已留存。至此证据支持“原公开 source/path、旧 default cache 保留时，新安装生成并实际运行新 key/ABI3”的有限升级检查通过，不只是在新空 prefix/cache 上成功。

**追加结论：** 本席此前等待的 affected compiler/native 构建、最终三后端安装字节桥，以及两次公开 v3 writer/source/cache 升级功能证据已足以关闭相应 pending，未确认新具体问题。关闭仅限这些工程证据；独立完整数学/特性矩阵当时仍在准备，未经过本席本次复核，不得称本轮全部资格验收通过。原 Ascend scalar/state 失败历史仍未解释；这里没有性能或 GPU 开销结论。
