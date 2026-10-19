## T101 GCU 原真机ELF计时器helper位宽与身份辅助函数核对（run066，在研）

- 前一goal turn为progress：R065同原ELF已取得可用LLVM11 native输出，正常fatbin逐byte重现；已push d3aa2a0。当前沿用原件，不运行SDK编译/设备数学/SQL/UI。
- 新有限stdlib checker只在server现有Docker解析原ac6748... ELF symbol与R065 native stdout61fa447...。逐条反汇编bytes与原ELF重核；计时器helper地址0x379a0/208B，identity helper0x37a70/32B。原SDK声明i64 global_timer的读低/高/低与回绕比较和重读序列、高word mask0x3fff可见；physical identity helper为原movs r4,sipinfo后return，没有额外mask。
- v1 checker普通/-O都因检查器对branch landing错误地用了instruction PC-8而拒绝；这是新诊断代码自身错误，不是硬件/产品失败，也不重数学。v2按实际16-byte bundle landing PC&~0xf核目标，原v1失败保留；同原件server normal/-O均通过，wrong_upper_mask和missing_rollover_comparison两个负例均拒绝。
- 独立保留capture声明核同：input fa35be044476e8bd57e74e7ebd4a597cb9e5374389160e3a5c36948d846521b8，fatbin bd419b80...，debug_clock_bits46、domain=enflame.sdk.global_timer、primitive=_ZN4tops12global_timerEv、linkedlibrary SHA1a780215d7a63e34ce9c8cba6bfb126d222db726f5dca8802f3af0161fce81ec与helper输入一致。这里只补实际helper返回值位宽上界/声明一致，不能把46bit上界当独立测得的物理counter本体位宽。
- actual inline reader→raw record绑定、source region、shared epoch、absolute frequency、hardware busy均在新result中明确false；同MMIO地址不证明跨SIP epoch。没有产品字段/API/SDK改动。已请原R2实际阅读这份有限checker/原结果/声明与native输出后判断具体错误或越界，结果尚待，不预写通过。原SDK/private源码不入Git，下一步仍需source/nativereader路径闭环，整个goal active。

- T101原R2实际阅读有限checker/两种Python结果/原失败/声明及SHA匹配native helper文本后复核：未发现影响该有限结论的具体错误；确认branch bundle目标0x37a40、返回值最多46bit和未mask的sipinfo。强调不是物理counter精确位宽/周期/全执行一致性，不能推跨SIP epoch；原ELF字节比对依已存server收据，review没有访问设备或重跑。结果不是仅依据root摘要的意见。
- 新tracked小证据timeline-gcu-clock-helpers-r066保留own checker/原失败/去掉完整native文本的actual结果摘要/声明/外部SHA索引和有限review。runtime文档仅增加有限helper证据与边界说明，不改变产品clock/region资格。normal/-O结果与同一capture声明46逐项核同；无额外build/device/math/TP/UI测试理由，所有本轮CPU诊断已结束，paper/Study未写。整个G1 source/loop与pipeline-preservation仍待闭合，不能把本补项当完整goal通过。
