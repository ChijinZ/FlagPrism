# Ascend 已留存 recurrence：有限 source/body/occurrence 审计

结论先列：**这份同一真实 ELF、实际 source-linked observer bracket、已定位 native member issue 前缀及 raw 多 occurrence，足以支持原 goal §2.2(1)(2) 在该 Ascend 案例上的“实际内部区域与循环重复”证据。** 不是 source-exclusive 耗时、完整原 LLVM fragment 的逐指令包围证明、native iteration_id、物理 engine busy 或普通流水保持。site16 单独仍只有一个源区域；本来已有的 site17 或 site18 store bracket 可作为第二个不同源区域，site15 的 Steps load 也提供独立 source-linked 区域。因此不需要为“两区域”新采集或重跑数学。

本文不作 whole-goal 签字。未读 peer 报告，未自行运行产品、测试、SDK 编译、模型、设备、数学、TP/UI 或 SSH。仅用本地文件/Git、jq、哈希、tar 流式读取及 od 读取原字节；只写本报告。请求 GPT-6.1-Sol / xhigh；resolved model/effort 未暴露，记 unknown。

## 实际阅读与最少原件

已读原 goal §2.2、design §0.6 与相关 source/loop 约束；R061 `ascend-boundary-inspect-evidence-v1/output/vector/` 的 original/adapted LLVM、actors、counter-map、DWARF、旧反汇编；R063 的实际 CSV、source manifest、retained audit v2、compute-prefix checker/result、retained-file 索引和其证据 README。跳过同目录 reviewer 报告。

初盘点缺 actual capture/raw/ELF。root 随后只读回收 `run-089/preflight/ascend-vector-boundary-receipts-v1/`；本次实际读取其中 vector capture、events、raw、guard、source snapshots、counter-ns view 与原结果，独立核关键 SHA。root audit 登记 180 regular files / 24,077,000 B，archive `601dfa7089f035c6df25e9364b46397116361dd349a8ba13c3e97966d95dfe53` 全 index 核同；本 reviewer 没有重算全部 180-file ledger。

| 原件/链 | 实际核对身份 |
| --- | --- |
| hardware loaded ELF / R063 SDK dumped ELF | `73c2d8d27a949359f22fce1095c56706240d065cad492e73f97653848d682b0d`；本地 loaded ELF 独立 SHA 核同，R063 对同一 dump 的绑定保留 |
| actual binary / invocation | `59c6e82cbc4eb4c265ed899ba6ec23e93c28a65d455351b1dae512d3630a6fad` / `invocation-ef486a8af15948359d7457a3931d08d3` |
| capture JSON | `39a5724ecf58c31d5fea78833fb0fe6e89cb8b427dc153d89d08c3771b7c8c8b` |
| raw / guard | `e13e3c846d7f31ec2243676a55ee847279822817d26834090ad2a850e464d7ab` / `39557315215be0f6922cec45d29336c8f72198032cababdc5ec0672d45e894ad` |
| normalized original / adapted LLVM | `fd23a0cdaaaf3a362c6557bc2230994977756d7b56646ef4b0f2616a64e380b1` / `ec3af485d05701ae12230cc8e3ee8f8d3559593ed1052045e27cb2dfbebaee7b` |
| manifest / counter-map / DWARF | `279f8cdeb39aecab94d3d95da5a63ea49d239aa7c99e42ddf522f71cff837a2d` / `4f9c2f99b23c49f94f62d1c2c4786533019c8d05abbdccd70498e974da4fb3b4` / `f976c72d9209d4bf436c609dc47c91b9d644caabb4dcfdb311563f20e27785c9` |
| SDK instruction CSV | 由保留 JSON 精确流式还原文本后 SHA `3fcd3f93b52b99d1e5fbe9369f53c5c0c31f8f8100fa2a8e991f069bc1bf5846`；`.text` 10,916 B，SDK text-load base `0x10d11000` |

manifest 原始 source block 名称与 LLVM 重新序列化后的 `%45` 等编号不同；对应依据是 source-op ID、原 fragment 内容 SHA、实际调用与 manifest 身份，不靠 SSA 名称相等。capture 保留 enclosing SDK process group / exact final output association，final binary SHA 与上表相同；没有用另一次重新编译的对象替代。

SDK 模型 child **139** 继续保留：只取该相同 ELF 已留存的 opcode/PC/静态 operand 信息，不用 CSV 的 cycles、模型时长、寄存器样例数值或 model call_count 冒充硬件时长/动态轨迹。1,728 个 CSV PC 是已留存子集；36 个 marker 中 28 个有行、8 个 absent，absence 不表示未执行。本审计不追那 8 个无关 marker。

## 有限 source/site → native body → readers → occurrence 表

全部为同一 `recurrence` AIV scalar observer。grid `[3,1,1]`，选中 program 0 与 2；actual header actor=1、flags=257，设备 GET.SUBBLOCKDIM 发布 count=1，reserved slot2 不是第二个执行主体。raw 两 header 分别有 16、20 个 committed pair，无损完整。下列数据只在各自 observer 内解释。

| site / source 关联 | 实际 LLVM body / source scope | 实际 ELF reader / member | 该 capture raw occurrence |
| --- | --- | --- | --- |
| 15 / source op10，line29 Steps `tt.load` | 原 load Steps 与原 WAIT_FLAG 同 fragment，循环之前；原 LLVM `%40 = load i32, ptr %6`，adapted `%630` | begin `0xdf0` → `0xe08` B32 scalar load → end `0xfb4`。`0xdf0..0xe08` 每4B有实际 CSV row、无 branch；期间有正常 stack/operand preparation。原 wait 另在 `0xe50` 附近，不能把 load bracket 称纯 load cost | program0/2 各1；Δtick 7 / 8 |
| 16 / source op11，line31 `value*0.75+0.125` | manifest 原 fragment 含原 BARRIER、vmuls、BARRIER、vadds 与 induction add；fragment SHA `eb6a54e7a6f3efbd958535212b708b12c568c7a9cf8b2f778726bcc1063ca4df` | begin `0x12d0` SYS_CNT→`0x12e8` VMULS→`0x130c` VADDS；到 VADDS 为完整、无 branch 前缀；end reader `0x1334`。两个 native member 有 UB `0 → 0x200 → 0` 数据链，原两个 VEC BAR 位于 `0x12d8`、`0x12fc`。**induction 不在该 bracket 内，不能归入其耗时** | program0/2 各3；Δtick 分别 `[2,0,1]` / `[2,1,1]`；iteration_id 均 null |
| 17 / source op16，line32 Y store | loop 后原 WAIT_FLAG + float UB→GM store；fragment SHA `da04d14e662a5b450dcdb818d5bc339b01e16c86cba5b072cb7193d448db7cc5` | readers `0x1784` / `0x1978`；原 WAIT_FLAG 在 `0x17e0`，MTE3 `MOV_SRC_TO_DST_ALIGN` 在 `0x1974`。有内部 guard/logging 路径，故这里给**已定位 issue member 的真实 observer bracket**，不是整个 helper 所有路径/硬件完成时间 | program0/2 各1；Δtick 13 / 8 |
| 18 / source op21，line34 State store | 原 WAIT_FLAG + int32 UB→GM store + 原尾 barrier；fragment SHA `dd5d5a4d5a4896f638832e1e1d5bab6a27ca96e6f058dccdad7c4cd55d32a7b5` | readers `0x2740` / `0x2934`；WAIT_FLAG `0x2794`，MTE3 store `0x292c`。同样只授该已留存 member 位置/issue bracket，不把尾 barrier 或完成范围凭空补齐 | program0/2 各1；Δtick 15 / 15 |

source snapshots 实际 SHA 为 `298743dc44abde27a6326f02be3b0204c1a046c855a8eb6f24fe5a27006cca50`（文件）与 `8a0ab1f855d7ba150f3e4efb56691a10618fb0734dcea9eac95a74b4a48120c9`（captured JIT text），均已本地核同。JIT 原文明确 `steps = tl.load(Steps); for ... value=value*0.75+0.125`，不是手写 timing kernel。实际 R060 runner 的保留 source 使用 `steps_cpu=[3]`，ordinary/profile 各一次，原数值/input/tail/State-once 结果通过；本审计没有重跑这些调用。

## reader / raw occurrence 的具体核对

本次直接用 od 读取实际两 segment header 及全部已提交 pair 的原始 u64，人工对上选定 sites 15–18 的 24 个 endpoint 引用。site16 的六个原始 pair 为：

| program / occurrence | raw entry / exit byte offset | start_tick → end_tick |
| --- | --- | --- |
| 0 / 0 | 131536 / 131544 | 170669674589800 → 170669674589802 |
| 0 / 1 | 131600 / 131608 | 170669674589812 → 170669674589812 |
| 0 / 2 | 131664 / 131672 | 170669674589815 → 170669674589816 |
| 2 / 0 | 525072 / 525080 | 170669674589824 → 170669674589826 |
| 2 / 1 | 525136 / 525144 | 170669674589836 → 170669674589837 |
| 2 / 2 | 525200 / 525208 | 170669674589840 → 170669674589841 |

实际 zero interval 保留，不写成六个 positive interval，也不加最小宽度。record descriptor 为 site16/semantic1，pair sequence 在各 segment 中连续递增，program/actor/block 与 header 一致。`occurrence_basis=complete_pair_order` 表达真实完整 pair 流中的次序；不是 native/source loop iteration ID。

adapted LLVM 中该 source body 的 begin `%854` 经 `%timeline.start15` 到记录 field2，end `%868` 到 field3，same source tuple/actor 共同选择；实际 native CSV 的已留存正常 store tail 还可看到 X4/X5 两 word 的低/高位写入：begin low/high 在 `0x13f8/0x13ec`，end low/high 在 `0x140c/0x1408`。这是可复用的局部 provenance 线索；本报告没有将含缺失分支的完整 native record-value 所有路径标为 qualified。独立读取 ELF reader words 为 42,502,272 / 42,633,344，与 counter-map 的 site16 两端相同。

## loop：已经支持什么，哪些更强结论仍未知

原实际 LLVM 有 `%41` header（phi / load-derived K compare）、`%45` body 和回到 header 的 latch、`%52` exit。adapted 中对应 `%815` header、`%819/%855` body、`%935 → %815` latch、`%936` exit；begin/end 留在这个原 runtime loop 的 body/selected observer 分支内。实际 K=3 的两 observer 都留下三次配对 occurrence，且已定位的 native reader→两项计算为无 branch 前缀。这足以说明**该实际 source-linked observer bracket 在真实运行中重复三次，并包含已定位计算 issue 前缀**；不因未解码所有未选分支而否定这一有限事实。

LLVM loop lowering 已旋转：native `ADD/SIGNEXT` induction 在 `0x1254/0x1258`、即 begin reader 之前；header/exit 候选区是 `0x1244..0x1274`，回跳候选在 `0x1450`。induction 是 source association membership 中的控制成分，不是公开语义已经承诺的 source-exclusive 成本。它在 bracket 外**不构成本报告确认的计时产品 bug**；应按实际成员范围说明，不能把括号外的 induction cost 算进来。

若以后声称更强的 native loop/每路径端点/iteration 对齐，当前尚缺的是以下具体有限事实，而不是“所有 native 都未证”：

- `0x1260` JUMPCMP、`0x1270` JUMP、`0x1278` observer guard、`0x1450` JUMP 的实际目标/条件语义。CSV 中这些项的 TargetPC 为 0，不能当作静态目标；`0x1444..0x144c` 构造的 X4=-0x83 与相对 word 回到 `0x1244` 数值吻合，也**不以这种吻合发明 JUMP 规则**。
- site16 VADDS 之后的 `0x131c/0x1320` 分支，以及 CSV 没有的 `0x1324..0x1330`。这不破坏已经完整读到的 begin→VMULS/VADDS 前缀；它限制的是“整个尾路径、所有可能返回/回边都经过同一 end”的更强声明。该区间 26 个 word 位置只有22个 CSV row，不能填造4条缺失指令。
- site17 的 `0x184c/0x18f8/0x194c`、site18 的 `0x2800/0x28b4/0x2904` 涉及 guard / helper / logger 路径。各 reader 区间126个word位置仅108个 CSV row。它们支持已留存 store member 的 bracket 关系，未建立 clipped/tail 的一般 all-path helper 证明。
- 本次未取得**同一73c2d8… ELF 的另一实际 K** 原 capture/raw/math；不拿另一个编译版本的 K7 替换。没有因此要求新矩阵；如果已有同binary材料，按其原身份复用即可。当前 K3 三 occurrence 的事实不依赖另一 K 才存在；另一 K 是更广 runtime-K/循环 lowering 交叉检查。

root 已尝试 R090 两种 `--disassemble-aicore` 组合；实际 terminal0 /0.165957985s，但 stdout 与旧 `-d` 同 SHA、均2729 `<not available>`，没有新 decode。本报告不重复该工具试探、不要求新模型。若需要更强分支资格，最小下一步是取得上述少数分支的受信 SDK opcode/operand/目标规则或既有完整 decoded 输出，再核有限选中路径；无需通用 ISA/alias/全 CFG 证明器。

## 公开语义是否需要修正

实际读当前 `timeline_events_ascend.py:388–412, 588–616`：source relation 为 `compiler_origin_navigation`，semantic 为 `observer_region_elapsed`，记录 provenance/fragment scope，原 `boundary_status` 留 `unverified`，notes 明确 lowered fragments 是导航而非 source cost/busy。现存 counter-ns view 也明确是 counter bracket、`source_boundary_status=unverified`；`timeline_perfetto.py:236–264` 的轨道名含 semantic，详情保 raw offsets、ticks、occurrence、iteration_id 与 source boundary status，HTML 也明示非 certified source cost/engine busy。未见公开字段承诺“manifest 的全部原 instructions 都必在这个区间内”。

因此可以诚实使用现有三层含义：**source association → 实际 observer bracket → 有限已核 native member issue 前缀**。不必改计时、不删原 membership、不改 raw/时间或把 unverified 改成整区域 qualified，也不把同一个融合 fragment 拆成两个算术操作各复制一份 duration。

若希望把本次新增事实向用户解释得更直接，最小呈现增强仅是派生详情一句明确范围（例如“source-linked observer bracket；VMULS/VADDS issue 前缀已核；induction 在区间外；native loop/尾路径未授资格”），并绑定本 binary/site/reader/member PC。原 `name=arith.mulf` 是 source navigation label；可统一显示为 `Source fragment: arith.mulf / observer elapsed` 以避免读者误当乘法独占耗时，但现有 semantic/notes 已作区分，**没有据此发现必须先修的 public-label correctness defect**。新对象若要自动授类似事实，应按有限通用结构和实际对象生成对应范围，不按算子名或手填PC白名单长期批准。

## confirmed / gaps / optional 与最终有限判断

**Confirmed blocker/major/minor：没有在当前保留 unverified 的公开语义内确认新的错误放行。** “native 完全没有可读出口”也不是准确总结：R063 对同 hardware ELF 的有限 opcode/PC、两个真实源码前缀及 raw 证据均实际存在；SDK child139与缺行同时保留。

**Verification gaps：** 只涉及上节列出的更强 branch/loop/iteration 路径与另一已存在同binary K 的交叉检查，以及将新增局部事实自动用于新对象的检查器/收据范围。它们不否认本次已记录 interval 的真实、多 source 与多 occurrence；也不由 raw 次数反向冒充已经解码 native 回边。

**Optional：** 仅上述有限派生详情/导航 label 增强，无新实验建议。

对原 goal 的问题给直接回答：该案例已有多个真实内部 interval，site16 有真实三次 occurrence，site15/17/18 是另外的源码关联区域，所列正与零 tick 皆原样保留；**Ascend 这部分实际内部区域/循环重复证据可作有限肯定结论，不需要再为第二 source 区域造新样本。** 当前对象可按 source-linked observer elapsed / member issue 前缀解释；不得将其升级为 source-exclusive、native iteration_id、完整片段/所有路径证明、engine completion/busy 或普通 pipeline 保持。本轮整体审阅继续等待原 pipeline 等剩余项；这份报告本身不是 whole 通过。
