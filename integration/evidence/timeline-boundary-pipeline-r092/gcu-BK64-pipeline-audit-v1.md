# R092 GCU BK64 三方关键 pipeline 有限 delta

**最终追加结论：actual64 v3 原件已读，GCU BK64 三方关键关系有限门可关闭。** 初版缺原件记录保留下方；实际比较、SDK复用条件和精确范围见文末。没有本范围 confirmed 缺陷或剩余必要补采，不授whole goal。

**初版结论（已由文末实际原件闭合追加替代）：verification gap。** 初版本地能核实际运行终态、三方身份摘要及普通测试源码，但缺 BK64 ordinary / sparse1 / default8 的实际 IR、capture metadata/LLVM/raw。以下保留当时定位与最小请求；最新结论见“实际原件闭合追加”。

配置沿用原独立 R3：请求 GPT‑6.1‑Sol / xhigh，实际 resolved model/effort unknown。只读本地文本、JSON/stdlib、Git；未执行产品/import/测试/SDK/设备，未读 peer 新报告。本文不重开已闭 State、SQL 或 whole review。

## 原范围与已核事实

`timeline_testing.md:300` 原文要求“C2 每个调度变体分别对照”。R090 的 BK32 有限审计不能替代 BK64；这是原范围的 G3 补项，不是新增调度变体或实验门。也不把 BK64 当新独立数学。

实际 BK64 owned root 为 **`/tmp/chijin-timeline-r057-gcu/runs/controlled-density64-v1`**，不是 BK32 的 `controlled-density-v1`。本地 `run-057/preflight/gcu-density64-current-v1.jsonl` 保实际 terminal0、44.790694836s，两个 child 均 returncode0；argv 明确 `--variant 64 --ordinary-repetitions 3 --repetitions 3`，density 分别为 `--timeline-max-sites 1/8`。`gcu-density64-runner-v1.py` 实际绑定 maintained source SHA `298743dc44abde27a6326f02be3b0204c1a046c855a8eb6f24fe5a27006cca50`。

该测试源码固定 M=N64/K192、A/B half、grid(2,2)、warps4/stages1；BK 从32改为64，源码 K tile 次数从6变3。后一个是源码推导，尚未冒称已核实际最终对象的 loop/消费路径。

`run-057/preflight/gcu-density-both-summary-v1.json` 的 BK64 两组三 ordinary、三 profile 均记录 math_passed / original_calls=1，实际身份为：

| 对象 | binary ID | 已记录 IR SHA256 |
|---|---|---|
| ordinary，两密度共同 | `c402c0304c6a6424e410f5d0c215fdb6c90db4114380914ae3ceb7d67da3ba11` | gcuir `26007957edca8aef18dc21ef8ef10b0cd5f61f5955afd5221b39f6c4270782ad` |
| 真正 sparse1 | `33597b37e0375a6e6ec0f980c2faa59de9b547b2d93f8742d359ab5f4e6d9a98` | recorder input `4eb4b6c4801ed561c95982232b3fb2af08eba69dda8a6f18220baba0260d4c33`；output `ff8b875d68b440d08b6d9000cc2d54d4fd2be952908f5d7bd65c48d113a47464` |
| default8 | `2c808c04b23d530e4a6d3b646830ad97cbc4cee7e78372c785cb46adafca6ef3` | 同 input；output `73e5d262ab735a7abdb525fe1126df8b043778eb15aad54bd077874eb06c0d9a` |

摘要有104/106个正 interval、两 observer、unknown slots0、各两 counter/dependency export，原 memref_ext primitive + matmul ordered projection相同。这些只用来定位原件，**没有用计数/同名序列证明 descriptor、wait coverage、consumer 或 reuse**。

`run-090/preflight/gcu-density-details-v1.json` 本地不存在；实际为 `gcu-BK32-density-details-v1.json`。后者及 `gcu-BK32-density-inventory-v1.json` 都仅列 BK32，不能冒充 BK64 actual metadata。BK32 receipts archive也未含64对象。

## 精确最小缺项与可复用条件

只读回收上面真实 root 中下列 regular files，并给 relative member length/SHA index 即可；无需整个HTML/report/SDK数据库：

1. `launch.json`、`terminal.json`、`output/formatted.py`、`output/steps.json`，以及 `output/density-{1,8}/result.json`，绑定原运行与数学/三方配置。
2. `output/density-1/64-ordinary-1/ordinary.{source,ttir,ttgir,gcuir,llir,fatbin}`；`output/compile-cache/*/product.json` 中 `metadata.hash` 为上述 c402c030… 的那份。另对两密度六次 ordinary 仅做 artifact SHA inventory，若相同不用重复回收六份大对象。
3. 两份 `output/density-{1,8}/64-0/capture/timeline/index.json`，及各自 index 指向的 invocation main JSON、`.input.json`、`.events.json` 和 `.raw`。main 的 `compiled_snapshot` 已含实际 LLVM、binary 与 compiler identity，无需另造 SDK codegen。
4. 由这两份 main 的 `debug_execution_rewrite_receipt.argv` 定位实际 temporary directory中的 `input.mlir`、`output.mlir`、`manifest.json`、`launch.json`，terminal若存在一并保留。实际核查确认 `debug_execution_input_ir` 本身为输入文本，文件路径在该 argv 中。以上共同 input/两 output SHA应与表内摘要核同，不能拿BK32的tmp路径代替。
5. 各 main 的 `observed_dependency_exports` 所指 issuer view JSON，用来交叉核实际 tag/index/descriptor/generation与raw引用。无需重复pftrace/TP或新时钟实测。

拿到这些后，复用 R090 已读的 actual fa9 SDK十根完整定义（`pipeline-primitives.ll` SHA `f09d690912c6b0c357a140e01b2e24a2986fd46633ac6c3bba59f9ba330cd870`）有明确条件：BK64 actual compiler资源仍为同 fa9库与同调用 ABI，没有profile库同名覆盖，且实际FP16 descriptor/window处于已核支持范围。不能只按GCU品牌或BK数值继承。

有限审计只需连接：ordinary→recorder input→两actual output的完整 application core（hidden arg/SSA/导航正规化与明确observer增量另核）；改变后的A/B搬运尺寸、地址与tag；每个compute消费前原wait覆盖；原消费者之后才复用对应buffer；若原ordinary存在非空future机会，logger没有在该窗口插入强制排空。新private controller/发布DMA/wait是否仍在原return前、全部原应用wait之后，亦须从BK64实际位置核，不能继承BK32的行号。

不要求same schedule、same issue order或测得hardware overlap；也不由stages1先断言future为空。若actual对象没有某种future机会，报告其真实关系即可。只有发现真实关键关系改变才考虑产品修复；本轮缺原件本身不是confirmed bug。

## 本次交付边界

初版完成了BK64真实owned路径/身份定位和最小输入清单，当时没有完成实际参数/tag/wait/consumer/reuse/future比较。原BK32有限结论保留，原State/SQL/数学成功不撤回；下面按回收的 actual64 原件完成本项。

## 实际原件闭合追加

**最新结论：GCU BK64 ordinary / true-sparse1 / default8 的关键 pipeline 关系有限门可关闭。没有本范围 confirmed blocker/major/minor，也没有剩余必要补采。** 这是原 C2 BK64 变体的静态关键关系与实际运行原件连接，不授测得硬件 overlap/busy、generic source/loop 自动放行或 whole goal。

### 原件、身份及完整比较

实际回收根 `artifacts/timeline/run-092/preflight/gcu-BK64-pipeline-receipts-v3/`；本席用 stdlib 逐项核 `BK64-pipeline-index-v1.json` 的 **52 regular / 25,130,122 bytes**，长度与SHA全部匹配。archive SHA `d5db887411232db23a2664b0cd6a25bc240db54c03c237661836137211262c93`。下面 `P` 指其 `retained/chijin-timeline-r057-gcu/runs/controlled-density64-v1`。

ordinary 全artifacts与 product.json 绑定上表 c402c030…；fatbin SHA **`27d2bf863b6f19be09e7f755a4acc9044909fd8fc0ad5356c4e390ea9da2f0b9`**。两 capture 分别为 density-1/64-0 的 `invocation-198f62d07dde4483a2529233aabac138`、density-8/64-0 的 `invocation-03bb015f18324a32963599b54bbfe85a`。实际 max_sites=1/8，四 physical threads（warp_size=1），warps4/stages1、同 gcu300/compiler/clock helper 与原源码/输入规则。ordinary shared=8192B，符合实际两个 4096B shared staging windows；不能沿用BK32的4096B总量。

两 actual rewrite目录为 `P/tmp/flagprism-gcu-execution-bwt_30k8` / `…-731mti35`。从 rewrite argv核实际input/output/manifest，而不是把内嵌IR文本当路径。input/两output SHA与上表完全相符；各 capture 的 `compiled_snapshot.compiler_artifacts.gcuir` 是相同output文本。实际最终LLVM SHA：

* sparse1：`0b26bbc5f1e5993bef508523701dd256f628e96b29e83ae6bbb160ef16acb6ff`，fatbin `e60166c10fdc5a595194d16899801584ef1f248217561899830b4259c3f3cbc1`。
* default8：`c7df8e736c562b92076d3038d98eb054112e59ba98439d323bb2995145da343d`，fatbin `0c529b09bd0e4d9149d63d2c0c7794ffd44a2178dde62e272522310cfb7b2929`。

本席逐byte解码并核 capture 内 binary snapshot SHA与executable字段相同。两 capture 的完整 `debug_execution_tool_identity` 均与本席已核 BK32 完全相同；实际最终LLVM callee集合也分别与BK32相同，无新增未知SDK调用。包括 profile库SHA `1a780215…`、compiler.py `f21fd9af…`、native recorder `4750b6bc…`、clock helper source `25ab3c5f…`。据此复用已审 fa9 SDK / profile库不覆盖这些helper 的有限语义，不按品牌继承，也不再提取/编译SDK。

完整application比较结果：ordinary内部body与recorder input各 **447行**。仅规范formal/SSA/debug属性，并把同类型同值常量按定义对应后，**421行有序非constant application core相同、26项typed constant多重集相同**。ordinary/input仅有32/64两个独立constant声明顺序互换，使用的值未交换。不是按primitive名称投影。

在actual sparse/default output中分别核并剥离136/139个明确的observer selection区域，另核fresh ring/count分配、count初始化和回收；只移除前缀中已无使用的24项selection纯计算。余下仍是相同447行application body：相同421行有序core及26项常量。原guard、descriptor、原wait/两处barrier、loop/accumulator/return路径均包括在内。新增scalar stores只到fresh `%0` ring、`%1` count，新增scalar loads只读count；返回发布另如下核实际位置，没有把其内存效应忽略。

### BK64实际参数、wait coverage及非空future

行号以下对应 `P/output/density-1/64-ordinary-1/ordinary.gcuir` 及两actual output.mlir；两output的关键app行号相同。实际循环0..3、步1，最终LLVM同样是 `i<3`，不是仅由源码K/BK推断。

| 实际阶段和tag | ordinary行 | 两actual output行 / 结果 |
|---|---:|---|
| A GM→local **32×16 half**，source K起点64·i+16·thread，tag1 | :93,134 | full slice :1079；原descriptor/guard保留 |
| B GM→local **64×8 half**，source K行64·i、N列32·program.y+8·thread，tag2；B提交先于A raw wait | :158,198；A wait :214 | B full slice :2600，A raw wait :3340 |
| Araw→shared **32×64**、dest col16·thread，tag1；wait512 elements，原barrier | :224–226 | :3522 / :3713 / :3886 |
| Ashared→Acompute **16×64**，source row16·floor(thread/2)，tag1；先提交再等B raw tag2 | :231；B wait :235 | :4059；B wait :4253 |
| Braw→shared **64×32**、dest col8·thread，tag0；wait512，原barrier | :242–244 | :4432 / :4623 / :4796 |
| Bshared→Bcompute **64×16**，source col16·(thread%2)，tag0 | :249 | :4969 |
| **消费cut**：B tag0与A tag1各wait1024 elements，才addmm(out,A,B,prior,16,64,16) | :250/:253/:255 | :5160/:5335/:5509 |
| compute返回后才dealloc compute/shared buffers、yield，下一tile再复用 | :257–262 | 完整core中同样保留 |

在合法program坐标0/1、thread0..3、tile0..2下，两GM输入均为实际完整tile；A的16·thread和B的8·thread分别覆盖合法K/N分片，compute source行/列窗口均在shared尺寸内。fallback/pad分支也保留，但没有拿本例不走的分支制造overlap。BK64把输入/compute搬运元素数扩大并把tile数减半，没有改变上述tag角色或consumer cut。

这两个**非空future机会**真实存在于ordinary：B已提交后才等A；Ashared→compute已提交后才等B。Sparse/default没有在这些窗口加入logger DMA、completion wait或global lock。不能由stages1宣布无future，也不把静态保留机会说成测得引擎并行。

### 最终LLVM、物理buffer及reuse

ordinary LLVM的tag数组为独立三个768B private controllers（:76–90），各下标0/1/2。其Araw wait :331，Araw→shared :340、wait :343、原sync :344；Ashared→compute :351 **先于** Braw wait :356；B布局传输/ready :364–375，Aready :378，matrix :380。两actual LLVM仍按相同tag下标取controller：sparse Araw/布局wait :2162/:2435，Brawwait :2834，B/Aready :3498/:3629，matrix :3759；default对应均+1。两原sync只有sparse :2562/:3232、default :2563/:3233，没有增加本体sync。

以下均为相对实际 `tops_get_local_memory()` 返回基址的byte区间，**不把raw中的device地址当zero-based local offset**：

| buffer | ordinary | 两profile |
|---|---|---|
| Acompute | [0,2048) | [66048,68096) |
| Braw | [2048,3072) | [68096,69120) |
| Araw | [3072,4096) | [69120,70144) |
| Bcompute | [3072,5120) | [69120,71168) |
| initial accumulator | [5120,6144) | [71168,72192) |
| output accumulator | [6144,7168) | [72192,73216) |

完整application空间统一平移+66048B；ring=[0,65568)，count在73216。Shared A/B分别是shared-base+[0,4096)/[4096,8192)，不是local ring空间。**Araw与Bcompute确实复用地址**，其原最后消费者Araw→shared已在原wait/barrier完成后才填Bcompute；下一iteration的compute/shared buffer复用又在原addmm返回后。实际fa9 `tops_addmm_fp16_fp32` 的已审定义按16×64×16读取A/B/prior、写结果后返回，不含新的DTE提交；因此这项reuse cut有消费语义依据，不是只看dealloc顺序。

SDK wait仍以传入controller的channel为目标。实际BK64使用相同FP16 slice/deslice ABI、合法窗口、同原wait覆盖和同helper定义；不需要全native ISA或隐藏scoreboard重解释。此处也没有把helper名称当engine-busy依据。

### 发布位置与动态交叉依据

原State最后wait为sparse output :8471 / default :8639，原State buffer随后释放。新增private tag仅在sparse :8686 / default :8854出现，ring→hiddenoutput发布DMA :8690/:8858，wait :8693/:8861，return :8700/:8868。最终LLVM确认原最后wait :5434/:5558，新controller初始化 :5590/:5714、新memcpy :5601/:5725、新wait :5603/:5727，均在原应用工作后返回前；发布65568 bytes。沿用前审准确限制：private controller初始化含barrier相关MMIO/intrinsic，不能写成“SDK无任何新增barrier”；实际没有把该初始化/发布搬进上述原future窗口。

两raw SHA分别 `42e1cfca263b6c94ebd7971d0603d78f1672423c42c5782eb2b4feb8878aaf62` / `8637e63382e1eb4a610a1ba9fc05ec2bddb8ea10e29a3fa9396bee8d27aad1ef`。两program([0,0,0]、[1,1,0])各实际3次matmul observation；每个issuer view为42nodes/21edges，tag1 generations0..9、tag0 0..7、tag2 0..2，原raw身份核同。这与三轮及后续C/State drain相符，未把重复地址串成同一代。

原view的consumer_readiness/source_cost/busy/physical-temporal-comparison未证字段保留，不改成全局真；本次是绑定对象的静态consumer/reuse/preservation审计，不以104/106正interval数量补native资格，也不以TP成功补本门。

**处置：初版缺actual64原件的gap已关闭；GCU C2 BK64关键关系可与已闭BK32各自登记。** 无本范围必要额外验证，无产品/SDK/数学/设备执行或原件改写；不触及另行进行的自动source/loop规则、全登记适用链、其它后端或whole签字。
