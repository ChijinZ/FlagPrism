# R094 typed LLVM structure：有限 compiler review v1

结论：本增量能够用 typed MLIR 操作索引实际最终 SDK LLVM 的 SSA、block forwarding、callee 与 marker，已有两份真实旧输入正例；未授 native/source schedule 的范围是正确的。但发现 **2 个 confirmed major**：nested symbol table 下 caller 身份可能错联，以及 type 文本展开缺少构建前/累计预算。另有一个需最小 CLI 验证的 malformed forwarded-type admission 缺口，未冒称已复现。当前不建议把这两个确认问题留到消费者以后处理；修复可以限定现有 flat SDK 模式，不需完整 IPA/ISA 或 whole-goal 重审。

## 身份、实际阅读与限制

冻结 HEAD **90fe92853c3fe09c0abe6e1976f9c31fbc0aabe7**，读取时工作树 clean。沿原请求 GPT-6.1-Sol / xhigh；resolved 型号/effort 未暴露，记 unknown。未读 peer、未与其它 reviewer 商议；未运行代码、import、tests、编译、SDK、设备、数学、TP/UI 或 SSH。

实际读取 `GcuExecutionStructure.cpp` 全文、`GcuTimeline.h`、CLI main/CMake、`gcu_execution_structure.py` 六个 nativeCLI fixtures、Python binder和其tests、实际 parent patch接入点；读取 `run094/preflight/structure-receipts-v3` 的 matching源码、terminal、CLI normal/-O stdout及两真实输入结果，以及binding-format-v1的hooks结果。未重审原已闭pipeline，也未把结构索引当 source/loop 或 native顺序证明。

C++ matching源码SHA **a8a51a3bf65ff6041bc70edc32911b48c4dd2d74baa54e51879b1226d07a8c55**；本席cmp与执行归档一致。CLI测试SHA **3938c5b727108316dd101cbaee0c384e8ec893c7cd0dd56b4a12ec3abb77ce18**，binder `gcu_timeline.py` SHA **005a00b47f4f5735462bb339163f3d534f06fc104e2a4cf546428313d460310c**。

## 已成立的有限实现

- 先登记全部 block argument / operation result，再引用 operands；所选函数外的operand与successor拒绝。使用 `BranchOpInterface` 获取每条successor实际forwarded operand，而不是文本正则猜分支。produced operands或arity不匹配拒绝，未知有successor但无接口也拒绝。
- 保结果类型、block argument类型、integer位宽/常量、ICmp predicate、GEP indices/element type、callee与原location；宽于64位integer没有猜截断常量。
- 外部声明不作为defined body；选唯一marked body并允许实际wrapper存在。两个真实保留SDK LLVM分别有93/84 blocks、1603/1754 ops、46/48 markers、87/105 calls，均正常索引。
- Python hook核序列化LLVM输入SHA等于 `debug_execution_native_ir_sha256`，绑定manifest摘要与索引output摘要，再在fatbin阶段绑定实际ELF/fatbin/target；parent patch在实际SDK verifier返回的LLVM文本处调用。没有新source/native schedule资格，header与报告字段相容。

这些正面事实不能消除下面的具体反例。

## Confirmed major M1：nested symbol table 中 caller 按 leaf name 错联

**位置：** `Debugger/lib/Instrumentation/GcuExecutionStructure.cpp:25–49,160–163`。

**触发：** 全module递归walk会收集nested module内的LLVM functions，但caller判定仅比较 `call.getCallee() == function.getSymName()`。同名leaf symbol在不同symbol table中可以合法存在，selected function与call的真实callee并不因此相同。

最小合法形态：

```mlir
module {
  module @inner {
    llvm.func @body() {
      llvm.return loc("__flagprism_gcu_clock_v1__":7:1)
    }
  }
  llvm.func @body() { llvm.return }
  llvm.func @wrapper() {
    llvm.call @body() : () -> ()
    llvm.return
  }
}
```

唯一marked body是 `@inner::@body`。外层 `@wrapper` 的call实际解析到外层未marked `@body`，当前字符串比较却把wrapper登记成marked body的caller，且报告 `function="body"` 也丢失qualified identity。全部操作可保持typed/valid，不依赖畸形operand或任意native ISA。静态推理直接来自递归收集与leaf-name比较；本席未运行该fixture，未声称已经取得服务器stdout。

**后果：** 有限结构服务中的caller→observation body身份可能错误。source/native资格false防止它立刻变成时间证明，但并不使错误caller索引本身正确；后续自动lowering-family关联会以错误关系为输入。现有两个actual输入是flat模式，不据此判它们已经发生错联。

**最小修复：** 直接拒绝非当前顶层ModuleOp所属的defined functions/nested symbol tables，明确首版支持flat SDK module+wrapper，或对call用最近symbol table解析并比较实际Operation identity，输出无歧义qualified path。二选一即可，无需做IPA。

**最少验证：** 保原flat wrapper正例；新增上述同名shadowing反例，要求明确拒绝该不支持模块，或结果绝不能把wrapper归给inner body。由root在现有Docker执行 `gcu-timeline --execution-structure shadow.mlir shadow.json`，normal/-O CLI harness均核正确身份。

## Confirmed major M2：类型文本展开/重复复制在最终output限额前可失控

**位置：** `GcuExecutionStructure.cpp:67–72,78–80,90–92,131–132,169–174`；location同样是打印后才检查单项/累计大小。

**触发与推理：** 16MiB输入、8192blocks、100000ops，并不限制类型别名展开后的总字符数。MLIR type alias可在短输入中被许多SSA结果引用；`type.print(stream)` 每次独立打印完整类型文本，随后复制进JSON string，直到所有rows构建并序列化完才检查32MiB输出。

例如在input中定义一个约数KiB的LLVM literal struct alias，在成千上万条合法 `llvm.mlir.undef : !alias` 中复用。输入仍远小于16MiB且ops少于100000，result_types却可累计数十/数百MiB。更深的共享type-alias树可使**单次**展开也远大于输入；输入bytes预算不能替代有界展开。当前代码在这些分配/打印完成后才拒绝output，故并非“最多构建32MiB报告”。

**后果：** 正常公开结构服务或CLI可在有界输入内产生超预算内存/CPU工作，可能在到达明确budget错误之前被OOM/外层deadline打断。不是实际旧两LLVM的故障，也未实际制造大对象或运行OOM实验。

**最小修复：** 对待打印类型/位置先做有界表示或复杂度/展开量预检，并在逐字段/逐row构建前累计真实字符串/输出工作预算；缓存重复类型可以减少打印，但JSON重复复制仍需计入总量。单个type的打印工作也要有界，不能只把末尾size检查移到打印完一个巨型type之后。可以限定现有SDK使用的有界type形态，不需全LLVM语义解释器。

**最少验证：** 以共享type alias和重复SSA结果构造小输入的超输出预算负例，要求由明确budget原因提前拒绝；原两实际SDK输入保持成功。选可控大小，不跑会耗尽容器的大实验；对单type深层展开亦用限额较低的fixture核预算，不要求设备/新数学。

## Confirmed blocker / minor

无额外confirmed blocker或minor。M1/M2均是有限索引本身的工程问题，不以它们否定旧数学、raw、pipeline或其它已闭产品能力。

## 必要 verification gaps

### V1：parse关闭验证，forwarding只查arity，需最小核forwarded type拒绝

`GcuExecutionStructure.cpp:20–21` 使用 `ParserConfig(&context, false)`，没有显式verify；102–110只核produced count和target参数个数，未比较每个forwarded value与对应block argument的type。

最小待核：

```mlir
module {
  llvm.func @f(%x: i32) {
    llvm.br ^next(%x : i32)
  ^next(%y: i64):
    llvm.return
  }
}
```

若parser在关闭verify时接受该文本，当前提取逻辑会输出i32 value转发至i64 argument而返回 `typed_sdk_llvm_structure_indexed`。本席没有运行parser，因此**未将该具体CLI接受结果计为已复现confirmed**。实际正常路径在SDK verifier之后且有exact input绑定，其已验证前提可复用；这里不是要求另做全LLVM证明。

最少由root跑这一条CLI并确认：若接受，优先开启适用的MLIR验证，或补当前支持的block forwarding/type/terminator最小不变量检查；若SDK私有debug属性妨碍整module verifier，可限所选函数的必要结构，而不是静默接受错type。该负例应命中type/结构判据，不只意外触发其它parser错误。无需新SDK/device矩阵。

### V2：normal installed闭环尚未由本席所读收据覆盖

structure-v3 terminal0，**21.598509792s**，tool SHA **65029c34e39a3524aa41b0d37b3c5750f7585418173dc378a98e454586b1a7cb**；native build及6CLI normal/-O通过，两个actual输入SHA为 **6b8b2e1a95808ec6f924dac1324f449b44f5177e89f5d5e11de6ade3511eb593** / **acdeadcb66fe11896706b9d384e3d4a7dad22c3aafe8f00bd56ac321f71068e7**。binding-format-v1 ruff/yapf/check-ast两轮全0。上述范围是实际matching源码/native工具，不冒尚在途normalwheel已安装成功。

最少后续核修复冻结源码、新tool/normalwheel身份与实际finalLLVM→binary绑定的installed收据；producer/native SDK本体未变的部分复用，不要求重跑旧数学或全矩阵。source/native schedule字段继续false。

## Optional 与结论

无新增大框架/ISA建议。若选择首版flat-module限制，应在CLI错误中准确写明“不支持nested symbol tables”，避免把普通有效MLIR概括为错误IR。

当前可以肯定typed结构提取路线和两份actual输入可行；**建议先修M1/M2并执行上述最小negative，再关闭本delta**。V1根据最小parser结果处置，V2按实际normal安装终态补身份；本报告不是whole-goal票。
+

## c057552：原 M1 / M2 / V1 的有限修复复核

本追加只核原三项，不重开whole/已闭pipeline或其它代码。冻结 **c0575528418292c65eeccab4bd105b68bd000225**。实际只读源码diff、`structure-receipts-v4` matching源码/terminal/result/完整9CLI normal/-O日志与三个negative stderr，以及`binding-format-receipts-v2`终态、source SHA与hooks；未执行代码/SDK/设备/测试，未读peer。

**M1 已关闭。** `GcuExecutionStructure.cpp:48–50` 要求所有defined functions属于所选body的同一lexical parent，允许实际SDK GPU module中flat body+wrapper，不强限根builtin module。原nested同名shadowing不再进入leaf-name caller比较。新normal negative真实返回 **“GCU structure definitions require one lexical container”**，不是意外parser拒绝；原flat wrapper与两actual SDK LLVM仍成功。该修复限制首版支持形态，足以关闭原错联，不要求新增IPA。

**M2 原type展开/重复预算问题已关闭。** 74–131在调用MLIR type printer前，对支持scalar/vector/LLVM descriptor的type DAG进行饱和8192的成本计算，depth>32/cycle拒绝；重复type成本/文本缓存。每个argument/result/element type的实际文本总量累计到8MiB并在继续构建前拒绝。共享alias的子类型成本按出现次数相加而非只算distinct类型，不能用DAG共享绕过展开预算。类型未知family明确拒绝，未偷偷忽略。位置总量另有独立8MiB原限制；本有限追加没有扩成全IR/ISA预算重审。

新共享alias指数展开negative真实命中 **“GCU structure type expansion budget exceeded”**，在printer之前的复杂度门拒绝；normal与-O均在同版9项测试内通过。原两实际descriptor/类型仍能输出，未用一律拒绝替代支持。

**V1 已关闭。** 170–174逐个比较successor forwarded value类型与target block对应argument类型。所给i32→i64 minimal negative实际stderr是 **“GCU structure successor argument type differs”**，证明命中新guard，并非仅parser抢先失败。无需因parse仍保SDK已验证前提而另要求全LLVM verifier框架。

### Matching source / native 证据

- 本席cmp确认candidate C++与 `structure-input-v4/source/Debugger/lib/Instrumentation/GcuExecutionStructure.cpp`执行字节一致，SHA **1069a22edae14a8feac2ce2d4b0f380214ae418cff703ddb1a2ddd5a0a98f253**。
- actual v4 tool SHA **a2937f0de72fd2b7f2e031804ab6025a5fe1ba512db46f58e771f796a4d367b9**；native build/actual job terminal0，**21.549156127s**。
- **9 nativeCLI normal /9 -O**，分别0.057s/0.055s，均OK；包含原6项与nested-shadow、alias-expansion、forwarded-type三项新增。
- 两份原实际LLVM SHA仍为 **6b8b2e1a95808ec6f924dac1324f449b44f5177e89f5d5e11de6ade3511eb593** / **acdeadcb66fe11896706b9d384e3d4a7dad22c3aafe8f00bd56ac321f71068e7**，93/84blocks、1603/1754ops、46/48markers、87/105calls成功，source_region_qualified保持false。未新执行原应用/设备。
- Python CLI最终formatted SHA **0eed11147b0e98d8737dfade06c3cffd5520517879396368a2548a6a0dcb0348**，与binding-format-v2结果登记一致；该格式job terminal0/1.867335353s、两轮ruff/yapf/check-ast全0，runner记录AST等价。未把format后的test字节冒充format前完全同字节，C++matching已单独cmp。

**追加结论：原两个confirmed major及V1有限type-admission缺口，在此freeze的source/native/CPU范围均已处置闭合；无本次新增确认项。** 正常wheel安装仍在途，本席未读其成功终态，所以原V2 normalinstalled身份/实际接线gap继续保留，不能以standalone v4代替。source/native schedule/whole资格未提升，也不需要重跑旧数学或全矩阵。
+

## Installed 终态追加：原 V2 有限安装 gap 已关闭

本追加只核正常安装与新typed index公开接线，不复审whole/source-loop family。实际读取 `run094/preflight/installed-structure-receipts-v1` 的index、两job terminal/result、完整normal/-O日志，以及本地 `normal-install-input-v2.tar` / `public-structure-input-v1.tar` 中相关runner/smoke源码。未执行任何代码/测试/SDK/设备或SSH，未读peer。

- **normal-install-v2** terminal0，**55.446909023s**；source **c0575528418292c65eeccab4bd105b68bd000225**，502 installed members，wheel SHA **87a34857607a8c54e0467f573f6b85d664e10b9743d56ee508bce04898c3f0d0**。步骤中的parent patch、assemble/install、guard/import、测试均returncode0。
- runner在复用前核实际新tool摘要及所有相关native源码，复制已真实v4构建的 **a2937f0de72fd2b7f2e031804ab6025a5fe1ba512db46f58e771f796a4d367b9**。未变core/runtime/SDK复用有明确输入检查，不把复制称为又一次native重建。
- 六个相关Python测试文件 **117 normal /117 -O**，0.28s/0.41s；-O只有预期pytest assert-warning。实际native CLI **9 normal /9 -O**，各0.050s，均OK。原M1/M2/V1最小负例因此进入正常安装对应链，非仅standalone v4。
- **public-structure-v1** terminal0，**23.047613809s**；正常2次、profile2次新真实数学，math/input_unchanged/guards/host_once全true，两个capture **22/20events、各2observers**。不是原capture离线重读冒充默认入口。
- smoke实际显式 `need` 检查结构索引LLVM SHA == compiler最终native IR SHA == snapshot实际最终LLVM bytes SHA，并核fatbin/ELF身份；索引status正确且source资格false。此为正常产品hook自动生成的metadata，用户未填site/结构表。

两个新capture的实际绑定：

| binary ID | 最终SDK LLVM SHA256 | events |
| --- | --- | ---: |
| f240d1951172a25dc57d8734568c1a4d29051b15438b8bbedfc95a2c178ac5ba | 50fda194b13a0fe0ab2d67d75bd866f5db222d20564d544d2e3ac26c02daaead | 22 |
| 2bef3ec513d36e11f5b162d16a02dd3d6ad2e4c6561eca8bbed902c6a2dc0b6c | 4559f79e009edbcbc9d719b7ecb12bef699aadcec81c515d352f440868b7ac69 | 20 |

**当前结论：原M1/M2/V1修复及原V2 normalinstalled/公开LLVM→index→binary接线，在本delta范围已闭合；无本次新增确认问题。** 上文在途安装说明保留为历史，不再作为待办。仍保持 `final_machine_boundary_qualified=false`；typed结构服务没有替代source/loop family规则、最终native边界或whole-goal审阅。没有新增数学矩阵/ISA框架或要求重跑无变化的SDK、TP/UI。
