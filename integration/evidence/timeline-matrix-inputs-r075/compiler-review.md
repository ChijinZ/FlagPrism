# R075 finite matrix-input review

结论：本轮 source review **没有确认 blocker / major / minor**。当前实现可作为有限 qualification 工具：在支持的 SM120 `HMMA.16816.F32` / x4 LDSM / 原字 MOV 结构内，关联 A4/B2 各 word 的实际 reaching load，并在 fresh provenance / collective byte model 成立时关联该 load occurrence 的唯一 shared generation。它没有据此授予 ordinary pipeline、硬件 overlap、tensor completion、source cost 或 whole-goal 资格。

本报告的 source 判断与实际新 runner 验收分开；初稿后已补核 `matrix-suite-poll-v1` 的终态和步骤，不能把先前 prototype 的成功替代为本轮实际结果。P2R 本轮未重审，仍保留原 unknown。实际 resolved 模型未知。

## 阅读及未运行事项

实际逐行阅读 candidate 的 `tests/timeline/native_matrix_inputs.py`、`test_nvidia_matrix_inputs.py`、`p01_nvidia_matrix_inputs.py`；相关已有 `_inventory` / `_iteration`、`_destinations` / `_move_source` / `_predicate`、machine binding、`load_observed_dependency_inputs`、`derive_late_async` 与 byte model 中的完整 consumer footprint / producer / publication / reuse 检查。只复核本轮需要的交接，没有重开旧全审、阅读 peer 或重新审 PR 语义。

三个文件与 `run-075/preflight/matrix-suite-input-v1.json` 的对应源码逐 bytes 核同：

| 文件 | SHA256 |
| --- | --- |
| `native_matrix_inputs.py` | `0b303c2c5e22359d991480b3432d57c0f716483971613e7035dd581aac643cb9` |
| `test_nvidia_matrix_inputs.py` | `6545ff55f2f70e9f2ab09e4dc6dbf6d123a36659013464c2f705e08074d99c79` |
| `p01_nvidia_matrix_inputs.py` | `28845b9e5026794cf132a0770c07aa5f98ead411997aaea5f00c873201c94c2c` |

阅读了输入归档、旧 `matrix-inputs-poll-v1` 的终态 / prototype 结果，以及新 suite 的 launch / `matrix-suite-poll-v1` terminal、steps、normal/-O fixture stdout、actual 摘要；没有把旧 prototype 当成新循环/代际规则的实测结果。仅用 stdlib 读文件/JSON/核 hash，未 import 产品或 helper，未运行检查器、pytest、编译、SDK、设备、数学、模型、UI 或服务器任务。没有改实现。

## 有限代码判断

1. **逐 word 原生来源：helper:17–25、63–101。** 只接受支持的非条件 HMMA 型号及四个规范寄存器 operands，A 展开四 word、B 展开两 word；这没有把 B2 误扩成整个 x4 load 的四个输出。每个 use 都查所有 CFG reaching definitions，LDSM 记录真实 `destinations.index(current)`，`MOV` / `MOV.64` 使用已有 `_move_source` 保留对应 word offset 和 `.reuse`。活跃的其它 writer、未知 footprint、未定义入口、缺失/多重 load origin 拒绝。predicated writer 同时保留旧值路径，不因同名物理寄存器而猜来源。这里只认原字复制，不假设其它算术保持数学含义。
2. **防止前一轮 PC 冒充本轮 load：helper:26–61。** 依据 object-bound CFG 的 dominator natural-loop inventory 选最内层 loop；切掉该 header 的所有 latch 返回边，再作完整 DAG 检查。每个 use 的反向追踪局限在这个 iteration 图，带值越过 header 会成为 undefined；残留第二 cycle 不会只因 static load PC 相同而被忽略。profile runner:103–109 还核对与已 checked reader-pair loop 的 header 相同，避免另选一个较弱 loop。ordinary 只声明 native input origin，不声明 raw generation 或每轮 source 身份。
3. **source site 到动态 occurrence：helper:122–128，runner:99–115。** 只允许一个 checked matrix group，整个函数的 HMMA PC 集合须等于该组 members，所有 associations 的 loop header 须与已 checked native loop 一致。来源 LDSM 必须对应同 function、同 native PC 的唯一 checked shared-load site；在相邻 matrix records 之间该 site 恰好一次，缺失、重复、stale load 均拒绝。该限制对本轮已登记的 single-group loop 有效，不冒称支持多组共用 load 的动态关联。
4. **每 word 代际：helper:130–147，runner:87–98。** runner 先重新走 installed observed-dependency provenance（native boundary、timer/store、地址/ordinal/payload/header origin、wait 及 invocation/raw identity），然后从实际 raw 重新 decode / derive collective byte model。已有模型逐 byte 要求 observed producer 和 completion/publication，不能只由一小段有 edge 推断其它未覆盖字节。新 helper 要求该 load 全 footprint 的 producer 集合只有一个，且 generation 唯一、ready/publication 在 load 前；于是每个已知来自该 load 的 word 可绑定同一 generation。它不推断 LDSM lane→byte permutation，B2 只取其中两 word 也不要求猜它们的字节子集。mixed generation 保持拒绝正确。
5. **对象与调用交接：runner:40–57、67–92、118–135。** ordinary CUBIN 与 vendor JSON hashes 和实际数学编译身份绑定；profile fresh machine-map CUBIN 与 inventory hash 相等，fresh canonical identity / proofs 与 capture owner 对应，程序号唯一对应 byte model。每次 original runtime tiles 与 matrix occurrence 数交叉检查，留存输入在结束时复查 hash。profile 的 `raw_generation_binding_verified=True` 指这些关联成立，不表示 ordinary 也有 raw 代际证据；ordinary 仍明确为 false。

以上范围内未发现具体 unsafe pass。预算沿用 inventory 的 4096 nodes / 128 backedges / 1M work 上界，输入 word cone 另有 32768 states 上界；超限拒绝，不静默截断为成功。没有要求任意 ISA、任意 kernel、完整矩阵字节置换或新设备矩阵。

## 实际执行范围与 verification gaps

- **本轮执行终态已核，完整逐 binding 原件仍待归档。** `matrix-suite-poll-v1` 的 terminal 为 0 / 16.293s，三 steps 均 0。23 fixtures 包括 word-copy / 高 word / predicated overwrite / 多来源 / 未定义 loop entry / 无 loop，以及动态 stale、repeated、mixed generation、publication/site 错误等；normal/-O 各 23 passed，-O 只有预期 pytest warning。actual normal runner 摘要显示 ordinary 四 HMMA 的原生来源通过（raw binding 仍为 0），default / 真 sparse 的 K3/K7 四 capture 分别有 144/336/144/336，总 960 个 input-word → raw-generation 关联。该结果与 source 的四 HMMA × 六 word × 两 program × K 对应。本报告尚未读取取回后的完整逐 binding result 或最后格式冻结身份；最少后续仅核该原件和最终源码字节/AST对应，不要求重跑旧矩阵或设备。
- **ordinary 对应的 functional stage 仍是独立事实。** 本轮可补前述 pipeline gate 的 matrix operands → LDSM → profile raw generation 缺口，但不能仅凭各 word 都来自某个 load 推导三方 group/slot/commit/wait/cut 角色均相同。ordinary 的 raw generation 明确未授予，原 CTA publication / reuse 角色、非空 future group 在对应 compute 阶段的关系、剩余三个 P2R 控制锥与 recorder 存储隔离仍按原范围分别处理。
- **它不是硬件活动证明。** A/B 原生 register 来源和原 wait 的 ready checkpoint 不提供 tensor physical completion / busy、独占 source cost、精确 source iteration identity，也没有解码隐藏 scoreboard；这些未被提升，不构成本工具新增交付要求。

## Optional

当前没有额外必需实现改动。保留本规则的 single-group / fresh-load / unique-generation 限制与清晰 unknown 即可；超出结构时拒绝相应关联，不按算子名或成功样本挑选放行。

## 最终格式冻结与完整收据补核

已实际读取 `run-075/preflight/receipts-v1` 完整 final matrix / input / bounded-register 结果与 terminal、steps、fixture 原 stdout。45-member archive 的 SHA256 核同 `26faaa67e10cdb0b1e174d33432367674cd5550ca59df53c478d3006fa0af214`。六份最终源码均与 `tested-source` 逐 bytes 相同；最终 matrix helper / tests 与初审版本 AST 相同。runner 除格式外，把所有 shared-load site 的 status 检查提前到 function 筛选之前，属于保守拒绝范围的收紧，已在本次 final actual 执行。

| 最终文件 | SHA256 |
| --- | --- |
| `native_pipeline_relations.py` | `5fcac896218618252d1c89946ecc6d597389f53135fb065182b018528e27f4ba` |
| `test_nvidia_pipeline_relations.py` | `7bd2c5eb98c8b9991b11d2d7fcbda9e7a7473224a1af9e5028d46cf799a4c26c` |
| `p01_nvidia_pipeline_inputs.py` | `9175ddeb9bc13722fb78971529a9c6c0b639c5ff6773fa201608416dd0f1385a` |
| `native_matrix_inputs.py` | `ffb2e4dd1a4056bfeaa894a9dbeb5be85e96f59c7de7c3acbd9d2965331bc8f2` |
| `test_nvidia_matrix_inputs.py` | `91ac8ec9cdf35d78aa31b3997f9390e14ace23f90dc8f459ad11a4d2401e4f09` |
| `p01_nvidia_matrix_inputs.py` | `fb7bbb6a35c88a7caccb2b2f725905474a8cc6a98ccd8b2c9c34d7f7de0012c0` |

`final-suite-v1` whole terminal 0 / 16.844s；48 fixtures（25 输入、23 matrix）normal/-O 各通过，-O 仅预期 pytest warning。actual matrix step 0；完整结果确有四 capture 的 144/336/144/336，共 **960** word→generation 绑定，以及 ordinary 四 HMMA 的 native word origins，ordinary raw binding 仍 false。初稿“完整逐 binding / 最终源码尚待核”的有限 gap 至此关闭。此 qualification 代码运行于已安装 runtime 之上，未改产品 runtime；没有新增 native、设备或数学资格主张。

### P2R 与独立否定性质

补读最终 helper:48–59 / 117–130 和新增 fixtures。仅精确规范 `P2R Rdest,PR,Rsrc,0x00..0x7f` 接受保守源全集 `P0..P6`，同时保留 merge register 与执行 predicate；未知 packed 形式仍拒绝，不按 mask 精确选谓词。`P6` 经 HMMA 转换及 merge 直接携带 HMMA 的两种语义负例均保留 forbidden，不能用低 mask 漏读高谓词。

已核 final input CLI **仍实际退出 1**，总体 status 仍 unverified；default 5360/9264/10976 各有入口未知 `P3..P6`，没有伪造完整输入定义。`bounded-register-result.json` 另列 **26/26** explicit register cones 的遍历完成、无本函数 HMMA/clock result definition 路径，`input_values_fully_verified=False`、`through_memory_dependencies_verified=False`、ordinary preservation false。

这两个事实可以同时成立：入口符号未定义，不会自动成为本函数生成的 HMMA/clock 定义；在保守源全集、所有 CFG reaching definitions、未知/预算超限拒绝的前提下，可以单独排除**本函数显式 register 数据路径**，无须把入口值定义完整。此有限性质没有关闭 through-memory、隐式 scoreboard 或物理 completion 边，也没有自动建立整个 pipeline gate。当前新增字段和原件范围一致，未发现具体缺陷。上文“另三个 P2R 控制锥仍未闭”的表述现在只适用于输入定义完整性；对于这个更窄的本函数 register-result 路径性质，三者亦已列入 26/26 的实证范围。其它原 functional-stage / cut/reuse / ordinary 关系缺口保持独立。
