# 独立评审：编译、发布与适配边界

评审者：`/root/timeline_design_review_compiler`；GPT-6.1-Sol / xhigh / fork none。只读文档与源码，未连接服务器或运行测试。本文件整理完整问题、依据及建议；协调处理见 README。

## 初次结论

**有条件合理、可执行**。无 P0，无需推翻整体路线。compiler/transport/decoder/clock/mapper 的分工合理，保留架构事实，不要求逐算子适配；§8.11–8.13 限制空插件框架与 NVIDIA 模型外推。

## 问题与建议

### P1：guard 失败可能丢掉已经取得的原件

设计 §8.12/§8.13、测试 §8.7/§8.8 的留存合同有交接缝隙。抽查 `timeline_cuda_runtime.py:58–65`：allocation 已拷回 bytes，guard 不符却直接抛错；`timeline_runtime.py:194–214` 归 read_failed，raw 未交给持久化层。重读坏 guard 仍失败。

必须分开传输完成与完整性合格：安全取得的 raw、实际长度、坏 guard 先保留，再拒绝解释；真正未取得 bytes 的 D2H 故障单独记。完成已证明且原件已保存的 scratch 可安全回收。最小验收是在真实完成捕获的 readback 校验边界注入坏 guard，核最终磁盘原件、应用次数和 owner 回收；不能只用落盘后篡改代替。

### P2：有限 guard 不独证无大跨度越界

GCU `Passes.cpp:1244–1251` 的 byte stride / 4 对应 i32*，host `TransferEngine.cpp:1224–1228` 使用 byte pointer，目前对应关系正确。但单位错误可能使写址跳过尾部 guard；observer 缺记录能抓失败，不能代替地址范围证明。

冻结可检查不变量：stride 可整除元素大小，设备实际 slot 地址差等于 host 布局，每种 header/payload/commit 的最大 byte end 在 admitted extent 内、索引无溢出；核实际 pointer lowering。guard 补充实证。沿单/双/多 program、2D/tail 保推导与实际 IR/对象，错元素大小/stride 仅用合同拒绝负例，不在设备运行危险版本。数学输出 tail canary 不等于 timeline allocation guard。

### P2：复用 owner 状态机，不强制 NVIDIA 调用签名

`TimelineOwnerPool.prepare` 当前要求正整数 function、整数 device/stream 和 num_ctas，适合现有调用者，不是未来 target 必备形状。公共复用应为预算、唯一身份与潜在写者生命周期；loaded executable、execution context/queue、完成条件和布局请求由后端类型化封装检查。不得编造 function/stream；按第二个实际调用者提取合同，不预建类层次。

## 可行性与最小实证

编译边界风险真实，但已有 LLVM 依赖/noinline helper/memory clobber 落点；PTX 注释不是机器寄存器依赖，`timeline_nvidia_machine.py` 仍保 region_boundaries_verified=False。文档要求最终对象/路径与 ordinary、稀疏、较密三方对照，未把 marker PC、指令总数或正 duration 当边界证明，因此不能仅因尚未实现断言不可行。

GCU 尺度与异步、Ascend 新 timeline 可见性仍需小样本。每后端复用一份普通 load→runtime-K依赖数学→store（同 binary 改 K）及一份 ordinary 确有 async、两轮物理复用的样本，取边界、发布、clock 与 Trace Processor 证据，再扩大独立数学。无需第四设备或完美 engine busy。

新增 publisher 独立版本、cache 失效、writer 到达、逐 observer 非空、默认/advanced 分验和最终 bundle 重读可防原来的错误通过。整体无架构过度设计；重复章节应引用小合同，不各自演化新门槛。

## 修订后有限复核

原三项全部在文档闭环：P1 的取得 bytes/完整性分离与真实 readback guard 注入；P2 的 pointer 范围不变量和危险 stride 合同负例；P2 的 owner 状态机与类型化后端输入、完整异步资源集合。ready-first、分层预算和 A/B/C/D 顺序一致。

**无遗留文档问题；设计合理可执行，设备可行性与实现资格待实证。** 未扩大走查或运行测试。
