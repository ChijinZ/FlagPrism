# R088 GCU State payload admission：有限独立 compiler review

本报告只审新增 qualification helper、source-use audit 及两个实际调用 runner；不是 whole-goal、native boundary、pipeline 或 State SDK ABI 签字。没有阅读 peer 报告，没有执行 Python、产品、测试、SDK、设备、SSH 或数学任务；仅用文件/Git/哈希读取作静态复核。仅写本报告。请求配置为 GPT-6.1-Sol / xhigh；实际 resolved 型号与 effort 未由工具暴露，均记 unknown。

## 阅读与源码身份

实际阅读全文及当前 diff：`tests/timeline/gcu_state_writer_partition.py`、`test_gcu_state_writer_partition.py`、`state_source_uses.py`、`test_state_source_uses.py`；读取 root `run-088/preflight/check_gcu_source_admission_v1.py`、`check_gcu_profile_partition_v1.py`、CPU runner、parser probe、完整回收的 v1 normal/-O stdout、terminal、result 与 source-format result。复用此前独立审过的 R087 whole high-IR isolation certificate 合同，没有重开其审计。

审阅期间 candidate HEAD 为 `11d9b1f23ee2b623d951937bfba9efa54f45f828`；本 delta 含未提交修改，所以以下 SHA 比 HEAD 更精确。

| 文件 | 已执行 v1 字节 SHA256 | M1 修复后实际读取 SHA256 |
| --- | --- | --- |
| gcu_state_writer_partition.py | `91f5441b47fca355b9bc65aeefe97f845bd792dccfd8efa2c5873fff349fdd5f` | `923c704053e0c30752f08cbaa9e9d33741683779c36f0f57f4930a3053490fe9` |
| test_gcu_state_writer_partition.py | `c5d4a593afc7c396769e9f28a6fb5bd2b2acdd68f2412fbffaf8a95e1452abd9` | `a687c358170b3cbbcc8f704ef269328935f03ca16da3aa0595ca975cc4ed4c93` |
| state_source_uses.py | `73338d4f2d12dc1ed956d2a6327e10af58ff131a670b07c7efcdac139d4a7a54` | 相同 |
| test_state_source_uses.py | `cf4a4bdb73f44e278e8521662318dad8b081c5134798d4bb2817e176edbc2285` | 相同 |

回收的 `source-partition-input-v1` 四个 helper/test 文件逐个 SHA 与上表 v1 相同。两个 executed runner 的 SHA 分别为 `4c75bdeb14a4e56fef4a84d5c70e6010038c2730776ae3477078b4274ebfb7e7`、`d370785fd459f7edbda4118e0645664f57ff81423ce1bbf25ec98938b64b13b4`，与实际读取的本地 runner 相同。未自行重新核整个 archive ledger；读取到 root 的 receipt audit 为 207 members、全 indexed bytes match，archive SHA `0036d2b766a230641a667a2f6ffad9ca04d85a26b38e640ea5e1e3323f917301`。

## Confirmed findings

### M1 — major：空 formal-root 集合不能证明 payload store 目的为 private

位置：v1 `gcu_state_writer_partition.py:216` 的 `roots` 与 `:263–267` 的 admitted store 分支；修复后对应 `:250–279`、`:298–304`。

触发：在已有合法 admitted fixture 中加入：

```llvm
%bits = trunc i64 %base to i32
%global = getelementptr i32, ptr @external_global, i64 0
store i32 %bits, ptr %global, align 4
```

推理：`roots` 只累计 pointer formal，global GEP 不产生此类 root；v1 的 `not roots(%global)` 因而为真。该 store 在 payload 分支直接 `continue`，不能兑现“仅 private data store”的局部合同。这里是静态确认的 helper false-pass，不是发现现有 97 个对象已发生该行为；本 reviewer 未运行该反例。

后果：admission 会把一个明确 external-global 的直接 payload store 当作 private。即使上层 high-IR certificate 对真实输入另有保护，这个 LLVM 局部判定自身也不成立。

最小修复与当前状态：root 已增加正判 `private_destination`，仅接受实际 local/shared getter 或 alloca，经有限 GEP / addrspacecast / bitcast 传递；global、unknown、循环依赖均拒绝，并新增上述 global-GEP negative。已实际读取该修复，原触发在新逻辑下为 false；无需增加一般 alias/IPA。**源码层修复成立，尚未读取修复版执行收据，不以 v1 的 41 项通过关闭新 SHA 的执行缺口。** 最少验证是新 negative normal/-O 及原 33 distinct admitted partition 的同版复核，不需重跑 SDK、设备或数学。

没有另外确认 blocker 或 minor。

## 合同与实现边界

`ObserverPayloadAdmission` 是由受信 QA caller 提供的身份记录，不是自认证 capability。构造器只核四个 SHA 的形式和 State ordinal；`analyze` 再核 ordinal 对应实际 State formal。该分工已在 docstring 明示，不能单独构造四个任意 SHA 就声称取得资格。

新的源码审计使用实际 MLIR Value ID，完整 walk 后建立 State pointer propagator 闭包，再检查所有相关 operand 位置。State 作为 value、return、未知 call/region forwarding 都拒绝；load/store 只接受非 pointer 数据；源中原有 `tt.ptr_to_int` 不会被 observer admission 豁免。20,000 op 上限和有限 Value ID 闭包存在，未见本 delta 的具体 false-pass。此审计证明 pointer noescape，既不证明 State allocation 范围，也不代替实际 lowered transfer/actor 检查。

LLVM helper 默认仍严格拒绝 State address trunc/lshr。只有 admission 存在才把精确 `trunc i64 -> i32` / `lshr i64, 32` 的直接 projection SSA 作为 observer data；实际 State transfer、guard、descriptor、actor 枚举仍走原检查，没有因 admission 跳过整条 State 路径。

需要准确保留的组合边界：该 LLVM 检查止于**直接 projection SSA 到首个正判 private data store**，不作 store/load 后的传递 taint。例如同址 store→load 后的 unknown callee，并不由本 helper 独立识别为 payload 用途。已向 root 指明这一点；root 明确采用原有组合合同，由绑定的 R087 whole high-IR observer isolation certificate 覆盖后续 observer effect，修复后源码 `:232–237` 也已明确。不把“所有传递用途均由 LLVM helper 拒绝”当作已证结论，也不为此新增完整 ring alias/IPA 门。

## 实际证据及 verification gaps

`gcu-source-partition-poll-v3.json` 与回收 terminal 一致：CPU job terminal 0，42.175348913 s，owned deadline 240 s；无设备或 application replay。回收 normal 与 -O stdout 均为 **41 passed / 0.14 s**；-O 只有预期 pytest assert warning。v1 format result 的 ruff 为 no-files skipped，yapf/check-ast 为通过，不将 skipped 写成实际 lint 覆盖。

109 条历史行全部作 source noescape 检查（33 distinct source）；97 条有 preserved certificate 且完成 partition（33 distinct partition）。其余 12 条全部因旧 q05 `Historical transform is not preserved under the current checked producer` 保留 unverified，不是新 State checker 拒绝，也不是 109 条 partition 全通过。最终适用 registry 中替代条目的选择须按原 frozen case/affected 登记组合；本报告不要求重做这 12 个历史 producer。

外层 source runner 实际核 capture/math、TTIR、before/after SHA、R087 preserved 状态与 certificate SHA/三个 true 字段/边界；partition runner 再核 snapshot binary、math fatbin、compiled hash、LLIR/TTIR、原文件/certificate、State ordinal、wrapper 精确 forwarding、physical threads、grid、elements，并仍核每元素 count=1。缓存 key 包含实际 LLIR SHA、State formal、threads/grid/elements，且逐行身份核验在缓存使用之前；未见本 delta 的缓存错用。

尚未由本轮收据关闭的仅需如实区分：

1. M1 新 SHA / global-GEP negative 的同版执行确认，见上；旧 v1 实过不继承为修复版实过。
2. `functions.ll` 与实际 loaded LLVM、SDK transfer/launch ABI 的完整受信链仍要复用对应原收据绑定；本轮有限阅读没有重新独立核全部 SDK 资源及历史译出文件 ledger。runner 对 retained `original.mlir` 输入核 SHA，并记录译出 LLVM SHA，但这不替代其既有真实 translate/ABI 证据。输出继续保留 `state_writer_qualified=false`、`SDK_ABI_binding_qualified=false` 是准确的，不需因此新增 SDK/math 重放。
3. 原 source/loop native boundary、pipeline 及 whole qualification 仍不在此 delta 交付范围内，也不由 observer payload admission 获授。

## Optional

无新增 optional 工作建议；优先只补 M1 同版最少收据及既有外层身份组合。

## 有限结论

此 source-noescape + checked high-IR isolation + actual lowered State partition 的组合路线在本小范围可成立；v1 的真实结果及 12 条历史拒绝均有明确保留。已确认的 M1 private 判定漏洞已作最小源码修复，执行闭环待对应新收据。除此之外，没有在约定有限合同内确认新的实现缺陷；不能把本报告解释为 State SDK/native/pipeline 或 whole-goal 放行。

## M1 修复版 v2 同版收据追加

本追加只关闭上述 M1 的匹配执行缺口，保留前文为历史记录。没有重审 whole、运行代码/测试/SDK/设备/SSH，或新增 memory taint/alias/IPA 门。

重新读取了最终 `private_destination`、direct SSA 合同注释及 global-GEP negative。最终 helper SHA 为 `867a00b2599c379acfa49bcad0f3295bc05449100d764c308eb1e50c08241c6d`；test SHA 为 `a687c358170b3cbbcc8f704ef269328935f03ca16da3aa0595ca975cc4ed4c93`。对 candidate 与回收 `gcu-receipts-v2/source-partition-input-v2/` 对应两个文件，分别实际读取 SHA 并执行文件字节比较 `cmp`，两份均完全相同。相对于先前静态修复，helper 为格式化后的字节；source-use helper/test 身份在 format result 中保持不变。

新逻辑要求 store 目的既没有 external formal root，又必须正判来自有限已支持的 local/shared getter 或 alloca，只沿有限 GEP / addrspacecast / bitcast 回溯；因此 `GEP @external_global` 无法因空 roots 获准。新增参数化 negative 明确包含原 M1 触发，且要求 `Observer address payload` 错误。direct SSA 检查止于首个正判 private store，后续 observer memory effect 由独立绑定的 R087 isolation certificate 覆盖；这个准确合同已写在最终源码中，不把此 helper 当成传递 memory taint 分析。

已读取 `gcu-receipts-v2/runs/source-partition-v2/terminal.json`、完整两个 fixture stdout、`output/result.json`、actual partition result 及 rows 的状态/错误项：

- 实际 terminal 0，39.676662691 s，deadline 240 s。
- normal 与 -O 各 **42 passed / 0.14 s**；-O 仅预期 pytest assert warning。新增 global-GEP negative 属于该同版测试集合。
- 实际 109 checked，**97 partition / 33 distinct**；rows 中独立读到 97 个成功状态、12 个同样的旧 q05 certificate 拒绝，没有新 State checker 拒绝。v2 复用 v1 的实际 source admissions；本次没有重做 source、SDK、设备或数学。
- `source-format-v2` 实际 terminal 0 / 1.767362741 s，两遍 yapf / check-ast 返回 0；ruff 两遍返回 0、stdout 均为 no-files **Skipped**，不将其表述为实际 lint 覆盖。

**M1 已按最小源码修复 + 精确 matching test/actual 收据关闭。** 本有限 delta 未留已确认的未修实现缺陷。97 条结果仍是冻结 SDK 模型下的 partition；12 条旧历史拒绝、外层实际 SDK/loaded-object 身份组合及 `state_writer_qualified=false`、`SDK_ABI_binding_qualified=false`、native/pipeline/whole 未授资格均保持原范围。
