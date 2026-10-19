# R070 limited independent delivery review

代码基线：`132650989f25088eaaf87c0cae1796c0b67ae20d`，相对 `7f8fdf5`；仅两个 Python 文件的 count-lifetime 修复和验收。未运行产品、测试、构建、设备、SQL/UI 或旧矩阵，未读取其它 review；只读源码及已有本地收据。resolved model 未暴露，记为 unknown。

**结论：现有证据支持本次 count-lifetime 修复，未发现该逻辑 delta 新增的 confirmed blocker/major/minor 产品 bug。正常 wheel 安装闭环在本轮已读收据中尚未完成，不能将冻结代码称为已完成安装交付。** 不授予 whole-goal、源码区域或普通 schedule 资格。

## 产品路径与修复判断

- 原错误有实际触发：`count-poll-v1.txt` 的 sparse executable `e4448ced...`，header 的 count pair 是 R12/R13。pc 1456 的 `IADD3 R13,...`、pc 1552 的 `MOV.64 R12,0x1` 是初始 batch literal assignment 前的临时寄存器用途；旧全函数 register-number inventory 会把它们误当 count 写入。pc 2064 的完整 pair assignment 已将这两次写入杀死。它们出现在本次 suite 的 `unrelated_register_writes`，没有假装这些机器指令不存在。
- `timeline_nvidia_late_addresses.py:357` 现在从实际 header store 与真实 counter-index LEA 用途建立 roots；`:426` 的 `_live_count_definitions` 对两个 word 取全部 reaching definitions，并沿 self-IADD64 递归，覆盖循环携带的旧 count。它只忽略不再流向这些实际用途的物理寄存器写入，不按 operator、source、shape、PC 白名单或 observed ticks 选路径。
- `_count_write_inventory:397` 仍拒绝 live partial/predicated 写入，要求完整 pair 的已支持零初始化、literal 初始 batch 或正 self-add。唯一零初始化、与完整 batch 数量/种类一致、LEA 两 word 和 carry/input 稳定性的既有检查仍在。不同 add input 不是可放宽的“同一 count”。
- `_check_batch_control:465` 保留 store/update 同一 single-entry straight region 的检查。对固定 zero-based 初始 batch，新检查沿真实 CFG 的所有前驱回溯，拒绝先前任一已建模 record store；因此仍拒绝重复初始 batch 或覆盖先前其它 batch。初始 literal assignment 不依赖此前已被复用的 R12/R13 值，继续要求它们始终为零会错误拒绝这个实际对象。
- append batch 仍要求 address-high 在 update 前、地址与 append 之间 count pair 不被改写；raw ordinal loader 继续校验完整 raw、source batch 顺序、首次 zero-based batch、四字段 offset 及当前 invocation/binary/raw 身份。
- 该模块经 `load_native_boundary_report` 进入 live capture 和 offline provider；依赖消费路径仍独立要求 machine/value/payload/origin/clock 等证据并校验 joined identity。新检查没有把本模块的相对地址事实提升为 absolute slot/source/time-flow 事实。`_rule_digests` 包含本文件，派生报告保留规则身份；旧 capture 不需要重新编译来使用新离线规则。

实现复用既有 `_ReachingWords`、CFG、目的寄存器解析和 `MAX_STATES` 上限，没有新增全局 register lifetime 假设或另一套无界分析。未见本修复需要修改 native producer、ABI 或默认用户参数。

## 实际验证范围

证据根：`artifacts/timeline/run-070/preflight/`。

1. `count-suite-poll-v3.json` terminal 0，2.469 秒；这是原安装上的源码 overlay CPU 检查，不是已安装新 wheel 的通过记录，更不是设备重跑。
2. 四 capture 为两个真实 executable（default/sparse），各 K3/K7；raw-bound batch rows 分别 1280/2304/1280/2304。default 的 live count writes 为 zero、literal 6、append 20/17；sparse 为 zero、literal 6、append 11/13，并正确排除上述 pc 1456/1552 的无关寄存器写入。
3. 每份 capture 有五个故障 fixture，共 20 次拒绝：live high-word overwrite、predicated live add、不同 add input、重复初始 batch、其它 batch 之后的 initial batch。前两类 body corruption 和后两类 CFG helper corruption 都是 CPU 负例，不是 20 份实际损坏的 SDK executable。新 test 没有据此声称源码区域或普通 pipeline-preservation 通过。
4. `count-suite-input-v3.json` 的 addresses/test 与冻结文件字节不同，但分别 AST 完全相同；`formatted-v1.tgz` 的两份最终文件与当前冻结字节完全相同。`format-poll-v1.json` terminal 0，yapf/ruff 通过。故原 suite 的语义可对应本次格式化后的实现，不能把格式化后的 exact bytes 冒称原 suite 实际运行字节。
5. 既有 `p01_nvidia_late_addresses.py` 另覆盖 address/carry/shift/count-update/identity 等故障；是否在新 wheel 下通过，应以安装后的实际运行收据为准，本报告不提前继承。

## 安装与交付缺口

**D1 / verification gap：冻结实现尚缺完成的 normal wheel 闭环。**

- `native-install-poll-v1.json` 是已确认失败的真实尝试：source commit `1326509`，whole terminal 1，3.320 秒；源比较和 parent 初始化后，`assemble` 返回 1。receipt 没有附 assembler 的内部 log，所以不能仅凭这个包装层 traceback 把原因归为 count 逻辑、native ABI 或某个具体 assembler bug。该失败必须保留，不能称作安装通过。
- 当前出现的 `native-install-config-v2.json` 指向后续 `a71d32fe...`，超出本次冻结产品 diff。其 input archive 中两份 count 文件与本次冻结字节一致；但已读 `native-install-poll-v2.json` 的 terminal/result 均为 null，仍无成功终态。不能用“正在安装”替代证据。
- `install_count_lifetimes_v1.py` 的方案本身符合本次 Python-only 变化：检查匹配 native source 后复用原 core/runtime/standalone tool，assembler 逐字节包装，安装后检查 wheel members/isolated import，再运行 normal/`-O` count suite 和既有地址回归。未改 native 的本 delta 无须因此要求 native rebuild。
- 最小补项是收回这次正常安装的新终态、wheel/source identity、member 字节检查、installed import、两个 count-suite 模式及既有地址回归结果；若最终包来自 `a71d32fe`，应明确其包装变动与这里的冻结 count 文件同一性。无需为此重跑数学设备、SQL/UI 或旧矩阵。后续包装源码本报告没有审查，也不默认为通过。

本轮支持的是实际寄存器复用导致的误拒绝修复，以及四份保留原件上的相对地址/raw ordinal 闭合；不是全部 NVIDIA kernel、所有稀疏形状、动态依赖、完整 source/valueflow 或整体交付门的签字。无新增 optional 审计要求。

## Local evidence digests

- `count-suite-poll-v3.json`: `fc00372ed5a8828ab309167e122860190e79678037dc6422136998338671e6be`
- `format-poll-v1.json`: `00a2d97ab4571ebd12d77cf95a49e237ce364b1af878f7064f0d23457703c601`
- `native-install-poll-v1.json`: `cf5159acb4eff7e2054cf96b41491e28829597859696adb3277c4a83901c5968`

## 有限交付追加：D1 在 baea706 上关闭

本追加保留上面的 `1326509` freeze 和当时安装缺口记录，仅审 `a71d32f` 的 assembler 路径修复并核对新的收据；不将后续 `baea706` 的其它产品修改纳入原独立代码审阅，也不依据其它 reviewer 意见授予正确性或 whole-goal 资格。以下是 D1 的当前状态，上文 pending 是已保留的历史状态。

- **Assembler 小 delta 未见新增问题。** `a71d32f` 在 `assemble_automatic_wheel.py` 将 `egg.egg_base` 改为 `os.path.relpath(egg_dir, args.flagtree)`，其余变化是说明注释。参数已 resolve，且 `main:40` 已 `os.chdir(args.flagtree)`，因此 egg-info 使用的相对路径仍指向同一个已创建、隔离的 output/egg 目录；没有迁移输出到任意工作目录、改变 native build 或放宽字节校验。`native-install-input-v3.tgz` 中实际 assembler 字节与所审版本相同。
- `packaging-failures-v1-v2.json` 补齐了原失败原因：v1 的 `build_py.analyze_manifest/assert_relative` 明确拒绝 absolute `.../wheel/egg/flagtree.egg-info/PKG-INFO`，与上述修复对应；v2 已到 install，但当时 runner 使用的 pip 不认识 `--python`。两次失败均保留，不改写为成功，也不再把未知包装层错误归到 count 逻辑。
- `native-install-poll-v3-final.json`：source `baea70620f8561369cc440fefba48f7938cbc25a`，whole terminal 0，78.703 秒。assemble、venv、seed-pip、install、disassembler、isolated import、normal/optimized count regressions、既有地址回归和 installed-public-reexport 均 0。639 个 installed members 校验通过；wheel SHA `eb6452e55bf6d6f851cdc778bd8e853377bcad41e97da1d939520efddc6a0613`。仍明确复用未变 core/recorder，没有冒称 native 重建。归档 runner 与保存脚本、terminal 的 script SHA 对应。
- `native-regressions-v3.json`：normal 和 `-O` 各四份实际 capture 通过，各拒绝 21 个故障 fixture；额外记录的 reset fixture 是后续产品变化的运行收据，不等于本追加重新审阅了那项实现。既有 native address 回归拒绝 33 个负例，113 个原文件保持不变，application_replayed=false。
- installed public CLI 对原 sparse bundle 的自有 copy、指定一个 invocation 执行重导；runner 清空 `CUDA_VISIBLE_DEVICES`。结果为 8 counter exports、2 observed-dependency exports，dependency_reason=null，application_replayed=false。不是设备重放，也不据此声称全 sparse/default 分母升级。
- `new-dependencies-sql-result-v1.json` terminal 0，2.419 秒；runner 检查原 pinned dependency verifier SHA 为 `0d72cf3a882ea4b9d3bd1fe6c7172066fa486f708db8d2787ae47aef15147e03`。两个新 trace SHA 分别为 `2df4f2bc4696bbf3956cf958532afbce29c84f4d3ea923185327e1b51f1afbc2`、`288b4d4f74dc1f36d1840606612385daea837cb2226c7567720a971b0be1292f`；各有 180 nodes / 404 flows，actual raw/tick/ns 与 protobuf 检查通过，各保留 263 行 importer stats，无非零 error/data_loss，importer_errors=[]。这是这两份新依赖导出的实际 SQL 收据，不代替其它 trace 或全目标验证。

因此，原 **D1 安装 verification gap 在上述后续交付版本和有限收据范围内已关闭**。原 `1326509` 代码审阅的范围、后续未复核产品修改的边界，以及 source/schedule/whole-goal 非签字状态保持明确。

追加收据 SHA：

- `native-install-poll-v3-final.json`: `6b540e657b99894d98ac9636ee23b271ca223e5735514265b25df0a0a1a11e1e`
- `native-regressions-v3.json`: `ebf8d753aa7d11d6819f64876e700adf423d41d271005d8c0294b2e5a61db6c1`
- `new-dependencies-sql-result-v1.json`: `bf8b93df16ee098c6a42413511efb897cdfb7e90bcdc30167d8c00c70a40502a`
- `packaging-failures-v1-v2.json`: `77fcd9576de0b89f634dbf88e9635f7f77bb0603c140a24d1d99b0281ed08282`
