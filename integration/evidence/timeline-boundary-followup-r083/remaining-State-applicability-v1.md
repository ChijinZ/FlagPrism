# R083 剩余 profile／补二 State 检查适用性

**无需每个调用或每个文件名重跑 checker。** 每条原登记调用须有身份与适用性记录；相同实际输入、State ABI、实际 launch/actor 域、State extent及所需标量绑定，可以共享一次已经完成的有限分析。整份输入不同也可有限复用已证明等价的 State cone，但现有 Asc/GCU 材料尚未建立这样的统一映射，不能直接把 ordinary32 推广给 profile／q07/q08。本项是剩余覆盖证据，不是已确认数学或产品故障。

配置请求 GPT-6.1-Sol/xhigh，实际 resolved 型号/effort 未暴露，记 unknown。只读本地源码、JSON与archive，用stdlib核身份/分母；未 import/运行产品、checker、测试或SDK，未连接设备、Docker或SSH，未读其它席报告。未重做已闭 ordinary32，不审当前 GCU final boundary／NV pipeline，不作 whole-goal 签字。

## 已有方法与实际分母

直接读取 R078 `check_nvidia_writers_v9.py`、实际 `writers-v9/output/{ordinary-checks,profile-checks,result}.json` 及 terminal。runner `:20–27` 的缓存 key 是 **PTX SHA、State 形参位置、num_warps×32、实际grid、State元素数**；每条调用另核原数学、compiler artifacts、冻结ordinary对应关系和host-once。实际40条ordinary＋118条profile均pass，但只分析72个key（ordinary32个、profile40个）。118行与其原登记列表逐file/SHA相等；不是把summary计数当覆盖证据。

已按 R059 trace-index 的 `source_capture_file/source_capture_sha256` 去重核分母，并另读 R062 的60条registration及archive中的60份实际math报告。这里的“保留对象”含历史首轮失败；不把它们升级为当前成功资格，也不把SQL通过当State证明。

| 后端 | 已闭State范围 | 最小当前剩余登记 | 若延续R078的完整历史保留覆盖 |
| --- | --- | --- | --- |
| NVIDIA | ordinary40＝原32＋补二8；profile118，含补二36份历史/修复capture | **无新增State检查**。原补二、当前对应profile已在上述收据中 | 原118已覆盖；无需重跑或再造分母 |
| Ascend | 原ordinary32，R081派生闭合 | **补二ordinary8＋当前profile96**：R062替代60＋未受该修复影响36 | 原R059 profile96＋R062新60＝156个保留capture，分别登记历史/替代关系，非156个新数学调用 |
| GCU | 原ordinary32，R082派生闭合 | **补二ordinary8＋当前profile96**：13个affected替代＋其余83 | R059保留109＝original-six72＋supplement-first24＋affected13 |

补二ordinary的8个ID对两家均为 `q07/q08 × s0/s1 × c0/c1`。每个逻辑组合原有cold/warm1/warm2，不增加新阶段。

- Asc当前96的具体分解：q01–q04的48条及q08的12条用R062实际替代；q05/q06的24条及q07的12条复用原登记。历史被替代60条保留原资格状态。R062的60份math对象仅有 **16个不同npubin／bcmlir**（q01/q02各4，q03/q04各2，q08为4），已经说明按调用机械重做60次分析没有必要；尚不能据此宣称16个State key，因为还须核实际State ABI、launch及所用输入。
- GCU affected13具体为q05全部12个cold/warm调用，加 `q07-s1-c1-cold`。原bundle CPU预算恢复只改无损存储/派生表示，不能另算一批State数学或要求再检查完全相同的compiler bytes。

## 可直接复用什么

1. **已核SDK/主体规则直接复用。** Asc沿R081实际同版meta_op、1D/2D wrapper、atomic0、source/destination descriptor、scalar/no-op/DMA byte范围及AIV/mixed actor ABI；GCU沿R082 fa9库的getter、memcpy、1D/2D slice/deslice/Pad和四个实际整数helper。无需为每个对象重复提取同字节库、重新证明相同ABI，亦无需新ISA解释器。
2. **精确相同输入共享分析。** 先绑定原math/host-once、actual capture、原对象与实际编译输入；由真实TTIR/入口转发确定State形参。以已验证输入/函数SHA、State ABI、实际actor/launch/grid、State extent和State cone所需的实际标量绑定作key，附checker/SDK规则版本。一个key检查一次，其余行引用该receipt并核key一致。cold/warm、文件路径、不同compiled_hash标签本身不需要重新枚举；反过来，同binary也不能忽略不同grid/extent。
3. **actor key取真实ABI。** GCU300为真实 `(num_warps,1,1)`；Asc取实际arch、aiv/mix、bs_task_type/subblock主体、auto_blockify和实际grid参数，不机械加入一个不存在的warp/lane维度。Asc两份logical num_warps不同、但实际输入和主体ABI相同的对象可共享，不能仅为config标签不同再强制分析。
4. **State cone相同可跨不同整体IR复用。** 仅在绑定各自真实编译对象后，对State pointer根、全部State使用/可能写回、地址与尺寸/stride、guard及相关CFG、可重复/可绕过性作有限比较；忽略SSA改名、debug/path、与State无关的浮点数学及已证无别名的logger写入。相同的字节写入函数及参与条件在相同actor域中产生相同分片，即可引用原partition，不要求完整LLVM、所有指令次序或整个数学函数相同。

最后一条是可选省工方式，**不要求新建通用cone规范化框架**。若有限等价比较不直接，直接对每个不同actual输入/launch key运行已有checker一次即可；不因可能复用而先扩充一套更大的证明系统。已有checker未改时，normal/-O正反例结论也可复用，无需对每个capture重复fixture suite。

## 必须保留的实际连接

profile改变插桩、hidden参数或SDK输入，不能仅凭“相同Python源码、数值正确、logger理论上不碰State”继承ordinary结果。应使用**实际写入SDK的profile输入**；若只保留普通/插桩前输入，需已有有限变换证据表明State根、相关CFG和写回保持，不能把它改称实际profile lowering。Asc的实际passive codegen LLVM、GCU的实际重写SDK输入/机械LLVM分析视图均沿已审方法使用；不要求把分析视图升级为vendor-final IR。

对象绑定可复用已有capture/compiler输入SHA及真实loaded对象链；只有某个不同输入缺少这条实际关联时，才对该distinct对象补必要CPU-only passive／逐byte重现证据。不是预先要求为全部profile重编。q07/q08也先看实际输入和State窗口；不能仅因是新数学就强制新SDK语义审计。

若新的实际descriptor仍落在已核helper路径及有效窗口内，复用其byte范围规则；若走到此前未适用的分支/尺寸/stride或新primitive，只补该具体路径的有限检查。不要把当前ordinary32 sidecar的硬编码计数、最大size256或已观测source stride当作任意后续对象自动通过的凭据，也不把那些观测值变成新的通用合同上限。未知State alias/写原语/参与条件继续unverified，不能静默丢弃。

## 精确最小下一步

1. **建一份只读适用性索引**：从原ordinary补二freeze、R059各stage/trace-inventory及R062替代60入口，记录上述每条当前调用；历史capture另标原stage和替代关系。逐行连接原math/host-once、input/config、actual对象/输入、State形参、actor/grid/extent与SDK身份。当前没有Asc/GCU统一State等价索引，distinct key数应记unknown，不推测为8、24或96。
2. **只处理未覆盖key**：相同key直接引用已有ordinary32或新代表的partition；确证同State cone则记录有限等价依据；其余不同key运行现有checker一次。若checker因某个真实新State操作拒绝，只保该具体缺项并作针对性修正/必要语义负例，不重做旧32，也不全量重采。
3. **派生范围明确的sidecar**：把每条当前profile/补二登记映射到代表receipt，保原false/失败记录不改；再更新该State覆盖范围。原数学、host-once、raw、预算、TP/UI沿原相同bytes收据复用。新的State资格不抹历史首轮失败，亦不授source/loop边界、pipeline保持或whole-goal通过。

现阶段可确认的是上述索引/适用性覆盖尚缺，**没有据此确认新的产品bug或原数学失效**。没有必要新数学、设备重放、TP/UI重跑，或对相同输入逐call重复分析。

主要可复核身份：R078实际runner SHA `bc187f969f5b8989a0c3e9ee5b7ffd2286c2ca60662f0499447a008b2025dc97`；R059压缩trace-index SHA `921cd412a8cc4160955b1764a1afe9b95c5d2ca6906991f9a8770b8a8ca6d6a8`；R062 registration-v2 SHA `a752d378eaf26e9acf22be6371ed9b4025a393b9c058069708b87fac43e502ed`。ABI依据为本席既有 `run081/review/ascend-state-ABI-v1.md`、`run082/review/gcu-State-ABI-v1.md` 与 `gcu-State-ordinary32-v1.md` 及其明确的实际SDK原件，未借用peer结论。
