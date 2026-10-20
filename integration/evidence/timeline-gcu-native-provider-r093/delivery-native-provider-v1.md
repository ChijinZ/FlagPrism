# R093 GCU native provider 接线有限 delivery 审阅

冻结对象：`0da41a89a21efc9912aa0c738b3b631d4f9af885`，本席Git核HEAD/clean。请求沿用独立R3 GPT‑6.1‑Sol / xhigh；实际resolved model/effort unknown。仅读源码、Git与文本；未运行产品/import/测试/SDK、未连接远端、未读peer新报告。范围仅本轮默认native diagnostics、保存binary的重新检查及其测试/打包；不重审whole、State、SQL或BK64。

**结论：没有发现本轮误授时间/source/loop资格；新接线的主体设计可行。确认一项新增minor故障路径问题，以及正常交付尚待实际收据的verification gap。** 不能把源码检查记成normal wheel/install、真实旧capture重检或默认两数学smoke已过；本轮也未完成通用source/loop规则。

## Confirmed minor M1：新decoder超时清理重新出现无界reap

**位置/触发。** `Debugger/python/flagtree_debugger/gcu_timeline.py:446–465` 的 `_native_shape_stage` 在启动owned `llvm-objdump`后用 `child.wait(timeout=20)`。登记/proc/launch收据异常或这个wait超时进入 `except BaseException`，kill之后调用 **`child.wait()`而无timeout**。

**证据/后果。** 这是源码上明确的无界清理路径；本席没有运行或声称观察到实际SDK挂死。如果kill后的reap无法及时完成，默认编译与保存binary重检均会在声称有界的decoder阶段继续等待，无法按同一函数的fallback返回unavailable；外层controller是否最终杀死父进程不能代替该库调用的有界清理。该问题不证明正常SDK路径有错误，也不授假终态。

**最小修复/验证。** 仅把新stage的kill/reap设为有界，沿用既有owned-child明确时间上限/不能确认终态时如实报告的做法，不把timeout写成已退出。补这一个调用点的登记失败和decoder等待超时受控fixture，核owned child确实reaped或清楚保留未终态、无无限wait、正常路径仍返回诊断。无需设备故障/新数学矩阵。当前location测试mock整个shape stage，因此没有覆盖这条清理路径。

Confirmed blocker/major：本范围无新增。M1为故障恢复minor，不是normal编译已被实证阻断。

## 实际接线与身份判断

* **默认入口。** 既有Enflame source patch在取得真实fatbin后调用 `bind_native_clock_locations`；`:350–425` 仍先从唯一GCU300 image取actual ELF，以packaged native tool重建clock location rows、核site/phase/manifest。新增 `_native_shape_stage`随后对该ELF调用实际SDK decoder，再交给共同 `gcu_native_analysis.analyze_native`。不同shape的有限不支持留unavailable/per-point原因；不是把它们改成source或loop通过。
* **保存binary重检。** `inspect_native_execution:501–518` 复制传入metadata的顶层字典，保留旧producer identity，替换副本中的当前tool identity，然后走同一 `bind_native_clock_locations` / analyzer。当前代码新增字段均为顶层替换，未改原metadata中的嵌套manifest或producer identity。返回fatbin SHA、旧producer identity内容SHA、实际locations、当前analysis。旧cached analysis/status没有被当作重检结果读取。
* **身份分工。** `tool_identity:38–68` version3纳入analysis/control/image/values四模块与actual llvm-objdump，新增诊断实现或decoder改变会使默认缓存身份失效；`prepare_ttir`仍在冻结选项后复核identity。重检的 `analyzer_identity_sha256`绑定当前完整身份，与返回的旧producer hash分开。当前做法保守地让纯analyzer变化也影响新编译缓存，未发现由此静默复用旧诊断的错误；不要求此轮再重构成另一个缓存框架。
* **ELF及site连接。** `gcu_native_analysis.py:14–54` 核schema严格int、bounded site表/唯一id、phase/column、16-byte marker与actual kernel extent；`bind_instructions`独立核实际ELF与disassembly字节/descriptor/symbol范围。默认和重检路径的location report均来自当前native tool读取同一ELF，不从cached sidecar取。报告保ELF/disassembly SHA与kernel symbol。未将一般调用者传入的诊断字典当成已签source proof。
* **不冒资格。** reader entry context、自动tail选择仅给conditional/relative事实。顶层source_region、reader_valueflow、external_entries、hardware_busy仍全false；未知control数、point原因与预算耗尽显式存在。`gcu_native_values`的新参数是可选kwargs，旧不传control的reader/tail接口仍可用。没有看到新字段被公共clock/dependency exporter用于提升资格。

这里的保存binary重检会调用**当前SDK objdump及packaged native工具**，属于无应用重放的CPU inspection；不能把它描述为SDK不可用时仍能运行的纯离线重导。现有公开 `timeline_reexport` / `timeline_enflame_offline.reexport_views`未新增该SDK调用，其原有无设备/无SDK重导合同未改变。两条inspection入口共用analyzer，不等于公共重导会自动重新解析native。

## 打包和测试的已覆盖/未覆盖范围

本席核 `gcu_native_image.py` 与对应test确实Git tracked，不是只存在于工作目录的遗漏文件。Enflame正常wheel assembler会递归打包两component的所有Python模块并核wheel member字节，新analysis及其image/control/values依赖在该规则内。此轮为Python改动，未发现要求重build未变C++的理由；actual wheel包含/正常import仍须由待完成收据确认。

| 测试源码 | 已表达的有效检查 | 当前限制 |
|---|---|---|
| `test_gcu_native_analysis.py` | synthetic ELF/native字节绑定；schema bool、foreign site、错phase/bool address、重复point、wrong bytes拒绝；deadline耗尽可见；资格false | 首正例的reader本来unverified，不能证明真实SDK形态得到有用reader/tail结果；真实旧capture重检可补这项，不必再造新设备数学 |
| `test_gcu_native_location_binding.py` | fatbin唯一image/extent；错误native report拒绝；missing phases保留；ordinary不启动检查；metadata不改、重检使用当前identity | missing-phases test mock了shape stage；重检test mock了整个binding。没有覆盖decoder child生命周期、SDK失败→unavailable及真实两层串联 |
| `test_gcu_native_values.py`新增 | hoisted地址跨join/loop、checked entry constants、自动tail；错offset/不一致def/load clobber/unknowncontrol/loop-carried/samepacket拒绝；reader roots不能被entry constants替换 | 是有限算法fixture，不等于正常packaged provider已在实际ELF上执行，也不授source/loop规则 |

新生产代码的拒绝使用显式条件/ValueError，不依赖assert；pytest测试里的assert由pytest处理。未执行normal或-O，不能把源码有测试记作测试通过。

## Necessary verification gap G1：当前冻结正常交付收据待完成

Root已说明尚在准备；本席不把它误记成产品缺陷或永久阻碍。按本新增路径最少需要：

1. 正常wheel/install/import收据，核新四模块、packaged native/SDK身份及当前source；未变native明确复用即可。
2. 正常installed版本对已有真实capture的actual binary重检，保原capture/metadata hash不变、旧producer与当前analyzer身份分别可查；实际支持形态至少得到非空reader/relative-tail结果，其余点保明确unknown。若测试已有cached诊断，核该诊断不能替代新计算。不重放应用。
3. 已计划的默认两数学smoke，确认普通compile callback自动附加diagnostics、正常math/raw采集仍通；不把diagnostics false说成source/loop完成。无需扩大独立矩阵、TP/UI或性能认证。
4. M1修复后，仅补该child调用点的受控故障与受影响normal/-O回归；不重开旧四处child、State或其它后端。

Optional：无新增实现要求。若最终文档称“离线”，应沿上述inspection与public reexport各自真实依赖说明，不能声称两者访问能力相同。

本报告只确认接线/身份/打包规则与测试范围，保留M1和G1；不以其通过替代原自动source/loop能力或whole-goal签字。

## 追加：4fdf634 源码修复有限复核

本次只核冻结 `4fdf6344d89c746ee1c5872a3656daa1517fcb24` 相对首审的四个文件，不把读取时工作目录已前进的 `4fc741f66144b6c2617545b8868b6ac3ae6cf0a1` 混入本结论。未执行测试、产品或远端命令。

**M1 的源码缺陷已修复；正常 installed 验证仍待补。** `_native_shape_stage:451–472` 在读取 `/proc` 前先保留PID，异常后kill与 `wait(timeout=3)` 有界，不能确认退出时收据明确为 `termination_pending` 并保留PID，不伪造terminal成功。新增registration/timeout fixtures直接进入此stage，检查wait分别为 `[3]` / `[20,3]`、kill调用、unavailable及落盘PID/state。它们使用Mock child，证明预期调用合同，不能声称实际SDK进程已完成回收。原M1描述作为首审历史保留；本次没有发现该修复引入新的具体缺陷。

`inspect_native_execution:511–525` 现在要求严格整数版本1，并在调用当前工具前核保存locations中的fatbin SHA、ELF SHA和target与实际输入一致；缺字段、不同binary/ELF/target、bool版本均显式拒绝。producer metadata继续保留，当前analyzer仍重新计算。该准入要求意味着缺少原native-image身份的旧capture会明确失败，不能将其算成已经支持的重检对象。`analyze_native` 在reader之后、启动record分析之前重新检查deadline，并标明 `budget_kind=cooperative_between_checks`；这如实表示检查间协作预算，不承诺单次有限分析的硬墙钟中断。

已读 `format-receipts-v3/runs/format-v3/{terminal.json,output/result.json,output/steps.json}`：terminal0，两遍ruff/yapf/check-ast均0，六份源码/test SHA逐一与冻结Git bytes核同。此证据只覆盖格式/语法，不等于新增pytest、正常wheel或真实decoder路径通过。`normal-install-terminal-v1.json`实际为terminal1；root所报源传输漏 `cmake/FlagPrism.cmake` 不得被忽略为成功。本席读取时 `normal-install-terminal-v2.json` 是空文件，没有可据以关闭G1的终态。

因此当前有限结论是：M1源码修复可接受；G1仍保留正常wheel/install、受影响normal/-O测试、实际保存binary当前analyzer重检及默认两数学smoke这几项既定收据。没有新增矩阵或资格要求，也不授通用source/loop或whole通过。

## 最终追加：4fc741f 实际交付闭环

本节更新前述待证状态，原失败与首审结论保留为历史。冻结runtime `4fc741f66144b6c2617545b8868b6ac3ae6cf0a1` 已Git核同；新增入口将bytes/bytearray先复制为不可变bytes，再做image身份准入和当前工具检查。mutation fixture在取identity时改写调用者bytearray，要求检查仍使用原快照，修复范围明确，没有发现新增具体缺陷。

本席用stdlib逐项核 `normal-provider-receipts-v2/normal-provider-index-v2.json` 的57个文件及format-v4/v5各7个文件：size/SHA全部一致。format-v4六份源码/test SHA与冻结Git bytes一致；normal-install-v3输入archive内本轮五模块及location test也与冻结bytes一致。原 `normal-install-v1` terminal1仍在归档，未替换成成功记录。

* **正常安装与受影响回归已闭合。** `normal-provider-receipts-v2/runs/normal-install-v3/terminal.json` 为terminal0、53.847693220s；result/steps/assemble日志显示正常assembler、wheel安装及installed imports通过，502个installed members逐字节核wheel，131个component Python文件由assembler核source。wheel SHA `79b9c3499da162264712241cca659d3f1c34c0b6ff0f34624e82bc331292dfc7`。旧native/core及recorder以核同字节复用，没有冒称重建未变C++。四份installed provider测试normal与-O各106通过，包含M1受控故障及mutable-input fixture。
* **当前installed analyzer对真实保存binary重检已闭合。** `runs/installed-provider-actual-v1/terminal.json` 为terminal0、20.695610856s。runner与terminal的script SHA `d291ad31c4e5660a9f75ab94bfa2df96abe3a203f4de48908d1e32b55aa67de6` 相连；源码实际调用新inspection，并在前后检查原metadata与capture文件不变。两份R069 capture各25/38个points、8/18个reader检查结果及2/0个relative-field检查结果；不把第二份的0升级为已支持。原producer SHA `df8885bf…40cbb` 与新analyzer SHA `caee0ca8…f1fa0` 分开，两份实际SDK decoder收据均保PID/PGID/startticks且terminal0。原capture SHA分别仍为 `ef003113…b6648`、`3c7a6282…538d0`，未重放这两个应用。
* **默认新接线的两数学smoke已闭合。** actual runner用同一正常installed interpreter启动受维护public测试，ordinary2/profile2；数值、input不变、tail、host-once均真，实际两capture各22/20 events。测试明确检查identity version3、默认编译产生 `finite_native_diagnostics`，并拒绝source/reader资格提升。它只证明这次接线正常可用，不以events数量授source/loop资格。

本席核实际输入archive的 `smoke.py` SHA为 `6b90df9198cc129829314b2730d3cf92a6c349c997481c1e79eb06b45abb307c`，与受测时维护测试精确相同。随后未提交test的format-v5字节为 `a698b172174ea51588697c0e47441884e68ab3a4e4a58c45f04fb76366087d20`；stdlib AST比较与实际受测脚本完全相同，不冒称最终格式字节曾重新跑数学。quickstart SHA `634d7c13c47fe2d3516b0164947b60d178b52fffba7272b9b08ca6be73aa36e3`，新增load_capture/binary/inspection例子与实际API相符，也明确原image绑定、独立producer/analyzer及资格不升级。format-v5 terminal0；yapf/check-ast两遍通过，ruff按配置无文件可检查而skip，如实区分。

**最终有限结论：本报告M1和G1均闭合，R093 provider接线与其实际交付delta可接受；未发现本范围尚待处理的confirmed blocker/major/minor或必要verification gap。** 各未支持形态及诊断资格false继续保留。原whole的通用source/loop与全登记适用性仍开放，本节不为它们签字。没有执行本机产品/测试、远端或设备，也未读peer报告。
