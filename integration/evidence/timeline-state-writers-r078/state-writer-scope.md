# R078 State writer：有限合同范围判定

**结论：V1 不要求把已绑定实际编译对象的 PTX 地址/谓词，再逐份翻译为 SASS 重新证明。** 对本次 NVIDIA 原登记输入，若保留的实际 PTX 已明确物理 thread/program、State 指针、store 宽度和实际写入谓词，且与实际执行 cubin 的编译身份链核同，计划中的有限整数 address/predicate 检查加既有数学/host-once 收据足以满足这一项。不能只凭高层 `tl.store` 索引或数值恰好正确，也不需要增加任意 ISA 证明器或重跑数学。

## 原文与判定依据

- 根 `timeline_goal_prompt.md:111` 要求“合法 side-effect oracle”；`:73–75` 要求保源、实际编译对象/驱动输入和安装身份链，未规定 State 检查必须止于 SASS。
- `Profiler/docs/timeline_testing.md:100–103` 的适用范围是每个 eligible 组合的 ordinary 与 profile。准确要求为：“oracle 必须有合法唯一写者或独立不重叠写入，先证明其实际 lowering；不能把不合法非原子多写者 State 当 replay oracle。”这是 State oracle 的门。
- 本席原 V1（`run-075/review/delivery-whole-v1.md:41–49`）缺的是原 kernel 的 State store，最小项为实际地址索引、尾部 mask、物理 lane/subblock/writer 选择及 scalar store 合法化，允许复用同一通用 lowering 规则，绑定原对象/配置；没有另设 SASS 全量解释门。采集器 logger writer 不能替代它。
- design `:68`、`:95` 明确不要求任意机器码形式化证明；testing `:123` / design `:170` 的实际 IR/ISA 顺序、timer 边界与 schedule 检查是其它语义门，不能据此给本项额外添加 SASS 重解释要求。

这里接受 PTX，是因为待证明的是其中已经显式决定的 thread/address/predicate 存储语义，并依赖匹配目标编译器正常保持该语义；不是把 PTX 称作最终机器码。若只有重新生成但未与原 cubin 绑定的 PTX，或关键 State 写入仍藏在未解释的 helper/opaque 操作里，则相应局部仍未证；应补最短缺失链，不自动扩大为全 SASS 审计。

## 最小完成范围

1. 对原登记实际使用的 ordinary/profile 对象及 runtime-K 对照，绑定 source/State 形参、实际 PTX/LLIR、cubin、编译目标/配置和原数学/host-once 收据。相同对象可复用检查结果，仍绑定各调用的实际 grid、参数与 State extent；不新增数学或配置。
2. 找全会写 State 的实际 store 及其控制路径，区分原 State 与 logger scratch。按实际整数位宽、向量 store 字节宽度和路径/predicate，在登记的合法 thread/program 范围核：每个应更新的逻辑 State 元素有且仅有一个动态写者（或独立不重叠写入），尾部/guard 无写。不能把 `v4` 当一个字节，也不能把归约后逻辑 scalar 直接当唯一物理 writer。只需 State 有关 cone，不重证浮点数学或所有指令顺序。
3. 与原数值、State 正确增量、输入/tail/host-once 结果连接，保逐对象覆盖/未证项。没有具体对象变化或实际不合法 writer 时，不需要设备重采、SQL/UI 或安装重做。

## 已读 R078 的状态，尚不授完成

三家 `preflight/*inventory-poll-v1.json` 均 terminal0，实际结果明确为 `original_ordinary_math_and_compiler_objects_bound_not_writer_qualified`；各32份 ordinary 报告（24 primary +8 runtime-K），不是 profile 全覆盖或 writer 检查已通过。已读 inventory runner 的 eligibility、baseline、数学报告及各 asm SHA 核对逻辑。

`nvidia-state-ptx-v1.json` 目前只有 q01/q03/q05 三个 s0/c0 摘录。q03 实际 `.reqntid 128`，State 参数路径是 `q03_param_3` → `%rd12 + ctaid.x*4`，State `st.global.b32` 受 `%p6 = (tid.x &31 ==0) AND (tid.x &127 <32)` 控制，因此该摘录对应128线程中 thread0 唯一写者；这支持采用上述 PTX 方法，尚不代表其它配置或 profile 对象已核完。当前缺的是计划中全登记范围的有限检查与绑定收据，不能把 inventory terminal0 当 V1 terminal0。

GCU DMA lowering、Ascend LLVM/npubin 链本次不作资格判定，也不预先要求它们采用 NVIDIA ISA 检查。whole goal 不在本次范围。

本席仅 Git/stdlib 读文件，未 import 产品、运行测试/SDK/设备或读 peer 报告。请求配置沿用 GPT-6.1-Sol/xhigh；实际 resolved unknown。原文 SHA256：goal `a67839fab0143ca27f99a3eb463a3eae8510d67980c91aaf5bda8e03bd857f57`；testing `d112210633fc659fdf5a6772254cb422e420cd16266b685662077725eba49993`；design `54eded77e2d5fe8d7b59702393db02ba36fe2dd77d41f40ff2bde9319462937f`。本次 PTX 摘录 SHA `a80e82b71dd70ee73adda367a23c4942ea27412424ce6058ecad53e2554716da`。
