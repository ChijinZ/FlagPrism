## T104 GCU 最终 ELF 位置自动绑定；Asc SDK 汇编出口诊断（run069，在研）

- 前一goal turn分类progress：GCU synthetic-file缺失修复已有正常安装、两新math真机及actual ELF文件/site/有限phase证据，并push9232936。当前canonical/candidate起点clean；本轮没有自动重跑既有矩阵/UI。核原design §0.6/testing §0.2/§5.6：有限结构实际边界与原关键依赖保持确为要求，任意机器码形式化证明、完全相同instruction order、精确hardware busy不是要求，NV性能/开销认证仍按用户暂缓。
- Asc仅CPU一次诊断，精确读取R060实际公开C1 vector的adapted LLVM/driver argv与原object/loaded ELF，所有链接输入SHA核同；正常SDK codegen0，原object/loaded/newobject .text均10916B、SHA7e72a230c7e76d1fb2e88550d631c52fb0b03c8ccd3d664c7ef6bb8b52941642。同argv新增标准-S的独立step明确失败 error: unsupported option '-S' on device side，whole controller1（assembly-probe-v1）。未修改SDK/原件，未执行NPU/模型/数学。不据此断言不存在任何其它SDK出口；这条具体常规出口不可用，normal重现不是native语义证明。
- 新增GcuNativeLocations.cpp，以现有packaged gcu-timeline --native-locations模式调用LLVM Object/DWARF读取最终ELF的自动marker file/site/column/section地址，记录line0/未知column；严格检查可执行section范围及row/output预算。它不解析/逆向私有ISA，也不授reader-valueflow/source-region/engine-busy资格。
- normal standalone tool四TU+link已实际成功；原5 scope tests+完整真实IR SDK验证0。新5个真实native CLI/GNU-as host ELF fixtures通过（site7 begin/end实际row、错ELF、普通文件、未知column、I/O）；这些是DWARF CPU fixtures而非硬件时间证据。对R068两actual已执行ELF读取，分别48/62正位置、13/13sites、line0为10/25，site10阶段与独立readelf原摘录地址一致；native-map-check-v1 whole0，无重放。
- 现编译后hook已编码：从真实fatbin按有界Clang bundle header选择唯一GCU300 ELF，自动运行同一native tool并将fatbin/ELF/tool/输出SHA、位置表和缺失phase写compiler metadata。scope与ELF inspection共用单快照/30s/owned child/失败原件留存入口。SDK正常产出的binary bytes原样返回，无按算子身份分支。位置表仍只叫compiler debug location rows，缺失phase显式保留，不升级P03/G1。
- 新tests覆盖错误bundle header/extent/alias/重复target、报告越权/错site/错phase/bool column、缺phase保留与ordinary不触发；公开两math脚本新增本次executable hash/自动位置表检查。补丁对pinned public FlagTree实际apply-check0；server clang-format/yapf/ruff回收实际字节。下一步冻结、正常新tool+wheel隔离安装，运行这些定向CPU tests和同两math。尚未安装这份新hook，不能把已有retained ELF检查当新公开入口通过。paper/Study未改。

- T104 后续：固定68faaaf normal安装和新公开入口2math实测均通过，细节见顶部恢复摘要；不再把该hook记为未安装。`native-device-poll-v1.json` 保留实际controller0、22/20events、2observers与新binary身份。新位置服务是通用编译hook，无逐算子适配。
- missing阶段定向调查：`clock-origin-aliases-v1.json` 显示LLVM独立timer call23/24而不是逻辑26；`shared-end-blocks-v1.txt` 原实际LLVM摘录进一步显示优化器尾部合并（bb16/bb53），site字段和begin通过块参数选择，end timer仍在共同后继运行。不能依据call数或单一debugloc推断timer丢失；mapper继续只承诺原生DWARF行表，missing表示未找到独立行表位置，不表示阶段未执行。没有为保留debugloc插入额外wait/barrier或改动原SDK优化。
- 一次辅助 SDK bitcode属性诊断因 `/opt/tops/llvm11/bin/llvm-dis` 不存在退出1（`timestamp-use-v1.txt` 保留此前成功的LLVM摘录，stderr由SSH返回）；该支线不作timer属性结论，也不继续寻找不必要工具。已有实际CFG已定位上述缺口原因。
- Asc driver `-###` 探针：outer/controller及child0，但stderr明确unsupported option '###'、未导出cc1命令。这是功能不支持，不能记作命令可用；连同先前-S失败只排除这两种入口，不宣称所有SDK汇编出口不可用。未增加NPU/数学重放。

- T104 最新：新8trace已用原pinned tools/verifier真实TP全过（counter4，42interval；dependency4，16endpoint/8flow），原raw端点、单位换算、protobuf和SQL均核验，完整stats保留，无正error/data_loss。CPU工具编排初始v1错误controller路径、v2缺wrapper输出父目录、v3错误把dependencyview送counterverifier、v4转移漏.raw，均保留原失败；v5补齐正确输入且whole0，不重跑数学/device/UI。
- 三原指定reviewer对68faaaf的compiler/runtime/delivery有限delta均无新增confirmed blocker/major/minor，支持交付但不授全goal资格。delivery提的两个verification gap已处理：新8trace真TP如上；最终脚本server yapf补覆盖并回收实际格式字节，AST与真机脚本完全相同（仅摘要字段排版），不重跑数学。新文档明确missing独立DWARF行不是missing clock、不伪造多路径别名。
- 本轮有限证据归档 integration/evidence/timeline-gcu-native-map-r069；完整原始产物保留服务器及root artifacts。下一步合入正式detailed-profiler并push，然后继续有限G1/G2原合同缺口，整个goal不标完成。
