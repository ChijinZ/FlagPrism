# R081 Ascend source descriptor：有限独立 compiler delta review

在本次明确保留 `state_writer_qualified=false` 的离线模型范围内，未发现新增 delta 的具体正确性缺陷。新增 source 尺寸/stride 检查收紧输入，source 描述导出没有提升产品资格。SDK actor / transfer ABI 与 State 整体资格仍 pending。

## 实际阅读与身份

- 只读候选两个文件相对 HEAD 的完整 diff、相关 source/destination transfer 解释及新增测试；读取 R081 runner、输入归档、launch metadata 结构和 `ascend-state-partition-poll-v1.json`。没有重新审阅未变 LLVM evaluator 或其它后端，不读 peer。
- helper SHA256：`bfad3bcf27fcd193ac625b5b0dbd7eca17dde84c5d743742fee5a138031d621b`；测试 SHA256：`56c64ff262cb6663b2003823796d6369e6ff6dcb16caa57ca4ca8d6ca55f0c5a`。两者与 `ascend-state-partition-input-v1.tgz` 成员逐字节相等；归档 SHA256 为 `264254730afe4d4a9087b0c63d9dc3d8b740ffcfd0ee598475428a43738f4cbd`。此时两个候选文件为未提交修改。
- 未运行本机 import、checker、pytest、产品、SSH、SDK、编译器、数学、设备、TP 或 UI，仅本地文本、Git diff、JSON、归档与哈希读取。
- 请求配置 GPT-6.1-Sol / xhigh；实际 resolved 型号/推理档位未暴露，记为 unknown。

## Confirmed blocker / major / minor

本有限 delta 没有新增 confirmed blocker、major 或 minor。

helper 470–483 行对 source 的索引符合本轮保留的 descriptor 模型：1D 的 source offset/size/stride 为参数 2/3/4，2D 为 offset 2、sizes 3/4、strides 5/6；对应 destination 仍由既有 base=5/7 分支读取。`source_sizes == sizes` 继承 destination 尺寸上界；source strides 要求正且不超过 `2^30`。它没有修改已有 GM 元素地址、重叠/越界检查或 writer multiplicity 计数。

source offset 由原 typed integer evaluator 读取，再按其声明字宽作 signed 解释；aligned source 的 UB constexpr base 仅从参数 1 精确解析 `ptr addrspace(6) inttoptr (i64 N to ptr addrspace(6))`，未解析时明确导出 `None`。`source_byte_address` 是该 base，不包含另列的 element offset/stride。新增四个字段附着于每个实际 write instance，不会将无法解析的地址替成零或从最终 GM 范围倒猜来源。

测试 211–217 行两条 negative 只修改 source descriptor，保留原正确 destination 和 State transfer：一条 source size=2 / destination size=1，一条 source stride=0，均针对新的 `source transfer` 拒绝路径。没有通过破坏原 GM writer 或错误控制流掩盖目标检查，也没有增加数学或 native 调度解释。

## Matching CPU 收据

实际 poll 的 runner `script_sha256` 为 `b5db2ce3a8dbff3cf244d4e1b18bed11ebd89454ab8d7c5509f752b37332d1f1`，与输入归档 `run.py` 的 bytes/SHA 相同。terminal 为 0，耗时 `3019334265 ns`（3.019334265 s），实际预算 120 s；32 registered / checked / partitioned，failures 为空，checker SHA 为当前 `bfad3bcf...`。

独立阅读 matching runner 10–17 行可见它先执行最终测试文件的 normal / `-O` pytest，两条 child 任一非 0 即停止，随后才处理 32 原件和写摘要。因此该 terminal 0 支持新增两条 negative 随原 fixture 在双模式成功；按原 32 加本次 2 项，测试集合为 34 项。本次尚未读到完整 stdout fixture 日志，不编造日志原文或 child 耗时。实际原件检查由正常 CPU runner 进行，不声称对 32 原件另做 `-O` 数学或设备执行。

runner 19、26–28 行进一步绑定原 installed launcher SHA、实际 cached metadata SHA 和 registered compiled hash，并核对 `arch=Ascend910B4-1`、`enable_auto_blockify=false`、`force_simt_only=false`、`parallel_mode=simd`，以及 vector `(aiv,10)` / mixed `(mix,32)`。mixed AIV 的模型 count 从已核 metadata 的 `bs_task_type % 10` 取值，而非从缺失 trace slot 推断。它继续把 transfer ABI qualification 明确留为 pending；摘要也明确 `state_writer_qualified=false`、`device_executed=false`、`mathematical_application_replayed=false`、`source_loaded_qualification_tool=true`。

## 有限范围未证

`source_offset` 在这里是由整数类型限定范围的值，尚不是 UB allocation/capacity 的已证安全偏移。当前代码没有宣称 source descriptor 的完整 footprint 已落在已知 UB 分配内，也没有要求 `source_byte_address` 必须非 `None`。因此不能将“source size 相等、stride 正”表述成 UB 读范围安全或 SDK source→GM 实际传输语义已经证明；`None` 应继续按未知处理。这与本次 diagnostic/export 以及原 SDK ABI pending 相容，不要求为此扩大本轮实现。

本次读取的 poll 是 32 个结果的摘要，没有逐项证明每个新导出 source 字段都为具体常量；后续若以这些字段建立 ABI 关联，应使用对应完整 write-instance 事实，而不能将 base 与 element offset 混成有效字节地址。相应 SDK helper 对 source/destination sizes、strides、mode 的实际作用，以及 launcher metadata 到物理 actor 的关联仍是独立 pending，不因 metadata 严格比较自动关闭。

## Optional 与有限结论

没有要求新增 optional 实现或测试矩阵。源码、目标负例和 matching CPU terminal 足以支持本次 source descriptor 检查/导出服务的有限交付；完整 fixture stdout 回收后可仅追加日志核实。原 State 整体资格、SDK actor / transfer ABI、其它后端及 whole-goal 均不外推。
