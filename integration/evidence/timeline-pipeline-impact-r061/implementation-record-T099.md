
## T099 NVIDIA 全部读钟memory-clobber单次CPU探针（run064，非发布）

- 既有只移除matrix两个reader clobber的R061探针未恢复ordinary交错。本轮单一有限variant在同一实际LLVM副本仅移除全部70个clock-reader调用的memory clobber，保留其余输入/输出和所有其它指令，不改canonical产品/SDK/旧对象，不进入GPU执行或新的数学矩阵。
- server existing Docker/chijin-study-pro6000，R061 budget venv；新owned root/workspace/chijin-timeline-r064-nvidia/runs/all-clock-probe-v1。controller121107/worker121108 terminal0/1.167s，worker missing、controller Z；实际LLVM translate/PTX release+lineinfo/ptxas/native disassembly/counter map均成功，scriptSHA8b8a4ccb2d229614a6585c03c5a20952dded6525ae516e1c526823751f22ac0f。
- 实际21条critical opcode及DEPBAR/BAR等待参数投影与原default profile完全同，与ordinary不同；4HMMA仍在matrix reader 0x13c0..0x1440内。故移除所有reader memory clobber仍未恢复原交错，不作为修复发布，也未唯一归因其它liveness/metadata。仍是B=ordinary保持未证明，不宣称新增完成依赖/硬件串行化。
- prototype cubin SHA735ee43405e8a0728b9a27604483ee706b326eed054c4aa726ab1e27998c6a80；完整archive78964B SHAdc48e25b363fe115d2d26a72feeaac50d9c10f6d8b3d674747220bd3e2569a5a含17文件，离线只读核输出SHA/投影；summary/probe追加Git timeline-pipeline-impact-r061。没有应用/硬件/SQL/UI重跑，不为负的未发布探针重启三席全审或资格矩阵。
- GCU完整disassembler/最终汇编导出选项异步请求仍待用户回答。整体目标未完成，final source边界与ordinary-overlap仍不升级；本轮工程动作已terminal，无新device/browser工作，paper/Study不改。
