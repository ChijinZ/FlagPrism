# R070 independent limited runtime delta review

Freeze：`132650989f25088eaaf87c0cae1796c0b67ae20d`，相对 `7f8fdf508768cfaa9fcb82e7dfb6eaed65ca1212`。仅两项 delta：`timeline_nvidia_late_addresses.py`（SHA256 `72214e58be3758aef4dabd43e39912e58f3d889e6074111c32b9c0623a3ec3d6`）和新测试（`4d24f2fddb8258fdecba132f16d091e65dfb6a9b1aa4cd61df91fdbe2cb0e1af`）。安装输入归档中两文件 SHA 与 freeze 一致。收尾时 HEAD 已前进至 `a71d32f`，且这两文件出现后续未冻结修改；本报告不读取或覆盖那些修改，结论只针对上述 freeze。

**结论：未发现该有限 delta 的 confirmed blocker、major 或 minor。** 从实际 count 用途反向检查 live definitions、允许被完全覆盖的物理寄存器临时值，符合这里的地址/计数语义；未发现由此绕过活跃 partial/predicated 写检查的具体路径。此结论不等于 installed 资格：目前实际打开的安装v1收据是 terminal/1、assemble/1、result=null，必须与源码加载检查成功分开。也不授 whole goal、source cost、ordinary pipeline 或调度保持资格。

本次只读源、git diff、既有收据与输入归档；未 import/运行 checker、测试、SDK、设备或性能任务，不读取其它 review 意见。唯一写入为本报告。

## 代码与误放行风险核对

- **实际用途及两word：** `timeline_nvidia_late_addresses.py:358` 从已识别的 header count store 与参与实际记录地址推导的 count LEA low-PC 开始。`_live_count_definitions`（`:422`）分别追溯 counter 的两个32位word；沿用 `_ReachingWords` 的保守 CFG predecessor 遍历。没有父定义的路径拒绝；predicated 写保留该写及未执行路径，不被当成无条件 kill；只有无条件完整覆盖才能截断此前无关临时值。
- **循环自增：** 到达 `IADD.64 counter,counter,...` 后继续以该指令的旧输入为用途回溯，因而不把 loop-carried self-add 当作一个无来源叶子，也不靠观察到的 tick 值或本次运行路径挑选定义。visited/worklist 和底层 definition cache 均有现有状态预算。每个 live PC 最后仍进入 `_count_write_inventory`（`:397`），只接受无条件、以准确counter pair起始的 MOV.64 零/字面值与合法正 batch self-add；部分word写、其它输入寄存器、未知writer或predicated live写仍拒绝。
- **LEA与counter用途的配对没有放松：** 原 `_Wide.pair` 仍核对 low/high operands、carry、shift、输入寄存器、low/high之间无覆写及直线执行；因此用 low-PC 建立 counter use 没有放弃 high-word验证。header 地址仍不得依赖 mutable count epoch。batch字段地址/descriptor与native字段value-flow检查未在此 delta 删除。
- **首batch字面赋值：** `_check_batch_control`（`:465`）仍要求每一完整store batch与唯一、数值匹配的count update处于一个无歧义的single-entry straight region，实际live update清单与完整source batches必须一一对应。新首batch规则（`:501`）从该region最早点向所有CFG前驱回溯，拒绝任何既有record field store；回边到自身batch也会碰到其store而拒绝。因此允许字面赋值前的无关寄存器临时值，并没有把“已写记录后重设零基batch”当作初始记录。
- **append检查保留：** counter-relative batch的high地址必须先于update；从地址生成到update之间不得改counter pair。未关联的live update、缺初始化或多初始化仍拒绝。固定零基batch与append batch的模式/数量匹配没有改成只看最终header数值。
- **原件与恢复：** delta不改native/ABI、plan/layout、raw decoder、clock来源/位宽/单位、owner/readback/释放路径。现有 `load_record_ordinal_bindings` 仍核对binary identity、raw SHA与complete状态，逐batch检查site序列、首batch只在ordinal0、四字段的实际offset/stride。`load_native_boundary_report`及header-origin路径重新调用地址推导；地址与origin报告的implementation digests包含此模块。旧原件不需迁移，当前规则重算出的派生证明有新的实现身份。未知模式的inspect wrapper仍返回unverified和false权限，而不借旧成功状态直接放行。
- **权限范围：** 本模块输出仍明确 `absolute_raw_slot_binding_verified=False`、`time_flows_qualified=False`。相对raw ordinal绑定不等于绝对allocation/program/thread来源，也不等于完整source边界或硬件完成时间。本 delta 没有改这些消费者的资格字段。

## 实际打开的证据

`preflight/count-suite-poll-v3.json` controller terminal/0。`count-suite-input-v3.json` 的run.py明确从文件替换加载新addresses模块到旧安装环境，再运行测试；它是CPU源码加载检查，不能写成新wheel已安装验证。与freeze源/测试比较，仅有格式差异，未见逻辑差异。

- 四份原实际capture来自既有 default/sparse 的 K3/K7 retained timelines；本次没有重新执行或编译数学应用。两个binary分别为 `aae4821d…` 与 `e4448ced…`。每组两capture的raw-bound batch occurrence rows分别1280/2304（不是新增数学次数，也不是record总数）。
- default每份得到4个live count writes，未排除额外物理写；sparse每份也得到4个合法live count writes，并明确排除PC1456、1552这两处已被覆盖的无关物理寄存器写。新测试要求至少一个实际寄存器复用case，否则失败。
- 四份各拒绝5类CPU反例，共20项：live high-word overwrite、predicated live add、different add input、repeated initial batch、initial after other batch。前三类验证live/inventory检查，后两类向CFG添加有害前驱后验证首batch拒绝；它们是有限CPU corruption fixtures，不冒称设备发生过这些错误。
- `device_executed=False`、`application_replayed=False`、source regions与ordinary pipeline qualification false均在结果中保留。
- `preflight/native-install-poll-v1.json` 的结构是 `terminal/result/steps/stderr`；实际terminal/1，assemble step/1，result=null。它只证明本次安装尝试失败，不能继承旧安装或源码加载的成功。安装runner和归档也已读；未执行或重试它们。

## Verification gaps（非 confirmed code defects）

1. **当前安装包回归尚无成功证据。** 本次已打开的v1失败收据没有说明新wheel已安装，normal/-O的installed count suite及existing-address regression亦不能从该失败继承。最小补项是既定新wheel正常安装、matching import后，对相同保留原件运行已准备好的有限CPU检查；无需重放应用或扩大设备/性能矩阵。后续新收据应另列，保留v1失败。
2. **五类反例是针对子检查的有限覆盖。** 前三项修改native body并重建live/inventory结果，后两项向predecessor graph加边并调用batch control；不是重新封装、重签整个machine map的端到端恶意binary试验。现有静态检查及原件正例支持本次窄修复，未据此要求新增通用机器码证明器或旧矩阵。若以后声称更广泛CFG/writer家族已验证，需有相应有限case；本报告没有给该资格。

Optional：新测试可像现有 `p01_nvidia_late_addresses.py` 一样，显式核对每份原件目录前后hash，并对relative-binding/absolute/time-flow false作直接断言。当前源码路径是只读、权限字段未改变；此增强不构成当前confirmed defect。

已读完整两个delta文件，以及有关reaching words、CFG/destination、straight-path、native store、raw ordinal、digest与fresh recomputation调用路径；已读源码suite、安装v1及其输入。未读peer报告、未审后续未冻结修改、未执行installed或设备任务、未重开完整验收。
