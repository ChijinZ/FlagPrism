# R084 GCU relative record tail：有限独立 review

此模块只检查 caller 提供的有界 straight-line tail 中，人工指定 reader 入口寄存器到相对 end 字段的传值。它未接自动入口，也没有证明 MMIO、ring 分配、begin/site tuple、observer、region 或 loop。本次不将它升格为 source boundary 或 whole-goal 资格。

## 阅读及身份

完整阅读 `Debugger/python/flagtree_debugger/gcu_native_values.py`、对应测试、实际 runner 和 v1 poll/input。未读 peer，未执行 import、测试、产品、SDK、数学或设备。

初读 helper SHA256 为 `83bd8389d3ac1ee205e1ab136e1bc22f1281820297a247d4e11469927f9f6cea`、测试为 `e2600d7f7462fa523347398e8b4fd9f844ebd44ae82a49e0b6e459e28fe8baaf`；随后有限复核更新版 helper `6a7eb55cefb6f7ac271037e7aa8a61e2f200723444a5e260a522a8f761701673`、测试 `b9c55096a8d51a8c87e7d8147024b1353b61812f43a97aa9db10e67e9e2355d2`。以下原缺陷保留初读事实，修正进度单列。请求 GPT-6.1-Sol / xhigh；实际 resolved 型号/档位未暴露，记为 unknown。

## Confirmed major：相对未对齐 store 可覆盖字段却漏掉

初读 helper 140–147 行只按 store 起始 offset 更新 `fields`。在正常 fixture 的末尾加 `l.st.w r0,[r7,0x19]`，它与 end-low/high 的字节范围重叠，但成为独立 offset 25；原 offset 24/28 的正确值仍保留在 map，因而预期字段检查可通过。不能将未知的 native 未对齐行为当成保证不影响字段；应保守拒绝。

更新版 157–160 行要求所有与 record base 同一符号部分的 word store 相对 offset 四字节对齐；原有“不同符号表达式可能 alias，因此拒绝”规则保留。这覆盖上述具体漏项，无须一般 alias 或完整存储模型。新增 `unaligned_overlap` 保留原正确字段后追加偏移 0x19 的 store，确实针对原 false-pass。源码原因已覆盖，新执行闭环仍待 matching 收据。

## Confirmed minor：用历史 magic store 定位却未核最终 magic

初读只找唯一写入 magic 常量的 store 来定位 base；在正常尾部再写 `r0` 到 `[r7]`，magic 已被覆盖却仍可返回成功。即使 end 四字段保持正确，也不应把已失效的 record marker 当最终有效 anchor。

更新版 165–166 行检查最后留在 offset 0 的值仍是 magic，新增 `magic_overwrite` 与这个原因对应。它不扩成检查所有 header/seal 字段；其它字段依旧由原 ABI/decoder 负责。

## 已收紧的边界与源码判断

未知入口值始终为符号；地址仅在 affine modulo-32 表达式完全具有相同符号部分时求相对 offset，任何不同符号部分的 store 均拒绝。没有把“表达式不同”当作“不 alias”。loads 返回 PC/地址绑定的新符号，不会把未知内存值猜成 reader；无法证明的 spill→reload 等形式可能保守拒绝，不能据此自动连入资格。

加法、左移和线性项均按 native 32-bit modulo 计算，符合本组件声明的位向量模型，不与 LLVM nsw/nuw poison 混用。更新版对 `c.li`、`l.ldi16.s/u` 给出不同的 signed/unsigned 范围；`ldi_hi` 需要已知低字和有界 high immediate。非线性 mask/shift 的未知结果保留为符号，仅原高字与准确 `0x3fff` 的 mask 可成为 `end_high_masked`。本有限修改未发现新的具体整数等值误授。

原版把同 packet 指令按 PC 顺序串行解释，但 packet forwarding 未作为已证输入。更新版 85–95 行保守拒绝同 16B packet 的 RAW 和重复目的寄存器写；把 store source/address、显式源和 `c.add` / `ldi_hi` 的隐式旧目的均计入读取。WAR（先读取/存旧值，再写寄存器）可保留，因为 serial 与无 forwarding 的读旧值解释一致。这个有限规则避免依赖未知 packet forwarding，不要求解释全部 packet ISA。

`same_packet_raw` 负例把 mask 常量形成与 mask 使用放入同 packet，旧 serial 模型会通过，新规则应拒绝。PC 顺序/唯一性、512 instruction 上界和未知 opcode 拒绝仍保留。此处只校核输入 list 的值流，不把 PC 有序当作完整 CFG 或完整指令枚举证明。

## 一个最小测试验证缺口

当前 `signed_immediate` fault 将 mask immediate 改为 `0xffff`，但仍只要求任意 `ValueError`。旧模块虽不检查 signed immediate 范围，也会因这个错误 mask 不能产生 `end_high_masked` 而最终拒绝。因此该负例不能证明新 range guard 被命中。

最小修正是对这一 fault 单独要求 `Native immediate range` 的具体错误（或等价的直接范围回归），其它 fixture 不必扩大。它是新 guard 的测试针对性问题，不是新数学/ISA 门，也不指称修正版模块仍有 protected-field false-pass。

## 实际 v1 证据及未证范围

读取 `gcu-record-tail-poll-v1.json`：实际 terminal 0，`wall_ns=515631322`（0.515631322 s），180 秒预算；原 ELF `7d56f25f...f00500`、native `a4423a38...015e8b`。runner 在指定 `0xabce..0xb05a` 内逐 instruction 显示 bytes 对原 ELF executable section 比较，共 219 rows，得到 word6/7/8/19 stores `0xadea/0xad2a/0xad8a/0xaeca`。

input-v1 归档 SHA256 为 `4fc7a964123ab1575dd4e01307ac9b5dd6bdab530e989eb46484b9219cea5ad1`。runner SHA `7f2f802b68a6f159a6448d50d9ec404e7d6e1abf312e314a9696c94d782122f5` 匹配 terminal；测试所加载的 package copy 和 actual runner 加载的 root copy 都为旧 helper `83bd8389...`，不存在两份版本混用。runner 先执行 normal / `-O` fixture，任一失败即停止，再核原对象；因此原终态支持原 14 项及该 tail 成功，**不能用于新 `6a7eb55c...` / 18 项执行闭环**。

该实证准确保留 `actual_reader_inputs_independently_qualified=false`、`manual_actual_tail_selection=true`。`r13/r9/r5` 是本次人工确认的 tail 入口输入；自动入口、MMIO reader、实际 ring/sequence 来源、incoming tuple 和整条 non-full path 完整性不由本模块证明。输入列表还必须包含声明 tail 的全部有关指令，不能从同对象抽一个“只有正确 stores”的子集；字节相等本身不证明列表完整。此为原输入合同，不要求本组件重做全部 decoder/CFG。

## 有限结论

更新版源码覆盖原 unaligned-overwrite / magic-anchor 问题，packet 与 immediate 收紧方向正确；本次小修复未发现新的具体模块 false-pass。只需修正上述单项 negative 的命中要求，并取得同一最终源码的 normal / `-O` 与原 219-row tail matching 收据。无需重跑 SDK/设备/数学，也不提升 reader/MMIO、ring、begin/site、region/loop 或 whole-goal 资格。

## 最终 matching closure（record-tail-v3）

以上保留原问题及中间进度；截至本追加，本次 relative-tail 的两个已确认缺陷和单项测试针对性意见均已闭合，没有剩余的本范围 confirmed blocker/major/minor。

实际读取最终源码、`gcu-record-tail-poll-v3.json`、回收的 `gcu-receipts-v1/runs/record-tail-v3/output/{normal,optimized}.log` 和 `result.json`，以及 `gcu-hooks-v1.json`。最终 helper SHA256 为 `45b30938a02a7c10dfef787cf25cf10193a3352b2e957843f501eb2753253e88`，测试为 `45db43d26a72903b0a86f6005044b3e1320dcf9927a238200dbcd90cde282474`；当前文件与 input-v3 的 root helper、package helper、测试分别逐字节一致。input-v3 归档 SHA256 为 `631470e9308548abd9134c5d5a1d5384e801aec535fecd24fd60719e29ecd172`。input-v2 与 input-v3 的 helper AST 相同，符合仅格式调整的有限说明。

最终 helper 174 行拒绝未对齐相对 word store，180–182 行检查最终 magic；对应 `unaligned_overlap`、`magic_overwrite` 反例保留原正确 stores 再覆盖，覆盖原具体 false-pass。测试 100–106 行已对 `signed_immediate` 单独要求 `Native immediate range`，因此不能再由后续 wrong-mask 拒绝误充这一 guard 的验证。原测试针对性缺口关闭。

v3 实际 terminal 0，`wall_ns=515362947`（0.515362947 s），预算 180 秒。完整 stdout 为 normal / `-O` 各 **18 passed in 0.02s**；`-O` 另有预期 pytest assertion warning。实际结果绑定上述最终 helper 和同一原 ELF `7d56f25f70633d7f0d813a78e8ded073b884a4356d940a4cb48c710794f00500`、native `a4423a389544cde04466ad381de272754c8c79d3860eabc48dd86898a9015e8b`；219 条原 tail 指令仍返回相对 word6/7/8/19 的 stores `0xadea/0xad2a/0xad8a/0xaeca`。ruff、yapf、check-ast 三项实际收据均为 0，收据 source SHA 与最终文件相同。本次只读复核没有自行执行测试、导入组件或运行 SDK/设备。

闭合结论仅为：在调用方提供的完整有界 straight-line tail、指定入口 reader 值及已绑定 executable bytes 前提下，此模块可核验相对 end 字段传值。它仍为 **source-loaded 内部组件**，未接自动入口，未主张 normal-installed 产品闭环。实际 reader 输入仍人工指定，`actual_reader_inputs_independently_qualified=false`、`manual_actual_tail_selection=true`；自动 reader、三入口及动态 site/begin tuple、ring/sequence、source/loop 资格均未授予。结果中的 `reader_valueflow_qualified`、`source_region_qualified`、`ring_allocation_qualified`、`incoming_begin_site_qualified` 保持 false。本追加不关闭其它 whole-goal 门，也不新增门。
