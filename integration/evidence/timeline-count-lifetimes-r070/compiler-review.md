# R070 limited compiler review

审阅对象是相对 `7f8fdf508768cfaa9fcb82e7dfb6eaed65ca1212` 的 count-lifetime 修复：`Profiler/python/flagtree_profiler/timeline_nvidia_late_addresses.py` 与 `tests/timeline/p01_nvidia_count_lifetimes.py`。审阅期间该 delta 被提交为 `1326509`，随后 HEAD 为 `a71d32fe16ae699656dd02d98034d1d01db0270a`；本报告没有审阅随后无关的 wheel manifest 修复。实际 serving model 未暴露，未知。

实际阅读了上述两个文件、原实现 diff，以及其直接依赖中 `_ReachingWords`、`_predecessors`、`_predicate`、`_destinations`、`_straight_path`、`_single_entry`、record-field/address 与 raw-ordinal 检查；阅读 `preflight/count-suite-input-v3.json` 和 `preflight/count-suite-poll-v3.json`。只进行了文本、Git、stdlib JSON/hash/AST 读取，没有 import 产品、执行 fixture、编译、运行数学、连接服务器或设备，也没有阅读 peer 报告或修改实现。

**结论：live-definition 修复方向正确，四份实际原件的有限成功收据成立；但还有一项 count 安全检查遗漏，当前不建议把这版作为已完整恢复 count-execution 安全的修复签字。没有据此认定四份真实 capture 已发生计数错误，也不涉及 whole-goal 资格。**

## Confirmed findings

### Major M1：live zero reset 可以被当成 initialization 放行

- **位置：** `timeline_nvidia_late_addresses.py:367`、`:405`、`:478`、`:500`。`initialize` 现在仅要求数量为一；其 PC 没有参与批次配对或“先前记录/更新不可到达”的检查。新的逆向 CFG 检查只从固定首批的 region 起点出发。旧代码要求首批 literal 更新之前的两 word 都来自唯一 zero initializer，这个顺序约束已移除。
- **触发：** 唯一的 `MOV.64 count,0` 出现在记录之后，并在条件分支的一路上抵达 published header。该写是活跃定义，而不是应被忽略的寄存器临时生命周期。
- **代码推理：** 以下有限 CFG 已足以说明遗漏，不需要未知 ISA 或设备假设：先执行一整个固定零基首批及其 `MOV.64 count,6`；随后条件分支，一路直接到 header，另一路执行唯一 `MOV.64 count,0` 后汇合到同一 header。两个 word 在 header 都有完全定义；`_live_count_definitions` 会收集非零 literal 与 zero 两个写，inventory 分别把它们标成 `initial_batch_count` 和唯一 `initialize`。非零更新可与首批一一配对，首批 region 保持 single-entry straight path，其 region 起点之前没有 record stores，因而现有所有新增条件均可满足。执行 reset 分支时，已经写完六条记录，header 却发布零。加入正常 append 批次不会改变这个问题，只要 reset 仍在这些批次之后，另一路保留正常最终 count。
- **后果：** checker 可在确有活跃 count reset 的 CFG 上给出 `dynamic_count_execution_verified=True`。raw ordinal binder 只检查实际被 header 公布并解码出的事件，不能替代“没有把先前记录计数清零”的静态检查。这里是确定的检查逻辑遗漏；本轮没有运行该反例，也没有声称当前四个实际对象具有该结构。
- **最小修复建议：** 对唯一 live zero initializer 也作有界逆向 CFG 检查，拒绝任何非零 batch-count 更新或 record store 能够先于该 zero 写执行的路径。需要同时检查非零更新与 stores：literal 更新可能被调度到 stores 之前。保留现在基于真实 uses 的 lifetime 切分，不恢复全函数按物理寄存器同名误扫，也不必要求无关临时值为零。
- **最小验证：** 增加一个 CPU native-CFG semantic negative：首批完成后，在 header 前的一条分支上做唯一 zero reset，另一条分支保留非零 count；确保该结构被拒绝。再复用已有四 capture 和五类 negative 即可，无需新数学或设备矩阵。

**Confirmed blocker / minor：** 本次有限阅读没有其它项。

## 已核实的有限正面事实

`count_uses` 从实际 header count store 和实际 counter-index LEA 起步，`_live_count_definitions` 对两个 word 的全部 reaching definitions 取并集，并递归追踪 self `IADD.64` 的输入。未知谓词的写保留在集合中，partial、predicated、错误 add input 随后拒绝；任一路 entry/uninitialized 也拒绝。没有看到把这三类活跃写简单过滤掉的错误。LEA 两 word/carry 的既有保护及 append 的地址读取—count update 间不许改 count 条件仍在。

固定首批的新逆向扫描确实走所有 predecessor，不在 literal reset 处提前停止，并检查全部已绑定 field-store PCs。因此它会拒绝首批之前已经存在记录以及首批循环回入；允许此前同名物理寄存器存过无关临时量是合理的。这些事实不关闭 M1 中另一个 zero 写的顺序问题。

现有 terminal 为 return code 0，2.468912959 秒。四项实际原件分别覆盖 default/sparse 的 K3/K7；default live writes 为 1408/1504/5456/9344，sparse 为 1392/2064/4800/7808。sparse 的 1456 与 1552 被报告为非 live 的同名寄存器写。每种设置的 K3/K7 分别保留 1280/2304 个 raw-bound batches；五类 negative 各拒绝四次，共 20 次。收据明确 `device_executed=False`、`application_replayed=False`、source-region 与 ordinary-pipeline 资格均为 false。

输入收据中的 `addresses.py` SHA256 为 `2dde1d6f34d3d8813083ac7dc83bf19e5f3b501c4faa5df223e0407bbf2090a6`，当前格式化文件为 `72214e58be3758aef4dabd43e39912e58f3d889e6074111c32b9c0623a3ec3d6`；逐项 diff 仅格式，stdlib AST 比较相同。测试脚本同样仅格式差异、AST 相同；runner SHA256 `8742794574ac899bc9db96d2d2b56264ae390613bd6123e6312827c7674c4c79` 与 terminal 相符。不能把此说成 exact formatted-byte execution，但可支持本次所审语义版本的有限 CPU 收据。

## Verification gaps / optional

M1 尚无本轮执行复现或修复后 negative 收据；以上结论来自明确的控制/数据流代码推理。现有五类 negative 没有覆盖 zero initializer 被放到记录之后的情况。

本次没有重新独立生成机器码、检查新安装或重放任何 application，也不复开原 source/loop-region、absolute-slot、clock、ordinary-pipeline-preservation 等独立缺口。修复 M1 后，现有材料可支持的仍只是这两个对象、四次既有 capture 的有限 native count/address 与 raw ordinal 绑定，不是 whole-goal 签字。没有另外要求的 optional 扩展。

## 追加：M1 修复的有限静态复核

原问题记录保留。随后只读审阅了新增 `_no_prior_recording`、两个调用点及两项 zero-reset negative；此时产品文件 SHA256 为 `e22d07dd7e380cfa4828daf7fe7bda0b93a6e04a970b2827b94ab8be10c8bc30`，测试文件为 `530d2de7113d37ee222777489dbc9ed3c543b6cf1220303616718d06197535b2`，尚未提交。

**代码层面支持 M1 的最小修复。** `timeline_nvidia_late_addresses.py:465` 的 helper 从全部 predecessors 逆向遍历，使用有限 visited 集但不在 count 重置处切断。`:495` 将所有非 initialize count updates 与所有 record stores 合并为 forbidden，并在唯一 live zero initializer 前检查；`:525` 对固定首批入口使用同一集合。这样原反例中 reset 前的非零更新或记录必然被找到，循环回到 reset/首批也不会漏掉；此前不属于 live count 的无关 temporary 仍不在 forbidden 集里。没有发现这个小补丁引入新的具体正确性问题。

**验证仍需与原遗漏对应。** 新 `zero_reset_after_record` 通过向旧 entry zero 增加 predecessor，保留它原本通往首批的后继，因此同时制造了“先前 record store 可到达首批入口”的路径；原有首批逆扫也会拒绝该结构。它可检查新 helper 的拒绝行为，但不能单凭名称证明已回归 M1 的原漏判路径。最小补充仍是“首批完成后，分支上 reset，另一路绕过 reset，汇合 header”的小 native-CFG fixture；应确认旧 guard 接受而新 zero guard 拒绝。`zero_reset_after_count_update` 对更新前后约束有补充价值，但不能替代这一无首批回入的分支反例。

本次追加未运行任何 fixture，也未看到新增版本的终态收据。结论为 **source fix 静态通过；对应语义回归及安装闭环尚待实际收据**，不使用旧四 capture 的绿替代新增 negative。

## 追加：`baea706` 的对应 CFG fixture

只读核对冻结 `baea70620f8561369cc440fefba48f7938cbc25a` 的 fixture 与 guard；未运行测试或读取新安装结果。产品文件 SHA256 为 `9c5820e03738d4329107010783d9a5f400c881918717728742238eedb6ce1989`，测试为 `480dd5a77be2bbc25b94396e72e146ac12e253d4728ad88299170c22a7ba10b5`。

`p01_nvidia_count_lifetimes.py:25`–`:58` 现在准确对应 M1：PC 32 给完整首批赋 count=1，PC 48/64/80/96 是其四个 stores，PC 112 的条件分支跳到 PC 144 zero reset；旁路经 PC 128 直接跳到 PC 160，同一 header 也接收 reset 的 fallthrough。没有边回到 entry 或首批。`_predecessors` 对这个有限 body 保留两条路径，header 的两个 word 都能分别抵达 PC 32 与 PC 144 的完整 64-bit 定义；fixture 显式要求这两个 live write PCs 恰好被发现。

首批入口 PC 0 的 `_no_prior_recording` 显式正向调用（`:54`）应通过。批次覆盖 PC 0–96，是没有内部控制转移、没有外部中间入口的直线区；旧版首批逆扫在 PC 0 没有前驱，也会通过。因此旧 guard 不会因“首批回入”提前拒绝。新版 `_check_batch_control` 则在 zero initializer PC 144 逆扫时，经 PC 112 到 PC 96 的已完成记录写，必然在 zero-reset 约束拒绝。这关闭了前一追加提出的 **fixture 与原遗漏不对应** 的代码层验证缺口；没有发现该小 fixture 的具体错误或过度表述。

此时静态结论是 **M1 source fix 与对应 negative 均通过有限走查**。执行与安装的终态收据仍待提供；本次没有据 fixture 推断新 wheel 或任何设备行为。

## 最终追加：M1 的有限闭合

实际完整读取了 `preflight/native-install-poll-v3-final.json` 和 `preflight/native-regressions-v3.json`。安装 terminal 为 0、78.702621451 秒，13 个步骤全部为 0，source commit 为已审 `baea70620f8561369cc440fefba48f7938cbc25a`；隔离 venv 使用自身 ensurepip 与正常 pip install，installed import 成功。收据记录 639 installed members，wheel SHA256 为 `eb6452e55bf6d6f851cdc778bd8e853377bcad41e97da1d939520efddc6a0613`。本次是 Python count 检查修复的正常 wheel 装配/安装，沿用明确记录的未变 native compiler 和 recorder，没有声称重新构建它们。

安装后 interpreter 的 normal 与 `-O` 两项终态均为 0；对应结果各包含四份实际 default/sparse K3/K7 原件的完整 native count/address 与 raw ordinal 成功，以及 21 次拒绝。其中明确包含已静态核对的 `conditional_zero_reset_after_complete_batch`，加上原来的 20 次实际原件变异；不再使用两个不对应原漏判的 zero 回边负例。原 native-address 回归也为 0，33 negative 被拒绝，113 个原件文件保持不变。

**原 Major M1 至此按 source fix、准确对应且已执行的 CFG negative、normal/-O 已安装路径闭合。** 本次有限 compiler delta 没有剩余 confirmed blocker/major/minor；此前原问题与阶段性待证记录保留为历史过程，不再代表 M1 的当前状态。

同一收据中的公开 normal CLI 在复制 sparse bundle 上导出 8 counter 与 2 dependency，dependency reason 为 null，application replay 为 false。这只是离线产品入口的有限成功；本轮没有执行 GPU/application，也未读取或判定另一个仍在验收的 SQL job。source-region、ordinary-pipeline-preservation、absolute-slot 等原独立缺口与 whole-goal 资格均不因此关闭。没有重新运行任何测试、编译或设备任务。
