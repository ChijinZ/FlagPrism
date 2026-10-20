# R092 automatic relative record-block selection — finite runtime review

审阅对象为候选 `9d238911290b42475833b431cac71f85e0ff2451`，审阅时工作树干净。请求配置为 GPT-6.1-Sol / xhigh；实际 resolved model / reasoning 配置未暴露，记为 unknown。独立只读审阅，没有读取其它席结论，没有执行产品、import、checker、测试、SDK、设备或远端命令。本报告是唯一写入文件。

## 结论与 confirmed findings

本增量未发现 confirmed blocker、major 或 minor。新增 `inspect_inline_record_fields_auto` 可以作为内部、有限的自动 tail 选择功能交付；现有代码和直接收据支持“从已绑定的实际 native 指令中自动选择一个受支持的直线 block，并检查 reader 输出到相对 end-record 字段”的结论。没有发现它通过仅检查合法 prefix、忽略终止 control packet 中的 store，或选择任意一个歧义候选来误放的具体路径。

这不关闭原整体 source/loop 适用链，也没有把该内部 helper 视为 default capture / offline 的已安装功能。它对两个实际对象的结果确实是 **1/23** distinct end-marker locations 通过相对字段检查、其余 22 保持具体 unknown；不是 23/23 source qualification。

## 已读代码与有限判断

实际读取 `Debugger/python/flagtree_debugger/gcu_native_values.py`，包括新增函数（452–527 行）和它复用的 reader、bridge、symbolic record-tail 检查；读取 `Debugger/test/test_gcu_native_values.py` 的已有测试及新增测试（255–301 行）。产品文件 SHA256 为 `f9c46304eb45a37773ee3bcebc202a09d0a39d5dc307ba87286a544adab2bbc2`，测试文件为 `07730ef841de78ac6616889695352d53611b047cba1a840e231a97d73327c649`，与提交的 `source-freeze.json` 一致。

| 关注点 | 实际实现与判断 |
|---|---|
| prefix-only 放行 | 候选延伸至下一个已知 control packet 或输入末尾，再把整个直线 block 交给原字段检查。达到 magic / 必需字段后不会提前返回；末尾覆盖、未知操作或无法绑定的 alias store 仍在检查范围。 |
| control packet co-issue | 终止 packet 的所有其它指令均检查，只有列出的 padding 可接受；非 NOP store 不会因 control 在其后打印而被裁掉。新增 `control_packet_store` 反例对应这一风险。对不支持的合法 co-issue 可能保守拒绝，未见误授资格。 |
| 未知控制与覆盖 | 未列为 control 的未知操作留在候选中，原 symbolic checker 拒绝。不能通过跳到稍后的候选绕过未知指令或 call，因为 reader-to-tail bridge 也检查这些指令。bridge 中覆盖三个 reader 输出寄存器、回跳和进入候选内部的 guard 均拒绝。 |
| 字段与 alias | 继续使用原有限 32-bit symbolic value flow；检查唯一 magic、相对 end-low / masked-high / 两个 identity 字段以及后续覆盖。无法证明与 record base 同一 symbolic 地址族的 store 被拒绝；本增量没有把未知地址默认为无 alias。 |
| 边界预算 | 输入仍受 reader 的 100000 条上限约束；起点只取前 64 条 continuation 中 control 后的有限集合，bridge 最多 64 条、单 tail 最多 512 条，超限不通过。终止 packet 扫描虽然遍历有限输入，没有引入无界搜索。诊断文本截断至 1024 字符。 |
| 候选歧义 | 每个候选独立经 reader/bridge/tail 验证；零个成功报 unknown，多个成功报 `Ambiguous automatic native record blocks`，不会取首个成功。该唯一性仅针对所检查的有限候选，不表示已经证明全 CFG 路径唯一。 |

函数返回的 block 结束处字段关系不等于后续控制流执行完毕后的最终发布状态。后续路径、外部入口、分支选择、begin/site incoming tuple、实际 allocation 和 MMIO 仍未被此函数证明；代码保留相应 false 字段，docstring 与 README 的范围一致。无需为了本 helper 的有限声明新增通用 CFG / ISA 证明器。

## 直接证据核对

实际读取候选 `integration/evidence/timeline-gcu-auto-tails-r092/{README.md,source-freeze.json,actual_runner.py}`，以及 root `artifacts/timeline/run-092/preflight/gcu-auto-tail-receipts-v1/runs/automatic-tails-v2/` 下的 `terminal.json`、normal / optimized 日志、`output/format.json` 与 `output/result.json`。

V2 owned runner 为 terminal / returncode 0，耗时 2.671033470 秒；normal 和 `-O` 各 46 passed。优化模式的 pytest warning 原样保留；产品拒绝检查使用 `_need`，本增量没有依赖会被 `-O` 删除的 `assert`。新 fixture 覆盖普通和 forward-guard 正例，以及 late overwrite、alias、unknown opcode、tail 内入口、call、reader 值提前改变、终止 packet 非 NOP store 七类负例。两轮 Ruff / YAPF / check-AST 收据均为 0，runner 明确比较格式化前后 AST；返回源码 SHA 与冻结一致。

实际对象检查是 source-loaded 内部 checker 在既有 ELF/native 上运行。runner 核验 ELF/native SHA、逐条打印指令的 bytes、唯一可执行区间、descriptor / symbol extent，并检查没有未覆盖的非零 executable bytes；没有应用重放或 SDK codegen。结果分别为：

| 原实际对象 | distinct end locations | 自动相对字段通过 | 保留 unknown |
|---|---:|---:|---:|
| ELF `7d56f25f70633d7f0d813a78e8ded073b884a4356d940a4cb48c710794f00500` / native `a4423a389544cde04466ad381de272754c8c79d3860eabc48dd86898a9015e8b` | 11 | 1 | 10 |
| ELF `5860432eef0a3004e35740a68b17b10bd9f33d49bf3ab7a30f8cb11be72131f6` / native `3e15c05637ef8ab999165d5496ebe07e7dff1967aa648828437c65038c063935` | 12 | 0 | 12 |

唯一成功是第一对象 DI site1 的 shared end packet `0xaaa0`，自动选择起点 `43980`（`0xabcc`）、终点 `45150`，bridge 31 条；低/高/identity 推导为 r13 / r9 / r5。返回 `tail_boundaries_automatically_selected=true`、`reader_to_relative_fields_checked=true`，同时 `source_region_qualified`、`reader_valueflow_qualified`、`record_path_selection_qualified`、`ring_allocation_qualified`、`incoming_begin_site_qualified` 仍为 false。其余 location 有地址不匹配、缺 identity、guard 进入 tail 内部或未找到唯一 magic 等具体原因；这些 unknown 不能据此称为原硬件记录错误。

V1 和 V2 都保留在原 archive 中；最终判断绑定增加 co-issue 反例后的 V2，没有用 V1 替代。已核收据没有声称 wheel 安装、default/offline 接入、设备执行或 23 个 source region 全通过。

## Verification gaps、未承诺范围与 optional

本有限增量未发现需要新增产品修复或补跑矩阵的必要缺口。现有收据足以支撑上述 helper 级结论。

完整 ELF / 指令输入绑定是 caller 前提；本 helper 自身不接收 ELF bytes。当前实际 runner 提供了有限原件绑定，但不能把任意未绑定或省略指令的第三方 list 当成已验证 native。default/offline 接入、source-body / runtime-loop 与 incoming tuple 适用链、MMIO 来源、record 选择与后续发布状态均不在本增量承诺内。原整体剩余适用链保持原状态，不因这个 1/23 自动检查结果扩大或关闭。

Optional：若以后修改搜索上限或候选形成规则，可加确切 64/512 边界及多成功候选反例，固定这些已有保守拒绝分支。当前无证据表明这些分支有误，不把它们列为本次交付阻断，也不要求新通用 native 证明工具。

未读/未执行：没有重读其它 backend、旧 whole review 矩阵或 peer 报告，没有重跑已有数学、raw capture、TP/UI 或 SDK。结论仅绑定本提交的自动 tail 选择增量及上述直接收据。
