# R093 compiler：reader context / 自动 record tail 有限审阅

结论：本次冻结增量未发现可确认的 blocker / major / minor。有限 affine context 在所给 direct 控制索引内收集全部 reaching definitions、要求值一致；自动 tail 保留完整直线块与后续覆盖检查。它支持当前声明的 conditional reader / relative-field diagnostics，**不关闭 source/loop、MMIO、外部入口、真实 record selection、incoming begin/site 或 whole-goal**。正常 wheel 安装尚未在本席所读材料中闭合。

## 身份与实际范围

候选 HEAD **0da41a89a21efc9912aa0c738b3b631d4f9af885**，读取时工作树 clean。沿原请求 GPT-6.1-Sol / xhigh；实际 resolved 型号/effort 未暴露，记 unknown。没有读 peer，没有与其它 reviewer 商议；未重开已闭 BK32/BK64 pipeline 或整体 goal。

本地只读 Git、文本、JSON/SHA/cmp，未运行产品/import、测试、SDK、编译、设备、数学、TP/UI 或 SSH。实际读取：

- `gcu_native_values.py` 全部相关 reader/context、bridge、relative-tail、automatic-tail 逻辑及新增 fixtures；
- `gcu_native_control.py` 的完整 direct-edge/predecessor/unknown 合同；
- 新 `gcu_native_analysis.py`，`gcu_timeline.py` 的正常编译及 immutable reinspection 接线、身份/错误处理；
- 新 provider/location-binding tests；
- `run093/preflight/gcu-context-receipts-v4` 的 matching executed source、runner、terminal、完整 normal/optimized stdout 和两原 loaded-object 结果。未重审前轮已独立处理的 native-image ELF/symbol/string-table 实现全部历史。

冻结 SHA256：

| 文件 | SHA256 |
| --- | --- |
| gcu_native_values.py | c2f2fc374ae1f62117d044fdf1d500bb24c1c5b92cb92cfd12b195a85042fc2e |
| test_gcu_native_values.py | 85a7b0c82f9aedc1fb857915db0879a12a9f4a19d8c8dadb6c06997c9802e970 |
| gcu_native_control.py | 90a0c4343e0b0193583500bc2bbabacd25a1b74d47e499ca39ea530190a61f83 |
| gcu_native_analysis.py | 3e408afe54dc2c3391eb70c4dca6be1cd2fec6c19c00a4e131a806fc6cdf7dae |
| gcu_timeline.py | d9e348a5e4a4cfc653f2dcf6ecdfbca821f3a1403351ee0db56c672d46e88a68 |

## 关键正确性核验

### 1. Context 是有条件的 reaching-definition 检查，不是全函数寄存器扫名

`gcu_native_values.py:220–363` 对每个 (packet, register) 沿 predecessor 逆向查最近写；有写则在该路径止步，没有写的循环按 visited 终止而不凭循环创造值。入口可达但未定义时保留独立 `entry:rN` 符号，不填0。不同入口/分支的 reaching values 逐项比较，只有 affine 表达式完全一致才合并。

递归值定义由 pending /64深度拒绝，累计逆向遍历有250000步预算。必要路径上的 unknown packet 拒绝；有定义的 load/未支持ALU不会被当成旧值绕过，而在实际 definition 解析处拒绝。memo 只在完整求值成功后填入，不缓存 DFS 中间空集合。两个 word 地址须实际满足 low/high差4及重读一致，不因它们“看起来都是计时器”放行。

同 packet 多写同一目的拒绝；定义读取的寄存器若同 packet 另有写，也拒绝，未假定未知 forwarding。已支持 immediate 的有符号范围、ldi_hi保留低16位及32-bit modular affine运算与前轮有限模型一致。未知 ISA 保具体 unsupported，不扩大解释器。

这些判断仍依赖调用者提供同对象完整 instruction list/direct index；不能从 direct predecessor 中缺一条未知 indirect/call edge 推出无 external entry。源码/doc和返回资格字段保留这一限制。**本席没有把 conditional/index 或 default false 字段本身当成新的全 goal 失败或通过。**

### 2. Optional control 的接入不覆盖原 reader 检查

`inspect_inline_reader:374–426` 先保留原局部 reader 正例；只有原局部失败恰为 word地址不一致时才尝试 context 解析真实 live-ins。原两端输出、low/high/low、unsigned rollover比较、fallback重读、fast/fallback join、identity与同packet限制仍执行。context没有把 clock load 结果改成常量，也不能替换三个 reader 输出。

因此无需 context 的 reader 可保原结果，而需要 hoisted base/address关联的形态只新增有限证明。返回 `conditional_entry_context_checked` 说明实际是否使用该支路；不强求每个已过局部形态都重新标该字段。

### 3. 自动 tail 不靠找到一个好前缀放行

`inspect_inline_record_fields_auto:681–762` 从 identity 后/原 direct guard 后枚举有界候选，核至下一控制 packet 的**整个直线块**；不是找到magic及四字段后提前停止。multiplepassing candidates 拒绝；control同packet有有效其它操作时保守拒绝。后续 field overwrite、未知 alias store、unknownop、call、跳入tail中段的旧规则仍生效。

`inspect_inline_record_fields:637–663` 只给已完整解析为常量的必要 store data live-in 提供 entry_constants；未知保符号，reader输出不得被常量覆盖。entry常量由同graph到tail入口的实际 reaching definitions 取得，不按site名、寄存器名或fixture hash填值。

新增 backward guard 只在显式提供control且目标在marker之前时作为 outside skip保留；跳回reader内部、跳入tail中段仍拒绝。它支持的是保留fallthrough record分支上的有限值关系，**没有宣称该skip的所有后续动态路径/外部入边/selection都被证明**。返回 selection/external/incoming tuple/source 等 false 与此相容，不应把该诊断升级成完整CFG值流证书。

### 4. 自动调用点与身份没有混用 producer / analyzer

`gcu_native_analysis.py:31–81` 从 byte-bound image生成同一kernel extent内的direct graph，核manifest site、phase/column、packet地址和重复点，按实际PC缓存reader/record诊断；unknown保每point原因，不删除未支持站点。报告保持source_region/reader_valueflow/external_entries/hardware_busy false。

`gcu_timeline.py` 在现有final fatbin→ELF/locations后调用分析；tool identity版本3包含实际analyzer/control/image/values及LLVM11 objdump，防旧cache悄悄继承新解释。shape失败返回独立unavailable，不把它伪装成source成功。离线inspect复制metadata并给新analyzer身份，保producer身份，不回放应用或覆盖旧producer收据。

## Matching 实际收据

本席 `cmp` 确认 final candidate helper/test 与 `gcu-context-receipts-v4/reader-context-input-v4` 执行字节一致。terminal0，**3.419671718s**；normal **73 passed /0.08s**，optimized **73 passed /0.09s**，后者只有预期pytest assert-warning。未亲自运行这些命令。

语义fixtures实际包含不同路径地址不一致、load clobber、unknown control、loop-carried value递归、same-packet forwarding；自动tail包含late overwrite、alias、unknown、tail entry、call、hoisted mask、control packet store负例；合法hoisted base经join/无定义循环，以及outside skip有正对照。它们是CPU结构测试，不是新的硬件执行。

真实未变对象结果：

| actual ELF SHA | native SHA | unique end points | reader shape checked | relative record checked |
| --- | --- | ---: | ---: | ---: |
| 7d56f25f70633d7f0d813a78e8ded073b884a4356d940a4cb48c710794f00500 | a4423a389544cde04466ad381de272754c8c79d3860eabc48dd86898a9015e8b | 11 | 6 | 2 |
| 5860432eef0a3004e35740a68b17b10bd9f33d49bf3ab7a30f8cb11be72131f6 | 3e15c05637ef8ab999165d5496ebe07e7dff1967aa648828437c65038c063935 | 12 | 9 | 0 |

合计 reader **15/23**、relative record **2/23**；其余unknown明确保留。ELF0显示site11（frontend source39）的端点现自动选择tail **48808..49870**，context给r11=11、r13=0、r23=1179666227(magic)、r15=3；它们来自实际代码，不是runner手填tail/常量。另一个checked shared-end tail为43980..45150。site共享/前驱tuple与source/loop尚未因此成立。raw/数学未重跑，也没有据这两个success自动授其余21个record成功。

runner自身按两actual ELF/native SHA、逐显示instruction bytes、descriptor/codeextent与ELF symbol、其余非零execbyte覆盖核对后使用产品image binder；本席阅读其实施与结果，复用此前matching原件审阅，不把本报告称新的设备/SDK证明。

## 分类与结论边界

**Confirmed blocker / major / minor：本增量无新增确认项。** 未给root提出必须修代码的最小false-pass触发，因为本次实际未确认这样的路径；不为凑缺陷扩展未知ISA。

**Necessary verification gaps（仅本delta）：**

- 上述73及两原ELF结果证明final matching source-loaded组件；当前所读收据不包含此冻结的新normalwheel安装、真实公开capture hook与installed immutable reinspection的终态。因此可支持有限源码/CPU旧原件诊断结论，尚不能把它写成normalinstalled链已通过。最少后续只核新normal安装身份、实际provider接线与同原件offline读取，复用不变producer/raw；无须新数学/SDK/device矩阵。
- 所有external entry、MMIO physical base、ring allocation、incoming begin/site、recordselection、source/loop qualification仍是明确未授的不同范围。本报告没有把它们增成这一conditional诊断必须先实现的门，也不据本delta关闭原whole剩余。

**Optional：无新增重构要求。** 可在交付摘要明确“15/23 reader shape、2/23 relativefields，其余unknown；analyzer版本与producer版本分开”，避免读者把诊断数量当完整source门通过。

本次有限review完成；支持按上述精确范围合入/验证该诊断delta，不支持将其独自提升为完整GCU source/loop或整体goal完成。
+

## R093 正常安装与实际接线的有限闭合追加

本追加只关闭上文第一条安装/公开接线 gap，不重审 context 源码或 whole-goal。对应 runtime freeze **4fc741f66144b6c2617545b8868b6ac3ae6cf0a1**。本席实际读取 `run093/preflight/normal-provider-receipts-v2` 的索引、normal-install-v3 与 installed-provider-actual-v1 的 terminal/result、完整 installed tests stdout、两旧capture reinspection结果和新公开数学结果；未执行任何代码/SDK/设备/测试或SSH，未读peer。

### 正常安装

- normal-install-v3 terminal0，**53.847693220s**；source_commit与上述freeze一致，wheel SHA **79b9c3499da162264712241cca659d3f1c34c0b6ff0f34624e82bc331292dfc7**，结果登记 **502 installed members**。
- assemble/install/import/guard-binding/observer-import及normal/optimized provider tests步骤全部returncode0。四个相关测试文件合计 **106 passed /0.23s**（normal），**106 passed /0.36s**（-O）；后者只有预期pytest assert-warning。
- 沿用未变recorder/native与compiler，结果明确列出复用路径；没有把本次Python analyzer接线称为新native/SDK/producer重编译。
- 对比0da41a8至freeze，context/relative-tail核心未变；额外接线保护包括offline bytearray先快照为bytes后核捕获fatbin/ELF/target身份、诊断budget明确cooperative-between-checks和record检查前再查budget等。它们不改变本席原context判断或给qualification填true。

### Installed 实际旧原件重读

installed-provider-actual-v1 terminal0，**20.695610856s**。它用正常安装的公开reinspection入口只读原R069两capture，记录实际LLVM11 objdump argv/tool SHA **e37efecc349022f96c6a0fdaee12fa2019be01c8225d63999f8ea7fafce22c50**；两个decoder terminal均0。原capture SHA分别：

- **ef003113276cbc65997bb5e54f12554d81c584a71204bb7ca70ee702f85b6648**；
- **3c7a6282434a1241a4922f4a3b090130900773270d712ebd065643bc4fd538d0**。

结果均 `original_unchanged=true`；actual ELF仍为上文的7d56f25f…f00500 /5860432e…2131f6。保producer identity **df8885bfe537cae850d535480143a1ac0ff4e92569e478fafe2dc28f66440cbb**，新analyzer identity **caee0ca8012c97cfcd1b7b99051ccbbff51d3bdfa62e5174bd07f6cc67ef1fa0**，没有改写原producer或回放旧应用。

| 原对象 | 本次provider的site/phase point行数 | reader checked行数 | relative fields checked行数 |
| --- | ---: | ---: | ---: |
| ELF0 | 25 | 8 | 2 |
| ELF1 | 38 | 18 | 0 |

**这个分母含begin/end counter point，不能与上文unique end markers的15/23 reader、2/23 record分母混用。** 同一PC可服务不同site/phase行，checked行数也不是新独立硬件reader数量。原context-v4结果不被重写成另一成功率。

### 新默认数学的公开接线

同一正常安装额外运行普通2次、profile2次新数学，结果 **math/input_unchanged/guards/host_once全true**。两个新capture分别：

- binary `8a3a613dd944df77aeeaf4d9a09d090f200f21216cbc12a3cc8cab9fdf5d82ce`，22 events、2 observers、48 native-location points；
- binary `284438abdd4fdf21756c51d48946ed3119027465784fb031ff17d7ea7079228e`，20 events、2 observers、62 native-location points。

这些新默认capture及installed reinspection证明正常包中的服务接线实际到达，不只source-loaded单元函数。新数学仍明确 `final_machine_boundary_qualified=false`，没有据新DI或诊断行数授source/loop、MMIO、外部入口、完整reader值流、selection或whole资格；也没有把旧capture重读冒充新producer执行。

**追加结论：本delta的normal installed身份、旧原件公开reinspection与新默认数学接线 gap 已关闭。** 上文“正常安装尚未闭合”是追加前的历史状态，当前不再作为本delta待办。原conditional范围及所有未授资格保持；不因此重开或关闭其它whole剩余。
