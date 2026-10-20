# GCU compiler-owned debug-value provenance：有限可行性审阅

**这条路线合理，且本轮六变量 CPU 探针已经实证 SDK 接受和导出能力，当前没有已知根本不可行点。** 该路线有望把已标记 SSA 值经寄存器分配、copy 和 spill 后的位置交给编译器记录，从而减少手写 native 标量/栈值流。现有成功尚未证明相关 store/stack 检查点都有正确、可用的位置范围，不能用 `dbg.value` 单独证明 record store 或完整路径。

本文是实现路线判断，没有新增产品验收门，没有实现、导入、执行测试/SDK/设备或重放数学。未读 peer。请求 GPT-6.1-Sol / xhigh，实际 resolved 型号/档位未暴露，记 unknown。

## 实际依据及当前明确限制

阅读当前 `GcuDebugScopes.cpp`（SHA256 `fcc4182732aa08ba87b46701ac6a8723c4ab3f67afff04469e4a0b6f49a9bda9`）、对应 header/CLI、`gcu_timeline.py:preserve_native_locations`、Enflame make_llir/make_fatbin patch、`GcuNativeLocations.cpp`，及 R065/R067/R068 保留的 SDK 参数、DI API 和 CPU codegen 脚本。另读 R083 实际 `0.llir` 的 `^bb16/^bb17` 和 DI metadata、两原 ELF 的 section headers，以及新启动的 `probe_gcu_debug_values_v1.py` 和 `gcu-debug-value-schema-v1.json`。查阅的公开依据仅为 LLVM/MLIR 官方资料；以下可行性推断与本地实际事实分列。

1. **当前是行表模式。** `GcuDebugScopes.cpp:36` 调用默认 scope pass；保留的实际 `0.llir:1841` 明确是 `emissionKind=LineTablesOnly`，`isOptimized=true`。原两 ELF 有 `.debug_line` 和很小的 `.debug_info`，没有 `.debug_loc/.debug_loclists`。这些原件没有为新增人工 observer 变量提供现成 location 列表。已有 scope 输入再调用 pass，不能不经核验就假定 CU 会从 LineTablesOnly 变 Full。
2. **已有桥只准 location 改动。** 68–70 行要求原 non-location IR 相同，96 行要求 walk operation 数相等，98–106 行只把 location 复制到第二个 opaque parse。往第一个 module 增加 debug op 后直接复用这段 transfer 会被正确拒绝；把第一 context 的 SSA `Value` 直接用于第二 context 也不是合法方案。这是扩展点限制，不是现有行表实现的 bug。
3. **必要 public schema 已存在。** R068 保留的 header 含 `DILocalVariableAttr`；R086 新 schema 快照明确含 `LLVM_DbgValueOp`、`varInfo`、`locationExpr`。该 builder 还明确在无 current debug location 时返回而不生成记录，因此新增 op 必须具有所属函数的有效 local scope/DILocation，不能给 block argument 用一个 unknown loc 后期待导出。schema 文件 SHA256 为 `53cfa3565dfd7d7d9146d59fa8c41dcdcdaa65357a72296f5e5830cf5ef744ef`。实际 SDK parser/translator/backend 是否全部支持及保留它，仍应由能力原型观察。
4. **现有真实 SSA 已足够作一个有代表性的例子。** `0.llir:480` 的 `^bb16` 四个 block arguments `%306/%307/%308/%309` 分别传动态 site、begin low/high/identity；`%310` 是 i64 end clock，`%314` 是 i32 end identity。`^bb17` 中实际字段 stores 使用这些 SSA，以及 `%310` 的两个 i32 派生字 `%311/%313`。无需先构建完整 native ISA 解释器才有可命名的 producer/merge/use。

官方 MLIR 的 `llvm.intr.dbg.value` 正是“值—局部变量”的关系接口；LLVM 的变量跟踪可跨寄存器分配及 spill 形成位置范围，也允许优化后不可用。它提供了所需的技术机制，并不承诺某个 vendor 后端或每个 PC 都有可恢复位置。[MLIR LLVM dialect](https://mlir.llvm.org/docs/Dialects/LLVM/#llvmintrdbgvalue-llvmdbgvalueop)、[LLVM 18 source-level debugging](https://releases.llvm.org/18.1.8/docs/SourceLevelDebugging.html#how-variable-location-metadata-is-transformed-during-codegen)。

## 最小 CPU-only 原型路线

**先只回答“正常 SDK 能否导出这些值的位置”，不先改产品。** 复用一份已保留、SHA 绑定的真实 `0.llir` 副本，在同一函数里创建独立 observer-value namespace 的 `DILocalVariable`，保留现有 source/clock 坐标 marker。变量 ID/名称绑定函数、角色与真实 SSA 定义/merge/use，不用行号或物理寄存器号当身份；变量类型准确为 unsigned i64/i32。共享 site 必须标为动态 site 值，不能因共用 end 的 DI 行是 site1 就把整条路径改称静态 site1。

对尚无 scope 的输入，可用明确 Full 的 scope-pass option；对已含 LineTablesOnly 的副本，要显式替换其所引用 CU 并在 SDK roundtrip 中确认 Full，继续保留真实优化标志。分别在 producer 后及 merge block 开头插入 `dbg.value`：本例先只需上述四个 block arguments、end i64、end identity 共六个。block argument 的记录引用实际 merge SSA，不能仅在各 predecessor 标不同值后假设 debug tracker 会替它创造一个正确合并。

然后沿已用过的真实 CPU 链运行：SDK opt 验证并序列化，再以现有 `gcu-compiler-compile --device-only --is-triton-backend --arch=gcu300 --toolkit-path=/opt/triton_gcu` 正常优化流程产生新 fatbin/ELF，用 `readelf --debug-dump=info --debug-dump=loc` 或已有 LLVM DWARF 库检查。输入、实际工具、每一步 returncode、输出 ELF、各变量 DIE/location 的 SHA/范围都绑定；parse 接受、变量名称存在、可用寄存器位置、可用 stack 位置应分别报告，不能只看整个 diagnostic runner 的 terminal 0。SDK linked IR/native dumps 保持原私有留存策略，不放入 Git。

本次已实际阅读的新 `probe_gcu_debug_values_v1.py`（SHA256 `fcae4899fa282e1048cb1c63bbdf947cea881b24267025e343dbd2011c2b12bd`）正是这个六变量的有界能力探针：固定实际原输入 SHA，移动属性 alias 以供非-location 使用，显式 Full，未改 producer/store 数学，只新增六个 debug op，然后做 SDK parse/codegen/readelf 与 executable bytes 比较。随后实际读到其成功 poll，具体范围见下节；它把 `debug_value_provenance_qualified=false` 保留得正确。这个脚本是单原件探针，硬编码 `%306...%314` 可用于此诊断，不应照搬成通用产品选值器。其名称/全局 location 计数只判能力线索，尚未证明每个角色的可用范围或 spill 绑定。

若六变量确有位置，再只补同一原件的实际字段-use SSA：在原 `^bb17` stores 前描述 site、begin 两字/identity、end 两字/identity；同时记录它们与实际 producer/phi 的 IR use-def 关系。优先观察现有真实 spill，不必制造新的压力矩阵。若 i64 被拆为 DWARF pieces 或不可恢复，直接采用实际 ABI 已有 i32 两字的 debug 描述，并保留它们来自同一 i64 的已知 trunc/lshr 关系；不能按名字猜 high/low 拼接。

## 已到的六变量 CPU 能力证据

实际读取 `gcu-debug-values-poll-v1.json`：terminal 0，`wall_ns=1116259564`（1.116259564 s），180 秒预算，runner SHA 与上述已读脚本相同。三个真实步骤 SDK parse、正常 SDK codegen、readelf 均 returncode 0。原输入 SHA256 为 `6b8b2e1a95808ec6f924dac1324f449b44f5177e89f5d5e11de6ade3511eb593`，新增 debug 信息后的输入为 `c0552bc9b09b614ef98f73e8bb7cad06d1f0d823bc0875286514f47e9d5848fb`；新 ELF 为 `ed55bc986ddb8c39f17c4f88a66e0f95fc723041b0c9b7e47ca3a08777587796`。

结果保留全部六个变量名称，计到六个 `DW_AT_location`、四个 register expressions，`DW_OP_fbreg` 计数为零；runner 比较的全部非空 executable section bytes 与原 ELF0 相同。它关闭了“实际 SDK 是否会接受并导出这些 observer 变量”的能力不确定性，不只是借用公开文档推测可行。

本次尚未取得本地完整 `dwarf.stdout`，故没有核各 DIE 的具体 expression、PC 半开范围、piece 或 frame base；全局六个 location 属性也不等于六个变量在所需 PCs 都有有效位置。零 `fbreg` 不能证明栈位置完全没有或不被支持，仍可能有其它表达式形式。当前事实无需新能力/数学矩阵，后续只需读已有真实输出，并在同一原件上扩大到实际字段-use 即可。该 CPU 结果没有修改、执行或重新资格化旧 loaded ELF；所有 provenance/product/source 资格保持 false。

## 未来接入当前桥的最小工程改动

保留同一 immutable input snapshot 和 opaque vendor properties。先在没有新增 op 的两个 parse 间，按原 operation/result 或 block/argument 序号建立对应，再在 opaque 原模块用对应的原 SSA operand 插入仅允许的 debug ops；DI attributes 经已验证的跨-context 序列化/重解析转移。剥除本工具新增的明确 debug-op 集合后，原 non-debug operation、operand、CFG 和 vendor property 的 generic core 必须回到原快照。不能只删掉原保护检查或把整个新 LLVM printer 的输出当原 SDK IR。

这可做为独立 prototype mode，不必改变现有 `--debug-scopes` 的 location-only 合同。未来若集成，变量格式/选值规则和相关 tool bytes 应进入已有 compiler/cache 身份链，不能让旧无变量对象冒充新映射对象。本轮没有要求实现或重新审计 cache。

DWARF reader 可复用现有 LLVM Object/DWARF 依赖，输出有界的 DIE、section、半开 PC range、表达式和状态。先只支持观察到的 register、明确 frame-base+offset、constant 及必要 piece 形式；无 location、范围有洞、冲突、复杂/未知表达式都保留 unavailable。不能把未知范围用前一条位置填满，也不能把 DWARF register number 直接假定等于 `rN`，或把 `DW_OP_fbreg` 的 offset 直接假定等于 native `sp+offset`；只需核实际目标的寄存器编号/`DW_AT_frame_base`，不需建立一般 alias/ISA 系统。

## 这条路线能补什么，不能替代什么

工程推断：如果真实 SDK 在相关 PCs 给出这些 SSA 的有效 register/stack locations，它可把目前费力的“begin/site 值经任意复制和 spill 到哪里”收敛为编译器拥有的位置映射，加上少量实际 load/store 及字段地址核验。这个范围适合复用现有 relative-tail、direct-edge 工具，而不是重写 SDK 标量 ISA。

但 `dbg.value` 描述值的位置，不以 store identity 绑定写入副作用；LLVM 为 store-assignment 绑定另有机制，不能仅因两个变量名或寄存器位置相同就认定字段已写对。[LLVM assignment tracking](https://llvm.org/docs/AssignmentTracking.html)。本原型无需强求 SDK 支持较新的 assignment-tracking 格式：保留真实 LLVM store operand/地址与小范围 native store 检查即可。marker 行表也不自动给出 store 的精确机器 PC。

同一 machine tail 被多个 IR 路径合并时，某个分支独有的变量可能在 merge 后不可描述。要么保留这个 gap，要么对“当前记录的某逻辑字段”在所有有关原 IR store/use 处作正确的赋值描述；不能把一个分支变量在 shared PC 的位置外推到其它路径。尤其 R086 已发现 `0x9720→0xabd0` 另一个入口，必须继续由实际 origin/CFG 与该路径的字段 SSA 对应覆盖，DWARF 变量不会自动消除这条义务。

因此 root 提出的“各真实 record 字段使用同一动态 role DI variable、clock 样本另按 site/phase 区分”是可行的下一步：每个字段 store/use 前把该角色更新为它实际消费的 SSA，merge block argument 也显式描述；IR 表记录这个角色来自哪些 producer/phi。它应覆盖所有实际记录路径，不限 `^bb16` 三入口。角色是同一调试变量的多次赋值，样本身份另行保存；对尚未赋值的当前记录角色终止旧 location，或只在有本次 SSA 描述覆盖的检查点取值，避免把上一条记录留下的值当作本次来源。无法跨 merge 描述的项仍 unknown，不强求 metadata 保活。

debug value 也不是保活/阻止优化的执行屏障；本路线应接受 unavailable，而不是为追求 coverage 添加 volatile store、额外时钟或强制 O0。新 CPU ELF 仅用于能力判断；即使 executable bytes 相同，仍不能把新增 DWARF 直接嫁接成旧 loaded capture 的完整证书。后续产品若产出新对象，继续按原身份/加载范围绑定，不在本轮要求新的设备回放。

**有限结论：没有观察到根本不可能的接口障碍；有两个明确的现实现前提要改——Full variable emission 与允许仅 debug-op 扩展的安全跨-context 桥。** 当前未证的是实际 SDK 正常优化后的 location coverage/target frame-register 描述和字段对应，不是要求新的源独占耗时、完整 ISA、精确 issue order 或 hardware busy 证明。本路线可减少现有值流缺口的实现负担，不能单靠 DWARF 关闭 source-region 次序、loop、ordinary pipeline 或 whole-goal。

## 三份实际 CPU probe 的最终收束

本节更新此前“未读完整 DWARF”和原型建议的进度。已只读核验 `gcu-debug-values-details-v2.json` 的完整 v1 DWARF/allocated-section 表（SHA256 `8460f7b3e751a728b741e9edc5af839c427ac3ac5524c73163c48f28817d0646`），v2 poll 与 failure 的头部诊断，以及 `probe_gcu_debug_values_v3.py`、v3 poll 和 `gcu-debug-values-details-v4.json` 的完整 v3 DWARF/section 表（SHA256 `15f73d04584f2d8af8b022933c6b33288c7f8cc1f71584071a098407c42ab97e`）。没有执行新探针、设备或 SDK，也不建议本轮追加探针。

### v1：部分真实位置可用，i64 ticks 的表达式不足

通过 `DW_AT_abstract_origin` 对应变量名称及 location-list offset，原输出确实给出：

| 角色 | 实际 DWARF 位置 | 半开 PC 范围 |
| --- | --- | --- |
| site | `DW_OP_reg15` | `[0xaaa0,0xabd0)` |
| begin low | `DW_OP_reg23` | `[0xaaa0,0xabd0)` |
| begin high | `DW_OP_breg2 + 172`（`0xac`） | `[0xaaa0,0xabd0)` |
| begin identity | `DW_OP_breg2 + 140`（`0x8c`） | `[0xaaa0,0xabd0)` |
| end identity | `DW_OP_reg5` | `[0xab10,0xab20)` |
| i64 end ticks | `breg9+0; constu 16383; and; lit0; or; stack_value` | `[0xab10,0xabd0)` |

两个 `breg2` 表达式没有 `stack_value`，描述的是相应地址上的 i32 变量位置，不是把地址数值当字段值。这些具体 spill 候选与原 native `0xac9a: ld.w r23,[sp,0xac]`、`0xaf5a: ld.w r14,[sp,0x8c]` 及后续 word5/18 stores 相吻合；begin identity 应以 **`0x8c`** 为准，不能沿用 `0xbc` 的人工猜测。正式位置 reader 仍应固定实际目标的 DWARF register2 与 native `sp` 的对应；本例也显示“零 `fbreg` 计数”并不代表没有 stack location。

**i64 ticks 不能接受为完整 clock 值。** 原 native 的 `r9` 是高字，完整返回值需要低字以及高字左移 32 后拼接。实际 debug expression 只有 `(r9 & 0x3fff) | 0`，既没有 low 来源，也没有 `shl 32` 或等价 pieces，虽 DIE 类型为 8-byte unsigned，也不足以表达完整 ticks。这是该 SDK debug salvage 的具体可靠性风险；不能因变量名和 `DW_AT_location` 存在就接受。它不证明原 recorder 的 runtime 数值有错：原 executable bytes 相同，已核 native reader/record 值流是另一个证据链。

四个 begin/site 范围都在 record body 另入口 `0xabd0` 处终止，end identity 更早终止；原字段 stores 在其后。不得将这些范围外推到 stores，也不得据它排除 `0x9720` 入口或覆盖完整记录路径。

v1 allocated-section 比较的修正版把 `SHT_NOBITS`（type8）的 `.bss` 只按 logical metadata 比较，不再哈希不属于该 section 的 file slice；这一修正正确。修正表中旧新 11 个 allocated sections 的地址、type、flags、size 及所有有 file contents 的 SHA 均一致；`.bss` 地址 142,512、size 1,572,352，SHA 为 null。先前 NOBITS 错误切片得到的 all-alloc false 应废弃。这个结果加强了 v1 是 debug-only CPU 变体的身份依据，仍不是给旧 capture 嫁接新 DWARF 的完整产品资格。

### v2：直接给 i32 trunc 结果加描述，实际 SDK codegen 失败

实际 poll 的 diagnostic runner terminal 为 0，耗时 0.966444326 s；**它不代表编译通过**。结果明确 `SDK_parser_accepted=true`、`SDK_codegen_accepted=false`，真实步骤 parse 0 / codegen 1。failure 头部是 `LLVM ERROR: unsupported opcode found in DIExpression`，发生在 `gcu-compiler-llvm-spirv` 的 `SPIRV::LLVMToSPIRVPass`。本次没有把后续私有 linked IR dump 全量输出或写入报告。

这份变体新增 `%311/%313` 的 end low/high i32 描述，实际未走通；因此此前“可改为 i32 两字描述”的建议只能保留为已试失败的具体路径，不能继续当作 SDK 已支持的补救。现有诊断没有指出具体是哪一个 DIExpression opcode，不推测其原因，也不泛化成所有 i32 debug value 都不支持。

### v3：动态字段角色可导出部分位置，但改变代码且 join coverage 仍不完整

已读 v3 selector/runner（SHA256 `0865f65b90fe2ac4ff6efd1158fe234374570cc5efe3e7a4bba76bae9080e960`）。它只用于这个原件：从实际 `%77` ring GEP、常量字段 offset 和 magic 找十组完整 32-word records，在四种 begin/site stores 前加入同一 role 变量的 40 次描述，不添加 end-trunc 描述。它没有成为通用产品 parser，不能据本诊断 selector 直接宣称任意 record 都能自动识别。

v3 terminal 0，耗时 1.116693145 s，真实 SDK parse/codegen/readelf 均 0；四个变量名称、四个 location attributes、28 个 register expressions 被导出。新 ELF SHA256 `ab8e465985e403f642d1ca31f712b69dd31cc6fb23f8c756b5a71a2890358a22`。原 IR producer/数学没有改写，但 **executable bytes 不同**：`.text` 从 138,896 增至 139,072 bytes（+176），SHA 也改变；后续分配地址与 relocation 等表随之变化，`.bss` 从 142,512 移到 142,688。不能把“只加 debug 信息”当作 native allocation/布局必然不变，也不能把该对象的 PC/location 嫁接到旧 loaded ELF。

完整 v3 DWARF 确实产生多个常量、寄存器及 `breg2` 区段，比只给单个 join 加六变量更丰富。但共同区段的四个角色仍仅在 `[0xabe0,0xabf0)` 有描述：begin low 为 r23，begin high 为 `breg2+176`，begin identity 为 `breg2+144`，site 为 r15。地址及 stack offsets 已属于新对象，不能套原 `0xabd0`、`sp+0xac/0x8c`；这些短范围也尚未提供后续所有 stores 的完备覆盖。40 次 debug 描述不等于 40 个已核的最终字段写入。

### 最终有限结论与最少下一步

三份原件足以界定当前路线：**SDK 能导出部分真实 begin/site 的 compiler-owned 位置，包括 stack 地址；但 i64 salvage 不完整、这组 trunc debug 触发 SPIRV 编译失败、动态 role-use 描述改变代码且共享 join 后仍有 coverage gap。** 因而它尚不是可直接替代现有 finite native 路径证据的产品捷径；这也不是对全部 debug-value 路线的否定。

本轮到此停止能力探针。保留已发现的 begin/site 位置作为有界 spill/寄存器候选，用原 IR 的真实 phi/store 来源与已有小范围 native/CFG 证据核对；end 继续使用已通过的 finite inline reader/relative-tail 路线。无法覆盖的入口、区段和值仍 unknown，而不是再让 metadata 计数授予资格。本报告不要求 SDK 修复、更多 ISA、更多数学或新设备矩阵；`debug_value_provenance_qualified`、source/loop、normal-installed 与 whole-goal 资格均保持 false。
