# R082 GCU State SDK ABI：有限只读语义核查

**结论：已有实际库定义与 launcher 足以确定本批所需的 getter、搬运参数和有限窗口检查方法；尚不能授 State writer 资格。** 必须再对实际 State caller 的地址/CFG/参与条件作有限枚举。完整库 v3 已补齐初版缺少的 State tail/deslice 路径；不需要新数学、TP/UI、全 ISA 或全 SDK 解释器。

请求 GPT-6.1-Sol/xhigh，工具未暴露实际 resolved 型号/effort，记 unknown。仅 stdlib/Git 读保留数据及源码；没有 import/执行产品、测试、SDK或SSH，没有读 peer 或改产品。本报告非 whole-goal 签字。

## 身份与当前证据范围

- 原 SDK builtin SHA `fa9d850080258f7cfd3acbdccfdb3485007b9b87c3c5ed34ab187dacbb52944a`。R081 `original-compile-v2/output/result.json` 保原登记32份 ordinary（24 primary＋8 runtime-K）、24个不同编译对象，32 bound；本席逐24份对象收据核 `whole_binary_identical=true` 且 produced/original fatbin SHA相同。没有设备数学重放，`state_writer_qualified=false` 保留正确。
- `gcu-original-State-inputs-v1.json` 的32份实际 LLIR/TTIR 文本，已逐项重算 SHA并与原 row.artifacts 核同，零不符。`num_warps`为4/8，各16行。不是另写一份相似的数学源说明原 binary。
- 初读 R079 v2 库文本 SHA `ed5545318799081aec1c77d62ee6980cb5a3b1e1beb0deaa2a11ffede52124b9`；后补 R082 `enflame-State-primitives-source-v1.json`（实际 extraction v3）文本 SHA `d52b889366fe0e06a21049958f10eb59f2e826444a6c1352b06038a1912153aa`，包含六种1D/2D slice/deslice/slice_deslice、memcpy及getters。下文行号使用该v3文本。

## Getter、launch 与 writer guard

`tops_get_thread_id :24–46` 的参数0/1/2分别直读 `llvm.dtu.read.tid.x/y/z`；`tops_get_block_id :49–71` 同样直读 `bid.x/y/z`；其它维度值返回0。它们没有把 SIPINFO、vector lane 或warp内部编号拼成program ID。

实际 backend源码 SHA `ccd500895c64cf19330071a3da156c113d001391c064beb1a458b93ea82f71e8` 的 launcher `:475–478`：gcu500分支才乘128；本批 **gcu300** 走 `topsModuleLaunchKernel(function,gridX,gridY,gridZ,num_warps,1,1,...)`。因此本批 caller 的物理线程枚举域为 `tid.x=0..num_warps-1, tid.y=z=0`，block坐标按原grid各轴；不能再乘32、12或128。保留LLIR的 `ttg.threads-per-warp=1` 与此一致，但实际launch和getter才是这里的连接依据。

**没有可借用的通用“隐藏 thread0 写回 guard”。** 已读搬运函数在构造command后提交，没有按thread ID选唯一writer的代码；deslice1的 `barrier.param(3)` 读数没有参与writer分支。context模式、地址类别、MD寄存器/通知路径也不能直接当作thread0谓词。q03-s0-c0的实际唯一候选来自caller：LLIR `:120` 取得tid.x，`:460` 与0比较，`:498–509` 的State GM写回仅在该条件真时提交；外部q03 wrapper原样转发State参数。其它向量/矩阵caller可以由多个PU分别写不重叠区域，不能一律强制thread0。

## 参数、字节范围和裁剪

以下按实际定义中零起点参数编号重命名；E是原DTE context，D/S是destination/source，尺寸和offset均为i32。公式限定本批需检查的**非负、有效窗口**；不把库中的signed/reverse编码推广为已审通用能力。

| 函数 / 位置 | 实际参数与有效写范围 |
|---|---|
| `tops_memcpy_async :89–595` | `(E,D,S,nbytes)`；D/S分别为参数1/2。参数3直接写入command长度字段，并以zext记录到context，**单位bytes**，没有乘4或尾部32B取整。写区间为D起的nbytes。State作source的是读取，不能计writer；E是context，不能误认作payload指针。 |
| `tops_deslice_async_1_si32 :601–1116` | `(E,D,Dlen,S,Slen,d)`。先算 destination `D+4*d`；`L=min(Slen,Dlen-d)`，command字节长度为`4*L`。source从S开始。它没有`max(L,0)`；不能把非法d/负L当安全no-op。 |
| `tops_slice_deslice_async_1_si32 :1713–2390` | `(E,D,Dlen,S,Slen,s,Lreq,d)`。先将D指针前移`4*d`，有效`L=min(Lreq,Dlen-d)`；DTE源shape为Slen、源start为s，destination shape为Dlen-d、start0。安全窗口下写`D+4*(d+i)`，读`S+4*(s+i)`，`0≤i<L`。不能只核destination，再默认source足够。 |
| `tops_deslice_async_2_si32 :1119–1710` | `(E,D,D0,D1,S,S0,S1,d0,d1)`。将两端完整shape、destination起点及4-byte元素大小编码进rank2 DTE；定义中**没有**与1D同样的显式destination `min`。本批有限检查应核`d0+S0≤D0,d1+S1≤D1`，不凭函数名假定自动裁剪越界。非负有效窗口的写地址为`D+4*((d0+i)*D1+d1+j)`，`i<S0,j<S1`；source按S1行宽读。 |
| `tops_slice_deslice_async_2_si32 :2393–3092` | `(E,D,D0,D1,S,S0,S1,s0,s1,R,C,d0,d1)`。库显式算`R'=min(R,D0-d0)`、`C'=min(C,D1-d1)`；DTE记录source shape/start、destination shape/start、4-byte元素及R'/C'。有效窗口下读`S+4*((s0+i)*S1+s1+j)`，写`D+4*((d0+i)*D1+d1+j)`，`i<R',j<C'`。没有统一的非负归零，也不能以该min证明source端可读范围。 |

1D/2D command形状/offset的若干字段掩为24bit；指针拆成低32＋高16bit。mask不是越界拒绝。当前有限规则应证明原已用参数在可表示范围内、实际整数运算无溢出/错误符号解释，不能先截断再声称数学地址正确。其它内存类别分支包含 `llvm.assume`，也不是运行时安全校验。无需因此扩成全部地址空间或任意ISA证明。

`tops_slice_async_1/2_si32 :3095/:3613` 是源侧裁剪的相关读取路径，不能与上述destination写回混同；它们的source窗口/padding在需要连接原State读数时按实际调用核。库最终将payload指针/shape/offset写进DTE command，并提交该command；context/MMIO/通知字段中的store不能作为原State store计数。

## 实际 caller 暴露的必要范围

初版三种搬运root不足以覆盖原件。q01-s0-c0的State来自internal `%arg9`，经`%198`成为global State基址；末尾既有 `tops_deslice_async_1_si32 :453`，也有 `tops_slice_deslice_async_1_si32 :445`。最后program起点768、有效1元素、PU0的32元素chunk走后者的tail分支，不能当死代码忽略。矩阵原件还出现2D deslice。后补v3已经给出这些定义，**该库源码覆盖缺口已补齐**，不继续要求重复提取；未来checker仍必须实际支持/核该可达分支。

q03的State路径可作为scalar正例：原State参数加`4*block_id(0)`，真实readback DMA→wait→本地i32加1→mfence→tid.x==0条件下的4-byte GM写回→wait。这个具体可读路径支持检查方向，不代替其余caller枚举或授该批资格。

## State 分片最小 caller 检查条件

1. 从原TTIR的State参数/ABI，经外部入口到internal函数，追实际State pointer根及两端地址；分开State read、GM write和本地temporary/context。找全可达的直接store与搬运call；不按算子名、int32后缀或文本最近定义选择State写入。未知别名/未知State写原语保未证。
2. 绑定每个原row的LLIR/对象、builtin版本、grid、num_warps和State extent；在上述真实block/PU域上，求实际CFG路径及typed整数address/predicate cone。处理block参数/phi、前驱及helper结果；State写回不能被循环重复、被分支绕过后仍计作一次，也不能把条件false的定义当已覆盖旧值。只需State相关cone，不解释浮点数学或全schedule。
3. 对每个实际提交按上表解码D/S、shape、offset、真实有效长度。核source窗口、destination窗口与4-byte单位；不得将声明shape当实际有效tail，或将helper中的min当负值保护。无写条件要由真实caller guard或已明确的原语语义证明，不能因长度≤0就在checker里自行归零。
4. 按实际byte区间累计所有program/PU/可达写call，要求每个原oracle应更新的State元素恰一writer、尾部/guard无写；向量多个PU合法分片允许多writer，但同元素重叠不能靠最终State==1放行。State用值/完成的连接复用原math/host-once，并仅核该路径已有DTE wait、local更新及mfence；不添加同步补证明。
5. 把结果写成原登记范围的逐对象/逐调用覆盖收据。可复用相同对象及规则，仍绑定不同runtime-K调用；未识别分支/primitive/地址算式明确未证。checker自身按原合同以有限正例、重叠/错单位/坏tail/未知路径等负例在normal/-O同判，不重采数学。

当前**剩余是实际caller checker及其上述范围的覆盖/拒绝收据**，不是要求再跑设备或扩ISA。新q03 opaqueLLVM翻译可作为分析入口；只去GPU module外壳且保操作行，不能叫vendor final LLVM，也不由此授native schedule/time boundary。没有在本次范围确认实际State写入错误；尚不授GCU State或whole通过。

输入索引SHA256：R079库v2 JSON `ea7516629acdbcc4a0673d60baba872fc30dd7724b6db647b8d1365396e9b824`；R082完整库v3 JSON `c0402f6582ceb1915ac6e3b1588c8bdd3de95ea883acb8edc144b6fd1129f44b`；launcher/compiler JSON `f6f169336bbda8cd80a68e0995ba56b613b127b78d77490795935f28a311398e`；32原State输入JSON `47d33069de447673a373cc1a2492b4df0fd3d92a2520777b3f8d3f38710400ef`；R081 whole binding result `1f2ee78f4cbbda4cd22d0bcb1016dea870e3b916773848891f8a472882efb185`。

## Pad source/destination 角色的有限补读

已读同fa9库的 `run082/preflight/enflame-State-primitives-source-v2.json`（实际 extraction v4），重算文本 SHA `2c1799b3a316d4a08bd66aa6649dfc224087e07c13f7e001250dc395bc56d566`，JSON SHA `2a4ab6f51427d2b53e59c6d836432b3827e299efd581c800275b0ba9516c688f`。下列index均零起点，arity包含context：

| 实际函数 | 参数角色与直接依据 |
|---|---|
| `tops_slice_pad_async_1_si32 :4245–4932` | 共8参数：`(E,D,Dlen,S,Slen,s,L,pad)`。**D是index1，S是index3**。`:4283–4285` 将S转换成i32指针并前移s；`:4381–4388` 把该指针记为source、D记为destination；`:4549–4566` 分别写入DTE source字段6/7、destination字段8/9。末项pad为i32填充值，`:4595` 写pad控制字段，不是payload地址。 |
| `tops_slice_pad_async_2_si32 :4935–5650` | 共12参数：`(E,D,D0,D1,S,S0,S1,s0,s1,R,C,pad)`。**D是index1，S是index4**。`:5078–5082` 记录source=S、destination=D；`:5262–5279` 将S写DTE source字段6/7、D写destination字段8/9；`:5311` 的末项pad同样为填充值。 |

库在两种Pad路径上构造读取source窗口、写入destination及其padding的DTE command；未发现对source payload的写回。普通有效非负窗口下，1D有效读取长度为 `min(L,Slen-s,Dlen)`，2D各轴相应取请求长度、source剩余量与destination尺寸的min；仍没有把非法负长度统一归零。padding扩大的是destination填充范围，不将source变成writer。

因此在State、context和destination原有独立分配前提下，**只允许State出现在Pad source（1D index3 / arity8，2D index4 / arity12），且拒绝State destination，可把这些调用分类为State GM读取，不计State GM writer**。State若同时出现在D/E等位置，不能因它也在source位置就跳过。这个结论只确认实际SDK的payload角色，不代替新checker的实现/最终正反例复核，不额外增加源UB容量或全SDK门；本次仍不授State资格。
