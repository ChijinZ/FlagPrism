# R072 limited independent delivery/test review

审阅基线：`5dca71cd80dda78afafebb52b8c965ac9368b377`，相对 `38e2ffa`；另只读当时额外的 `p01_nvidia_operation_origins.py` 43 行 offline-reader fixture。没有运行产品、测试、构建、设备或 SQL/UI，也没有读取其它 review。resolved model 未暴露，记为 unknown。走查完成时另见 HEAD `1068cb4` 及 operation-origins 模块/测试的新工作区修改，**本报告不覆盖这些后续产品字节**。

**结论：现有证据支持 5dca71c 的有限 operation-origin delivery，未发现本次走查范围新增的 confirmed blocker/major/minor 产品 bug。** 新 standalone 实际重建、640-member wheel 安装及实际 capture 自动 inspection/offline reload 有收据。不能把 compiler debug origin 映射当作完整源码边界、valueflow、耗时归属或 whole-goal 通过。

## 产品路径及解释边界

- `late-timeline.cpp` 在 manifest 中先保留每个 selected LLVM member 的原 source file/line/column，使用独立 synthetic file 和唯一 origin line；插入 recorder 并完成 mem2reg 后才给原 member 设置 DebugLoc。没有直接把 reader/logger 的 LLVM 指令分配为原操作 marker。原 debug scope 缺失时明确记录 unavailable，不伪造 scope。既有记录布局、数学指令和资源上限没有由该 delta 改写。
- `timeline_nvidia_machine.py` 在实际 counter map 成功后，用同一 nvdisasm 对实际 retained cubin 额外采集 `--print-line-info`。输出经过独立 native JSON 的 function/PC/opcode/operands 校验，采集前后检查 disassembler SHA，保存 source output、origin report 和状态。新增分支失败只降级 origin inspection；没有因此授权其它 qualifier 或丢掉 raw。
- `timeline_nvidia_operation_origins.py` 验证 binary、marker version、line/column、origin ID 唯一性和实际 native function/PC；保留一对多 locations、missing origin 和 unknown rows。总体 mapped 只表示存在映射，不能解释为每个操作齐全。
- `matrix_member_locations` 只对已经通过 finite matrix-issue boundary 的支持成员，要求各自唯一 HMMA、同 function、成员 PC 不重复，且 PC 集合与真实 bounded issues 完全一致。未知 geometry、缺 origin 或重复 association 仍 unverified。它独立于旧 PTX instruction-line boundary，但仍是 compiler debug identity，不能升级为 source-exclusive duration。
- `load_operation_origins` 离线只读 retained source/native JSON 和 sidecars；重查 binary/cubin/JSON/source SHA 及 matching disassembler identity，重新推导 origins/matrix association，不信 saved origins 或 saved qualification。文件缺失/损坏及 legacy marker 缺失返回 unverified；不调用编译器、nvdisasm 或数学应用。live/offline boundary report 都接入这一结果，旧 capture 仍可读。
- 新报告明确保持 source_regions、source_cost、participation、hardware_busy 为 false。现有 canonical/Perfetto 消费链没有因 operation-origin mapped 开启新的 timing/dependency 资格。runtime 文档的“selected LLVM origin、one-to-many/missing、legacy unverified”表述与代码一致。

## 安装与测试证据

根目录：`artifacts/timeline/run-072/preflight/`。

1. `native-install-input-v1.tgz` 的 C++、machine/boundaries/origins 三 Python 模块、原 native CLI test 和 runtime 文档，与走查开始时 frozen source 逐字节一致。归档 runner 与 `install_operation_origins_v1.py` 相同，SHA `ffd7be1cf6412ffe3af3f32629c0ca42db0e07ba4c2a8e94a14a9b26d41776eb` 对应 terminal receipt。额外 reader fixtures 不在此原归档，不混为同一版本。
2. 安装 runner 先正常构建新 standalone，检查 build receipt 的 source/executable SHA；共享 core/runtime 输入经源码比较后复用，再装入同一 wheel。`native-install-poll-v5.json` whole terminal 0，77.792 秒：实际 native build、assemble、seed-pip/install、disassembler、isolated import、既有 matrix normal/`-O`/actual regressions、legacy public reexport、origin CLI 和 origin-mapping normal/`-O` 均 0。640 installed members 字节核同，wheel SHA `0dacd4ea6d6adf0976b3457fc92637a68b32e015fc98cc6345a5f85fbcbd1d53`。不能把其中复用的 core 称为新构建。
3. native CLI test 覆盖 direct、no-debug、inlined 三个 LLVM fixture，检查原 source 导航、unique marker、缺 scope 降级及 probe 不继承 operation marker。mapping test 的 CPU SDK object fixture 用于 location/parser/corruption 检查，不是设备数学证明。原冻结实现/测试字节与 `formatted-v1.tgz` 一致。
4. `real-and-reader-poll-v1.json` 的实际 real-origins-v3 whole terminal 0，75.091 秒。C2、default 及后续 native-origin 检查均通过。C1 数学来自先前 real-origins-v2 已 terminal-0 的 C1 子步骤，保留 capture 后仅重新离线检查；v2 whole terminal 1 没有因此改写为成功。C1 是 8 origins / 7 mapped / missing [3]；C2 是 45/40，missing [26,28,41,42,43]；default 是 53/50，missing [40,48,50]。支持的 matrix members 均有限关联通过，missing 不计完整 source coverage。
5. 初次名为 sparse 的运行实际传 `--site-budget 8`，与 default 的 binary 相同，不能充当 sparse=1 覆盖。独立 `real-sparse-origins-poll-v1.json` whole terminal 0，22.302 秒，runner 实际传 `--site-budget 1` 并检查 manifest max_sites=1；两个 capture 使用新的 `0e0272e4...` binary，各 33 origins / 31 mapped / missing [31,33]，matrix association 通过。该补件确实关闭了这个有限 sparse 触发范围的证据不足，不扩大为其它稀疏形状或完整矩阵。
6. `origin-reader-v1` whole terminal 0；同一新安装的 Python 在 normal/`-O` 下执行额外 reader fixture 均 0。代码在自有临时目录使用实际 object outputs，检查忽略 forged saved qualification/origin cache、source/tool hash 不匹配及 missing source 降级；不是修改原 capture，也不是设备重放。fixture 内的配对假 tool hash 只用于 loader 分支测试，实际 tool identity 的证据来自正常自动 inspection。额外测试的当前快照 SHA `ca5641548a9b6239b37438ac072c934a821096a34774b294c61e148b492cdb48`，与读到的 `formatted-v2.tgz` 测试字节相同。

## Verification gaps / 正式交付状态

**G1：额外 reader fixtures 不在原 freeze。** 走查开始时 43 行测试增量尚未提交；normal/`-O` 的执行收据不等于 `5dca71c` 自带这些维护测试。最小补项是用正式 test commit / SHA 对照纳入这份已执行的测试；若后续已纳入，只需对照字节，不要求重跑设备。后续 `1068cb4` 和新的未冻结产品修改没有在本次小 review 中获批。

**G2：新 trace 的实际 TP 终态尚不能计通过。** 本轮已读的是 launch/poll 与 runner，未读到本任务新增 trace 的完整 terminal/result/stats 通过收据。runner 选择 C1/C2/default/真正 sparse=1 roots，排除重复的 budget=8 sparse label，计划检查 80 counter + 8 dependency，并固定既有 verifier SHA、seal 原输入。计划和空 stderr 都不是 TP 通过。最小补项是这一批新 trace 的实际 SHA/结果/完整 importer stats；不要求重采旧矩阵或重导相同旧 bytes。旧 UI 可说明未变的 view 编码/展示行为，不能代替这批新 bytes 的 SQL 接受。

未重审旧矩阵、其它 backend、全部 source-region/valueflow、普通 schedule/扰动、完整 async 或 whole goal。没有新增无边界审计要求；本结论只支持上述有限 build/delivery/test delta。

## Local evidence digests

- `native-install-poll-v5.json`: `5d417eeed51e9e1e9dcff4a78650c312c3d020f6b324e8c98f3302376bc82751`
- `real-and-reader-poll-v1.json`: `159dfb582678d40b75f245345dd87b0bd5ec54fae45804ab4c58d49c7040d27e`
- `real-sparse-origins-poll-v1.json`: `81cb60ae82373eaa9ef3cfa40b7f4aa755bacbbfd327afff6209bddcbc5d59b5`
- `formatted-v2.tgz`: `fe2d6e20c2cb03abb78066cd0f40a563ba28d49b0ad3c63280f55f0ff6062f35`

## 有限追加：G1/G2 闭环及 f420014 delivery 修复

以下更新保留原 freeze、历史 gap 和失败记录，不将它们改写为初次即通过。没有执行测试或连接设备，也不重审完整 goal。

### 原 G1 / G2 当前状态

- **G1 已关闭。** `1068cb4280cdda3555cfbad21aa06e71a059be9b` 提交了 43 行 reader fixture 和维护文档。该提交的 test SHA 正好为原报告记录的 `ca5641548a9b6239b37438ac072c934a821096a34774b294c61e148b492cdb48`，不是另写一份测试代替实际已运行字节。
- **G2 对首批新采集的实际注册分母已关闭：72 counter/shared + 8 dependency。** 原计划 80 counter 的估算没有通过 inventory gate；v1 是 receipt path 解析的编排失败，v2 实际明确拒绝分母 `(72,8)`。这些失败仍保留。没有把 80 改成产品容量、放松 verifier 或伪造另外八份 counter traces。
- `new-traces-sql-poll-v5.json` terminal 0，87.669 秒。`receipts-v1/new-traces-sql-v3/output/` 的 manifests 分别 72/8 行，results 分别 72/8 checks，trace 路径顺序及 input-seals 的 trace SHA 逐项一致；两组内部 SHA 均唯一。根 result 的两个结果 SHA 与实际文件一致：counter `92ab3e969ca0c65f270d094a059c474d8270d3d26fbd2c4493325c402188b521`，dependency `0c4597a7aeda2c49fff3b14d7b301e8480786774d40756289e12ceb82fc3a65c`。
- 八十份各保留完整 263 行 importer stats，无非零 error/data_loss，importer_errors 均为空；counter checks 的 exact ns/raw reference、dependency checks 的 raw offset/tick/ns/protobuf 检查均通过。合计 6512 counter slices；dependency 合计 2080 nodes / 4384 flows。结果明确没有 application replay 或 device execution，不能据此授予 source cost、精度、busy 或 whole-goal 资格。
- `receipts-v1.tgz` 实际 SHA `54916562f0395eb86f2c486e156c3672cb1229ac949615d48db719b0ca240418` 与给定封存 SHA 一致；34 个解包收据与归档字节逐份核同。

### f420014 源码有限补审

新基线 `f4200142b5c68352c74c853fdc71b2da123e092c`，相对 `1068cb4` 仅此处明确列出的 Python 修复/测试。本补审确认两个先前异常路径的修复，不把原有限 review 的“未发现”解释为穷尽保证。

1. `load_operation_origins` 读取 origin/counter JSON 后各检查 `type(...) is dict`，再调用 `.get`。原来的合法 JSON array/null/string 会产生未被隔离的 AttributeError；现在由 `_need` 变为受控 unverified。检查没有吞掉 core counter-map 校验、提升 optional source 权限，或拿缓存资格替代新推导。新增 fixture 对两个文件各三种 JSON 类型逐一恢复原件并验证降级。
2. `_run_tool` 将 `/proc` 身份读取和 command receipt 落盘纳入 `try/finally`。登记异常现在会进入 owned-child 清理；若 descendant-discovery 因持续身份读取错误不能收束，仍以尚未 reap 的 Popen handle kill/wait 直接子进程。没有按模糊 PID/name 搜索并杀其它进程。原成功路径继续等待并记录 terminal；输出/时间上限仍在。新测试实际启动长睡眠子进程，分别注入一次身份读取、持续身份读取、首次 receipt 写入失败，再检查 bounded return、returncode 和 waitpid 已无子进程。

未发现本小 delta 新增的 confirmed 产品 bug。两个产品模块、两项测试在 `native-install-input-v2.tgz` 中均与所审 freeze 字节一致，runner 与保存脚本及 terminal script SHA 对应；无 C++ 变化，因此复用已实际构建的 origin standalone/core 是合适的，不需要 GPU 数学重放。

### 新安装终态和有限 closure

- `native-install-poll-v7.json`：source f420014，whole terminal 0，74.897 秒，15 个步骤全 0。640 installed members 字节核同；wheel SHA `e112f2ecee6fc9557fbda7db71343dae132af8ee9a8722eda49bc2197213c7e7`。native/core/standalone 字节经源码一致性检查后复用，没有声称重建。
- 同一新安装 Python 的 normal/`-O` 实际 retained sparse reader（包含上述非 object JSON cases）和三种 child-cleanup pytest 均通过；实际成功 nvdisasm `--version` 路径也通过。这些是 CPU/工具路径实证，不是新 GPU capture。
- installed public CLI 在 owned 真 sparse 副本中将可选 `operation-origins.json` 改为 `[]` 后，仍生成 8 counter + 2 dependency，origin 为 `unverified_native_operation_origins`，application_replayed=false。该实证支持 optional-sidecar isolation 的普通离线用户路径；原始 raw/object/capture 没有被篡改。
- 这次 malformed-sidecar 重导产生的两份新 dependency 的 TP 检查，在本补审结束时仍为在途，**不提前计通过**；首批 72+8 的已封存 SQL 结论保持其自己的输入分母和 SHA 范围。它不阻止上述安装/异常隔离小修复的有限 closure，也不替代整体资格门。

追加收据 SHA：

- `new-traces-sql-poll-v5.json`: `d3b87f7021276c8aecaadb04d4f23adaea3ea32a87b636571d9b0755e12c30af`
- `native-install-poll-v7.json`: `2c4a249eaf64fd614fd13ccd6691404d063c1c429e7d4d1274d99a3f27e0bee9`

### 最后两份派生 dependency 的 SQL closure

后续收据已使上一段的“仍在途”成为历史状态，本有限 delta 的交付缺项现已闭合：

- `guard-deps-sql-and-counter-bytes-v1.json` 记录实际 TP job whole terminal 0，2.469 秒；独立结果 `receipts-v2/guard-deps-sql-v1/output/verified/result.json` 恰有两份实际 dependency trace。runner 固定原 dependency verifier SHA，未修改 verifier。两份 SHA 为 `8c6215405fdd4f816844f85861471f7916467bdf0057cbd25a0452b659fc14d3`、`fd60867b04dd10ae45045bd8275a6d5ce4d567a39c97705be9bbb6e8afc8a563`；各 180 nodes / 404 flows，实际 raw/tick/ns 和 protobuf 检查通过，各 263 行 importer stats 无非零 error/data_loss，importer_errors=[]。
- `guard-counter-bytes-v2.json` 的实际 byte-comparison 收据记录新导出的八份 counter bytes 与原件完全相同（8 counter / 2 dependency）。因此复用首批中对应 bytes 的既有 SQL 结果，不冒称为八次新 TP 导入，也不要求重复相同 bytes 的导入。
- 第二份归档 `receipts-v2.tgz` SHA `3ff62f024642944a42510e5697a5eaa9d9adff19ef7428aca26b8c6b62f16357` 核同，13 个解包收据逐份与归档字节一致。其实际 child-cleanup 日志分别为 normal 3 passed / 0.48 秒、`-O` 3 passed / 0.49 秒；pytest `-O` warning 原样保留。正常 wheel 的完整 15-step 终态收据也在该归档内。

最终有限结论：**G1/G2、f420014 的 normal installation、optional-source isolation / owned-child cleanup，以及此次新增派生 trace 的 SQL 接受均有对应收据，可支持该小 delta 交付。** 原全矩阵、source/valueflow、普通 schedule、全部依赖或 whole-goal 门不因此完成；whole goal 仍 open。没有执行新的测试、设备或 SQL，也没有改产品代码。

- `guard-deps-sql-and-counter-bytes-v1.json` SHA: `f4f632781c3582f6874011b2b8c172a8eac4c0e4e0f6c5884f18d686e4a4095e`
- `guard-counter-bytes-v2.json` SHA: `2df09e9fe6b01ede6f23ea795fe1a5f044194620d1973b7d1383241e48e1f06a`
