# r10 独立设计评审：编译边界与后续芯片适配

2026-10-18。评审类型：设计合理性与条件可行性，兼顾整体，重点为 compiler。调度请求 GPT-6.1-Sol / xhigh；回执未提供可独立核验的 resolved 身份。

完整阅读两份主文档，并只读核对 runtime/events 和实际编译源码。未读其他本轮 reviewer 报告或旧 review 结论，未访问 SSH，未 import 产品、运行产品测试或编译。未跟踪的 `Profiler/llvm/AscendTimeline.h` 不视作已构建能力；本报告为唯一写入文件。

输入：HEAD `8e91da356946263055dfc8ffeae15ff365c78d1c` 的工作区版本；最终核对 §0:7 当前“先推进三个实际后端的功能，随真实调用形成抽取公共实现”。摘要：

- design：`45d9c02808115f2aa71ec7670662a13c3e03e73ecf4c9843bccafb2612f81745`
- testing：`fa300abc858a268e0f8fbd8ed1cdffa18bb3fdb6caede72ec0a903028af8df87`

## 结论

**设计合理、条件可行；confirmed P0/P1 为 0，已证实硬阻碍为 0。** 允许按 §0 继续实施，不授予任何设备或实现门通过。

五部件分工保留了编译、布局、时钟和机制差异；公共 owner/身份/验证/时间算术/导出能减少重复实现。编译静态计划与 launch 实际 grid 分开绑定，M:N 源映射不复制 duration，源码导航/区域边界/硬件完成分开授资格，这些均可实施。§0 和 §8.12–§8.14 给出了足够具体的开工入口，不要求先搭插件平台、统一 ISA、统一物理 ABI 或第四设备。

对未来芯片只能支持“公共链可复用、差异有明确替换位置”，不能保证新编译链适配便宜。同工具链新型号可能复用 hook，但仍需核实际优化、getter、发布和机制条件；全新工具链可能需要新 pass、隐藏参数和机器对象检查。设计 292、336–348、393、419、447–457 行准确保留了这些成本，没有承诺一个 adapter 或配置即可移植。

## 实际源码对设计的支撑与限制

| 路径 | 只读核对结果 | 设计判断 |
| --- | --- | --- |
| NVIDIA | `integration/patches/nvidia/automatic-scopes.patch:7`、`Profiler/python/flagtree_profiler/hooks/instrumentation.py:402`/`:415` 在 `ttgpuir_complete` 自动接入；`Profiler/Dialect/lib/ProtonToProtonGPU/AutomaticScopes.cpp:254`–`:290` 提取实际 cp.async 角色，`:389`–`:408` 放记录 | 有具体接入点，但 LLVM/PTXAS 尚会变换；早期 inventory 不能直接授最终源边界 |
| NVIDIA boundary | `Profiler/Dialect/lib/ProtonToProtonGPU/ProtonToProtonGPUPass.cpp:106`–`:132` 使用真实 operands/results；`Profiler/Dialect/lib/ProtonGPUToLLVM/ProtonNvidiaGPUToLLVM/TargetInfo.cpp:53`–`:65` 限定 LLVM 输入/clobber 范围，`:79`–`:139` 实现 helper/forwarding | 可实施候选；源码没有证明任意算术/异步完成均被机器边界包住。设计 409、491 行正确要求最终对象，并未强迫其它后端继承该 ABI |
| GCU | `Debugger/python/flagtree_debugger/compiler.py:548`–`:588` 在 TTIR 选点、插桩并继续 CSE/canonicalizer；`Debugger/lib/Instrumentation/Passes.cpp:3853`–`:3890` 调用真实 SDK timer；`integration/patches/enflame/flagtree-source.patch:42`–`:45` 保位置 | 位置和 timer 路径可复用，纯算术是否越界仍待证；设计 261、439、491 行未把早期来源当晚期边界 |
| Ascend | `Profiler/llvm/AscendLateObserver.cpp:1002` 明写 pre-scalar-optimization，`:1033`–`:1035` 注册 pipeline start；`:578`–`:590` 包原 wait/set，`:626`–`:633` 为 checkpoint | observer 名称不等于最终优化之后。设计 50、177、261、302 行准确保留新 producer、区间、发布与动态关联缺口，未继承 census 通过 |

ordinary 流水要求也可执行：设计 217、409、439 行及测试 89、266 行要求保关键依赖、机制和合法 overlap 机会，明确不要求对象逐字节相同。它允许调整通用插桩位置/密度，也区分 observer elapsed 与异步 engine busy；不是要求零扰动或用完成 barrier 保时间线。是否真的保留仍须设备/对象证据。

## Confirmed P0/P1 与硬阻碍

无 confirmed P0/P1。没有发现必须修改公共分层才能继续的矛盾，没有“通用机器码证明器”“所有芯片必须提供 CUDA 句柄”“ordinary 与插桩指令完全相同”等不可执行要求。

无已证实硬阻碍。本轮没有运行设备/SDK，因此不能声称任何目标没有插桩点、时间尺度或可观测异步。当前功能未实现不等于设计错误，尚未取证不等于硬件不可能。条件仍是各后端闭合最终边界、发布/回收、本地尺度、真实两代复用及所需时钟比较；最小输入实证无法闭合时，按设计 241、380、505 行报告具体环境/SDK 限制，不能扩大矩阵或降级门槛。

## 执行落点待定：不阻塞开工、不新增门槛

### E1：首个可通过的边界通用模式

- **位置**：设计 117、195、251、491、505；测试 160、177、246–247、307–308。
- **触发**：首次把 source-linked counter bracket 晋升为源区域 elapsed，或第二工具链接入 receipt/schema。
- **缺口性质**：文档已有收据结构；实际支持哪种控制/优化模式仍需从首条真实链收敛。完整 marker-PC 映射不能代替这个选择。这是实施待定项，不是设计漏项。
- **最小修订/动作**：无需新文档章节。在现有接入清单内，用第一份 runtime-K 对象明确一种通用模式的检查输入、判定和未覆盖形态；分别保 source origin、site、最终机器范围。陌生形态未证，修通用处理，不按算子名/shape 特判。
- **验证**：复用 P03 runtime-K/load-compute-store 及最终对象，仅检查实际出现的 fusion/split/消除；缺字段/错范围用已有合同负例。不新增 ISA 证明器或独立数学。

### E2：ordinary 关键关系的具体基线

- **位置**：设计 43–48、217、439、505；测试 14、84–89、164、266。
- **触发**：首个真实 ordinary 异步样本进入 C，或 C2 改调度变体。
- **缺口性质**：正确的“关键依赖/允许 in-flight/消费前等待”判据仍须落到实际样本；调度变化不能自动判失败，无新 barrier 也不能自动判通过。
- **最小修订/动作**：无需改门槛。直接在已有 ordinary baseline 中列 operation/group 集合、wait 覆盖、消费约束、buffer/flag 分代和允许跨 compute 的提交关系。不要求寄存器、指令数或展开逐字节相同。
- **验证**：复用测试 266 的 ordinary/稀疏/默认对象与动态记录；C2 每个变体各自对照。若测量增加完成依赖或消除需解释的合法 overlap 机会，修通用插桩/选择并复核该样本。静态关系保留不升级成测得硬件重叠。

## 可选建议 O1：文档去重，避免索引变成额外矩阵

- **位置**：设计 183–235、265–292、311–328、344–393、399–441、459–507；测试 158–171、209–238、246–251、261–270、278–309。
- **触发**：真实公共概念改版本，或维护者准备按每小节建独立接口/测试清单。
- **问题**：五部件、独立资格、最小链、公共层不解析厂商 ISA 重复较多，增加维护漂移风险。§0 已改善导航，故不阻塞实施。
- **最小修订**：后续保 §0 为入口，§8.12–§8.14 为具体合同，旧重复段逐步改准确引用，保独有要求。测试用一份 P/E/C 注册表复用原件，不为 §8.1–§8.9 各跑全矩阵；本轮无需为此大改文档。
- **验证**：只核交叉引用与唯一要求；两区间、真实两代复用、最终对象、三后端和最终代码审阅原门均保留。无需新产品测试。

可靠留存、离线重导、版本化派生与有界锁有实际需求和实现路径；不必扩成分布式服务或兼容全排列平台。设计 503 行仅覆盖实际依赖边、测试多处明确不增独立数学，是合理范围控制。

本报告不授予 P01、设备、SQL/UI、源码耗时、epoch、动态复用或安装资格；实现完成后仍须额外三个独立最终代码 reviewer。
