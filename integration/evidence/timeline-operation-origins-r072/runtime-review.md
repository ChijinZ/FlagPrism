# R072 independent limited runtime/offline review

**后续限定关闭：M1/P1已在 `f4200142b5c68352c74c853fdc71b2da123e092c` 的静态复核与新installed定向验收中关闭，见文末追加记录。下文原freeze的问题、未冻结修复及当时pending状态保留为历史，不再代表当前未完成项。** 本结论仍不授whole goal或来源成本/参与/busy等额外资格。

原 freeze：`5dca71cd80dda78afafebb52b8c965ac9368b377`，相对 `38e2ffa`。原 `timeline_nvidia_operation_origins.py` SHA256 为 `96aad14ec29ad96ad72bded7fbb2600b94f747d87edaa87fd139892f10c7ba5e`，与实际安装输入归档一致。起初额外未提交的是离线 reader fixtures；它们后来随 `1068cb4` 提交，不改变原产品 freeze。另按 root 明确要求实际读了其随后针对本审阅发现所作的两个类型检查和六个fixture，见下文候选修复；不把未冻结修复当成已安装。

结论：**原 freeze 有一项 confirmed major（M1，可选sidecar错误类型逃逸），候选修复静态方向正确，尚待新installed终态。** 未发现本 delta 的具体错误授予 source-exclusive cost、participation、busy 或跨域时钟资格。另记录一项在新调用复用的 helper 中发现的继承性 minor，和本轮新缺陷分开。此报告不作 whole-goal 签字。

本次实际只读源、diff、收据和归档；不 import/运行产品、checker、测试或 SDK，不连接设备/服务器，不读取peer意见；唯一写入为本报告。

## Confirmed major

**M1 — 可选operation-origin sidecar的合法非object JSON会中断无关离线导出。**

- 位置（原freeze）：`timeline_nvidia_operation_origins.py:177`–`:188`、`:189`–`:195`、`:206`；传播路径为 `load_native_boundary_report` → `timeline_nvidia_offline.control_evidence:89` → counter export准备（`:201`）。
- 触发：仅把owned副本中的 `machine/<binary>/operation-origins.json` 改成合法JSON `[]`、`null`或字符串，保留有效raw、cubin/PTX、counter map和source output。`json.loads`成功，但后续 `saved.get` 抛 `AttributeError`；该函数catch不包含它。`counter`也在未确认是dict时直接调用`.get`。
- 证据：原源直接可确认异常路径。新3类reader篡改fixture覆盖hash错/缺文件/不信缓存成功状态，但没有覆盖非object顶层。下游boundary和counter路径也不隔离这个AttributeError；因此这不是“operation_origins=unverified”的受控拒绝。未运行reproducer。
- 后果：本应可选的来源诊断损坏可以阻断有效旧/新raw的counter/dependency离线派生；raw本身仍保留。没有证据表明它会错误授予来源或时间权限。
- 最小验证：复用现有 `p01_nvidia_operation_origins.py` 的owned临时目录fixture，仅写入上述3种JSON形状，调用loader应返回 `unverified_native_operation_origins`而不抛异常；对仅operation-origin sidecar损坏的副本，已有counter export路径应仍能继续。若counter map本身损坏，整体counter证据仍应按原规则拒绝，不能把局部loader的降级误称全counter map有效。

**候选修复静态复核：** root随后在两次`json.loads`后、任何`.get`前增加 `_need(type(saved) is dict, ...)` 与 `_need(type(counter) is dict, ...)`。这使错误类型通过已有ValueError分支返回unverified，且正常来源重算/身份匹配不变。新增fixture对两个sidecar各注入`[]`/`null`/string，共6项，未用catch吞掉异常冒充通过；逐sidecar恢复原字节后继续检查缺文件。已实际读修改，静态上关闭上述M1路径。该次未格式化工作区源SHA为 `b955013057a1bd26efe529fb01f40215a5a33ba295fc404fda3c5a532ffa05e2`、测试SHA为 `c157b5c2cb4e345ef993054185cfac5cac184f397a66054254479b650f49583f`。报告时新wheel/normal/-O终态尚未提供，故不把M1记为installed closed；不需要重编native或重跑GPU数学。

## Confirmed inherited minor（非R072新增，不作为本delta新增阻塞）

**P1 — `_run_tool`在进入cleanup块前的登记失败可遗留child。**

- 位置：`timeline_nvidia_machine.py:613`–`:629`；`try/finally`从`:629`以后才覆盖等待与超时清理。此结构在R072之前已存在，新source-lines阶段复用它。
- 触发：Popen成功后，`/proc` owner读取或首次`commands.json`写入发生OSError；例如只对这次receipt写入注入失败。异常绕过finally，未执行wait/stop。新可选阶段随后可将错误转为unverified，但child可能仍运行，未受该函数剩余deadline监督。
- 后果：正常成功路径不受影响；故障路径不能严格声称有界owned child必被reap。不是设备kernel复用或来源误授缺陷。
- 最小验证：CPU fixture用一个睡眠child，令`commands.json`首次写失败，检查登记PID已终止/reaped；fixture自身必须最终清理该PID。最小修复范围是Popen之后立刻进入cleanup覆盖，不需ISA证明或设备矩阵。本次没有执行此fixture。

## 其余delta语义与预算

- native producer仅在manifest保留原用户导航后，给选中的LLVM member分配独立synthetic location；在recorder插入/ordinal promotion后才设置原member location。无debug scope明确unavailable；origin ID上限65535，超限显式失败。没有改raw ABI、timer carrier、发布、容量、pool或设备同步路径。新工具实际重建，原LLVM core/runtime复用。
- `derive_operation_origins`要求plan marker version严格为整数1、binary一致、source-lines bytes不超过32 MiB、每个assigned marker身份/column合法且ID唯一。它用同一object-bound JSON逐条对照source版SASS的opcode/predicate/operands和function范围，再解释来源注释；未知ID拒绝，line0计unknown，无location成员留missing，不按最近PC/时钟猜测来源。
- matrix-member规则只处理既有verified matrix issue bracket与有限LLVM MMA家族；每个member恰有一个HMMA.16816.F32，function一致、PC互异，集合恰等于原bounded issues。不能由“某origin附近有HMMA”直接授一对一身份。普通origin允许一对多并保留missing。
- 新source-lines采集位于已写好的counter map/status之后，其常规工具/parse/IO错误只写 `status.operation_origins=unverified`。复用已有总export deadline和单次至多20秒、stdout+stderr合计32 MiB的轮询上限；没有扩大raw/session预算。正常timeout/输出超限在既有finally中停止工具；P1是登记阶段的独立继承性例外。
- offline loader仅用安全相对bundle路径和有界artifact读取；检查保存的binary/cubin/json/source SHA及匹配counter sidecar的disassembler SHA。随后用保留source/json/plan重新推导origin与matrix member，忽略保存的origins、mapped status和qualification字段。缺文件/hash错/旧plan无marker均返回unverified；原计时/依赖消费者未改为依赖origin成功。M1是该可选隔离中的具体类型缺口。
- 所有来源报告仍保持source region、source cost、participation、hardware busy为false；matrix结果也不授source cost或participation。LLVM debug来源身份不等于source-exclusive持续时间、动态参与、物理完成或普通pipeline保持。

## 实际证据，分别计范围

1. `native-install-poll-v5.json`（其terminal/result是JSON字符串，已解析读取）：controller terminal/0，正常standalone native build、wheel组装、640成员安装、matching import成功；wheel SHA `0dacd4ea6d6adf0976b3457fc92637a68b32e015fc98cc6345a5f85fbcbd1d53`。旧matrix规则normal/-O、既有实际retained边界、公开reexport、origin CLI与fixture mapping normal/-O各0。公开旧原件重导仍有8counter+2dependency，不能因legacy origin unavailable取消这些原有资格。
2. `real-and-reader-poll-v1.json`：`real-origins-v3` terminal/0，共8个capture结果。C1两capture复用此前已成功的R072 C1采集，无额外数学重放；C1为7/8 mapped，C2为40/45，default为50/53，missing均保留。标作`sparse`的budget8结果与default同binary/53 origins，不能当成真正max_sites1证据。原数学/输入/尾部/once检查由既有workload脚本执行，本轮未量性能。
3. 同文件`origin-reader-v1` terminal/0：在matching installed包上，用额外owned-copy fixtures检查normal/-O离线重算、不信缓存资格、错source/tool hash和缺source文件。它没有覆盖原M1的错误JSON类型，也不能支持候选修复已安装。
4. `real-sparse-origins-poll-v1.json`是两个连续JSON对象；已分别读取terminal/0与result。脚本明确检查max_sites==1，两capture各33 origins、31 mapped、missing[31,33]，四个matrix member位置均通过有限匹配；performance_measured=false。它关闭本次实际sparse来源采集范围，不把missing或参与/成本权限提升。

## Verification gaps 与可交付范围

- 原5dca freeze存在M1，不能称可选来源损坏已经完全隔离。候选类型修复已静态通过，待既定matching新wheel和6类wrong-type fixture的normal/-O成功终态即可补installed closure；无需扩大矩阵、重跑GPU或新增通用ISA证明器。
- optional source-tool失败/输出预算等新分支没有本轮专用故障注入收据；静态预算路径已读，P1明确列为继承性问题，不把正常capture成功当成该故障已实测。
- 本报告只授操作来源与有限matrix member身份的工程结论。missing origins、source-exclusive cost、参与、硬件busy、ordinary pipeline等仍独立未授；不要求为了本次来源身份delta任意追加ISA证明或旧矩阵。

已读新增模块、machine/boundaries delta、native producer delta、当前离线fixture、相关tool生命周期/read_artifact/bound-function/离线counter消费者；已读上述三类收据与原安装归档、实际runner。未读peer报告，未执行测试或访问设备，未审其它后端与全goal。

## 追加：f420014有限修复及installed closure

本追加只复核M1/P1修复，不重开原验收。实际读了freeze `f4200142b5c68352c74c853fdc71b2da123e092c` 的两处产品修改、三child故障fixture、六种sidecar错误类型fixture，以及 `preflight/native-install-poll-v7.json` 与其v2安装输入/runner；未运行测试或连接设备。工作区当时干净。v2安装归档中的machine、origins、child测试SHA与此freeze逐项一致。

- **M1关闭：** 两sidecar在任何`.get`前严格要求dict，错误类型转为原有ValueError→`unverified_native_operation_origins`。matching新wheel以真实sparse retained timeline运行reader normal/-O，覆盖两个sidecar各`[]`/null/string的6种组合及原hash/缺文件/不信缓存检查，步骤均0。更直接的公开CLI验证在owned真实sparse副本只将可选`operation-origins.json`改成`[]`，仍产生8 counter+2 dependency；control中的origin明确unverified，`application_replayed=False`。这验证了原M1的实际导出隔离，而非只检查私有函数返回值。
- **P1关闭：** `/proc`登记与首次receipt写入已进入try/finally。发现后另补核了持续`/proc`失败分支：`_stop_worker`被嵌套finally包围，若它找不到child直接返回或自身抛错，仍对当前Popen拥有且存活的直接child执行kill，并`wait(timeout=10)`回收，去除了无超时wait。三类实际sleep-child CPU fault包括一次/proc失败、持续/proc失败、首次commands写失败；每项检查10秒内返回、returncode非None及`os.waitpid`确认已reap，fixture自身finally防泄漏。normal与-O各3项的步骤均0；真实nvdisasm `--version`成功路径另有步骤0。未把所有可能的OS异常扩大成已验证范围。
- **实际新安装：** `native-install-poll-v7.json` terminal/0，source f420014，640成员，15步骤全部0；wheel SHA `e112f2ecee6fc9557fbda7db71343dae132af8ee9a8722eda49bc2197213c7e7`。runner SHA `5df73e971d45882998c9bc535e4e8e8d9149629bb2943dfe80a698979273ef4c` 与terminal一致。native/core/recorder保持字节核同复用，matching import成功；没有新native rebuild或GPU数学重跑。

独立核对补充SQL收据：`new-traces-sql-poll-v5.json`首行payload为terminal/0；结论依据下载的完整 `preflight/receipts-v1/new-traces-sql-v3/output/counter/result.json` 与 `dependency/result.json`，两文件SHA分别与72/8摘要登记一致（`92ab3e96…`、`0c4597a7…`）。共80项真实TP checks，每份263项完整stats，无正error/data_loss；dependency合计4384 flows。这是既有新采集trace的实际protobuf/SQL检查，没有应用重放、UI或额外source/clock/busy资格，也不是本次Python修复后的新GPU数学。

**当前有限结论：M1及P1均已关闭；本修复范围未见新增具体缺陷或待完成的installed检查。** 原missing origins及source-exclusive cost、参与、busy、ordinary pipeline、whole goal等独立资格保持原先未授范围。
