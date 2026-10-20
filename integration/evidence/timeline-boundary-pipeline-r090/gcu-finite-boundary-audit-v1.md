# GCU ELF0：有限 source / shared-end / runtime-loop 人工核查

请求配置 GPT-6.1-Sol / xhigh；resolved serving 配置未暴露，unknown。本次只读指定实际原件、相应 LLIR、R084–R086 小结果及 R069 已有 source/raw/JSON；没有执行产品、checker、测试、编译、设备、SSH、数学、TP 或 UI，没有阅读其它席报告。只写本报告。工作树 HEAD 在本次期间已变化，结论绑定下面的原件 SHA，不绑定移动的 HEAD。

**R088 中明确点名的 ELF0 三路 shared-end、site4 另一路 record 入口、输出两路 shared-end，以及 polynomial 的 source39 runtime-loop，现可接成下表。在这一冻结对象和所列范围内，没有剩余的 begin/site/identity→end→record 具体断点，也未发现错接 site 或跨 observer 配对的实现证据。** 这是一份实际 compiled object 的有限人工补证；不改原收据中的自动 qualification=false，不等于其它 ELF、State-writer、ordinary/default/sparse pipeline 或 whole goal 通过。

## 1. 原件和实际调用身份

下列 run 目录均位于 workspace root 的 `artifacts/timeline/`。

| 原件 | SHA-256 |
| --- | --- |
| `run-083/preflight/gcu-matching-native-v1/0.elf` | `7d56f25f70633d7f0d813a78e8ded073b884a4356d940a4cb48c710794f00500` |
| 同目录 `0.llir` | `6b8b2e1a95808ec6f924dac1324f449b44f5177e89f5d5e11de6ade3511eb593` |
| 同目录 `0.native.stdout` | `a4423a389544cde04466ad381de272754c8c79d3860eabc48dd86898a9015e8b` |
| 同目录 `0.locations.json` | `047be88eb350a496a5fc53da5925e44693f30ceb8ff774ae1bcd5e9c4024cb1d` |
| R069 `native-device-input-v1.tgz` 中 `run.py` | `ab9441068b40661a977f64bc34b7606cc5f21ebd68b9040b8dad8c4427b4aaf0` |
| R069 `trace-raw-input-v5.tgz` 中 `captures/invocation-b62efc6fae914b0485a3fd8a1a6cdb16.raw` | `d4f84686cf36effd45fbc92d2eab3e566bd0b50a64213a851328557892adf8f9` |

本次重新读取并核对了这些 SHA。R083 `result.json[0]` 将 ELF/LLIR/native/locations 绑定到原 R069 capture `invocation-b62efc6fae914b0485a3fd8a1a6cdb16.json`，capture SHA `ef003113276cbc65997bb5e54f12554d81c584a71204bb7ca70ee702f85b6648`，binary ID `30528ea30096f5da303f2a6e09c0d83e95c761cfaaeccc2c9e0419f65aff8c48`，fatbin SHA `298ab8ec5eed6d0d5961882683e0284f2996f8f29500c2ad4c3b511100f58a68`。这里 capture JSON 的摘要取自既有 R083 绑定收据；本次没有重新取得服务器上的该文件。

R069 原 source 的 `polynomial` 在 line37 load X、line38 `for _ in range(steps)`、line39 计算 `x = (x*x)*0.0625 + x*0.25 - 0.125`、line40 store Y；`steps` 明确 `do_not_specialize`。实际此次调用是 N=251、B=128、grid=2、steps=3。`native-device-poll-v1.json` 的 terminal returncode=0，source script SHA 与上表相同，原两种数学的 ordinary2/profile2、input/tail/host_once 通过；本次只取其中 ELF0，不借用 weighted_moment/ELF1 的资格。

R069 `trace-input-v4.tgz` 中 `derived/counter-ns/c161747d1d5e08a8cec6a0f58b18a6463f523a268b4c51ca8acfecc7c2e8b433/canonical.json` 的实际文件字节 SHA 为 `19726146e00b5e699300c585a2b2997d94358df940f45e87ff27f94d157576b8`。其 binary ID 与上文相同，raw 131136B、SHA 与上表相同；两个 selected observer 为 program0/1，physical full_sipinfo 分别 0/544，各11物理 pair，无 drop/overwrite/saturation。该旧 canonical 的 `boundary_status`、`clock_status` 仍为 unverified；本报告不重写它们。

## 2. 共同约定：PC、timer、observer 和 record 字段

本报告 `0xaaa0` 等是16B packet/DI landing；实际 scalar 指令可在 packet+0xa，例如第一条 end load 是 `0xaaaa`。branch target 按实际 packet 读，不按 PC−8 推断。

`0x350a/0x351a` 构造 r16=`0x42430010`；在此后到本次输出 shared-end `0x100da` 的范围内没有重新定义 r16。所列 begin/end 都使用 `[r16]` low 与 `[r16+4]` high，采用 low/high/low、unsigned low rollover 比较及 fallback high/low 重读，high 经 `0x3fff` mask；identity 是实际 `movs ..., sipinfo`。这接上了本对象内的实际 inline reader 基址和形状。46bit是此返回值表示的上界；本表不独立测量物理 counter 本体位宽、绝对频率或跨 SIP epoch，也不从相同 MMIO 地址推出共 epoch。

LLIR `%97 = (thread_id(0)==0) && (linear_block==0 || linear_block==grid_product−1)`（LLIR150–180附近）。native 在 `0x1e..0x1f..` 构造 first/last、thread0 条件，`0x25fe` OR、`0x28ea` AND 到 r28；`0x443a` 存 `[sp+0x94]`，helper 使用 r28 临时值后在 `0x5b8a/0x5d6a/0x732a/0xa6ea` 等恢复。下表入口和 end 处均受该 selected 条件约束。未 selected 路径可带零 tuple，但不进入对应记录分支；不能把这些零初始化算成一次真实 timer read。

对输入共享 tail 记 `n=入口 r14`，`B=r20+32+128*n`。这是局部物理 pair 首字地址；输出 tail 和 compute tail 使用同样的相对布局。

| 字段 | 相对 B | 输入 tail 的实际证据 |
| --- | --- | --- |
| magic / site / seq / kind | +0 / +4 / +8 / +12 | magic `0x46504733`；site 在 `0xac5a` 从 r15 写入 |
| begin low / high | +16 / +20 | `0xac8a` 写入口 r23；`0xac9a` 读 `[sp+0xac]`，`0xad0a` 写 high |
| end low / high | +24 / +28 | `0xadea` 写 r13；`0xac1a` mask r9，`0xad2a` 写 masked high |
| end identity | +32 及 +76 | `0xad8a`、`0xaeca` 写 r5 |
| begin identity | +72 | `0xaf5a` 读 `[sp+0x8c]`，`0xafca` 写入 |

**`[sp+0xbc]` 不是 begin identity。** `0xad1a` 所读值流向 payload 的 B+40。把它当 identity 会造成错误审计结论；真正 begin identity 是 `[sp+0x8c]`。

R084/R085 已有的 shared end→相对字段结果可直接复用：reader packet43680，low r13、high r9、identity r5，32条 bridge 后接 tail；本次补的是其入口 tuple/site 和 source/loop 关系。原工具明确保留 ring allocation、自动 path/source qualification=false，本次未对整份 ring/allocation/return DMA 再授新资格。

## 3. 输入 line37：三组 incoming 和 site4 的独立 end

LLIR `bb16(%306site,%307beginlow,%308beginhigh,%309beginid)`（line480）恰有 `bb15/bb22/bb26` 三个前驱：

| LLVM caller / 传给 bb16 的 tuple | 源语义 |
| --- | --- |
| bb15 → `(1,%300,%301,%302)` | `tops_slice_pad_async_1_fp32`，有效区加 padding 的 submit |
| bb22 → `(2,%407,%408,%409)` | padding 清零/mfence 之后的 `tops_slice_deslice_async_1_fp32` submit；清零在该 submit bracket 之前，不能计作该 bracket 内的全部 source cost |
| bb26 → `(3,%418,%419,%420)` | `tops_slice_async_1_fp32` submit |

三组参数都来自各自 selected begin 的 timer + identity；调用后再由相同 `%97` 进入 bb16。bb16 只取得本次 end tuple，再做计数/容量分支。对应实际 native 如下。

| site / begin packet | begin tuple 实际保留 | body / incoming → end → record | 本次结论 |
| --- | --- | --- | --- |
| 1 / `0x4570` | low r8=`0x45aa`/fallback `0x45da`；high mask→`[sp+0xac]@0x460a`；sipinfo→`[sp+0x8c]@0x462a`。body dispatch 在 `0x7ece/0x7f7e/0x982e` 等把 r8 转 r5；`0x9d9e/0x9f5e` 再转 r23，此后到 shared end 无 r23 重定义。 | slice-pad descriptor/body；`0x98fe` r15=1，body 最后 `0xaa8a` 写 submit/control；packet **0xaa90** 的 `0xaa9a` selected fallthrough→`0xaaa0`→tail `0xabd0`。 | `(1,r23,[sp+ac],[sp+8c])` 进入正确 shared end；LLVM/native 分支和字段一致。 |
| 2 / `0x4ce0` | low r23=`0x4d1a`/fallback `0x4d4a`；high→`[sp+ac]@0x4dca`；id→`[sp+8c]@0x4daa`。helper `0x6baa` 把 low 存 `[sp+e8]`，临时使用 r23，`0x733a` 从该槽恢复。 | deslice descriptor/body，`0x858a` 最后写 submit/control；`0x859a` selected guard，`0x85ae` r15=2；packet **0x85b0** 的 `0x85ba` jump→`0xaaa0`→`0xabd0`。 | `(2,r23,[sp+ac],[sp+8c])` 接上；不能用 helper 中途 r23 临时值否定已明确的 spill/restore。 |
| 3 / `0x4910` | low r23=`0x494a`/fallback；high masked r13→`[sp+ac]@0x4a6a`；id r8→`[sp+8c]@0x4a5a`。该 body 的 live low 保持在 r23。 | slice descriptor/body，`0x687a` 最后写 submit/control；`0x688a` selected guard，`0x689e` r15=3；packet **0x68a0** 的 `0x68aa` jump→`0xaaa0`→`0xabd0`。 | `(3,r23,[sp+ac],[sp+8c])` 接上；是原 capture 两 observer 实际执行到的输入 site。 |
| 4 / `0x4ea0`，**不进 bb16** | low r23=`0x4eda`/fallback；high→`[sp+ac]@0x4f3a`；id→`[sp+8c]@0x4f5a`。LLVM bb29 是 `tops_memset_async_fp32`。 | memset descriptor/body；`0x871e` r15=4，`0x959a` 最后控制写，`0x95aa` selected guard；自身 end `0x95ba..0x964a` 得 `(r13,r9,r5)`，计数后 **`0x972a`→record `0xabd0`**。 | 这是第四个 record incoming，有自己的 end read；不能给它硬接 `0xaaa0`，也不是未读 end 的旁路。 |

共同 end 的实际 low/high/low 是 `0xaaaa/0xaaca/0xaada`；`0xaaea` rollover 比较，必要时 `0xaafa/0xab0a` 重读，`0xab1a` sipinfo。site4 使用 `0x95ca/0x95da/0x95ea` 与 `0x95fa` 比较、`0x962a/0x963a` 重读、`0x964a` sipinfo。两条 record 入口均先饱和递增 attempted count，n>511 跳过写 record，正常入口共享同一个上述字段布局。共享 reader 和 record 的入边与 R086 原控制索引逐项相同；相关路径在该对象的首个 `l.loop0@0x10b5a` 之前。

这里只确认原 async **issue bracket** 的实际 caller/descriptor/control store 在 begin 与 end 之间。输入完成另有原 wait：`0xb52a..0xb54a` 取 DTE counter，`0xb55a l.wait.dec r7`，其后 site5 end reader，再进入计算循环。不能把 site1–4 end 当作 DMA 完成或 engine busy 区间。

## 4. 输出 line40：bb53 的两个 incoming

LLIR `bb53(%735site,%736beginlow,%737beginhigh,%738beginid)`（line1099）恰有 bb52/bb58 两个前驱。两条 issue 路径合用 end reader，DI landing 只命名 site6；这不表示 site7 没有 end。

| LLVM / site | 实际 begin tuple 与 body | incoming → end / record |
| --- | --- | --- |
| bb52 → `(6,%727,%728,%729)`；`tops_slice_deslice_async_1_fp32` | packet `0xc490` 读钟：low r8→`[sp+b4]@0xc52a`；high mask→`[sp+8c]@0xc53a`；id sipinfo r7→`[sp+b0]@0xc7ea`。descriptor/body 后 `0xe3be` r9=6、`0xe3da` 最后控制写。 | `0xe3ea` selected branch→packet`0x10050`→shared end `0x10060`；end tuple 为 low r12、high r14、id r10。 |
| bb58 → `(7,%833,%834,%835)`；`tops_deslice_async_1_fp32` | packet `0xc5d0` 读钟 low r17、masked high r25、id r14；`0xc71a` id→`[sp+b0]`；进入 helper 前 `0xef2a/0xef3a` 分别把 low/high 存 `[sp+b4]/[sp+8c]`，随后 r17/r25 才用于临时值。 | body 最后 `0x1001e` r9=7、`0x1003a` 控制写，`0x1004a` 未 selected 跳出，否则落到同一 `0x10050/0x10060`。 |

共同 end 为 `0x1007a/0x1008a/0x1009a`，`0x100aa` 比较，fallback `0x100ba/0x100ca`，`0x100da` sipinfo。记录时：site r9→B+4 `0x1027a`；`[sp+b4]` low→B+16 `0x1021a/0x102da`；`[sp+8c]` high→B+20 `0x101ea/0x1025a`；`[sp+b0]` id→B+72 `0x103fa/0x1045a`；end low/high→B+24/+28 `0x1033a/0x1031a`；end id→B+32/+76 `0x1050a/0x105aa`。栈槽虽在前后两个 source 阶段复用，输入 pair 已写完，输出 begin 又明确赋值，不是继承输入的 identity。

## 5. source39 runtime-loop：实际 body 与每轮端点

LLIR bb41 使用 `%618 < %arg10(steps)`；bb43 begin→bb44 vector load/算术/store→bb45 end→bb46 record→bb47 `%618+1` 并把结果 descriptor `%617` 送回 bb41（lines930–1066）。实际 native 没有把 reader 提升到循环之外：

| 关系 | 实际 PC / 含义 |
| --- | --- |
| runtime trip 来源 | `0x1d8a` 从 kernel argument block `[r31+0x1c]` 取 steps 到 r17；直到循环入口没有 r17 重定义。`0xbb3a` 对 r17<1 跳到 `0xc2e0`，零/负 trip 不进 body。 |
| first iteration / head | `0xbc0a` 首轮跳 `0xbc30`，绕过 decrement；`0xbc6a` selected guard 后 begin packet`0xbc70`，low r22、masked high r24、identity r14（读/比较/fallback `0xbc7a..0xbcfa`）。 |
| 被声明的 source body | `0xbd0a` qacc6 从当前 buffer r6 load；`0xbd34 msqr`；`0xbd44 mdm` 乘0.0625；`0xbd54 mac` 加 x×0.25；`0xbd64 madd` 加−0.125；`0xbd70/0xbd80` 写结果。常数由 `0xbb4a..0xbb9a` 设定，与 LLIR source39 的表达一致。 |
| recurrence buffer | 首轮 r6=`r20+r26` 是 X staging；`0xbd1a` 转为结果 staging `r20+0x10800`，后续回边不重置它，因此下一轮 load 上轮结果；对应 LLVM loop-carried descriptor。K<=0 的 `0xc2e0` 则让 output 使用原 input staging。 |
| 每轮 end / record | selected body 后进入 packet`0xbda0`，end low r19、high r25、id r18，`0xbdaa..0xbe0a`；site常数11=`0xbb8e`，`0xbf0a` 写 B+4；begin low/high/id 在 `0xbf6a/0xbf9a/0xc22a` 写 B+16/+20/+72；end low/high/id 在 `0xbfca/0xbffa/0xc03a/0xc25a` 写 B+24/+28/+32/+76。 |
| latch / exit | 未 selected `0xbd9a`、record满 `0xbe9a`、正常 record尾 `0xc2da` 均到 packet`0xbc10`；`0xbc1e` r17−1，`0xbc2a` 为零退出 `0xc2f0`，否则落回 begin/body。退出后才进入 line40 output。 |

因此，对 selected actor 的每个正常已记录动态 iteration，原 source39 load/算术/结果写发射都在本轮 begin/end 之间；每轮取得新的 begin tuple，end/record 后才回边，不存在把上一轮 begin/high/id 当作下一轮端点的这条断点。record满时保留 attempted/loss 语义并跳过 record，不绕过原 body。此处是 observer region elapsed；不证明 vector 引擎独占/完成、所有 source 运算的 exclusive cost、hidden scoreboard 或实际 engine busy。

## 6. 实际 raw 的有限交叉核对

没有重新运行 decoder。直接读取保留的 canonical 字段引用，并用 `od` 查看原 raw 的首个 compute pair，确认 site11、seq4、kind5 与 begin/end words、identity 字段相符。例如 observer0 首个 compute pair B=544：low/high `(3421053854,287)`→`(3421054394,287)`；observer1 对应 B=66112：`(3081560500,287)`→`(3081560994,287)`，end/begin/end identity 均544。原 raw SHA 已核同。

| selected observer / full_sipinfo | source39 occurrence | canonical 原始 entry/exit offset | 原 tick 差 |
| --- | --- | --- | --- |
| program0 / 0 | 0、1、2 | 560/568；688/696；816/824 | 540、540、525 |
| program1 / 544 | 0、1、2 | 66128/66136；66256/66264；66384/66392 | 494、496、494 |

这与原 source runtime steps=3、native head/latch 和每轮 site11 相符。没有从两个 observer 的 tick 大小推导它们之间先后/重叠。原实际 raw 的 input/output 分支均为 **site3/site7**；site1/2/4/6 是本次在同一最终对象中核到的编译分支，不能记作此 capture 已动态走过的分支。无需为这张静态 incoming 表另跑数学矩阵。

## 7. 有限裁定及停止点

- **本请求内已闭：** ELF0 的 bb16 三 incoming、site4→共享 record 的另一路、bb53 两 incoming；各自 site/beginlow/high/identity→本路径 end→正确 record字段；source39 body 与 runtime-loop head/latch/exit，且已有实际 K=3 raw occurrence 接上。R088 对这些关系提出的具体人工补读已完成。
- **confirmed blocker/major/minor：本次范围未新增。** 没有因 DI 缺 site2/3/7 的独立 end marker 就判 logger 丢失；实际 shared-end 合并解释了这些位置。没有把 site4 的 `0x972a` 误判为绕过取 end 的非法发布。
- **本报告适用范围之外：** ELF1/weighted_moment 的 source/body/loop；State-writer 与 sites12/13 相关后段（首个 `l.loop0@0x10b5a` 等在这里，不在所审 source39 runtime-loop 内）；ordinary/default/真正 sparse 的关键 pipeline 三方对应；其它 backend 和 whole goal。本次不裁定这些范围当前总体是否已闭，不把它们当成新增阻断项或重采要求，也不以这份 ELF0 审计替代各自已有证据。
- **时钟/自动资格边界：** 本对象的 r16 字面值及 inline reader 已实际读到，但物理位宽测量、absolute frequency、跨 SIP epoch、引擎 busy、source-exclusive cost 均未从此表推出；原产品 generic qualification=false 保留。此一次冻结对象人工审计可作有限 native-boundary 补证，不要求再建全库 ISA/CFG/taint/DWARF 证明器，亦不应变成用户逐算子人工放行步骤。

在所列 ELF0 路径内没有还需新 probe 才能解决的具体断点。后续若只整理此证据，应停止新增设备/math/TP/UI 或通用机器码证明工程；其它独立范围的现状以各自既有证据和原合同为准。
