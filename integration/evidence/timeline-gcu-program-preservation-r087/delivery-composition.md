# R087 GCU transform 与 State writer 的有限组合

**可行。** 对实际 before/after 与 profile SDK输入/编译对象链均核同、且本证书通过的对象，完整 high-IR 新增效应隔离可以替代“在LLVM重新追完本地ring所有alias/use”。没有必要再实现一套同等的LLVM内存taint或全IPA。仍须沿实际profile LLVM计算原State transfer、guard、descriptor及物理actor分片；该certificate单独不是State writer资格。

唯一需要明确的reader边界是：**证书隔离的是新增observer，不能当作原程序任意地址逃逸的全局豁免。** 应把payload例外绑定到已证observer部分，或以已核before/ordinary State使用范围排除原有同类逃逸，再组合实际profile分片。无需为此新造完整ISA或逐scalar解释器。

配置请求 GPT-6.1-Sol/xhigh，实际resolved型号/effort未暴露，unknown。仅只读源码和实际收据、stdlib核文件身份；未执行/import产品、checker、测试、SDK或设备/SSH，未读peer。本报告不重审ordinary32、allocation容量、timing boundary、pipeline或whole-goal。

## 已实际读到的保证

候选实现 `3b65197ad4ef03fdaeb2bc222e365bf63d0055b0`。完整读取 `GcuExecutionPreservation.cpp`、rewrite调用、CLI及维护测试；四份关键源码与实际build-v5输入archive逐byte相同：

- preservation C++ SHA `6c60defb0509c72c132d2fefe0bf38effd05b5fd444e15549ca7dc9b12737644`；
- `GcuTimeline.cpp` SHA `6cad9fa1a7b28353125bbd2fb9ae57d078e7c4f26217b8e1523ed6edc2f5e39b`；
- CLI SHA `d5aa34a0f06e2483412ee8d6d11c5d3b1280906bbf46bd51b3b35f7ed855d6b0`；
- fixture SHA `2ff1d883a59b27d348f41422d6f3b35c7c8b090910e7a0f5bc2e36f9d733868a`。

其证明不是只比较几条预期State store：

1. `GcuTimeline.cpp:331–337` 在改写前保存module clone和原Operation身份。preservation `:68–114` 验证模块、原操作仍在原控制树内、原operand不消费新增value；删除clone中的所有新增op后，整个generic typed core必须恢复原程序。SSA/CFG、types、operation properties都比较，只有导航locations及明确新增版本attr排除。
2. `:120–150` 要求hidden是before中未使用的最后参数，且新增ptr2memref只能来自该hidden。fresh只取新增 `memref.alloc` 的直接结果，不把原memref或未知别名视为fresh。
3. `:153–199` 新load/store/dealloc只接受fresh；新DMA只能fresh source→hidden view、tag也fresh/private；没有把load出的bits变回原内存view的允许路径。纯整数/descriptor观察可以读原value/metadata，但原操作不能消费其结果。新增call只接受实际解析到的、无参数/非variadic/返回类型精确的external timer/identity；local shadow和其它callee不被豁免。
4. `:218–265` 的公开检查重新运行受检查producer，再把实际after与其完整typed core比较；不是相信旧manifest自报成功，也不是从另一份相似IR推断。整bytes是否相同独立记录；location等价只给源级语义权，不给最终native/timing权。

在合法memref/SDK语义及原独立hidden allocation合同下，上述限制已阻断“新保存bits→load→GEP/指针重构→写原内存”和“新保存bits→unknowncallee解释”的路径。原ring随后如何在LLVM中变成local地址与GEP，不需要再用另一份完整alias分析重复证明同一新增效应隔离。已核getter/byte-copy SDK语义和本对象实际编译资源身份继续复用；证书不自行授予未知SDK/helper语义。

## 新实际收据能说明的范围

已读 `gcu-preservation-build-poll-v5.json`、`gcu-preservation-actual-poll-v1.json`、`gcu-transform-reference-poll-v1.json`、实际枚举runner及维护fixtures：

- 新native正常configure/build通过；normal/-O各10项通过，包含原store被新值替换、未知helper、保存位经index写原内存、额外读原内存、reserved clock local shadow/错签名及hidden wraparound拒绝。现有恶意after用完整producer复现拒绝即可，不必再把相同反例降成完整LLVM ISA测试。
- 实际109条、37个不同transform中97 preserved；**12个原q05旧logger whole core不同而拒绝**，原失败保留。不可把“current installed对37个before都产生新相同输出”改读为“37个历史after都通过”。
- current R077 installed tool与新tool对37个actual before的输出37/37 byteequal，说明这个检查delta没有改变这些已登记输入的当前producer输出；它不是历史旧q05输出的资格替代。
- 实际runner连接math/loaded binary、snapshot LLVM、before内嵌SHA/原rewrite receipt/原input文件、actual after SHA、hidden/capacity/regions，并按该tuple缓存。它仍明确State/SDK/native资格false，正合本次范围。

这里读取的是完整实际runner、原poll及其登记汇总/失败详情；没有在本次逐37份远端原blob重新跑或重做lowering。正常wheel安装尚未以本次所读收据证明终态，不能据standalone build冒称正常安装完成；这不改变上述证明组合方法的可行性。

## 给现State checker的最小接法

1. **按对象准入模型**：只对正certificate行启用“verified observer address payload”模式；核certificate所引用的实际before/after SHA、transform参数、受检查tool/规则身份，并连接到该capture的actual SDK输入、loaded object、State formal、actor/grid/extent。`97`计数或一个无绑定boolean不够。12个拒绝对象没有这项准入权。
2. **保留原程序的State检查**：仍扫描/解析profile实际LLVM中的真实State source/destination、地址、predicate、CFG、1D/2D参数和合法byte范围，未知State callee/直接未知写回继续拒绝。certificate不能把所有State-related op删掉，也不能继承普通对象的一份数值count来替代profile实际分片。
3. **例外属于observer**：对已证新增观察分支，不求运行时指针数值即可接纳其ptrtoint后的低/高字trunc/lshr及data-only保存；不把这些位再当State写地址。在源级完整隔离和实际编译链已绑定的前提下，先前建议的“LLVM再追全部ring load/alias/未知消费者”不再是另一道必做门。
4. **避免原有逃逸被误放行**：可复用对应before/ordinary已证State使用/cone，确认这些低层例外只来自新增observer；或对其与observer的来源作有限匹配。若before本来就有State地址保存/恢复/unknown helper，原规则仍管它，不能因after附有此通用证书而忽略。这里是既有未知State写者规则的延续，不要求全函数新语义框架。

第4点可以很小：原登记数学已无该类原地址逃逸时，记录其已核before/State-cone身份即可；不必逐LLVM store重新证明local ring别名。若难以区分某条原/新增投影，保该条unverified，不能默认所有trunc/lshr/store都是logger。本报告不规定一定要增加新C++标签或一个通用mapping系统。

## 最小下一步与当前不足

**没有在本次有限实现中确认阻止上述组合的具体源码缺陷。** 最小下一步仅为：在当前97个正证书对象/实际key上，把新模型绑定并运行现有State分片；未变SDK/helper/数学/host-once/TP/UI复用，旧q05不通过certificate的12份保持历史状态。原补二/各profile依其原登记与当前替代关系覆盖，不能把历史对象计数改成新的数学分母。

新模型需保一个正例“证书＋实际地址payload＋原State分片”，和一个“有证书但原程序自身包含未建模State地址逃逸”的拒绝边界；其余当前producer/内存隔离反例已有normal/-O实际收据，不要求再叠一套全内存/ISA测试。最后读正常wheel安装终态、原实际CPU分片结果及精确身份即可；不需要new SDK、设备、数学、TP/UI重放。

allocation bounds、SDK lowering、native boundary的false继续保留。源级新增效应隔离足以给出本题的observer-payload模型，不能单独叫Statewriter、timing或whole资格。

输入索引：actual preservation poll SHA `0580d1adf8a92104560750bf7969018296bf679ece6d73b18e044f726181a1cd`；37-output reference poll SHA `c642476b588c6121ce98ba9cba0baf498a3e44b34b92ce638c0136c9bcae0f34`；build-v5 poll SHA `c93bf166d153b6284527f76172271d612db74b563dbc34db770b5448b695bec4`。
