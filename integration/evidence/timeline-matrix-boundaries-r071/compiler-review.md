# R071 limited compiler review

审阅冻结候选 `c2224b35d8c4363921b5369b038778730960b164` 相对 `85f08a8` 的三个文件：`timeline_nvidia_late_boundaries.py`、`test_nvidia_matrix_issue_boundaries.py`、`p01_nvidia_matrix_issue_boundaries.py`。另读其直接依赖中实际 object/disassembly 绑定、PTX lexer、reader map、`_single_entry` / `_straight_path` 和自动报告调用链，以及 `run-071/preflight` 的 input、terminal/result、format 收据。未阅读 peer 报告。实际 serving model 未暴露，未知。

**结论：没有发现该有限 delta 的具体 unsafe 假通过或新的 compiler 正确性缺陷；支持把它作为 SM120 指定 FP16 形状的自动 matrix issue 边界诊断服务。当前证据是源码加载的 CPU 检查与既有真实原件的离线核验，正常 wheel 安装闭环尚待对应收据。此结论不授予 native loop/source region、普通流水保持或 whole-goal 资格。**

## Confirmed blocker / major / minor

本次有限阅读没有此类项。判断依据如下。

- `timeline_nvidia_late_boundaries.py:306` 的入口仍要求实际 late-v1 SM120 map、相同 binary ID 及原 PTX hash；`_bound_functions` 检查两份原 disassembly 的 hash、函数 extent、opcode、predicate 和 operands。真实原件测试通过 `load_late_machine_map` 从 retained CUBIN/PTX/disassemblies 重新建立 map，没有仅信任保存的成功状态。reader 的 marker line 与 site/phase 键也须一致且唯一。
- `:118`–`:188` 只识别明确的 `mma.sync.aligned.m16n8k16.row.col.f32.f16.f16.f32` 及 4/4/2/4 register groups。候选必须非空、数量与 manifest members 相符；bracket 中出现所识别 matrix 家族的其它 PTX 形式或 predicated PTX 会诊断为 unverified。reader 必须同函数且无 native predicate，每条 PTX instruction line 必须映射到恰好一个 `HMMA.16816.F32`，PC 必须严格落在两 reader 之间且自身无谓词。
- `:189`–`:199` 拒绝多个 PTX issues 复用同一 native PC，并把 bracket 内已识别 native matrix 家族的 PC 集与绑定结果作精确比较。随后检查完整 reader-to-reader native path：内部真实控制转移、缺指令、外部进入中间的控制边均拒绝。没有依赖两个 reader 的数值接近或正 duration 来替代这些条件。
- 成功项只是 `matrix_issues_between_inline_readers`。matrix completion、source cost、hardware busy、participation 均保持 false；顶层 source-region、clock、value provenance、hardware overlap 和 time-flow 资格也保持 false。`:401` 将新项目放进既有自动报告，没有把成功状态用于放开这些权利。

## 实际收据与测试对应关系

`matrix-rule-poll-v1.json` 为 terminal 0，0.615734957 秒，pytest 输出 `13 passed in 0.09s`。两个正例为 1/4 个支持的 issues；11 个反例覆盖不同 geometry、PTX/reader/native predication、别名 PC、missing/outside native issue、额外 native matrix、member 数量不匹配、内部 branch 与外部中间入口。

`test_nvidia_matrix_issue_boundaries.py:72` 的 internal-branch / extra-matrix 变异会先平移后续 PCs、native-line 映射和 exit reader，保留全部原矩阵指令，再插入真实 BRA 或 IMMA。尤其 branch target 在 bracket 内，矩阵数量和映射仍完整；其失败确实需要控制路径检查，不是删去矩阵造成的间接失败。external-entry 反例从 bracket 外跳入 PC 32，触发独立的中间入口约束。

四个实际报告覆盖 default/sparse 各 K3/K7，site 23 均为四个支持的 PTX issues：default 的 reader `0x1260` / `0x1310` 间为 `0x1270,0x1290,0x12b0,0x12d0`；sparse 的 reader `0x1010` / `0x1090` 间为 `0x1020,0x1040,0x1060,0x1080`。四份既有 capture 分别有 24/56/24/56 个 positive paired intervals，共 160 个区间、320 个 endpoint u64 比对。脚本逐端点读取原 raw word，并与保存的 record tick 和 event start/end tick 核同，同时检查 raw SHA256、complete 状态与 canonical site 导航。

输入收据中的产品文件 SHA256 为 `de67176c5712369fa835e6a5b6e8924d3612b1cc1efe532fe683b72899f249e9`；当前格式化文件为 `592fec29cdab3ca243f3bbaa9396352fa1770c05390473b58be67982ab04ec91`。三份 executed/candidate 文件逐项 diff 仅格式，stdlib AST 比较全部相同；formatted archive 中的产品文件与候选 bytes 相同。runner SHA256 `b62d85398a8de8eb357357c0093db4e85d44ce6deb585ae9ce9b2ea0e951086e` 与 terminal 相符。format 收据为 0，yapf/ruff 通过。这里支持相同语义源码的检查，不声称已执行格式化后 wheel。

## Verification gaps / scope / optional

正常 wheel 的装配、隔离安装及已安装入口报告尚未在本次所读收据中闭合；不把 source overlay 冒充安装资格。该项不否定当前源代码的有限正确性结论。

本规则核对的是 bracket 内原 PTX issues 与有限 native 家族的 issue placement。manifest members 在此只作数量核对，未证明每个 LLVM source member 的独立身份或 value flow；报告也没有赋予该项资格。未知矩阵形状、其它 SM/ISA、任意源区域、iteration/loop 身份、全路径动态次数、clock value-to-store、tensor engine 完成/忙碌和 ordinary overlap 关系都不因此获证。不能将保留的 160 个区间解释成 source-exclusive cost 或原普通流水的时长证书。

本次只做 Git/文本、stdlib JSON/hash/AST 与 archive 读取及报告写入；没有 import 产品、跑 pytest、编译、重放 application、连接服务器/设备或启动子 agent。不要求新矩阵或通用 ISA 证明器；没有额外 optional 项。

## 追加：有限 installation gap 已闭合

实际读取了 `preflight/installed-and-loop-results-v1.json` 中仅 `native-install-v1` 的 terminal/result/stderr，以及 `preflight/installed-regressions-sql-v1.json` 的安装后回归和新 dependency trace 验收结果。没有把同文件内的 native-loop-probe 纳入本产品 delta，也未对该 probe 作资格判断。

安装 terminal 为 0、71.942429863 秒，13 个步骤全部为 0。source commit 为已审 `c2224b35d8c4363921b5369b038778730960b164`，记录 639 installed members，wheel SHA256 `22f7d3334505c057e35615512932c6981aa9f0a0cf19c77bc328eb9435c4fd1e`；隔离 venv 的正常 pip install 与 installed import 均成功。收据明确本次 native 沿用 R070 安装输入，264 个相关 native 源文件不变、`native_rebuilt=False`，没有把 Python 规则更新说成新 native 构建。

已安装 interpreter 的 normal / `-O` 单位检查各 13 项通过，分别 0.12 / 0.21 秒；`-O` 仅有 pytest 关于 test modules/plugins 之外 assert 的预期 warning。已安装实际原件检查为 0，仍为四个相同 binary/invocation/raw 的 24/56/24/56 个区间，共 160 intervals / 320 endpoint words，四个 matrix site reports 均成功。

公开 normal CLI 在复制 sparse bundle 上导出 8 counter 与 2 dependency，reason 为 null；控制报告实际包含成功的 `matrix_issue_sites`，仍保留全部 false 资格。8 个 counter exports bytes 与 R070 相同，未重复验收其未变 bytes；2 个 dependency exports bytes 已变化，因此读取了其新 Trace Processor 验收，而不是继承旧结果。新 SQL job terminal 为 0、2.418730067 秒；两份新 trace SHA256 分别为 `df965ba3fb710d6f69d16400c613a39885a3b98a08c1233f8fbf66c96de2aea5` 和 `0d3a840da5d8c4dc610101b5f5d0e1f1355d8313f3b7c445f022fd30d88ed19d`。每份均为 180 nodes、404 flows、208 internal events，raw offsets/ticks/ns 与 protobuf fixed64 核同，importer errors 及非零 error stats 均为空。

**当前结论：本报告此前待证的 R071 installation gap 已按正常 wheel、已安装规则/原件检查、公开报告入口及变更 dependency bytes 的新 TP 验收闭合。** 这支持已审有限 matrix issue 诊断服务的实际安装链；source/loop、ordinary pipeline、engine completion/busy、参与完整性及 whole-goal 等原独立边界仍保留。本次只是读取收据和追加报告，没有运行任何产品、测试、编译或设备任务。
