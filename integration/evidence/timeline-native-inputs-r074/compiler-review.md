# R074 finite compiler / qualification review

结论：支持把本轮代码作为**有限、允许 unknown 的 qualification diagnostic** 交付。先前指出的输入宽度、入口、PR 漏读及对象身份绑定问题，在本次受测源码中均已修复；当前没有确认仍然存在的 blocker / major / minor。当前实际结果是 partial-unverified，不能把旧版本的全 clean 结果继承到新版，也不能据此关闭 ordinary pipeline preservation。

本报告只评本轮 qualification helper、调用脚本及 retained-raw prefix 诊断，不评整个 goal，不改变已独立核验的 matrix issue / native loop / origin 事实。最终 qualification commit 为 `d557202fb2eb56cf056a72d0eecd341c503fdbcf`；runtime 未变。实际 resolved 模型未知。

## 阅读与复核范围

实际逐行阅读 candidate 的 `tests/timeline/native_pipeline_relations.py`、`test_nvidia_pipeline_relations.py`、`p01_nvidia_pipeline_inputs.py`，以及它们调用的现有 `_predicate`、`_predecessors`、`_destinations`、`_branch`、P2R normalizer / object binding 的相关代码。复核了原 design §0.6、§8.14、ordinary baseline 段落和 testing §8.7；未读 peer 报告。

实际读取 `run-074/preflight/pipeline_relations_v2.py`、原结果、ordinary PTX 机制摘录、`p2r-v1.json`、poll v3/v4/v5 和完整 `receipts-v1` 的 terminal / steps / normal、optimized 结果，随后补核 `optimized-fixtures-v1` 的 terminal / result / 原 stdout、stderr，以及提交内 `timeline-native-inputs-r074/README.md`。归档共 50 members，SHA256 核同 `0c2f2bea3c0afb4d975bb19c50ac9c25af521397ff2bacc934be979d04156fbb`。当前三份 qualification 源码分别与 `tested-source/native-dependencies-input-v4/` 逐 bytes 相同：

| 文件 | SHA256 |
| --- | --- |
| helper | `2541b93809294d3d1f0cd23828e0a5cdb2530843c9c4a4c18eb7cd4a8b21ed6d` |
| fixtures | `016de7d043a8cbcb228ccc95bcd68f8a6052f83a450a4afc62c335d1e77a0d67` |
| actual-input runner | `76f9a5c7ad1e804a5d71d853de257e75f22238e5770d1a0b942e557063fdddd5` |

prefix 源码也与其受测 `run.py` 逐 bytes 相同，SHA256 `436f3e8cbacc50fa59a65aead16cdc653e533d3aaa1c81b125367f96abf6b2d7`。本次只用 stdlib 读取/核 hash；未执行这些检查器、pytest、产品 import、编译、SDK、设备、模型、数学或 UI，没有连接服务器，也没有修改实现。

## 已确认问题及修复状态

以下是本轮 source review 中发现、已在当前源码修复的缺陷，不是当前尚存问题。

1. **Major：隐含高 word 可漏掉真实依赖。** 原 `sources()` 只展开部分 `.64`，会漏 `ISETP.*.S64` / `UISETP.*.U64`、`UIADD3.64`、`SEL.64` / `USEL.64` 的输入高 word；`.WIDE` addend 带 `.reuse` 也曾漏高 word。例如低 word 为常量、高 word 来自 HMMA 时，原检查可能报告 clean。当前 helper:48–59 对这些实际家族补齐输入 pair，tests:105–165 的独立 semantic negatives 保留该依赖。v4 normal 的 20 fixtures 已执行通过。该 source defect 已关闭；没有要求支持未知 ISA 家族。
2. **Major：PR 曾被当作没有寄存器源。** `registers()` 不展开 packed `PR`；原 `P2R` 可能仅追 merge register 而漏 predicate 来源。当前 helper:45–46 对未建模 PR 明确拒绝，tests:169 验证该行为；现有 normalizer 恢复 `P2R Rd,PR,Rs,mask`，没有把 JSON 的 `predicate='PR'` 当执行谓词。新版实际 default 的三个必要控制锥因此为 unverified，说明该洞已关闭，未知语义并未被伪装成 clean。
3. **Minor：seed 恰为函数入口时空 worklist 可假 clean。** 原入口没有 predecessor 时既不入 worklist，也不记未定义 root。helper:73 现在直接保留 seed roots，tests:144 的入口负例已在 v4 normal 执行。source defect 已关闭。
4. **Minor：inventory 与 machine map 的 CUBIN 身份缺少最后一条等值检查。** 原脚本分别核 inventory bytes 和 machine map，但没有明确比较两者的 `cubin_sha256`，可能把某对象标签写在另一对象的指令检查上。runner:85–86 现明确比较，并在 v4 actual 执行经过。不是发现原件实际错配；该绑定遗漏已关闭。

在当前支持的实际指令形态内，没有再确认会放过活跃 HMMA / clock register 依赖的解析错误。遍历按每个实际 use 的所有 reaching definitions 递归，predicated overwrite 保留旧定义，所有 CFG 分支并集而非挑实际成功路径，已覆盖的物理寄存器生命周期不会继续携带旧身份；unknown writer/control、入口未定义和 32768-state 超限都拒绝放行。所有分支和 conditional EXIT 根由 actual runner 独立检查，因此没有只查 copy 数据源而完全忽略控制根。

## 实际结果与 verification gaps

**新版 v4 的真实终态是 1，含义是有限验收脚本因 unknown 拒绝放行，不是应用数学运行失败。** normal 20 fixtures 通过；ordinary/default/sparse 各 3 个 copy 输入锥，共 9 个均 clean。控制根分别 3/7/7，共 17 个，其中 14 个 clean；default PC **5360、9264、10976** 因 `Packed predicate source is not modeled` 保留 unverified。结果总状态及 `ordinary_preservation_verified`、`hardware_overlap_verified` 均如实保留未证。v4 runner 在此停止；随后独立 `optimized-fixtures-v1` 终态 0 / 0.315s，对同一路径的 v4 fixture 执行 `-I -O`，原 stdout 为 **20 passed, 1 warning**（预期 pytest assert warning），因此本 freeze 的 20 fixtures 已在 normal/-O 均通过。未声称新版 actual partial 检查还在 -O 完整运行；旧 v3 的全 clean 不能替代新版 PR guard 结果。本有限 partial 交付不必等到这三个 unknown 被消除。

**P2R 最小下一步（可选补证，不是新增交付门）。** 目前材料仅展示六条 `P2R` 的规范化格式和实际 masks `0x4/0x1/0x2/0x10/0x2/0x40`，不能单靠这些观察独立证明 mask bit 到 `Pn` 的精确选择语义。当前 reject 正确。若以后只闭这个必要锥，可在原 PTX / native 局部 source binding 上确认这一种规范形式 `P2R Rdest,PR,Rsrc,imm`；保留 `Rsrc` merge 输入和执行 predicate，非规范 PR 位置、modifier、mask 仍 unknown。对于已确认的低七位形式，保守追 `P0..P6` 全部可避免先依赖精确 bit 选择；只有确认 bit 语义后才按 mask 缩小到相应 `Pn`。不能把 RZ merge 当作 PR 也无输入，不能将裸 PR 当执行 guard。无须扩展其它 ISA。

**raw prefix 诊断的有限结果成立。** prefix:15–40 用现有动态 group/consumer 模型和实际 raw payload，要求 future async group 已 commit、原 wait 尚未要求其完成、有效源字节非空，且其 shared footprint 与当前已知 consumer footprint 不相交。default / 真 max_sites1 sparse 的 K3 各 6 个 matrix prefixes 中 4 个有 witness，K7 各 14 个中 12 个有 witness；每个 witness 有实际非空 2048B，尾部 drain 没有 witness 没有被偷偷算入成功。只把 wait payload 改为 0、保留 op counts 的反例均不再有 witness。该范围内未发现 checker 的具体错误。

这些结果说明“在这些 recorder checkpoint，存在未被原 wait 强制完成的非空 future group”，不说明该组物理上仍在飞，也不说明矩阵正在消费刚枚举的 shared ranges。`matrix_operand_binding_verified=False` 是关键而正确的限制；`completion_observed_sequence > matrix_sequence` 也不是硬件完成发生在 matrix 之后的证明。所有 stronger flags 保持 false 合适。

## 原 1–4 项还缺的最少事实

这些是既有 pipeline 门的未闭合部分，不是新增矩阵或任意 ISA 框架：

1. **三方的功能阶段对应。** 当前 ordinary 数学 / CUBIN / vendor JSON 和 profile fresh machine map 的身份已绑定；ordinary PTX 摘录也显示 prologue 提交、循环 wait1 / 消费 / body copy、尾部 wait0。仍需在同三对象上把原 group 成员、body copy 的 future-tile 角色、commit / wait 覆盖与实际 CFG 阶段对应起来。不能只由 PC 最近或 op 数相同认定角色相同，也不要求恢复相同 issue 次序。
2. **实际 matrix operands 到共享消费者的最后关联。** 当前 prefix 的 consumer events 是 matrix 前的读事件集合，尚未证明对应四条 HMMA 的 A/B 输入确来自这些 LDSM 输出及其 raw-backed shared generations；也未完成三方原 CTA cut / slot reuse 的角色对应。最小材料是这几个已保留对象的实际 matrix-input uses → reaching LDSM outputs → 已有 shared-read / generation 的局部关联，不是 source-exclusive、任意 kernel 或通用访存证明。
3. **将已有 future-group witness 放回该功能 compute 阶段。** 非空和未被 wait 强制完成部分已有实际 raw 证据；与第 1、2 项关联后，才能称对应 current compute 的静态异步机会保留。不要求每个尾部 drain prefix 有 witness，不把“允许未完成”写成“硬件实际重叠”。
4. **余下的关键输入 / 控制与存储隔离事实。** 新 register-cone 检查已排除全部 9 个 copy 输入和 14 个控制根的 HMMA / clock 结果依赖；default 另三个控制根仍未知。它不追 through-memory def-use，也不授 alias 或 scoreboard 资格；可复用原 recorder allocation / address-space / footprint 与原 tile 分离的实际事实，配合原 CTA cut / consumer-reuse 对应，不需要构造通用 alias 分析器。当前 receipt 不能单独替代这些材料。

未发现本轮材料已经证明某条必须先修改 runtime 的新增 tensor-completion 串行依赖。ordinary 与 profile 的 issue 交错确有变化；是否保持合同所需的静态关键机会仍属于上述具体工程证据缺口。没有新增 copy-before-last-HMMA 门，不要求完整隐藏 scoreboard、硬件 schedule 等价、engine busy 或 measured overlap。本报告不授予 ordinary pipeline、source-region cost 或 whole-goal 资格。

## Optional

无额外必需改动。若暂不补 P2R，可保留当前 source 和明确的三处 unknown，连同 terminal1 原件交付 partial diagnostic；不要把历史全 clean 或只通过的 copy 锥压缩成整个 pipeline 已通过。
