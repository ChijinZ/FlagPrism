# GCU G1：最短自动规则接口建议

本次只给剩余适用链的实现接口，不重审 whole，不授 current96 通过。请求配置 GPT-6.1-Sol / xhigh；实际 resolved 配置 unknown。实际读取本席 R089 有限表、R090 scope、R091 的同一剩余项，根合同及 design §0.4–0.6 / testing P03，当前 GCU producer、preservation、compile hook 和 ELF0 的对应最终 LLVM 片段；没有读取 peer，没有测试、import、SDK、远端或设备执行。仅写本报告。

**可以优先用实际 SDK LLVM 的 typed CFG、caller 和 block-argument tuple 形态完成这一步。无需继续建设 native 全 ISA、一般 taint 或全库 CFG 分析。最少新增产物是一份“本对象哪些 required source/loop 满足哪条已审 family 条件”的自动收据，随后将已有 current96/raw 身份表 join 到它。**

这里的 verified 语义限于实际 selected observer 的 issue/wait/body region，不是 source-exclusive cost、引擎完成或 busy。R093 的 reader/relative-field diagnostics 保留其原范围，不必先让所有诊断点都成功才开展这条适用连接。

## 1. 放在哪一处，以及现有输入够不够

最短路径是在现有 packaged `gcu-timeline` 增加一个只读 LLVM-structure 检查入口，由 `gcu_timeline` 在同次编译/离线补证中组合结果。已有 `GcuDebugScopes.cpp` 已能读取实际 SDK LLVM dialect 的 typed operations；vendor target properties 保持 opaque，SDK 验证后的实际返回文本才是检查输入。检查器只读该 snapshot，不重写代码或重新编译应用。不要为跨版本 parser 兼容性重新打印/规范化 SDK IR 后送回 codegen。

建议逻辑接口如下，名字可沿现有代码调整：

```text
check_llvm_boundary_families(
  execution_before, execution_after, manifest,
  actual_sdk_llvm, compilation_binding, family_rules
) -> scoped_boundary_receipt
```

| 输入 | 最少实际内容；已有材料如何复用 |
|---|---|
| `execution_before/after` | retained 实际 GCU execution IR；复用 R087 当前 producer reproduction / program-core certificate，得到自动 primitive 或配对 fusion region 的来源和所在原 loop。不是重新证明所有原 SSA。 |
| `manifest` | 当前 site id/kind/source location、native marker、observer/layout 与 preservation certificate。site id 仅在该 manifest 内有效。 |
| `actual_sdk_llvm` | 本次 SDK 验证后真正送往后续 codegen 的 LLVM MLIR bytes，核 `debug_execution_native_ir_sha256` / snapshot artifact。读取 typed block、successor operands、callee/signature、SSA 与 source/marker refs。 |
| `compilation_binding` | 既有 producer/tool/SDK/library/config identity，before/after/manifest/LLVM/fatbin/ELF 摘要及 R069/R093 原件绑定。编译阶段尚未有 binary 时先保 LLVM 收据，make_fatbin 再绑定，不能先签某未生成对象。 |
| `family_rules` | 有版本、target/tool/SDK 适用条件和审计引用的有限规则；引用 R089 已审 native family 及已有 SDK closure，不按数学算子名或 ELF hash 选择。 |

现有 producer `GcuTimeline.cpp` 已有 site 分类、同 block 嵌套 border 配对、selected begin/end 与 record tuple；manifest 有 id/kind/location/marker，但**没有最终 body/CFG/tuple/loop 条件收据**。现有 preservation certificate 明确只到 SDK lowering 之前；`gcu_timeline` 的最终 LLVM SHA 和 DI/native binding 则已提供后一段身份。缺的就是上述结构检查及组合输出，不需要改 raw ABI、timer 或 record tail。

若从 retained execution IR 已能无歧义恢复 source region / 原 loop，直接离线推导即可，不强制为此改 producer。需要新增 manifest 描述时，只加 `origin_refs`、`body_anchor_refs`、`enclosing_loop_ref` 一类编译器结构引用；不能让用户手填 SSA、PC 或 site 白名单。block 编号/SSA 名只作本对象证据定位，不作为跨对象规则常量。

## 2. 三种最小规则及共同检查

共同检查只有五项：本对象 identity 在 family 适用范围；source→自动 site 对应；selected begin→声明 body/call→end 的有限路径；本路径 tuple 到正确 record；适用时 loop 重复关系。可使用 dominance/post-dominance 或直接有界遍历有限候选子图，不要求构造任意 native 全 CFG。

| 结构规则 | 必须自动检查什么 | 明确停止点 |
|---|---|---|
| **primitive issue / 原 wait caller** | 匹配实际 SDK callee 的签名、参数角色与已审 wrapper family；selected begin 在其前，所声明 call/操作在配对 end 前；wait 只引用已知原覆盖集合。对 body 内其它准备/清零，按实际 bracket 范围说明是否包含。 | 同名函数本身不够；但不用展开所有 SDK ISA。issue end 不提升为 DMA 完成，wait 不提升为 busy。已有 pipeline/依赖门引用原资格，不重开。 |
| **配对 fusion observer body** | 从原配对 region 及实际 source origins 找到最终向量 load/计算/结果 store 或相应 SDK call 的有限 body；确认它们在 declared observer 路径中的两端之间，producer 原数据/副作用关系没有被错误换成 logger body。接受真实 fusion/split 的 M:N origins。 | 不逐条解释所有算术 ISA，不要求该 source 行所有指令 exclusive；不能只看到同 location 或正 duration 就认定 body 被包住。 |
| **包含上述 region 的 runtime loop** | typed loop head、runtime trip 值来源、进入/退出条件、回边/latch；selected body 每次取得本轮 begin tuple，body 后取得 end，正常 record / 满容量跳过记录后才到 latch；不存在声明路径绕过端点或把旧 begin tuple 带到下一轮。 | 不要求每条 raw 恢复普适 iteration_id，不要求 source induction 也在 bracket 内；现有同 binary 改 K/raw occurrence 作为交叉核对，不新增数学运行。 |

两端必须沿用同一 selected observer 条件，零 tuple 的未 selected 路径不能进入“真实读钟已配对”的记录路径。这里只确认该 observer；既有 State/participation 事实可以引用，不把标量 writer 自动升级为全体引擎或协作主体耗时。

**shared-end 不需要每个 site 各有一条独立 DI end。** 在 LLVM typed branch operands / block arguments 上核每条实际 incoming 的 `(site, begin_low, begin_high, begin_identity)`，允许其接一个共享 end，再接实际 record tuple；保留所有 incoming 的条件和 site，不靠 end 行号猜 site。对 tuple 未知、出现额外无法解释入口或出口的该候选保 unverified，并点名具体边，不要求别的已闭区域再证明。

## 3. R089 怎样变成规则，而不是照抄 PC

已有实际对象提供可直接实现的正形态：

- 输入 `bb16` 的三个 incoming 分别携带 site1/2/3 和各自 begin tuple，body 分别为真实 slice-pad / deslice / slice submit；site4 是自己的 end 后进共享 record，不能因为 record tail 共用就给它套 shared-end tuple。
- 输出 `bb53` 两 incoming 携带 site6/7 及各自 tuple，共用 end。end 的 DI 只显示其中一个 site，typed incoming 关系仍完整。
- source39 的 `bb41→bb42/43→bb44→bb45/46→bb47→bb41` 是 runtime trip、selected begin、向量 body、end/record 和 latch 的实际形态；trip 来自 `%arg10`，body 的 loop-carried descriptor 是实际数据依赖。

这些 block/SSA/PC 仅定位审计正例。实现匹配的是“参数角色、callee family、selected diamond、typed tuple forwarding、body 与 loop 关系”，不匹配 bb16、site11、polynomial、source hash 或特定地址。共享/不同 end 与 record 合并应自然落在同一结构规则中。

R089 的 fixed SDK/native 审计支撑的是有明确前提的 lowering family。**不能把“同 SDK + typed CFG 看着相似”直接升成任意新纯算术/helper 的 final-native 保证。** rule pack 应写清其已审支持的 call/body/loop lowering 条件及 SDK/library/编译配置身份；本对象自动检查这些前提。若 current96 的某个 required region 确有一个尚无依据的 helper/出口/loop 变体，只需读该形态的一份现有 SDK LLVM/native 片段，补其具体关系或标 unknown；不预先要求每个 ELF 全指令审计，也不把纯 opcode 不同自动判成新 family。

## 4. 输出的最少可编码字段

不必新建公共框架，可以作为既有 backend boundary proof 的版本化补件。以下是逻辑字段，长图引用用内容寻址 artifact，避免复制整个 LLVM/CFG：

```text
schema_version, rule_version
inputs: {producer_identity, SDK/library_identity,
         preservation_ref, manifest_sha, final_llvm_sha,
         fatbin_sha, elf_sha, native_binding_ref}
regions[]:
  {origin_refs, site_ids, family_rule_ref,
   semantics, observer_selection_ref,
   body_refs, begin_refs, end_refs,
   incoming_tuple_refs, record_tuple_ref,
   loop_ref?, status, reasons[]}
```

`loop_ref` 只需 head/latch/exit、runtime trip/loop-carried tuple 的本对象引用。`status` 用 verified / unverified / unselected 等既有含义；verified 必须带本次范围及规则前提，不能只保存旧 `status` 字符串后离线信缓存。source-exclusive cost、hardware busy、跨 SIP epoch 等不在本接口授予范围；无需为了有限 observer-region 合格把 broad top-level 字段都改成 true。

normal compile 与 immutable offline 必须调用同一只读规则逻辑，结果绑定本次 analyzer/rule identity 和原件 SHA。可复用 R093 的 immutable snapshot、受管 child、失败/超预算留存与 unknown；此接口不重开其已闭 lifecycle。保持已有输入/输出预算，按内容身份缓存结构收据；超过原冷编译/导出额度要明确 unverified/失败，不静默跳过 required 项。

## 5. 接 current96：一次覆盖 join，不是96次人工签字

资格侧单独给规则结果一个很小的 coverage join：

```text
capture/case/replacement identity
  → 原冻结 required origin / required loop
  → 本对象 manifest site/path + boundary receipt region
  → 已有 raw observer/event/occurrence refs
  → covered 或一个具体 gap reason
```

必需区域取资格前的实际登记，不取“checker 恰好通过的 site 集合”。不要求所有 manifest site 都合格；但不能事后删 required source/loop。fusion 的多个 origin 引用同一 interval，不复制 duration 凑“两个区域”；split 的实际 alternatives 按本次发生路径连接，不强迫另跑所有编译分支。

按 **最终 LLVM/manifest/工具身份** 去重结构检查，cold/warm 只做身份 join；每个实际 binary 仍核自己的绑定。R090 的32 LLVM/binary与后来含前端的33-key不是同一个去重键，不新增分母。这个建议不假定某个数就是实际 family 数，也未遍历 current96 全部对象。ledger 成功覆盖原 required 区域，并复用已有正 raw / 同 binary runtime-K 事实，便可关闭这项 G1 适用链；不再以其它 unknown ELF 或历史 broad false 追加新门。

## 6. 最短实施顺序和裁定

1. 用已有 retained 两对象和 current96 的 required 索引作只读结构盘点，先输出上述三类规则的适用/具体 unknown；不编译应用、不跑设备。
2. 将 typed shared-end tuple + caller/body + loop 三种有限检查放入现有 packaged tool/后端补证入口；如已有等价结果，只补身份收据与 join，不重复造 checker。
3. 自动覆盖 join 指出确实剩余的 required 变体；只补那个变体的既有原件关系。不要从未知数量出发先写全 ISA、全 CFG 或逐算子审批表。

本次没有新增 confirmed runtime bug，也不声称上述三规则已实际覆盖 current96。真实必要不足只有“最终结构条件收据与 required 覆盖 join 尚未产生”；接口所需 before/after、manifest、SDK LLVM 与 binary/DI 身份已有保留渠道。该方案可以优先实施 typed SDK LLVM 检查，复用已审 native family，满足原最小 scope；无需继续扩建任意 native 证明工程。

源码读取时 HEAD 为 `0e63a5c0297bb59d4a782afbc0ed93f78313ce30`；producer SHA `6cad9fa1a7b28353125bbd2fb9ae57d078e7c4f26217b8e1523ed6edc2f5e39b`、preservation SHA `6c60defb0509c72c132d2fefe0bf38effd05b5fd444e15549ca7dc9b12737644`，与本席先前审阅相同。R089 原表及 clock/State/pipeline/DI/native 既有肯定范围维持，不在本报告重开。
