# R081 Ascend State transfer/actor ABI：有限独立核查

**结论：新增原件足以闭合这批32份 ordinary（24 primary＋8 runtime-K）的 State transfer/actor ABI 缺口，并支持该范围的合法物理写者判定。** 依据是实际 caller→memref wrapper→原链接库→明确搬运 ABI、实际 launch 与同目标主体机制的连接，不是把32/32逻辑分区或最终 State==1直接当物理证明。无需全 ISA、全数学反汇编或设备数学/TP/UI 重放。本报告不授完整 Ascend V1 矩阵或 whole-goal 通过。

请求配置沿用 GPT-6.1-Sol/xhigh；实际 resolved 型号/effort 未暴露，记 unknown。本次只 Git/stdlib 读原件，未 import/执行产品、测试、SDK或SSH，未读 peer 报告。未修改产品。

## 对象与实际 caller→库的连接

- `run080/preflight/ascend-byte-bound-callers-v1.json` 对应20个不同原 npubin。19次 CPU 重建各有与原 npubin **整个对象**相同的输出；另一个 q03 复用本席已核的 R079 整体逐 byte 相同链。mixed 编译另有不相同的中间 cube/vec `.o`，不把中间对象误当最终 npubin，也不要求它们与整体 ELF 相同。没有数学重放。
- 实际原链接 `meta_op.aiv.bc` SHA `d5c10fbdcb1a976e888a2ddb2bcccd0b66febc10e959e044d141ad2760b63fa0`，已核留存 bytes；递归提取的 `state-writeback.ll` SHA `baeb0d48d5a3c80b1e00622282722e4f28b3eee47efc8585999a21c85306a6e2` 与实际 extraction 收据相同。它是原库定义的完整相关递归闭包，不冒称已 dump 整个 kernel 的 post-link 优化模块。
- `ascend-actual-transfer-wrappers-v1.json` 补齐实际 caller 到库 memref 的一层。独立核20处 wrapper 均精确存在于其 SHA 绑定的实际 LLVM中；两个完整定义 SHA 为 `f31a1e9498905d72cb2e47f2fb7fe9b56b9b2cd0b9625056a66fdf445781ad03`（1D）、`bd9ea7c995aa89d1b30240bf4929e67282639fab1113f12d1d2df21541461b9e`（2D）。`insertvalue` 确实按 allocated/aligned/offset/sizes/strides 构造对应 memref，`alloca/store` 后交给实际 ciface；atomic 参数原样传入，没有把 size/stride次序调换。q03的原输入文本 SHA 也已单独核同。

因此这条证据不是从一个同名 helper 推测另一个二进制，也无需再人为重建一份任意 `llvm-link/opt` 模块来代替实际链。

## 手工核到的写回范围

具体位置均为原库 `state-writeback.ll`：

| 路径 | 实际定义与范围 |
|---|---|
| ciface / atomic | `:329`、`:1436` 把1D/2D描述符交给 core；本批实际调用末项全部 atomic0，`check_atomic_none :287` 接受0。证明依赖非重叠的普通写入，不用 atomic 掩盖重复 writer。 |
| 标量及前缀 | `:628`、`:1977` 的标量循环从 **source sizes** 取循环界，用各自 source/destination strides、offset及 `getelementptr i32` 读写单个i32；`:763` 的前缀处理取 `min(misaligned_prefix,source_size)` 后同时前移两端offset并缩小size，不越过原描述符。它们是相关闭包的实际 fallback，不能把一切 stride 都当1。 |
| 连续1D | `:883–929` 从 source size取长度，传入 `burst_count=1, burst_len=4*size`；两端offset均为i32元素单位。q03/q04的 scalar State descriptor size1因此是4-byte有效载荷，而不是无依据地从“scalar”推测一条物理store。 |
| 连续末维2D | `:933–1209` 取 source rows/cols，`burst_len=4*cols`，`gm_gap=4*(dst_stride0-cols)`；UB gap 为 `ceil(src_stride0/8)-ceil(cols/8)`，单位32B。必要时逐行降为1D；本批行数远小于4095分块阈值。 |
| 最末端 | `:1212–1264` 用i32元素offset形成两端指针，将 count放入控制字bits4起、byte length放入bits16起、两端gap放入另一控制字，调用 `llvm.hivm.MOV.UB.TO.OUT.ALIGN.b32.V220`。本批参数未触及掩码/截断上界。 |

本次关键的末端 ABI 已补实际 CANN header，**不再只是 intrinsic 名称猜测**：

- `ascend-transfer-ABI-header-v1.json` 中 `dav_c220/kernel_operator_data_copy_impl.h` SHA `efb584d2ca41a9d3a316eef039d4fce469477b81b4ee8ec5ac9123cdcd76703b`，`:519–533` 将 UB→GM DataCopyPad 的32bit分支接至 `copy_ubuf_to_gm_align_b32(dst,src,0,blockCount,blockLen,0,0,srcStride,dstStride)`，padding参数为0，并用 `CheckGmMemOverflowNormal(dst,...,false,true,params)` 核 GM extent。这层用于确定相同 primitive 的 ABI，不声称 AscendC header里的 actor guard被插入了原kernel。
- `ascend-native-transfer-span-v1.json` 中 `kernel_utils_base.h` SHA `806176189df399f1ea84c87f0f5b91cdd9332092e12fbb82adfaae31530ec288`，`:303–321` 的 ExtParams `GetGMLen` 在 `isSrc=false,isMovAlign=true` 时选 **destination stride，长度/stride单位均1 byte**；非零长度的 GM span 为 `count*blockLen+(count-1)*dstStride`。该同SDK实际API语义明确不把 GM 尾部扩成32B；UB源的块对齐/行间距不能误用成GM写入宽度。这个范围依据已足够，不需要为该 primitive 再建任意 ISA 解释器。

`run081/.../state-partition-v1/output/rows.json` 的每条实际写入已保 source_offset/source_sizes/source_strides/source_byte_address。本席独立核全部 source sizes与destination sizes相同、source strides正、实际 source byte起点均32B对齐；1D stride1，2D source `[32,1]`、destination `[N,1]`，零size走no-op。本批实际不需靠未对齐fallback补推写入范围。对2D每行，最终GM写区间正是 `4*(Doffset+i*Dstride0)` 起的 `4*cols` bytes；source行的32B取整不会增加destination尾写。因此现有逐元素分区可以落实为实际GM字节分区，tail/guard不会被DMA整块补写。

实际统计为365个transfer调用实例，source_offset全0、最大单维size256，其中6个含零维；按原SDK `is_no_op<1/2>` 它们不写GM，不把“调用到helper”算成真实payload写入。这里没有新增UB容量或全SDK解释门。

## 实际 launch 与主体

`ascend-original-launch-metadata-v1.json` 的原 installed driver完整文本 SHA 已重算为 `07ece28ddf331e61c3dc16018db104b0bc50c96621d2feefdd3419d6a8075859`。32个原cache metadata均为 `Ascend910B4-1`、`enable_auto_blockify=false`：24行 `aiv/bs_task_type10`，8行 `mix/32`。32份新分区记录的 metadata/math SHA逐项与这些原件一致。

driver `:830`、`:877` 确认实际 `rtKernelLaunch` 使用 grid乘积 blockNum，`:915–933` 按真实参数 ABI传入用户指针和三个grid值。`:554–563` 的10/32解码分别为AIV、MIX_AIC/ratio2；其中 ratio写入msprof信息本身不是设备参与者证明。

主体机制另由原 R060 `ascend-participation-evidence-v3.tgz` 的实际 device terminal0与原 getter记录支持：同 `Ascend910B4-1`，vector GET.SUBBLOCKDIM count1，mixed为AIC count1＋两个AIV、各count2（flags257/513）；不是按reserved slot数推演员数。这是同目标的机制证据，不是这32份原数学被重跑。

actual caller已用该主体语义区分两种合法写者形式：q05 c0的State写回受 `GET.SUBBLOCKID()==0` 控制；q05 c1 / q06按subblock分行（例如16行tile分成两个8行片段），尾部size随剩余行数缩小。八份mixed AIC函数的State参数除函数签名外没有使用，State写回在AIV函数中；本席逐份核过，不依靠logger observer数量排除AIC。纯AIV使用单个实际AIV标量上下文，不能再添加一个假定的NV warp/lane复制维度。

## 有限判定与余下范围

已读 R081 `ascend-state-partition-poll-v1.json`：terminal0，32/32 partitions，normal/-O各34 fixtures；实际source descriptor范围和metadata绑定均已导出。本席直接核新rows中每个合法元素writer数均为1，并用上述手工库/ABI检查补足其原来显式保留的前提。旧 `state_writer_qualified=false` / `physical_transfer_ABI_qualification_pending` 是该执行收据的原状态，应保留，再以新的有限判定/派生记录连接ABI依据；不能修改旧收据冒充首次已经完成语义核验。

**本次 transfer/actor ABI 子门无剩余实质验证缺口，未发现 confirmed 实际写回缺陷。** 对这32份已绑定ordinary，可将其State物理writer缺口记为已补证。完整原V1还须覆盖原登记profile及补二等其它实际对象；本批材料没有给那些对象作覆盖收据，本席也未重评它们。若尚无对应收据，最小后续仅为在已有留存对象上复用这组helper/actor规则、核各实际State调用与launch适用性并连接原math/host-once，不新造数学、重采设备或重跑TP/UI。scope明确非whole-goal签字。

主要输入SHA：callers `6f0cf67ada8701894f4add4122d847d6fa2033520c4b6d2d831abd37a6fb4dd9`；launch metadata `81616ed4dd95f5424b689e5d48817294a3278cc286a67798a151b0e4a2820c05`；wrapper桥 `eecf9a8d06619317ba0eef68a986125c5bb0f55d6b9b7d9c2fa6faf1383dc483`；transfer header索引 `385aaa5e158157abf5741e2fea850a9eb961cf77ce214a5e2c9776d31989c7cf`；GM span索引 `cf2aef4be3f3c2da1c6451d8fe5adce78eb56b27ecc092aa49a26597c0346936`；R081 poll `5972e3fccdfaa73251988a803b4a6aa40856853f904f59a783a781d1a69e0434`。
