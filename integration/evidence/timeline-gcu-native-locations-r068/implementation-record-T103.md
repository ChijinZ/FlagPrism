
## T103 将 GCU 调试位置接入产品编译入口（run068，在研）

- 前一goal turn为progress：R067原型真实SDK成功/.text不变但加载映像变化，已Git/push92ac7c5。原R1独立走查实际读代码/收据，未发现阻断路线的major；发现两次getFile间输入快照可能变化的minor。报告存R067证据，尚非整体终审通过。
- 本轮候选代码新增 GcuDebugScopes.cpp 和现有gcu-timeline工具 --debug-scopes 模式：两个parser从同一caller StringRef快照解析，修复该minor；不直接回写typed printer的SDK属性，输出仍强制实际SDK验证。原GCU recorder每site自动插入 file=__flagprism_gcu_clock_v1__、line=site id、column1/2为begin/end，3/4为identity的debug位置，并在manifest给出对应关系；不按算子/shape分支。
- Python bridge/SDK make_llir 接口已编码：只对timeline保留SDK debuginfo，补DI scope，真实SDK重新解析验证后才进入fatbin；新工具、bridge、backend与直接SDKopt/compile进入冻结身份，identity版本2。尚未装到运行时/真机，因此不得宣称native→raw或整体G1已通过。
- 第一正常standalone native build成功（main/GcuTimeline/GcuDebugScopes三TU+link）；初版测试夹具使用custom LLVM文本，opaque parser按设计只支持SDK generic文本，2正例失败/3拒绝例通过。保该whole failure（controller557589/worker557590 terminal1，13.484s），没有启动device。
- 将测试夹具改为实际generic形式，不改已成功的native实现，复用同一bin；5个真实CLI测试通过（marker/overflow属性保留、已含DI再次解析、malformed、missing input、输出I/O错误），完整R061实际保留IR经新bin处理并真实SDK验证成功，scopes-check-v2 whole terminal0。新完整source.patch对固定public FlagTree add842f2三文件git apply --check通过。无数学/SQL/UI重跑。
- server格式化已执行clang-format/yapf/ruff，回收实际输出修改；接下来冻结当前源码并正常构建新tool/wheel/隔离安装，再跑受影响真实算子。旧安装/原采集不动。NV pipeline与Asc全边界仍开放，paper/Study不改。

- T103 4fbc8e8候选已正常构建并安装到 /tmp/chijin-timeline-r068-gcu/runs/native-install-v1/output/venv/bin/python。新recorder三TU真实编译/link；其余共享native源码与旧实际安装逐文件比较相同（四个未参与GCU构建的NV/Asc文件单列排除），未冒称core/runtime重建。495 wheel成员安装逐字节核同，wheel SHA f06196ef...。两新math polynomial/weighted_moment公开API ordinary2/profile2通过，input/tail/state-once均正确，2capture各2observer、22/20真实events。
- 三原独立reviewer实际阅读4fbc8e8及该安装/真机收据后报告（R068 compiler/runtime/delivery-review.md）：单快照minor关闭、安装接入链成立；runtime/delivery未发现本delta confirmed bug。compiler确认major C1：真实两ELF decodedline/rawline虽0且stderr空，但synthetic文件/marker均缺失。LLIR有marker不等于native保留，原native-lines-v1 0rows结果完整保存。此前真机数学仍通过，但机器边界/source/raw资格不升级。review覆盖冻结4fbc，不把并行未冻结修改混入。
- 修复方向来自LLVM官方DebugTranslation.cpp（https://github.com/llvm/llvm-project/blob/release/18.x/mlir/lib/Target/LLVMIR/DebugTranslation.cpp#L302-L318）：裸FileLineCol不换既有scope文件，需要FusedLoc<DILocalScopeAttr>。新增局部DIFile/DILexicalBlockFile，以所属LLVMFuncOp DISubprogram为scope，只修改位置；仍走opaque转移和真实SDK验证。
- 修复后CPU scopes-build-v3正常三TU编译、5CLI tests及原保留IR真实SDK验证均0。lexical-compile-v4只用已有两新math第一份实际LLIR，normal SDK compile+readelf均0；最终新ELF出现synthetic文件、58条marker文件行表row，其中48条line>0且覆盖13/13 manifest site（另10条line0保留为编译器未知行，不当作site0）。这仅证CPU编译路径，原profile-v1 binary未改，也不冒称它已含标记。
- formatter-v2对最终相关源码重新执行clang-format/yapf/ruff并回收实际字节；修正先前v1 formatter早于Python ownership try修复的收据覆盖差异。当前准备冻结显式scope修复并安装新v2 wheel，再复测原两个math/最终ELF。尚未跑新SQL/UI；旧1740及unchanged exporter逻辑继续复用。完整reader→raw/source-loop/ordinary pipeline仍开放，不扩ISA框架，不改paper/Study。
