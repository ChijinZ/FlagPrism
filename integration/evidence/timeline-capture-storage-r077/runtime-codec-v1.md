# R077 capture object store：独立有限 runtime review

本席请求配置为 GPT-6.1-Sol / xhigh；实际 resolved serving 配置未暴露，记 unknown。本次只读产品源码、Git diff、测试源码、stdlib JSON/tar/SHA 与直接收据；没有运行产品、import、pytest、checker、SDK、服务器或设备，没有阅读其它席报告。仅本报告为本席写入。

## 结论与身份

本 delta 采用显式、有版本的引用包裹和内容寻址压缩对象，未修改设备 raw ABI、发布协议、时钟或依赖资格。产品读点已接入解码器，原件闭包在离线 canonical 输入中包含所用 CAS 文件。初版存在一项确认的 writer/reader 预算不对称；已实际读到候选源码修复及对应新增 fixture，但最终源码安装与新增 fixture 的执行收据尚未到达本席，不能记为验证已闭。除此未确认第二项产品 runtime blocker/major。

观察时 Git HEAD 为 `de69edea1dbc6acf6128415e457164a2d68c8b30`，所审变更未提交，维护脚本迁移仍在进行。这不是对最终冻结字节的安装签字。观察到的产品字节如下：

| 文件（相对 candidate） | SHA-256 |
| --- | --- |
| `Profiler/python/flagtree_profiler/timeline_capture_store.py` | `9adf16a563c3fad50bb936be9fc8fd3bd6a1819db147e74a81e95d977332202e` |
| `Profiler/python/flagtree_profiler/hooks/timeline.py` | `ea99c829c3ffadfb6407bf80b8bb36fe6af39728d0b54886342f8dbf90021ca8` |
| `Profiler/python/flagtree_profiler/hooks/timeline_late.py` | `fa548f0e5332a8b8fbcf7bb5d2694b65d3510e5bd2fe64b781b3d59dce09fed5` |
| `Profiler/python/flagtree_profiler/timeline_ascend.py` | `8a3682758b494da5572948a22a656400f0e68cef1f2ffd863a3f79cb3b965eb1` |
| `Profiler/python/flagtree_profiler/timeline_enflame.py` | `221c4edd5a8da70ff1045147b0c1963025c44ce7aa0d61b99161434d8645fcc8` |
| `Profiler/python/flagtree_profiler/timeline_reexport.py` | `76ce53a2d8b469eeaebfaae1f3249a6e6e3e364f3970680e8790218040ea40e8` |
| `Profiler/python/flagtree_profiler/_report.py` | `a43f9693958d5f4c4a108192ad1f560e9749f3a258c105ab980824b29bba75d8` |
| `tests/timeline/test_capture_object_store.py` | `8a84fcb1e4bd55c5c4ea2f30347ba9e251a5bbc92b9feb0ec01802a087fccaad` |

## Confirmed finding

### M1 — major，初版可发布 reader 必拒绝的 capture；候选源码已修，执行验证 pending

- 位置：初读 `timeline_capture_store.py::persist_capture/encode`，SHA `ef6bc989c359d6e49d6e48de175adbce6687a37c7359c03131422cb6bc38088a`。该字节也正是两份 `*-codec-cpu-input-v1.tgz` 内实际使用的源码。初版只检查完整展开 capture 的 JSON 字节数；没有限制每个对象加 envelope 后的 decoded extent，也没有限制 unique 对象 decoded extent 的累计值。`load_capture` 则同时实施这两个限制。
- 触发与最小复现：在 SDK Docker 的 CPU fixture 将 `LIMIT` 缩为 8192，保存 `{'blob': 'x' * 8180}`。按相同 compact JSON 规则，展开文档为 8192 字节，leaf envelope 为 8239 字节。初版 writer 可以成功发布，reader 因 `decoded_bytes > LIMIT` 拒绝。另一例 `{'a': 'x'*4050, 'b': 'y'*4050}` 展开为 8116 字节，两个各 4109 字节的不同对象累计 8218 字节，触发 aggregate read budget。上述长度仅以 stdlib JSON 计算，本席未执行产品复现。
- 后果：正常保留路径在 `persist_capture` 和外部 compiler/source 原件持久化成功之后释放 owner；这种成功写出的 metadata 此后不能通过公共 reader、报告或离线恢复读取。压缩数据仍保留，并非已证不可逆信息丢失，但成功发布的可恢复性合同被破坏。
- 已读修复：当前 `timeline_capture_store.py:83–90` 在进入任何文件发布之前检查每个 envelope，并按 CAS 唯一对象累计 `decoded_object_bytes <= LIMIT`。它保留原上限，并在不可读编码发布之前报错。`test_capture_object_store.py:174–191` 两个 negative 分别要求上述边界失败且没有 header/object 文件发布。修复在静态上关闭这两个具体路径；不能拿旧 18 项通过收据证明新修复已执行。
- 最少关闭项：最终安装字节与候选 SHA 对齐，normal / `-O` 执行这两个预发布拒绝 fixture，并保留原 roundtrip/损坏对象用例。无需新设备数学或扩大矩阵。

## 生命周期、闭包与限额走查

- `persist_capture` 在内存中完成树变换、对象数/深度/大小检查，再持有 `export_lock`，逐一不可变持久化对象，最后持久化引用 header。沿用 `timeline_store.persist` 的 fsync、原子 create-if-absent 和不同字节拒绝覆盖规则。中途失败可留下尚未被 header 引用的对象，重试可复用相同字节；不会先发布指向缺失对象的本次 header。
- `hooks/timeline.py:219–275` 顺序仍为 raw/guard、CAS/header、compiler/source 原件、pending 登记、owner release。编码或文件写入异常会在 release 之前退出；解码/派生失败时原件和 pending 仍可供无应用重放恢复。这个 delta 没有改 owner/SDK 释放、session raw/guard 预算或并发准入规则。
- 引用由独立 descriptor 的路径指定，普通用户字典不因含相似 marker 而被解释。reader 检查版本的精确整数类型、路径/容器/空占位、重叠路径、CAS 文件名、压缩及 decoded SHA/extent；对象由安全 bundle path 读取，symlink 拒绝。流式解压带 output limit，要求 eof、无 trailing/unused/unconsumed 数据，重复引用仍累计最终展开大小。
- 上限仍为 64 MiB 展开文档/对象读取累计、8 MiB 新 envelope header、256 对象/引用、深度 64。当前 reader 对旧 inline capture 使用 64 MiB 界限，避免把旧文档错误收紧至新 header 上限。新 writer 不修改输入对象。
- `timeline_reexport._original` 将 CAS `retain` 回调传给 reader，随后登记 header、raw、guard 和 compiler/source 原件；`original_inputs` 包含所用对象压缩字节的 SHA/size，canonical implementation identity 新增 codec 源码 SHA。缺对象/损坏对象不能从历史缓存授予资格。
- 已读三后端的 input/completed-capture 写点、三后端 decode 读点、`_report.write_timeline_page` 和 `timeline_reexport` 读点。Asc/GCU 新生成的 `.events.json` 改 compact JSON，不删逻辑字段，未改 raw 或已存在事件原件。没有新增时钟、source boundary、dependency、participation、busy 或 ordinary pipeline 资格。

## 直接证据与其范围

实际打开并解析：

| 收据 | SHA-256 | 直接支持 |
| --- | --- | --- |
| `preflight/enflame-codec-cpu-poll-v1.json` | `4791f4364f89bc1a34c73949aa6e5e8820acfe95a57525cbdb4b577433ee72e4` | terminal 0；旧实际 GCU 包 85,582,019 → 41,347,551 字节；20 份 capture metadata 相等 |
| `preflight/ascend-codec-cpu-poll-v1.json` | `d284806de0ce013100cfd15d0d70f40deb85949a4f05b325b60c8884ea310a0e` | terminal 0；旧实际 Asc 包 111,485,316 → 66,963,703 字节；20 份 capture metadata 相等 |

两份收据都明确 `source_loaded: true`、`normal_install: false`、`device_executed: false`、`application_replayed: false`。40 份 metadata 是每后端 10 调用的 input/completed 两份文档，不是 40 次新设备调用。

实际读了 `codec_cpu_runner_v1.py`、`codec_source_load_v1.py` 及两个 input tar 的成员身份：runner 复制既有包，只改 capture metadata、report/index.html、manifest.json；逐原件检查未允许改变文件的 bytes/SHA，并检查原始源包所有文件 SHA 不变；新增文件限 CAS 目录。它调用相同 reader 比较完整逻辑 JSON，再生成 timeline 页面及 manifest。因此这两份结果支持旧实际包的无损重编码、页面读取和相应体积，不只是压缩率估算。Asc 剩余约 145 KiB 的包预算余量不等于承诺任何未来 workload 都有相同余量。

初版 input 包内 codec SHA 均为 `ef6bc989...`，test SHA 为 `ddfe78214949d08fe1aa5e8eebf3d4189e026cd8559fcf47794d6de2ee736b8d`。旧 18 项 normal/`-O` 测试由 enflame runner 分支执行；Asc 分支进行实际包 roundtrip，没有据此声称每后端各执行一套 18 项。当前新增预算、旧 inline header 界限、对象发布失败重试和 `_original` 输入闭包 fixture 已读源码，尚未获得其新执行终态。

## Verification gaps 与迁移中观察

1. 最终正常安装尚未提供本席收据；旧 source-loaded 结果不覆盖最终新增 reader 入口、预算修复或维护脚本变更。最小补证是最终 wheel/member/import 字节对齐、定向 CPU fixture normal/`-O`，并以一份既有 CAS 实际包通过公开离线导出，确认输入闭包及缺对象时明确失败。无需新数学/TP/UI/SDK 运行。
2. 维护脚本迁移在走查期间持续发生，不能把中间态视作最终全部消费者已关闭。已向 root 定位 `p01_offline_reexport.py:164` 将普通 `index.json` 误传 `load_capture_file`，该入口要求父目录为 `captures`，会必然报错；index 应继续普通 JSON 读取。另定向定位 `p01_nvidia_matrix_inputs.py:91`、`p01_nvidia_pipeline_inputs.py:81` 和 `ascend_machine_probe.py:30–31` 的直接 capture JSON 读取。这里只记录具体维护入口，不认定为第二项产品 runtime 缺陷，也不要求重跑旧矩阵；最终迁移需保留原件 SHA 登记语义。

Optional：无本席新增 optional 工程要求。没有引入通用机器码证明器、任意 ISA 证明或新 workload 矩阵。

## 已读/未读边界与交付判断

已读：上述新增 codec 全文、存储基元全文相关段、产品调用文件的完整 delta 及 retain/decode/reexport/report 周边、runtime 文档新增段、对象 fixture 全文、新旧 input tar 中相关成员、两份终态、CPU runner/source-loader；定向搜索产品和维护脚本 capture 消费点。

未读/未运行：没有逐个大 raw/trace 重新解码，没有重审其它 runtime 模块或所有维护脚本全文，没有独立执行 ledger/checker；没有最终新 wheel、最终新 fixture 终态或新 live collector capture 的直接收据。源码仍变动，报告只绑定上列观察字节。

本范围可给出有限源码判断：CAS 方案和主要生命周期/闭包接线成立，已知预算缺陷的源码修复可接受，最终验证仍 pending。原 whole-runtime 结论保持：有限 P03 最终机器边界及 ordinary 关键依赖/适配边界等既有未完成项不会因压缩存储关闭；本报告不授 whole-goal 交付资格。

## 有限验证 closure — ea2c936 / cf0ee96

本节更新上述 **M1 writer/reader 预算不对称、legacy/公共读取接线的验证状态**，保留初版缺陷和旧失败事实。没有重新进行 whole review，也没有运行产品/测试/SDK/设备。release 的 M2/T1 closure 仍独立记录于 `runtime-release-v1.md`。

### M1 与旧格式/输入闭包验证已关闭

三份正常安装 v3 收据已实际读取：`enflame-install-poll-v7.json`、`nvidia-install-poll-v8.json`、`ascend-install-poll-v9.json`。三份均绑定 `ea2c936edc3a5bbd695cb46a3758bfd2a6d1196c`、terminal 0、所有步骤 0，各 normal / `-O` **55 passed + 11 subtests**。其收据 SHA 分别为 `79921bbfbadfcec1770e4c864913a2bef58c566d16ba8898b15f0e94efa89bc2`、`276800c5551a5213f361a7672cf0645b790afa9c3243e5d416e3d3ffd406e451`、`88c0aabc7f6e199dafdfc828f65f113ee99c76c68c222b98332940327ea89e2b`。

实际比较三个 v3 input tar 的 codec/test 与 Git freeze，均逐字节相等：codec SHA `437fa67e7e9e13a08cba4bc8a728d2bba07aec90520bd3ed1719f638ba54f9cf`；object-store test SHA `8a1410812d54d0fd598ab1734eeb87fe4071ccd32921dabf4790614be127305b`。已读安装 runner 在测试前逐 wheel member 核对正常安装字节，新 venv 使用 `-I`、移除 PYTHONPATH，不是 source-loaded 执行。

两个原 M1 near-limit/unique-cumulative negative、legacy inline 不受新 header 上限误限、缺对象/损坏对象、发布失败后重试及 `_original` CAS 输入闭包均在该测试文件内执行。writer 仍在任何发布之前检查每个 envelope 和 unique decoded 总量，没有放宽 64 MiB。reader 的 retain 回调现同时登记 header 和所用 CAS 文件；三份安装里的 fixture 明确覆盖该集合及 SHA/size。**M1 源码修复及所列 legacy/闭包 CPU 验证 pending 状态在此关闭。**

前述维护入口观察也已定向复核：公共 offline test 的 `index.json` 继续普通 JSON 读取，仅 capture 交 reader；matrix/pipeline input qualification 使用带 retain 回调的 reader，保留 header/对象 SHA 记录；Asc machine probe 使用新 reader。本席没有据此声称每一个维护脚本都实际重跑。

### 公共新 schema 离线读取：三后端已获直接有限证据

| 收据（相对 R077 preflight） | 收据 SHA-256 | 实际结果 |
| --- | --- | --- |
| `nvidia-followup-poll-v3.json` | `a77de81ff362fbfb5093c0810ec9dcb7e857e4ca783f8d7c83439724f4c75c5e` | E01-v2 terminal 0，整包 28,846,429 B；offline terminal 0，10 capture / 40 trace |
| `enflame-followup-poll-v1.json` | `59a83f5554823fe4475fe7ef288472c644137212082304d16a2338f1ece62f00` | E01-v2 terminal 0，整包 41,135,845 B；offline terminal 0，10 capture / 10 trace |
| `ascend-followup-poll-v4.json` | `497816a2eb33e4124e375768bdc65b6f931649e71853e94975ccff9c2dfaab58` | 原 E01-v2 terminal **1**；offline terminal 0，10 capture / 10 trace |

三份 offline 结果均绑定 ea2c936 正常安装，记录三个 fresh reexport processes、其中两个进程拒绝原环境路径及 subprocess、application_replayed=false、重建 trace 与原包 SHA 一致。原件不变计数分别为 NV 338、GCU 205、Asc 236。实际读了打包的 `offline_runner_v1.py` / `p01_offline_reexport.py`：它们通过公开 module 和两个 guarded normal/`-O` 子进程重建，比较完整 reexport identity、原 canonical 语义、原文件 SHA 与每个 observer 的 trace SHA。三个 input tar 的脚本均等于当前维护源码，故这不是仅在 JSON 摘要里声称 reader 成功。

这关闭了本报告所需的公共新 schema 离线读取验证缺口。三份明确 `trace_processor_deferred=true` / `trace_processor_verified_here=false`；本节不将这些收据授予 TP、UI 或其它时间资格，也不代替另行进行的 TP60。

### Asc 整包失败保留；cf0ee96 的空白修复与 retained-only 恢复

已实际读 Asc 原 E01 stderr：在最终 `Complete bundle exceeds 64MiB` 检查失败。`ascend-e01-size-v2.json`（SHA `41d95fb14f57d8c75872ff46dceafabd380e2a1ba5b50661a1d463a63efe13d8`）为 **67,773,556 B**。不能把三进程 offline 成功解释为原 E01 whole 已成功。

`cf0ee96fbc6fb0147c2a9b42e819bca21d7387ec` 的产品 diff 仅将 `profile.py::_augment_instrumentation_artifacts` 写 observations JSON 的 `indent=2` 换为 `separators=(',', ':')`；字段、值、转义策略和末尾换行不变。profile.py SHA `49a8aaa231f06ed13fae730201894f7c3730c089f7615028d92a5c55d224cf7b`。未发现此一行变化的新具体 bug，也没有时钟/依赖/边界资格变化。

`ascend-install-poll-v12.json`（SHA `7fae466e99936d73d149dd5b5002a20a367ff08a6163f00c772f934ae2d6a77e`）绑定 cf0ee96，Asc v4 wheel SHA `c9a5bc231bd634b4803994a8f11c2dba7a8ec96a8fe71eadbec913cb55c6a22e`、440 installed members、terminal 0、steps 全 0，normal / `-O` 各 55 passed + 11 subtests。实际检查 v4 input 的 profile/codec/test 字节均等于该 freeze。

`ascend-recover-poll-v1.json`（SHA `ef3a06b5796a53e453fd6f362650fdb0859d8152cdd6e94fb262542d4a5ab18a`）terminal 0，结果为 **66,815,281 B**，明确 original_device_terminal=1、device_executed_here=false、application_replayed=false。已读其 input tar 和 runner（SHA `d145d4eb3fe3ded583adfb80040d3b8c4e6d9db08652c9b04ce991118ad9aaac`）：只复制原实际 session、重序列化 observations JSON 并核 JSON 值相等、重写 manifest；逐原件 SHA 验证源包不变，其它目标原件不变。随后执行当前维护 `p01_interleaved_specializations.py` 从 `root = ...` 开始的完整 post-finalize AST，不执行 device setup/launch/finalize，保留十 capture、无 pending/owner/failure、两 binary、raw SHA、complete canonical、多正 site、ns export、单 session/十 invocation 和 64 MiB 整包检查。所包 test 字节与当前源码一致。该结果的十调用数学事实来自原已完成记录，未重新测数学；raw/trace/其余原件 SHA 不变。

因此可关闭这次编码/空白变更的有限验证缺口，并接受上述 **retained-only** Asc 体积恢复证据；不能将原 terminal 1 改记为成功，也不能声称 cf0ee96 已有新设备整轮 E01 重跑。没有因此新增测试或产品运行要求。

本次有限 closure 未发现新的具体产品缺陷。结论仅覆盖原 M1、legacy/公共读点与所述无损存储变化；原 whole/P03/ordinary 边界缺口仍保留，不授 whole-goal 签字。
