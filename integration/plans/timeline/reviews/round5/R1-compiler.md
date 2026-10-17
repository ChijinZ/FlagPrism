# R1：编译边界、源映射与适配可行性独立评审

## 结论

**有条件认可目标设计，可按 A→B→C→D 分段实施；不授予完整设备可行性或交付通过。** 未发现足以确认的设计 blocker、major 或 minor。条件是各后端在已有 P01/P03/P05/P07/P10 门中闭合最终机器边界、真实时间尺度、发布/launch ABI 和动态复用关系；任何一项闭合不了，必须保留该后端未通过及具体 SDK/环境障碍，不能靠扩大 source 标注或调整展示代替。三后端全部达成的工程风险较高，目前文档没有为 GCU/Ascend 的完整异步可观测路径提供确定性保证，但也没有充分依据判定其不可能。

这是目标设计评审，不是当前代码通过声明。当前 NVIDIA raw producer 仍未认证，其他后端 producer 尚未完成，均在 runtime:3–20、design:284 和 goal:67 正确披露，不能据此判设计错误。

## 阅读与约束

完整阅读 design 364 行、testing 226 行、runtime 92 行、events 55 行、goal 156 行。五个文件 SHA256 与 `round5/INPUT.json` 全部一致，输入 source_head 为 `f5731a08dbeebff633e416233b5faf857f1fc7da`。本报告位置之外未写文件；未读取其他 reviewer 或历史评审报告，未实现、测试、import、SSH、访问设备或论文。

为核对实际接入可能性，另只读抽查 `AutomaticScopes.cpp`、`ProtonToProtonGPUPass.cpp`、`PatternProtonGPUOpToLLVM.cpp`、NVIDIA `TargetInfo.cpp`、`hooks/instrumentation.py`、`hooks/timeline.py` 及 NVIDIA 两份 compiler/launcher patch；对 Ascend compiler 仅作相关接口文字检索。未完整审计运行时、decoder、各 SDK/编译器或最终对象；源码抽查不能替代设备证据。本报告中的 design/testing/runtime/events/goal 行号均指上述冻结输入。

## 确认的设计缺陷

- Blocker：无确认项。
- Major：无确认项。
- Minor：无确认项。

理由并非实现容易，而是关键难点已纳入可拒绝、可保留 partial、不可降低完整门槛的合同，并有对应验收。没有把尚待完成的实现任务重新包装成设计缺陷。

## 必须在实际实现与设备阶段核验的风险

### V1：LLVM 约束尚不能承担最终区域边界证明（高风险）

**位置与具体张力：** design:68、202、314–318 要求最终区域顺序，runtime:29–44 明确当前策略止于 LLVM。源码 `ProtonToProtonGPUPass.cpp:106–132` 将 begin counter 接入 operand forwarding，并让 end counter 消费结果；NVIDIA `TargetInfo.cpp:49–79` 的计时依赖使用 LLVM inline-asm 输入及 PTX 注释，另有 memory clobber。因而现有链可以约束 LLVM，但注释形式的依赖不能直接作为 PTXAS 后的实际数据依赖。对于 store、无普通 SSA 结果的异步操作、token/descriptor 与控制区，尤其不能靠普通算术 operand/result 模板推断完成或完整覆盖。这与文档并不矛盾：runtime 已正确标 unverified。

**最小修订/落地：** 无需降低或重写目标合同。首份接入清单按边界类型列出“约束到哪层、最终对象如何定位、哪些原指令必须落在 anchors 内、哪些操作仅表示 issue”；若机器顺序失败，修通用 lowering 或选更粗但真实的合法区域，不能加完成 barrier。未闭合 site 保持无源耗时资格。

**验收：** 复用 testing:142、159 与 214：真实依赖算术 loop、load/compute/store、原 wait 的最终对象逐项对照，证明 loop 内 anchors 未外提、实际指令未越声明边界；仅证明计时 PC 存在或 duration 为正不足。机器对象不满足者必须拒绝对应源区域归属，不让合法 clock proof 补齐边界资格。

### V2：M:N 设计正确，但 provenance 必须穿过真正优化链（高风险）

**位置与具体张力：** design:146、202、210、298 明确 fused/split/eliminated/unknown 及导航与成本归属分离；events:11、23–24 同样避免复制 duration。实际自动 scope 在 `automatic-scopes.patch:3–18` 所接 TTGPUIR 阶段运行，`AutomaticScopes.cpp:299–341` 保存候选 operation/location，389–408 插入 markers；这些只是可用接入点，单靠该 inventory 不能证明后续 LLVM/PTXAS 的全部 M:N 关系。

**最小修订/落地：** 无必需文档修订。保留 source origin 集合与实际执行 anchors 的独立身份，在晚期 manifest 中将无法证明的关系显式记 unknown，不能从最后残留的一个 location 恢复丢失 origin。若 fused 后只剩一个真实执行区间，不得重复归属凑“两区域”。

**验收：** 复用 P03 和 testing:159、209、214。在真实发生的融合、拆分、循环变换样本中核 source snapshot→实际 anchors→binary；额外用缺 origin/错 snapshot/单区间多 origin 负例检查公共 validator。无需强迫某设备产生本来没有的优化。

### V3：三后端 timer/logger/launch 是不同的实际 ABI，不能把公共模型当作生产者（高风险）

**位置与具体张力：** design:86–88、158、212、263–276、306–312 已区分物理布局、紧凑 slot、初始化、完成与 cache 身份。实际 NVIDIA `preallocation-admission.patch:15–26` 在 scratch allocation 前传 actual stream，`hooks/timeline.py:45–88` 核 scratch/grid/stream 并交给 owner，说明所提 prepare-launch 边界有真实调用点；这并不证明 Ascend/GCU 有等价已可用接口，更不证明其发布可见性。Ascend census v3 与 timeline 协议不可直接继承，文档已识别。

**最小修订/落地：** 无必需设计修订。分别冻结真实隐藏参数顺序、布局公式、writer 身份、发布/提交条件和实际 loader/launcher 版本；SDK 中缺调用点时使用合同允许的通用 patch，不能在 Python 侧假定成功。logger 布局、timer 位宽与 decoder 必须共同版本化。

**验收：** 复用 P05/P10、testing:160–162、193–194、213：实际两 program/未选 program、变 grid、header/padding/canary、错误旧 ABI 早拒绝及恢复；真实设备核 commit 可见性、owner 安全完成。NVIDIA 实际 ABI 证据不能代替其他设备。

### V4：异步组可观测，不自动代表物理 buffer 复用可证明（高风险）

**位置与具体张力：** design:112、166–168、274 正确允许逻辑组及 unknown buffer；完整资格由 testing:70、146、196 明确要求每后端两轮真实 buffer/flag 复用及代际证据。当前编译层可能只保留 submit/commit/wait 及逻辑序号，不能因 group 序号递增而推导物理 buffer generation。三后端至少一个满足完整要求的普通合法样本仍是实际可行性的关键未知。

**最小修订/落地：** 无需放宽 P07。开发早期对候选普通编译对象登记可取得的地址/slot/flag 来源、动态控制路径与 reset/复用规则；不能证明的事实保 unknown。优先寻找已有合法、能够保留该来源的真实调度；必须改机制时改通用 lowering，不按 kernel 名适配。

**验收：** 复用 P01/P07 与 testing:195–196：首轮、steady state、drain 的真实复用，同地址不同 generation、部分 wait、丢 commit 后不串代；opaque/隐藏状态变更使关联降级。group-only 通过不算完整资格。该门确实失败应报告后端未完成，不能把“未查到路径”提前说成硬件不可能。

### V5：普通算子单次执行与早期资格必须按正确阶段解释（中风险）

**位置与具体张力：** design:46 要求应用仅执行请求次数；design:174 的 ordinary eligibility 与 testing:39–44 的 baseline/freeze 是开发和资格程序。若实现把这些验收预跑误植入每次公开 capture，便会破坏 host-once 和 side effect。另一方面，单次 JIT 仍须在 launch 前完成静态资格、actual grid admission 与所有可预知不相容检查，不能为避免预跑省略预检。

**最小修订/落地：** 无确认冲突。实现清单明确区分测试 harness 的 ordinary baseline 与公开 capture 的 compile-time/prelaunch 检查；运行时未知 clock 资格允许保 raw/partial，不能隐式重跑补证。

**验收：** 复用 E01/E02/E07、testing:50–57、162 与 design:300：实际副作用恰一次、cold/warm 各是明确独立捕获、改 actual grid 不串 selection，缺 proof/导出失败不再执行应用。

## 后续芯片复用判断与可选建议

设计的可复用边界合理：design:148–158、286–312 将 compiler、transport/decoder、clock、mechanism 分成可组合事实生产者；公共层统一身份、完整性、时间转换、依赖与导出。允许新公共语义显式升级，且不要求第四芯片证明，避免用“零公共修改”倒逼抹掉架构差异。实际适配成本仍包含晚期 pass、隐藏 launch ABI、timer/发布及机制规则，design:242 已如实承认。**本评审只支持该边界可实施，不支持未来新芯片只需配置或已有工期保证。**

可选建议 O1：design:318、331 的接入清单可用一张固定表记录每个实际 site 类别的“语义、约束层、final-object 证据、clock、mapper、资格结果”，直接引用已有 raw/proof，不新增重复工程日志。具体风险是分散清单容易把 getter 或 marker 的证据误扩到源区域边界；最小改变仅为证据索引模板。验收仍是 testing:214 的两个 site/observer 资格隔离，不需要增加数学或设备矩阵。

若按这些已规定的门保留失败，方案可以推进；若要求现在无条件保证三种 SDK 均能闭合最终机器区域、共同 epoch 与物理复用来源，现有只读材料不足以给出该保证。
