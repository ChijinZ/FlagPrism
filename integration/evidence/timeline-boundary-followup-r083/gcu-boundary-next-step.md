# GCU reader→raw 与 source/loop：最小有限下一步

**共享 end block 可以合法服务多个 site，不需要每个 site 独占一个 end PC 或 DWARF 行。** 充分的有限证据是：对每条受支持前驱路径，把动态 site ID、对应 begin 值/identity、共同 end reader 的值/identity，证明送入同一个实际 raw record；再分别核声明区域与循环路径。现有 IR 摘录展示了这种可行结构，但原始 site ID、正 duration 或单个 helper 符号审核，均不能代替最终机器传值与区域边界。

本报告只给原合同要求内的可实施检查，不新增完整 ISA、独占 cost、精确 issue order 或 engine-busy 门，不重复已闭普通 State writer/传输/单位/安装项目。

## 本次实际阅读范围

读取 R069 `shared-end-blocks-v1.txt`、`timestamp-use-v1.txt`、`clock-origin-aliases-v1.json`、`missing-native-phases-v1.json` 及相关 native map/device 收据；读取 R065 LLVM11 工具、原 ELF identity、helper/native 材料，R066 `finite-helper-audit.py` 与实际结果；读取当前 `GcuTimeline.cpp` 的 clock/record/publication 和 `GcuNativeLocations.cpp`、native decoder 相关字段；读取 design §0.6/§8.14、对应 testing 要求。未读 peer 报告。

亦读取 R083 `gcu-current-native-v1.json`、`gcu-reader-windows-v2.json`，随后读取已补齐的 `gcu-matching-native-v1.json` 和本地 matching 原 ELF/LLIR/native/locations。早期两份诊断摘要 SHA256 分别为 `f2a6414beee4ba6d99c8864eccd4a285a628362fa7a278339be0d2d6e69a1ce8`、`cf22d23d14d11fc3092a6c564d7f66f7c9773873b0e54d5e7743343945effa9c`。未执行产品、checker、测试、SDK/codegen、设备、数学、TP 或 UI，也未连接服务器；本次本地材料足以形成下一步方案。原请求 GPT-6.1-Sol / xhigh；resolved 型号/档位未暴露，记为 unknown。

## 现有证据真正说明了什么

1. **完整反汇编出口已经存在。** R065 对原 ELF `ac6748ff...701cba` 的 LLVM11 objdump 实际返回 0，stdout SHA `61fa447c...b1067c`、3,000,060 B，零 decode failure/unknown。probe whole terminal 1 来自 assembly metadata 重组装失败，应保留，但不能据此声称无反汇编出口，也不需要用重组装副本证明原对象。
2. **R066 已有的 helper 证明应复用其有限范围。** 脚本绑定同一原 ELF / disassembly，逐显示字节对原 section，核低/高/低读取、rollover 分支和重读、upper mask `0x3fff`，以及 identity helper 的 sipinfo。它明确 `actual_inline_reader_to_raw_binding=false`、`source_region_qualified=false`。46 位是该返回值上界，不是未经证明的物理 counter 完整位宽；本轮无需重新打开这个已闭有限事实。
3. **实际 reader 已被 SDK 内联，不能强求 call 指向 timer 符号。** 旧 R065 原 native 中也可见 inline MMIO 序列。R083 的 R068 ELF 0、site10 begin marker packet `0x3d00` 内，实际有效读取从 `0x3d0a` 开始；end marker packet `0x3e70` 内从 `0x3e7a` 开始。两端都有 low/high/low、unsigned 比较与必要重读，identity 为 sipinfo。高字 mask 可能在 identity 或其它 recorder 指令之后，不能套固定连续十三条 callee 指令顺序来判 caller 失败。
4. **R069 的共享 end 并非“缺失 clock”。** `^bb16` 的四个参数承接 site ID 与 begin low/high/identity，来自三个前驱；共同 end `%310` 及 identity `%314` 后进入 record 路径。`^bb53` 同样承接两条前驱的 site/begin 数据，共同读取 `%739`。DI 只保留其中一个源位置，会使其它 site 的 end columns 缺失，但不等于那些动态 interval 无 end。需要补的是实际路径和传值证据，而非人为复制读钟。

### 必须保持的原件身份边界

R065/R066 helper 原 ELF 是 `ac6748ff...701cba`。本轮 R083 新 native 实际来自 R068 两个原 ELF：

| index | ELF SHA256 | native stdout SHA256 / bytes |
| --- | --- | --- |
| 0 | `6b69d4a8a3457fc3a99d10f8b447c29de828e3ca748932be8498bdc8cbb30faf` | `7893a00ca8e3fd96b6c0b699963b18c22c80774fea5d5bd2cba3fb63ca7a52ad` / 1,706,337 |
| 1 | `a0c0ffc0f5e4b0d622fd545d8226f833e12f439f8f32bf0a651022e551cdcf50` | `3016b9c2b698a7c3018247aee279c67f3394e089246bde1c6488036b16d74928` / 1,684,317 |

R069 shared-end 摘录所属两份 capture 的 ELF 是 `7d56f25f...f00500`、`5860432e...2131f6`，不是上表两 ELF。上述 R068 对象只作历史诊断，不能拼入 R069 证明。**此身份材料缺口现已解决**：下节新增 matching 原件直接来自 R069 capture 的实际 compiled snapshot。已核字节相同的 helper/pattern 可按真实内容摘要复用，不能仅按函数名复用。

### 已补齐的 matching 原件与首个具体检查目标

`gcu-matching-native-v1.json` SHA256 为 `c69b9e4dfb702abe6d8ece6e764cda2601385bcfddc565e9f19debe8541604d7`。本次实际逐核本地 `{0,1}.{elf,llir,native.stdout,locations.json}` 八份文件，各自 SHA 均等于登记值，并读取 ELF0 `^bb16/^bb17` 与 native `0xaaa0..0xb060` 的共同 end / record 片段；没有运行工具或重编译。

| index | matching ELF SHA256 | matching native stdout SHA256 | matching final LLIR SHA256 |
| --- | --- | --- | --- |
| 0 | `7d56f25f70633d7f0d813a78e8ded073b884a4356d940a4cb48c710794f00500` | `a4423a389544cde04466ad381de272754c8c79d3860eabc48dd86898a9015e8b` | `6b8b2e1a95808ec6f924dac1324f449b44f5177e89f5d5e11de6ade3511eb593` |
| 1 | `5860432eef0a3004e35740a68b17b10bd9f33d49bf3ab7a30f8cb11be72131f6` | `3e15c05637ef8ab999165d5496ebe07e7dff1967aa648828437c65038c063935` | `acdeadcb66fe11896706b9d384e3d4a7dad22c3aafe8f00bd56ac321f71068e7` |

这套原件分别绑定 R069 binary ID `30528ea3...ff8c48`、`937ef765...ba3223`，与共享块摘录一致。新 matching windows 是实际 48/62 marker 行，不用前述重复诊断窗口填充证据。

最省事的首个 finite matcher 可从 **ELF0 的共享 end packet `0xaaa0`** 开始；无需先覆盖全部 kernel。实际可见：

- `0xaaaa/0xaaca/0xaada` 为 low/high/low；`0xaaea` 比较两个 low，rollover 路径在 `0xaafa/0xab0a` 重读。`0xab1a` 读取 sipinfo。
- mask 常量到 `0xabea` 才形成，`0xac1a` 才执行 `r19 = r9 & 0x3fff`。它晚于 identity 和 cursor/capacity 控制，不能按连续 timer helper 顺序拒绝。
- 在 retained-record 路径，`0xadea` 将 end low `r13` 存到 `ring + sequence*128 + 0x38`，即 record word6；`0xad2a` 将 masked high `r19` 存到 `...+0x3c`，即 word7；identity `r5` 在 `0xad8a/0xaeca` 分别进入 `...+0x40/+0x6c`，即 words8/19。ring base、sequence 和这些地址的实际 def-use 仍应由 matcher 明确输出，不能仅保本报告的人工位置描述。
- 动态 site 通过 incoming `r15` 在 `0xac5a` 存 word1；begin low 在 `0xac8a`，begin high 从 `[sp,0xac]` 恢复后在 `0xad0a` 存 word5，begin identity 从 `[sp,0x8c]` 恢复后进入 word18。最小余项是逐三条前驱追这些 incoming 值，核它们属于同一个 site 的 begin，而非重新证明所有 recorder 字段。

LLIR `^bb17` 同时确实存 `%306`（site）、`%307/%308`（begin）、`%311/%313`（end）、`%309/%314`（identity），支持上述路径模型。这里仍只给可落地目标与已读事实；未把少量 native 位置检查升成自动 reader-valueflow、全 source region 或 loop 资格。ELF1 共享 end 的 DI packet 是 `0xaa50`，也不应套 ELF0 的地址常量。

## 建议的最小实现：四张有界事实表

### 1. 实际 reader 表：允许 packet 与寄存器分配变化

输入只用一个已留存 capture 的 owner/manifest、actual fatbin→ELF/section、同对象 final LLIR 和 LLVM11 native，记录工具/输入 SHA。将 DI marker 地址当候选 **16 B packet** 定位，核 packet/有效 instruction 的实际 section bytes；不能要求 marker PC 与 objdump instruction PC 相等。省略的全零 packet 按 ELF 原 bytes 处理，不从文本缺行推断控制流不存在。

有限 matcher 只解释实际所需的常量形成、MMIO loads、低字比较/重读、上字 mask、sipinfo、move、必要 spill/load 和分支。追实际 def-use 与 CFG，允许 alpha-renamed registers、base 地址提前形成、mask 延后、reader 分支展开；未知的必要写入/控制路径给具体 unverified。区别“counter base 常量可循环外复用”与“实际取样 loads 被外提”。不需要模拟整个 SDK 或核全部数学/机器指令。

每行输出 `(ELF, function/section, caller reader path, candidate marker packet, 实际取样PC集合, low/high值来源, identity来源, predicate/observer范围)`。getter out-of-line 时核 call target/返回值，inline 时直接核同一有限采样语义；二者都不能只靠名字。

早期 R083 v2 诊断窗口有重复：ELF0 144 行只有 48 个唯一 `(site,phase,packet)`，ELF1 186 行只有 62 个，分别多 96/124 行；新的 matching 材料已提供 48/62 原 marker 窗口，不再把诊断重复当额外证据。实现仍应保多个真正不同的候选范围，不把一个 sampling sequence 中的重读/多条 DI rows 当多个 runtime occurrence。短窗口未必覆盖延后的 mask 与最终 stores，应沿所需值追到实际使用处，不能仅凭窗口中找到三次 load 就放行。

### 2. 动态 site→record 表：共享 end 的必要且足够的关联条件

对每个共享 end 的每条受支持入口边，核完整元组：

`(dynamic site, begin low/high/identity) → selected end reader/identity → 同一 sequence record 的字段 stores`。

在 LLIR 核 block arguments/phi 实际传参，在最终 native 核这些必需值的 reaching definitions、move/spill 和 control path；不可用“同名寄存器在全函数里出现过”代替实际生命周期。共同 end 必须在该入口所声明操作之后执行，site 常量/选择值与 begin 值必须来自同一前驱；不能把 site3 的 ID 配 site2 的 begin，或者把另一个 return/loop iteration 的时间戳混入。

当前物理 ABI 可直接复用：`record_base = slot_base + 32 + sequence*128`；site 为 word1、sequence word2、kind word3，begin 为 words4/5，end 为 words6/7，identity 为 words8/18/19，program 为 word25；seal/header/capacity/loss 的既有规则保持。只需证明 reader 值进入相应 local ring fields，并接已闭的 matching publication/transport 字段关系，不必重新解释全部 logger 或 SDK DMA 实现。原 raw 逐 u64 对照 canonical 的引用 offset/length/site/observer/sequence；CPU 无须“重算”不可回放的硬件 timer 数值。

**动态 site 关联足够消除共享 end 的 DI 歧义，但前提是这条传值与路径链已经核实。** 单看 raw 中正确的 site、正 duration 或两份相同 duration 不够；反过来也不应额外要求每个 site 自有 end PC、每次执行独占 marker 行。

### 3. 区域表：声明的 source group 与最终代码实际被夹住

在已注册的 runtime 依赖循环/真实异步样本中，先选现有自动 site/source group，按其声明操作集合找最终关键指令/基本块或实际 SDK call/展开路径。不得按 checker 成功状态挑样，也不能用只夹一个方便指令替代原声明 region。

对该有限 group 核 begin 的实际 sampling 路径、组内关键 data/control/memory 关系、end sampling 路径及旁路。原 source/DI 用于定位，最终依赖和控制证据决定放行；DI 存在不证明算术没有跨界。reader 内部 mask/identity 的延迟不自动等于数学跨界，应以取样值来源和实际支持的路径为准，明确读取窗口的适用解释。若确实发现关键算术被移出区间，再修对应通用 dependency/late lowering；不先加 completion barrier 或按算子补特例。

submit/SDK async start 的 bracket 只支持对应 caller 发射/提交阶段；原 wait 的 checkpoint 只覆盖其实际已有保证。source elapsed 可以包含 recorder/调度干扰，不要求 source-exclusive，也不能因此把发射 bracket 升成异步操作的硬件完成或 busy 时间。

### 4. 循环表：实际 header/latch/exit 与每次 pair

对包级 native CFG 识别支持的自然循环，区分 counter rollover 的内部读钟分支与用户循环；列 header、全部 latch、所有实际出口及 selected observer 路径。按原 §0.6 核每条声明 body 路径确实经过相应 begin/end，不能有某出口绕过端点、重复 end 或 begin 被提到整个循环之外。共享 end 可作为同一 iteration 多分支的汇合，只要各 incoming tuple 与 backedge/exit 关系明确。

复用已有同 binary 改 K 的 retained occurrence/raw 作为交叉检查；次数吻合不能代替 CFG，native loop occurrence 也不自动等于 source iteration。只有 loop lowering 与源循环关系确实绑定时才填 source iteration，否则保原 `iteration_id=None`。如果当前 retained 样本没有所需双 K/路径事实，准确列缺哪份原事实；不为此新增独立数学场景或重开已闭矩阵。

## 最少语义反例与真实风险

复用上述真实对象作正例，再给已有 P03/P10 合同要求的少量合法结构负例：共同 end 的一条前驱换入错误 begin/site；raw 某 timestamp field 改用无关定义但 marker/正 duration 仍自洽；一条 body exit/latch 绕过端点或关键计算移出 bracket。要求命中对应传值/路径/边界规则，不能仅靠 parser/身份不符拒绝。保持合法共享 end、rollover、延后 mask 和 same-packet+0xa 正例，避免用“一律拒绝”冒充健全。它们是离线结构 fixture，不新增设备/数学矩阵。

实际风险集中在：不同 ELF 材料误拼；packet/零省略误读；把 phi/site 标签当已核 native 值；固定窗口看不到延后 mask/溢出分支；物理寄存器/stack 槽跨生命周期误连；只核观察到的路径却对未覆盖出口授予完整 loop；以及 marker 在界内但关键算术越界。未知所需 opcode/多入口/间接跳转可给该 site 的具体 unverified，不必发明全 ISA 证明框架。

## 当前结论

这些原件已经表明工具路径可行，且共享 end 不是必须修改产品的缺陷。当前材料仍不足以关闭最终 reader→raw 和完整 source/loop 边界：缺的是 matching ELF 上的实际值流、支持路径和关键 group 覆盖，而不是更多 duration、独立 helper 符号或重复数学。

最小下一步是先在一套 existing matching capture 闭包生成上述 reader/site-record 两表，随后同对象的 region/loop 两表与少量语义负例；结构规则可复用于既有适用组合，未支持形态如实保 partial。ordinary 关键 pipeline 关系仍是独立剩余项，不能因 source/loop 成立或 exact issue order 不同而自动判通过或失败。本报告不提升任何产品资格。
