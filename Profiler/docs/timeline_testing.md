# 内部时间线测试与真实算子验收

状态：**测试设计，尚未执行**。配套 [技术设计](timeline_design.md) 与根目录 `timeline_goal_prompt.md`。本文件所有算子/干预是待运行场景，不是已有性能结果；不预填时间、重叠率或加速比。

## 1. 分开验证四件事

1. 算子与应用没有被破坏：数值、输入、tail/canary、请求调用次数、side effect。
2. 时间数据是真的：实际设备 getter、原始 bytes、实际编译位置、时间单位、调用/主体/配对/损失。
3. 解释没有越界：issue 不是 engine busy，completion observation 不是精确硬件 end，静态边不冒充动态 flow。
4. Perfetto 真的可用：用实际导入器和 UI 打开本次真算子 trace，看到可解释的内部结构，而不是只校验 JSON/protobuf 能解码。

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
| E09 | 错 frequency、缺 clock proof、跨 SM/epoch 错配、错误单位、超大 tick | 转换 fail-closed；保原 bytes，不把 cycles 填入 ns |
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

每后端至少挑六份当前实际 trace，包含两个不同算法、一个异步案例、cold/warm、不同 program 或 occurrence。至少三个跨后端的异步案例分别在本机真实 Perfetto UI 打开；不能只用自写网页替代 Perfetto。

每份操作与截图：

1. 上传/打开本次 `.pftrace`，overview 出现内部多 track，不是只有 kernel bar。
2. zoom 到一个真实循环，能看见重复的 region/wait 等 slice；显示单位和采集范围。
3. 点一个 slice，详情能读源码位置、主体、时间、semantic、clock/误差、调用/原始证据 ID。
4. 点一个有证据的 flow，定位 producer/consumer；静态候选不冒充真实 arrow。
5. 看首/末 program 或两 actor，明确哪些同域可比较；不能从不同域归零图推断重叠。
6. 从 bundle 定位源 snapshot/原始记录；browser 前后所有 bundle 文件 hash 不变。
7. 至少三张实际截图：整体、局部循环/流水、slice/flow 详情。截图索引给 trace SHA、UI 版本和选择事件 ID，不用手工重绘波形。

输出：源码/安装/native/compiler/SDK pin；测试注册表；首次结果与修复后结果；每组合 math/raw/time/clock/source/Perfetto gate；真实 `.pftrace`、bundle/原始 bytes、SQL、UI截图和解释；受控案例；已知限制；三个独立最终代码审阅报告及闭环。大型产物放持久路径/hash 索引，Git 只提交可公开的代码/测试/文档/小fixture/必要索引，不提交 SDK 私有库、凭据或巨型 trace。

## 9. 成功判定

只有普通算子真实完成、时间正确、异步解释正确、Perfetto 真导入并可读、独立新数学通过、回归/安装/三个独立最终审阅闭环、Git与进程收尾全部成立，才能完成 goal。

多几个 timestamp、一个能打开的文件、一组 source count 或漂亮示意截图均不等价于这些条件。时钟未知、某后端缺内部区间、异步关系只能猜、真实 UI 没验等情况属于未完成项，不能把验收降级成旧 usability 标准。
