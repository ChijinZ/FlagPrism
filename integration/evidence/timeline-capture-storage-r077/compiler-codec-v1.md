# R077 capture codec：有限 compiler review

结论：公共内容寻址/压缩路线能完整保留逻辑 capture，所读实现没有厂商特判，也没有提升 source/raw/clock/dependency 资格。确认一个 **Minor M1：writer/reader decoded budget 不对称**；root 已加入提交前校验，当前静态修正方向正确，修正版 fixture 执行和正常安装尚待。旧 inline capture 的读取限额另有兼容回归，正在修补；不以原 offline 单入口已有8MiB限制替其它旧读取路径豁免。原 P03 / ordinary 门均保持独立。

## 实际范围与源码身份

只读了新 `timeline_capture_store.py`、当前 Git diff 涉及的 common/late hooks、Ascend/GCU collectors、`timeline_reexport.py`、`_report.py`、文档新增段落与两个调用测试；完整阅读 `test_capture_object_store.py` 和实际 CPU runner/source loader，复核其依赖的 `timeline_store.read_artifact/bundle_path/persist/export_lock`。检索产品对 `capture_file` 的读取点，没有再发现此次新增 envelope 漏接的产品调用者。没有整体重审、读 peer、执行 helper/产品 import/test、SDK、设备或数学。

初审 codec SHA256 为 `ef6bc989c359d6e49d6e48de175adbce6687a37c7359c03131422cb6bc38088a`，与 retained CPU v1 archive 的源码相同。root 修 M1 后本席实际读取的 codec SHA 为 `27b0c8a8576fe524d28574ebb31af91c10524df3caa5d74f35116aba24d29c4c`；该时 legacy 修复还未到。candidate 基底 HEAD `de69edea1dbc6acf6128415e457164a2d68c8b30`，本 delta 尚未提交。

其它实际观察源码 SHA256：

| 文件 | SHA256 |
| --- | --- |
| `_report.py` | `a43f9693958d5f4c4a108192ad1f560e9749f3a258c105ab980824b29bba75d8` |
| `hooks/timeline.py` | `ea99c829c3ffadfb6407bf80b8bb36fe6af39728d0b54886342f8dbf90021ca8` |
| `hooks/timeline_late.py` | `fa548f0e5332a8b8fbcf7bb5d2694b65d3510e5bd2fe64b781b3d59dce09fed5` |
| `timeline_ascend.py` | `8a3682758b494da5572948a22a656400f0e68cef1f2ffd863a3f79cb3b965eb1` |
| `timeline_enflame.py` | `221c4edd5a8da70ff1045147b0c1963025c44ce7aa0d61b99161434d8645fcc8` |
| `timeline_reexport.py` | `76ce53a2d8b469eeaebfaae1f3249a6e6e3e364f3970680e8790218040ea40e8` |
| `p01_interleaved_specializations.py` | `05c2f8aa25df23da97bb8e355ac426581586bcf01f9e2a8c4e5ba8368c8a0252` |
| tests（M1后、legacy修前） | `ee722291c2cbb5918b10aba2ec39562976971a558d32e77b53fc22747ca7cfaf` |

## Confirmed

### M1 — Minor：成功发布的 capture 可能被同版 reader 拒绝

- **位置：** 初版 `persist_capture:55,78–98` 与 `load_capture:161–165,193–195`。
- **触发：** capture 的逻辑 JSON 接近 `LIMIT`；writer 只检查逻辑长度，随后每个对象还增加 version/value/references 包络。单个包络或 unique 对象解压累计量可超过 reader 同名限制。
- **实际推理：** 无需运行产品即可由长度比较确定。将 LIMIT 临时设8192，取 `{'blob': 'x' * (8192 - len(json_bytes({'blob': ''})))}`，逻辑 JSON 恰8192，原 writer放行；叶对象包络多出字段，descriptor的 decoded_bytes>8192，原 reader在 extent检查拒绝。default64MiB同理。多对象累计包络 overhead也未被writer预检。
- **后果：** immutable `.input.json` 和对象已经发布，后续 decode 却失败；若该 input 已用于允许释放 owner，则其“留存成功”不是同版可读闭包。原 bytes/object仍在，不是确认丢 raw，更不是静默授予错误资格。
- **最小修正/验证：** 在任何 fs publish 前核所有对象包络及唯一对象累计读取预算，与 reader一致；保证发布成功可读，或在发布前明确拒绝。root当前 `decoded_object_bytes`、per-object长度与unique累计检查已静态补上，且都在 `export_lock/persist` 之前。新增near-limit fixture要求抛错且没有capture/zlib文件，方向正确；尚未据旧18绿或旧实际roundtrip声明此修复已执行通过。另新增partial publication失败/重试和offline `_original`闭包 fixture亦已读，静态对应正确。

### M2 — Minor：旧 inline 大 capture 的读取能力被公共8MiB header cap缩窄

- **位置：** 初版 `load_capture:111`（M1后为118）在判断legacy/envelope之前，一律 `read_artifact(..., limit=HEADER_LIMIT)`；common/late/Asc/GCU decode hooks和`_report.write_timeline_page`此前分别直接读JSON或沿原64MiB artifact预算读取。
- **触发：** 原来可由这些路径读取的8–64MiB inline capture；新reader在看到其为legacy之前已拒绝。原 reexport `_json` 的8MiB限制只解释该旧入口，不能证明所有旧live/report读取都有这个上限。
- **后果：** 存量raw/metadata虽未改，升级后的decode/report路径可拒绝旧capture，与“legacy inline remains readable”不符。没有据此断言本次两actual包的单capture已超过8MiB。
- **最小修正/验证：** legacy沿原64MiB有界读取/逻辑验证，只有新envelope的root header保8MiB；加一个大于HEADER_LIMIT而小于LIMIT的legacy正例和超限新envelope负例即可，不需SDK/新数学。root已确认此兼容点并正在修补；本报告此处尚未核到最终修正版。

无 confirmed blocker / major；未发现其它明确 codec/path 误放行。

## 保留的正确性范围

- 编译对象、manifest、loaded/source snapshots及identity作为普通JSON子树完整编码，不按vendor或字段白名单删节。引用位置由versioned envelope的显式path描述，普通嵌套user字典即使含类似marker字段也不会被当引用。重复对象只共享字节，不共享capture/invocation逻辑身份。
- compressed和decoded双SHA/长度、严格zlib EOF/无trailing/无unconsumed数据均检查；对象名由hash精确构造，经原`bundle_path`拒绝绝对/遍历/symlink。path须对上实际容器和None placeholder，重复/父子重叠路径、循环、过深、过多对象和恢复长度均拒绝，不用空值填丢对象。cache复用后仍按每次逻辑展开量计预算。
- objects先persist，最后immutable capture header；原`persist`的fsync/不可覆盖与共享export锁复用，没有先发布header再缺对象的正常成功路径。中途失败允许留下未引用object，不能作为已成功capture；重试使用原不可变字节，未删除历史。
- live collectors与报告读取已接公共reader。offline `_original`让reader把每个实际compressed object加入retain输入闭包，raw/guard/其它compiler artifact检查仍在；canonical revision另绑定codec实现SHA。这不是信任capture内的qualification字段，backend仍从raw和实际证据重新derive。没有新增vendor展示业务分支，没有修改时钟、source边界、dependency或enginebusy的放行规则。

## 实际证据与最少剩余验证

已读两个source-loaded CPU终态0：GCU原85,582,019B→41,347,551B，Ascend111,485,316B→66,963,703B（64MiB为67,108,864B）。各20个`.input.json`/final capture logical JSON（合计40份）还原相等，原raw/trace/其它原件保持，实际大小低于原bundle门。runner仅在复制包上重写这些capture和报告/manifest，没有math或device replay。这是v1源码的真实压缩/还原证据，不是normal installation或修复后fixture证据。

最少后续：对最终冻结源码在原Docker执行新增预算/legacy/发布失败/输入闭包fixture normal/-O；正常wheel安装后用公共reader、report和offline reexport走这两现有复制包并核输入对象闭包、raw/trace与逻辑字段不变。无native/ABI变化，不因codec重复SDK/数学/UI矩阵；只有发生实际输出字节变化时才对相应导出按既有规则核验。不把这份存储修复替代原P03或ordinary阶段关系的剩余工作。

## 有限 closure 追加：ea2c936 / cf0ee96

本次只核原M1/M2、公共reader接线及一行JSON序列化变化，没有重开whole/P03/ordinary审查。已实际读取当前源码、`git diff ea2c936 cf0ee96`、三份normal v3安装和Ascend v4安装收据、三后端E01/offline结果，以及Ascend retained recovery的源码与终态。没有执行产品、测试或设备任务。

### M1 / M2 与安装项关闭

最终codec SHA256为 `437fa67e7e9e13a08cba4bc8a728d2bba07aec90520bd3ed1719f638ba54f9cf`；tests SHA为 `8a1410812d54d0fd598ab1734eeb87fe4071ccd32921dabf4790614be127305b`；`timeline_reexport.py`为 `96e89ba6c79bcd17952f5827dd7eae5019d69f4632a5b1ff990ff2a48ab53835`。

- **M1已关闭：** `persist_capture:81–93` 在任何fs publish前检查每个decoded envelope和unique对象累计decoded预算；原near-limit反例及累计对象overhead负例要求没有capture/zlib发布。不能再成功发布该类同版不可读input。partial publication失败/安全重试与offline `_original` authoritative closure也在本轮fixture集合。
- **M2已关闭：** `load_capture:120–133` 先沿原64MiB有界读取，legacy保原预算，新envelope才施加8MiB header限制；`load_capture_file`仍委托原受限bundle路径，不预先resolve并绕过symlink校验。legacy大于新header正例、新envelope同样大小拒绝已纳入受测源码。
- **正常安装/reader接线有限gap关闭：** source `ea2c936edc3a5bbd695cb46a3758bfd2a6d1196c` 的三正常wheel assembly/install/import均终态0；installed members NVIDIA642/GCU498/Ascend440。每后端normal/-O各 **55 tests +11 subtests** 通过；原日志中的warnings保留，不能归零冒称无warning。没有把source overlay或重复构建旧native当作normal安装。

实际读取的安装收据为root `preflight/nvidia-install-poll-v8.json`、`enflame-install-poll-v7.json`、`ascend-install-poll-v9.json`，终态分别0/73.539s、0/56.295s、0/103.504s。三wheel SHA分别 `a7ba28dafaa63884b8a7bb9cef3a1876c8f1f3380c31ee3ab4f545b138ef7956`、`b2cfb644e549d91b57fdf762c8ba0381a032fc4c87a737cdbc948a557005ab46`、`f789488c98351b80e1e5651b2d737ceb5db84979dbef46ecf7d80d2d480c2938`。

`nvidia-followup-poll-v3` / `enflame-followup-poll-v1` 的实际E01各10调用、两specialization隔离、math/input/tail/exactly-once和完整包门通过；包分别 **28,846,429B / 41,135,845B**。正常安装的公共offline各三fresh processes重导原10 captures，分别40/10 traces字节不变，338/205原artifact保持。Ascend `ascend-followup-poll-v4` 的正常offline亦三process、10captures/10traces、236原artifact不变通过。两process的禁原环境访问范围按收据原样保留，不升格OS隔离。本次未将offline通过冒充source boundary/async/TP通过。

### cf0ee96 单行JSON变化与Ascend预算恢复

`cf0ee96fbc6fb0147c2a9b42e819bca21d7387ec` 相对ea2c936**仅**将 `profile.py:962` 的 `json.dumps(..., indent=2)` 改为 `separators=(',', ':')`，保留相同对象、key/value构造、其它JSON选项和末尾newline。当前profile.py SHA256 `49a8aaa231f06ed13fae730201894f7c3730c089f7615028d92a5c55d224cf7b`。没有改变device采集、raw、ABI、decoder、clock、identity或dependency运算，也没有丢compiler/source文本；`_capture.py:204–214`本来就解析此JSON再建立AI视图。该序列化改动在本有限范围内安全，未发现具体缺陷。

Ascend原E01 terminal **仍为1**，原包67,773,556B超64MiB **664,692B**；其math/隔离/raw与offline成功没有替它放宽包预算。cf0ee96的Ascend正常wheel v4（`ascend-install-poll-v12`）终态0/103.094s、440members、normal/-O各55+11；wheel SHA `c9a5bc231bd634b4803994a8f11c2dba7a8ec96a8fe71eadbec913cb55c6a22e`。

补读 `ascend_recover_whitespace_v1.py`：只复制自有失败目录，minify `capture/raw/native/capture.observations.json`并`write_manifest`，核JSON值相同、原件所有SHA不变、其它copied artifacts（含raw/trace）不变；随后从维护p01脚本原AST的post-finalize起点执行原验收尾段，没有执行device setup/launch/finalize，也没有删改预算条件。`ascend-recover-poll-v1`的实际脚本SHA `d145d4eb3fe3ded583adfb80040d3b8c4e6d9db08652c9b04ce991118ad9aaac`，终态0/10.030s，在正常cf0ee96解释器下恢复包 **66,815,281B <=67,108,864B**，无损省958,275B。结果明确`original_device_terminal=1`、`device_executed_here=False`、`application_replayed=False`。这支持本次**格式修复后的留存包预算与原post-finalize验收闭环**，没有把首次真机失败改为成功或声称新ELF执行。

本追加关闭原codec两项确认缺陷及正常安装/公共reader受影响回归gap。60新trace实际TP收据尚未由本席读取，继续单列待验；原P03、ordinary与whole-goal结论不变，也不因压缩/大小通过而新增source/raw资格。
