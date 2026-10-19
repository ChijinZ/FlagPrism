# R073 limited compiler review

本报告审阅冻结 `d3d05750cd34c9500a49b0dc1f1de3ea2915bb0d` 相对 `7bffec1` 的有限 native-loop delta，并保留后续小修复的复核位置。实际阅读 `timeline_nvidia_loops.py` 全文、boundaries 自动接入、两个新增测试和 runtime/testing 文档 delta；另读 `_predecessors` / `_predicate`、独立 issue boundary / straight-path 的直接相关代码，以及 `run-073/preflight` 的 v2 source-loaded 收据、runner、源码与 formatted archive。没有阅读 peer 报告。实际 serving model 未暴露，未知。

**冻结版结论：确认一项 Major 路径遗漏，条件 EXIT 的 taken termination 没有进入每迭代出口义务，因此目前不能对冻结版的完整 native iteration/exit 声明签字。除此之外未发现新的确认缺陷。六份实际原件的既有成功不证明本遗漏不存在，也没有据此认定六份原件实际执行错误。** 本报告不作 whole-goal 签字。

## Confirmed findings

### Major M1：条件 EXIT 的 taken 路径可以绕过 reader 而被放行

- **位置：** 冻结 `timeline_nvidia_loops.py:102` 仅将没有 successors 的节点当作 terminal，`:148` 的局部支配义务只有 latches、普通出边起点与这些 terminal；直接依赖 `timeline_nvidia_late_values.py:88` 对 `EXIT` 的图只保留可能的 fallthrough，没有表示 taken termination。
- **触发：** selected natural loop 内、reader pair 之前存在 `@P1 EXIT`。它仍有 fallthrough，可位于 natural-loop nodes 中，但不被当作一次退出。
- **最小代码推理：** 直接复用 `test_nvidia_native_loops.py` 的有效 simple fixture，仅把 PC 16 的 NOP 改成 `dict(opcode='EXIT', predicate='@P1')`；PC 32 / 64 两 reader、PC 48 HMMA、PC 80 条件回到 16 及 PC 96 最终 EXIT 均保持。独立 issue bracket 32–64 仍是完整 straight single-entry path。复用 CFG 实际只表示 `0→16→32→48→64→80`、`80→16/96`，所以自然循环为 16..80，切回边后的 DAG 中两个 reader 支配唯一被表示出的出口起点 80。冻结规则会给 checked；实际 predicate 为真时却在 PC 16 退出，没有经过任一 reader。这是明确的逻辑反例，本 reviewer 未执行它。
- **后果：** 可错误输出 `native_iteration_boundaries_verified=True` / `one_reader_pair_per_native_CFG_iteration_or_exit`。其它 source/participation/busy 资格为 false，不能修复这个 native 路径事实本身的错误。
- **最小建议：** 在新 loop 层单独保留每个可执行 EXIT 的退出义务（predicate 不恒 false），与 latches / 普通 exit sources 一起做每迭代局部支配检查。保留它的 fallthrough，也无需改变原 value-flow 图；或保守拒绝这类结构。输出对应 instruction PCs，避免在 exits 诊断中继续遗漏。
- **最小验证：** 添加上述 before-pair conditional EXIT 反例；另覆盖 before-end 拒绝、after-pair 可以通过及 `@!PT EXIT` 不产生退出义务。该 before-pair 例不依赖破坏原 issue bracket，能准确回归此漏判。复用现有六 capture 即可，无需新 GPU 或数学矩阵。

Confirmed blocker / minor：本次有限阅读没有其它项。

## 其它算法与边界检查

函数级 dominators 从实际入口计算，backedge 要求 header 支配 latch；同 header 的全部 latches 合并，逆向收集 natural-loop nodes 时继续检查 header 支配关系。选取同时包含两 reader 的最小候选，尺寸并列保持 ambiguous。切断全部该 header 的 latch returns 后，Kahn DAG 检查拒绝残余 cycle / nested loop；外部边只能进入 header，且每个非 header 节点仍须有局部 predecessor。这些条件没有用已观察到的一条动态路径替代其它 CFG 路径。

局部 dominators 在当前 iteration header 重新开始，而不是使用 function-level 的历史支配集。结合上游已独立 checked 的 reader pair 直线路径，正常 latch / 普通出口约束可以排除 reader bypass 或重复执行。对其它函数的 inventory 失败也只产生对应诊断，不清除已成功函数的结果。M1 正是这套推理所用出口集合不完整，而不是需要新的 ISA 证明器。

资源范围有明确上界：整函数最多 4096 native nodes，backedges 最多 128，函数 dominator 更新次数与 natural-loop inventory visits 分别最多 1,000,000；每函数 inventory（包括失败）缓存一次，局部 iteration 使用已有限 nodes 的 DAG/bitsets，没有枚举动态路径或模拟 trip counts。未发现本 delta 新增的无界路径搜索。大函数、未知控制转移、预算超出均返回 unverified；这些上界不是任意输入下的 wall-clock 性能承诺。

## 已读取的实际收据

`loop-rule-poll-v2.json` 的 terminal 为 0、4.773164146 秒，stdout 为 `18 passed in 0.06s`。18 例由 5 个有效变体、12 个拒绝变体和 1 个跨函数失败隔离检查组成；已有 early-exit 使用 BRA 跳出，未覆盖 M1 的 conditional EXIT。

runner 对真正 default 与 max_sites1 sparse 各两份已保留 runtime-K captures 使用外部注册的 3/7 次数，对 scalar C1 两份原件使用 3/3 和 `member-count 2`。选择来自原 plan 的 kind/group size，随后要求所有所选诊断成功，不是按 checker success status 挑样。单 member 的最终表达式在 loop 外，并未冒充被验证 recurrence。p01 重新加载 object map/native report，核对 raw SHA/complete、canonical site、观察到的每 observer 次数与每个 endpoint u64。该次数 cross-check 不生成 source iteration ID，也不证明所有观察者参与完整。

冻结版四份源码与 executed input 的 stdlib AST 全部一致；loop module SHA256 `cbe467ca6ed770b2720413ee88f3772d71f126945dc7c3ba756317271f018be7`，boundaries 为 `c13764df6e01480d23228efe8f7b61a1712f6e2eb3afbdce8b75078f34213f6e`。runner SHA256 `005926e067d04fdbca611994f8077dfc606bd957fad4b1a0ebc1ca9b31ba9af9` 与 terminal 相符。收据明确 normal_install=false、device_executed=false；它没有把源码 overlay 说成已安装新产品。

## Verification gaps / scope / optional

M1 的新小修复及对应 negative 的终态尚待本报告后续追加；正常新 wheel 也不能从旧 freeze 的在途安装推断已包含修复。原18项及六 capture 通过不替代新增语义反例。

成功 native loop 仅是有限 CFG iteration/exit 的 reader 路径事实。它不证明 source loop/iteration 身份、source all-path region、exclusive cost、参与完整性、终止、clock scale、ordinary pipeline preservation 或硬件完成/忙碌；产品保持这些资格为 false，未从第 n 条记录合成 source iteration ID。

本次没有 import 产品、运行测试/编译/SDK/GPU/数学、连接服务器、重跑 UI 或启动子 agent，仅做本地只读与本报告写入。没有额外 optional 扩展。

## 追加：conditional EXIT 小修复与 source-loaded v4

只读复核完整小补丁：`_inventory` 在原 value-flow 图之外单独收集 reachable、opcode 为 EXIT 且 `_predicate(...) is not False` 的 instruction PCs；`_iteration` 取其与 selected loop nodes 的交集，合入所有 return/exit 的局部支配义务，并输出 `exit_instruction_pcs`。原 fallthrough 图不变。调用点已传入新增集合，return 字段与维护测试一致；此前编辑中的两处机械接入问题未进入冻结版，不列为独立 confirmed defect。

**这个修复静态上正确关闭 M1 的遗漏。** before-pair 的 PC 16 EXIT 会在自己的局部 dominator mask 中缺少 reader bits，因而拒绝；before-end 同样缺 end bit；after-pair 的退出点可被两 reader 支配，继续允许；`@!PT EXIT` 不产生 taken termination 义务。新四项 fixtures 对应这些语义，其中 before-pair 保留了原独立 issue bracket，是准确的回归。没有发现该小修复另一个具体错误。

实际读取 `preflight/loop-and-install-poll-v4.json` 的 loop-rule-v4 部分及 `loop-rule-input-v4.json`。source-loaded terminal 为 0、4.873274557 秒，stdout 为 `22 passed in 0.07s`，stderr 空。runner hash 与已读 v2 runner 相同，继续完成 default / max_sites1 sparse / 原 member-count2 scalar 的六 capture 检查；未执行设备。修复产品源码与其 executed input bytes 完全一致，SHA256 `93bf1ac3b32b078c2bb756b825677caab1ae3755fa3029c17c172017ce70ae81`；测试同样 bytes 一致，SHA256 `831aa224ef88c976e4b3bb02dd7d91315326ffcff412ea71cbe03668b7199890`。

**当前 M1 在 source fix + 对应语义 CPU 回归范围内闭合，正常安装修复版仍待冻结和 v2 收据。** 同文件的 native-install-v1 属于旧 `d3d0575`，不继承为 M1 修复资格。其余独立 source/loop身份、普通流水保持及 whole-goal 边界不变；没有重开新矩阵。

## 最终追加：M1 installed gap 已闭合

实际完整读取 `preflight/native-install-complete-v2.json` 的 terminal、18 steps 和 result，并核对两个 steps 副本一致。terminal 为 0、81.859141007 秒，18 步全部为 0，source commit 为修复冻结 `efb23636c2aa3a6e8866875133765c4de3a00f91`。641 installed members，正常 wheel SHA256 `1f72d16c08a1d60e6ddfb2875827bd7db17bff7ee9fe8dc700966a8ef4fcc521`；隔离安装/import 成功。compiler core 与 recorder 明确复用原未变 native，本次没有新 native/GPU 执行。

冻结后的 loop module / test SHA256 分别为 `7825f43bf0e89dbbc3c98d64ec325331da8ddb7ff5c8e33f29539d47f6614c22` / `2a9b58377aad8fdeda1d49b166e8c75bd88d30bd4db89ea387b116b3cb63d1cf`；与已审 v4 小修复的 stdlib AST 相同，只有格式差异。安装后 normal / `-O` 均执行 22 loop + 13 matrix 维护例并以 0 结束；default、真正 max_sites1 sparse、原 member-count2 scalar 的六份既有 capture，在 normal / `-O` 下的 raw endpoints 与 per-observer counts 检查也全部为 0。

公开 normal control 报告实际包含 site 23 的 checked `native_loop_sites`：header PC 3104、latch 6032、普通退出 6032→6048，两 reader 为 4112 / 4240，`exit_instruction_pcs` 为空。它只令 native iteration boundary 事实为 true，source iteration identity / source cost / participation / hardware overlap 均为 false。公开导出为 8 counter + 2 dependency，counter bytes 与 R072 原件相同，application_replayed=false。

**M1 现按源码修复、准确 EXIT 语义回归及修复冻结的正常已安装路径闭合；本次有限 compiler delta 无剩余 confirmed blocker/major/minor。** 原缺陷与阶段性待证记录继续保留为历史过程。只有新 2 dependency 的 TP 验收仍在途，本报告不预判其成功；source/loop 身份、ordinary pipeline preservation 和 whole-goal 等原独立边界均未因此关闭。此次追加只读取本地收据，没有重新运行任何检查或设备。
