# R093 GCU native provider — finite runtime delta review

绑定冻结 `0da41a89a21efc9912aa0c738b3b631d4f9af885`；核读时工作树干净。请求 GPT-6.1-Sol / xhigh，实际 resolved 配置未暴露，记 unknown。只读源码、Git 和既有直接收据；没有运行产品、import、测试、SDK、设备或远端命令，没有读取其它席结论。本报告是唯一写入文件。旧 image parser M1 保持 V7 已闭，没有重开数学、State、SQL 或 whole 审查。

## 结论

本 delta 的默认 compile hook、独立 analyzer 身份、immutable metadata 副本以及失败时保留输入/SDK 输出的结构已经存在。所返回结果仍是 conditional shape / relative fields；source/reader/external/busy 全部 false，没有发现这些字段被误授资格。

确认一项 minor：新 SDK child 的异常清理使用无 timeout 的 `wait()`，并在 `/proc` 登记失败时丢失 receipt 中最基本的 PID。另有三项本有限接入必须明确的验证/边界缺口：offline binary 与 producer metadata 的身份前提、10 秒预算的实际含义，以及正常安装后的新 provider/fault 路径证据。现有 73/O73 不能替代这些证据。没有提出新 ISA / CFG 证明器或设备矩阵。

## Confirmed M1 — 新 SDK child 异常清理没有有界 reap，登记失败无 PID（minor）

**位置。** `Debugger/python/flagtree_debugger/gcu_timeline.py:440–468`，特别是 454–456、460–463。

**触发。** SDK child 已启动，随后 `/proc/<pid>/stat` 读取、launch receipt 写入、20 秒 wait 超时或取消抛出异常。try 范围确实覆盖这些操作，当前 `Popen` 对象也还在，因此不是原先那种完全没有清理的路径。但是异常分支最后调用 `child.wait()`，没有 timeout；若 kill/reap 未在预期时间内完成，默认编译/offline 调用不能按已声明的有限清理预算返回。这里是代码上不存在 deadline 的事实，没有推测硬件 busy，也未实测系统处于不可回收状态。

`receipt` 在 Popen 前仅有 argv/tool/ELF SHA，PID 必须等整个 `/proc` 读取和解析成功才填入。若登记读取立即失败，所保留/返回的 decoder receipt 即使写得出来也没有 PID，无法独立识别已尝试回收的 child。

**后果。** optional native diagnostics 的失败路径可能阻塞默认调用；失败证据的 owner 身份也不完整。当前没有实际 SDK 失败收据证明此情形已经发生，故列 minor，不把它描述成设备故障。

**最少修复与验证。** Popen 后立即把 PID 记入 receipt，再读取 pgid/startticks；给直接 child 的 kill/reap 设置有限 timeout，并保留无法确认 terminal 的真实状态。使用一个实际 owned sleep child 的 `/proc`/首 receipt 故障测试及 timeout 路径，检查有限返回、returncode 和已 reap；无需设备、数学或进程组/硬件推测。原 `tests/timeline/test_native_child_registration.py` 的四个目标不包含这个新增 `_native_shape_stage`，不能继承其旧通过结果。

## 必要 verification / 边界缺口

### V1 — offline 输入对的 producer 身份没有在本入口校验

位置为 `gcu_timeline.py:501–518`。`inspect_native_execution` 检查 execution version 后做浅副本、替换 analyzer tool identity，再重新生成 location/analysis；这保证不改原 metadata，也不重放应用。不过它没有读取原 `debug_execution_native_locations` 中已保存的 fatbin / ELF SHA 去核当前 binary，就覆盖了副本中的这些字段。返回的 `producer_identity_sha256` 仅绑定旧工具身份，不绑定旧捕获的 binary 或 manifest。

因此，直接 API 传入另一份有效、具有相同 site ID 集合的 binary，加原 capture metadata，当前代码不会因旧 binary SHA 不匹配而拒绝；它会返回新 binary 的诊断并带上原 producer 身份。这是输入约束缺失的静态事实；没有执行这一混配，也不声称已有实际收据被混配。新的诊断仍带实际 binary SHA、所有 source 资格为 false，所以这不是已观察到的 whole/source 误授。

最少完成方式：若已有 producer fatbin/ELF digest，调用前比较并拒绝不匹配；对确实缺该字段的 legacy 输入，可明确标记 producer-to-image binding 未验证，或要求外层经过原件 SHA 校验。若 API 的正式合同就是“caller 已验证 capture 对”，应将这条前提及实际调用侧校验明确保留，而不能仅以 immutable 字样替代它。一个同 site-ID 的 foreign binary 负例和正确 pair 正例即可，不要求新 native 证明平台。

### V2 — 10 秒是逐点启动预算，不是整个 analysis 的硬上限

`gcu_native_analysis.py:31–39` 先执行 image binding 和 control indexing，之后才建立 deadline。60–65 行只在每个 counter point 开始时检查；`inspect_inline_reader` 和 `inspect_inline_record_fields_auto` 都在当前 Python 线程执行，没有把 deadline 传入其有限 traversal。reader 耗尽时间后，同一 end point 仍会继续启动 relative-record 分析（74–80 行）。

128 个 reader、4096 个 location、512 个 site、有限 packet/context traversal 和 256 KiB core report 的检查确实存在，不能说完全无界；但它们不能证明“整个 analysis 在 10 秒内返回”。现有 clock mock 仅模拟在 point 开始前已经超时，不覆盖 reader 调用内跨过 deadline 的情形。

最少完成方式是明确这只是 cooperative scheduling budget，并在 relative-record 开始前再检查 deadline；若确实承诺硬 10 秒，则需要在已存在的有限重循环传递同一 deadline，或使用已有有界 owned worker。无需新增一般 CFG/ISA 工程。可用 fake clock 在 reader 返回时跨过 deadline，断言后续分析不再启动且保留 unverified 原因；不需要实际等 10 秒。

### V3 — 安装及新入口/fault 测试尚未由本轮现有收据证明

实际读取 root `run-093/preflight/gcu-context-receipts-v4/runs/reader-context-v4/` 的 terminal、normal/optimized、result，以及对应 `reader-context-input-v4/run.py`：terminal 0，3.419671718 秒，73 normal / 73 optimized，warning 保留；runner 明确只执行 `test_gcu_native_values.py` 和 `test_gcu_native_image.py`。两 actual loaded ELF/native 的 byte-bound body 等于旧独立 QA，并运行新的 conditional context reader/tail，这些证据有效。它们不执行新 `test_gcu_native_analysis.py`、新 offline reinspection 测试或 `_native_shape_stage` 的 Popen/fault 生命周期。

另已读 `format-receipts-v2/runs/format-v2/` 的 terminal/result/steps 和 formatter runner：terminal 0，六个变更文件两轮 Ruff/YAPF/check-AST 通过，AST 前后相等。该格式证据覆盖新模块，但不是其行为测试。

最少补证是正常 wheel 对应冻结源码核同，运行新增 analysis/location admission 测试与 M1 的有界 CPU fault，使用旧两实际 ELF 做 installed offline 正向检查，并保留原 binary/metadata SHA 未改变、producer/analyzer 身份区分及资格 false 的结果。计划中的一次默认数学 smoke 可验证 hook 接入，不要求重跑旧数学/State/SQL/TP/UI 矩阵。上述安装证据在本次核读时尚未到，不能提前判通过。

## 已核实现边界

`tool_identity` v3 包含 analysis/control/image/values 四个分析 Python、bridge 自身及实际 `/opt/tops/llvm11/bin/llvm-objdump`，沿用已有 stat+hash 检查；prepare/cache 配置、stage 前后均检查 expected identity。ELF 是输入 bytes 的独立文件 snapshot，结束后再核文件 bytes 与工具身份。对于本轮固定工具/输入身份模型，没有发现具体新 TOCTOU 误放；没有要求防御恶意同进程代码替换或完整 SDK 动态库证明。

SDK 非零、timeout、解析/分析错误与 core report 超过 256 KiB 时返回明确 unavailable、资格 false；input ELF、stdout/stderr 和已产生 receipt 留在独立 retained 目录。输出大小检查在 SDK child 退出后进行，属于结果 admission，不应对外称为运行中磁盘硬配额。256 KiB 检查针对核心 encoded report，之后附加 decoder receipt / identity 的返回对象略大；本次不把它当作整个 retained evidence 总大小上限。

`analyze_native` 验证 schema/marker/site/phase/address/范围，拒绝重复 point；对 unsupported shape 或 reader 数/时间 budget 保留逐点 unverified。纯 image/analysis decoder 没有启动 SDK；只有新 stage 启动指定真实 objdump。context 值仅在有限 direct predecessor index 条件下推导，遇到不一致、未知定义/控制或递归链拒绝；所有高层 qualification false。没有以 conditional positive 或 DI 行号证明完整 source region、external entry、MMIO、absolute frequency 或 hardware busy。

核同产品 SHA：bridge `d9e348a5e4a4cfc653f2dcf6ecdfbca821f3a1403351ee0db56c672d46e88a68`；analysis `3e408afe54dc2c3391eb70c4dca6be1cd2fec6c19c00a4e131a806fc6cdf7dae`；values `c2f2fc374ae1f62117d044fdf1d500bb24c1c5b92cb92cfd12b195a85042fc2e`。image 仍为 V7 已闭 SHA `4459cfe8f8cca719ac09b7c9d56452188fbee5bd7e124c2e85b02905a22a2149`。

没有本次范围之外的 optional 工程要求。结论只到该 provider delta，不是 whole/source 完整交付签字。

## 4fdf634 有限源码复核追加

绑定冻结 `4fdf6344d89c746ee1c5872a3656daa1517fcb24`，核读时工作树干净。仅核原 M1 / V1 / V2 的四个变更源码/测试文件及 format-v3 直接收据，没有执行代码或重开其它门。bridge SHA `ab80a506531456e83836ef8d2a3c0b0dd1491c5b903ced870aef64e242d00395`，analysis SHA `7cd68c211cb51dff6e197bd44786801d42465e3b7e51df868de6b9f14f93adc2`，两新增/更新测试 SHA 为 `88b3df9c1f3ecaa816aebad131555cd1b95d5d3de6127ffc7253cc9f296e5f08`（location binding）与 `e7bba1cb9c073f7e240ddd995c83e28283cfbcea3a85b3ae13ecf5088367ee77`（analysis），均核同 format-v3 返回字节。

**M1 源码已修、执行验证 pending。** Popen 返回后首先保存 PID，再读取 `/proc`；异常清理的 wait 改为 `timeout=3`，超时记录 `termination_pending` 而非伪 terminal success。直接 Popen owner 仍在原 try 中。新增 registration / timeout Mock fixture 精确检查 wait 参数为 `[3]` / `[20,3]`、kill、receipt PID 和 pending 状态。它验证所调用 API/状态序列，尚不是实际进程回收的执行收据；不把 Mock 当 actual SDK 或真实 child-reap 证据。

**V2 源码边界已澄清。** relative-record 分析开始前再查同一 deadline；reader 超时后不再启动下一项，并保留逐点 unverified。结果明确 `budget_kind='cooperative_between_checks'`，不再将其描述为整个 bind/index/check 调用的硬 10 秒上限。新增 fake-clock fixture 使用 `[0,0,11]`，断言 record checker 未调用。这个修复与原报告允许的最少完成方式一致；没有要求一般 worker/ISA/CFG 改造。fixture 实际执行仍 pending。

**V1 对 immutable bytes 的原身份缺口已修；可变输入前提仍须固定。** 入口现在拒绝 bool version，提取当前 ELF/target，并在任何 analyzer 工具调用前要求原 wrapper 的 fatbin SHA、ELF SHA 和 target 全部精确一致，缺字段也拒绝。五类负例和正确 pair / 不改原 metadata 正例覆盖原混配缺口。

同一修复还有一个很小的 TOCTOU 边界：`inspect_native_execution` 没有显式限制 `binary` 为 immutable bytes，也没有在校验前快照。Python `bytearray` 当前可以通过 bundle/哈希代码，而已有 `bind_native_clock_locations` 明确接受它、到函数内部才 `bytes(binary)`。若另一线程在 offline 的身份检查之后、`tool_identity()` / binder 快照之前改写该 bytearray，A 的 wrapper 检查可以通过而 B 被分析。最小静态 reproducer 是在这次 tool-identity 调用边界注入同长度 bytearray 改写，原 wrapper 保持 A；无需 SDK 或实际并发长测。对于 immutable `bytes` 不存在这个输入修改路径。

最少补项是入口明确仅接受 `bytes`，或者先对已限额的 bytes/bytearray 作一次 immutable snapshot，后续提取、校验、分析和返回 SHA 一律使用这个 snapshot；加一项 mutable-input admission 或边界改写 fixture 即可。这是 V1 身份校验的剩余输入前提，不是新 whole/ISA 门。

**V3 继续 pending。** 已读 format-v3 terminal / result / steps：terminal 0，1.917762651 秒，两轮 Ruff/YAPF/check-AST 全过并核同上述精确源码。格式证据不能替代新增测试执行。normal-install-v1 的原 terminal returncode 1 已实际读取并保留；传输遗漏 CMake 输入的编排失败不算安装通过。v2 已启动但本次没有其正常安装、定向测试和实际 CPU reinspection 的完整终态收据，不提前 closure。

本次没有发现除上述 V1 可变输入边界外的本修复具体新问题。原资格 false、whole 范围及已闭 image parser 结论保持。待受测冻结与直接收据，只需有限补这几项 closure，不要求旧数学/State/SQL/TP/UI 重跑。

## 4fc741f 实际闭环追加：本报告有限发现均已闭

最终 runtime freeze 为 `4fc741f66144b6c2617545b8868b6ac3ae6cf0a1`。实际读取相对 4fdf634 的 source/test diff、format-v4、normal-provider-receipts-v2 中正常安装与 installed actual 的直接收据/runner；没有执行产品、测试、SDK 或设备。核读时 quickstart 与 `p01_enflame_native_locations.py` 仍是未提交 doc/test delta，runtime 文件已冻结；它们未被冒充 runtime commit 的内容。

**V1 最后输入边界已闭。** offline 入口先验证 bytes / bytearray 类型并立即取得 immutable `bytes` snapshot，之后的 bundle 提取、旧 wrapper 的 fatbin/ELF/target 核验、工具调用和返回 SHA 一律使用该 snapshot。新 mutation fixture 在 tool-identity 边界改写 caller 的 bytearray，断言 analyzer 收到原 bytes 且返回原 SHA，直接对应上一轮残留。bridge SHA `22395849f23df5b9c77616535b361906e49cea29fe5ae6a9f83d8b7691b421ef`、location-binding 测试 SHA `d88985d30e4134bdf15b441ef680ccc00b8a9ca64d69de2ddb9dd45a078ca5c8` 均核同 format-v4。原缺绑定、foreign fatbin/ELF/target 与 bool version 拒绝分支保留，原 metadata 不改。

**M1 / V2 / V3 执行闭环已到。** format-v4 terminal 0、两轮 Ruff/YAPF/check-AST/AST identity 与精确文件 SHA 已读。`runs/normal-install-v3` terminal 0，53.847693220 秒，source commit 为本 freeze；wheel SHA `79b9c3499da162264712241cca659d3f1c34c0b6ff0f34624e82bc331292dfc7`。assembler 核 131 个 component Python 文件与 wheel 相等，installer 核 502 个 installed members 与 wheel 字节相等；四个定向测试文件为 values、image、analysis、location binding，normal / `-O` 各 **106 passed**，所有 step returncode 0，优化 warning 保留。新增 child registration/timeout Mock、deadline fake-clock、身份和 mutation fixture 都属于该实际运行集合。

这些 Mock 明确验证有界 wait 参数、保 PID / `termination_pending`、拒绝伪成功的分支，不是实际 SDK 超时或 OS 无法 reap 的实测。正常 SDK child 的实际正向完成则由下一项直接收据证明。结合已核源码与有针对性的执行结果，足以关闭原 M1 与 cooperative-budget V2，不要求人为制造 SDK/硬件故障。

`runs/installed-provider-actual-v1` terminal 0，20.695610856 秒，实际使用新安装环境。runner 对两份 R069 retained capture 只读调用公开 offline inspector，检查 metadata 的规范序列化和 capture 原 bytes 前后相等。capture SHA 分别为 `ef003113276cbc65997bb5e54f12554d81c584a71204bb7ca70ee702f85b6648`、`3c7a6282434a1241a4922f4a3b090130900773270d712ebd065643bc4fd538d0`；原 producer identity `df8885…cbb` 与新 analyzer identity `caee0c…1fa0` 分别保留。两份结果的 SDK receipt 都有 pid/pgid/startticks、state terminal / returncode 0，tool SHA 为 `e37efecc349022f96c6a0fdaee12fa2019be01c8225d63999f8ea7fafce22c50`，ELF SHA 对应原 `7d56f25…` 与 `5860432…`。

installed offline 两份分别得到 25 / 38 个 counter point，conditional reader checked 8 / 18、relative fields checked 2 / 0。这里是当前按 point 计数，不能与旧 distinct end-marker 1/23 分母混用，也不表示这些点已取得 source/reader 整体资格。runner 明确检查高层 source/reader false；native analysis 的其它 false 字段由本次未变代码保留。

默认 hook 的实际 smoke 为 ordinary 两次、profile 两次；input、tail/guard、host-once 和数学均通过，两 capture 为 22 / 20 events、各两个 observer，native location points 为 48 / 62。受测 `smoke.py` 从原 input tar 取回的 SHA 为 `6b90df9198cc129829314b2730d3cf92a6c349c997481c1e79eb06b45abb307c`，与当前未提交 `tests/timeline/p01_enflame_native_locations.py` 精确一致。新断言要求 tool identity v3、正常编译的 analysis 存在且状态 finite，并拒绝 source/reader 资格提升；输出仍为 `final_machine_boundary_qualified=false`。

已实际核同 normal-provider-index-v2 中两份 terminal 与两份 result 的 SHA：安装 terminal `09793e82…dd8c`、actual terminal `7e4408c8…a8c`、安装 result `4eaaa927…8d7b`、actual result `94a60a8a…fcef`。index 保留 normal-install-v1 的原失败，未将其改成成功；新 v3 的通过承担当前安装闭环。

quickstart 新增用 `load_capture` + base64 snapshot + `inspect_native_execution` 离线使用的示例，说明原 image binding 必须存在/匹配、producer/analyzer 分离、cooperative budget 与资格不升级；与本次 API 实际行为一致。

**最终有限结论：原 M1、V1、V2 和 V3 均已关闭，本 delta 无继续必需的补项。** 这确认默认内部诊断与 immutable offline reinspection 已实际接入并完成相应验证；不把 conditional shape / relative fields 升级为完整 source/loop/reader/external/busy 资格，也不改变原 whole 剩余适用链结论。没有本次新增 whole/ISA 或旧矩阵要求。
