# R090 GCU / Ascend pipeline input inventory

结论：**两家均已有匹配的 BK32 ordinary / 真正 sparse1 / default8 最终对象、数学记录与 profile raw；无需为补齐这三方重新采集。GCU 的 ordinary/改写输入/实际输出 IR 均可读。Ascend 仍缺本次 ordinary npubin 所对应的实际 actor LLVM/原 SDK 调用收据；其 ordinary bcmlir、metadata、npubin 完整。** 下列路径足够定向回收和后续关键关系审查；本次不签 pipeline preservation、完整异步资格或 whole-goal。

请求 GPT-6.1-Sol / xhigh；实际 resolved 配置 unknown。观察 candidate HEAD `7dc27a1b9564f3ecf56e47da63f41537b00febe9`。只读原合同/代码/原件，并通过既有 `study_remote.py` 在原 Docker 执行 stdlib 文件索引、JSON/文本读取和哈希；未执行应用、产品 import、测试、SDK/compiler、模型、TP/UI。未读其它席新报告。没有重新审查 NV pipeline；已闭 State 不重开。

## 合同范围与三方匹配

依据 `timeline_goal_prompt.md:43` 的实际异步生产消费/动态 generation，以及 `Profiler/docs/timeline_testing.md:122`、`:123` 的两轮生命周期和“原编译 schedule 的关键依赖未因插桩人为串行化”；设计 `timeline_design.md:492` 明确每组三方固定 ordinary 配置、输入、grid、数学和机制，仅改变观测密度，C2 每变体各自比较。这里要核 publication / reuse cut 和原来非空的 future 机会，不能以 opcode 数、完全相同 issue order、任意全 ISA 或 engine-busy 作为替代门。

首选有限集合是 R057 C2 **BK32**，无需先扩 BK64。两机实际执行的维护测试文件 SHA 都是 `298743dc44abde27a6326f02be3b0204c1a046c855a8eb6f24fe5a27006cca50`。已读该原源码 `product` 和实际执行 runner：M=N64、K192、BK32、warps4、stages1、grid `(2,2)`，同样的 CPU `linspace(...).half()` 两输入、FP32 oracle/tolerance、输出 tail 和 State 检查；density 只改变 `timeline_max_sites`。固定输入生成规则与每次实际 input-equality 检查支持输入相同；未声称留有单独序列化输入 bytes/SHA。

每机两种 density 各3 ordinary +3 profile。每机所有6份 ordinary 的每种编译 artifact SHA 全部相同；ordinary 与 profile 已查询的实际数值/调度配置一致。profile 各自只有一次请求。三方使用同一后端的同一 R057 安装/测试路径，目标分别 gcu300 / Ascend910B4-1；不是把其它 runtime/target 的 trace 拼成一个三方。原件是历史冻结输入，不能自动把旧 producer 的结论升级为后来变更实现的 pipeline 结论。

| 后端 / mode | compiled binary ID | 最终 binary SHA-256 |
| --- | --- | --- |
| GCU ordinary | `8c2717bcff8e5a649aa817bdaf2c1f094239b2705db1dfdb1e5138d7721253d2` | `cd1b1cf07b2fd559f782c89990822bf15c9dbde7b7345b12e6b407ef0942e3f3` |
| GCU sparse1 | `c165d745b1f1a21ef6c57bfa6728c47a49cc3331e535205ee5ab7e9cfd4886d7` | `9c2a4dc67eb2ae3c7158c1db5f9e94142d61c91d66ca8f536e6e360b9e6ec7f8` |
| GCU default8 | `de603eb95f38f6abf9a95a8b714345d4e143eb60f1564660c779131001b999ca` | `bd419b80d02b60ee661cd03e3a1d787a15f4b745089add4d1d773e1e8196f7ef` |
| Asc ordinary | `444d86a0a189f1d0b1a424fce116d0e69c4dc63079a2fc741433868fb7a2ea56` | `77d49b1a3f9f67358f72743a68c39e8adef48a4799af591e4b1ad4f484e8d0cd` |
| Asc sparse1 | `0b134fbc16c900cc159cce9bd94551e846cc50f578de4937477d04bc4ff583d6` | `0876c7da200bb942aa8d8f37dd3b52866773d0657edd17e1931f3cbf0cde9854` |
| Asc default8 | `127c1048ae995cd045e7ec760f8b3141deb78ee8e2af11367944c31ee16d650b` | `16fe3af431187563bf12bab074e96d5f398c9b3b8b6e2967b5242fa24c4c6be2` |

Sparse 身份已核实际参数，不能只看目录标签：GCU `debug_execution_max_sites=1/8`，实际 manifest selected source regions 为1/2；Asc 两个 actual observation_request 的 `max_sites=1/8`。mandatory native controls 另计，因此不能用事件总数推断 source budget。GCU 正 interval 为194/194/194 vs196/196/196；Asc为5/3/5 vs29/32/30。这些计数仅说明收据所在位置，不证明关键依赖保留。

## GCU 可读原件与已有关系材料

原访问：`zhiyuan_suiyuan`，`docker exec flagprism-enflame-dev`。

设 `G=/tmp/chijin-timeline-r057-gcu/runs/controlled-density-v1`：

- actual source：`G/output/formatted.py`；安装：`/tmp/chijin-timeline-r057-gcu/runs/install-refresh-v1/output/venv`。
- ordinary：`G/output/density-1/32-ordinary-1/ordinary.{source,ttir,ttgir,gcuir,llir,fatbin}`。其余 ordinary-2/-3 和 density8 三份核同，不必重复回收。ordinary GCU-IR SHA `e038ddb44934841062b068e8083857346c961b7036cafb41d89e5083d8eb384b`；LLIR SHA `960bb7e5095736daeae4cf536b6030d7e176cc6b7b3a546381d4bb6c2112acd2`。
- ordinary cache metadata：`G/output/compile-cache/RQTRPPH7RZNGJGVIC6626LA7BFBDTMTQLWY57WY6KE4NO4QSKPJA/product.json`，SHA `a6bedf98bf80b54a143987d7901042439caba0b601405689481b103e67fd97bc`。gcu300、warp_size1、warps4、stages1、vector_length512、fp_fusion=false 与 profile 查询项一致。
- sparse 改写目录：`G/tmp/flagprism-gcu-execution-jk8w5fmm/`；default：`G/tmp/flagprism-gcu-execution-ve1ug8ls/`。两者 `input.mlir` 均 SHA `0f9fd0f84e8e2dfbfcc40671e4469521f9a9f464cd2c6f4fb27ac072315d03f5`；各自 `output.mlir` 为 `cf954a9bc654ab0f8ca5b4fbc19e0d078b72057092d28c26019d76f9f8f21063` / `8c1f9bce27d3f26d70ee0dd48806e05e8e575d95e0d75b08e2586530a9549079`；`manifest.json` 为 `d16e8c872a0f714fca8e5eed4f69bc3ab73d91989ce10f692192f11c52b5168c` / `a99462e4ca7b323e17ba182d4167a163445be985c22e4745c0eac4cd4494f35f`。全部现场可读且与 captured rewrite/output SHA 相同。
- 两个 profile 的 `metadata.compiled_snapshot.compiler_artifacts` 还保实际最终 LLIR，SHA分别 `6329697a380b25b0c3f4bd328177848701148974238a86c9ce5324b967e23bed` / `0d874d3b93246f9d5487ae4f860333e1de59af6ca44adf455c195662113da66e`，以及实际 fatbin bytes；不是只有 high-IR opcode 摘要。

下表 `T` 是 profile bundle 的 timeline 目录；其 `index.json` 指向实际 capture，`captures/<invocation>.{json,input.json,raw,events.json}` 都保留。32-1/32-2 同结构可读；最小回收先用32-0即可，不跨调用合并事件。

| mode | T 相对 G 的路径 | invocation | raw SHA-256 |
| --- | --- | --- | --- |
| sparse1 | `output/density-1/32-0/capture/timeline` | `invocation-87965d0b276f49e4bea101049d2dc5ad` | `63f94caae4b3caf70ebc9a4e525e3f84700b9ae36c15542ca70bf29b7fc7f601` |
| default8 | `output/density-8/32-0/capture/timeline` | `invocation-af7d9b8e44174561834d63b5d6f7e2c7` | `41aaec4fc16499ba6f6508a39cb861da1180a8b37ae48c3d83cf1b3435f937f2` |

已有 manifest 明示 `publication=local_scalar_records_then_private_tag_DMA_at_original_return`、private queue-tag 编码及 source region/control site；source/output IR 可读原 `memref.dma_wait`、DMA 与 matmul/buffer SSA 参数。capture 中 `observed_dependency_exports[].view_file` 是现成的动态关系入口：

- sparse：`T/derived/counter-ns/ad6e0693853be25de271ded6444007850b0606a55db4e79707a39e521d2c7f77/views/gcu-issuer-counter-scope-c3b38ad362bd95cb24953976d36a8181d6d5c3695a28953a3e2a9b31c3f54fe1.json`。
- default：`T/derived/counter-ns/4fae0d6c92f7bf77b58184da356ae77948df99b84699bc56c236365f09549807/views/gcu-issuer-counter-scope-a69e27e9815140948c7f9359f9e34346a9ca44111d3cd8c321ce223eb4f02607.json`。

每份上述单-observer view 有78 endpoints/39 edges，并保 submit/wait raw offsets、queue base/index、tag_generation、source/destination address/space、destination descriptor-write generation。实际同 queue index 的多代已在材料中：index0 generation0–13、index1 0–18、index2 0–5；多个 destination 地址也有重复写入代。这可复用来核 tag/buffer 复用，不能把 tag 数当迭代数。view 自己保 `consumer_readiness_verified=false`、physical temporal comparison=false、busy=false、精确 completion time=false：它证明 submit→wait-return 关联，不自行证明 compute consumer readiness、publication/reuse cut 或 future 机会保留。

## Ascend 可读原件、ordinary 最小缺项

原访问：`zhiyuan_ascend`，`sudo -n -u chijin docker exec chijin_v3.5.x`。

设 `A=/tmp/chijin-timeline-r057-ascend/runs/controlled-density-v1`：

- actual source：`/tmp/chijin-timeline-r057-ascend/controlled-density-input-v1/p01_controlled_workloads.py`；安装：`/tmp/chijin-timeline-r057-ascend/runs/install-v1/output/venv`。
- ordinary：`A/output/BK32-density-1/32-ordinary-1/ordinary.{source,ttir,ttadapter,mlirbc,bcmlir,npubin}`。bcmlir SHA `47a6562b4be50965525ed93a01c4bb4f301c5577ab1349705be87adc4ea8f238`；npubin见上表。其它5份 ordinary artifact 核同。
- ordinary metadata：`A/output/compile-cache/IRGYNIFBRHY5BMNEET6OCFWQ42OE3RRQPGRPY5AUGODI7N5C5JLA/product.json`，SHA `8542efc4536e9c5f844a2e3e295bada4e6583b9bd876211b66ce5d4fd40f74b5`。完整 metadata 也保在本地 `ascend-BK32-density-details-v1.json`。
- 原 SDK：`/tmp/chijin-r15-sdk-scalar-legality/install-fixed/bin/bishengir-compile`，SHA `1f5cc5054402e901add18af133b3495b861775d68e2113bb8ba94667eef6cf9e`；`arch=Ascend910B4-1,use_bytecode=true,num_stages=1,multibuffer=true,auto_tile_and_bind_subblock=true,enable_auto_bind_sub_block=null,parallel_mode=simd,enable_auto_blockify=false,mix/bs_task_type=mix/32,bitcodes=[]`。原 `bisheng_options` 为 `-cce-link-aicore-ll-module /tmp/chijin-timeline-r057-ascend/runs/install-v1/output/venv/lib/python3.11/site-packages/triton/backends/ascend/lib/libdevice.10.bc`。

ordinary 的实际 SDK invocation/actor LLVM 在已查 `A/tmp/tmp*/kernel.o` 和全局 `/tmp/tmp*/kernel.o` 常见临时位置均未找到；这不是“所有服务器路径不存在”的证明。ordinary npubin 和上游 SDK 输入都在，但 **profile handoff 的 original-input-0.ll 是该 profile 的 late pass 前输入，不能冒充 uninstrumented ordinary**。

唯一必要补取可按原 metadata 与原 backend 有效选项恢复一次 owned CPU passive codegen，捕获实际 AIC/AIV 输入；必须生成整个 npubin逐 byte等于 `77d49b1a…8d0cd` 才接入 ordinary 解释链。原 CLI 收据本身未保留，不能把重建 CLI 冒称原收据。复用 R080/R089 helper 时注意 stages1使有效 auto-multi-buffer=false，auto-bind-sub-block=true；其余有效参数及 link资源按原 metadata/原 backend恢复，whole-object equality约束不能放松。无需数学/device、profile或新矩阵重跑，本次 reviewer 没有执行该补取。

profile 原件已齐，设置 `T=A/output/BK32-density-{1,8}/32-0/capture/timeline`，从 `index.json` 进入：

| mode | invocation | raw SHA-256 |
| --- | --- | --- |
| sparse1 | `invocation-29f2502d79e44b2389c77695306be227` | `3d15be391a1114026c169ea4809958ab59324646070b7048fa5c4cf816d0e07d` |
| default8 | `invocation-89ee5e07fa5d4eaca22dda0ed0dbac8a` | `617cf28cb29a7ec76eef2c1390935e5cf982401aac6bf4ec3f657beb6d0b32fe` |

actual handoff 已保最终 npubin association、SDK executed_command、retained original/adapted input SHA；late manifest 是以下每个 job 目录中的 `<manifest-stem>.json`，同 stem 的 `.ll` 是相应有导航信息的保留输入，另有 `original-input-0.ll`、`adapted-0.ll`、`receipt.json` 和实际 actor `output.bin`。

| mode / actor | A/tmp 下 compiler/compile/job 路径 | manifest stem | 实际 adapted LLVM SHA |
| --- | --- | --- | --- |
| sparse / AIV | `flagprism-ascend-compiler-wtsqmazv/8783f3f6-cfe0-4c2f-8842-aa0fd7188539/jobs/8c1da3ab-1878-4b6c-8107-8d47acbd7f0e` | `e6576dbcbeaea0e4170f29615537257ce0ee3f54c7409c7935aa24c145f4bf28` | `1680aed106b1430b259e8c45da401c2e80f5a78b42c3174d85d25eee4897ec58` |
| sparse / AIC | `flagprism-ascend-compiler-wtsqmazv/8783f3f6-cfe0-4c2f-8842-aa0fd7188539/jobs/a9aadf87-dbdb-486a-8f2b-8c83ab48f193` | `08a537d1f1d04cc010dac73c7f2b0d5a51787429df3558001c012ab42bf5cc74` | `fa38e7ec1aac09ba90ff47ad770929e6a7b73ed9a9621d0893515a7eaaec655a` |
| default / AIV | `flagprism-ascend-compiler-u6sxbfzj/06348174-868b-4570-a6d9-6cdaf77ba6da/jobs/926b3f05-5b1c-4510-b5e1-d4331aa51ede` | `4d695c977a763ecbf64057cf6a42e9a6aef708abd83744b29c984714fd7965cc` | `d1a7ef09475d9a0faffdec2b6ada410affbad4e0d4f2d9449871d99558b7ce44` |
| default / AIC | `flagprism-ascend-compiler-u6sxbfzj/06348174-868b-4570-a6d9-6cdaf77ba6da/jobs/ca11526e-bb10-4007-945d-5e5fbda2546a` | `020c41de6b9d7f5a6931c464e815c623623e223b2821ff42daa8dbe2ad19d7d3` | `d66cc1ee6eb06f66c80ae42461217f2b630b3ec01f2ab01b3d40d602d40ec2d2` |

这些文件现场可读。实际原/改写 LLVM 各有 AIV 6条、AIC 14条 SET/WAIT flag调用，保具体 `(source_pipe,destination_pipe,event_id)`，例如 AIC MTE1→MTE2 的 event0/1/2，以及原 CFG、buffer参数和 compute。manifest/site attributes 保 original block、native opcode/pipe/event tuple、debug marker 和 manifest SHA；raw records保observer、sequence、offset及ticks。`T/captures/<inv>.events.json` 和 `T/machine/<binary-id>/counter-map.json` 可读这些绑定。

此 BK32两种密度的 actual dependency status仍是 `unavailable: Native instruction/getter bindings are incomplete`；static_readiness是partial/空channels，不能据16/6等 opcode投影补 dynamic generation。最终SDK新增/未绑定flag以及它们与buffer consumer的有限连接应由现有实际输入/对象/manifest继续核；本次未授异步flow或把 issue当完成。这与ordinary LLVM可读性缺口是不同事实。

## 本次能交给下一步的最小材料

GCU：已有全部三方对象/IR，回收一份 ordinary artifact组、两个32-0捕获/manifest及上面两个dependency view，即可做实际 submit/wait/compute/buffer 和 recorder publication/reuse cut的有限对照。Asc：回收一份ordinary bcmlir/metadata/npubin、两个32-0捕获及四个actor job目录；只补取那一份 ordinary actual SDK LLVM，逐byte绑定原npubin。先确认普通对象里确有非空future机会，再检查两种观测密度保留它；本报告不从 `stages1`、名字、opcode数或相近 issue顺序预判结果。若没有该机会，应如实记录，不强迫人为制造并行图。

BK64 sparse原一正区间失败继续保留，未用于本报告 BK32正例或default资格；未扩controlled分母。已取得的R059/R062等数学、TP/UI与State证据按原scope复用，不因本次库存盘点失效，也不因对象齐全而自动闭其它门。

本轮新只读索引在 `run-090/preflight/`，不含 vendor CANN数据库，无产品修改。主要SHA：

| 本地索引 | SHA-256 |
| --- | --- |
| `gcu-BK32-density-inventory-v1.json` | `a3d8f28a340e6d8730b02f21ce6748a1a652a82c37586218a69081a50a5c00e8` |
| `gcu-BK32-density-details-v1.json` | `bf6cf4055da84f5fdd7e21265de91838f4506e0acd33516ceb8e360caad98bf1` |
| `gcu-BK32-pipeline-material-v1.json` | `ca066520e4a412e9ec8ffa7ed3dd62d38cb8962eae931c37534509e454b80629` |
| `ascend-BK32-density-inventory-v1.json` | `c866a153c2dbe87667a968fdc255f632ff123d84352ae086f1a707a022738c96` |
| `ascend-BK32-density-details-v1.json` | `fa089e11e527d755c84875ba3654d1953002a98c686634b03f24eedd3927b0d3` |
| `ascend-BK32-pipeline-material-v1.json` | `a846234e127fdf02812e3b69d7997d51dd058058ebc2c284ef28a6f8c15d2633` |
| `ascend-BK32-ordinary-locate-v1.json` | `e392690f7208c75548b046846adc21ea7ab8e5bdcc5a06d7f3f949397637e5d8` |
