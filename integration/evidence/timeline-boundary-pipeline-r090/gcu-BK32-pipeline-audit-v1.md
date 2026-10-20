# R090 GCU BK32 三方关键 pipeline 有限审计

结论：这组留存的 **ordinary / 真正 max_sites=1 / default max_sites=8** 对象，足以关闭其“关键 submit/wait、消费 publication cut、buffer reuse cut，以及原有非空 future 机会未被 logger 强制排空”的有限比较门。没有在本范围确认 blocker/major/minor。结论来自实际完整 IR 的操作数、描述符、控制路径和 SDK 定义连接，不来自同 opcode 数、manifest 声明、正 duration 或 trace 能打开。

本报告只覆盖下述 C2 BK32 对象；不签 GCU 全异步时间资格、所有调度变体、generic boundary、native busy 或 whole goal。未重跑数学、产品、SDK、设备、TP/UI，未读其他 reviewer 新报告。配置请求沿用 GPT‑6.1‑Sol/xhigh，工具未暴露实际 resolved model/effort，记 unknown。只读时 candidate HEAD 为 `f7ec2a87300c87c41fd1112982dec81f28f60c75`；审计身份由留存对象 SHA 固定，不按当前 HEAD 继承。

## 1. 合同和精确原件

按 `Profiler/docs/timeline_testing.md:118–123,300`，核普通 async 与原 wait/completion、动态 generation、原关键依赖和合法 overlap 机会。原文明确“不强求编译调度逐字节相同”，也明确总指令数或无新增 barrier 单独不够。`timeline_design.md:492` 区分静态保留机会和测得硬件重叠。此处不增加所有 ISA、完全相同 instruction order 或 engine busy 规则。

以下路径均相对 workspace。缩写：

* `R = artifacts/timeline/run-090/preflight/gcu-BK32-pipeline-receipts-v1`。
* `P = R/retained/chijin-timeline-r057-gcu/runs/controlled-density-v1`。
* `S = artifacts/timeline/run-090/preflight/gcu-pipeline-primitives-receipts-v1/runs/pipeline-primitives-v1/output/pipeline-primitives.ll`。

已用 stdlib 核 `R/pipeline-index-v1.json` 全 48 regular members，共 26,580,723 bytes 的长度/SHA；archive SHA 为 `bbcff87a5ccc400388f3247c6881f91d9c3c260fb125bfb9421f56aacf55a8e7`。另核 primitives index 的 9 members，共 240,250 bytes，全部匹配；提取 terminal=0，0.766023320s，`result.json` SHA `9b75807bcf8ca56f89f505b03e66499259f73ff961f3252adc1c0153ab10abde`。该任务是 fa9 原库定义的只读序列化，不是新 kernel 编译或设备执行。

共同数学为 `product`，M=N=64、K=192、BK=32，grid=(2,2)，num_warps=4、num_stages=1，实际 warp_size=1/四 physical threads，target gcu300。不能把 target 声明中的 warp_size=12 当实际 observer 数。`P/output/formatted.py:203–221` 固定 CPU linspace→half 输入、输出/State 初始化、reference 和 launch；源脚本 SHA `298743dc44abde27a6326f02be3b0204c1a046c855a8eb6f24fe5a27006cca50`。两密度 result 的 BK32 三次 ordinary 与三次 profile 数学均通过、每次 original_calls=1；此处没有另造“原输入数据 bytes 已独立留存”的说法。

| 对象 | actual binary ID | fatbin SHA256 | 关键实际原件 |
|---|---|---|---|
| ordinary | `8c2717bcff8e5a649aa817bdaf2c1f094239b2705db1dfdb1e5138d7721253d2` | `cd1b1cf07b2fd559f782c89990822bf15c9dbde7b7345b12e6b407ef0942e3f3` | `P/output/density-1/32-ordinary-1/ordinary.{source,ttir,ttgir,gcuir,llir,fatbin}`、compile-cache product.json；六次 ordinary artifact 身份相同 |
| sparse1 | `c165d745b1f1a21ef6c57bfa6728c47a49cc3331e535205ee5ab7e9cfd4886d7` | `9c2a4dc67eb2ae3c7158c1db5f9e94142d61c91d66ca8f536e6e360b9e6ec7f8` | `P/tmp/flagprism-gcu-execution-jk8w5fmm/{input,output}.mlir,manifest.json`；density-1/32-0 invocation `87965d0b276f49e4bea101049d2dc5ad` |
| default8 | `de603eb95f38f6abf9a95a8b714345d4e143eb60f1564660c779131001b999ca` | `bd419b80d02b60ee661cd03e3a1d787a15f4b745089add4d1d773e1e8196f7ef` | `P/tmp/flagprism-gcu-execution-ve1ug8ls/{input,output}.mlir,manifest.json`；density-8/32-0 invocation `af7d9b8e44174561834d63b5d6f7e2c7` |

两个 input.mlir 实际 SHA 同为 `0f9fd0f84e8e2dfbfcc40671e4469521f9a9f464cd2c6f4fb27ac072315d03f5`。实际 `debug_execution_max_sites` 分别为 1/8，选择 source region 1/2、site 45/46；mandatory native controls 独立存在。因此 sparse1 是实际预算 1，不是名称为 sparse 的预算 8。

ordinary gcuir SHA `e038ddb44934841062b068e8083857346c961b7036cafb41d89e5083d8eb384b`，llir `960bb7e5095736daeae4cf536b6030d7e176cc6b7b3a546381d4bb6c2112acd2`；sparse/default output.mlir SHA 分别 `cf954a9bc654ab0f8ca5b4fbc19e0d078b72057092d28c26019d76f9f8f21063` / `8c1f9bce27d3f26d70ee0dd48806e05e8e575d95e0d75b08e2586530a9549079`。

## 2. 原 pipeline 和三方逐项比较

ordinary.gcuir 内循环 `:76` 为六个 K tile，携带 accumulator；不是跨迭代提前提交下一 tile 的 pipeline。**stages=1 仍有本迭代内的非空 future 机会**：独立 B 输入提交在 A 首次等待之前；A shared→compute 搬运提交又在 B 输入等待之前。

下表 ordinary 行号为上述普通 gcuir；profile 行号为两份实际 output.mlir，核心阶段在两份中一致。tag 是实际 private tag 数组下标，未把名字当独立硬件引擎。

| 实际阶段、descriptor/依赖 | ordinary | sparse1/default8 |
|---|---:|---:|
| A GM→local 32×8 f16，tag1；GM row=32·program.x，K col=32·i+8·thread | full slice :132 | 原完整 guard、descriptor、提交均保留 |
| B GM→local 32×8 f16，tag2；GM K row=32·i，N col=32·program.y+8·thread；提交先于 A raw wait | full slice :196；A wait :212 | B 提交先于 A wait :3338 |
| A raw→shared 32×32，目的 col=8·thread，tag1；等待 256 elements 后原 barrier | :222–224 | :3520 / :3711 / :3884 |
| A shared→local 16×32，source row=16·floor(thread/2)，tag1；先提交再等 B raw tag2 | :229；B wait :233 | :4057；B wait :4251 |
| B raw→shared 32×32，目的 col=8·thread，tag0；等待 256 后原 barrier | :239–241 | :4429 / :4620 / :4793 |
| B shared→local 32×16，source col=16·(thread%2)，tag0 | :246 | :4966 |
| **消费 publication cut**：B tag0 与 A tag1 各等 512 elements，然后 addmm(out,A,B,prior,16,32,16) | :247 / :250 / :252 | :5157 / :5332 / :5506 |
| compute 返回后释放 compute/shared buffers，累加值再 yield；下一 tile 的复用在此之后 | :254–259 | compute 后对应 dealloc/yield 保留 |

实际完整比较不是 opcode 投影：

1. ordinary 内部函数 444 行，在只移除 `flagtree.debug.*` 导航属性并按已知 formal 角色/loop carried 参数重命名后，与 recorder input 的 444 行逐行相同。
2. 在两份实际 output 中分别核并去除 136/139 个已识别的 observer selection `scf.if(%25)` 区域；另单独核 fresh ring/count 分配、初始化、回收及只服务 selection 的无副作用 arith/ID 计算。余下 application core 按 SSA alpha rename 后仍是 **完整 444 行逐行相同**。原描述符计算、类型/属性、guard、循环、结果流、所有原提交/等待/两处 barrier/compute 均在比较中。
3. 未把新增内存效应一并忽略：新增 scalar stores 只到 fresh ring `%0` / count `%1`，新增 scalar loads 只读 count；四个原 vector stores 保留。新 calls 是 timer/identity，另有返回处显式审核的发布 DMA。没有在 K loop 插入 logger DMA、DTE wait 或额外 syncthreads。

## 3. 最终 LLVM、真实 SDK 和 reuse cut

实际 profile LLIR 在各 capture JSON 的 `metadata.compiled_snapshot.compiler_artifacts.llir`：sparse SHA `6329697a380b25b0c3f4bd328177848701148974238a86c9ce5324b967e23bed`，default `0d874d3b93246f9d5487ae4f860333e1de59af6ca44adf455c195662113da66e`；compiled snapshot/executable、raw 和 rewrite input/output 的身份相连。

LLVM 中 tag 数组的不同下标仍解析到原 private controller，原 wait 的 tag operands 未合并。ordinary 的 A shared→compute `tops_slice_async_2_fp16 :349` 仍在 B raw `tops_wait_dte :354` 之前；两 compute-ready waits :373/:376 在 addmm :378 前。profile 对应矩阵调用 sparse :3757 / default :3758，参数为同样的 16×32、32×16 输入和 16×16 prior/output；两原 `tops_syncthreads` 为 sparse :2560/:3230、default :2561/:3231，没有增加本体 barrier。

物理 local 地址不是未经审核地当作“同一 buffer”：ordinary Acompute=[0,1024)、Braw=[1024,1536)、Araw=[1536,2048)、Bcompute=[1536,2560)，后两者确有存储复用。Araw 最后消费者是 raw→shared DMA，其 wait/barrier 已完成，才把该空间用于 Bcompute；两 compute 输入的下一轮复用在 addmm 返回后。profile 的这些 application intervals **统一平移 +66048 bytes**，相同重叠/最后消费者关系保留；[0,65568) 是独立 ring，count 在 70656，不与上述 application window 混同。两个 shared staging windows 和原迭代依赖保留。

SDK 连接已补齐，不能由 helper 名字猜语义：

* `S` SHA `f09d690912c6b0c357a140e01b2e24a2986fd46633ac6c3bba59f9ba330cd870`，235277 bytes；来自实际 `gcu300_tops_builtins.bc` SHA `fa9d850080258f7cfd3acbdccfdb3485007b9b87c3c5ed34ab187dacbb52944a`，用已记录 opt11 SHA `96a7c03576a78d29dbe9e5fc3e16b0821b02dfef38c19b0de4de5c9988139598` 保选根完整 definitions。逐读 private controller、wait、syncthreads、addmm 及实际 FP16 slice/pad/deslice/slice_deslice/memset/memcpy 的 descriptor/提交路径。
* `S:665–767` 的 wait 读的是传入 `%0` 的状态/计数和 offset532 channel，最终 `llvm.dtu.l.wait.dec(%79)`；不是无参数“排空所有原 tag”。`S:29–656` 的 private controller 保存对应 channel/descriptor，分配自实际 free-slot bitmap。DMA helper 的 D/S 与 caller memref 角色一致，FP16 full-tile source/destination windows 均合法；它们填写该 controller 的命令并以 doorbell store 提交，没有调用 wait/syncthreads。full-tile 本例不借 pad/fallback 分支制造额外机会。
* `S:4440–4747` 的 actual addmm 定义明确按 M/K/N 读取 A/B/prior，完成 C 写回后返回；不含 DTE submit/wait。故本有限 SDK 模型下，上述“compute 之后才复用输入”有实际消费语义依据。此定义不是 engine busy 证据，也不据名称推硬件 MMA 引擎。
* profile API 原 bc SHA `1a780215d7a63e34ce9c8cba6bfb126d222db726f5dca8802f3af0161fce81ec`；已留存的 `run-088/preflight/gcu-receipts-v2/runs/SDK-resources-v2/output/profile-library.ll`（621 definitions、0 aliases，decoded SHA `1ea0d2b221ca3b296823d782069cd66ce313288dda7a0e543626817015406c82`）未定义覆盖上述十个 SDK 名称。global_timer 实际仅 volatile MMIO 读/回绕读，identity 为 sipinfo 读；没有新增 DTE wait/barrier call。

以上是绑定 SDK ABI 和实际对象的有限 cut 结论，不声称已逐条重新解释最终 vendor ISA、内部 scoreboard 或硬件并行持续时间。

## 4. Logger 发布位置及 raw 交叉依据

manifest 的 `local_scalar_records_then_private_tag_DMA_at_original_return` 与实际位置一致：原 C/State 最终提交、等待结束后，才填 header/unused tail、创建新的 private tag，并将 fresh local ring 发布到 unused hidden output。

* sparse output.mlir 原 State wait :8468、buffer dealloc :8633；新增 publish :8687 / wait :8690；return :8697。
* default 原 State wait :8636、dealloc :8801；新增 publish :8855 / wait :8858；return :8865。
* 实际 LLIR sparse 新 controller init :5588、memcpy :5599、wait :5601；default :5712/:5723/:5725。memcpy 为 **65568 bytes**（16392 i32），独立 tag、fresh ring→hidden output。

这里不能写成“SDK 没有任何新增 barrier 相关指令”：private controller 的实际定义含 `movs.barrier.all`/MMIO 初始化（`S:473,568`）。新增这一初始化也在返回处，位于本 actor 原应用完成 waits 之后；它不是 K loop 内、A/B future 窗口内新增的 completion cut。发布自身的等待与回收同样在返回前，未把原 A/B tags 合并或在原 submit→consumer 间插入排空。

两份 raw SHA：sparse `63f94caae4b3caf70ebc9a4e525e3f84700b9ae36c15542ca70bf29b7fc7f601`，default `41aaec4fc16499ba6f6508a39cb861da1180a8b37ae48c3d83cf1b3435f937f2`。各 derived `counter-ns/*/views/gcu-issuer-counter-scope-*.json` 保留 raw offsets、queue index 0/1/2、重复 descriptor 与 generation；单 observer 视图 78 nodes/39 edges，可见 tag0 generations0–13、tag1 0–18、tag2 0–5，覆盖首轮、后续复用及 drain。它们支持实际运行身份/代际交叉核查；194/196 个正 interval 的数量没有被拿来证明 pipeline。

原 view 的 `consumer_readiness_verified=false`、physical comparison/busy/completion-time false 保留不改。新有限审计可以为这组绑定对象提供静态 readiness/reuse/preservation 依据，**不能凭此覆盖其余 clock/native/source/动态关联的独立资格位**，也不能宣称图上测得 A/B 引擎 overlap。

## 5. 处置和范围

本次有限比较门没有剩余的 confirmed defect 或必要补采项。可以引用本报告及上述 exact artifact/SDK/raw SHA 派生本组关键阶段保持证据；不必为同一字节再跑数学、SDK 编译或 TP/UI。若迁移至不同 IR、compiler/SDK 资源或另一调度变体，须先匹配相应输入和规则适用性，不能按品牌或相同 opcode 数继承。

未覆盖的范围是其他 profile repetition 的逐份完整 IR、BK64、其他调度变体、跨 observer 时钟/实际硬件 overlap、generic 自动放行规则及 whole goal；本报告不把这些范围列成新增本组缺口，也不撤销此前各独立资格结论。原历史失败与原件保持不变。
