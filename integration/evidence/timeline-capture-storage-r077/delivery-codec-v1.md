# R077 capture codec：有限独立 delivery 走查

对象：candidate `artifacts/timeline/run-058/candidate`，HEAD `de69edea1dbc6acf6128415e457164a2d68c8b30` 上的未提交公共 capture 存储 delta；据请求 runtime 基线 `61cb831`。不作整体资格重审。未执行产品/import/test/SDK/设备/TP/browser，未读取 peer 报告，仅只读代码、Git 与现有收据；只写本报告。

请求配置沿用原席 GPT-6.1-Sol/xhigh；实际 resolved 型号/深度 unknown。

## 结论

确认两项具体缺陷：**M1 文档公开的维护消费者仍假定 capture JSON inline；M2 writer 能发布 reader 必拒的近预算对象。** M2 在本次走查期间已有可见源码修复，尚不能借 v1 的源码加载收据宣称修复验证/正常安装闭合；M1 的统一 reader 迁移正在进行。

压缩对象进入重导输入闭包和 canonical 修订身份的设计/接线未见直接遗漏。当前 18 fixture 与两个真实旧包 CPU roundtrip 支持原 codec 的有限可用性，不等于正常 wheel、新 producer/E01 或公开 offline reexport 已通过。

## 源码身份与范围

首次读到的关键 SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| `Profiler/python/flagtree_profiler/timeline_capture_store.py` | `ef6bc989c359d6e49d6e48de175adbce6687a37c7359c03131422cb6bc38088a` |
| `Profiler/python/flagtree_profiler/timeline_reexport.py` | `76ce53a2d8b469eeaebfaae1f3249a6e6e3e364f3970680e8790218040ea40e8` |
| `tests/timeline/test_capture_object_store.py` | `b8b85df085792fd74fffcef27a1e20a9d784856a66a8eaf1b5364ef96837b470` |
| `tests/timeline/p01_interleaved_specializations.py` | `05c2f8aa25df23da97bb8e355ac426581586bcf01f9e2a8c4e5ba8368c8a0252` |

完整读取新 codec；读取此次 hooks timeline/late、Asc/GCU、`timeline_reexport.py`、`_report.py`、runtime 文档的 diff，以及两个新/变更测试；为核读路径，检查文档中已有维护消费者的 capture-file 读取方式。没有借此扩大到其数学或整套 native checker。

两个 `*-codec-cpu-input-v1.tgz` 中实际 codec SHA 都是上述 `ef6bc…`；其实际 fixture 文件 SHA 为 `ddfe78214949d08fe1aa5e8eebf3d4189e026cd8559fcf47794d6de2ee736b8d`。因此不将旧 source-loaded 执行收据泛化到本地后增的 fixture/修复字节。

## Confirmed findings

### M1 — Major：新默认 capture envelope 使多项公开维护命令直接失效

**触发。** `persist_capture` 对 ≥4096-byte 的子树写对象引用，新的 `capture_file` 因而可只有 `flagprism_capture_storage/value/references` 三个 envelope 字段。正常实际 compiler metadata 会命中此路径；两份真实旧包已各转换20个 capture/input 文件，也证明这不是只存在于人为损坏输入的格式。

**具体位置。** 初始 delta 只迁移了 `_report.py`、collector、reexport 和 E01 / native-locations 两个维护脚本，以下仍直接 `json.loads(capture_file)` 后读取展开字段：

- `tests/timeline/p01_controlled_workloads.py:68–70`：随后取 `events_file`。
- `tests/timeline/p01_review_recovery.py:91–92`：随后取 `owner`；其命令仍公开于 `Profiler/docs/timeline_testing.md:356` 起。
- `tests/timeline/p01_nvidia_native_loops.py:26–28`：将 envelope 交给实际 machine-map loader；命令公开于 testing `:417` 起。
- `tests/timeline/p01_enflame_observed_dependencies.py:17–18`：随后取 `raw_file`；由 runtime `:528` 公开。

同类读取还存在于 operation origins / matrix / count-lifetime / offline / dependency-TP 的 timeline-input 路径。这里只确认共同的格式误读，不把每个脚本算成一个独立产品缺陷；独立 `--manifest` TP 路径不依赖这个 capture reader，不受同一方式影响。

**后果。** 新正常包在这些公开维护路径会以 `KeyError`/错误字段拒绝，尚未执行它们要检查的原有语义门。旧 inline bundle 继续可读，不能掩盖新格式回归。E01 自身已迁移不代表其它文档命令可用。

**最小修复/验证。** 将这些 capture 与 `.input.json` 的逻辑读取统一接到支持新/旧格式的共同 reader；纯字节留存/哈希比较仍应读取原物理 bytes。用现有新格式包做对应的 CPU 读取/离线消费者检查，并保一个旧 inline 对照；无需重新运行其数学。收尾时 `load_capture_file` helper 已加入，但所列四个消费者在本席最后读取时尚未完成迁移；不提前记 closure。

### M2 — Minor：writer/reader 对 object envelope 与累计解码预算不对称

**原位置。** codec 首次 SHA `ef6bc…` 的 `persist_capture:55` 只核展开文档 ≤`LIMIT`；`:78–91` 将包有固定字段的 object envelope 压缩并直接记 `decoded_bytes`。reader `:161–167` 要求每对象 `decoded_bytes≤LIMIT`，`:193–195` 又要求所有独立对象的累计 decoded bytes ≤`LIMIT`。writer 当时没有对应约束。

**确定反例，不执行产品。** 对函数明示接受的字典 `{'s': 'x' * (LIMIT-9)}`，按其实际 canonical JSON 编码，logical document 恰好 `LIMIT` bytes；字符串 leaf 的 storage envelope 恰好 `LIMIT+50` bytes。writer 会通过 logical budget 并发布对象/header，reader 必在 descriptor extent 检查拒绝。这里的9/59字节固定开销只用 stdlib JSON 算式核对，没有运行 codec。类似地，多个对象加 envelope/reference 开销可使累计 decoded bytes 超限，而原 logical JSON 仍在限内。

**后果。** writer 可以成功提交随后自身无法读回的 capture。该问题在预算边缘触发；未确认当前两真实包命中，也未声称 raw 错误或资格伪造。

**最小修复/验证。** 在发布任何 object/header 前，writer 必须与 reader 使用一致的单对象及 unique-object 累计解码限制；用缩小 `LIMIT=8192` 的一个近上限负例和一个累计 envelope 开销负例核“拒绝时未发布文件”，无需设备。

**可见修复进度。** 收尾 codec SHA `9adf16a563c3fad50bb936be9fc8fd3bd6a1819db147e74a81e95d977332202e` 已在 `encode` 中加每对象 `len(payload)≤LIMIT`，并按唯一 object name 累计 decoded payload，检查都在最终 publish 前。新增 fixture 源码也覆盖 near-limit / cumulative 两种情形；当时测试文件 SHA `8a84fcb1e4bd55c5c4ea2f30347ba9e251a5bbc92b9feb0ec01802a087fccaad`。支持该 source fix 的有限判断，**执行/正常安装闭环待后续实际字节收据**。

Confirmed blocker：无新增。未发现其它需要额外扩门的 confirmed 代码缺陷。

## 闭包、legacy 与文档检查

- `load_capture(..., retain=...)` 对每个实际读到并核过 compressed/decoded 长度与 SHA 的对象调用 retain，递归读取子对象，cache 只复用已核相同完整 key 的对象；因此同一物理对象共享不导致丢输入文件。
- `timeline_reexport._original` 将该 callback 接入已有 `sources`，随后保 root `.input.json`、raw、guard 和 compiler/source artifacts；重导 `decoder_inputs.original_inputs` 包括这些压缩对象的内容身份。`timeline_capture_store.py` 的实际源码 SHA 另进入 `implementation_sha256`，因此 codec 更新不会静默沿用旧 canonical revision。
- objects 先持久化、header 最后提交，沿用 bundle path/symlink拒绝、OS锁和 immutable/fsync publication；错误不会把半对象引用作为成功 header 发布。新 pending decoder 与最终 HTML report 都使用共同 reader。未见把存储共享变成 clock/来源资格授予的改动。
- 原 runtime 的授权/完整性检查由显式 `_need`/异常实现，不靠 assert。fixture 中的 assert 由 pytest 正常重写；不能只因 test 用 assert 就认定 `-O` 没有检查产品拒绝逻辑。
- legacy inline 分支及普通用户字典中的嵌套 marker 保留；新格式引用只由显式 envelope 解释。收尾版本另有 legacy inline/read budget fixture 和 publication failure/retry、`_original` 闭包 fixture 源码，但旧18项收据未运行这些后增测试。
- runtime 文档给出了真实 `load_capture(timeline_directory, index_entry['capture_file'])` 用法、必须带走 objects目录、损坏/缺失拒绝和不增加时间资格，方向正确。M1 是现存维护命令尚未随这项公开格式变化迁移，并非文档里新 reader 名称错误。

## 现有实证与必要最少后续验证

已读 `enflame-codec-cpu-poll-v1.json` / `ascend-codec-cpu-poll-v1.json` 的实际 terminal/result，以及 CPU runner/source-loader：它们明确是 `source_loaded=true, normal_install=false`。GCU terminal0/5.574s，Asc terminal0/17.439s；GCU原85,582,019→41,347,551 bytes，Asc111,485,316→66,963,703 bytes，两份各20个逻辑 capture文件恢复相等，原 raw/trace/source/compiler files保持，未重放数学。18 normal/-O fixtures 在GCU源码加载路径执行；runner只 source-load codec/HTML report，**没有用该收据执行新的正常 collector/reexport 整链**。

本 delta 最少还需：修复后 fixture normal/-O；正常匹配 wheel 安装确认新模块/共同 reader 字节；已计划的受影响 E01 producer检查；从其新格式真实包运行公开 reexport，核对象闭包进入 revision inputs、正常重复重导/原件不变，并对迁移后的维护读取保新旧格式对照。可以复用同一真实包，不另造数学、重跑旧全矩阵或重复同字节 TP/UI；C++/SDK 未变不要求重建。

只支持这个有限存储修复的推进；不授 source boundary、ordinary pipeline、性能或 whole-goal 资格。后续字节与安装到齐后，应追加上述两项的准确 closure，保留此首次 finding/失败范围。

## 有限 closure 追加：最终源码、正常安装与完整原件

本追加只处理上述 M1/M2 及这个存储 delta 的安装、生产、离线输入闭包和新 trace 验证，不替换首次 finding。读取的最终 candidate HEAD 为 `cf0ee96fbc6fb0147c2a9b42e819bca21d7387ec`；共同存储/reader 修复基线为 `ea2c936edc3a5bbd695cb46a3758bfd2a6d1196c`。配置仍为请求 GPT-6.1-Sol/xhigh，实际 resolved 型号/effort 未暴露，记 unknown。没有执行产品、测试、设备或服务器操作；以下执行结果来自实际原件，本席仅用 Git/stdlib 读取并核验。

最终 `timeline_capture_store.py` SHA 为 `437fa67e7e9e13a08cba4bc8a728d2bba07aec90520bd3ed1719f638ba54f9cf`；`timeline_reexport.py` 为 `96e89ba6c79bcd17952f5827dd7eae5019d69f4632a5b1ff990ff2a48ab53835`。`cf0ee96` 另仅将 `profile.py:962` 的 collector observations JSON 改为 compact separators；没有更改其逻辑值或 native/C++。

### 原 finding 状态

- **M1 closed，限于共同 capture reader 迁移与交付。** `16ebe22` 的迁移记录覆盖46个文件、53处读取；原报告点名的四个消费者现已使用 `load_capture_file`，其余 capture/input 逻辑读取也接入同一新旧格式 reader。正常 wheel 内的新旧格式、共同 reader、offline/registry 等受影响 fixture 均实际执行；下述三后端真实新格式包还通过已安装公开 reexport 的三个独立进程读取、重复导出与原件核同。没有把这组证据说成每个维护数学脚本均重新执行。
- **M2 closed。** 最终 codec `:58–90` 按唯一对象累计 decoded payload，并在任何发布前同时核每对象和累计 `LIMIT`。正常安装的 normal/-O fixture 实际覆盖缩小预算的 near-limit8192、累计 envelope 开销及拒绝时不发布文件，另保 legacy、publication failure/retry 和对象闭包检查。原先“writer 成功、reader 必拒绝”的不对称已有对应源修复和执行收据。

本次有限补审未发现新增 confirmed blocker/major/minor。原安装失败和 Ascend 原 E01 预算失败仍保留，不用后续成功覆盖历史事实。

### 正常 wheel 安装与实际使用

精确安装终态见 root `preflight/nvidia-install-poll-v8.json`、`enflame-install-poll-v7.json`、`ascend-install-poll-v9.json`，以及 compact JSON 后 `ascend-install-poll-v12.json`。它们均有正常 wheel 构建、成员/安装 import 核对及实际 step 收据，不能与最初 source-loaded CPU runner 混称。

| 后端/版本 | source | steps 全部0 | wheel members | 已安装 normal / -O |
|---|---|---:|---:|---|
| NVIDIA native-install-v3 | ea2c936 | 11 | 642 | 各55 tests + 11 subtests |
| GCU native-install-v3 | ea2c936 | 9 | 498 | 各55 tests + 11 subtests |
| Ascend native-install-v3 | ea2c936 | 10 | 440 | 各55 tests + 11 subtests |
| Ascend native-install-v4 | cf0ee96 | 10 | 440 | 各55 tests + 11 subtests |

native/core/recorder 源码未变的复用有身份核对；这些收据没有冒称本次重建所有 native。对应 wheel SHA 依次为 `a7ba28dafaa63884b8a7bb9cef3a1876c8f1f3380c31ee3ab4f545b138ef7956`、`b2cfb644e549d91b57fdf762c8ba0381a032fc4c87a737cdbc948a557005ab46`、`f789488c98351b80e1e5651b2d737ceb5db84979dbef46ecf7d80d2d480c2938`、`c9a5bc231bd634b4803994a8f11c2dba7a8ec96a8fe71eadbec913cb55c6a22e`。

新 E01 与离线原件分别见 `nvidia-followup-poll-v3.json`、`enflame-followup-poll-v1.json`、`ascend-followup-poll-v3.json` / `-v4.json`。NV/GCU 实际一 session 十调用、两 binary 交错的数学/input/tail/State/raw 等检查及最终预算均通过，包为28,846,429 / 41,135,845 bytes。三家公共离线读取均通过三个新进程（含两次拒绝原应用环境），NV40 / GCU10 / Asc10 traces 字节核同；分别338 / 205 / 236个原始 artifacts 不变，没有数学重放。

**Ascend 必须区分原设备执行与 retained recovery。** 原 E01-v2 实际 terminal1 发生于最后完整包预算断言，67,773,556 bytes；此前十调用、两 binary、数学和 raw 检查通过。`ascend-recover-poll-v1.json` 的 terminal0 使用正常 cf0ee96 interpreter，只在自有失败包副本 minify `raw/native/capture.observations.json` 并刷新 manifest，再按维护测试原 AST 执行完整 post-finalize 验收。结果66,815,281 bytes，距64MiB余293,583 bytes。已读 runner 的 JSON 值相等和 SHA ledger 检查：原失败包不变，副本除该 JSON 空白和 manifest 外所有原件/raw/trace SHA 均不变。该证据支持既有设备结果的无损存储恢复与最终预算闭环，**不记为新的设备 E01 terminal0**。

### 压缩输入闭包与 TP 原始依据

除已读 `_original` → `load_capture(..., retain=...)` 及 codec SHA 进入 revision 的源码外，本席直接读取三个最终 archive 中30个实际 canonical revision 的 `inputs.json`：重算 revision 身份、逐层跟随 capture/input envelope 的对象引用、核 compressed/decoded 长度与 SHA，并与每项 `original_inputs` 的实际文件 bytes/SHA 比对。NV10 revisions /20个 transitive object references、GCU10/120、Asc10/210，均无不符；每个 revision 都含最终 codec SHA。这里的 references 是各 revision 实际闭包引用数，不作为新语义资格计数。

`nvidia-tp-poll-v2.json` 为实际 pinned TP terminal0。完整原件是 NVIDIA archive 内 `runs/tp-v1/output/TP/result.json`，共60 checks（NV40/GCU10/Asc10），verifier SHA `75e1b08b1dd71256dd442f6ad3bfbffe745ba900026e8f6493e6ef208931a618`。本席核60个输入 trace SHA 均能对应实际归档 `.pftrace`，60项 `exact_ns_and_raw_references=true`、`importer_errors=[]`，每项263行完整 importer stats（共15,780行），无正值 error/data_loss。不是只依据“trace 能打开”或摘要总数；也不从 TP 通过推导 source/clock/async/UI 等其它门通过。

三个 `*-receipts-v2.tgz` 均已用 stdlib 独立逐 regular member 对内置 index 核实际 bytes/SHA，零不符；archive 自身 SHA 如下。小摘要 `integration/evidence/timeline-capture-storage-r077/summary.json` 只作索引，未代替原件。

| archive | regular members | archive SHA256 |
|---|---:|---|
| nvidia-receipts-v2.tgz | 1251 | `20a61ffc2c645ff8cb5aea134ca7982b20923cc564f437f0f806e69f37f6c90c` |
| enflame-receipts-v2.tgz | 814 | `70aa2036d71d61066a9793bd6ee64e5c402f5c089f3c843444c431e80b2f8059` |
| ascend-receipts-v2.tgz | 1197 | `a26f59643befa1433cce1199bc906946dfb3a01c861d3337c77210c7cc251efe` |

**有限交付结论：** 原 M1/M2 及本 delta 的正常安装、新格式实际生产/离线读取、对象输入闭包、新60份 counter trace TP 缺口已闭合，可支持这一存储修复交付。本席不再为本 delta 留待安装或 TP 的 verification gap；未复核的整体合同、原 kernel writer/source boundary、pipeline、其它数学/后端资格和用户延期的性能认证不由本追加授予通过，也不需要为本次 closure 重采未变数学、旧 SQL 或 UI。
