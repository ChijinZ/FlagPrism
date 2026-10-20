# R092 native-image component — finite runtime review

审阅绑定冻结 `c03fb877be742f2ce2b75c752c6bc2ea30027210`，开始审阅时工作树干净。随后共享候选 HEAD 前移；本报告仍以 `c03fb87` 文件及 V5 收据为准，不授予后续变更资格。请求配置 GPT-6.1-Sol / xhigh；实际 resolved 配置未暴露，记 unknown。只读源码、Git 和既有收据；未执行产品、import、测试、checker、SDK、设备或远端命令，未读取其它席结论。仅写本报告。

## 结论

已确认一项内部组件的预算缺陷 M1：V5 限制了符号表条目总字节数，但逐符号查找/解码名字仍可反复处理大量相同或重叠的字符串。没有发现本范围内其它 confirmed blocker / major，未发现两份实际输入的 byte-binding 结果错误或被提升成 source/reader 资格。

V5 的 60 normal / 60 optimized、格式化 AST 及两个实际对象的正向结果有效，足以支持这些对象的有限绑定；不能据此关闭 M1 的异常输入预算。此 helper 尚未接 default/offline，不涉及已交付 capture 的 ABI、raw、clock 或 owner 生命周期变更。原 whole 适用链不在本次复审范围。

## Confirmed M1 — 符号名字处理未受 aggregate symbol-table budget 约束（minor）

**位置。** `Debugger/python/flagtree_debugger/gcu_native_image.py:38–40,105–113`。`sum(s[5] ... SHT_SYMTAB) <= len(binary)` 限制条目数量；每条随后都执行 `strings.find(NUL, index)`、名字 slice 和 UTF-8 decode。名字长度及这些重复处理的累计量没有计费。共享一个字符串表的多个符号表还会重复复制该表。

**触发与静态证据。** 在现有测试 `fixture()` 的 ELF 骨架上保持 executable bytes、descriptor 和正确 kernel 符号不变，把符号表扩大为约 4 MiB，并追加一个约 4 MiB 的合法 ASCII 非 kernel 名字，让约 174000 个其它符号引用这个名字。更新两个 section 的 offset / size 后整个 ELF 约 8 MiB，仍小于 16 MiB admission；条目总字节数小于文件大小，正确 kernel 符号也仍唯一。这些条目在 111–113 行会扫描并 slice/decode 约 **0.7 TB** 名字数据，然后才能返回正常绑定。让这些名字引用同一长字符串的不同后缀，同样可以造成这一放大，单纯按 offset 缓存不足以一般解决。这里的处理量是由循环静态推得，未执行该反例，也不声称已测得具体超时。

**后果与分级。** 小于允许文件上限的 retained metadata 可以把内部检查耗时放大至远超输入规模；未来 provider 的 unknown/optional 路径也可能因此长时间占用 CPU。当前尚未接公开路径，也未观察到实际原件触发，所以按当前交付范围列 minor，不把它描述成设备或数学故障。README 中“aggregate symbol-table traversal”对条目遍历本身成立，不能推导成所有 symbol lookup 工作量已受该字节预算约束。

**最小修复/验证。** 对字符串表复制与名字扫描/解码累计工作设置有限预算，超限显式拒绝；或者一次性建立有界字符串表索引，避免逐条反复扫描长后缀。无需通用 ELF/ISA 平台。增加一个重复名字或不同后缀引用的小 CPU fixture，以确定性预算拒绝为断言；无需无期限大输入 benchmark、SDK 或设备。现有 `symbol_budget` fixture 只把 `sh_size` 改为文件两倍，覆盖的是第 38–40 行 admission，不能覆盖本问题。

## 已读实现及其它检查

实际读取完整 `gcu_native_image.py`（139 行）与 `test_gcu_native_image.py`（104 行），以及 evidence 中 `image_actual_runner.py`。产品 SHA256 `d2502c3eede953a48a5fc27fffebb0772798ac1e14b839709e50d3c68c4a26b5`，测试 SHA256 `c275634a18c796a603c5f0bf2a477096e9bcfc8c61b73d16f828c61769daf979`，与 `image-source-freeze.json` 和 V5 返回源码一致。

字节和范围检查的正向链合理：ELF/native 各至多 16 MiB；section table 至多 8192 项，表和实际读取 section 均检查文件边界；只接受一个非空 executable PROGBITS section。解码行必须 PC 单调、原始 bytes 非空且至多 16 字节、不重叠、在 executable 范围内并与 ELF 相等；总指令至多 100000。唯一 descriptor 的 entry/length 必须唯一、正且 packet 对齐，并与同名 ELF 符号的地址、总长及 section index 一致。descriptor 区不允许被指令覆盖，其余未覆盖的 executable bytes 必须全零。

SDK 函数可以位于同一 executable section 的 kernel 范围之外：它们也受逐条 byte-binding 和最终覆盖检查，但只计入 `other_decoded_instruction_count`；返回 `instructions` 按 descriptor/symbol 的 kernel code 范围过滤。该选择没有要求不存在其它 SDK 函数，也未把它们算成 application kernel body。新增正例针对这一点，实际 V3 原拒绝保留、V4/V5 修正范围的陈述与源码一致。

该组件显式消费 **trusted SDK disassembly**。它绑定该输入中的 raw instruction bytes 和范围，不独立从 ELF bytes 解码 ISA，也不能发现一个人为伪造但 raw bytes 不变的 mnemonic。这个 caller 前提在当前声明中明确；本报告不将独立 ISA decoder 追加为交付门。未知 source/clock/control、reader value flow 等没有因为 byte-binding 成功而被授予资格。

## V5 直接证据及范围

实际读取候选 evidence `timeline-gcu-auto-tails-r092/` 的 README、image freeze/index、`v5-terminal.json`、`v5-output__{normal,optimized}.log`、format/result JSON 和 image runner。V5 为 terminal / returncode 0，2.869233883 秒；normal 60 passed、optimized 60 passed，优化模式 warning 保留。两轮 Ruff/YAPF/check-AST 为 0，runner 比较四个源码/测试文件格式化前后的 AST。

测试数由原 relative-reader/tail 的 46 项及 image 的 14 项组成。image 包含 byte-binding / descriptor 正例、同 section 额外 SDK 指令正例，以及 wrong/missing bytes、重复/重叠 PC、错误 entry/symbol、section 外指令、截断 section、坏 symbol offset/table、重复 descriptor 和 symbol-table admission 等 12 个负例。M1 的长名字累计处理不在这些负例内。

实际 runner 对两个 retained loaded ELF/native 先核原 SHA，独立复用旧 QA 的逐指令 bytes、executable 覆盖和 descriptor/symbol 检查，再要求新组件返回的 kernel instruction list 与旧列表完全相等：

| ELF SHA256 | native SHA256 | 有限结果 |
|---|---|---|
| `7d56f25f70633d7f0d813a78e8ded073b884a4356d940a4cb48c710794f00500` | `a4423a389544cde04466ad381de272754c8c79d3860eabc48dd86898a9015e8b` | 新/旧 body 相等，auto relative tail 1/11 |
| `5860432eef0a3004e35740a68b17b10bd9f33d49bf3ab7a30f8cb11be72131f6` | `3e15c05637ef8ab999165d5496ebe07e7dff1967aa648828437c65038c063935` | 新/旧 body 相等，auto relative tail 0/12 |

V5 明确 `product_native_image_binding=true`，但 `default_capture_integrated=false`、`source_loop_qualified=false`、device / SDK recompile / application replay 均 false；两份实际原件仍为 1/23 相对 tail 通过，其余具体 unknown。没有把 CPU synthetic fixtures 当实际设备证据，也没有以此授予 reader/source 完整资格。

## Verification gaps 与 optional

必要补项只有 M1 的有限修复和相应 CPU 预算反例；没有根据本 delta 提出新设备/math/TP/UI 矩阵或通用 ELF/ISA 要求。正常安装、public provider 接入和完整 source/loop 适用性均未在本增量承诺中，保留原范围，不冒充完成。

本次不另列 optional 工程要求。没有重审旧 whole、其它 backend 或未冻结实现。

## V6 有限复核追加：名字扫描子项已闭，M1 尚有原已列复制残留

本追加绑定冻结 `7f208ca484ce79aaba078d1b73a402f846ed989e`（核读时工作树干净）。产品 SHA `9e71998ce150b7c568885c12b28608fe65650a3de3c9f6f2c0d03b2a36a76001`、测试 SHA `7d0503d1c9ab525903147516fb41dcb1e43f427bc6e231b9f55e9837146292a1`，均核同 V6 source freeze / 返回源码。只读取本 M1 的代码 diff、fixture 与直接收据，未执行产品或测试。

逐名字处理的修复成立：所有 symbol table 共享 `2 * len(binary)` 的 `name_budget`；每次 `find` 的搜索上界先由剩余预算限定，成功后按包括 NUL 的 span 扣费，不再逐符号 UTF-8 decode。后续名字 slice / bytes 比较的长度也受这些已扣 span 约束。预算为零时至多再搜索一个字节便拒绝；没有先完成任意长扫描再检查限额。129 个符号、128 个不同长后缀 offset 的新 fixture 使原放大路径显式报预算错误，不只验证重复同一 offset 的缓存。

实际读取 V6 terminal、normal / optimized 原日志、format/result 和 source freeze。terminal returncode 0，2.869578943 秒，61 normal / 61 optimized；两轮格式/AST 检查通过，优化 warning 保留；image helper SHA 精确对应本冻结。runner 仍对同两份实际 loaded ELF/native 要求产品 body 等于独立旧 QA body，原 1/23 relative tail 和所有未授资格字段保持。完整 receipts archive SHA 核同 `929f64a2fe89727882a0caeea3f2b0e2c51c569c6e6136eacf31988143d39ad9`。这些收据足以关闭 **长名字 NUL scan / 名字 slice / 重复 decode 子项**。

M1 原报告明确包含的“共享字符串表被重复复制”尚未关闭：`strings = data(sections[section[6]])` 仍在每个 SHT_SYMTAB 内执行，`data()` 对关联表作完整 bytes slice，这个复制量不计入 `name_budget`。例如约 8188 个各 24 B 的小 symtab 共用 8 MiB strtab，大部分符号只引用 offset 0 空名，另保留一个正确 kernel symbol。section table、这些条目与字符串表合计约 9 MiB，条目总字节约 196 KiB、名字累计扫描仅数 KiB，仍可重复复制约 64 GiB。此结构符合当前各项 admission；这里只作静态量推导，没有执行反例。

这是原 M1 复制预算的残留，不是新增 whole/ISA 门。最少补项是缓存相同字符串表的 materialized bytes，并对实际需要 materialize 的表累计 bytes 设上限，或直接在复制前限制关联字符串表总复制量；增加共享表的一个小 CPU 预算反例即可。故 V6 目前可判扫描子项已闭，**M1 整项仍为 minor / 未全闭**。其它有限正向结论与原未承诺范围保持，不要求数学、设备或旧矩阵重跑。
