# C1 独立代码走查：通用编译与观测

审查日期：2026-10-16。审查者任务：`/root/final_sol61_c1_compiler`。请求配置由 root 保存的工具调用记录确认；本报告不根据模型自述推断实际模型版本。

## 结论及版本

在下述实际阅读和抽样范围内，未确认新的 compiler/runtime blocker 或 major；确认 **1 项 minor 文档语义缺陷 C1-M1**。这不是“三后端资格验收全部通过”的结论：安全冻结索引的 `overall_qualification_pass` 为 false，Ascend 原 eligible profile 的 state 断言失败仍未解释，本报告不关闭它。

- 产品工作树：`FlagPrism-usability-r10`，实际 `git rev-parse HEAD` 为 **`0f6e1da62d6b789c9742e526d6bfc95274b8b649`**；读取时工作树无本地改动。
- 已安装运行包源版本：`ce00df63828c5e657c0307d7b69c99706dc12d49`。实际 `git diff --name-only ce00df6 HEAD` 为 11 个 tests/docs 文件，无 runtime/native 变更。
- native 输入：`1f914a8b03bc3fe4fe73c1be49f22b91babdc6a5`。对本席涉及的 Debugger C++/include、Profiler C++/Dialect/LLVM、cmake/python 构建输入做了该提交到 HEAD 的文件差异检查，无变化。
- 资格证据只读取 `qualification-final-safe-v3/` 的三份 `*-safe-aggregate.json`、`state-helper-ciface-scope.json` 和 `index.json`；其中冻结提交为 `8975cd9` / `916674b`。

只进行静态代码阅读、Git 只读命令及 Python 标准库对已存公开 JSON/tar/raw bytes 的离线检查。未导入产品模块，未运行测试/编译/数学 oracle，未连接设备，未安装依赖；仅新增本报告。

## 已确认问题

### C1-M1 — minor：Ascend 安装文档把当前自动默认模式描述为旧 checkpoint 事件流

- 位置：`FlagPrism-usability-r10/integration/patches/ascend/README.md:126`（段落至 136 行）。
- 触发：用户按该安装文档理解普通 `--detail auto` 的数据语义。
- 预期：当前默认为前端选择的 source-site census v2；输出是每个 program/actor/site 的 visit count，clock、occurrence、iteration、start/end 均不可得。旧 late-LLVM checkpoint/interval 模式应标为显式高级模式或历史实现。
- 实际：该段仍称 “Automatic Ascend observations include zero-interval … checkpoints”，称默认按每个 actor 的 source location/class 选八个区域，并提到 loop-header checkpoints 与 actor-local clocks。这与冻结代码及当前公共 census 文档不符。
- 依据：`Profiler/python/flagtree_profiler/profile.py:1416` 的 `_automatic_observation_request` 为 `counter/all_grid_census`；`Debugger/python/flagtree_debugger/compiler.py:270` 的 census 分支选择实际前端 op 并准备 v2 ABI；`Profiler/llvm/AscendLateObserver.cpp:515` 按实际 marker 写 count；`Profiler/python/flagtree_profiler/source_census.py` 产生 null timing/occurrence/iteration。公开 mixed 包实际记录同样为 `source_site_census_v1` 的 counter，而非 checkpoint occurrence 流。
- 建议：将 126–136 行改为当前 census 说明；旧段若需保留，明确加“显式高级 checkpoint 模式/历史实现”限定，并链接 `Profiler/docs/source_site_census.md`。
- 建议验证：静态核对该段与 `Profiler/docs/automatic.md`、`source_site_census.md` 及既有公开 mixed bundle 的 semantic/storage/timing 字段一致即可；本项不需要重新跑设备或构建 native。

已在审查中单独通知 root；报告定位以本节的实际 `nl -ba` 行号为准。

## 代码审查及实际证据

### 公共入口、自动请求及一次执行链

实际读取 `Profiler/docs/automatic.md`、`source_site_census.md`、根 README 和三后端安装 README；代码读取 `cli.py` 的参数/设备/执行/finalize/supervise 路径、`_capture.py` 全文、`profile.py` 的自动路由、request、start 及相关 instrumentation 激活/收尾段。默认自动路径向受支持后端发出 all-grid census，外部 counters/replay 是另外的显式路径；所读默认路径不存在为发现 site 再执行一次用户 kernel 的调用。

CLI 的应用执行和导出有明确边界，导出失败保留 stage。`_capture.py` 在写成功 manifest/清理 stage 前调用 `require_automatic_records`；记录为空或缺 invocation 的自动模式不能只靠 native collection 成功出具完整结果。此为所读路径的代码结论，不是对任意第三方 launcher/SDK 的无重放证明。

### 自动选点与通用结构

- **NVIDIA**：完整读取 `Profiler/Dialect/lib/ProtonToProtonGPU/AutomaticScopes.cpp`。候选按真实操作 dialect、纯度、tensor/control 属性和真实 region ancestry 决定，排除 combiner 内部与 pointer/layout bookkeeping。选择先保留有限入口控制位置，再取循环/分支 region 代表和 source statement/内部操作；预算在插入 `proton.record` 前应用。没有发现算子名、用户路径、特定 shape、固定 SSA/site/hash 的选点分支。
- **GCU/Ascend 前端**：完整读取 `Debugger/python/flagtree_debugger/automatic_plan.py`、`gcu_census.py`；读取 `compiler.py` 的 compile-options、前端 metadata/inline、census ABI 和 instrumentation 全部相关分支。`Metadata/Passes.cpp:1252` 附近实际赋 op ID、识别 public entry、从 SSA 追 condition producer，并记录真实 region/block/control ancestry。planner 不靠 ID 区间或源行邻近推断控制流。helper 先 inline 后赋实际选择身份；synthetic metadata 不进入设备 site。
- **实际写入**：读取 `Debugger/lib/Instrumentation/Passes.cpp:3050` 的 GCU census writer，以及 4265–4543 的选择/存在性检查和 hidden argument/cell-column 绑定；NVIDIA `ProtonToProtonGPUPass.cpp` 的 census lowering 和 `PatternProtonGPUOpToLLVM.cpp` 的单 writer 计数转换。device 工作受选点预算约束，后续默认 program 选择仅影响展示。

定向搜索上述产品 Python/C++、Ascend late observer 和 census 模块中的名称、shape、site、hash 条件。实际出现的名称条件为通用 IR 类别、官方 SDK intrinsic/target、版本/格式 guard 或身份摘要；未发现逐算子适配。此结论限于已读/已搜索模块，不能当作对全仓所有后端文件的穷尽证明。

### NVIDIA scope、源码位置与实际 binary

读取 `Profiler/Dialect/triton_proton.cc:29` 的结构化 `FileLineColLoc`/`NameLoc`/`CallSiteLoc`/`FusedLoc` 导出，以及 `get_scope_id_origins`、`get_automatic_proton_plan`。candidate ordinal 通过实际 scope name/allocator 解到 scope ID，不直接当设备 site。完整读取 `source_origins_nvidia.py` 和 `nvidia_census.py`；读取 `hooks/instrumentation.py` 的 allocator、activation、compile identity、binary registration、enter/exit/census export 主路径。

自动 inventory/policy/source-census/partition 版本与 max_sites 进入 instrumentation option；注册时读取当前已存 TTGIR 的 scope/计划、IR digest 和 compiler scratch metadata。descriptor 检查 actual grid、dense site IDs、actor geometry、scratch stride、实际 allocation 大小及容量预算。原始 capture 与同一 metadata object 的 launch scope/binary 关联；没有按名称或时间近邻补 ID 的分支。

### Ascend marker、typed ABI 与 late observer

完整读取 `Debugger/lib/Instrumentation/AscendProgramAnchor.cpp`、`Profiler/llvm/AscendSourceCensus.h`、`ascend_abi.py`、`ascend_census.py`、`ascend_compiler.py`；重点读取 `AscendLateObserver.cpp` 的 marker 解析、坐标支配关系、actor expression、instrumentActor、formal mapping 和 manifest producer 段（未逐行审阅旧高级 interval 的全部逻辑）。读取当前 `flagtree-source-census-v2.patch` 的 compiler/launch/cache/AutoBlockify 桥接及 `flir-source-census-v2.patch`。

前端要求 selected ID 唯一对应真实 operation，发出含 op ID、column、S 和六个 i64 program/grid SSA operands 的 sideeffect marker。AutoBlockify 桥按真实重写坐标运送 marker。late pass 检查 marker 版本、六参数类型、column 绑定、def-use 支配关系；每个 marker 用自己的坐标计算线性 program，紧邻插入该列计数，不拿物理 BLOCK.IDX 替代 source program。

hidden pointer 映射来自实际 source formal 角色与编译器发出的 sync/workspace index，late pass 校验 FFTS 配置以及从首 formal 到最后 global pointer 的类型前缀。未知类型/错位显式报错；没有按已知 kernel 名猜 final pointer ordinal。trailing scalar/coordinate 的关系明确保持 partial。AIC 使用 bank 0，AIV 使用实际 SUBBLOCKID+1；Python 按 kind/slot/module/compile ID 绑定，而不按 artifact 列表顺序猜 actor。

`ascend_compiler.finish` 保留原始 SDK input、canonical/adapted LLVM、manifest、全部实际 codegen jobs 和最终 binary bytes；成功状态要求同一 enclosing SDK process group、compile ID 和实际最终输出 digest/字节数一致。decoder 的 SHA/manifest 校验只是此 producer 链的消费检查；本席另看了真实留存 LLVM，未把 metadata 自报作为唯一依据。

### specialization/cache

读取 Debugger `apply_compile_options` 和 GCU publication/options 冻结逻辑，以及 NVIDIA JIT patch 与 instrumentation wrapper。request、site/census/publisher/control metadata 版本进入编译身份。Ascend source patch 在普通及 spec JIT **内存 cache lookup 前** normalize effective `enable_auto_blockify`，并让实际 SDK argv 使用同一个 option；NPUOptions disk hash 包含 compiler driver key。late driver key 包含 plugin bytes 和相关 Python capture/ABI/census 源码 digest。

所读身份链未发现从另一 binary 搬 site 数字来补当前 binary。未验证进程运行中替换 plugin 文件或改变高级编译环境变量时所有上游内存 cache 的行为；安装环境/插件在会话中保持冻结的正常使用路径已有对应身份材料。本席没有为这一未覆盖场景推定缺陷。

### source/identity/reconstruction/report gate

完整读取 `source_capture.py`、`source_view.py`、`source_census.py`、`fine_grained.py` 的 normalize/plan/write/gate；读取 `reconstruction.py` 的关联与输出、`hooks/launch.py` 的 binary/source registration 和每次 launch metadata bridge。阅读 `execution.py` 及 `execution_enflame.py` 的 location/candidate 解析部分。

结构化 callee/caller/fused 候选保留角色，文本 MLIR location 的各真实 atom 保留为候选；source view 不按 basename 找文件。捕获快照 SHA 以及 binary/file/版本决定导航，行范围无效或多快照歧义会留下 diagnostic。快照/行范围检查不证明编译输入文本一致，代码、JSON 和页面均保留了该限制；JIT text 不猜文件偏移。

`require_automatic_records:459` 按 capture/invocation/binary 精确匹配，逐 launch 检查 missing capture；一个 kernel 的记录不能补另一个调用。census 要 source-linked、exact、nonzero primary，并检查展示外程序的 overflow。未执行、没有主 site、源位置失效、缺关联不会直接称完整成功。计数为 N 仍是一个 count=N 的 counter，不展开成 N 个合成 interval。

### 安装链的独立离线核对

读取 `install-audit/summary.json`、三份 small-index 包的 native-output/source-wheel-installed 索引、`callsite-packages/summary.json` 和 `notes.txt`；读取三后端 callsite 的 component-python/native-source/package-file/native 索引，及 `ascend-public-build/index.json` 的命令/退出码/native/install 摘要。代码阅读了 `python/flagprism_build.py`、`cmake/FlagPrism.cmake`、NVIDIA build shell 全文以及 Ascend/GCU source-build recipe 的输入/隔离/命令记录/冻结部分；没有逐行审核全部 wheel assembly 脚本。

本席用标准库对每后端 **68 个 component Python 文件**逐项重新计算当前冻结工作树 digest，与 source 和 package index 比较，全部一致；对每后端 **268 个 native source 输入**逐项重新计算本地 digest，全部一致；native index 与 package-file index 的 digest 逐项一致（NV216 / GCU63 / Asc107 条）。这核实索引间及冻结源码的对应，不能替代重新下载所有大 wheel 并验全部实物 bytes；原 source/stage/ZIP/installed 比对由保留的实际审计数据支撑。

Ascend public build 索引记录 clean clone/pin/apply/configure/build-core/build-observer/assemble/install/check-install 均退出 0，且实际核心、插件、工具/native 的摘要明确。没有把仅重打 wheel 解释为新增 native 从源码构建。

## 本席直接抽查的公开包与原始字节

没有打开私有资格 kernel 源码或 IR。直接抽查：

1. `nvidia-final/runtime-public-evidence.tgz` 中 **`chijin-r11-nvidia-runtime/ordinary-cli`**：读取 binaries/observations/fine_grained/selection 及其 TTGIR/LLVM。两 capture 各 128 raw bytes，raw SHA 均重算匹配；12 个对外 count 均与其 raw offset 的 u32 一致。一个 binary 的同 site 循环 count 为 3 和 7；真实 TTGIR 有自动 record，真实 LLVM 有对应 count/flags store。
2. `gcu-final/runtime-public-evidence.tgz` 中 **`chijin-r11-gcu-functional-r2/bundle-ordinary`**：读取同类 JSON 与其 TTGIR/LLVM。四 capture 各 6688 raw bytes，SHA 均重算匹配；32 个对外 count 与 raw u32 一致，重复 site 的运行时计数包括 2 和 5。保留的两个 binary 分离；TTGIR 有按真实 op ID 选的 thread-zero 条件和计数向量写入，LLVM 保留实际 thread query/store。
3. `public-hardware-regressions/ascend-mixed-public-evidence.tgz` 中 **`bundles/m13-n29-k19-auto0`**：读取 binary/observations/fine_grained/selection 及嵌入的真实 original/adapted LLVM、原 SDK input bytes/manifest。capture 为 224 bytes，16 个记录与 raw count 一致。两个不同 module 分别为 AIC/AIV；各有八个实际 v2 marker。original/adapted/raw-input digest 分别重算匹配；adapted LLVM 在每个实际 marker 前有 volatile count/flags load/store，并使用实际 hidden global pointer；最终 retained binary bytes digest 与 binaries.json 一致。没有把 artifact 顺序当 actor 依据。
4. `public-hardware-regressions/ascend-state-public-evidence.tgz`：只读公开 receipts/commands/result/root-terminal；记录 ordinary16 + profile16 的 state 观测以及 `original_qualification_failure_closed=false`、`state_equals_one_is_no_replay_proof=false`。没有把这次诊断变成原失败解释。

这些是有界抽查，不是对所有包/所有 site 的重新证明；未运行产品 decoder 来替代独立原始字节比较。

## 未解决风险及未覆盖范围

**R1：Ascend 原 state 断言失败仍未解释，资格验收不能给全部通过。** 安全聚合记录：原 24 baseline 中 23 eligible，46 次 profile 有 45 完整通过、1 次原 CLI 失败且无 receipt。安全 helper 摘要显示实际 wrapper 仅有 ciface 声明、未保留定义，writer uniqueness 尚未建立。三个 ordinary/两个 profile 的受控通过及 profile binary 相同，只能说明这些控制运行成功；公共 RMW 诊断的 state=1 同样不能排除原问题或证明无重放。本席不能从静态产品代码为缺失的原失败实际 state 值/receipt 补原因。应继续保留原失败和“不完整验收”状态；如 root 安排进一步验证，应优先补实际 writer election/ciface 最终定义与每调用 receipt，而不是只增加成功次数。

**typed ABI 的剩余范围**：所读 final-prefix guard 明确支持整数/index、f32/f64 和 global pointer；更窄/复合 scalar formal 不在本席实际公开硬件证据中。静态 guard 会拒绝未知类型，本席未证明匹配厂商 baseline 能运行 f16/bf16 等独立 scalar 参数，因此没有据此确认一项支持回退缺陷。如需要扩大 ABI 声明，建议服务器 Docker 用合法 annotated scalar 在 hidden pointer 前交错放置，与 ordinary baseline 成对核验；tensor 的 f16 元素并不覆盖该 scalar ABI 场景。

其他限制：未审阅 peer 报告、产品角色结论、历史审阅结论或 `method_impl_record.md` 意见；未读其他 qualification 树、独立 worker 私有源码/IR；未复查全部 SDK/LLVM optimizer/scheduler 正确性；未做 race/sanitizer、完整 native 生命周期/所有高级 interval/counter/vendor 后端审计；未穷尽上游 JIT cache；未对全部历史 bundle 做归档重验；未做论文或 novelty 判断。

本席新增代码缺陷结论为“未发现”，不应改写为“已证明不存在”。C1-M1 可用纯文档修正关闭；R1 需要真实缺失证据或原因处置，不能凭本报告或数学/诊断成功关闭。
