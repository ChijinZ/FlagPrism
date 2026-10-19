## T105 NVIDIA 稀疏观测计数寄存器生命周期（run070，在研）

- 前轮分类progress：GCU自动ELF位置信息完成正常安装、两math/8新trace真实SQL和有限独立review，合入并推送7f8fdf5；本轮未重复旧矩阵、UI或应用/device执行。
- 从剩余关键依赖核验的实际失败切入：R061 sparse `Published count has a partial or predicated write`。normal installed730b9fe在Docker对原actualcapture重新读取机器码，count-liveness-v1 controller0；native counter R12/R13，全函数扫描误纳入0x5b0的IADD3 R13临时值以及0x610 MOV.64 R12,1。实际published header的两word reaching definitions不含它们，证明不能按同名物理寄存器全函数定身份。
- 候选通用修复：以实际header/count-index LEA用途为种子，两word所有路径追溯可达定义，继续跨loop-carried IADD.64追溯；活跃partial/predicated写仍明确拒绝。初步CPU v2剔除误报后暴露旧initial-batch判据过强：要求字面常量count赋值前寄存器只能为zero，拒绝此前无关临时值。新判据将检查真正必要条件：固定zero-based首batch不可覆盖任何此前record写，沿实际CFG反向检查所有路径，并拒绝重复initialbatch回边。
- 新p01_nvidia_count_lifetimes.py针对原default/sparse4captures核完整native地址+rawordinal，并注入活跃highword破坏/predicated add/错误add输入/重复首batch/先前其它batch五类语义错误。count-suite-v3已启动，尚未核终态，不冒称修复或安装通过。此次仅离线分析源码加载，不是新wheel安装；后续通过后需正常Python交付安装及受影响公开重导验收。

- T105 v3源码加载定向回归 terminal0：原default/sparse K3/K7 4captures全部完整native地址与rawordinal通过（每组合1280/2304batchrows）；原5类negative各4拒绝。此时只是1326509源码检查，不是新安装。server clang-format/yapf/ruff通过并回收实际字节，AST核同。
- 原R1独立review指出M1：live zero initializer不应在先前record/count非零更新之后，否则branch reset可能发布0。修复为zero入口和首batch入口都检查实际CFG全部predecessors不能有recordstores或任何live非zero count更新；保持无关temporary可覆盖。R1确认新source约束静态成立，并指出最初两项回边negative会被旧首batchguard偶然拒绝，不足独立回归M1。已移除，换成无回边的直线首batch→条件zero-reset/旁路→同一header的synthetic native CFG（明示非device），新guard必须拒绝；当前冻结baea706。
- 正常安装v1终态1，native源核同/git步骤通过但assembler被setuptools拒绝absolute egg_info PKG-INFO路径；通用相对egg_base修复a71d32f，v2实际assemble0（约50s），随后旧pip不支持--python导致install2、whole1。失败原件均保留，不声称装好。v3改目标venv标准ensurepip+自身pip正常安装、无需下载/重建native；冻结baea706完整源码已传服务器，正常安装/21negative normal/-O/旧地址回归与一次公开CLI复制bundle重导已启动，尚待终态。
- 当前canonical仍7f8fdf5（clean），候选baea706（clean），本轮产品尚未push；NVIDIA老730安装保留。其余后端无新device任务。不要重启尚在运行的v3；按runs/native-install-v3/terminal.json和owned PID核状态。R1有限复核进行中；R2/R3原报告绑定1326509，只将其称旧freeze有限审阅，不代表后续source fix已共同审过。

- T105 baea706 normal-install-v3终态0，13step全0、639wheelmembers核同，source/native分离证据完整。normal/-O各4actual+21negative；旧地址33negative/113原件不变。原R1独立读取新终态及normal/-O收据，已将M1 source+正确fixture+installed闭环追加关闭；不授ordinary/source-region/wholegoal资格。
- 公开CLI实际重导first sparse capture在复制bundle产生8counter+2dependency，reasonnull，无应用/设备重放。2新依赖导出使用原pinned verifier/TP真实导入全过（new-dependencies-sql-result-v1 whole0），每份180nodes/404flows，完整stats无正error/data_loss。只检查新导出，不重导旧1740、不重跑UI。
