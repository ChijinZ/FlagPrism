# R103 GCU current96：既有 native family 的有限组合范围

**结论：已有原件足以组合原门所需的 GCU current96 有限 native 适用链；本次没有确认新的产品缺陷，也没有找到必须新增 SDK/ISA 审计或重跑矩阵的关系。** R098 已补齐本席 R091 的 required source/loop→实际规则→原 raw 连接；R089 的实际 reader/body/tuple/loop family 与 R090 的 SDK issue/addmm family，可以在原资源和编译对象身份条件下复用。这里接受的是所声明的 observer 子区域或 primitive issue；不是整个源码行的 exclusive cost、DMA completion、硬件 overlap 或 busy。

请求配置 GPT-6.1-Sol / xhigh；实际 resolved model/effort 未暴露，记 unknown。仅本地 Git、文本和 stdlib 读取/哈希，没有执行产品、import、测试、SDK、远端、设备、TP/UI，也没有阅读 peer 新报告。只写本报告。读取期间 observed candidate HEAD 为 `9c14353a85c5a84ae7f76a3af8c82ef131277670`；以下结论按原件摘要和受审 helper 字节固定，不按移动 HEAD 扩围。不是 whole-goal 签字，Ascend 本轮独立工作不在此范围。

## 1. 原要求及已补的分母

沿用本席 R094 `gcu-minimal-rule-interface-v1.md` §3–5 的停止点：检查实际 caller/body、selected begin/end、完整 record tuple、适用 loop，并接回原必需区域；不要求逐算术 opcode 重证 native 等价、所有 manifest site、全部 native CFG 或 source-exclusive 端点。R094 所说不能凭“同 SDK、形状相似”放行，是要求上述实际结构和身份条件，不能反向扩成每个纯算术 helper 都须一份新 ISA 证明。

直接读取 R098 README、小摘要及 full primary：

`artifacts/timeline/run-098/preflight/required-receipts-v5/runs/required-v5/output/required-join/`。

* `result.json` SHA `2436b3658aaeb95b12643195f544c0091f512bde580197800f4da070218de682`；`required-plan.json` SHA `01d43bf102300630876f4bcfbb2663058c987ce7f6722f2b6012a174012d79b6`。
* 33 actual LLVM 输入、32 binary、96 唯一 current capture，q01–q08 各12，96/96 structural/raw join。required plan 在读取结果/occurrence 前冻结；同源码阶段的互斥 split family 保留未执行成员，未挑 checker 恰好成功的 site。
* 实际 observed case/site bindings 255，90 distinct object/site：24 runtime iteration、48 literal iteration、183 no-enclosing-runtime-loop。9 个未观察的分支明确保留。不是拿 interval 计数代替 body/tuple/loop 检查。
* 原 raw 重新 decode，连接 capture/binary/LLVM/producer/source/observer、record pair、offset 和 ticks；默认 observer complete/nonempty，主数学 body 的原 required witness 与适用次数均保留。原 `native_schedule_qualified=false` 没有被改写，也不是缺陷或缺门的独立证据。

受测、正常安装和当前读取的 `gcu_llvm_regions.py` 均为 SHA `d4e8d11009a0dcf23af281052991267ebb2a6067c714e1df11c0569d46f0d5a0`。本席此前已核的 R098 normal-install-v3、503 wheel members、39+39 normal/-O 检查与 fresh33+96 原件可复用，不要求重复执行。

## 2. 必要组合只有三类

| 必需关系 | 现有可复用依据及范围 |
|---|---|
| 配对 fusion / 计算子区域及 loop | R089 matching ELF0 的实际 selected reader、source body、incoming begin/site/identity、end/record 和每轮回边；R098 typed 检查本对象真实路径、body refs、完整字段与 runtime/literal loop。当前 required 中的 FP32 vector broadcast/floordiv/imas/mac/cvt/select/sqrt 属于该计算 body 条件，不因算术名字不同逐个增加 native gate。只授实际选中子区域，不把某个 helper 或子表达式冒充完整 reduction/source cost。 |
| DMA primitive issue / shared end | R089 已核实际 FP32 slice/deslice issue→shared end→record，R090 读取原 fa9 库的 DTE descriptor/submit、wait/controller 与 memcpy 定义。R098 将 required source primitive 连到实际 typed SDK callee、对应参数路径、两端及 record tuple。1D/2D、source 实现分支依其实际调用和已审 SDK family 组合；这里不是重建搬运字节范围或授完成时间，因此不要求每个元素类型/维数另做一次 native 解释。 |
| contraction issue | R090 同 fa9 库实际 `tops_addmm_fp16_fp32` 定义与参数/返回关系；R098 主数学阶段限定实际 `gcu.matmul` 对应 call，不能用同源码行的 cast/add 替代。结合 actual compiler/SDK→fatbin/ELF 身份即可复用，不扩为一般矩阵 ISA 或 busy 认证。 |

原件身份没有靠品牌猜测：R088 `gcu-receipts-v2/runs/SDK-resources-v2/output/result.json` 保留 current cohort 的 compiler/toolkit、target/config、实际 compile/translate 与库资源。builtin SHA `fa9d850080258f7cfd3acbdccfdb3485007b9b87c3c5ed34ab187dacbb52944a`，compile SHA `1b7e13a7a2888e126a1022de6a129eec1404da5e0f0f0a0c2e702de784855e40`，profile API SHA `1a780215d7a63e34ce9c8cba6bfb126d222db726f5dca8802f3af0161fce81ec`。本次还直接检查其已回收 `profile-library.ll`：required 15 个确切 callee 无同名 definition 覆盖。R090 `pipeline-primitives.ll` SHA `f09d690912c6b0c357a140e01b2e24a2986fd46633ac6c3bba59f9ba330cd870` 与此前审阅相同。R089 实际 ELF0/LLIR/native 摘要按原报告复用，没有重编新对象。

产品 `gcu_timeline.py:322` 在实际 SDK-verified LLVM 字节 SHA 上生成 typed index 并运行同一 `analyze_regions`；`:398` 后续绑定实际 fatbin 中唯一 gcu300 ELF。`GcuExecutionStructure.cpp` 的真实 typed CFG/SSA/callee/type 引用与 `gcu_llvm_regions.py:394` 的 body-family 检查，不是仅按 source location 或 duration 认定。legacy current96 走 R098 的 sealed per-object typed ledger 和原 compiler/binary snapshot 绑定，不额外要求这些旧对象都有后来加入的 DI marker。

## 3. broadcast 疑问的校准与实际用户影响

本次曾定位 q07 第二阶段 `tops_broadcast_async_2_fp32`：对象24 site49/51（`24.regions.json` SHA `7c51f336f8bf59abb08b1835c5c8c12c146e651545372bf150785605c8be9ca4`），对象25 site53/55，对象26 site49/51，对象27/28 site53/55。它不在先前选根提取的单份定义文本中；这只说明那份 closure 不是所有 SDK helper 的语义手册，**不等于实际默认采集或 Perfetto 有错，也不等于该功能缺失**。

原要求在此处是广播 **issue 子区域** 的 actual caller→端点→record 关系。当前 typed 结果已给实际 call 位于该路径内，且 producer/core、同 SDK/resource 与 compiled object 链相连；可以按上表已有 DTE issue family 组合。若以后要额外声称该广播精确 D/S span、padding、completion 或独立引擎时长，才需另读对应定义；这些不是本次新增的必达门。本次停止追加 extraction/native 读取。对普通用户，未发现新的采集失败、错误 interval/track/单位、丢记录或离线重导不一致的具体影响；不应以这一更细语义疑问宣告工具不可用。

## 4. 最短收尾清单及边界

若需要一个便于审计的最终组合索引，只需从现有结果派生一次：`current capture/raw SHA → object 的 before/manifest/actual LLVM/binary SHA → required stage/source family → checked body/path/tuple/loop + raw witness → 上表 family rule 与同 SDK/resource/native 审阅引用`。使用 R098 原计划与原96分母，不另筛 site，不重跑 helper/数学/SDK/TP/UI。它是已有事实的登记与作用域声明，不是另建证明器，也不能只把宽泛 false 翻成 true。

**Confirmed blocker/major/minor：本有限范围无新增。必要 verification gap：没有再识别出需要产品修复或新实验的具体缺口。** 更细的 broadcast descriptor 语义属于可选扩展，不列为 whole 阻断。本组合仅关闭 GCU 原 C1/V4 所需的已审 native family 适用链；不升任何 busy/completion/source-exclusive/general-ISA 权利，不重开已闭 State、预算、时钟、SQL/UI、BK32/BK64 pipeline，亦不裁定 Ascend 或 whole-goal 的最终状态。
