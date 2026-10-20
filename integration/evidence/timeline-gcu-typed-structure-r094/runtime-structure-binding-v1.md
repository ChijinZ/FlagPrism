# R094 typed LLVM structure binding — finite runtime review

绑定冻结 `90fe92853c3fe09c0abe6e1976f9c31fbc0aabe7`；开始核读时工作树干净。请求 GPT-6.1-Sol / xhigh，实际 resolved 配置 unknown。只读实现、Git 和直接收据；没有执行产品/import、测试、SDK、设备或远端，没有读取 peer。仅写本报告。三 family 规则尚未完成，本次不授 G1 或 native/source schedule 资格，不重开旧已闭门。

## 结论

普通 make_llir → SDK verifier 返回文本 → structure index → make_fatbin 附 binary 身份的正常路径，已在源码中接上。没有发现已核普通路径的 confirmed blocker/major/minor；新 mode 的 child 登记、输入快照/工具身份核验、有界异常 reap 和明确失败状态合理。typed index 与 wrapper 都保 source/native-schedule false。

有限必要缺项有两处：正常安装后的 binder/binary 交接直接证据仍 pending；既有 fabs fallback 是否使用另一个 codegen 输入，需要以当前实际 helper 原件核清，避免把 make_llir 输入误称为 fallback 的精确最终输入。后一项下文明确区分已读旧本地材料与尚未核实的当前事实，没有据旧文件直接判当前 confirmed bug。

## 已核普通路径与生命周期

实际读取新 `bind_execution_structure`、`_native_file_stage`、binary attach、maintained compiler patch、完整新 binding fixture，并为理解 schema 读取 `GcuExecutionStructure.cpp` / native CLI fixture。

- compiler patch 在实际 `toolkit.gcu_compiler_opt(scoped, '--mlir-print-debuginfo')` 返回后计算 `debug_execution_native_ir_sha256`，将同一个 `lowered` 字符串传给 binder，再返回给正常下游。不是索引 DI bridge 尚未经 SDK 验证的输出。
- binder 把不可变 string 编码成 bytes，先核 SHA 与上述字段完全相同才启动 native child。输出仅接受 exact schema/version/status 及 source/native-schedule false，随后保留 LLVM digest、原 native JSON digest、manifest digest、report 和 receipt。
- 新 mode 使用 `input.mlir` / `output.json`，receipt 的 `input_kind=LLVM_MLIR` 正确；入口 bytes/16 MiB、工具身份、源文件结束后相等检查沿已有 helper。Popen 后 PID 已在 receipt 中，`/proc` 和 launch 写入均在清理 try 内；异常 kill 当前 direct child，reap wait 至多3秒，未确认终态保 `termination_pending`。没有重新引入无 timeout 的 cleanup wait，也没有全局同步或无关 owner 操作。
- fatbin 阶段先取得真实 bundle/ELF 及原 native/location 分析，再检查 structure 的 LLVM digest 与当前 metadata 一致、manifest digest 一致，最后在新 wrapper 副本附实际 fatbin/ELF/target。旧 capture 没有 structure 时继续其原路径；未凭缺该新字段给 legacy 额外资格。
- 失败时子进程输入、输出、stderr/receipt 已在独立目录；metadata 的 structure 字段只在报告 admission 成功后赋值。当前实现是结构索引失败则编译明确失败，不是悄悄生成“已验证”替代品。没有数据证明支持 family 规则，因此不从 indexed 状态推出 body/loop 边界。

输入16 MiB、函数 block8192、operation100000、location长度/累计量和 native输出上限均存在。native service 允许 JSON 至32 MiB，而公共 helper 接受输出至16 MiB；因此集成实际按较小的16 MiB拒绝，不能宣传32 MiB结果都可经公开编译路径留存。该差异是保守 admission，不构成本次已观察误放；不要求为此扩大原预算。

## 直接证据与必要验证 V1

已读 root `structure-receipts-v3/runs/structure-v3/{terminal.json,output/result.json,output/cli-fixtures-*.log}` 及 runner：terminal0，21.598509792秒；真实新 standalone tool SHA `65029c34e39a3524aa41b0d37b3c5750f7585418173dc378a98e454586b1a7cb`。normal / optimized 各6个实际 native CLI fixture，包括 typed SSA/loop/marker、wrapper caller、无定义/多 body/嵌套 region 和输入预算拒绝。

两份旧 actual LLVM 输入均由新工具实际索引：`6b8b2e1a…b593` 为93 blocks /1603 ops /46 markers /87 calls；`acdeadcb…68e7` 为84 /1754 /48 /105，source false。它们是实际 retained SDK LLVM 正例；CPU synthetic fixture 不冒实际设备证据。这里证明新的数据源可处理这两个真实对象，没有证明 caller/body/tuple 的三类规则已经成立。

另已读 binding-format-v1 terminal/result：terminal0，1.868033292秒；两轮 Ruff/YAPF/check-AST 全0并核 AST/返回源码一致。bridge SHA `005a00b47f4f5735462bb339163f3d534f06fc104e2a4cf546428313d460310c`，binding test SHA `9a9302708eb2319107394b130377fb4cbc09dac96096256f808b429ebee12432`。

当前 binding fixture 覆盖正确 LLVM/manifest、启动前错 LLVM、错误 schema/source/native 权限和 ordinary 不调用；还没有直接覆盖附 fatbin 阶段的成功及 stale manifest/LLVM 拒绝。正常 wheel 正在安装，不能用 native CLI6项或 formatter 代替 installed binder 的行为证据。

**最少补证：** 正常 wheel/source/tool 核同后，用已有两 actual LLVM 和其原 fatbin 在新的 installed 环境走 `bind_execution_structure` + binary attach，核摘要/target/receipt和false资格；再把结构建立后改 manifest 或 LLVM digest 的一个小 CPU negative 放在同一交接，明确拒绝且原输入不变。无需为数据源接入重跑旧数学/State/SQL/UI或新设备矩阵。三 family 的验证不计入本次通过数。

## 必要身份边界 V2：核清 fabs fallback 的实际输入

maintained patch 保留 `make_fatbin` 的 `_compile_with_debugger_fabs(mod, ...)` 分支，但本轮新增索引只在 make_llir 的正常 `lowered` 上建立。需要确认该分支后续实际编译的 bytes 与索引输入之间的关系。

本次实际读取了既有本地 `artifacts/method-run/enflame/FlagTree-patch/third_party/enflame/backend/compiler.py:383–410`。**该历史文件**中的 helper 移除旧 target、加入 compatibility library，经 `toolkit.gcu_compiler_opt(unattached, '--gcu-attach-target=...')` 生成 `linked`，随后 `toolkit.compile(linked, ...)`；它没有返回/保存 linked 的摘要。若当前实际安装的 add842 baseline 保持这个实现，就会出现“structure digest 指旧 mod、binary 实际由 linked 编译”的精确输入身份缺口。callee/body 可能保持相同，仍不能据此把两个完整输入摘要说成一致。

该历史目录不是当前 freeze 的 backend 原件，本次尝试本地 Git 取 add842 源失败（目录不是 Git repo）；所以**不把这一历史实现自动当作当前 confirmed bug**。已向 root 点名请求当前 helper 的只读源码范围。最小所需读取就是该函数及其 make_fatbin 调用，不需要服务器执行、编译或设备。

若当前确实使用另一个 linked 输入，最少处理是在实际 linked SDK 输出处更新摘要/重新建立 structure，再附其 binary；或者明确保留该后续变换及其 application-body-preserving 检查，将结构收据精确限定为 pre-link body index，另绑定 actual codegen input。无需改兼容数学实现或新建通用证明器。未触发 fallback 的已核正常路径不受这个问题影响。

## 停止范围

没有本次新增的 whole、任意 ISA、全 CFG、逐算子人工批准或时钟/State/pipeline重验要求。索引的 schema/data-source 成功本身不授 caller/body/loop 资格；下一步只接原 R094 三类有限规则与 required coverage join。本次结论先保持上述两项有限验证/身份边界 pending，等直接材料到再作相应 closure。

## c057552：V2 当前源码修复的有限追加

本次仅核原 V2 fallback 身份及对应 fixture，绑定 `c0575528418292c65eeccab4bd105b68bd000225`。runtime 产品冻结；核读时只有 `p01_enflame_native_locations.py` 测试文件另有工作树变更。没有执行代码/SDK/设备，没有读取 peer 或复审 native 数据源的其它修改。

已实际读取权威 `run-094/preflight/fabs-source-current-v1.log`。该收据直接读当前实际 R087 installed backend 的 helper，确认确实生成 `linked` 并编译它；此前 V2 的历史本地线索现有当前源码印证。故原 V2 可确认为 fallback 精确输入身份的 minor，而不是未知硬件/数学故障。

**修复源码对应原缺口。** maintained patch 让 `_compile_with_debugger_fabs` 在成功编译后返回实际 `linked`；fallback caller 保原 pre-fallback SHA，保留 linked 的实际 codegen IR 与 transform 名称，更新 `debug_execution_native_ir_sha256`，记录实际 compatibility library bytes 的 SHA，并在附 binary 身份前重新调用同一 `bind_execution_structure(linked, metadata)`。原 make_llir 结构收据因此被本次实际输入的收据替代；正常未触发 fallback 的路径没有新增 relink 或重索引。compatibility 数学实现未因本修复改变。

新增 `test_gcu_fallback_structure.py` 从正常安装 backend 文件的 AST 只抽取这两个真实函数，分别走正常/已知 fabs linker-failure 路径；SDK compile / attach 显式模拟，断言发送给 compile 的输入、binary attach 前的更新摘要、重索引使用 linked、原 SHA/compat SHA 和 retained codegen IR。它测试真实 installed patch 的交接逻辑，不是字符串搜索 patch，也不是设备/SDK 数学成功证据。AST 载入的 helper 需要的分支被有意限制在该 fixture 的 GCU300 情况，未据此声称其它架构已受测。

另外已读 location-binding 新增的三个 case：正确 IR/manifest 附精确 fatbin/ELF/target、结构建立后 stale IR 拒绝、manifest 改动拒绝；保原 index 对象不改。它们正好补原 V1 点名的 binary attach 测试范围，不增加新验收门。

源码 SHA 核同：maintained patch `eef7078915dea296a5bde6b6265f123db71e79e98603637c3815963df0ad90c9`；fallback 测试 `571e70689ae2961805a188da9bbb7ad8ab5ff831c643f8160adaa1e4620fe632`；location-binding 测试 `0e3e7f873c96cee7296e65065c8165707700a86aceb73f778e8fa2563e3bd11a`。binding-format-v2 terminal0，1.867335353秒，五个 Python 源/测试的格式与 AST 核同收据已读。该格式任务不是新 fixture 的行为测试。

已读 native structure-v4 的直接 terminal/result/log：terminal0，21.549156127秒，新 tool `a2937f0de72fd2b7f2e031804ab6025a5fe1ba512db46f58e771f796a4d367b9`，9 normal /9 optimized native CLI fixture，同两 actual LLVM 输入成功、计数及 source false 保持。它证明数据源的新构建正例，不代替 installed backend AST fixture 或默认 Python binder 的执行。

**当前有限状态：V2 源码已修，installed 执行验证仍 pending；V1 正常安装/binder closure 继续 pending。** 本次未见该 fallback 修复引入的具体新问题。待 normal-install-v2 真实受测收据到，只需核 source/tool/wheel 对应和上述 targeted fixture、实际 retained-input 交接即可闭合；不扩三 family、whole 或新设备/数学矩阵。

## R094 installed 最终追加：V1 / V2 已闭

本追加仍绑定 runtime `c0575528418292c65eeccab4bd105b68bd000225`。实际读取 root `installed-structure-receipts-v1` 的 index、normal-install-v2 和 public-structure-v1 的 terminal/result/测试日志及相关安装检查；读取当前未提交 smoke/doc diff 与 smoke formatter/输入 tar 的原字节。没有执行产品、测试、SDK、设备或远端，不重开其它已闭门。

**V1 安装与绑定验证已闭。** normal-install-v2 terminal0，55.446909023秒，source commit 精确对应本冻结；wheel SHA `87a34857607a8c54e0467f573f6b85d664e10b9743d56ee508bce04898c3f0d0`。assembler 检查131个 component Python 文件与 wheel 字节相等，installer 检查502个 installed members 与 wheel相等，新 standalone tool 为已核 actual-v4 的 `a2937f0de72fd2b7f2e031804ab6025a5fe1ba512db46f58e771f796a4d367b9`。安装流程有各 native 输入与 actual-v4 build source 的逐字节 guard，不能用旧 tool 冒充；其余 core/runtime 沿原核同输入复用。

normal / optimized 各117 passed，优化 warning 保留；六个定向文件包含原四文件、新 structure binding 和 fallback AST 测试。三个 attach case 实际覆盖正常 fatbin/ELF/target、stale IR 和变更 manifest 拒绝；两例 installed backend AST 测试覆盖普通与已知 fabs error 分支。另9个真实 native CLI fixture 在 normal / optimized 下分别通过。它们补齐原 CLI-only / formatter-only 的不足。

**V2 fallback 身份修复的 installed 执行验证已闭。** AST fixture 从此次正常安装的实际 backend 取两函数，在模拟 SDK 调用中确认 `linked` 是传给 codegen、用于更新摘要及重新建结构的同一文本，并保 pre-fallback/compat 摘要。该结果证明 patch 真正进入安装后的函数及所修交接分支；不声称此次发生了真实 SDK fabs linker failure 或新的设备 fallback 数学实测。原兼容数学实现没有被本修复改动，不要求为身份交接重跑旧矩阵。

**实际公开路径也已到。** public-structure-v1 terminal0，23.047613809秒，使用新安装环境。ordinary2/profile2 的数学、input、tail/guard、host-once 通过；两 capture 分别22/20 events、各两个 observer，native location points为48/62。新 smoke 断言结构 LLVM 摘要等于 metadata 的 actual-input SHA及所保 actual codegen IR（无 fallback 时为 llir）摘要，且结构 fatbin/ELF 与 capture 原 executable 相等；typed index 状态正确、source false。输出仍 `final_machine_boundary_qualified=false`。

受测 input tar 中 `run.py` SHA `174ddbe02521febc641aaa8d2eddc64b23f7c1d49e894da75b7d44f167969d1b` 核同 actual terminal；其 `smoke.py`、formatter 返回文件及当前 `p01_enflame_native_locations.py` 均精确为 `1a7b930ef6345464d15892979538730e78af0451270e5258eecf36f5560f74d6`。因此不是格式化后另有未受测字节。formatter 的 YAPF/check-AST 通过，Ruff 明确保留 no-files skipped，不冒其执行了该文件检查。

已实际核同 index 中两份 terminal / 两份 result：安装 `8ff08fb6…c112` / `8e452b77…981f`，public `2f762c81…cd35` / `0ae71101…1a5b`。早前 normal-install-v1 的输入传输问题未改称安装成功；当前通过由这份有权威 terminal 的 v2 承担。

当前 runtime doc 只解释 typed 数据字段、actual fallback reindex、tool identity v3 及不授 source/native schedule 的边界，与已读实现一致。本报告不代替其它席对 native index 内部规则的判断。

**最终有限结论：本席 R094 原 V1 / V2 均已闭，无该交接 delta 继续必需的补项。** typed 数据源和编译/binary 身份链已实际接入；三 family 和 current96 required coverage join 仍属于下一步，未授 source/loop/native schedule 或 whole 资格。没有新增旧数学/SQL/UI矩阵要求。
