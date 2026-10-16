# R16 产品验收第三角色：默认体验与交付，有限 delta

身份：`/root/r16_product_delivery_delta`；本席是产品验收角色，不占额外三位指定模型代码走查名额。工具未返回可确认的实际 resolved 型号，本席不作模型自述认证。只读产品审查，唯一写入是本报告。未读 peer 报告、其他席历史结论、root 预期结论、private 数学/IR/case 映射；未运行产品导入、测试、构建、浏览器或设备任务。

审查起点：`FlagPrism-method` / `detailed-profiler`，`ffad8b94c81fbea1c961b0f167953db4c14c3889`。结束时 HEAD 为 `07fbc591458254f59e3d2c0d77022e0dda6f405d`；实际核对两者 diff，仅增加 `integration/evidence/usability-r16-nvidia-current` 的归档。产品 Python/native 目录相对 `a829a3312af69c1b961919025053829d7096a2b1` 没有 diff。工作树无 dirty 输出。源码和文档结论适用于上述相同产品内容，不把归档 HEAD 当成另一次 runtime 构建。

结论：有限实际阅读范围内未确认 blocker 或 major。发现一项 minor 当前交付状态文字过时；原 D1–D3 的有限文档修正仍成立。当前 NVIDIA 报告浏览器导航缺口已有真实有限证据闭合；GCU 当前最终矩阵及 Ascend 新增数学泛化结果在本稿时待父任务补充，不据此宣称三后端完整最终验收。

## Confirmed findings

### D4 — minor：Ascend 安装页的检查点状态没有接上当前 SDK/device 结果

- 位置：`integration/patches/ascend/README.md:33–44`；同一状态见 `tools/ascend_sdk_legality/README.md:243–246`。
- 触发：普通用户按当前 Ascend 源构建/SDK 替换文档判断可用安装组合与剩余验证。
- 实际文字：前者仍以 ec75 检查点描述独立资格 42/44、两项 State 失败“still open”，并称 isolated SDK compiler “device validation is still required”；后者也说新 compiler requires separately authorized device validation。
- 证据：这确实是旧 ec75 + stock SDK 的历史结果，不能删除或改记通过；但当前同仓 `integration/evidence/usability-r15-ascend-main24/SAFE_COMPLETE_AGGREGATE.json` 已为 main24 的 24 ordinary / 48 cold-warm profiles 保留通过结果、466 terminal obligations、原始 bundle 不变、source/object/binary 闭合及负控制拒绝等匿名字段。该 aggregate 的最大完整 bundle 为 22,082,976 bytes，最大 finalize/export 为 1.0609786515124142 秒。故“device validation still required”作为当前状态已过时，尤其安装页没有把这段标题明确标成历史检查点。该问题不否认旧 SDK 失败，也不证明尚待新增泛化集合通过。
- 预期/有限建议：将原段明确标为历史 ec75 + stock SDK 检查点，并追加当前实际 SDK compiler 指纹/选择方式与 main24 证据链接，分别注明新增泛化的真实终态。只需文档修正，不要求重跑设备任务或改 runtime。
- 范围：已确认的过时交付说明，非安装命令已实际失败的证明；不能据此升级为 runtime blocker/major。

没有其他 confirmed blocker/major/minor。未将“任何输入都可覆盖”“自动诊断”“所有并发均支持”等额外能力列为缺陷。

## 默认工作流与实际源码一致性

实际读合同 `usability_goal_prompt.md`，以及 `Profiler/docs/automatic.md`、`automatic_schema.md`、`source_site_census.md`、三 backend 的完整安装 README、source-build 与 wheel assembly helper。源码重点为 `cli.py`、`_deadline.py`、`profile.py` 的自动请求/启动与 finalization、`fine_grained.py` 的报告列与逐调用完整性门、`source_view.py`/`execution_view.py` 导航、`observations.py` 和 `source_census.py` 的默认请求/语义/损失。另读共享 graph guard 与 Ascend SDK build/bootstrap/buildcompat/template/rebuild 工具实现及 compiler identity 文档。不是重做 native 全量代码走查。

- 默认命令可复制：`python -m flagtree.profiler.cli --detail auto -n profile-run my_kernel_script.py`。`cli.py:122–124` 的 detail 默认仍为 None；公开文档明确省略它得到 native collection，API 也需显式 `detail="auto"`。未把 native-only 成功冒称内部观测成功。`profile.py:1418–1427` 为三个目标 backend 实际构造 `counter` + `programs=None` + `all_grid_census`；`observations.py:40–43,77–84` 对应八 sites、1,048,576 cells、8 MiB 与禁止 census sampling。文档没有把展示一个 program 说成只采一个 program。
- CLI 与 API 时限区别真实存在：`_deadline.py:73–97` 单 worker JIT 锁拒绝同时 host-thread JIT；`cli.py:405–419` 将 auto 放入 supervised worker。文档写 eager streams eligible，但不据此承诺任意同时记录。120 秒编译/60 秒累计导出及 API 无同等强制中断的限制均有明示。完整 bundle 64 MiB 是验收小样本门槛，不被说成任意用户输入硬上限。
- Graph 边界：自动指南明确 NVIDIA/NPU/GCU 内部采集拒绝 graph capture；共享 `Debugger/python/flagtree_debugger/graph_guard.py` 实际对当前/实际 stream 查询，无 query、失败或非 bool 均拒绝。文档区分 native CUPTI graph mode 和已有 graph replay 无自动 JIT 记录。未发现将不支持路径写成支持。
- 语义与损失：`source_census.py:339–346` 保留 count/exact/unknown_loss，occurrence/clock 为 None；指南明示 visits 不等于 productive lanes、completion 或时长。Ascend v3 header/三 bank/padding 的预算说明和 legacy v1/v2 unknown transport loss相符。`fine_grained.py:511–546` 按 capture+invocation+binary 做 exact nonzero primary gate，并让全矩阵 overflow/unknown loss失败；`548–557` 检查 expected launch 缺 capture。报告没有以另一个 kernel 的有效记录补空调用。
- 首次报告：公开入口为 `report/index.html`，细粒度、sources、execution 各页可达。`fine_grained.py:278–281,391–403` 实际显示 Visits、Count exact、Site role 并给 source/execution 导航；`source_view.py` 使用已捕获 source identity，`execution_view.py` 分开静态组织和测量身份。文档明确快照 bounds/digest不等于编译文本完全一致；没有要求用户解析 IR/多份 JSON 才能完成基本导航。
- 源构建与打包：NV pinned baseline + 三 patch、真实 setuptools/CMake build，文档包含 Torch 的 upstream Triton 依赖冲突和 no-deps 独立安装；GCU recipe独立 clone、immutable component snapshot、fresh build/metadata executable/venv并保留 resume失败；Asc recipe 固定三仓/两个完整 diff，真实构建 core/frontend/native + 独立 LLVM15 observer，再打包安装检查。GCU/Asc advanced assembly helper 明确复用 native，不暗称重新构建；逐 Python/native/header 字节检查和 backend marker存在。Asc SDK LLVM19 独立工具与 LLVM22 parent、LLVM15 observer分开，template resources和 matching baseline gate均写明，不要求用户将 LLVM 插件载入 vendor fork。

D1–D3 独立重核：automatic.md 不再要求叠旧 Asc origins patch；Asc README 明确旧 patch禁止叠加。Enflame README明确默认为 admitted全grid visits/null clock，legacy timer另标 advanced。automatic.md明确源构建 recipe已经存在，链接、前提与实际 source helper相符。未重新提出原已关闭问题。

## 当前有限结果证据与版本范围

以下读取匿名结果、安装字节/来源收据及本席离线摘要，未阅读 private 数学源码/IR，未冒称本席亲自执行硬件/浏览器验收。

- Python/native 安装闭合：实际离线读取 `run-014/python-alignment` 的 NVIDIA/GCU retained tgz，SHA 分别为 `d90b3d45c129c2ab621570fe0732609592ad820533fa042b8d24bd1e289a0dd3` 与 `a93276ad55d4e6bcb377ae19f91954fe5146a936cdde3a1f63e077ea97a6c089`。两个归档各自 `native-source-bridge.json` 的 273 项逐一与当前实际源码 bytes SHA 比对，均无 mismatch；只解析 JSON/哈希，不导入产品。`root-alignment-retained-byte-audit.json` 记录 NVIDIA 597 package / 348 Python / 216 native origins，GCU 438 / 359 / 63；`root-nvidia-actual-byte-check.json` 对实际 package-stage-ZIP-installed 597 项、source 1049 项有原始路径/hash结果。当前 runtime 目录对 a829 无 diff，因此不能因当前证据归档 HEAD 变化反推 package过期；这些 receipts 也不表示新的 full native rebuild。
- NVIDIA：允许的 `SAFE_CURRENT_MATRIX.json`、`SAFE_CAPTURE_RESULTS.json` 与 `root-current-qualification-audit.json` 明确 current Python a829、24 ordinary/48 profiles/64 captures、24 cold-warm binary pairs，0 eligible removals/0 automatic retries；最大 bundle 2,026,437 bytes、最大 export 0.5200843459970201 秒。标注是 original independent cohort 的 current repaired-version revalidation，不是新数学。
- NVIDIA 实际浏览器：`SAFE_CURRENT_BROWSER.json` 的六个真实 bundles各有 source navigation/backlink、filter empty/reset、raw link打开、非空 execution mapping、Visits/Count exact/Site role等可见列；page errors空。首次因错误 FONTCONFIG 环境 page crash被保留，修正已有软件 browser环境后成功，product/gate/report bytes未改。`SAFE_BROWSER_LIFECYCLE.json` returncode0、owned_remaining空；`SAFE_DEVICE_RELEASE.json` controller无 children/fds，24/48任务 owned remaining空。它闭合旧“只有静态HTML字段、没有真实导航”的 NVIDIA缺口，不扩展为其他 backend浏览器通过票。
- Ascend main24：读取 `SAFE_COMPLETE_AGGREGATE.json` 的匿名结果/字段，24 ordinary/48 profiles、466 obligations完整；与上述 D4 当前状态差异直接相关。此证据是现有 owner实际结果，不是本席重新检查466份private IR或做数学认证。

## Verification gaps 与 optional

V1：本稿时 GCU current 最终24/48矩阵、实际browser终态，以及 Ascend 两个新增数学泛化的有限匿名最终结果尚待父任务提供；不得以旧结果或运行中状态当最终通过。无需为本席另采集，本席只接受最终有限证据 delta。NVIDIA当前导航已有证据，不能继续列为同一个未完成项。

本席没有逐一动态复现所有 SDK不可用/取消/cleanup/多stream/graph错误恢复；该有限审查没有发现相反证据，不能把未亲自重跑自动升级为confirmed缺陷。完整三后端及额外三位指定模型代码走查的验收仍由总任务汇总。

Optional：无新增建议清单。本报告只要求 D4 的有限当前状态澄清，不要求未变产品重新全量review/构建/资格采集。

## 最终有限补核：D4 文档处置与 V1 终态补证

父任务仅提供文档 dirty diff 与已完成匿名结果后，本席进行一次有限补核；没有重读无变化的 runtime、访问服务器/设备、启动测试或读取其他审阅者意见。以下替代上文稿时状态，原发现及其当时依据保留。

**D4 已关闭。** 实际完整读取三文件 dirty diff：`integration/patches/ascend/README.md` 现在以 current a829 / actually built bd61acd native / isolated fixed SDK 为当前组合，链接 strict12、finite2、main24、new8；旧 ec75 + stock SDK 的42/44保留为 Historical checkpoint，没有改记为首次通过。`tools/ascend_sdk_legality/README.md` 同样区分 build recipe无NPU运行与随后单独执行的device验证，不再写新工具仍待device验证。`BUILD_VALIDATION.md` 保留原CPU任务范围，把 pending限定在当时CPU-build checkpoint并指向当前README。全部新增/相关本地相对链接实际存在，未编造anchor。未确认此有限文档修正引入其他问题；不需要改变runtime或重跑矩阵。

**V1 中 GCU 当前矩阵和browser、新增Ascend数学泛化证据已补齐。** 本席实际读以下SAFE原件并对匿名数组做离线一致性摘要：

- `artifacts/usability/run-015/gcu-current-qualification/SAFE-final-aggregate.json`：component a829、wheel `f24cd4cb39dc411c7c1e04ab3f7d6797a0628ae9284d3cb267b4e8e9b1645c30`，24 ordinary全部通过、48 profiles全部通过，2944 full-grid cells、16 same-binary runtime pairs；removed0、first_failures0、hidden_retry=false、原数学/输入/容差与bundle不变。最大完整bundle 23,212,507 bytes，最大finalize/export 0.5148944016546011秒。实际profiles数组48项均为pass。
- 同目录 `SAFE-browser-results.json`：当前GCU自身12个真实新bundles（六kernel cold/warm），逐项all_counts_exact、source navigation/backlink、interactive filter、execution mapping、raw evidence link均为真，page_errors空。`SAFE-device-release.json`：qualification exit0、GPU_jobs_finished=true、907 owned identity checks，owned_alive空；final aggregate的owned_survivors也为空。这里不以NV浏览器代替GCU实测。
- `integration/evidence/usability-r15-ascend-new8/SAFE_COMPLETE_AGGREGATE.json`：8 ordinary /16 cold-warm profiles全部pass，96 terminal obligations；本席按16行实际求和为96，所有 `required_terminal_all_pass`、`original_bundle_unchanged`、`source_actor_generated_input_object_binary_closure`为真。最大完整bundle20,499,086 bytes，最大finalize/export1.0582344275899231秒。`root-new8-complete-audit.json`列出24 indexed files、17 actual remote anonymous files及同样8/16/96终态，writer proofs为16 mixed explicit SUB0 guards。这闭合上文新增数学泛化终态缺口，未读取kernel数学/IR。

本席获得的补证尚未包含 Ascend new8 的实际browser SAFE终态；父任务称正直接比对，因此本席不提前为该额外browser补证盖章。它不使已补齐的new8 8/16/96数学/raw终态倒退为pending，也不撤销当前NV/GCU实测导航结果。若总任务另要求new8实际browser闭合，由root引用其直接比对终态；本席无需新采集或扩大review。

本席最终结论：confirmed blocker/major无；D1–D3未复发，D4经实际文档diff关闭；有限交付复核无其他确证缺陷。以上结果只证明所列实际版本与范围，不代表任意输入/并发/设备性能认证。
