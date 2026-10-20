# R085 inline reader 与 relative record bridge：有限 compiler review

本次只审 `gcu_native_values.py` 新增的 `inspect_inline_reader`、`inspect_inline_record_fields`、对应 fixture 与原件 runner。确认一个 reader join 的路径合并 false-pass；随后候选已按该根因修正，源码及新负例对应正确，matching 执行收据尚待补。未发现其它本范围的 confirmed blocker/major/minor。本文不授予完整 reader、source/loop 或 whole-goal 资格。

## 阅读、身份与未运行范围

实际阅读新增两函数及其调用的 relative-tail checker、`Debugger/test/test_gcu_native_values.py`、`check_gcu_inline_reader_v1.py`、`gcu-inline-poll-v1.json`、input-v1 归档内 runner/两个 helper copy/测试，以及 R083 matching loaded ELF0 的原 native reader/bridge 窗口。未读 peer，未执行组件 import、测试、产品、SDK、设备或数学；本机仅只读文本/JSON/归档/hash。请求 GPT-6.1-Sol / xhigh，实际 resolved 型号和档位未暴露，记 unknown。

初读 helper SHA256 `f9afcf582c29e7b4988b3d5888e08a4be9f749876ed8728d73a7be7e3b83c397`，测试 `a0fbc19ec92d38ae7869ecdce0f3e28db4f3a762490d8c3870bb656249f9f21e`，与 input-v1 root/package 两 helper 和测试分别一致。归档 SHA256 `27c31fa1f676c340190ca8397f2a55e22af5c32332154d6ac6719e9c7acc46d2`；runner SHA256 `7b1362112d2a8436360c22b89dce1aa497d695cfccdfd5e9217d02fd7ea57e52` 匹配 terminal。

收到修复后只追该 delta：本次读取时 helper 为 `beb548b52bf1deb64f41cd105b0aacd75cdb906e1034721aa096c97ad1a56878`，测试为 `2375a07a4cc00a0603cdf9aeefe67386dd148b479e61cb5b99574c888f5074c2`。以下行号在该修复快照中；原缺陷初读行号另列。

## Confirmed major M1：join 沿用 fallback-only 临时值，可能误认 fast-path 输出未改

**位置。** 初读 `inspect_inline_reader` 249–259 行在 join 只把两个采样寄存器替换为 `reader_low` / `reader_high_raw`；其它 `values` 仍是按 fallback 路径线性计算的状态。随后 275–277 行允许使用这些状态作加法，317–320 行只检查最终符号是否仍为 reader token。

**最小触发。** 在现有 `reader_fixture` 保留前三次采样、比较以及两次 fallback load，将 branch target 改为 `0xa0`；在 fallback 两 load 后放 `pc=138: c.li r8,0`，join 放 `pc=170: l.adda.u r13,r13,r8`，identity 放 `pc=186: l.movs r5,sipinfo`。各非空操作位于不同 packet，仍有五个正确地址的 load、正确 unsigned compare、相同 high/low join 目的及三个不同输出寄存器。

**推理及后果。** 原模型在 fallback 见 `r8=0`，join 后认为 `r13 + 0` 仍是 `reader_low`，因此接受。实际 fast branch 跳过清零，`r8` 是入口值；若其非零，join 加法已经改变 low。这是 helper 可检查范围内的明确 false-pass，不是要求 MMIO 或外部入口证明，也不指称本次 14 个实际成功 reader 已出现此形状。即使所有产品资格字段仍 false，也不能把该 false-pass 作为可靠的有限 shape/传值证据。

**最小修复与验证。** branch 处快照 fast 状态，join 时对所有后续可读寄存器合并 fast/fallback；缺值按入口符号，值不一致保留未知。仅已独立核验的 low/high 对可置为对应采样 token。新增上述完整反例，并要求拒绝原因是输出不再为 reader token，避免由构造错误或额外控制指令误充验证。无须新增设备/数学或 ISA 矩阵。

**当前源码修复进度。** 候选 305 行保存 `fast_values=dict(values)`，258–263 行对并集逐项合并；不同值变成 `reader_join:<reg>`，随后 264–265 行只为已核 pair 赋采样 token。对于反例，`r8` 合并为未知，join 后 low 含这个未知项，327–328 行会拒绝。新测试 211–218 行保留原完整采样结构，确实只在 fallback 清零、join 使用该值，并限定 `match='Reader output register'`。源码与负例覆盖根因；v1 收据不能替代修复后同版执行闭环。

## 其它有限规则判断

reader 对 marker 使用 16B packet 起点，不将 DI 地址当精确指令 PC；扫描跳过已知 padding，要求第一条有效指令位于该 packet。五次 load 的地址、前三次 low/high/low 的 unsigned 比较、forward join、fallback 目的和地址、branch 前 fast 输出及 join 前 fallback 输出均有明确检查。未知 opcode、额外控制、缺失 reread、不同地址或输出覆盖均拒绝。寄存器是从实际 load/compare/identity 推导，不再由 actual runner 人工传 `r13/r9/r5`。

同 packet 的显式源 RAW 与同目的 WAW 保守拒绝，WAR 可保留；本 reader 白名单没有未计入源集合的 read-modify-write 指令。native 加法以 32-bit modulo 表示，未知入口保持符号，立即数按各已支持形式检查范围。上述 M1 修正后，未发现这份有限运算规则另有具体等值误授。

bridge 只检查 identity 后、人工 tail 前的有界 guard：scalar 指令不得写三个输出，调用/未知指令和 backedge 拒绝，forward 条件 branch 不得进入 tail packet 范围。所有获准 scalar load/move/add/high-immediate 都是显式单目的写，故保守禁止写输出足以建立这段输入寄存器保持；本函数不需要证明其它临时量或 guard 条件值正确。允许 branch 离开所选记录路径，与 `record_path_selection_qualified=false` 一致，不能外推成 guard 必然到达 tail 的证明。实际 tail 再由原 checker 拒绝未知 store alias、字段覆盖和 packet forwarding。

未将上述输入范围当作一般 CFG 证明：完整 decoded instruction list、同 ELF 字节绑定以及 tail 边界仍为 caller 责任；在 reader/bridge 范围之外进入、离开后返回，或人工漏选指令，不由本组件自动排除。现阶段资格字段及说明如实保留这些限制。

## v1 实际证据与未闭验证

v1 poll terminal 0，`wall_ns=815718625`（0.815718625 s），180 秒预算。runner 先运行 normal / `-O` pytest，任一非零即停止，再处理实际原件；源码中可枚举原 18 加新 18 共 36 个 fixture。当前读取的 poll/runner 支持该控制链成功，但本次尚未读取回收的两份完整 fixture stdout，不将它写成已逐日志核验。

runner 对两 matching loaded ELF/native 校 SHA，并对解析出的每条 native instruction 将显示 bytes 与唯一 executable section 比较。原件分别是 ELF `7d56f25f70633d7f0d813a78e8ded073b884a4356d940a4cb48c710794f00500` / native `a4423a389544cde04466ad381de272754c8c79d3860eabc48dd86898a9015e8b`，以及 ELF `5860432eef0a3004e35740a68b17b10bd9f33d49bf3ab7a30f8cb11be72131f6` / native `3e15c05637ef8ab999165d5496ebe07e7dff1967aa648828437c65038c063935`。这是同原 capture 取回的对象，不是重新 codegen 的替代物；字节核同也不独自证明反汇编列举了所有可能入口。

按唯一 end-marker 地址去重，ELF0 为 5/11、ELF1 为 9/12 结构成功，其余九项保留 `unverified` 及具体错误，未静默丢弃。实际 common-end `0xaaa0` 中 `0xaaaa/0xaaca/0xaada` 的三读、`0xaaea` branch、`0xaafa/0xab0a` reread 与 `0xab1a` identity，直接对应原 native；这里没有 fallback-only 临时量参与 join 后计算。该 reader 自动推导 `r13/r9/r5`，通过 32 bridge rows 连到人工指定 `0xabce..0xb05a` 的原 219-row tail，word6/7/8/19 stores 仍为 `0xadea/0xad2a/0xad8a/0xaeca`。

当前最少必要验证仅是最终修复/格式冻结后的 matching normal / `-O` 新反例与同两对象、同 23 个 marker 的重复读取；不需重放设备/SDK/数学。应保留九个 unknown，而不是把 14/23 成功解释为全部 marker 或所有 site 完成。

## 有限结论

初版存在上述一个 major，候选源码已给出有界、对应的修复，待 matching 收据闭合；没有新增其它 confirmed 缺陷或 optional 要求。本模块仍为未接自动入口的 source-loaded 内部组件，不能称 normal-installed 产品资格。MMIO base、external entries、真实 selection、ring/sequence、动态 site/begin tuple、source/loop 均未授予，tail 范围仍人工 structural case；也未授予独占 cost、engine busy 或 whole-goal 资格。

## M1 最终 matching closure（inline-v2）

本追加更新上述中间进度：**M1 的源码修复、对应语义负例与同版实际对象回归已经闭合**。本有限 review 没有剩余的 confirmed blocker/major/minor；九项实际 reader 的 `unverified` 及其它原资格限制继续保留。

已实际读取最终 helper/test、`gcu-inline-poll-v2.json`、input-v2 两 helper copy/测试、format-input-v1 的格式前源码，以及回收的 `gcu-receipts-v1/runs/inline-v2/output/{normal,optimized}.log`、`result.json` 和 `gcu-hooks-v1.json`。当前 helper SHA256 为 `dcc0d5eb8a5493dc8b2bda43acb4cb9695631d339855299c7badbea4ded42812`，测试为 `01c64b3d2378b9a4f34f1a986c4e75ccd975af179c861dd138f791acabe2b1a5`；input-v2 的 root/package helper 与测试逐字节匹配当前文件。input-v2 归档 SHA256 为 `92dd601862762644f018934e17d0c82100d69046666bad794f5721dd6ed38384`。两文件格式前后分别 AST 相同，修复逻辑未因格式发生变化。

最终 helper 336 行保留 branch 状态快照，273–281 行合并全部寄存器后只为已核采样对生成 low/high token；测试 242–251 行保留完整 fast-path / fallback-only-zero 反例并明确要求 `Reader output register`。它验证的是原错误路径合并，而不是其它解析失败。

inline-v2 实际 terminal 0，`wall_ns=816182608`（0.816182608 s），预算 180 秒，runner SHA 与 v1 相同。完整 normal / `-O` stdout 各为 **37 passed in 0.04s**；`-O` 仅多出预期 pytest assertion warning。ruff、yapf、check-ast 收据均为 0，收据 SHA 与当前两文件一致。本次复核没有自行执行测试、组件或 SDK/设备。

回收 result 与 poll 中 result 逐字段一致，绑定最终 helper 和前述两个 matching loaded 原 ELF/native，仍为 5/11 与 9/12 reader shape 成功，九项 unknown/error 全部保留。实际 shared-end 自动推导 `r13/r9/r5`，经 32 bridge rows 连接原人工 tail，四个 end 字段 store PC 仍为 `0xadea/0xad2a/0xad8a/0xaeca`。因此这份收据关闭 M1 修复后的 matching 缺口，不是继承旧 v1 绿灯。

该结论仅支持有限 inline register shape 与选定 tail 的相对字段传值。MMIO、external entries、真实 selection、ring/sequence、动态 site/begin tuple、source/loop、normal-installed 及 whole-goal 资格均未授予；人工 structural tail 和未接自动入口的 source-loaded 内部组件状态保持不变。本追加不新增验收门。
