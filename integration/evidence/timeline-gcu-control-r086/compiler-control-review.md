# R086 GCU direct-control packet 索引：有限独立 review

在本次限定的“已绑定 ELF bytes、caller 提供 code extent、只索引已支持显式 packet 控制边”范围，未发现 confirmed blocker/major/minor。v2 实际索引正确保留了共同 reader 与公共 record body 的不同 join，并如实保持两个对象的 `direct_control_complete=false`。这不是完整 CFG、三个入口 tuple 值流或 source/loop 资格。

## 实际阅读与源码身份

完整阅读 `Debugger/python/flagtree_debugger/gcu_native_control.py`、`Debugger/test/test_gcu_native_control.py`、`check_gcu_native_control_v2.py`、v1/v2 poll、parser-gap 原始诊断及 input-v2 归档；并读取 R083 两个 matching loaded 原件身份、ELF0 descriptor、相关 native 控制窗口。仅使用本机只读文本/JSON/归档/hash；没有 import、测试、产品、SDK、设备或数学执行，未读 peer。

本次 helper SHA256 为 `62235c0c3b41e2daac9d3686b695e46c1cee11f2409a5ee1710c00cfd065234e`，测试为 `a34ff76682297f1463ea5d1515805e3e851fbf25102aa7e9848129e83ff321a8`，与 input-v2 root/package helper、测试分别一致。input-v2 归档 SHA256 为 `2f1292a952a0d335edd027b11a202d3595694e37c999a9a5072dec101a292744`；runner `2f09d9ceed12d8e9ff97483e74e74455a722cc116ab91059dc87cbce798dbec0` 匹配 v2 terminal。请求 GPT-6.1-Sol / xhigh；实际 resolved 型号/档位未暴露，记 unknown。

## direct-edge 规则判断

helper 50–65 行要求半开、16B 对齐且有界的 code extent，最多 65,536 packets / 100,000 decoded rows，并拒绝重复、无序和范围外 PC。它按 packet 起点聚合实际指令，不将有效 branch 的 `+0xa` PC 当作目标 packet 或 fallthrough 起点。

68–78、98–104 行对已支持 conditional 记录 taken 和下一 packet 两边，对 `jal r0` 只记录 jump；target 必须唯一并对齐，范围外 target 明确是 exit。没有按 predicate 值猜测删边。每 packet 多个已支持 transfer 被拒绝。普通已知非控制 packet 和 caller 已核零/NOP packet 记录 fallthrough；return ABI 形状 `jalr r0,lr,0` 与 halt 没有本地 continuation。它没有解释条件寄存器、证明 return LR 值或推导迭代次数；这些均不属于此直接边索引。

未知 opcode、hardware `loop0`、call 和其它 `jalr` 均进入 `unknown_controls`，123 行以非空 unknown 阻止完整声明。调用/间接跳转并未假装存在一个已知的普通 fallthrough；其它未知 opcode 所在 packet 虽可保留候选 fallthrough，也始终伴随 unknown。**因此 edges/predecessors 是已识别的显式边索引，不能在 unknown 非空时拿其缺边排除路径。** 当前没有接入会误用它的资格入口，source/external/begin-site flags 全 false，这不是已确认实现缺陷。

这份索引只关心 packet 间控制，不解释 packet 内数据 forwarding；不需要把值流组件的 RAW/WAW 拒绝机械套到无寄存器求值的索引上。沿用原 GCU 已支持的 direct branch packet 语义即可，不要求重建所有 ISA。

## 原件完整性与 descriptor 修正

v1 whole terminal 1，`wall_ns=715961309`，因全 `.text` 非零 byte coverage 检查拒绝，没有 result。parser-gap 诊断的 15 个未覆盖非零 bytes 均落在 ELF0 `0x1b90` 的 `.dtu_kernel_code_t`；原 native 确实把它打印为 vendor descriptor，而不是指令。应保留这个失败事实，不能把 v1 当完整原件检查已过。

v2 runner 19–23 行逐条把 native 显示 bytes 与唯一 executable section 的原 ELF bytes 比较，28–46 行核其它所有非零 executable bytes 的 coverage；只将从原 objdump descriptor 得到、并与同名原 ELF symbol value/extent 对应的 metadata prefix 单列。不是通过忽略剩余未解码 bytes 放行。

本次实际 descriptor 为 `entry_offset=128`：ELF0 `polynomial` 的 descriptor base `0x1b90`，code size 95,536，symbol extent 95,664；code extent 为 `[0x1c10,0x19140)`。ELF1 `weighted_moment` code size 92,944、symbol extent 93,072，code extent `[0x1c10,0x18720)`。entry、code size 对齐，范围在实际 executable section 内，传入 index 的 rows 已裁到该 code extent，未把 boot、descriptor 或后续 helper body 当作该函数指令。

这仍依赖原 LLVM11 decoder 和原 ELF/symbol 的既有身份链，不是重新组装替代对象的证书。全非零 coverage 也只排除未交代的 bytes；不能自动推出任意间接入口、ABI return 路由或全部 hidden hardware control 已解释。

## v2 实际证据

读取 `gcu-control-poll-v2.json`（SHA256 `f3608339a6673c5cb8f63738e94b621e3d12e23bbb5377b7d7ce9f15d04a3609`）：实际 terminal 0，`wall_ns=966368442`（0.966368442 s），预算 180 秒。result 的 control helper SHA 为上述当前版本，reader helper 仍为 R085 `dcc0d5eb8a5493dc8b2bda43acb4cb9695631d339855299c7badbea4ded42812`。

ELF/native 身份仍为原 matching loaded 对象：

- ELF0 `7d56f25f70633d7f0d813a78e8ded073b884a4356d940a4cb48c710794f00500`，native `a4423a389544cde04466ad381de272754c8c79d3860eabc48dd86898a9015e8b`：5,971 packets、6,508 indexed edges、6 unknown controls，完整标志 false。
- ELF1 `5860432eef0a3004e35740a68b17b10bd9f33d49bf3ab7a30f8cb11be72131f6`，native `3e15c05637ef8ab999165d5496ebe07e7dff1967aa648828437c65038c063935`：5,809 packets、6,298 indexed edges、63 unknown controls，完整标志 false。包括未建模 vector/算术 opcode，也如实记 unknown，没有为得到 complete 而推测其控制效果。

ELF0 的两个 query 由实际 native 对应：共同 reader packet `0xaaa0` 已知直接前驱为 `0x68a0`、`0x85b0`、`0xaa90`；record body packet `0xabd0` 前驱为 `0x9720` 的 direct jump 与 `0xabc0` 的 fallthrough。原 native `0x972a: jal r0,...<0xabd0>` 确实存在，且直接跳过 `0xabce` 的 `c.li r10,0`。所以“共同 reader 只有三条已知前驱”不能被当作 record body 只有那三条路径；新索引揭示的是需要后续值流纳入的另一入口，不能沿用先前共同 end 的局部证明覆盖它。

原 reader 成功数保持 5/11 与 9/12，九项 unknown 保留；已选 shared-end → 32 bridge → 原 relative tail regression 仍通过。这只说明新增索引没有改变原有限回归结果。

## Verification gaps 与最少后续

runner 先运行新 control 12 fixtures 和原 values 37 fixtures 的 normal / `-O`，任一失败停止，再做原件检查；v2 terminal 0 支持这条执行链。源码可数为 49 fixtures。本次尚未读到回收的完整 stdout，不能声称已逐日志核验；如做最终同版封存，补读取两日志和最终格式后源码身份即可，不需新设备或数学回放。

索引的 caller 前提是完整 byte-bound instructions/code extent，空 packet 必须由原零/NOP bytes 支持；脱离此输入绑定单独调用不能证明 text gap 是 NOP。当前 v2 runner 对这两个实际对象提供了该有限输入链。

下一步局部值流至少须把已发现的 `0x9720→0xabd0` 入口及其实际 high/low/identity/begin/site/初始化状态纳入，或对未覆盖的入口明确保留 unknown；不能仅因 index 查到 `0xaaa0` 三前驱就忽略公共 store body 的另一个 join。**不要求为交付这份有限索引先解释全部 6/63 unknown**，也不把未知项当运行功能失败；但不能据不完整 index 的“没有发现其它边”作入口穷尽或 all-path 结论。

未发现需要另外提出的 optional 修改。组件仍是 source-loaded、未接自动资格入口的内部服务；external entries、MMIO、selection、ring、incoming begin/site、source/loop 及 normal-installed/whole-goal 资格均未授予。它可作为后续有界值流审查的 direct-edge 输入，不能代替该值流结论。

## 最终格式与 matching 收据追加（control-v3）

已读取最终 helper `90a0c4343e0b0193583500bc2bbabacd25a1b74d47e499ca39ea530190a61f83`、测试 `f59c923e00a9e5a8e80267355bd047912ab213c6a53656978deb90e936b606d9`；它们与 input-v3 的 root/package helper、测试分别逐字节一致，与 format-input-v1 内上述初读源码分别 AST 相同。input-v3 归档 SHA256 为 `ff75fea414c91298bc2bf24d84eb1f43234e32550abbb4244d5d0b498316d5bb`。

实际读取 `gcu-control-poll-v3.json` 及回收的 `gcu-receipts-v1/runs/control-v3/output/{normal,optimized}.log`、`result.json`，poll/result 逐字段相同。terminal 0，`wall_ns=966356002`（0.966356002 s），180 秒预算；normal / `-O` 各 **49 passed in 0.05s**，`-O` 只有预期 pytest assertion warning。`gcu-hooks-v1.json` 三项 ruff/yapf/check-ast 全 0，源码 SHA 与最终文件相同。本复核未执行这些测试。

最终版保留 5,971/5,809 packets、6/63 unknown，两个 `direct_control_complete` 均 false；相同 code extents、descriptor/symbol 绑定、全非零 bytes coverage、两组实际 reader 和 shared-end tail 结果不变。reader 三个直接前驱与 record body 的 `0x9720/0xabc0` 两前驱均保留。至此仅上述最终同版源码/日志验证缺口闭合，没有发现新的 confirmed 缺陷，不提升任何原资格或 whole-CFG 结论。
