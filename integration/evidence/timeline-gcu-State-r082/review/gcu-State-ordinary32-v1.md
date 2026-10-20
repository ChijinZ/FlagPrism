# R082 GCU ordinary32：State 物理写者有限组合复核

**结论：可以关闭原登记 ordinary32 的 State 物理写者门。** 范围为24个 primary ordinary 加8个 runtime-K 调用、24个不同原编译对象；不包含 profile、补二、native schedule 或 whole-goal 资格。本次未发现该有限范围内的 confirmed 缺陷，也没有剩余的 ordinary32 writer verification gap。

请求配置 GPT-6.1-Sol/xhigh；工具未暴露实际 resolved 型号/effort，记 unknown。仅只读源码及保留收据，并用 stdlib 核 SHA、连接身份和重算已记录的 descriptor 范围；未 import/执行产品、checker、测试或 SDK，未访问设备/SSH，未读 peer，未改实现。观察 candidate HEAD `6e6fa4ac2bb256763e493529f5afd3d89fd0bc5b`；本结论绑定下列具体文件 SHA，不给整个 HEAD 签字。

## 复核依据与身份连接

原合同 `Profiler/docs/timeline_testing.md:103` 要求 oracle 有“合法唯一写者或独立不重叠写入，先证明其实际 lowering”。本次是在既有数学/input/tail/host-once 收据上补实际物理 writer 分片，不把最终 State 数值正确单独当作 writer 证明。

- 已完整读取 candidate `tests/timeline/gcu_state_writer_partition.py`，SHA `7aeadcab3ecb2e6e64f37fb86d8479cf88f3400de7cd5d5d33dc998810e2102e`，与实际 `State-partition-input-v4` 保留副本逐字节相同；读取其 runner、30项正反例及 normal/-O 日志。runner SHA `ae103b2965c339bd8557a524dc8a5275a7da208d09c70473773d9bc497cf410e`，fixture SHA `1b48bb1a87e56c027f08210f7f2e274ed8c83baadf372570567b59da7aff93f7`。
- 从 R078 原 archive 读取 `state-inventory-v1/output/inventory.json`，32个 row 与 R082 `gcu-original-State-inputs-v1.json` 内的原 row 完全相等。后者每份 LLIR/TTIR 文本均重算 SHA 核原 artifacts；本次逐32行连接 `(id, variant, math_sha256)`、原 grid/config/compiled_hash、原 LLIR、R081 whole-fatbin binding、R082 translation 和最终 partition rows，无不符。
- R081 原 `original-compile-v2/output/rows.json` 的32行均为原 fatbin SHA = 实际重编 produced fatbin SHA，`whole_binary_identical=true`，关联24个不同对象；本席此前已读24份实际对象收据。本次再核每个 translation/partition 引用的 whole-binary SHA 均与对应原 artifact 和该绑定相同。SDK builtin 仍为 `fa9d850080258f7cfd3acbdccfdb3485007b9b87c3c5ed34ab187dacbb52944a`，不是另一版库解释另一份对象。
- 读取 `translate-input-v3/{run,row}.py`，逐32行核实际 translation result SHA、LLVM SHA 及原 source SHA；对24个不同输入独立重建“仅移除 GPU module 容器”的文本，与实际 `input-LLVM-functions.mlir` 逐字节相同，原 LLVM 函数/操作行未改。实际 SDK translator SHA `f93024f7d86828022bc6b61d77c02522195d25df5ad76ac634d909efe74bb361`；24份结果 exit0。这是原输入的 LLVM 语义分析视图，**不是 post-link/vendor-final/native IR**。

以上对象逐字节重现链加实际 SDK ABI，可用于本门的有限物理写者判断；不另要求完整 ISA、全部数学反汇编或新设备数学。

## ABI、入口与实际 caller

复用本席已手工核过的实际 SDK 搬运/getter 定义及 launcher，并在本次对接最终 checker 与实际文本：

- R080 实际 installed backend SHA `ccd500895c64cf19330071a3da156c113d001391c064beb1a458b93ea82f71e8` 的 `:475–478`：本批 target 是 gcu300，launch 为原 gridXYZ、`(num_warps,1,1)`；gcu500 的乘128分支不适用。getter 实际定义直接读对应 `tid/bid` 轴。本批4/8 physical threads 各16行，枚举域没有再乘 warp_size12、32或128。
- 逐32行由原 TTIR 具名 State 的形参位置，核实际 opaque LLVM 外部 entry 仅原顺序、原指针转发到内部函数并 return；与 rows 的 `State_formal` 一致。原 LLIR 的 num-warps 与原 launch config 相同，threads-per-warp 为1。不是按临近 store 或算子名猜 State 根。
- checker `:180–263` 分开 State source、destination、context，找可达 State 写原语；拒绝未知 State callee、直接 store、State pointer escape 和未知指针来源。Pad 只允许 State 在实际 source 位置（1D index3/arity8，2D index4/arity12）；destination 被拒绝，读取不计 GM writer。
- checker `:265–487` 沿 typed integer/address/predicate cone 枚举实际 block/thread，保 word 宽度、signed 解释、溢出/poison检查及定义支配关系；未知分支保两路，不能任选有利路径。`:489–506` 对活跃 writer 检查不能绕过到 return、不能在循环重复，不借用不存在的 SDK thread0 guard。
- 实际 q03 scalar 路径中 State 地址为原 State 加 `4*bid.x`，真实 `tid.x==0` 控制最后4-byte GM写回；State DMA read→wait→本地加1→mfence→写回→wait 与原数学/once 链相接。向量/矩阵允许多个实际 PU 写独立区域，并非把所有 case 强制归成 thread0。

本次发现 checker 实际地址/谓词 cone 还调用四个整数 helper，已补读同 fa9 库的 `enflame-State-integers-source-v1.json`：`remsi=srem i32`、`maxsi=icmp sgt/select`、`minsi=icmp slt/select`、`extsi=sext i32 to i64`，与 checker 的对应规则一致。实际 extraction terminal0、库输入 SHA 核同；文本 SHA `4f4c5d44622db0043895798f6acbdc9d47429200bf1a3f2395d75a5e8460cf9b`，JSON SHA `4a6595c03d9a77b1bedc1be254bf777a2c9d1efa9085a10f9fa6fa25228adbbe`。本批未调用的 div/floordiv 不从这里获得额外 SDK 资格。

## 搬运窗口与 rows 的独立核算

实际完整搬运定义为 `enflame-State-primitives-source-v2.json`，文本 SHA `2c1799b3a316d4a08bd66aa6649dfc224087e07c13f7e001250dc395bc56d566`。本席此前逐函数核的 D/S、尺寸、offset、4-byte元素/byte单位及无隐藏 writer guard，与最终 checker `:507–594` 对应：

- memcpy 直接按 byte 数；1D deslice 取 `min(Slen,Dlen-d)`；1D slice-deslice 参数顺序确为 source offset、requested length、destination offset，不能互换。
- 2D deslice 没有借用不存在的 min，要求整个 source shape 能放进 destination；2D slice-deslice 按 source offsets、R/C、destination offsets 解码并核有效 source 窗口。负长度、错误窗口不能自行归零为 no-op。
- 写入按原 State pointer 的4-byte对齐偏移和 row-major 目标位置展开，每个元素必须在原 extent 内且至多一次；runner 再要求原全部元素均覆盖一次。

本次没有执行 checker，而是从最终 `rows.json` 的每个 descriptor 独立按上述 SDK 公式重算全部934个 writer instance，并核原 grid/thread 域、有效 source/destination 窗口、元素个数、目标边界和累计 counts。结果：

| 实际写回 primitive | instance 数 |
| --- | ---: |
| `tops_deslice_async_1_si32` | 448 |
| `tops_slice_deslice_async_1_si32` | 16 |
| `tops_memcpy_async` | 144 |
| `tops_deslice_async_2_si32` | 260 |
| `tops_slice_deslice_async_2_si32` | 66 |

32行累计 **51,076个 State i32 元素均恰一 writer**，重算 counts 与保留 `element_writers` 完全相等；目标没有越过原 allocation。所有实际 source 窗口有效、934次均非零写入；没有以假设零长度语义放行。4-byte对齐、完整字覆盖及目标界内共同给出该批 State payload 的逐byte独立写入，未向 tail/guard 扩写。q01 的最后 program/1元素 tail 已落在实际 slice-deslice 路径中，2D caller 的两种实际写回分支均纳入上述计数。

## 实际收据与限定结论

`State-partition-v4/terminal.json` 为 terminal0、`2.969512766s`，脚本 SHA 核同；normal/-O 各30项通过。负例包括重叠、错单位/OOB、未知谓词/callee/别名、逃逸、重复 writer、poison、非法 source 窗口、2D deslice 误裁剪和 Pad destination。资格检查使用显式 `_need`，不是会被 `-O` 去掉的 assert；pytest 的 optimized 提示保留，没有当作产品 gate 被跳过。

关键原件：`State-partition-v4/output/rows.json` SHA `c6a5332cda605c7a44488beaa94f188feba72522abd1f0a4ff1cb67aa139e6eb`；其 result SHA `33da8a8fb3c613e46eeae8188f0f3db3042824f0d7b1ea2e48793281cad6346e`；`translate-v3/output/rows.json` SHA `f6c8f72bf5527fd7761df088d2e612bb814b42534c31c92a5fd908d813ea4c33`。均位于 `run082/preflight/enflame-receipts-v1/runs/`，旧失败和旧版本收据仍保留。

原始 CPU 收据保留 `state_writer_qualified=false`、`SDK_transfer_ABI_verified=false`、`vendor_final_IR=false` 正确表达其执行自身不授资格。本次独立 review 将实际 SDK/launch ABI、原对象重现链和32行分片证据组合后，关闭的是 **GCU ordinary32 物理 State writer** 这一门；无需改写历史收据或再采相同数学。profile、补二、source/native loop、时间边界/依赖及 whole-goal 的未闭门不由本报告关闭。
