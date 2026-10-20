# R095 compiler：LLVM region / runtime-loop 有限审阅 v1

结论：本轮规则确实检查选中路径、fresh begin tuple、共享end的forwarding和完整record；不是只数marker。但发现 **2个confirmed major**：必要值锥中undef/poison/不可信opaque值可经affine抵消伪造正确tuple；额外reset回边可被误当runtime loop的initial入口。建议只修这两个明确路径并补同版最小反例，不需要全LLVM/ISA、whole-goal或新数学矩阵。

## 身份与范围

冻结 **734e0968046326e8de3ee00f2b312106d84b55b3**。沿原请求GPT-6.1-Sol / xhigh，resolved型号/effort未暴露，记unknown。未读peer；未执行产品、代码/import、测试、SDK、设备、数学、TP/UI或SSH。

实际读 `gcu_llvm_regions.py` 全文、self-contained CLI tests全文、`gcu_timeline.py`新接线、旧typed-index输入合同；读取 `run095/preflight/regions-receipts-v1/runs/regions-v3` terminal/result/15normal/-O日志及format-v4源码身份/hooks。仅写本报告，不修改实现。

冻结SHA：

- helper **47c8f3261af9ae757c8ad8ef46c3e021fc958c0eba45506695807ae96ce49af8**；
- tests **76d006c11de4d52144c46a249d537fb5dbf66d61e5a912916384cdf75b0b1384**。

## 已成立的有限检查

- `_Index` 核schema/SSA唯一性、operand引用、branch arity及forwarded类型；用真实typed successor表，不从文本猜CFG。
- entry-invariant selector与false-selector全entry可达集合分开，不能只看紧邻guard就认begin必然selected。
- begin须含本site counter/identity两marker及实际三word tuple；选中body各可行分支逐路径走到end，cycle/过长路径明确拒绝。
- shared end靠每条path的实际forwarded site/begin/identity核record字段，不要求end debug site等于动态owner。完整32word stores、magic/seal、sequence/capacity、饱和count update和normal/full合流均被检查，不能只取好前缀。
- runtime-loop另核header中的entry-invariant trip、0初值、+1 latch和选中iteration的begin/end覆盖；失败只令loop unverified，不自动取消独立bracket事实。
- 这些输出保native_schedule/source_exclusive/source_iteration_id资格false。原producer/SDK验证、native family及真实raw关系仍是独立输入，不把LLVM facts当最终native schedule。

这些设计方向成立，下面两个具体路径仍会给出过强checked结果。

## Confirmed major M1：undef/poison或不可信opaque值可抵消为已证tuple

**位置：** `gcu_llvm_regions.py:170–222`，特别178/181/222的opaque atom及192–201的affine add/sub/mul；最终在468–483肯定record tuple。

**触发：** 在合法runtime/straight fixture的entry加入：

```mlir
%u = llvm.mlir.undef : i32
%fakezero = llvm.sub %u, %u : i32
%wrongsite = llvm.add %fakezero, %c7 : i32
```

把record word1的store由 `%c7` 换成 `%wrongsite`，其它32stores、clock、capacity与CFG全保留。定义放entry，不触发tail对unknown effect的拒绝。

`value(%u)` 被当成固定 `ssa:ID` 原子，sub两项抵消为literal0，wrongsite遂被认成literal7。LLVM undef每次use可取不同值；poison更不能按这种抵消证明为常量。对未建模的可能undef/poison scalar结果同样不能靠稳定atom消掉其不确定性。SDK verifier接受typed IR，不会替本规则建立所有必要值definedness。

**后果：** site字段实际不确定或poison，规则却可返回 `llvm_observer_boundary_checked`，破坏它声称已核的fresh site/begin/end→同record关联；类似抵消还可能影响loop初值/步长/选择等必要等式。这不是要求解释全部数学指令，而是所用肯定等式自身不健全。未声称旧两actual对象已经包含此故障。

**最小建议：** 必要value cone直接拒known undef/poison，并区分可作为稳定输入的值与不能用于肯定等式的unknown/可能poison结果；不得让后者经抵消/模乘0变成已证constant。可按当前有限cast/affine/clock/count形态保守拒绝，无需全LLVM definedness解释器。

**最少验证：** 用上述entry表达式改变word1的真实typed fixture，要求命中值锥/tuple原因拒绝；再给poison或未知scalar结果抵消的同类小反例，合法fresh tuple继续通过。由root在已有Docker执行，normal/-O同版；本席只做静态推理，未运行该反例。root已确认并拟修，未冻结/执行前不按修后通过。

## Confirmed major M2：header可达的reset回边被当成initial入口

**位置：** `gcu_llvm_regions.py:688–698,729–743`。

**最小触发：** 原runtime fixture仅把末尾：

```mlir
^exit:
  llvm.return
```

改为：

```mlir
^exit:
  llvm.br ^header(%c0 : i32)
```

这是可typed索引的另一条control edge。它与当前第16例“header false successor直接改成latch”不同：header false target仍是独立exit block。

**实际逻辑推理：**

1. 正常latch仍forward induction+1，685–687通过。
2. 遍历header predecessors时，除正常latch外，entry和新增exit都forward0，于是exit也被689–698登记成合法initial block。
3. iteration_blocks不包含header false分支后的exit，因此730的直接target检查通过。
4. external-entry检查只覆盖iteration_blocks，不检查额外回到header的这条reset边。

故仍可报 `llvm_runtime_iteration_checked`，实际上存在第二条非+1回边，trip结束后会重置并重启，甚至永不返回。给定有限header/trip/0+1/latch结构的结论不成立；source_iteration_id=false并不能使这条遗漏的backedge消失。每一次局部begin/end bracket仍可能独立成立，修复不应混成“所有source区间都错误”。

**最小建议：** 在已有有界CFG内，拒绝从header/iteration或其exit continuation可达的non-latch“initial” predecessor；或明确检查退出延续不得回到header/iteration。支持其它真实嵌套形态时可具体unverified，不必新建通用natural-loop/ISA证明器。

**最少验证：** 新增上述exit→header(0)精确negative，要求region本身可以仍checked、loop必须unverified并给reset/reentry理由；保现有真正entry0、latch+1、直接exit正例。无需新应用或设备实验。本席未执行。

## Confirmed blocker / minor

没有另加confirmed blocker或minor。以上是本LLVM规则的具体false-pass，不推翻已闭原数学、State writer、pipeline或计时器资格。

## 已读证据与必要 verification gaps

- regions-v3 terminal0，**0.465588395s**；15normal/15-O均OK，0.084s/0.081s。旧两capture原SHA分别 **ef003113276cbc65997bb5e54f12554d81c584a71204bb7ca70ee702f85b6648** / **3c7a6282434a1241a4922f4a3b090130900773270d712ebd065643bc4fd538d0**，结果为11/13及10/13地区checked，其余“No original source body/caller”保unverified；runtime source39有有限loop正例。
- 该实际v3 helper SHA **b771b360bd9d75dd7be9306485e3547471c27e997ac7be83614e909f1020fd9a**，与冻结47c8…不同，不能把旧15项日志称为最后entryschema/cast/exit第16例已执行。
- format-v4 terminal0，**2.268418439s**，两轮ruff/yapf/check-ast全0；登记helper/tests SHA与734e096吻合并有AST等价。它证明格式冻结，不代替新增semantic case或修复M1/M2后的执行。
- 正常wheel/公开入口及最终16项还在途；更不能用旧freeze正常安装结果关闭新修复。最少后续是matching修复源码、上述两条negative加原定向正反例、两旧actual对象重读与正常包身份/接线；不重跑数学/SDK/TPUI矩阵。
- native schedule、完整source region、exclusive cost、source iteration_id仍未授。它们不是为本条LLVM中间事实新增的更强门；原最终family组合另按其真实条件判断。

## Optional 与有限结论

没有新增重构建议。保 `body_refs` 的实际原操作/位置列表及每site未证原因；不要把“某source关联body/member在此LLVM bracket里”的结果改写成该source所有指令的独占耗时。

本次审阅支持有限结构规则路线和已观察正例的范围，但**M1/M2修复及同版semantic验证之前不建议关闭此delta**。只需上述具体修补，不应扩大成全SSA/ISA/SDK/whole重审。

## 追加：M1/M2源码与定向CPU验证闭合（4ae3561）

本节更新上文两项缺陷的当前状态，保留原始触发与旧证据。实际读取最终提交 **4ae3561735a186a5ad2352ac901a168a93517709** 的两文件修复、`delta-receipts-v5.tgz` 中 regions-v5 与 format-v6 的terminal/result/完整定向日志、格式化输入与输出，以及实际执行runner `check_regions_v4.py`；未执行任何实现、测试、SDK或设备。resolved型号/effort仍unknown。

最终formatted helper SHA **5c99a53f1ca21b3447046a64b49e970d17e52f647159535ad2d5dfc09598eab6**，tests SHA **bea3838c80c0a9372bbccb5ad97ab9d757581247c04dde2a90dd90ea71bdbfe5**，均与candidate及format-v6输出归档逐字节核同。实际source-loaded helper SHA为 **43ef5863187fa20e6eefb1bef44650d03d52525f3debf8e099a432cf25b26e22**；format输入中的helper即此SHA，tests为 **eeb4276385a2fc08e25a16f4afe4c0c067cef88f2230d283760e75b06222b7e8**。format-v6 runner明确比较前后Python AST；其script SHA **58a43cb60fbdb4148ccf279c2be20a46007405c637fd72a64b8ae4ffb265fa1f** 与terminal一致，terminal0 / **2.317988758s**，两轮ruff/yapf/check-ast全0。故本次以实际执行源码及有凭证的AST等价格式冻结闭合，未将formatted bytes冒称另行执行。

**M1已在本有限值锥范围关闭。** helper现第197–200行在所需表达式递归中明确拒 `llvm.mlir.undef` / `llvm.mlir.poison` / `llvm.poison`；第29–39、42–56行分别阻止opaque `ssa:`项经模乘归零或add/sub抵消消失，不能再借unknown→常量制造合法site字段。最终tests第347–377行通过真实native CLI建立合法undef/poison typed索引，再要求必要值锥拒绝，并独立覆盖opaque抵消及乘0。该修补针对本规则使用的肯定等式，未声称一般LLVM poison/definedness解释完备。

**M2已在本有限loop family范围关闭。** helper第646–655行由实际continuation遍历有界后继；第717–719行拒绝从该集合可达的non-latch initial predecessor，因而exit→header(0)不再能混入initial入口。第656–665行还在“begin不可再达”的情形检查continuation不得重复body/end/record，避免把无fresh begin的重录误报为无循环。最终tests第379–412行保留准确reset反例和continuation→end反例；这是已有有限CFG规则的补全，没有增加通用ISA或循环证明门。

实际regions-v5 terminal0 / **0.615696408s**，timeout40s；runner SHA **640938f9a75e6c806d36b72682197ac7010979398d0e8f2880a5ba7a1c620997** 与terminal一致。旧734e096 helper先执行三个新增方法，完整日志确有 **4 failures**（undef/poison两个subtest、reset回边、无fresh begin重录），展示原false-pass；随后新helper **20 normal / 20 -O** 均OK（0.103s / 0.104s），包含opaque算术反例。旧两实际capture及structure SHA仍与上文相同，11/13、10/13区域checked不变，未证source-body项仍明确unverified；第一个实际对象site11的有限runtime loop仍checked，header41/latch47/exit48、唯一initial40，source_iteration_id资格仍false。

**当前confirmed缺陷状态：M1、M2均已完成源码修复及matching定向CPU闭合；本追加未发现这两处修复的新具体false-pass。** 不重新授予native schedule、source-exclusive cost、source iteration_id或whole-goal资格。必要verification gap只保留**修复版4ae3561的正常安装/公开接线身份闭环**；归档中的旧normal-install-v1不作为新修复安装证据，进行中的v2亦不提前算通过。无新增optional要求。

## 追加：修复版正常安装与公共入口闭合

已只读核 `run095/preflight/installed-receipts-v1` 的normal-install-v3/public-regions-v1原收据，以及 `post-receipts-v2/runs/public-post-v1` 的小补查收据；两份index分别32/5项的size/SHA均重新核同。未重审实现、未运行产品/测试/SDK/设备。

- **matching安装gap关闭。** normal-install-v3 terminal0 / **55.300713808s**，source **4ae3561735a186a5ad2352ac901a168a93517709**，wheel SHA **a115e6ceb2ecb1e5794709b18642728e149138255e7d2e5a2156d603c6a083cc**；503个installed members与正常wheel逐字节核同。实际runner SHA **75bd4b3ca0ce40bfa7e58d6981576b317f71671d417788b7e2a95e7224667a4d** 与terminal及输入归档一致；该输入中helper/tests正是本报告上一节的5c99a53f…/bea3838c…最终formatted版本。guard ABI、installed imports和所有步骤均0。此版本复用已核且未变的native/core，不声称本轮重新构建SDK/native。
- installed定向验证 **39 bindings normal/-O** 均过（0.18s/0.31s），**20 native-CLI规则 normal/-O** 均OK（0.105s/0.108s）；-O仅保预期pytest assertion warning。此前v2 launcher指向不存在的r087/v2、未启动worker，不用它冒称安装成功；正常闭合依据是v3。
- installed reader只读重检两旧capture，capture/fatbin/ELF链仍与原件匹配，原bytes/metadata未改；LLVM区域分别 **11/13、10/13**，有限loop **1/0**，未证项仍保留。该结果与point级native reader/relative-field计数分母不同，不把其合并为完整source/native资格。
- public-regions-v1实际普通2/profile2数学、input、guards、host-once均通过，产生22/20 events；controller最终仍如实为 **terminal1 / 23.901551122s**，stderr明确为验收脚本把相对 `captures/...json` 直接当CWD路径读取导致FileNotFoundError。原成功状态JSON写在此后置检查前，不能覆盖该terminal失败。
- 后续 **public-post-v1 terminal0 / 0.715718437s**，用同installed interpreter及公共 `load_capture(root, relative_path)` 读取上述已生成的两capture，不重放应用。runner SHA **55f429236fc3efd51aa08c18d73ff36bf6720cf45295de54157c4228124fd59d** 与terminal一致；结果给出22/20 events、区域11/13与10/13、loop1/0。其绑定的原public-math result SHA **7ec0d40c042c6a2923b6e262572155dc67068533f755614033ef2cc4be94a669** 与实际原文件核同。`post-receipts-v1`误收了旧目录，不作补查证据；本结论只用已实际读取的v2正确归档。

因此，**本R095 delta的M1/M2源码、定向验证、正常安装及默认公共接线范围均已闭合**，不再保留上一节的matching install gap。此结论仍限typed LLVM region/runtime-loop中间事实，不授native/source family组合、source-exclusive cost、source iteration_id或whole-goal资格，也未新增更强门。

