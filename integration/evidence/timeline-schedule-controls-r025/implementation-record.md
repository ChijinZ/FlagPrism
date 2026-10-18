## T039 普通与观测流水的生产编译对照

- 上一goal turn为no-progress：回答用户“是否偏离设计”并读取既有记录，没有改变产品或新增实验；本轮复核HEAD8fc1058408a9403a1e3acb6c842801329090affc工作树clean后继续实际编译诊断。只用既有NV Docker/最终r024安装，无产品改动、无用户数学launch、无论文/Study修改。
- r025 sparse-v1 controller62439/start18113624、worker62440/start18113627终态0。原普通GEMM K192/B32/stages3实际LLVM/PTX保loop/4MMA，最终SASS24MMA；不能把r023独立opt的展开行为直接当生产根因。sparse1实际15scope，default8实际22scope；两者最终SASS均保loop/4MMA，四MMA后才是未来两copy，普通有copy穿插。
- inline-v1 controller62534/start18127353、worker62535/start18127356终态0：只改观测模块metadata，移除boundary3/marker1并用旧record2 inline timer诊断；非公开/合格边界，不作为产品替代。helper calls消失但loop/调度差异仍在。该首轮common transformed-input被第二variant覆盖，plan是变换前record3选择信息，不能用作有效record2物理plan；后续逐variant保存有效输入。
- expanded-v1 controller62646/start18204696、worker62647/start18204699终态1：harness调用pm.run缺必需stage字符串，无用户数学launch；失败原件保留。修成v2新源/新run，实际终态0，普通与sparse/default诊断均按此冻结控制的6次循环在自动选site前展开；有24静态MMA，仍不能恢复普通copy穿插。固定6来自实验K192/B32，不进产品、不按算子/shape特判、不盲改展开阈值。
- nostore-v1终态0，仅删LLVM里精确匹配的日志st.shared.v4.b32 calls；实际SASS连未使用timer也被删掉，故不是storage-only因果对照、不是可用profiler。deferred-v1终态0，保留日志/inline timer、只将日志写移到原LLVM基本块末尾；未恢复copy穿插，反而sparse/default分别新增35/78条静态local spill-store。该变换未合入产品，不能据此宣称低成本修复。
- 重要边界：现有观测loop仍是wait2→当前load/MMA→未来copy/commit→下一轮，末尾wait0；没有每轮新增wait0。该冻结控制按6轮投影后普通/观测均16 copy/commit尝试、24MMA、6wait2+1wait0。因此较细指令交错损失不能独自证明所有跨迭代流水被串行化，下一动作应核实际关键依赖/端点路径与运行时view/wait覆盖，而非强求指令顺序相同。未被wait保证完成的group可能早已完成，mask也可能空提交；不据投影授实际硬件重叠/物理安全复用/区域耗时资格。
- 完整只编译原件artifacts/timeline/run-025/preflight/schedule-evidence-v1.tgz：743175B/164成员/SHAbb3d18c7380fff3cf6a689823721d19b69f9592ecd151a67596a48747c0c3b9d。含六run首失败、实际对象/反汇编、有效转换输入和源码、terminal/身份审计。stdlib逐成员byte/CUBIN hash及有限critical投影审计通过，详细结果与局限在integration/evidence/timeline-schedule-controls-r025/；不import产品、不将此当真实数学通过。
- 采集时12个controller/worker身份均missing/Z/不同startticks，无自有r025活动作业；NV查询15MiB/0%。GCU仅新证据脚本的缓存precommit格式化，结果待当前handle收尾；没有启动GCU/Asc设备数学。完整三后端goal/时钟/源边界/动态异步/独立数学与最后三个额外指定reviewer仍未完成，不complete或blocked。

- T039格式收尾：GCU controller388474/start1013415297、worker388475/start1013415301 terminal0/1.817s，三证据文件完整precommit第二轮固定点通过，Python AST同一。格式后的stdlib审计重跑结果与原audit.json逐byte相同；未运行不受影响的产品测试或重复构建。Git证据提交/推送待收尾。
