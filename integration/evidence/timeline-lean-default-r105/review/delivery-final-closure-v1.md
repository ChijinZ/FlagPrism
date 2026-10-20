# R105 R3 whole delivery：最终有限收尾复核

**截至本版，未发现仍需产品实现的 confirmed blocker/major/minor。原 R075/R091 的 GCU/Ascend source/timing适用连接、State writer、预算 cohort、关键pipeline等具体缺口已经按原最小范围闭合；不再以optional static unknown或所有证书全绿追加门。** whole最终签署尚待本轮新数学全部终态、这些新资格trace的实际TP/SQL，以及最后证据/文档的exact Git和owned-job终态。下文保留这些具体待证项，不把21/24写成24/24。

配置请求沿用原独立 R3 GPT-6.1-Sol/xhigh；实际 resolved model/effort 未暴露，unknown。正式/candidate请求冻结 `244bd8c1bc67071b6ddf4eee7a62221fb0152b5a`，candidate已Git实读；产品行为冻结 `6e78f136214da74254211fa19b90a3f7b7353fa2`。6e78→244的runtime/build源diff为空。唯一当前工作区改动为请求的quickstart文档，另列如下。未读peer报告；没有执行产品/import/tests/SDK/远端/设备/TP/UI。仅复用自己已读且未变的原件/报告，针对影响范围读取Git、代码/文档和现有JSON/hash。不改实现或论文，只写本报告。

## 1. 已闭事项与真实边界

| 原必达项 | 本席实际闭环与当前口径 |
|---|---|
| 三后端公开默认CLI/API与适配边界 | 公开detail=timeline→各backend compiler/transport/decoder/clock/mechanism→共同validator/exporter均有真实安装和调用。真实SDK/target/ABI/cache身份、兼容拒绝与正常恢复，P02/P04–P10按原whole及受影响delta复用；不要求第四芯片或空框架。 |
| 独立数学的原kernel State writer | R078 NV actualPTX/编译对象ordinary40+profile118；R081–089 Asc/GCU reviewed SDK、actual actor/descriptor/address/guard及whole-object绑定，双方ordinary40/current96闭合。logger writer与原State writer已区分。不是保留旧false就继续判该门未做。 |
| GCU原失败预算及E01/owner/reader | R076原36超预算cohort逐case无损闭环；R077三家10call/2binary、真实raw/隔离/reader/reexport/预算、R076 child与原R3五finding已修/安装/实际或对应故障回归闭合。当前6e78对原Asc E01 owned副本CPU重处理10call/2binary，66,815,281B前后不变、raw/pftrace/counter/dependency不变；没有数学重放或新SDK执行。 |
| GCU C1/V4 source/loop/native family | R098原required plan与fresh33/current96实际typed+原raw连接；R103 reviewed reader/body/tuple/loop、DTE issue/addmm family与同SDK/resource/binary适用范围；R105组合索引96case/33object/255observed/9未执行分支与原件逐项0差异。原C1/V4 GCU项已闭；不再要求单独broadcast ISA、每纯算术op新证明、source-exclusive或busy。 |
| Asc原96 source/timing及当前通用MMA选区 | R103正常安装、原raw/selected-loop交叉；R104原96重算无unavailable；R105 facts按原冻结source SHA、actual table/selected carrier和原raw summary连接，96/96有≥2distinct positive source，q01/q02实际body重复、q03/q04reduce、q06 contraction、q08 reduction事实具备。旧q05/q07各12无MMA观察如实保partial。原registry未要求每trace独立MMA/store timer；R101修复回归与新q11/q12独立泛化另列，不移填旧raw，不把GCU固定epilogue行数组加为Asc门。见本席`ascend-source-timing-index-scope-v1.md`。 |
| 内部时间/专用async/clock及两个受控case | 原三后端真实getter/raw/范围匹配clock、NV shared-byte generation、GCU tag复用、Asc recurrence flags0/1；内部时间门与专用async门不同。C1真实干预与内部occurrence；C2普通/default/true-sparse关键publication/reuse/future关系及SDK原件按本席相应有限审计复用。没有从相同opcode数推preservation、从stages1推无future、从wait-return推exact hardware completion。NV独占性能/开销认证保持用户延期。 |
| 既有TP/SQL/UI及不可变原件 | 本席已核原1740 retained proof_key/result SHA/row/完整263stats，后续R062168、R0698、R07280、guard/dependency和R07760变化trace也有实际TP；未变trace/视图编码和原标准UI操作/截图/前后bundlehash可复用。1740含历史失败，不是当前合格调用分母；TP成功不消除旧qualification失败。 |
| 原首次失败、修复与独立性 | 原ordinary/profile eligible分母不删；曾用于修复的case均称回归，旧reserved-slot、capacity、budget、coverage和wrapper失败保留。旧24无MMA只保它实际未采内容；不是把optionalstatic的opaque/dup诊断叫runtimefailure，也不是把新数学事件塞回旧capture。 |

这些闭环引用本席R075/R091 whole和之后自己实际完成的有限报告/原件，尤其R105三个scope/index报告；无变化部分不再逐个重读SDK/全矩阵。engine busy、source-exclusive、全部SSA/ISA、源iteration_id及未知跨域epoch都不由本报告授予，也不是新的完成门。

## 2. 当前安装、公共命令与文档

当前Asc matching正常安装原件为 `phase-receipts-v1-recovered/runs/install-v1/output/result.json`，SHA `763d02c5388698af9890bcc3f5f9ab24478d3576acae4649338d962b574e589e`：6e78、450 matching members、wheel SHA `433c500d8d4ba66ad4e6ca613cd5c94723ed3006548028d61f73a5f0f88e5543`，未变native/compiler/recorder源核同复用。当前只是默认不自动生成额外static graphs的三行Python变更；没有假称重建未变C++。原GCU/NV正常build/install及真正改动工具的重建证据按各自原scope复用。

实际新q11 public命令的application-terminal argv为installed Python `-m flagtree.profiler.cli --backend cann --detail timeline --device 4 ... launch.py`，没有`-I`或源码热补丁。当前quickstart移除三backend公共应用命令的`-I`，与`cli.execute_as_main:199–213`逻辑一致：非isolated运行临时将应用脚本目录置于sys.path首位，finally恢复；`-I`则按其隔离语义不加入，可能阻止普通sibling模块导入。诊断/help和offline reexport继续用`-I`正确。该文档修正不需重跑数学。

quickstart所列collector `cupti/cann/enflame`、compiler环境变量、逻辑device、torch_npu导入顺序和三个source-build/normal-wheel链接均与现有实现相符；timeline轮子需要额外late/native工具而非Python替换。删除早期not-final措辞没有宣称所有资格位真：文档仍明确各capture资格、observer/counter/issue/wait/依赖边界、原件与重导历史、不把instrumented elapsed当ordinary收益。未发现本次文档/API/安装链的新具体缺陷。

## 3. 仍待直接收据的必要项

### V1 — 新q11/q12完整独立泛化终态及原资格结果

当前root报告21/24通过，最后q12-s1-c1原owned controller仍运行；本版不提前写24/24。本席已直接读8 ordinary math_pass，以及本地已回收的5组/15个profile完整rows，cold/warm身份、actual MMA、math/input/guard/hostonce、raw/source、预算与导出均按其原结果保留。未回收部分不以实时口头状态代实际最终aggregate和输入索引。

最小补项只收齐最后已授权任务和完整24原件/aggregate，逐原预登记8组×3、case/capture/binary/raw及受测6e78安装身份核同，保首失败/修复/未见口径。没有要求重采旧24或原96，也没有新的数学数量/结构门。

### V2 — 新资格trace的实际TP/SQL，不是旧UI重做

原 `Profiler/docs/timeline_testing.md` §7明确：“对所有正常资格 trace 用实际 Trace Processor 导入，保存退出码、SQL、输出和 importer stats。” 新q11/q12产生新的正常资格`.pftrace` bytes；旧1740和未变exporter的成功不能直接冒作这些新bytes已导入。

最少用原pinned TP/verifier处理新24的实际registered trace inventory，核原raw/ns、source/track/observer和完整stats；保verifier/输入/result身份与终态。已回收的15个capture均各6个standard traces；最终分母以真实inventory为准，不猜或为了方便删减。exact-input/result可以复用，同编码UI复用原覆盖；不需要新设备/数学、旧trace重复SQL、增加UI场景或改verifier门。新TP收据尚未在本版已读材料中提供，因此明确待证，不因这是最后一步就省略原合同。

### V3 — 最终证据/quickstart版本的exact Git与owned终态

`preflight/git-delivery-v1.json`已证244bd8c canonical/candidate/remote相同、两树当时clean、正确detailed-profiler且非force。本次实读的唯一未提交quickstart及新结果/索引/报告尚须最终归档提交；不能用旧clean证明新最终版本已push。

收齐最终提交和其source/docs/evidence范围，fetch/祖先/remote精确HEAD/clean收据；确认最后profile/TP及自有控制器已终态、没有遗留自有设备或browser任务。不要重启已经运行的q12 controller。三席最终处置由root汇总，本席不读peer或代签其它席。只需对新文档/证据差异有限追加，不重审无变化产品。

## 4. 本版交付判定

Confirmed blocker/major/minor：无新增；未发现必须新增实现才能解决的默认体验、安装、错误时间线/flow或原件破坏问题。必要verification gaps仅V1–V3所列实际收据；optional无新增工作要求。旧R075-V1 State、旧预算和旧pipeline不再开放。

原goal §8的1/3/5/6在已述真实范围可接受，4的原展示层已闭但新增资格bytes受V2约束，2待V1，7/8待V3最终处置/精确交付。**本版仍不签whole complete；V1–V3直接收据齐备且无新实质代码变化后，可仅作最后有限追加，不再启动新框架/旧矩阵/可选证书扩展。**
