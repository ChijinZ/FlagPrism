# 内部时间线测试与真实算子验收

状态：**完整验收计划，尚未通过**。有限原语/CPU/构建检查已有独立记录，不等于下列设备资格或 Perfetto 验收通过。配套 [技术设计](timeline_design.md) 与根目录 `timeline_goal_prompt.md`。本文件所有算子/干预是待运行场景，不是已有性能结果；不预填时间、重叠率或加速比。

## 1. 分开验证五件事

1. 算子与应用没有被破坏：数值、输入、tail/canary、请求调用次数、side effect。
2. 时间数据是真的：实际设备 getter、原始 bytes、实际编译位置、时间单位、调用/主体/配对/损失。
3. 解释没有越界：issue 不是 engine busy，completion observation 不是精确硬件 end，静态边不冒充动态 flow。
4. Perfetto 真的可用：用实际导入器和 UI 打开本次真算子 trace，看到可解释的内部结构，而不是只校验 JSON/protobuf 能解码。

5. 后端边界真正可复用：三个真实后端遵守同一事件/时钟/依赖消费合同，架构特有信息没有被削成公共指标；不依赖新增厂商展示分支。

所有产品 import、oracle、测试、编译、设备采集和浏览器在服务器 Docker。工作机只编辑、Git、调度和留存 bytes 审计。CPU 合成记录用于负例，不算真实设备覆盖。

## 2. 真实开发算子集合

先使用明确的算法和结构开发。下面的形状为初始测试输入，合法 tile/warps/stages 在普通 baseline 阶段按后端确定并冻结，不能以改变数学或放宽容差迎合 logger。

| ID | 算子/算法 | 初始工作负载 | 必须在实际时间线检查什么 |
| --- | --- | --- | --- |
| D01 | 流式融合更新：读 x/a/b，在运行时 K 次递推中执行稳定的逐元素非线性/有依赖更新，再写回 | N=65536、65539；K 从 device 输入取 3/7/11，系数选择保证有限值 | 多个内部区域；同一 binary 的真实重复；begin/end 没被移出循环 |
| D02 | 分行稳定 Softmax：max、减 max、exp、sum、normalize | M×N=64×256、67×257 | 两个以上可解释内部时间段、归约/控制区别、首末 program 与 tail |
| D03 | Residual RMSNorm：residual 加法、平方和、rsqrt、scale | 64×1024、65×1009 | 融合区域源关联、不同 layout/tile 的 specialization 分离、区间语义 |
| D04 | tiled GEMM，累加跨 K tiles，包含合法 software pipeline 变体 | M×N×K=128×128×256、137×131×259 | 循环阶段、提交/等待/计算区域；有来源的 buffer/group/generation；不能假定配置一定重叠 |
| D05 | GEMM + bias + 非线性 epilogue/行归约的普通融合算子 | 128×128×256、133×139×261 | 对实际 lowering 为多主体的后端展示 producer/consumer；纯单主体也要如实显示 |
| D06 | tiled 分块归约/streaming 计算，两个数学等价调度变体：单缓冲与合法双缓冲 | 32×4096、35×4103；tile/config 两组 | 实际 async producer/consumer、等待与可证明的阶段关系；未生成异步结构不能算异步覆盖 |

D04/D05/D06 是异步案例候选，**每后端至少一个必须实证生成并观测真实异步结构**。先核普通编译的 IR/ISA/执行组织，不能从 `num_stages`、算法名或图形期望推断异步。若某候选确实没有异步结构，保留其结果，另预登记合法普通算子；不能把 profile 失败改记成“本来不适合”。

必须区分：正常 Triton 数学/调度代码可以使用编译器支持的异步能力；验收不能写 profiler scope/site/marker。Gluon/厂商特性程序可以补机制覆盖，但不能代替三类普通 Triton 输入的通用验收。

数值 oracle：服务器 CPU 高精度参考或已核验参考实现，记录输入 dtype、accumulation、FP 模式、seed、rtol/atol 和 tail 定义。FP16 GEMM 等误差阈值在普通 baseline 前根据算法固定，不在插桩失败后调大。主输出必须来自原真实数学，不接受纯 sleep、人工延迟循环或仅打时间戳的空 kernel 充当本集合。

## 3. 独立新数学与冻结

- 开发集合和旧 census 验收只作回归；另由独立 qualifier 写至少六个新数学 kernel，三类各两个：融合访存/逐元素、归约、矩阵/融合计算。数学表达和源码不能仅换名字/shape。
- 每个新 kernel 每后端两 shape（至少一个 tail）、两合法 config。grid 至少包含两个真实有工作 program，单 program 仅作单独机制测试。
- 每后端登记 24 个 ordinary 组合。普通 baseline 冻结源码、配置、输入、oracle、预期控制/执行结构、编译器与目标身份的 SHA 清单。
- 全量 profile 前冻结产品、默认 planner、native/SDK、wheel、公开说明与 verifier。每个 eligible 组合跑一次 cold、两次 warm，合计每后端最多 72 次独立 profile；每次使用自己的输出目录/调用身份。
- cold/warm 指编译缓存；不允许为得到 warm 结果在 profile 内秘密多跑。harness 的三次运行都显式记录为三个独立捕获。
- 某组合普通不能编译/运行，保留前置失败并事先登记替补；普通可运行但 timeline 失败必须保留为产品失败，不能替换、缩范围、只报告成功 subset。
- 至少两个 kernel 用运行时输入改变循环次数并证明 binary 相同。`constexpr` 重编译不能算该验证。
- 工程人员在 freeze 前不读独立源码。失败后可以为通用修复查看实际最小失败代码，记录暴露范围；样本随后改称修复回归，不再叫未见。最后补至少两个独立新数学，覆盖被修复结构。无需强制永久保密导致不能调试，但严禁 per-kernel 特判。

## 4. 每份真实 trace 的硬性检查

对每个 eligible 非平凡组合，ordinary 与 profile 同时满足：

- 原数学、输入不变、canary、tail、有限性、原 tolerance 通过。
- host script 仅请求的次数；device side effect 为每请求正确增量。oracle 必须有合法唯一写者或独立不重叠写入，先证明其实际 lowering；不能把不合法非原子多写者 State 当 replay oracle。
- 原始事件能追溯到实际 capture/invocation/binary/region/program/observer。至少两个不同源码区域产生真实有起止的区间；qualification 的非平凡输入必须有多个正 duration，不能全部是整核条/instant/0-width。
- 循环样本至少展示三个实际 body occurrence；重复次数随 runtime 输入改变，parent/child 和 begin/end 关系由真实动态结构核验。不能要求被优化消除的循环仍有虚构事件。
- raw ticks 来自真实设备、getter 的实际编译对象有 hash。每条已导出的 slice 都能定位到 raw offset 或保留的原生 SDK event；不能从整核时间按比例分配。
- 单位和 epoch 证明有效，end≥start；回绕只在唯一可解的位宽/窗口内处理。负 duration、时钟逆行、未知频率或不可解回绕不能偷偷 clamp。
- default 选定 program/observer 范围全部闭合；未选择与丢失分开。loss=0 的默认资格不能靠大量截断过关；overflow 机制测试另计，不混入正常集合成功率。
- 每次请求的调用分别有自己的结果，不能另一调用的事件补空。多个 specialization 不串 site/binary/clock。
- 原编译/导出/容量预算通过；保冷编译、host export、bundle、raw、trace 大小和实测值。

不能强迫每条极短操作都有可分辨时间。若测量量化不足，可自动选择更粗的真实区域，但仍需满足这些非平凡算子的内部时间线要求，且不能为放大时间在产品中添加无关计算。

## 5. 异步与调优解释案例

每后端至少一个例子必须具有：

1. 普通编译证实的 async submit 和原有 wait/completion。
2. 实际记录的 producer/consumer 或 submit/wait 泳道，正确标注观察者身份而非猜引擎。
3. runtime operation/group/buffer generation 关联；flow 由这些证据产生，不由名字/邻近时间产生。
4. 支撑该图的共同/可转换时钟。若只有单域局部相对时间而没有目标 edge 所需的对齐，异步可视化门尚未完成。
5. 至少两轮 in-flight/reused-buffer 生命周期；同地址/同 flag 下 generation 不串联。分别覆盖首轮、steady state、末轮 drain。
6. 无新完成 barrier/全局 logger lock，原编译 schedule 的关键依赖未因插桩人为串行化；保实际 IR/ISA 对照和稀疏/较密观测影响证据。

受控案例至少两个，不预设漂亮结果：

| 实验 | 允许改变 | 固定项 | 所需结论 |
| --- | --- | --- | --- |
| C1 计算工作量干预 | D01 的 runtime K 或真实有效归约工作量 | binary、配置、logger、输入生成规则与计时方案 | 动态重复与区域经过时间可以被独立解释；在噪声足够小的窗口检查趋势，不用一次快慢断言 |
| C2 流水调度干预 | D04/D06 同数学的合法 tile/stages/buffering 变体 | 同输入、shape、dtype、tolerance、观测语义 | 哪些 submit/wait/完成包络发生变化，哪些重叠有证据，是否仍是同工作量 |

Ascend/GCU 在稳定窗口记录未插桩参照和噪声，避免拿插桩执行时间直接声称加速。NVIDIA 保留用户此前暂缓的设备性能/开销认证边界；本轮仍必须采集真实时间戳、验证单位与结构，不能以“暂缓性能”跳过时间线。时序功能验证不需要宣布速度提升。

若变体并未降低等待或并未加速，应报告实情；这不是测试失败。无法给出任何可信内部时间变化、依赖或局部瓶颈解释，才说明该层尚不可用。至少提供一个“当前数据能解释什么/不能解释什么”的实际案例记录。

## 6. 必须覆盖的工程/故障场景

| ID | 实际/负例输入 | 验证点 |
| --- | --- | --- |
| E01 | 同脚本重复 10 次调用，交错两个 specialization | 调用/二进制/region/token 隔离，无隐藏 kernel replay |
| E02 | 两个真实 program，首末含尾部；再加单 program/零 grid 边界 | 选择前预算，实际坐标，未执行/未采集区分；零 grid 不造 trace |
| E03 | 两 stream 交错启动不同输入；并发 host-thread/graph 测试 | 已支持路径真实隔离；不支持路径早拒绝且可恢复，不能 SIGABRT/假关联 |
| E04 | tiny buffer + 有真实数学的长运行时循环 | raw canary 不破坏、attempt/commit/drop、未配对事件与 incomplete 状态；不补端点 |
| E05 | 正常异常、编译失败、logger 分配/导出失败与 CLI timeout/cancel | 原异常保留；owned descendants 含 setsid 子进程有限清理/reap，下一正常程序可用 |
| E06 | 旧 census、旧 interval、native-only/API 回归 | schema/读写兼容；旧数据不被覆写成新真实时间 |
| E07 | 同源切换计数/时间、SDK/compiler/plugin 原地升级与 symlink | 实际身份进入 cache；mode/ABI 不串；旧缓存原件保留 |
| E08 | 修改 raw payload/header/commit flag/offset/ABI、删 begin/end | 必须检测拒绝或明确 partial，不能仍报完整时间线 |
| E09 | 错 frequency、缺 clock proof、跨 SM/epoch 错配、错误单位、超大 tick、长区间近边界、end≥start 但整圈回绕不可判定 | 转换与端点比较 fail-closed；保原 bytes，不把 cycles 填入 ns，不把不确定先后/重叠报确定 |
| E10 | flag/buffer 地址重复、故意串 generation、漏一 producer/consumer | 不产生假 flow；歧义有原因，动态 edge 的精度优先 |
| E11 | 跨 invocation 的同 site、同名 kernel、不同 capture/replay | 不用名字或时间邻近 join，不跨 replay 伪造一次执行 |
| E12 | payload saturation、选择之外的记录损失 | 全采集范围损失核，不只检查 UI 当前可见 program |

Schema、authorization、verifier 和完整性检查必须在普通 Python 与 `python -O` 下都有明确拒绝，不能靠会被移除的 assert。实际硬件测试仍用正确的普通数学，不把 CPU fixture 冒充硬件正例。回绕/异常比例等可以用合成负例，报告区分来源。

## 7. Perfetto 导入器验收

固定 Perfetto UI 与 Trace Processor 的版本/来源/SHA。依赖安装、SQL 和 browser 都在现有 Docker；优先复用已有 Chromium/Playwright 与完整字体配置，缺工具可在容器独立 prefix 安装，不改 host/daemon。

对所有正常资格 trace 用实际 Trace Processor 导入，保存退出码、SQL、输出和 importer stats。SQL 随 schema 固定，不仅数 event：

- `slice` 的时间/时长与规范化事件、raw ticks 经验证换算逐条对应；身份集合和可见 source args 不丢。
- 至少两个非 kernel 内部 region，有多个正 duration。trace 无内部记录却返回 0 不算通过。
- `track/args` 的 observer/program/invocation/clock 不能折叠或伪造；异步 flow 的 src/dst/token/generation 对应真实 edge。
- 不同独立域没有被错误叠在同一同步坐标；不同比较条件/重放明确分开。
- 纯 metadata、missing end、故意损坏单位/clock 等负例不能通过语义验收。
- 检查已知 importer error 类 stats；保存完整 stats，不通过过滤未知 error 获得全绿。

可提出如下查询意图，但实现时必须核实际工具 schema，不复制未经执行的 SQL 当结果：按 semantic/source 聚合真实 duration、枚举 track、还原 flow 两端、对照 event_id 与 raw proof、查询 parse/import errors。

## 8. 真实 UI 验收与交付内容

每后端至少挑六份当前实际 trace，包含两个不同算法、一个异步案例、cold/warm、不同 program 或 occurrence。三个后端的异步案例分别在对应服务器已有 Docker 中的标准 Perfetto UI 打开；不能只用自写网页替代 Perfetto。

资格前冻结 UI 覆盖表，列出每份 trace 的算法、cold/warm、program/occurrence、循环/异步适用性及预期步骤。每份操作与截图：

1. 上传/打开本次 `.pftrace`，overview 出现内部多 track，不是只有 kernel bar。
2. zoom 到实际内部结构，显示单位和采集范围；循环样本必须看见真实重复 region/wait 等 slice，非循环样本核对实际区域，不要求制造循环。
3. 点一个 slice，详情能读源码位置、主体、时间、semantic、clock/误差、调用/原始证据 ID。
4. 对有动态 flow 的样本点击端点，核 producer/consumer、generation 和目标时钟；每后端至少一份真实异步 trace 必须执行。无异步的普通样本核没有伪 flow，不将本来没有的 edge 记为失败；应有 edge 的异步样本不能用 N/A 逃避。
5. 看首/末 program 或两 actor，明确哪些同域可比较；不能从不同域归零图推断重叠。
6. 从 bundle 定位源 snapshot/原始记录；browser 前后所有 bundle 文件 hash 不变。
7. 每份至少三张实际截图：整体、局部内部结构（适用时为循环/流水）、slice 详情；动态 flow 样本另保可定位端点的详情，可与上述截图合并。截图索引给服务器/容器、browser/UI 版本、trace SHA 和选择事件 ID，不用手工重绘波形。

输出：源码/安装/native/compiler/SDK pin；测试注册表；首次结果与修复后结果；每组合 math/raw/time/clock/source/Perfetto gate；真实 `.pftrace`、bundle/原始 bytes、SQL、UI截图和解释；受控案例；已知限制；三个独立最终代码审阅报告及闭环。大型产物放持久路径/hash 索引，Git 只提交可公开的代码/测试/文档/小fixture/必要索引，不提交 SDK 私有库、凭据或巨型 trace。

### 8.1 适配边界与可行性验收（P01–P10）

遵守设计第 8.1–8.11 节。只用现有 NVIDIA/Enflame/Ascend 完成验证，不启动第四芯片适配。下表包含真实设备正例与 CPU 合同负例，必须在证据中区分；CPU 测试仍在服务器 Docker。建议复用同一份参数化公共消费者测试，后端分别提供真实 producer/安装证据。

| ID | 输入/操作 | 通过条件 |
| --- | --- | --- |
| P01 | 三后端分别登记真实能力与纵向样本 | 全量资格前有普通数学、实际 getter/单位、至少两源区域真实区间、一个真实异步机制/动态关联/可比时钟、Trace Processor 结果；未知点与硬阻碍单独列明。机制证据全部满足才进入该后端最终资格 |
| P02 | 目标/SDK/插件能力变化；未知项、错误 capability 声明负例 | 不仅按厂商品牌分支；目标不匹配/证据缺失明确拒绝或 partial，不报 verified；profile 失败不转 unsupported。CPU 构造目标描述只验证合同，不宣称额外硬件覆盖 |
| P03 | 三后端真实源区域经优化后 fusion/split/loop 的 manifest | 同一公共身份校验器核对源→执行的一对多/多对一与消除状态；实际 begin/end 在声明边界，核纯算术/访存/原 wait 不越界；按实际变换检查 fused 多 origin 不复制 duration 凑两个阶段、split/消除不造点，不用早期源节点冒充晚期 observer/engine |
| P04 | 三后端真实主体、缺失物理身份负例、额外角色 fixture | 公共 consumers 不强制 warp/SM 树，program/observer/operation/resource 分开；未知身份不补造；命名空间扩展可显示且不覆写核心字段 |
| P05 | 已有真实 raw 及合法不同 layout 的合同 fixture | 后端解码器承担物理格式，公共配对/时钟/导出消费同一合同；校验 raw offset/version/commit/loss。保 Ascend padding 和旧 ABI 回归；fixture 不代替真实发布可见性测试 |
| P06 | 同一套时钟负例参数化到三后端输出 | 错 target/epoch/frequency、精度不足、回绕歧义等均明确拒绝或标无比较资格；整数大 tick 换算正确。未知/未对齐域不因 backend label 获得共享时间轴 |
| P07 | 每后端真实异步样本至少两轮 buffer/flag 复用（完整资格必需；只有逻辑 group、unknown physical buffer 的结果不能单独满足此门）；批量/部分 wait/多消费者合同 fixtures | 真实机制覆盖的 operation/group 集合与记录一致，generation 不串；同一公共依赖校验器生成 edge；部分 wait 不完成未覆盖组、多消费者不丢第二条边、丢 commit 不平移后续 generation，只有明确锚点才恢复；不要求三后端都具有每种机制。合成 case 只补合同覆盖，不能称该设备支持该机制 |
| P08 | 实际后端数据通过公共 exporter/报告，扩展属性和新角色 fixture | 三后端用同一个 exporter 与 SQL 语义检查；展示无需厂商专用业务分支；扩展字段保留且 core schema/未知字段策略固定，不因 permissive dictionary 绕过验证 |
| P09 | 第一实现→第二/第三实现的 Git diff 与公开安装 | 有逐后端适配清单、公共变动理由和回归证据；注册/编译 hook 入口明确，不依赖私有热补丁；公共修正同步验证已有后端。无修改行数硬指标，不把新概念藏进厂商判断 |
| P10 | target/compiler/plugin/timer/rule/ABI 切换和 capability 失败后恢复 | 缓存/安装身份包含真实依赖，模式不串；早拒绝后下一合法请求可用，无隐式重放/额外完成 barrier；旧 count/native 和数据读取不退化 |

P01 是开发阶段的可行性检查，不是用一个样本代替独立资格。若一后端暂阻，保留证据并继续其它不依赖工作，不标三后端完成。所有未跑的测试保持未验证；设计评审不能替代实现后的真实设备、SQL/UI 或最终代码走查。

适配证据交付至少包含：接口/协议版本、三份后端实现清单、目标能力与证据、实际编译接入及产物、设备正例与 CPU fixture 标签、P01–P10 结果、公共/后端 diff 分类、未解决限制。采用可定位代码的审计，不能仅凭“有 adapter 类”判定通过。公共代码确需新增概念时允许有理由的版本化修改，不把“零公共改动”作为压倒正确性的指标。

### 8.2 评审风险对应的最小实证

不另外扩大独立资格矩阵；在 P01、P03、P05、P07、P10 与 E01/E03/E05/E07/E09 中复用以下检查，并保留实际证据：

- **编译边界**：真实有依赖纯算术 loop、load/compute/store 区域和原 async wait，核普通/插桩最终 IR/ISA 中的顺序、无新完成 barrier、loop occurrence 与真实 runtime 输入对应。volatile/正 duration 本身不足。覆盖已实际出现的 fusion/split/消除，不能要求设备生成本来没有的变换。
- **时间记录布局**：Ascend 新 timeline 物理协议独立证明 cache-line/commit 可见性，不把 census v3 通过搬给动态 v1；GCU 核实际 work-item 写者及完整 payload；NVIDIA 核 timer 与 packed 位宽/decoder/ABI 一致。
- **生命周期**：支持的两 stream 交错多次启动，脚本返回前不主动同步，验证无逐 launch host wait 强制串行；pending 时关闭/异常/cancel 不提前复用仍在写的 buffer；D2H/导出失败后下一合法 capture 恢复。允许最终化为安全导出等待本次完成，不能偷加设备全局完成屏障。按真实支持边界执行，不能在冻结后靠 unsupported 改分母。
- **缓存与目标身份**：同 specialization 改真实 launch grid（含 1D/2D、单 program、零 grid、tail），首末坐标/admission 不串；内存/磁盘缓存查询前取得 SDK/timer/plugin/rule 的实际依赖身份。本次 epoch 不从历史 bundle 继承。
- **合同与扩展**：第一真实链之后冻结设计 §8.6 的小版本及实例；错类型/core 覆写/未知必需语义/悬空 group/source/binary 引用显式拒绝，ordinary eligibility、target 能力、本次 plan/outcome 不相互覆写。每 slice/flow 保所有端点与组成员所需 raw 证据。

历史设计评审见 [评审记录](../../integration/plans/timeline/reviews/README.md)，本轮适配边界与资格范围评审见 [最新评审及处置](../../integration/plans/timeline/reviews/round5/README.md)。这些检查均待实现后执行；评审确认设计合理不等于 timer/epoch、编译顺序、发布可见性或 Perfetto 已通过。

### 8.3 后端交接与 owner 生命周期的具体判定

下表复用既有 P/E 场景，不新增独立数学数量，不引入第四芯片。状态机由设计 §8.7 定义；资格前将支持的并发组合和预算固定到注册表。真实设备正例与受控故障/CPU fixture 分开标注。

| 对应项 | 操作 | 必须保留的证据与失败判定 |
| --- | --- | --- |
| P03/P09 | 逐后端列出能力解析、计划、启动、完成、解码、机制映射的真实实现位置 | 输入/输出版本及公共消费者调用点；没有使用的空接口不算复用。通用结构修复可接受，按算子名/shape 派发插桩不可接受 |
| E01/E03/P10 | 对预登记支持 two-stream 的后端，在两个 stream 交错多 invocation，改变输入/grid/specialization，提交结束后才显式等待 | owner 快照、buffer 标识、原 stream 上完成依赖、实际 launch/host-wait 顺序与输出；先前 owner 不被覆盖，无逐 launch host wait。CPU 模拟仅补状态机，不能替代真实两 stream |
| E02/E04/P05 | 单调用满足预算但 pending 累积超过 session 字节/owner 上限；另测 grid 改变和 header/padding | admission 在产生被拒调用的设备副作用前完成；不大分配后补检查、不靠隐藏强同步清空队列。已有在途调用安全完成；报错与本次未执行状态明确 |
| E05/P10 | 在纯 admitted、初始化部分写入后失败、初始化成功但 kernel 未提交、提交后未完成、完成后 D2H、decode/export 阶段分别注入异常 | 逐阶段状态/owner/资源证据；只有未分配或已证明无任何设备写入者可直接取消回收；初始化也算潜在在途写者，armed/submitting/quarantined 无覆盖全部写入的完成证明不得释放或重用；超时仍在写时隔离资源并明确 session 失败。隔离资源的失败 session 不要求原地复用；写者结束、安全清理后的新合法 session 必须可运行 |
| E05/P08 | 同一 raw 原件首次导出失败后重导 | 不再次调用用户算子，raw SHA 不变，重导结果与同版本直接导出语义一致；保原失败。失败前未取得完整 raw 时不能伪称可离线恢复 |
| P06/P07 | 后端提供错误 clock 资格、串 invocation group、丢 commit、错误 generation 或越界 raw 引用 | 公共验证器实际拒绝/partial，不因后端声明 verified 而通过；真实机制语义仍用实际 IR/ISA/SDK 对照，不能仅用两个共享错误逻辑的模块互证 |
| P09/P10 | 将第二、第三后端逐项接入，审计公共/后端 diff 并回归已有实现 | 导出、身份、时钟算术和依赖完整性走共同合同；物理 ABI 和机制识别可不同。必要的公共版本修改须有原因与旧后端回归；不要求零公共改动或承诺第四芯片适配时间 |

生命周期故障注入只作用于本次拥有的测试作业/缓冲区；不得改系统 driver/daemon 或干预其它用户进程。逐后端在资格前冻结 two-stream、host-thread、graph 支持表与正/负例对应关系。两 stream 不新增为每后端无条件必达项：声明支持的后端必须真实通过两 stream 正例；声明不支持的组合必须核启动前早拒绝、无该调用设备副作用及安全恢复，不能以 CPU 正例冒称并发可用。不事后改标 unsupported，不以拒绝项声称保留跨 stream 行为。

阶段报告按“原语 / P01 / 最终资格 / UI / 最终代码审阅”分别给出结果；已通过时钟算术、手工 clock 原语或 native 构建不得自动填其它列为通过。设计合理性评审也不能填这些列。

### 8.4 最小接入合同的针对性验收

对应设计 §8.9；以下复用 P/E 的既有开发和回归样本，不增加独立六数学的数量，不把合成协议测试当作真实设备通过。每项记录“实现位置→输入身份→实际输出→负例→证据路径”，未跑保持未验证。

| 对应项 | 具体检查与通过条件 |
| --- | --- |
| P02/P09/P10：接入动作 | 三后端各定位 probe/plan/prepare/finish/decode/mechanism 的实际调用点及复用来源。公共消费者只消费合同；注册可有厂商分发，公共验证/导出不能自行解析厂商指令补语义。没有调用者的空接口不算完成 |
| P02/P06/P08：能力递进 | 构造本地域可用但跨域未知、逻辑关联可用但时钟不可比等组合；保留合法区间与事实，缺失部分 explicit partial/拒绝，无伪 flow/engine busy。partial 不计 P01/完整资格；某增强能力缺失不能使已验证的其它能力谎报失败或成功 |
| E02/P05/P10：紧凑存储 | 实际设备运行同 binary 的不同合法 grid（1D/2D/单 program/tail），核首末坐标、slot 映射、raw 字节上界及 allocation canary。存在未选 program 的 grid 检查其不写选中 slot；插桩后数值/副作用次数仍正确。静态/动态 grid 维度变化造成新 binary 时如实记，不伪称缓存命中 |
| E02/E07/P10：存储资格 | 旧 full-grid binary/错误 storage 版本与新紧凑 allocator 组合启动前拒绝；cluster/多 CTA 不支持时早拒绝，支持时实测映射。维度/乘法溢出在分配前拒绝；合法零 grid 无设备记录和伪 duration；错误后下一合法请求可用 |
| P03/P07：机制闭合 | 对每后端选定的真实异步机制核 manifest→最终编译对象全部状态变更及规则来源。用受控 opaque/缺边界/外部状态变更负例检查关联降级或拒绝，不能把未匹配指令默认为无影响。编译器拒绝该语法时记录不适用，并另用 manifest 完整性故障注入验证合同；不宣称该设备执行过负例 |
| P07/P08：身份与证据层次 | 逻辑 group 无物理 buffer 信息时可保留 group 关联，详情标 unknown buffer/iteration；禁止伪造 generation。完整异步资格仍须满足 §5/P07 的每后端两轮真实 buffer/flag 复用与代际证据；group-only 结果不能豁免该门。当前样本无法提供时，另取有来源的真实复用样本或保持该门未通过，不填造 buffer 身份。只有动态关联与相应时钟/边界证据满足时才生成时间箭头；未证共享 epoch 不跨域连时间线 |
| P01/P09：阶段放行 | 允许基础区间/owner/export 链先实现，以及其它后端原语调查；完整 P01 的两区间、异步、时间和 Trace Processor 门不变。逐后端结果分别记录，不以接口设计评审、局部构建或 CPU 合同通过替代设备可行性 |

适配成本审计解释哪些代码被复用、哪些目标条件/后端语义仍需实现，列实际新增/修改文件与公共版本变化。它只验证现有三后端的边界，不能由“类的数量/代码行数/假后端注册成功”推出新增芯片容易或已有设备支持。

### 8.5 面向新芯片的复用边界验收

对应设计 §8.10。以下是现有 P/E 的补充判定和证据组织，不新增第四后端、不增加独立资格算子数，也不以文档清单替代设备测试。实现前的设计评审只判断方案合理性，不能填写下表的实现通过结论。

| 对应项 | 实施时如何检查 | 通过条件 |
| --- | --- | --- |
| P02/P09：部件组合 | 对三个真实目标分别定位注册入口、compiler/transport/decoder/clock/mechanism 的实际调用；从公开命令追到它们 | 可复用部件无需每目标复制；相容条件明确。工具链不同允许独立实现，未使用的空类不算通过。保逐后端文件 diff 和公共变动理由 |
| P02/P10：组合不相容 | 在服务器 Docker 中构造错 target/compiler、storage/logger ABI、timer/机制规则版本组合；与正常设备路径对照 | 可启动前识别的错误在本次设备副作用前拒绝，原因可定位；必须到编译/解码后才识别的错误不获 verified，保已取得原件。恢复后正常请求可用；不把故障改写成 ordinary 不支持 |
| P03/P05/P09：新主体与物理布局 | 三后端实际 raw 分别走自己的 decoder、共同 schema/validator；额外 nonwarp 角色与合法不同布局仅补 CPU fixture | 公共消费者无 warp/SM 必备树、不解析厂商指令；布局/对齐属于后端，source M:N 不重复造 duration。公开注册可有目标分发，禁止的是公共业务层的厂商补丁 |
| P06/P08：raw 与 ns 分离 | 同一原始 batch 分别提供有效、缺失、过期和错目标 clock proof；真实设备正例与合成负例明确区分 | 原 raw SHA 不变；只有有效证明生成 ns 派生视图，保原 tick/转换/误差证据；无效 proof 明确 partial/拒绝，无静默 ns 或跨域箭头，不重放应用 |
| P07/P08：机制与展示分离 | 三后端各一份实际异步/两轮复用样本；共同依赖消费者与 exporter 处理机制事实；以批量/部分 wait/多消费者 fixture 补合同 | group 集合、buffer/flag 代际及完整引用保持；未知状态无伪 flow。显示名称和扩展属性可异，但时钟/edge 的资格判断不按厂商补分支 |
| P08/P09：公共导出可复用 | 冻结公共 exporter/SQL 语义的版本；对三个后端实际 canonical/ns 数据运行同一消费入口，再实际导入 Trace Processor/UI | 保证单位、identity、source、loss、flow 的同义检查；可按 semantic 查询，不靠放宽某厂商 SQL 让其通过。新增真实公共概念可版本化修改，并回归已有实现 |
| P02/P05/P10：独立部件兼容轴 | 从已使用的三后端组合出发，分别改变 compiler/manifest、storage/logger、transport/launch、clock getter、mechanism rule 的一项必需版本或条件；每项先有合法组合对照 | 实际调用的组合检查拒绝已知不相容项，诊断含冲突两端/预期/实际/阶段；启动前已知冲突无该调用设备写入/初始化。只能在 raw 阶段发现的问题保原件并拒绝解释；未知必需版本不获兼容。CPU fixture 只证明合同，不能声称额外硬件支持 |
| P03/P06/P07/P08：资格范围隔离 | 同 batch 至少两个 site/observer，分别使一个区域边界缺证、一个 clock 过期或一个 mechanism 不完整；另测仅有 counter PC 映射而无区域顺序证明 | 不把一个有效证明扩散给其它 site/domain/机制；时钟合格不使源区域边界自动合格，机器 PC 映射不等于区域边界，逻辑组不等于物理 generation。有效子集明确 partial；完整资格仍按原必需范围判失败，不能缩分母 |
| P06/P08：补证与重复导出 | 固定原件和应用调用次数，对同 raw 留存初次判定，再添加范围匹配的有效 proof 重新派生；以错 binary/epoch 的 proof 作负例 | 原 raw 与初次报告 SHA 不变，新视图引用 proof 和旧输入身份；无应用重放。导出和 SQL 只准展示具备该结论全部前提的字段/edge，未满足源边界的 counter 间隔不得冒充源操作耗时 |
| P01/P09：阶段与成本证据 | 每后端分别登记设计 A/B/C/D 的结果及证据路径，指出新增/复用/仍缺部件 | A/B 不冒充 P01；C 仍满足完整 P01；D 满足最终合同。以实际修改范围说明成本，不用工期承诺、代码行数或假目标注册声称新增芯片已容易适配 |

设计中“无需公共层新增厂商分支”通过代码走查加三后端真实消费验证，不要求通用 schema 永远不变。公共版本变化必须说明不可表达的新事实、兼容策略及已有后端回归；合理扩展不算失败。共同消费者可以按明确的 event semantic/clock 资格处理数据，不能把异构细节抹成最小公共指标。

新增型号尚未提供时，不要求伪造硬件正例。兼容条件和错误组合可用合同 fixture 验证，但具体 timer/epoch、发布、实际最终编译边界及动态复用能力，只能由相应真实设备证据授予。最终三个额外代码 reviewer 必须同时检查本节的复用边界；这轮设计评审不替代它们。

### 8.6 本轮设计更新对应的执行用例

对应设计 §8.11，复用现有 P/E 与开发样本，不另加资格算子数量。以下是待执行判定，不是已通过结果；设计合理性由独立设计评审判断，设备可行性由真实运行证明。

| 对应项 | 具体操作 | 必须观察到什么 |
| --- | --- | --- |
| P03：自动边界落地 | 公开 API 捕获运行时 K 的有依赖算术循环和 load/compute/store；保存实际 binary、IR、反汇编和 raw；改变 K 而不改 binary | 自动 site 的入口/出口及目标指令在最终对象中有可核对关系，动态次数与 runtime K 对应；数值/输入/canary/调用次数正确，无额外完成 barrier。手工调用探针、版本常量或 marker PC 不代替自动样本 |
| P03/P10：多函数机器映射 | 对实际包含 helper/callee 的编译对象检查代码段、函数符号、非零起点、counter 与 caller；缺符号/错范围用合同负例补充 | 文本反汇编、结构化输出、嵌入 debug 与实际对象身份一致；不按最近 PC 或名字前缀猜归属。只有工具实际支持时才做该工具路径，后端可用自己的等价真实对象证明，不强制三家使用 nvdisasm |
| P06：因果校准的范围 | 单独运行实际有因果顺序的校准样本，训练/独立保留轮次分开；另构造错误比例、过期窗口、端点误差与矛盾区间负例 | offset 界与保留轮次一致；getter/尺度/误差和比较范围另有依据。有限样本一致不是普遍硬件误差上界；不把 tick GCD 当分辨率保证，不把 offset 界当 ns/全局 epoch 资格。不能把校准同步注入用户 kernel |
| P06/P08：时间解释的分辨能力 | 在已核验 clock proof 下，用两个端点不确定界重叠的真实样本或明确标注的合同 fixture，对照可分辨样本 | 可分辨范围内才报确定先后/重叠；不可分辨时保 slice 与误差说明及逻辑依赖，不生造确定的关系。fixture 不能证明设备时钟精度 |
| P02/P09：部件独立复用 | 对三后端逐一追踪公开入口到各实际部件，记录 transport/decoder/clock/mapper 各自的复用条件和调用者 | 无需为一个部件变化重写完整链；无需逐算子适配；不存在仅为满足表格建立的空继承层。新语义引起的合理公共修改保版本理由及回归，不硬判失败 |
| P01/P09：按依赖推进 | 为每后端最小纵向样本分别标注 boundary/publish/clock/mechanism/export 的实际证据和未满足项 | 最小输入的失败优先修复，不用扩大矩阵掩盖；A/B 阶段不能填 P01/C 通过，三后端及完整资格门槛不改变 |

验收报告沿用既有证据索引和 live 工程记录。每项给源码/安装身份、最小命令、终态、实际原件与结论范围；不新增一套重复的“已完成”状态文件。实际没有实现、没有运行或只能得到部分证据的项明确保留未验证，不以本轮设计评审结论补齐。

## 9. 成功判定

只有普通算子真实完成、时间正确、异步解释正确、Perfetto 真导入并可读、独立新数学通过、回归/安装/适配边界 P01–P10/三个独立最终审阅闭环、Git与进程收尾全部成立，才能完成 goal。

多几个 timestamp、一个能打开的文件、一组 source count 或漂亮示意截图均不等价于这些条件。时钟未知、某后端缺内部区间、异步关系只能猜、真实 UI 没验等情况属于未完成项，不能把验收降级成旧 usability 标准。
