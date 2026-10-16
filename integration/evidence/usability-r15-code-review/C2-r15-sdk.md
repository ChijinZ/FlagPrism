# C2 r15 — Ascend SDK scalar tiling legality 工程代码走查

2026-10-16；静态阶段，等待 source freeze / 实际构建重放后的有限 delta。

最新受审状态见文末补充 delta 3：已核 fixed 实际 CPU 构建、安装收据、五个 pass 输出和公开 Bind IR；设备与正式资格验收仍未在本报告完成。下文保留各阶段原始判断与证据边界。

本次只读检查工程源、公开 probe 的既有 IR/receipt 和构建脚本；未运行本机测试、SDK 编译、NPU 或 GPU，未读取私有资格数学、IR 或 PRIVATE archive，未修改产品/论文，未派生 agent。本报告本身是请求的审查产物。

## 当前判断

最小 legality patch 未发现已确认的新增 blocker/major 语义缺陷。它正确拒绝任一带 `tile_and_slice_failure` 的 `hivm::StoreOp`，不会让成功 tiled sibling 掩盖失败的普通 store；失败 attempt 丢弃 clone、回到原函数的已有 store election。fallback 成功后的 `continue` 与失败后的 `signalPassFailure(); return;` 位置正确，分别继续后续函数和终止失败 pass。

这只是源码审查结论。隔离工具首次构建的实际终态是**链接失败**，并非 ready；未审到可执行未改 legality baseline replay、fixed changed-TU receipt、fixed public actor IR 或设备验收。原正式 44 项的 42 pass / 2 State fail 仍 open，公开 probe 也不能替代它。

## 已确认问题与工程边界

| 项目 | 分级 | 证据和影响 | 建议 |
| --- | --- | --- | --- |
| 首次隔离 build 未产生工具 | 当前交付阻断，非已确认产品源码缺陷 | Root 补充的实际终态：`build-133-compile-unmodified.log` 最后 `bishengir-opt` link 缺少 `mlir::tensor::reshape_utils::collapseAndReplace<CollapseShapeOp>(PatternRewriter&, CollapseShapeOp, Type, Value, Operation*)`；controller 抛 `RuntimeError`，两个目标 binary 均 absent。本 reviewer 未读取该远端原始 log，按 root 已核实信息记录。 | 单独保留 link failure、修复来源和最终 build identity。若需要 compatibility patch，不能称为完全未修改 exact 源码或 SDK bit-identical rebuild。必须重新建立用于 legality 对照的兼容 baseline。 |
| 文档的全新 prefix bootstrap 入口会立即失败 | Minor，可静态确定 | `bootstrap_sources.py:62–64` 只为 `PREFIX/downloads`、`PREFIX/source` 调用 `mkdir()`，没有创建 `PREFIX`；README:13 的新 prefix 调用在 prefix 不存在时先得到 `FileNotFoundError`。 | 创建 prefix 本身，或明确要求先创建一个空 prefix；继续拒绝已有下载目录以避免覆盖半成品。 |
| baseline gate 的 source → executable 链还可加强 | Minor，身份检查缺口；不说明现有 replay 无效 | `rebuild_fixed.py:54–59` 检查 build state、baseline matched/byteequal 和 baseline compiler hash 等于磁盘工具，但未同时核对 `build-receipt.json` 已记录的 `compiler_sha256`。这样一个替换过且重新 replay 的工具仍可通过该 gate，尽管不再与那份 build receipt 的工具身份相等。 | 把三个 hash 显式相等写入 gate/receipt。root 另外核对实际构建工具与重放 hash 也可覆盖当前交付，但脚本合同本身宜补全。 |
| codegen/resource 身份尚未由 recipe 完整收据化 | 交付证据待补；不作为已确认运行错误 | `replay_public.py:31–50` 记录 resolved compiler/hash 和完整 argv，但 libdevice 只有路径，继承环境没有记录实际 external `hivmc`/`bisheng` realpath/hash，工具相邻 `../lib` 的模板/resource 集也未形成 manifest。`build_unmodified.py` 明确 `BISHENGIR_BUILD_TEMPLATE=OFF`，不能由 C++ build 成功推出 resource 合同已成立。 | 在批准 Docker 的实际 replay/交付 receipt 中保留上述依赖身份及采用的明确资源合同。缺资源造成的失败应原样保留；不要调 flags 凑 baseline 字节。 |

未把尚未出现的构建结果、潜在别名或未覆盖 effect 自动列作安全 bug。

## fallback 语义核查

审查依据是归档的 exact428 `public-sdk428ab8-TileAndBindSubBlock.cpp`，SHA256 `c33d6effd6a128a16126a4ee1f1c511754d1b045157133a664baa63607ad4d11`，不是较新的 LLVM22 parent 版本。

- `:729–742`：原来的普通 failure 分支可以留下 `isFailed=false`；新分支无条件置 true 并 interrupt，因此不依赖 store 顺序，不存在后续成功 store 再覆盖 true 的路径。atomic failure 的原判定结果保持相同。
- `:764–809`：attempt 在 clone 上创建整个 AIV body 的 subblock loop；失败时删除 clone。新检查不会把已部分切分的 clone 当作 fallback 原函数。
- `:539–609`：exact fallback 只匹配 `hivm::StoreOp`，对每个 store 就地创建 `subblock == 0` 的 `scf.if`；不是 guard 整个 body。无 result store 复制进 then；有 result store 的 else yield 原 dst。这不是跨 AIV 值广播合同，也不能推广成任意 effect 的完整 election。
- `:880–930`：预先收集 `FuncOp` 列表；成功 clone 替换当前 original，fallback 成功保留当前 original。新 `continue` 不会引用已删除 clone，也不跳过下一函数。失败 fallback 后立即 return，不会继续把失败 module 当作成功输出。

公开真实 Before 中 AIV 只有 arg6 output 与 arg7 State 两个 `hivm.hir.store`；State load → add → insert → store 是闭合末端链，后接 return，无 store result / iterarg / caller 通道。AIV 的 workspace load 和 `sync_block_wait` 在链之前；AIC 的 fixpipe + `sync_block_set` 在另一函数。因而保留原 body、只 elect 两个终端 store 的静态行为与这份公开 scope 相符；把整 AIV body 包进 guard 会改变 sync 参与者，当前 patch 没有这样做。

原 fallback 不覆盖 call、Copy、IndirectStore、裸 `memref.store` 等通道，也没有为 escaping scalar value 提供传播证明。这是 exact428 的已有边界；本次公开 actual Before 未显示这些通道，不能据此虚构当前修复错误，也不能将该 patch 宣称为任意 AIV effect 的通用合法性证明。更广的输入要按实际 post-lowering effects 另审。

## 测试与构建 recipe 的有效性

目前脚本有五个公开 MLIR fixture；`check_pass.py` 计划 unmodified 跑四个、fixed 跑五个。未执行或审到运行结果。

| fixture | 能检查的变化 | 限制 |
| --- | --- | --- |
| `store_legality.mlir` | tileable output + terminal scalar RMW；保留 load/add/insert/store SSA，fixed 两个 store 都走 election | 结构 fixture 不包含真实 AIC/AIV wait 通道 |
| `unaligned_store.mlir` | 普通 63 元素 tensor failure，证明检查不是 State/rank0/shape1 特判 | 不证明任意 alias/effect 合法 |
| `multi_function.mlir` | 首函数 fallback 后仍处理第二个 tileable 函数，直接针对 `return` → `continue` | 未造 fallback rewriter 本身失败的输入；该失败分支当前可静态审查 |
| `tileable_store.mlir` | 保留正常两 subblock tiling，避免全局强制唯一 writer | 仅一个正向规模 |
| `conditional_store.mlir` | fixed fallback 仍保留原条件和闭合 RMW SSA | 仅 fixed 执行；文本存在性检查不独立证明 guard ancestry |

checker 的 guard 数量、`map_for_to_forall` 数量和 SSA 正则是有用的回归信号，但不是跨 actor 语义证明。特别是 `"scf.if %arg3" in output` 只证明文本仍存在，不能单独证明两层 if 的嵌套关系。当前静态 rewrite 是就地替换 store，提供了这点的源码依据；实际 fixed IR 仍应检查 store 所在原 branch/loop、subblock-zero guard 及 wait 是否留在 guard 外。未因缺少完整 parser assertion 将当前 patch 判为 major。

source pins、官方 LLVM patchset manifest、命令/PID/log、失败退出、baseline 字节比较的设计合理。`rebuild_fixed.py:64–149` 会识别唯一真实 TU object、保存 Ninja compile commands/deps、比较所有 object hashes，要求目标 object 改变，安装到独立 fixed prefix，确认未改工具未被覆盖且 fixed executable 不同。这能支撑“实际 changed-TU 增量重建”的表述；成功前不支撑已重建宣称。dependency parser 会忽略不再存在的条目，因而发生变化时仍需人工检查 before/after 完整集合，不能仅凭 reused count 判所有依赖不变。

## 当前检查快照与后续有限 delta

工作树 `FlagPrism-ascend-scalar-legality`，branch `fix/ascend-scalar-tiling-legality`；本次读取时 source 尚未 freeze，patch 未跟踪。关键 SHA256：

```text
sdk-scalar-tiling-legality.patch 7ce7f7c116b9beade493b6473337e73cedff230a62b1b180d26d6f591e30a4db
bootstrap_sources.py           227f6e68611e78ba3c4d8f4c101cd07120cd0257422b568c221e4fd193aeef53
build_unmodified.py            1b1edd989107fa3bc9cf350e1052447c61f87bc82dc9d4c761b3e9426b88d21f
replay_public.py               93e7338dc91637e8be3024c1f0a883d41f8913f8183e8cef66f67eef3fcd89ba
rebuild_fixed.py               bec99d71f9c7b73ca77d58d230f63e337ae94c67af921ff48dda50cf7079c5dc
check_pass.py                  98eea489bbf3480f85281220b9141228d60c351c60d6a53a22bd2a278ef50c34
```

root 已核的旧 SDK ordinary public archive `a0154653…e7ac21` 证明输入 `6b910a15…6a76b3f` 的原 SDK baseline/custom-print/MLIR-print 最终 NPUBIN 均为 4576B、`05b54efe…fe6b6e` 且 byteequal。custom-print 无 IR；实际 MLIR Before/After 是独立有效证据。这里采用其限定结论，未把它算作新隔离工具的重放结果。

收到新的冻结材料后只需审受影响差异：独立 compatibility patch 及 link 修复来历；新未改 legality baseline 与旧 ordinary bytes/IR；legality patch 的实际 source/object/dependency/link/install hashes；fixed 五 fixture 的真实 stdout/receipt；fixed ordinary 与 profile 的 compiler identity、actor IR 和所有 store guard；最终授权设备结果。安装、编译和测试仍只能在批准远端 Docker 发生。GPU 本轮禁止，不会以等待 GPU 作为任何行动前提或完成证据。

## 补充 delta 1 — explicit-template build compatibility

Root 已独立定位首次 link 缺口，并批准在原有 Expand 显式实例化旁增加 Collapse 的同签名显式实例化。本 reviewer 已读新增 `sdk-build-explicit-collapse-instantiation.patch`（SHA256 `4c6e07d319ed7b75c9a7d6ec718b8151c8abb0a5640c1e6eac360a6b17321d64`）及归档 `public-sdk428ab8-PropagateReshape-Utils.cpp`：

- `:179–184` 的五参函数模板 body 定义在 cpp；`:239–241` 只显式实例化 Expand。新声明与模板的 `PatternRewriter &, CollapseShapeOp, Type, Value, Operation *` 参数和 void 返回类型完全一致，位置也在定义之后。
- `:187–191` 现有四参 Collapse wrapper 使用同一五参模板，不提供新的算法实现。Release 可将该处隐式实例化调用 inline，而不输出供另一 TU 链接的外部定义；root 报告的 actual library 只有 Collapse `U`、Expand `W` 与此相符。
- 新增显式实例化强制输出已有模板的 Collapse specialization；没有改 reassociation、shape、insertion point、replace-use 逻辑或 LLVM patchset。源码层面是针对缺失链接符号的适当最小修复，未见新增语义问题。

尚未独立读到原 header、`PropagateCollapseDown.cpp` 五参跨 TU 调用和 actual nm/link log；也未读到新增 compat recipe，因此本段不提前声称 build 已成功。后续需把这些与 actual changed-TU/object/symbol/link/reuse receipt 一并归档。新 baseline 应称 **exact428 + explicit-template buildcompat / legality-unmodified**；首次纯公开 pins build 的失败继续保留，不能覆盖成 ready，也不能因该可修链接缺口就永久判交付不可行。

## 补充 delta 2 — compatibility、resource baseline 与 gate 独立红绿

本节追加后续证据，不覆盖上面的原始静态状态。Root 单独授权本 reviewer 在现有远端 Docker 的新目录 `/tmp/chijin-r15-c2-sdk-review` 运行固定公开 gate 正反例；未编译用户输入、未执行 SDK compiler 或设备代码，没有本机测试、NPU/GPU、SDK BC/lib/executable 内容复制或私有资格材料。

### compatibility 与资源身份已闭合的部分

已读 `sdk428-resource-baseline/compat-source-before/` 中 exact header、五参 caller 和模板 body。`Utils.h:99` 的模板声明、`PropagateCollapseDown.cpp:425` 的五参 Collapse 调用与补充 delta 1 的显式实例化签名一致。原 link failure 同时列出两个工具未定义的同一五参 specialization。`build-compat-receipt.json` 的实际 compile/install/version 均 returncode 0；只有 `Utils.cpp.o` hash 改变，2618 个 object 复用，CMakeCache hash 不变，legality TU 仍为原 `c33d6eff…`。新安装工具 SHA256 为 `7edd1aa8b4d9cad6a55355997af7d5969d2c277664a9477ca08555e51c7e3822`。

`resume_template_compat.py` 保留原失败 receipt、原 source/caller/header、符号命令、deps 和 object manifests；只允许对应的缺失模板符号失败进入该路径，并要求只改变预期 Utils object。未改算法或官方 LLVM patchset。当前本地安全包没有完整 nm 输出正文，已读其真实命令/退出收据与实际 link 成功，不把命令收据称为已亲读 nm 全文。

`templates-receipt.json` 记录官方公开模板 source manifest、现有 `ccec`/`llvm-link` realpath/hash、官方 configure 生成模板与独立 prefix 安装；五份资源齐全。其 compile 阶段 0 个 object 改变、2619 个复用，新旧 compiler hash 仍是同一个 `7edd…`。`complete_templates.py` 使用官方 CMake template options，并验证五份非空输出；没有从 system SDK 复制私有模板 BC。既有首次 missing-BC 与 resource-complete `binary_mismatch` receipt 保持原失败含义。

资源完整的 replay 实际观察到 `hivmc`、`bisheng`、linker/host 流程，保留工具和 libdevice/公开模板资源 hash；前述“recipe 未记录 external/resource 身份”的交付证据缺口在这份具体 baseline 中已有实际收据覆盖。采样观察的范围仍按其 receipt 表述，不能提升为完整系统依赖追踪。

### 对精确 baseline 例外的独立字节审计

本 reviewer 另用独立的只读结构/哈希读取核对归档 public ELF，没有运行产品 comparator：

| 检查 | 结果 |
| --- | --- |
| 新/旧 public NPUBIN | 均 4576B；新 `5bdc6ab47c5456d8e6d7c7a1f1ab2a56132bc0d20e251ebed5995548dbb3357b`，旧 `05b54efee3ed790bc6c76b40110e92b2f7684d2761605bea6f1dfa31c1fe6b6e` |
| 实际差异 | 85 bytes；全部位于 `.comment` union `[1640,1837)` 与它自己的 `sh_size` `[4352,4360)` |
| 装载与 ABI 内容 | ELF header、全部 program headers、所有其余 section headers/content 相等；唯一 PT_LOAD 文件区间 `[176,1616)` 与 `.comment` 不相交 |
| Bind 前后 IR | 新 Before `0b1f6b3241e15b95dfbcfa74b7d4dcc0166eca74c02a94928b89ea1b6dc66c2f`、After `03c4eddd74753f6bcdda5a403e1db4417d201c20d5abb1c20729198a4f3cbe0e`；逐字节等于原 SDK 对应 IR |

`.comment` flags 为 48，不含 SHF_ALLOC；新 size 194、旧 197。`producer-source.json` 记录公开新生成模板包含的 producer 串来自当前 `ccec` dated version，不是改写旧 binary 或读取/修改 SDK 私有 BC。这些证据支持**本次 public CPU baseline 的 producer-only 等价**，不支持 bitidentical SDK rebuild、设备正确性或正式 State 失败已消除。

Root 明确的授权边界是：通用 comparator 可以接受严格的非 ALLOC `.comment` payload / 自身 size 差异类；不能忽略其他 metadata、执行/ABI 内容或 layout。本轮 execution seal 必须另外绑定已审 `5bdc…` candidate。任意 ASCII comment 改写仍通过严格通用 comparator 是该合同允许的行为，不是数学 bug。

### C2-R15-01：assert 关闭使 baseline gate fail-open；已在限定修复边界关闭

新引入的 vulnerable `compare_public_elf.py` 与 `accept_public_baseline.py` 用 `assert` 执行关键拒绝条件，Python `-O` / `PYTHONOPTIMIZE` 会去除检查。这是已确认的 **Major acceptance-gate 缺陷**，不是推测的 device/math 故障。已保留旧 source 和独立 red。

固定来源与实际执行源码 SHA256：

```text
vulnerable archive      3516b9ab64cfb2d323780796974dc72931a2375dffaac061fbbc73f65508d2d2
vulnerable comparator   83f660c928db41a09a97b58d12a63a709077804c64aa00c484925d220514368b
vulnerable acceptance   d8e0faa96b5092f9efbf1cd9898b6ff66b813cc470f36fa3c8ebc73c0fafaf72
hardened archive        056756bca8516e54f4e50d9b3622aaf32e21263111b648951fc9c95cae7b7687
hardened comparator    653a8fda34d05054a8a7b2010cc39b715a00caa9df5dd06a191df3ca147b29bc
hardened acceptance    bc79e0d6037a1c46a0a8049d8b43158dd9eeba3bcb12d24fe18a0932cf975be7
delivery validator     dbae8224f08ef8f906e642613f00a2892bd1576879a1fa8b746c093efb5b43cf
```

独立 Docker 单轮共 58 个 subprocess case，整体 exit 0，全部符合预先固定的期望。每次都保留 actual argv、退出码、stdout/stderr SHA 与正文：

- 旧版 `-O` 误接受 9 个负例：comparator 的 text / PT_LOAD metadata / ELF header / `.comment` ALLOC 变异，以及 acceptance 的 text / input / output-hash / tool-hash / Bind-IR 身份误配。普通模式均拒绝对应变异。
- 修复版把条件改为显式 `if` / `RuntimeError`。普通和 `-O` 均拒绝全部 26 个负例：上述 comparator/acceptance 变异，加 source / build-compiler / template manifest / actual external manifest 身份误配。
- 修复版两个模式的 comparator、acceptance、delivery 三个真实有效基线检查均通过，共 6 个正例。另两个 `.comment` payload-only scope probe 合法通过，未将其算作误接受。

因此 C2-R15-01 在上述三份已执行冻结模块的边界关闭，原 red 和 Major 历史不删。未执行整个 rebuild 脚本、native pass 或设备验收，不能把这 58 个 gate case 当作这些任务的结果。

### accept → rebuild 身份合同的后续源码核对

`validate_delivery.py` 实际重新读取 build/compiler/replay 三者 hash、原 source archives、legality 与 compat source、完整五模板的 generated/installed/replay 三者身份、公开 template source manifest、实际 external tool/resource 文件 hash；不是只检查 `state=true`。上述独立负例验证了对应拒绝行为，初始报告的 build-tool 三者身份缺口在该 validator 中关闭。

后续 `rebuild_fixed.py` SHA256 `666cf0c914eff2c936c484609889f9397980edafdb1637000a312e0410176e85` **仅做源码审查**；本轮 red/green archive 中冻结的较早 `12632886…` 没有执行，不冒充同版本复现。新差异有两点：用 canonical JSON 比较 derived receipt，消除序列化 tuple/list 的假不等并避免 bool/int 宽松相等；producer-only 分支强制 `--execution-seal`，八项实际 hash（candidate/input/reference/compiler/derived receipt/build receipt/templates receipt/source）必须与 seal 完整 canonical 相等。derived 又重算 strict ELF/IR 并绑定 replay receipt hash，delivery 重读资源，因而 seal 可把本轮已审 candidate 与其实际 manifests 串起来。未发现这一源码合同有已确认 hash 替换或 only-bool 绕过。

尚待实际 fixed build receipt/argv/seal、changed TileAndBind TU 与最终工具 hashes，才能确认上述新 rebuild 版本和本轮 execution seal 实际执行；legality pass 五 fixture、fixed public actor IR 和最终授权设备结论仍按各自真实证据验收，不外推当前 gate 结果。

独立附件：

- `C2-r15-sdk-gate-review.py`：remote runner，SHA256 `cacaa2aa6f2c09ab2ae3dae39df85ae2e99eba46cdd00b791d2d6a32803828c7`。
- `C2-r15-sdk-gate-review.sh`：带不可变 source packages 的 remote bootstrap，SHA256 `ec055c490d1261029314e66dd5c639b1f4f1802aa39a640b2dabd253dba1dcd8`。
- `C2-r15-sdk-gate-review.log`：实际输出与 58 项完整 argv/exit/hash，SHA256 `c97b183b32b2b4f171b274b868ad82bd5090a294311b8bbbdd4f8fec4786a66e`。
- `C2-r15-sdk-gate-review-freeze.tgz`：原脚本、冻结源码、public binary/IR、所有结果与源身份 fixture，SHA256 `7485c8e3dd68c6d2c7a26c7da9ed58939a3ebb0d19140926e8b5156142ae0c2a`；独立 inventory 2728 members / 1834 regular files / 10 指向既有安装的 symlink，**0 SDK BC/lib/executable regular files**，不跟随这些 symlink。
- `C2-r15-sdk-gate-review-freeze-audit.json`：归档 inventory 与结果审计。

执行命令：

```sh
python scripts/study_remote.py zhiyuan_ascend \
  --command 'sudo -n -u chijin docker exec -i chijin_v3.5.x bash -s' \
  --stdin-file artifacts/usability/run-013/final-code-review/C2-r15-sdk-gate-review.sh \
  --stdout-file artifacts/usability/run-013/final-code-review/C2-r15-sdk-gate-review.log \
  --timeout 90
```

## 补充 delta 3 — fixed 实际 TU、安装、pass 与公开 CPU actor IR

只读核对 `state-failure-forensics/sdk428-fixed-cpu/` 及原始公开 baseline；没有运行新编译、checker、SDK/NPU/GPU 或本机测试。证据 archive SHA256 `4a9da10348c74fb3ec069b515030a0989eae17705ed2d3fadf2920c66184e055` 与 root 指定值相符，共 46 members，无 SDK BC/lib/executable regular files。独立清点和哈希核对结果保存为 `C2-r15-fixed-cpu-audit.json`。

**本次新增证据范围内未发现 confirmed blocker/major。** 最小 legality 修复已进入实际编译的 TU 与新独立安装工具，并由真实公开编译和 pass 输出观察到预期 fallback。此结论仍不等于硬件、ordinary/profile 全路径、strict public 12 项或原 44 项正式资格验收通过。

### source → object → link → install 的实际链

原 `c33d6eff…` 与归档 fixed source `5370a0df12b9f1216dc935888e843376c61391aa96c8a2864132cec30a6d434c` 的完整 diff 只有已审最小 patch 两处：所有 failed StoreOp 强制 fallback，以及 fallback 成功继续 / 失败立即终止。patch SHA256 仍为 `7ce7f7c116b9beade493b6473337e73cedff230a62b1b180d26d6f591e30a4db`，无 State/helper/shape 特判、atomic 算法或全局 barrier 改动。

实际 `fixed-compile.log` 是四步：编译 `TileAndBindSubBlock.cpp.o` → 链接 `libBiShengIRHIVMTransforms.a` → 链接 `bishengir-compile` → 链接 `bishengir-opt`，returncode 0。独立核对完整 before/after manifests：

- 两侧 object 集合完全相同，共 2619 个；恰一个目标 object 从 `d8f70c6b…` 变为 `88a53f9a…`，另 2618 个 hash 不变。
- 两侧 dependency 集合完全相同，共 756 项；恰该 source hash 改变，另 755 项不变。没有以仅统计 reused count 掩盖新增/删除依赖。
- 两份 actual Ninja commands 日志逐字节相等，SHA256 均 `3a8756c5a9b6291bc64005267237ae83ea3caf68f689179dcb1eabc39fb42653`；末条实际目标命令使用 `/usr/bin/g++ -O3 -DNDEBUG`，输入是隔离 exact source 中的目标 TU。整个 command 日志包含其生成依赖命令，不能误称这些都在本次重新执行；四步 compile log 才是实际重建列表。

`fixed-build-receipt.json` controller PID 1985860 的 recipe SHA256 正是已源码审查的 `666cf0c914eff2c936c484609889f9397980edafdb1637000a312e0410176e85`；archive 内 recipe 字节与之相符。执行使用的 validator 为 `dbae8224…`，属于补充 delta 2 已执行独立红绿的冻结版本；后来 clean-entry 改动不冒本次覆盖。

receipt 中 execution seal、其文件 SHA、derived receipt SHA、原 compat build/templates receipt SHA 与归档实际文件一致；封闭的是已审 `5bdc…` candidate / `6b910…` input / `05b54…` reference / `7edd…` baseline tool，不是任意新 candidate。实际安装命令含独立 `--prefix …/install-fixed`，returncode 0，`--version` returncode 0。fixed compiler SHA256：

```text
1f5cc5054402e901add18af133b3495b861775d68e2113bb8ba94667eef6cf9e
```

这同时是后续 public CPU replay 的 selected compiler hash；baseline 安装 hash `7edd…` 保留。五份 fixed prefix 公开模板的 hash 与 resource-complete baseline、fixed build receipt 及 fixed replay 三份 manifest 逐项一致。真实 observed `hivmc` / `bisheng` / linker identity 与 baseline 相同，实际 argv 指向 fixed prefix 的公开模板路径；未把 SDK executable/BC 内容复制到本地证明工具运行。

### 四个 baseline 与五个 fixed pass 的实际输出

已亲读 fixed 五份 stdout，以及针对旧错误的 baseline `store_legality`、`multi_function` stdout；其余 baseline 由 receipt/hash 核对。全部实际命令为对应安装的 `bishengir-opt <fixture> --hivm-bind-sub-block --verify-each`，四个 baseline / 五个 fixed returncode 均为 0、stderr 均为 0B。fixture 当前公开源字节与每个 actual input hash 相同，所有 stdout 与 receipt hash 相同。

| case | 实际观察 |
| --- | --- |
| `tileable_store` | fixed 仍有 0..2 mapped loop，每个 subblock store 8 元素，保留正向两 subblock 切分 |
| `store_legality` | 旧输出把 terminal scalar RMW 留在 mapped loop 内、无 election；fixed 保留 load/add/insert，两个原规模 store 各有 SUB0 guard，取消整个函数 mapped loop |
| `unaligned_store` | fixed 64/63 两个完整普通 store 均 election，无 mapped loop；覆盖非 State / 非 shape1 的普通 failure |
| `multi_function` | 旧 first fallback 后 second 保持未处理；fixed first 仍 fallback，second 确实变为 0..2 mapped loop、32 元素 partition，直接观察到继续处理后续函数 |
| `conditional_store` | 原 `scf.if %arg3` 包围 scalar load/add/insert 与其内层 SUB0 store guard；output 的 SUB0 guard 位于原条件之前。源 branch 层次真实保留，已补足仅字符串存在性断言的局限 |

baseline opt hash `c388432da3154bb9f195fd83b60649d3184482a2ebf1d3de4208477d54240bdc`；fixed opt hash `fa2ee876fd4b2172b1399fe4b316b92230a5aba4b2c04c7f041cafd8fadb6cce`。早期 verifier-invalid fixture 没有被当作这些成功结果；本表对应归档 v4/fixed 的真实 input hashes。

### actual public Bind IR 的 guard 支配与 effects

fixed public replay 的输入 hash 仍为冻结 `6b910a15…`，其 Before Bind 与 legality-unmodified / 原 SDK Before **逐字节相同**，SHA256 `0b1f6b3241e15b95dfbcfa74b7d4dcc0166eca74c02a94928b89ea1b6dc66c2f`。After 为 `ea9f95969639a81a3e321a5b5065f4ecf28f6f06cf4a1ba9bc08c9ee2916e7ea`。已逐行核对实际 After，而非仅采信 receipt 的四个 verified booleans：

- AIV `:88` 的 `sync_block_wait` 在函数主块中；workspace load 和原 tensor vector ops 随后执行。它在两个 store guard 之前，且不位于 guard 内。
- `:102–104` 定义 `get_sub_block_idx → index_cast → cmpi eq 0` 的 `%29`，`:105` 的 `scf.if %29` 直接包含 `:106` 的完整二维 output store；`:107` 关闭 guard。原 mask 的动态 slice `%14` 和原 output offset 仍保留，没有切成每 subblock 的半片输出。
- `:109–113` 仍是原 arg7/BLOCK-derived offset 的 `memref.load → addi 1 → tensor.insert`。`:114–116` 定义第二个独立 SUB0 条件 `%36`，`:117` 的 if 直接包含 `:118` 使用该 `%inserted` 的 terminal State store，`:119` 关闭，`:120` return。没有用常量/旧 dst 代替 RMW 值，没有新 IV 依赖或 escaping scalar 结果。
- AIV 没有 mapped loop、call、Copy、IndirectStore、裸 `memref.store`、AIV fixpipe 写 workspace/L1 或跨 actor SSA 通道；本公开 scope 的两个外部可见 StoreOp 都在各自 guard 内。原 FFTS/mask 设置、wait 和计算留在 guard 外。
- AIC function body 的 Before/After 文本逐字节相同；原 fixpipe → `sync_block_set` 未改。不能将本 fallback 简称“整个 AIV 只运行一次”：非零 subblock 仍执行原读取/局部计算，唯两个终端 store 被 election；这一点正是已审公开闭合链所需的边界。

因而在**这份实际公开 Before/After** 中，可以确认 guard 支配实际两个 store，且没有把同步参与者包进新 guard。未将该观察扩大成任意未知 effect / alias / escaping value 的通用 fallback 证明。

fixed driver 的自然 CPU compile returncode 0，最终 NPUBIN 为 4528B、SHA256 `d5e366436832b147c619d65a467442a23e33a7bb0a49e27a4ebcfc27ce9169c3`，本 reviewer 已从归档 bytes 重算一致；与 buggy 4576B baseline 不同是实际 repair 输出，不走 producer-only 等价例外。stderr 的 libdevice data-layout、target-triple、linker warnings 原样保留；未增加凑相同字节的 codegen flags。

实际源码 TU / deps / build / install / five pass / public compiler IR 的这批待证项在上述具体材料边界已闭合。clean checkout entry/docs、普通与 profile 安装后硬件路径、strict public 12 项及原正式 44 项的 State/math 门继续分别验收；本 reviewer 没有设备 lease，也没有作硬件通过宣称。

## 补充 delta 4 — 公开 strict12 最终硬件证据补审

本节是最新的限定结论，追加补充 delta 3 之后到达的硬件材料；不改变原阶段结论或历史失败。仅阅读归档公开源、12 项原始 result/receipt、编译元数据、actor LLVM、terminal/cleanup 与 hash；未重跑构建、CPU 测试或设备任务，未读任何 PRIVATE 数学/IR，未修改 canonical `cb968eb8d1891bd1ec6ad2574e070747a0f80986` 或工程代码。

**这份公开 strict12 的实际硬件回归通过；本次有限补审未发现新增 confirmed blocker/major。私有原资格矩阵及其两项历史 State 失败仍需独立原源验收，不能由 public pass 关闭。**

材料为 `state-failure-forensics/r15-strict-preparation/strict-evidence/` 及指定终态记录。独立重算 `public-state-strict-evidence.tgz` SHA256 为 `67781c88999fdcb4420d538f1195a090b177c03bbaf43e3bc69c10ebaf1539e7`；270 个 indexed files 的实际 bytes/hash 全部相符，archive 共 271 regular files，未发现 PRIVATE 或 SDK BC/library/executable 内容。

### 原始 12 项结果与原判据

逐项读取 12 份原始 `output/result.json`、`receipt.json`、`host-ledger.json`、plan/source。公开源每项均为原冻结 `b09827d6f088e3b1d6484e8a3dbd8b341ce467e6eb6821164028dee2e49b774e`；2-program grid、BM16/BM32、scalar/vector/atomic、ordinary/default(detail auto) 组合完整，无 skip/retry/warmup/timeout。probe 源仍保持原数学和 State 更新，不因修复改 oracle；额外只读 `strict_state_gate.py` 对原结果完整 values 数组要求 `type(value) is int and value == 1`，不采信 `equals_one_observation` 单一 bool 或把 bool/float 当整数。

| 配置 / State | ordinary 原始 State | default 原始 State |
| --- | --- | --- |
| BM16 scalar | 2 项，均整数 1 | 2 项，均整数 1 |
| BM32 scalar | 2 项，均整数 1 | 2 项，均整数 1 |
| BM16 vector | 1024 项，均整数 1 | 1024 项，均整数 1 |
| BM32 vector | 2048 项，均整数 1 | 2048 项，均整数 1 |
| BM16 atomic | 2 项，均整数 1 | 2 项，均整数 1 |
| BM32 atomic | 2 项，均整数 1 | 2 项，均整数 1 |

12 项各自 ledger 与 result 一致，`attempted=1, returned=1, synchronized=true`。96 个原 checks 全为 pass：math（原 `rtol=2e-3, atol=2e-4`）、三个输入严格不变、output 左右 canary 和 State 左右 canary 严格不变。所有 result 均 `diagnostic_completed`、errors[]；receipt 均 exit0、terminal_confirmed=true，timed_out / variant_compile_unsupported / device_fault_detected 均 false，interrupted[]、cleanup[]、remaining_descendants{}。因此没有以 unsupported、终止动作或异常同步后的设备读取伪装自然成功。

probe 源内 State 仍写“diagnostic observation”；本轮严格 State==1 是独立 gate 对这些原始结果附加的确切通过要求。它不把 State 值单独提升为未审 helper 内部物理 writer 数的通用证明。

### 已安装 parent → 实际 fixed SDK → 最终 binary 的一致性

preparation、summary 与 pins 记录实际新环境为 source `a829a3312af69c1b961919025053829d7096a2b1`、wheel SHA256 `bbd3ff08a15f2cb174be3d63d527540935f2811d8a0356772d7749a85b1a7a14`。最终 launch 绑定 root-approved seal `a10392fe518b3be04f505d6c31c19878803d3521c03cb169d710de2999e90f7b`；旧 pending seal `bb534…` 原样保留，未被当作已批准对象。`LAUNCH_REQUEST.json` 的显式 selector 和 PATH prefix 均为 fixed prefix；进程以隔离模式启动，并清除继承 patch hooks。

12 份**实际 compiled metadata** 的 `ascend_compiler_identity` 都是：

```text
/tmp/chijin-r15-sdk-scalar-legality/install-fixed/bin/bishengir-compile
1f5cc5054402e901add18af133b3495b861775d68e2113bb8ba94667eef6cf9e
```

本 reviewer 只对 metadata AST 的 literal identity 字段解码，未 eval 全部 repr 或导入产品。六份 default 的 actual handoff、SDK capture receipt 和 command[0] 也都指向该工具：phase/state finished、实际 returncode 与 sdk_process_returncode 均为整数 0；`sdk_tool_sha256`、metadata 与 handoff identity 相同。六份 driver 的 source IR hash 等于归档实际 `bcmlir.txt`，其 final-output hash、exported binary hash 与实际保留 NPUBIN bytes 三者相同，四份 actor 原始/适配 LLVM 的 retained hashes 逐项相符。

seal 中 fixed-build 与 CPU gate receipt hashes 均等于补充 delta 3 已审归档文件；五模板与新环境 libdevice hash 延续同一合同，新旧 venv libdevice 均为 `9142883f…`。因此这里不是仅将期望 compiler path 写进 report：普通实际 metadata、profile 实际 SDK driver、已审 source/TU/CPU fix 与最终运行 binary 有对应收据。BM16 scalar ordinary 的实际最终 binary 还是补充 delta 3 的 `d5e36643…`，直接连到已审 public CPU actor IR；profile binary 含观察代码，未宣称 ordinary/profile 二进制相同。

### 公开生成代码抽样与同步边界

抽样亲读 BM16/BM32 scalar default 的 actual SDK-original 与 adapted AIV LLVM，及实际 GraphSyncSolver dump。BM16 原 AIV `633b3786…` 中 `GET.SUBBLOCKID()==0` 的 `%45` 控制 output helper block46 和 State helper block55；State 从 formal7 的 GM load 经 add1/UB 值进入 terminal store helper。适配 AIV `16d34d9b…` 仍由 `%167` 控制 output block168 和 State block217；State formal7 与动态 trace formal8 分开，观察代码未移除两个产品 store 的 election。BM32 对应 original `347674b3…` / adapted `d580011e…` 也保留 SUB0 产品 store 分支。

实际 scalar GraphSync dump 中 AIV workspace `sync_block_wait` 分别在 BM16:134 / BM32:133，两个 `limit_sub_block_id0` store if 随后出现；没有将整个同步 body 包进 guard。原/适配 LLVM 的相关 WAIT.FLAG 同样先于产品 store 条件分支。BM16 ordinary/default 的公开参数区间抽样也相互不重叠。以上与补充 delta 3 的普通 fallback 行为一致，不是“只给 profile 使用修复”。

抽样不宣称已证明全部 launcher→formal 的隐藏 trace 实际地址链、helper 内部所有物理写或任意输入的跨 actor 合法性；本源保留的 pointer-chain 限定仍适用，未据此虚构本次失败。

### 自然终态与释放

`suite-exit.json`、`root-terminal-actual.txt` 和 observation009 相符：controller / strict-State gate / actual-identity gate / suite 均 exit0。12 cell 都是自然终态且 cleanup[]；最终 summary 为 `finite_table_finished`、completed12、skipped[]、remaining_descendants{}。release receipt 核对 14 owned PIDs / 13 groups，owned_live0、rows[]、zombies[]；observation009 记录 suite PID2004238 和 controller PID2004273 均已不存在。root 已回收本轮 NPU4 lease，本 reviewer 没有追加实时设备访问。

因此公开 strict12 的 State、host-once、math/input/canary、实际 compiler/driver 和自然 terminal/cleanup 证据在这次冻结材料边界闭合。它是 **public hardware regression 12/12**，不是私有原资格全矩阵通过，也不替代后续独立 qualifier 的原源结果。
