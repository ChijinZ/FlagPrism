# R079 Ascend State writer：有限合同与证据范围

**结论：可以用与原 npubin 绑定的实际 linked/优化 LLVM，加明确的 launch/物理主体及最终写回原语 ABI，完成 V1；不另要求全 ISA 或反汇编所有数学。当前材料尚未闭合 State writer 资格。** 整个 npubin 逐 byte 重现解决了这份新增编译输入是否能解释原执行对象的问题，但不会自动证明 helper 内部写回宽度、物理参与者或唯一写者。

范围：正式 `detailed-profiler` HEAD `b508acf6e5153eac827b2dd31993bfaa4b1a90a7`、record T113；仅本项合同判断及已有文件读取。请求 GPT-6.1-Sol/xhigh，工具未暴露实际 resolved 型号/effort，记 unknown。

## 原门与已取得的证据

根合同 `timeline_goal_prompt.md:111` 要求合法 side-effect oracle；testing `Profiler/docs/timeline_testing.md:100–103` 对 ordinary/profile 要求：“oracle 必须有合法唯一写者或独立不重叠写入，先证明其实际 lowering；不能把不合法非原子多写者 State 当 replay oracle。”本席原 V1 的缺口是原 kernel State 的实际 writer，不能用 logger writer 或最终 State 恰好为1替代；这项要求没有指定必须使用某种机器反汇编工具。

已读实际 poll、passive inputs 和完整 probe 源码：

- `ascend-ordinary-lowering-poll-v1.json` terminal0，3.519929191s；实际 SDK `4a1312e7d3aa2d21a220b3acd081e90d7b4a3d043af5da98e8cfc681c13048ef`，底层 bisheng `2b5d17a037767ad41123868e14bedb91741b0682cafd1a2aa05a1da5d8b8bade`。runner 核原 math/保留对象 SHA，并直接比较产生的整个对象与原 npubin bytes；实际 `kernel.o` 为3648 bytes，`whole_binary_identical=true`，SHA `86d3a4b717d38cd23cf5ddf912ebdb130c0b08944a6b8a9e12beb2b8ae12c322`。不是仅 `.text` 核同，没有 device/math replay。
- 实际 bisheng 输入 kernel LLVM SHA `3a56e0820276d7a7f6e487de796350db8067278a7546389e86ae4ebeb257168c`；同时捕获实际 link 输入 `meta_op.aiv.bc` SHA `d5c10fbdcb1a976e888a2ddb2bcccd0b66febc10e959e044d141ad2760b63fa0`、libdevice SHA `9142883f2a38a17980b83c5d1e777744d823ddd4af370674015364dfc7eee11f`。这是实际 codegen **输入**，尚不是已展开这些库函数的最终 linked 优化 LLVM。
- `ascend-passive-inputs-v1.json` 内 device LLVM 行209起：`q03` 的 State 为 `%6`；行213–217用 `GET.BLOCK.IDX` 和 grid 参数投影 program，行267–274为 State i32 load、加1、写 UB5760，再调用 `store_ubuf_to_gm_1d_int32_t`，descriptor 的 offset为program、size/stride为1。wrapper行187–203只组装 memref 并调用 `_mlir_ciface_store_ubuf_to_gm_1d_int32_t`；行207仍是外部 declaration。当前不能由这个名字或 descriptor 推定最终仅写4 bytes或仅一个主体写。
- 实际 codegen 为 `dav-c220-vec`；host LLVM 的 `q03_infer_task_type_function` 返回10。这些是追查主体 ABI 的具体入口，不能仅据名称/常量猜测物理实例数。原报告为 q03-s0-c0 / grid17 / shape17×193；本次只解释该对象。

## 最小还须闭合的事实

| 必需事实 | 有限证据范围与判定 |
|---|---|
| 实际 launch 与主体映射 | 沿原 metadata/launcher、task type10、目标 ABI 说明实际 blockDim/grid参数、`GET.BLOCK.IDX` 含义，以及一个 logical program 有几个会执行 State 路径的标量上下文/AIV/subblock。证明 program 投影在实际实例集合上不重复、不遗漏；如多个实例共享 program，则须核实际 helper/调用路径如何选唯一写者或划成独立地址。无需新设备探针；明确的实际 ABI/SDK 实现证据可用。 |
| State helper 的真实 GM 写回 | 从实际输入的库定义/实际 linked 优化 LLVM，追 wrapper → `_mlir_ciface_store_ubuf_to_gm_1d_int32_t` → 最终 GM store/搬运原语。核 memref offset/stride 的单位、size1的实际写回 bytes、mode0、尾部/对齐/分块与主体条件；若落到 DMA/目标 intrinsic，给该具体原语的 ABI/SDK语义。不能把 size1 默认当4-byte物理写回，也不能将 UB store 当 GM State store。只追 State 相关调用闭包。 |
| 一次合法更新与边界 | 在上述实际主体/路径上核 State 地址来自正确参数且每个合法元素只被一次更新，不写过尾/guard；UB中的 load+1 值确实到达对应写回。仅核这条路径需要的 flag/wait/完成语义，沿用已有完成/readback与数学收据；不引入新 barrier、不重证整个浮点数学或全 schedule。相同 State值的多写者仍不能冒充唯一写者。 |
| 说明对象与原登记范围的绑定 | linked/优化 LLVM须来自这条实际 codegen 链，或另一条已核输出与原对象相同的被动取证链；不能把任意 `llvm-link/opt` 产物直接叫实际最终 lowering。把结果连接原 State/math/host-once、目标、配置、实际 grid/参数与对象 SHA。本 q03证明不自动授其它 ordinary/profile；相同 helper/主体规则允许复用，只核各原对象的 State调用/参数适用，不要求重跑原数学或全部重编译。 |

这些事实若能在实际 linked 优化 LLVM与明确 ABI 中闭合，就已达到原门。若只有某个末端 intrinsic/主体约定仍不透明，只补该局部的 SDK/目标语义依据或对应窄机器片段；反汇编 `<not available>` 本身既不授资格，也不构成必须全 ISA 审计的理由。

当前属于 **verification gaps**：物理执行实例与 launch 映射尚未解释，外部 State helper 尚未追到实际写回语义，未有完整原登记覆盖。没有据此确认 State 实际存在重复写入，也不授 q03/Ascend V1 或 whole-goal 通过。现有原件、数学/TP/UI/SDK与安装不因本范围判定而要求重跑。

## 审阅来源与限制

本席只用 Git/stdlib 读合同、T113、上述原始收据/捕获 LLVM和probe源码，没有执行产品、测试、SDK或设备。一次对 runtime/已跟踪 State evidence 的宽文本检索意外返回 R078 其它审阅报告片段；未用其结论作本次 Ascend 判断，故不声称完全未见 peer 片段。上述结论依据本次实际调用断点与原 testing§4，不依据该检索片段。

原件 SHA256：poll `ed385937f4c3c333a1b38e89b8f740dbe6f305f5154f63284b1f1eeeb30ce2b9`；passive inputs `b8cae968bb27ca8a019de100a48fd6dfab12369bb8f8c7a7443770a99b27bc42`；probe `207fc54f9715337e4c15b75e8a847b45b0f97671870aebe0c9faad11b45049d6`。没有读取或修改私有 SDK文件，仅阅读已留存的输入文本/摘要。
