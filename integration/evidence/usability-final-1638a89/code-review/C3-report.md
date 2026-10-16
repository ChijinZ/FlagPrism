# C3 independent code review — public service and delivery

审查时间：2026-10-16。结论对应冻结源码 `FlagPrism-usability-r10` commit `0f6e1da62d6b789c9742e526d6bfc95274b8b649`；开始时 `git status --short` 为空。发现 **1 项 confirmed major、1 项 confirmed minor；未发现其他可证实 blocker**。这不是整体产品验收通过意见：安全资格摘要仍有一个 Ascend eligible profile 的真实状态断言失败，未解释。

本席是用户追加的独立 C3 代码走查。请求配置为 `gpt-6.1-sol / xhigh / fork_turns=none`；实际可确认的工具配置由 root 保存，本报告不凭自述认定模型版本。只读本席模板、产品合同、冻结公开代码/文档和指定已存证据；未读 peer 报告、产品席结论、method_impl_record 意见、私有资格数学或 IR。未连接服务器/设备、运行测试、pip 安装、调用产品模块或修改产品/论文/Study/原证据。仅用 Git/文本查看和独立的 JSON/tar/hash 读取脚本检查已存公开数据，并写本报告。

## 已证实问题

### C3-MAJOR-01：Ascend counters 忽略显式禁止重放的策略

**位置**：`Profiler/python/flagtree_profiler/_backends.py:23–35`，调用入口 `cli.py:129–131`、`_capture.py:242–266`，实际命令生成 `cann.py:97–104,122–128`。

**触发**：匹配的 Ascend 安装中执行以下高级计数器命令（输出目录须新建）：

```sh
flagtree-profiler --backend cann --counters --replay-mode none -n fresh-output app.py
```

也影响同时指定 `--detail auto` 的该组合。CLI 未指定 `--replay-mode` 时默认也是 `none`。

**预期**：请求 `none` 时不能启用 SDK kernel replay；若此后端只提供 independent replay，应在启动应用/外部工具前报明确错误，要求用户显式选择 `independent`。

**实际/依据**：`_ascend_counters` 接受 `none` 和 `independent`，但随后无条件调用 `collect_msprof(... replay_mode="independent")`。`collect_msprof` 本身在 103–104 行正确拒绝非 independent 值；包装层使这道检查失效。122 行固定生成 `msprof op ... --replay-mode=kernel`，128 行的 receipt 也将策略记为 independent。调用链不依赖某个 kernel 或 SDK 返回内容，因此接受/改写策略本身已由静态源码确定。这里没有声称已观察到某次具体重放次数或数值破坏；风险是用户的显式 no-replay 选择被忽略，状态型 kernel 的实际执行语义可能改变。`--counters` 是选择额外计数，不足以取消同一命令明确给出的 `--replay-mode none`。

默认不带 `--counters` 的基本命令不经过此分支；此发现也不能解释原 Ascend 默认资格状态失败。

**最小修复/验证建议**：只允许 `replay_mode == "independent"`，并给出 `--replay-mode independent` 及副作用说明。由 root 在服务器 Docker 做 CPU 回归：通过已注册的 `capture_backend("cann").collect_counters` 调用，stub 掉 `cann.collect_msprof`，断言 `none`（包括 CLI 默认）在 stub/外部进程/应用被调用前失败，`independent` 原样透传；对 unsupported `application` 保持拒绝。现有 `Profiler/test/test_cann_importer.py:45–50` 检查的是直接 collector 的拒绝，未覆盖包装层。无需为了验证策略拒绝在设备上运行 stateful kernel。

### C3-MINOR-01：公共安装索引给出过时的 Ascend 补丁叠加顺序

**位置**：`integration/patches/README.md:39–42`；正确的对应合同在 `integration/patches/ascend/README.md:3–14` 和 `integration/patches/ascend/build_from_source.py:18–26`。

**触发**：用户从主 README/Profiler README/automatic guide 的公共 integration 索引进入安装，并执行其中“complete patch first, then automatic-source-origins.patch and automatic-import-order.patch”的指示。

**预期**：精确 FlagTree0364/FLIRff91/AscendIR4c304 pins；FlagTree/FLIR 各应用一次完整 census-v2 patch，不再叠加旧补丁。

**实际/依据**：总索引仍命令叠加旧补丁，后端专页明确禁止把这两份旧补丁叠在新完整 patch 上；实际 source recipe 的 `PATCHES` 也只选择完整 v2 patch。用户公共入口得到互相冲突的构建步骤。完整 source recipe 已有成功证据，这不是其 fresh build 失败，也不是 native 构建能力缺失。

**最小修复/验证建议**：把总索引替换为三个精确 pins/两份完整 patch 的摘要和 source recipe 链接；明确旧补丁仅留作历史。顺带让 NVIDIA 索引列全专页中的 `preallocation-admission.patch`（当前总索引只提前两份）。静态核对总索引与后端 recipe 的列表一致即可；不需要重复不变的 C++ 构建。

## 待验证风险与边界（不计入 confirmed 缺陷）

1. **资格未整体通过**：只读取 `qualification-final-safe-v3/` 的 index、三份 safe aggregate、`state-helper-ciface-scope.json`。NV/GCU main 各 48 profiles pass；Ascend 注册 24 baselines，23 eligible，46 profiles 中 45 严格 pass、1 个 `original_cli_failed_missing_receipt`，且 `unresolved_eligible_actual_state_assertion_failures: 1`。安全摘要说原实际状态值未保留、exact profiled binary 与 passing controls 相同，ciface 定义未在当前安全材料中建立写者唯一性。不能用 passing controls、公开 RMW 的 state=1、其他回归或本次静态走查关闭该失败；不能标为环境问题或更改分母。本席未读私有源码/IR，不能独立归因。
2. **gate 诊断的防御性边界**：`fine_grained.py:515–527` 对 identity 有效、source 位置有效但仅 context census 行的输入会正确拒绝，却给 `internal_records_lack_valid_source_snapshot_positions`，action 指向 snapshot。`test_fine_grained.py:523–544` 的现有 fixture 涵盖该输入，只检查 incomplete。继续追 producer 后，`source_census.py:146–147,229–230` 在没有 primary visits 时选 `None` 并输出空 records，因此未证明冻结默认 producer 会生成“纯 context-only normalized rows”。这只列为 helper/未来输入诊断风险，不冒称默认链已证缺陷。若以后要保留 context-only 视图，可同时细分无 primary 与无有效 snapshot 的原因。
3. **静态/source identity 不等于动态成本**：`SourceCatalog` 确认 snapshot digest、精确 binary/path 与行范围；文档和 HTML 都明确不独立证明 compiled-text alignment。census 的 count 是 source-control visits，包含 all-false masks，无 duration、active-lane 或 busy 结论。本席未把这些诚实边界当缺陷。
4. **验证范围有限**：没有执行交互浏览器控制、复杂并发、SDK 取消/进程异常，也没有重新编译 C++。所读 tests 证明项目存在相应断言，不表示本席新运行过它们。CLI/API 默认与显式模式、fresh install、公开证据均不能被扩写成任意输入/SDK 都通过。

## 安装、版本桥和已存证据核对

- **包版本桥**：最终安装包来源 `ce00df63828c5e657c0307d7b69c99706dc12d49`，native 输入 `1f914a8b03bc3fe4fe73c1be49f22b91babdc6a5`。本席用 Git 查看 `1f914a8→ce00df6`：只涉及 Python callsite candidates、相应测试与文档；`ce00df6→0f6e1da` 共 11 个测试/文档文件，没有 runtime/native 改动。故审阅源码与安装包 runtime 对齐，但不能称 0f6 包做过一次新 C++ 编译。
- **三包独立安装**：读取 `install-audit/{summary.json,audit-notes.txt}` 和 `callsite-packages/{summary.json,notes.txt}`；实际打开三份 callsite evidence archives 的 `audit-result.json`、native/source indices、assembly metadata，独立重算 archive SHA 与 summary 一致。新包 component Python 各 68；parent Python NV280/GCU291/Asc180；完整 ce00 source packet 各 943 文件；native/header/frontend member 集合和 bytes 记录为 unchanged，268 native source files unchanged。三份 `audit-result` 都如实写 `native_rebuilt:false`、`device_work:false`。本席未重新访问 remote wheel 或全量 object graph，只检查所存索引/receipt；没有用“49 CPU tests”代替源码走查。
- **完整 source recipes**：NV 是指定 57d348b baseline + 三 patch + official setuptools/CMake；GCU 是 add842f2 baseline 的独立 clone/snapshot/build/metadata executable/wheel/install；Ascend 是 0364/ff91/4c304 pins 与两份完整 v2 patch、LLVM22 core/native + 独立 LLVM15 observer。本席实际读了三个公开 recipe/build scripts、Python/CMake packaging policy，以及 Ascend `ascend-public-build/{index.json,REPORT.md}` 的原 argv/exit/hash/PID。Ascend 公开入口 29 commands 全 0、无 manual header pregeneration，有明确 snapshot `08edb28` 与 native-input 版本桥；这证明该入口，不能替后续 unseen qualification 背书。
- **没有抹去安装副作用**：notes 明确保留 NV offline SDK cache 初次缺失及 `/root/.triton` 写入、GCU 缺 wheel packager 的失败/恢复、没有 `.git` 的 copied source packet、GCU build/lib RUNPATH 与实际解析、Ascend torch/torch_npu import-order 限制、filtered build snapshots 和初始严格文件数比较失败。匹配 Torch/SDK/LLVM 分发依赖允许复用；这不授权依赖未记录的热改源码目录。本席未将其重新包装成全量 fresh native 编译。
- **默认公共回归**：读取三个 `*-root-archive-check.json`、`root-bundle-capture-accounting.json` 和相关 terminal。计数是 NV22 bundles/22 captures、GCU12/14、Asc9/9；原 terminal 的 captures 字段确实按 bundle 计数，修正另存，不能拿旧字段代替实际 captures。
- **三 bundle 独立离线抽查**：在公开 archive 中分别读取 NV `result-ordinary/reduction`、GCU `result-control_flow_hardware-default/alternating`、Asc `result-ordinary-default/reduced`。直接用标准库核对所选 bundle manifest 的每个文件长度/SHA，分别 33/38/38 项，均无 mismatch；observations captures 分别 1/2/1、normalized rows 7/16/8，selection_status 都 complete、coverage 行数匹配，source diagnostics 都为空。census count/exact/role、null clock/start_tick 与源码位置符合 guide；三个 derived views 都使用 refs。此抽查没有运行产品 decoder，也不取代全矩阵 gate。
- **其他证据边界**：只读 `independent-worker-aggregate.json`，未读取其私有 kernel/IR；记录其 8 profiles、16 calls/captures、state/non-idempotence 和全 rawcells 验证均为已存 aggregate 声明。读取公开 mixed/state archives 的 index 与 result commands：均指向 ce00 runtime/0f6 source、保留 actual SDK input/object/final 输出。没有据 result 的 pass 推导 ciface 写者唯一性，也没有把公开诊断关闭原资格失败。

## 实际源码阅读范围

完整阅读或重点段落跟踪如下；“重点段落”不宣称逐行覆盖整个模块。

- 公开合同/入口：`usability_goal_prompt.md`、本席 C3 模板、主 README、Profiler README、`Profiler/docs/automatic.md`、`automatic_schema.md`、`source_site_census.md` 的相关合同、`docs/enflame.md`，三个 backend README 和 integration 总索引。
- 安装/打包：`python/flagprism_build.py`、`cmake/FlagPrism.cmake`；NVIDIA helper 与三 patch 入口/ABI/cache 关键段；GCU `build_from_source.py`、`build_automatic_wheel.py`；Ascend 两个 build scripts 和完整 source patch 的配置入口。未逐行重审合并的全部 upstream patch。
- 公共运行：`cli.py`、`_capture.py`、`_deadline.py`、`_backends.py`；`profile.py` 的 automatic routing/request、start、snapshot、native observation durable recovery、finalize、cleanup、API timing重点段；`hooks/launch.py`、`hooks/hook.py`、`hooks/graph_guard.py`，`hooks/instrumentation.py` 的版本能力检查、allocator admission、capture/ack/deactivate；`native.py`。
- 编译/设备到 bytes 边界：`Debugger/python/flagtree_debugger/compiler.py` 的 GCU/Ascend census ABI 生成段、`runtime.py` prepare/export/release、`gcu_census.py`；`ascend_compiler.py` prepare 和 source/plugin/driver handoff 相关段；`nvidia_census.py`、`source_census.py`、`ascend_census.py` 的 descriptor/admission/read/selection 相关段。没有逐行审完 C++/LLVM pass/native runtime，也没有阅读私有 IR。
- 导出/报告：`_report.py` analyze/normalization相关入口及 write_bundle/write_manifest 主链；`reconstruction.py`、`fine_grained.py`、`source_capture.py`、`source_view.py`、`execution_view.py`、`export_refs.py`、`export_timing.py`；`cann_artifacts.py` 路径/完整保留/ZIP验证/cleanup；`cann.py` collector 和 importer。legacy Hatchet viewer 仅查看函数/入口范围，未完整审查其全部派生指标。
- 测试源码：`test_fine_grained.py`（identity/source/gate/census）、`test_source_navigation.py`（snapshot/encoding/escaping/ambiguity）、`test_export_refs.py` 相关契约、`test_deadline.py` 主要用例、`test_export_timing.py`、`test_cann_importer.py`、`test_portable_capture.py` 的错误/恢复用例；`tests/DEFAULT_AUTOMATIC.md`、`source_census_public_regression.py` 和 default drivers/shared raw-census 断言入口。没有读 private qualification workload、数学 kernel 或其 IR。

交付修复应先处理 C3-MAJOR-01 的显式 replay policy，再改公共安装索引。两项都可以做有限、针对性的验证，无需因为本报告重跑全部不变的 C++/硬件矩阵。修复后本报告仍只对应上述冻结版本；新版本需记录处置和相关复核。未解释的 Ascend eligible 失败继续保留独立验收状态。
