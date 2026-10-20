# R087 GCU State 地址观察：有限只读建议

**可以有界接纳地址位作为记录数据；不能仅放宽 trunc/lshr/store，或把它们的 State 来源删掉。** 最小 sound 做法是为实际 IR 建一个封闭的地址观察用途证明：State 指针只经当前真实的低/高32位投影，保存到已识别的独立本地记录区，最后只由已核 byte-copy 发布；没有从这些 payload 位再获得写地址或交给未知解释者的路径。这个有限 producer/transform 证据可以与原 State writer checker 组合，**不需要完整 IPA、全部 scalar ISA 或再跑数学**。

本报告是建议，未审到修复实现、未授 profile State 资格。观察 detailed-profiler/candidate HEAD `14f9d68218895156752544a6e9ae1726c286d3dc`；checker 仍为 SHA `7aeadcab3ecb2e6e64f37fb86d8479cf88f3400de7cd5d5d33dc998810e2102e`。请求 GPT-6.1-Sol/xhigh；实际 resolved 型号/effort 未暴露，unknown。只读实际保留源码/收据及stdlib文本核查，未执行/import产品、checker、测试、SDK或SSH，未读peer。未重审ordinary32或其它whole门。

## 实际触发，不是由函数名猜 logger 行为

已读 `run083/preflight/gcu-profile-State-receipts-v1` 的v2实际翻译、v3 rows/runner。109条登记中84条停在 `Unmodeled State instruction`，25条先停在旧 `state_unique_logical_index_pass` 字段名；28个已保留LLVM翻译约5.19MB。旧checker `:173–176` 对load切断数据来源，`:253–262` 又把所有State相关store/未支持整数投影当escape，因此这次是**有限qualification工具未建模实际观察路径**，不是已确认设备写回错误。

代表性实际输入为 `profile-State-v2/output/d9131cd5fc24b2a9c6f593e5d79328a27e9276f8466ac8b4958440eee17b7120/functions.ll`，SHA `3f1c786b25e5855a79e97a9ea1da4c7648f7937d91d7fcc7570ed4708ef4d9ec`：

- `:2093–2095`：原State `%4` 经ptrtoint、program偏移、inttoptr形成 `%1416`。
- `:2165–2168`：`%1470=ptrtoint %1416 to i64`，随后 `trunc i64→i32` 取低字，`lshr i64,32` 再trunc取高字。
- `:2212/:2215`：这两个i32值写到 `%13` 的GEP位置；`:65` 确认 `%13=tops_get_local_memory()`。不是向 `%1416` 写数据。
- 原State读取/写回仍真实存在，如 `:2132` 的Pad source与 `:2787/:2940` 的State destination；不能将它们和地址记录一起删除。
- `:3133–3137`：记录区经 `tops_memcpy_async(context, hidden %5-derived destination, local %13-derived source, 65568 bytes)` 发布并wait。这个具体方向/长度和真实参数角色才是可复用的byte-copy证据，名称“logger”本身不是证明。

对28份文本作不执行checker的SSA依赖文本核查，State相关新增结果只有 `trunc`112处、`lshr`56处，地址位作为i32数据的store共112处；其余仍是原ptrtoint/add/inttoptr/GEP。未因此断言全部内存用途已安全或授28份资格。

另读 `run087/preflight/gcu-State-fields-poll-v1.json`：原25条使用 `state_count_passed` 的cohort经实际字段适配/对象关联后补9个不同翻译，25条均同样停在State地址trunc，partitioned0；controller return0只说明诊断枚举完成，不是State门通过。这份poll SHA `66728b86d5929346eb700ef83faa22dbff161190b1e8395ec4cde65a3ab65b80`。原字段名是兼容读取问题，不替代物理writer证明。

## 最小处理边界

建议保留旧State pointer/address建模，另外识别**仅用于观察的整数投影分支**：

1. 只接纳当前实际形态 `ptrtoint ptr→i64` 后的 `trunc i64→i32`，以及 `lshr i64,32→trunc i64→i32`；逐SSA use检查全部消费者。当前不需要把任意integer算术、phi/select或未知call都加入允许集合。原ptrtoint/add/inttoptr生成真正State写地址的路径照旧检查；同一个地址可同时用于合法搬运和观察。
2. **不能清掉 provenance**：投影值仍标为State地址位。若投影SSA还有未接纳用途，例如重组/转换为指针、作为GEP offset、控制未知写路径或交给未知callee，保持unverified。无需求出ASLR后的实际地址数值来验证trunc/lshr的纯数据角色。
3. 仅 plain i32 payload store 可成为观察终点，且目标必须是实际独立本地record区。不能用“目的root不是State”代替证明：空roots、未知pointer-return、loaded pointer、phi别名或仅依赖变量名都不够。直接pointer store继续拒绝。
4. **保存后仍要闭合内存用途**：记录payload可能被scalar/vector/pointer load、memcpy搬走，或被接收其指针的callee读取。对可能重叠的用途，要么沿有限数据/搬运关系继续保地址位来源，要么直接拒绝。未知alias或未知callee不做IPA，拒绝即可。仅支持当前必要的已核纯byte-copy方向；它搬的是数据，不把payload解释成指针，目标仍须绑定独立hidden trace allocation及实际ABI。

第4条是不能省的部分。现有 `roots(load)=空` 会在允许store后遗忘保存位。即使继续拒绝简单的 `load→inttoptr`，也不能漏掉 `load→整数重组/减otherBase→GEP otherFormal→store`，或 `unknown(ptr ring)` 在callee中恢复State写者。只保证“未见直接store ptr”不足以排除它们。

## 更省工的实现选择：有限 actual producer／transform 证书

**可以不用扩建内存解释器。** 在本批实际输出上核一个有限记录区/producer合同，再让checker仅对证书覆盖的观察指令作例外。建议证书至少绑定 actual LLVM SHA、State formal、已核producer/规则版本、ring root与record范围、terminal copy方向及其对象/ABI身份，包含：

- 所有State-address投影的SSA use集合都在上述闭包内；profile所有原State使用/实际写回仍接受现有扫描，不能只找几个预期store就放过其余State逃逸。
- 新记录控制流在原State操作前后重汇合，不增加、删除、重复或绕过原State写回；原State address/guard/descriptor cone保持，或直接由旧checker继续验证。可以忽略与State无关的数学与logger计数值，不要求整函数或指令次序相同。
- 对实际record payload区没有重新解释地址的readback/unknown消费者。固定header、单独counter、State临时区若以实际地址范围证明不重叠，可以排除；不能把整个local base所有load都当成读取了payload，也不能因它们同为local就一概忽略。上述代表输入的record发布区为 `[local,local+65568)`，counter在 `local+66048`，State临时区起点 `local+66560`；其它输入须按其实际布局读取，不硬编码这三个数字当通用定理。
- 仅允许实际已核SDK数据搬运向独立hidden trace发布；未知方向、目的State/未知别名、复制到随后被解释的其它temporary均不在此证书内。trace指针须由实际入口/owned allocation连接，不能按参数名或“最后一个参数”猜。

这可以是少量已识别logger生成模式的actual-IR检查/有限变换对照，不必做通用地址taint、全函数IPA或全SDK证明。producer源码的意图/哈希**单独**不够；证书须核本次实际输出，不能用另一版本template替它背书。若选择保留投影值并做有限store/load taint，也可以，但范围更大，并非本次必需。

这里没有新增源UB容量或完整记录器安全验收门；只核允许此State来源进入memory后，为防漏State写者所必需的用途/别名连接。现有raw guard/所有者及SDKbyte-copy合同可复用。

## 少量有区分力的验证

保留旧普通32和已存在pointer escape负例；新例只需覆盖新增允许边界，不做LLVM语法笛卡尔积：

| 例子 | 应有结果 |
| --- | --- |
| 实际低/高字记录到独立ring、已核DMA发布，同时保留原合法State写回 | 正例；State counts与原数学extent一致，观察不增加writer |
| 投影值除记录外还被重组/inttoptr并产生额外写回 | 拒绝；不能因另有合法观察用途便移除来源 |
| low/high位存local后经load（含一个volatile/别名形式）读回，重组后再作写指针 | 拒绝；防memory laundering |
| 保存位load后不用inttoptr，而经other formal的GEP offset形成State别名再写 | 拒绝；防仅检查inttoptr的漏洞 |
| 保存后把ring/payload别名交给unknown callee | 拒绝；不能假定callee只是logger |
| 将terminal copy改成State/未知目的，或先复制到另一temporary再恢复写地址 | 拒绝；防复制绕过观察闭包 |

若plain destination存在State/非State混合alias，继续沿旧未知别名负例拒绝；不必另加一套全alias测试。root修复后只需normal/-O这些有限例与现有已翻译输入、按原key去重的CPU适用性复验；37个已产生翻译可复用，不要求再跑translator、设备数学、TP/UI。应保留原109失败/25字段诊断，新增派生closure；新实现出现其它具体unsupported时如实留未证。

**当前判定：修复方向可有限且sound，不需要扩大验收门；现有材料仍不足以授profile State通过。** 只有地址观察闭包/实际transform证据及修复后原登记适用性终态到位，才关闭对应State范围；ordinary32保持原已闭结论，whole仍open。
