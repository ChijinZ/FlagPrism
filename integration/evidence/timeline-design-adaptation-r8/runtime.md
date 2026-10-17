# 独立评审：运行时、资源与收尾

评审者：`/root/timeline_design_review_runtime`；GPT-6.1-Sol / xhigh / fork none。只读设计 §8.7–8.13、测试 §8.3–8.8，抽查 runtime、hook、CUDA transport、GCU compiler/native/TransferEngine；未修改、连接服务器或运行测试。本文件整理返回问题及依据，协调处理见 README。

## 初次结论

**方案总体合理、可实施；无 P0，建议补一个 P1 和两个 P2。** 设计评审不授予三后端设备、代码或 Perfetto 资格。

### P1：共同截止时间内 salvage 顺序不明确

设计 §8.7/§8.13 和测试 §8.7/§8.8 主要覆盖首 decode/export 失败，未覆盖首 owner 完成未知、后 owner 已完成。`hooks/timeline.py:177–183、261–275` 按提交序共享 60s deadline，首 owner 可耗尽时间，使后续 ready 连 readback 都不尝试。

建议非阻塞识别 ready，按共同剩余预算优先读取/持久化，再轮询 unknown；不保证无限 ready 都落盘，不无限延长 deadline。耗尽逐调用分 completion_unknown、completion_observed_raw_pending、raw_ready_not_persisted、raw_persisted，保所需资源/host bytes/身份，不报 all_saved。A/B 用例：在真实 capture 查询边界使 A unknown，B 已有真实完成证明，核 B 获 salvage 机会和预算不足时真实 pending/无应用重放恢复。不故意挂 kernel/改 driver；该故障注入不证明硬件挂死恢复。

### P2：owner 须保完整异步资源

GCU `TransferEngine.cpp:1195–1228` 初始化可能异步 memset/H2D，pinned host header、event 和 native handle 同须存活。`Bindings.cpp:832–839、890–898` 旧析构 release、`Bridge.cpp:130–147` 旧 init-first 异常回滚可能立即 release。

新 allocate_timeline_launch(..., false) 已有正确落点：先 handle 交 owner，再 initialize。默认 deferred transport 须在首次可能提交初始化前接管 device scratch、H2D/D2H host staging、完成依赖、native/context 引用，完成收据覆盖所有访问；不得由旧 prepare 回滚/临时析构绕过。分别测试初始化部分成功后异常、D2H 已提交后异常；CPU 延迟访问 fixture 证生命周期，真实正例证实际流顺序，不制造 SDK 硬故障。

### P2：raw 预算作用范围和单位需冻结

设计 §3/§8.7/§10 的总 raw 8MiB 容易混同单调用、在途峰值、累计留存。当前 pool 限 pending physical bytes 和 64 owners，累计 bundle 是另一额度；physical pair 与 canonical endpoint 也不同。

冻结单调用物理需求、session pending 字节/owner、累计留存/bundle 上限和 header/padding/guard 归属。超限在该调用初始化前拒绝；不需无限队列、后台线程或隐式同步回收。

## 应保留的边界

初始化也是潜在写者；timeout 不等于完成；隔离 session 不必原地恢复，安全清理后新 session 可运行即可。持久化与派生分离、重导不重放。two-stream/thread/graph 按后端冻结，不新增无条件并发门；advanced/旧 raw 不能替代默认采集。五部件按实际变化组合，无需第四设备、共同物理 ABI 或 engine busy。

最小实证沿既有 P/E：公开 runtime-K 数学的单/多 program、2D/tail、首末 writer、guard、side effect，声明并发的交错提交和独立 owner，真实完成 capture 持久化后派生故障及从磁盘恢复；再补 unknown/ready 用例，不扩大独立数学矩阵。执行留待服务器 Docker。

## 修订后有限复核

原 P1/P2 已在文档层面闭环，无剩余缺项。§8.13/测试§8.8 明确 ready-first、共同 deadline、四类状态、资源/bytes 留存与有界无重放重试，未承诺全部落盘；完整资源覆盖 device、staging、native/context 和完成依赖，禁止 legacy 回滚/析构绕过；§10/测试区分单调用、live pending、累计 physical raw8MiB，计协议开销、重导不双计、未冒称实现通过；A/B/C/D 一致。仅文档闭环，不代表代码/设备通过，未执行额外检查或测试。
