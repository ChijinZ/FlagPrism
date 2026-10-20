# NVIDIA ordinary pipeline：有限 buffer-generation / preservation 复核

请求配置 GPT-6.1-Sol / xhigh；resolved serving 配置未暴露，unknown。本席独立读取原件、资格工具源码和直接收据，没有阅读其它席 review，没有运行产品、测试、编译、SDK、设备、数学或 SQL，没有改产品。一次尝试本机 `docker exec` 只读原 JSON 因无 docker.sock 立即失败，没有容器动作；随后直接读取 root 从既有 Docker 取回的完整原 native JSON。

**结论：本次补齐的 ordinary slot/source 来源，结合已核 R073 native、R074 非空 future-group 和 R075 MMA-word/generation 结果，足以关闭这组既有 ordinary/default/真正 sparse、runtime K=3/7 的有限 buffer-generation 与关键阶段保持关系。未发现本范围的具体矛盾或需新增的必要关系。** 该结论是对所列实际对象的有限证据连接，不是 whole-goal 签字，不授硬件 overlap、engine busy、source-exclusive cost 或任意其它对象的流水资格。

## 原件身份链

| 原件/收据 | SHA-256 / 身份 |
| --- | --- |
| R082 `nvidia-ordinary-slot-source-v1.json` | 容器 JSON SHA `acf93d2949ba88c7600f7b2c2e776156921c5efed05e49c987943a18f5248524`；实际 `text.encode()` SHA `767dca47ea53e34aa11f2f2bce7e96fa4eea2b40f53d27139facee0ee7e76d55` |
| R083 `preflight/nvidia-ordinary-native-v1.json` | 15,646 B；SHA `623a7d8b35593c422b7cc0deea13657f5b47aeb0e10a05242dce162dad01cae9`，与 R073/R074/R075 同一原 disassembly |
| R073 pipeline object inventory | SHA `861f706f59aada4f4217eec0f3ca533011b4481eb2cc338f04e1512a780e3d4c`；ordinary compiled hash `57fee66060cdb11bf3963e81517a4fb1d138663bbbb54a7f2745854916abad39` |
| ordinary CUBIN | `76d2bd463b479eeb70eae1d86c6e14f6689c2c699f7ff174f0eae4e83ceb5956` |
| default CUBIN / binary_id | `585258452a4b8c4fab16a4cc94f0e57211fc787cc51255e0e7e898f724474c72` / `0dc7aa816e50a2ed7ba67b59fa3468588b7eb557579ecb0a3830c14a98ea593d` |
| sparse CUBIN / binary_id | `782fc33b19c48d5280ac25de9fbc0c64bf1d1bf806ddee2ded69df6fb036cbd9` / `0e0272e41d4a786d97f67e0f06e16daae29b4371512e0b36145fc9b801c56c3f` |

R073 inventory 从实际 ordinary 数学记录的 compiled hash 定位唯一缓存 CUBIN，并核 metadata/CUBIN SHA；profile 对象从各自 capture artifact 定位。R074 `pipeline-relations-v2/output/result.json` 的输入 ledger 同时绑定上述完整 PTX 和 ordinary native SHA，故新取回文本不是另一次编译或相似算子的替代。R073 native result SHA 为 `6cef62b7745e63b2471a1eed02a51f45fb5f414dd27bf7842b79c800fdf2bf9f`。

已实际读取 R082 notes，但以下结论由全文独立核对，不以 notes 的结论代替来源。

## ordinary 两槽与真实 source iteration

1. PTX 第159–175行：current selector r133 从 -1 开始，每轮加1、>1回0，轮 i 使用 `i % 2`；第253–262行将该 selector 乘2048加共享 base，供两个 B-side transposed ldmatrix 使用。两个 A-side shared loads 使用固定 `base + 4096` 的独立 staging 区。
2. prologue 第85/105行分别 copy 到 r20、r20+2048，各有自己的 commit。第251/252行的 wait_group1 + CTA publication barrier 位于本轮 shared load 之前。因此本轮要消费的 B generation 已等待并发布，后一个 committed group仍可合法未完成。
3. r134 从1开始，第277–279行同样加1、wrap，首轮写槽0，之后与 current selector 同相。第289行已有 reuse CTA barrier 在 shared loads 之后、第295行 body async overwrite 之前。**覆盖的是刚消费完的同一物理槽，用来保存 i+2，而不是改写尚待下一轮消费的另一槽。**
4. B source r132 从 `r12 | 4096` 开始；r12 为 `(tid.x >> 2 & 31) * 64`，最大1984，故该 OR 在此确为加4096。prologue tile0/1 的 source index 分别为 r12、r12+2048；body source 为 r12+4096+i*2048，并乘2加同一 rd1。每轮增加2048 elements，即32个K行×64列，确为 tile i+2；column/lane偏移未换域。
5. rd42/rd43 分别每轮加1/32，p15 使用 `i < ceil(K/32)-2`，另有 p26 的 source K-row及 p1 column-program mask。因此末两轮仍可 commit，但其 source-valid payload 为0；不能将这些空组当非空 future-tile 证据。

以上不是仅 PTX 层的推定。完整 ordinary native 的最终 lowering 给出相同角色：

- `0x600` 初始化 UR13=1，`0x620` 初始化 UR14=-1；`0x940..0x970` 递推 current UR14，并构造 `UR11 = shared_base + UR14*0x800`；`0x990..0x9c0` 递推 overwrite UR13。两者首轮均0、随后0/1交替。
- `0xa70/0xa80` 的 B LDSM 从 `[R25+UR11]`、`[R8+UR11]` 读取，R25/R8 是 thread lane permutation；`0xba0/0xbb0` 构造 overwrite `[R32 + UR13*0x800]`，`0xbf0` 实际 LDGSTS使用该地址。R32 是与 prologue相同的 shared base/lane写偏移。
- `0x580` 的 R3 含 source初始+0x1000 elements；`0xb70/0xb90` 形成其两字节 global source地址；`0xc40` 每轮加0x800 elements。与PTX的 i+2 source递推一致。
- native两个 prologue LDGSTS 为 `0x390/0x3f0`，dest间隔0x800，各跟 LDGDEPBAR；本轮 `0xa40` 为 `DEPBAR.LE SB0,1`，`0xa50` publication BAR，四个 LDSM（A/B）在该 cut之后；`0xaf0` reuse BAR 在全部本轮 shared loads 之后、`0xbf0` overwrite之前。最终 `0xc70` 的 wait0位于退出循环后，不是每轮新增全排空。

## 与 default/sparse 的实际 native / raw 连接

下表 PC 用十进制，与原 R073/R075 JSON 一致。每行 publication wait均为 SB0,1；body copy之后都有 LDGDEPBAR；最终 wait0在循环外。

| 实际对象 | publication wait / BAR | A LDSM | B LDSM | 原 reuse BAR | body copy |
| --- | --- | --- | --- | --- | --- |
| ordinary | 2624 / 2640 | 2656, 2752 | 2672, 2688 | 2800 | 3056 |
| default | 4432 / 4464 | 4528, 4576 | 4624, 4672 | 4912 | 5200 |
| sparse | 3840 / 3872 | 3936, 3984 | 4032, 4080 | 4288 | 4576 |

R075实际 `final-suite-v1/output/matrix/result.json`（SHA `6799fce589ee233f7c791b8ab028233b8dd0592674f0ab525f5240bca6a38ff1`）将每条 HMMA 的4个 A word、2个 B word经最终 native reaching definitions连到上述 LDSM，并将 default/sparse各 K3/K7、program0/3 的实际动态 load occurrence连到 fresh raw byte generation，共 **960个动态 input-word binding**。每个 load的整个模型footprint属于一个generation，且满足 completion / publication早于该load；不是凭两处相近PC猜同一代。

ordinary 的四条 HMMA在2704、2736、2944、3072；后两条仍消费先前 LDSM取得的寄存器word。特别是3072虽在copy3056之后，但它的 B words来自2688、A words来自2752，全部在reuse BAR2800之前已读出。因此copy覆盖已消费shared槽不等于破坏当前MMA输入。default/sparse的四条HMMA均位于各自matrix组内、body copy前；此issue排列差异不构成“缺失shared generation关系”，也没有以相同issue顺序作新增验收门。

R074 `pipeline-relations-v2/output/result.json`（SHA `499a48e4afb0e3dab2dc3046d5e9c501df1ffed0330ffb97ef55adf95b12650c`）与R075对应case的 invocation/raw SHA一致。以program0为例，default首轮matrix seq22消费B async-1、A sync-15，B完成seq16、publication17、读取20/21；同时另槽async-2已commit seq5，在该prefix尚未观察完成，source-valid unique bytes=2048。第二轮消费async-2/另一同步A代，并允许已写回槽0的async-3作为后续代。sparse对应首轮seq13、完成7、publication8、读取11/12，具有相同两槽角色。

K3每个对象两program合计4个非空future prefix，K7合计12个；最后一个消费prefix没有非空future witness，未缩分母或以空payload补证。R074还保留wait-limit改为0的full-drain反例：copy/commit/site数量不变，但所有非空future witness消失并被拒绝。由此能区分“保留非空预取机会”与“仅保留相同指令数/空commit”。

R075的26个copy/branch native register cones未见当前函数 matrix/clock-result通往这些根的显式寄存器依赖。已实际读 runner：它预期 input诊断step返回1以保留三个predicate entry-root未解析，再核26个cone的局部遍历完整；外层terminal0不是把该step伪报0。`input_values_fully_verified=false`、`through_memory_dependencies_verified=false`等原字段保留。本结论使用其有限“未新增显式结果寄存器依赖”事实，不把它外推为任意别名或隐藏机器资源证明。

## 范围、剩余与交付判断

本实际样本的关键关系现在可闭合为：两prologue generation → wait1/publication → 当前A/B shared消费及MMA word输入 → 原reuse cut → 同槽写i+2；另槽非空future group可保留到当前matrix prefix。default与真正sparse的原raw保持该关系，没有新增每轮wait0来消灭它。**有限的buffer-generation、关键消费/覆盖依赖及非空预取机会保持可以接受；本席不再为此条实际关系列额外必需补证。**

这不意味着测得物理执行同时性、MMA completion latency、完整硬件调度一致或源码独占耗时。原收据的 broad `ordinary_preservation_verified=false` / `hardware_overlap_verified=false`未改，本报告给的是所列补证后的有限关系结论，不授权批量翻转产品字段。无需新增ISA证明器、相同issue-order或hidden-scoreboard门，也无需重跑设备/数学/SQL。

已读：R082全文PTX/notes及嵌入SHA；R083完整ordinary native；R073原inventory/native收据和其生成脚本；R074原prefix/generation/result、full-drain逻辑与terminal；R075 matrix/input/cone结果、terminal/steps、对应资格工具及runner。未独立重新执行decoder或checker，未重新取得default/sparse完整native原件，沿用其已绑定的R073最终native摘录和R075实际native/raw验证收据；没有扩审其它backend、其它kernel或其它whole门。

未确认本范围的新 blocker/major/minor；optional无新增工程要求。整个goal是否完成仍取决于其它原mandatory门，本报告不作whole-goal签字。
