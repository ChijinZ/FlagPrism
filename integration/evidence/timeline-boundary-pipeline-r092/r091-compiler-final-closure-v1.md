# R091 compiler 最终闭合审阅

结论：冻结版本已形成真实的三后端自动采集、来源导航、内部 observer 时间、动态机制与离线导出链，很多原剩余已由实际材料关闭。本席本轮没有新增 confirmed blocker / major / minor。但**仍不能给原完整 goal 完成票**：主要剩余是 GCU/Ascend 有限最终 source/loop 规则的自动接入及其原资格结构适用性；C2 另一已登记变体的三方关键关系也不能用 BK32 的结论代替。下面分别说明已证事实、真正缺项和最短补项，不要求 source-exclusive cost、完整 ISA、精确相同 issue 顺序、native iteration_id 或 engine busy。

## 身份、范围与未执行事项

请求配置沿用原独立 fresh reviewer 的 GPT-6.1-Sol / xhigh；工具没有暴露实际 resolved 型号或 effort，均记 unknown。本人独立判断，未读 peer 新报告，未与其它 reviewer 协商；parent 提供的事实线索只用于定位原件，不作为预期票。

审阅冻结 candidate 为 **6ebe9ecb8f13bcd0f32b86fa7a7ab00a44a32107**。Git 对比 `3b65197..6ebe9ec -- Debugger Profiler integration/patches` 只有 `timeline_runtime.md` 的 16 行说明，最后实质产品增量是已独立审核的 GCU preservation。读取时工作树存在 `gcu_native_values.py` / 对应 test 的 R092 未提交改动；本报告相关判断使用 **git show 6ebe9ec:…** 的冻结源码，不将新 auto-tail 在途能力计入。

冻结关键源码 SHA256：

| 文件 | SHA256 |
| --- | --- |
| Debugger/python/flagtree_debugger/gcu_native_values.py | dcc0d5eb8a5493dc8b2bda43acb4cb9695631d339855299c7badbea4ded42812 |
| Debugger/python/flagtree_debugger/gcu_native_control.py | 90a0c4343e0b0193583500bc2bbabacd25a1b74d47e499ca39ea530190a61f83 |
| Debugger/lib/Instrumentation/GcuExecutionPreservation.cpp | 6c60defb0509c72c132d2fefe0bf38effd05b5fd444e15549ca7dc9b12737644 |
| Profiler/llvm/AscendLateObserver.cpp | 0d5b551951df6407604d81b2e03dcb1b3299f71f6e5903d0cb0f7ea0963fe805 |
| Profiler/python/flagtree_profiler/timeline_events_ascend.py | 762d18c8f9fa7fc4b5818433df1385f03b87619bee5f655265d9a90ca5286e2d |
| Profiler/python/flagtree_profiler/timeline_nvidia_loops.py | 7825f43bf0e89dbbc3c98d64ec325331da8ddb7ff5c8e33f29539d47f6614c22 |
| Profiler/docs/timeline_runtime.md | 2459a651edf15960b54df90a9323b3439aea5f9d0d0b1e028081186534ff671d |

判据为根 `timeline_goal_prompt.md`，设计 §0.5–0.6 / §8.12–8.14，测试 §0.2 / §3–§5 / P03/P07 / §8.7，及当前 runtime/quickstart。复用本人 R057 全链与 R058–R090 已完成、无变化的有限源码/primary 收据审核；复读本人 R075 whole 清单，重点重核其剩余是否已被新材料关闭。本轮实际读了 R083 matching GCU ELF/最终 LLIR/native/位置、R069 共享 end/时间值用途、R084–R087 组件与安装事实、R089 Asc vector/原 manifest/raw/R063 保留 opcode、R090 三方流水与精确 SDK helper、R091 current96 inventory，以及 R076–R089 State/预算/codec/E01/安装的 primary 结果或本人已核原结论。未用历史 README 的 pending 字样直接决定当前状态。

只做本地文本/JSON/Git/字节和 SHA 读取。没有运行产品/import、测试、编译、SDK、模型、设备、数学、TP/UI 或 SSH，没有新增矩阵，没有修改产品/论文。未重新逐条复验所有历史大归档、所有 UI 截图或另一席负责的全部 clock/epoch 算术；这些无变化结论沿原独立审核范围复用，不能以本报告替代另外两席。

## 已直接完成，不能再作为当前 pending 的项目

| 原项目 | 当前直接依据与结论范围 |
| --- | --- |
| 三后端公开编译/采集链 | CLI/API 的 timeline 选择真实进入 late NVIDIA、GCU execution rewrite、Ascend SDK actor driver。kernel 无需 scope/site/scratch、逐算子适配或隐式 replay。按实际 target/compiler/SDK/plugin 条件分发，未发现按数学名、shape、固定 SSA/hash 放行的产品分支。 |
| ABI/cache 与安装 | Ascend 两条真实 JIT pre-lookup 身份、文件内容及 bare-opt PATH 修复已有 pinned-parent apply、normal/-O、正常构建安装和 profile→ordinary→同 profile binary 恢复证据；NVIDIA v4 预算/parent optimized-LLVM ABI、GCU tool/bridge/SDK 指纹均已接实际 lookup。没有用 QA overlay 冒充正常安装。 |
| 实际 observer / 完整性 | Ascend GET.SUBBLOCKDIM 发布 flags8–9，按实际 actor 数排除 reserved slot，旧无 feature raw 仍 unknown；GCU guards、计数/发布/owner 恢复、NVIDIA count reset-after-record 缺陷已按 matching 修复闭合。partial、unselected 和 unavailable 不被当 complete。 |
| State writer V1 | NV 最终 v9 的 40 ordinary +118 profile、72 distinct partitions 和 22 normal/-O fixtures 已核绑定；Asc ordinary32/current96/supplement8、GCU ordinary32/current96/supplement8 已有有限 checker、真实 transfer/actor ABI 和原 binary/LLVM/input/State identity 组合。GCU 原 109 历史中的 12 q05 certificate 拒绝保留，current96 使用登记修复替代，不给旧失败追授资格。此子门不再因 SDK ABI pending 的旧状态开放。 |
| 预算/恢复/E01 | R076 GCU 原 bundle recovery、owned child/SDK 外部工具生命周期；R077 writer/read 预算对称、legacy64MiB、公共 object store/reader 接线与正常 wheel；NV/GCU E01 和 Asc owned-copy whitespace recovery 均已有限闭合。Asc 原 E01 terminal1 保留，新副本 66,815,281B <=64MiB，raw/trace 不变，不冒充旧 run 成功或新设备执行。 |
| 公共消费者与输出 | 原 raw/manifest/schema、单位/epoch、机制资格分别处理，公共事件/view/Perfetto 不解析三家 ISA 补业务。已有实际 ns、dependency、TP/SQL/UI 与离线重导/版本化原件，不因本轮未重跑而倒退。R059 1,740 trace 索引及后续受影响定向 TP 不再是旧 G5 缺口。 |

GCU R087 尤其新增了实际有用的保留证书：`GcuTimeline.cpp:561–583` 在 rewrite 内按原 Operation identities 投影额外操作，严格比 typed SSA/CFG/attrs/types，并核新增效果隔离，再写 `manifest.user_program_preservation`；公开离线检查重现同 producer，不用有歧义的 greedy 子序列。实际 normal tool / standalone / installed SHA 同为 `da3a0392eb85fe0f211028aa5403d62e199b5698d026fd5ec578c50cccea21fb`，10 native fixtures normal/-O，109 历史输入的 97 preserved /12 different-core、37 distinct 及旧/新 37 outputs byte-identical 均有终态。它支持组合 State 判据及原高 IR 数学未变，**不独自证明 SDK 后最终边界或 native 流水**。

可扩展边界也不只是 adapter 类：公共 owner/admission/retain/decoder/view/exporter 实际复用于三种 executable/queue，后端保留 AIC/AIV、private tag、full-CTA byte participation、各 clock/provider 的真实差异。新目标仍需逐 compiler/transport/decoder/clock/mechanism 条件补证或替换；没有第四芯片不构成缺陷，也不证明同品牌自动继承资格。

## 原 source/loop 剩余中，已有实际成立的有限事实

### NVIDIA

`timeline_nvidia_late_boundaries.py:387–400` 自动衔接 source issue、matrix issue 与 native loop；独立 origin 标识、最终 PTX/CUBIN 两种 native 对象、reader→raw 字段及循环路径均有 normal installed 实证。R061 FFMA 被夹住，R071 matrix、R072 origins、R073 conditional EXIT 修复分别有实际源码/语义反例闭环。源 iteration 身份、exclusive cost、engine completion/busy 没有被误授。

这些规则是有限支持谓词，不能仅凭一个成功样本授给所有源码 fragment；但不能再把 NVIDIA 与 GCU 未接入规则描述成相同空白。

### Ascend：已记录区域/重复门的有限正例成立

R089 vector capture、硬件 ELF **73c2d8d27a949359f22fce1095c56706240d065cad492e73f97653848d682b0d**、原/adapted LLVM、manifest/counter-map、原 raw 与 R063 保留 SDK opcode 有一致对象链。模型子进程139、不完整执行、8 absent markers 均保留，未将模拟耗时当硬件时间。

- site16：begin **0x12d0** → VMULS **0x12e8** → VADDS **0x130c** 的连续已 decode 前缀无控制转移，end **0x1334**；原 scalar induction 在 **0x1254/0x1258**，位于 begin 前。后者不推翻真实 observer bracket，也不是宣称全部 source membership 原指令都在区间。
- 实际两展示 actors 均有 site16 **3 个原 raw pair**，正/零 tick 原样保留，`iteration_id=None`。这是同 source 关联的真实重复，不是仅从常量 K 画图。
- site15 source load、site17/18 两个 store 区域分别有实际 readers/issue 定位；17 的 MTE3 store **0x1974** 在 **0x1784..0x1978**，18 的 **0x292c** 在 **0x2740..0x2934**。它们提供另一源区域佐证，不强求每条极短 store 独立正 duration，也不把该 containment 升成 all-path 完成证书。

因此，原 goal §2.2 的 Ascend 实际内部区域与循环重复的**这一有限案例证据**可肯定，不再以完整 native CFG、source iteration_id、独占耗时未证拒绝。当前 `timeline_events_ascend.py:588–619` 的 observer elapsed、pair-order occurrence、boundary unverified 与文档两段澄清均相容；无需改 raw/membership/计时。仍须区分下述产品自动规则与其它资格结构。

### GCU：已有明确实际 reader/body/loop 正例，但尚无自动收据闭环

matching R069 ELF0 **7d56f25f70633d7f0d813a78e8ded073b884a4356d940a4cb48c710794f00500**、LLIR **6b8b2e1a95808ec6f924dac1324f449b44f5177e89f5d5e11de6ade3511eb593**、LLVM11 native **a4423a389544cde04466ad381de272754c8c79d3860eabc48dd86898a9015e8b** 可逐实际字节对应；不是用 R068 另一 ELF 拼证。

site11 的 LLIR bb41/42/44/45/47 保留原 runtime-step compare、选择路径、compute、end/record、increment/backedge。native begin packet **0xbc70**（有效取样 +0xa 等）、原数学 **0xbd34/0xbd44/0xbd54/0xbd64**、end packet **0xbda0** 与 latch **0xbc10** / exit **0xc2f0** 明确可定位。实际 site、begin low/high、end low/high、identity 分别进入本 record 的相应 stores，足以说明这里存在可实施的有限模式，不是只剩 opaque SDK 或正 duration。

共享 end 同样可以正确：LLIR bb16 合并 site1/2/3 的 site/begin tuple，共用 end；原三前驱 packets **0x68a0/0x85b0/0xaa90** 到 **0xaaa0**。记录体 **0xabd0** 另有 **0x9720** direct entry，故不能只查三前驱就对整个 record body 授全入口资格。begin high/identity 的具体 spill 槽为 **sp+0xac / sp+0x8c**，不能依旧 manual 猜值。DI address 是16B packet 起点，不能按与有效 instruction PC 不全等误报缺失。

R084/R085 已把 relative tail、reader rollover/fastpath join、same-packet 限制做成健全范围明确的组件；R086 bounded direct-edge index 保留 unknown/call/loop 等。它们减少了实际缺项，但冻结版尚未把该组事实自动联接到 source/loop 报告。

## 三方关键 pipeline：本轮可以关闭什么

### NVIDIA 已补齐旧 V2 的具体普通事实

原 ordinary CUBIN `76d2bd463b479eeb70eae1d86c6e14f6689c2c699f7ff174f0eae4e83ceb5956` 的 native JSON SHA **623a7d8b35593c422b7cc0deea13657f5b47aeb0e10a05242dce162dad01cae9** 与 R061 本地原件逐字节一致；R073 新 ordinary 编译身份不是借旧不同 CUBIN 的 PTX 猜测。

current slot UR14 与 body-write/reuse slot UR13 分别递增/wrap0/1，LDSM 使用 current UR11，body copy 地址经 R7 的另一索引形成。prologue 两个非空 copy/commit，body wait1→publication BAR→当前 LDSM，reuse BAR 后 body copy 复用已消费 slot 为未来 tile(i+2) 写入；另一已提交 tile(i+1) 可保持 in-flight。四 HMMA / body copy 的 issue 交错变化真实存在，但不是新的完成依赖证明。

该普通角色链结合 R074 default/sparse K3 的4/6、K7 的12/14 非空2048B future-prefix witnesses、wait1→wait0同计数反例，以及 R075 **960 word→实际 raw generation**、26/26 显式寄存器锥排除本函数 HMMA/clock 结果路径，足以关闭该案例“静态关键依赖/合法 overlap 机会保持”的有限缺口。无需 body copy 仍位于最后 HMMA 前，也不要求隐藏 scoreboard 全解码。入口 P3..P6 定义未知和 through-memory=false 仍保留，不包装成完整值定义或硬件 overlap 证明。

### GCU BK32

R090 ordinary、actual before、sparse1/default8 SDK input/fatbin 与原 capture 相绑定。实际原程序 A/B 非空 GM 搬运分别使用 private tag1/tag2；A await 时 B submit 已存在，A reslice 在 B publication 前已提交，两个消费者前只等待其原 tag。shared/local footprint、tag角色、publication/reuse cut 未变。具体同库 helper SHA **f09d690912c6b0c357a140e01b2e24a2986fd46633ac6c3bba59f9ba330cd870** 表明 wait.dec 使用实际私有 tag token，不能读作全 tag drain。

logger 在独立 local ring 记录，正常 return 才用独立 tag 发布 hidden buffer；没有新增 loop 内原 completion wait、全局 logger lock 或原 compute 结果到提交/原控制的数据边。这是参数/来源/原 consumer 等待的核验，不是只有相同 primitive 数量。具体非空未来操作仍被原等待集合许可；不声称硬件实际并行比例。

### Ascend BK32

R090 ordinary passive-codegen whole kernel.o 与原 npubin 同 SHA **77d49b1a3f9f67358f72743a68c39e8adef48a4799af591e4b1ad4f484e8d0cd**；两 profile 用其真实 loaded 对象及 actual actor输入。原 GM A/B → L1 readiness、L1→L0、MMA、归还事件、6轮复用及最终 C publication 同参数/pipe/event 保持。

同资源 SDK helper **7f4e64f840da5f1c581754e8e57cfa3f9510ddff57b422fc2f3f05824d70c7e9** 解决关键 opaque：该实际参数下 MMA 返回前原本已有 M→MTE1 两尾部 WAIT；小 tile 另有原 barrier。故该 caller 下一轮 GM 提交 cut 本来无未完成前轮 MMA，不从 num_stages=1 猜测，也不强造漂亮 future overlap。logger SYS_CNT/独立 hidden-GM 记录未引入新完成依赖。

该 BK32 静态保持可以肯定；原 capture 的 native valueflow/epoch/unavailable timed dependency 字段不会因此改 true。每后端至少一个异步时间图可使用原已闭相应机制案例，不必强迫这个 BK32 产生箭头。

## Confirmed blocker / major / minor

**本轮均无新增确认项。** 未发现必须先改普通数学、缓存或 logger 才能保住上述三方 BK32 关键关系的具体串行依赖。下面是原要求的实现/verification gaps，不能改写为已证明的硬件错误；同样不能用“无新 bug”代替完成票。

## 必要 verification gaps 与最少补项

### G1：有限 source/loop 规则尚未接自动链，GCU 是最明确的产品缺项

**合同原文：** design §0.6 要求首批支持结构有“自动检查器最低核验内容”；testing §0.2 要求“收据自动绑定实际 binary/site/路径”，并用“关键运算越过读钟、循环读钟外提或出口绕过端点、helper caller/site错关联、原wait覆盖改变”等自洽语义反例验证实际规则。原合同允许未证内容保 partial；这不等于当前所有原必达已完成。

**位置/触发与后果：**

- `gcu_timeline.py:345–408` 正常 fatbin hook 仅调用 `--native-locations`；`GcuNativeLocations.cpp:110–134` 是 DWARF 行定位，三个 qualification 字段明确 false。`gcu_native_values.py:1–6` 也明确不核 incoming begin/site、选择、source；`gcu_native_control.py:index_direct_control` 只索引支持 direct 控制。这些组件未在公开自动 source/loop provider 组成 actual site→reader→record→body/loop 报告。触发者是正常 runtime-K/source 操作，不是用户额外要求高级解释。
- Ascend `AscendLateObserver.cpp:688–708` 自动生成原 fragment 与端点，但 `timeline_events_ascend.py:607` 统一 boundary_unverified。R063/R089 本人的实际有限 source 正例不是用户路径中的通用结构判据。不能把它直接授给 current 独立数学；反过来不因尚无此产品规则否定该实际案例已记录的 issue prefix/occurrences。

**最小可实施路线：** 在 GCU 现有 `bind_native_clock_locations` 后接独立 derived provider（offline 同一 provider），消费 matching ELF/final LLIR/manifest、byte-bound LLVM11 native 和现有 reader/control 组件。先支持已有 site11 这类有限 scalar/vector body+有界 direct runtime-loop：核 actual reader 输出到同 record 字段；选中路径的声明成员在 pair 内；相关 header/latch/exit 不绕过端点。只处理实际必要 copies/固定 spill 槽、支持 direct 分支及现成原语，必要 unknown 明确未证，不扫描解释整个 SDK。共享 end 按动态 site/begin tuple 入边核验，遇额外 0x9720 入口须纳入本模式或保该共享模式未证；不能假复制 DI 行。

Ascend 可先把已证 `source-linked observer bracket + verified issue-member prefix` 作为独立且范围准确的规则结果，保全部原 membership 与 boundary_unknown，不谎称整个 fragment/source cost；输入仍须绑定该真实对象的实际 opcode/reader及原 actor/manifest。另一对象若没有所需 decoded prefix，只保具体未证。对 runtime-loop 仅在真正支持路径时授 loop-boundary 范围，实际 occurrence 与 native/source iteration_id 分开。

最少语义负例仍是原合同几类：关键 member 越过 reader、selected body 的出口绕过 end、共享 end site/begin 错配或被覆盖；合法实际对象是正例。规则版本/target/tool/input摘要与实际 export/cache失效分别绑定，在原预算内运行。只补该代码/安装/受影响离线正反例，不重做数学矩阵或创建全 ISA/alias/IPA 证明器。R092 在途 auto-tail 可以减少人工选择，但尚未接入口，不能单独关闭本项。

### G2：把已有有限规则实际适用范围接回原独立矩阵；盘点不是资格

R091 两份 inventory 已终态0、无 device/codegen，calls各96；GCU为32 distinct binaries /33 binary+LLIR结构对象，Ascend为28 binaries /40 current actor-input SHA（不是旧44）。对象和调用表 SHA 已核：

- GCU objects `32745e99151c3660c530739268126eaa371a2726a9d82083ba73c360954816cb`，calls `200c0d134a628cbf52bc18cbff832069eb82e3147ce39f42e5096132a57a50ad`。
- Ascend objects `ce37b1e04dfaa0cc1c2086bc5113f3205005394a45ab31b13b22227ba815b134`，calls `8150a5f35299a826fab2791b95c2392e682082e79b34be195f65cbff8498ea7d`。

它们明确 `native_source_loop_qualified=false`。具体例：GCU q01-s0-c0-cold binary `1aca222a…8a4ab` /LLIR `38a200e7…f6b90` 的 metadata 只有原 debug_execution_manifest，没有 native_locations；不能把新 R069 另一对象的成功代入。Ascend同case binary `30a52f0f…de512` /actual AIV input `e038de7d…f113c` 也不是上面73c2d8 vector ELF。后果是当前96的数值、State、raw、clock/TP通过，尚不能自动填 source/loop 门通过。

最少补项是以这些已去重结构对象为输入，按原 runtime-K、reduction、matrix 家族及支持谓词运行/关联有限规则，逐当前调用引用实际结果与旧producer/修复替代身份，列必要模式是否覆盖、具体 unknown 和已有真实 occurrence。相同对象/结构可复用，不要求每个 fragment、每条 ISA 单独证明或再运行96数学。NVIDIA已接规则，也应在原资格结构索引中说明实际支持/未证范围；不能以几个 scalar/matrix 正例整行放行所有源区域。此项是 G1 的适用性闭环，**不是新增独立数学数量**。

### G3：C2 另一冻结变体的原关键关系，不以 BK32 冒充

这里只按原 `timeline_testing.md:300` 的明确要求：“**C2 每个调度变体分别对照**……必须说明关键依赖、机制和原有合法 overlap 是否因测量串行化。” 原 runner `p01_controlled_workloads.py:158` 登记 C2 [32,64]；因此这是原 C2 范围，未新增一个“所有 variant 必须同样表格”的门。

本次具体完成的是上列 BK32；R057 另一个 **BK64** 的真实 ordinary/default8/sparse1 数学/IR primitive projection存在，但 projection 名称与顺序并不独自说明 buffer/consumer/wait覆盖/future cut。本席未取得与 BK32同等的这些有限关系依据，不能将 BK32 helper 的具体 k_actual32/尾部 cut 外推所有参数。Ascend该case ordinary binary `21681db4dbb5059b5954421e5b97334d670b29a5718d8f0d544af54504a6e91d`、default `2b76cd0cfcc0de6d13a28596095764dec41f7956f37eac117a5bc8470a514c74`、sparse `31f2a9ce155693913e894535db6eeb06db56c326da08279ebb608a46228da20c`；GCU为原 density results 的 variant64/density1、8。

最少是复用这些已存在的三方实际对象，核与原变体差异有关的 tile/buffer参数、submit→wait覆盖→consumer→reuse及原in-flight是否仍许可；同 SDK helper 的完全同条件可直接复用，不用再解释全部 native 或要求相同 issue 排序。若现有原件中这些关系已经足够，只需该有限核验/引用，不需要新设备/数学矩阵。Ascend BK64 sparse1 只有第一capture正常、第二仅1 positive而失败、第三未启动，是既有显式低密度失败，继续保留，不能挪入 default 失败或要求它为关闭 default 门重新变成功。两种 default 的成功也不据此失效。这里待的是原 C2 解释范围，而非强迫每个低密度 trace 合格或强造硬件 overlap。

## Optional

没有新增必须重构或通用框架建议。可把上述 GCU共享end/packet、Ascend issue-prefix/occurrence、BK32普通原completion cut、NV保留非空future机会作为简短可解释案例索引；这是呈现改进，不替代 G1/G2，也不改 raw/旧资格。

## 最短剩余清单与最终判断

1. 补首批有限 GCU/Ascend source/loop 判据的自动接线与语义负例，复用已有 matching 原件、reader/control 与编译来源；未支持形态如实 unknown。
2. 用 current 去重对象将这些规则的实际适用范围映射回原独立资格调用，补具体缺失的原件/模式，复用已证数值/State/单位/TP，不新造矩阵。
3. 对原 C2 的 BK64 仅核尚未直接闭合的三方关键关系/参数差异，保历史 sparse1 失败，避免将 BK32 有限结论扩大。

本席支持按已证范围交付当前阶段工具能力；不支持宣布原完整三后端 goal 已完成。没有新增确认代码缺陷，也没有把完美 hardware busy、source-exclusive latency、通用 ISA、全路径形式化、精确相同 issue 顺序或所有 region 都必须正时长变成门槛。G1/G2 属真实工程接入/适用性缺口，G3 属原已登记 C2 的有限解释缺口；不能由正 duration、同指令数、单个 adapter 类或 reviewer 投票替代。
