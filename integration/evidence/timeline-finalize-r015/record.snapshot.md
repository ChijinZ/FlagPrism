# T023 工程记录快照

## T023 两阶段收尾、跨调用原件保全与实际解码失败恢复

- 上turn分类progress：3037f03更新设计/测试合同，三独立Sol6.1/xhigh设计评审与有限复核闭环。当前以工作树/服务器实际终态继续，不重新创建或降级active目标。
- r014旧三任务真实PID/startticks再次核terminal、worker missing/controller Z；PRO6000 15MiB/0%/无computeapps。T021文档/原件索引已提交70fd0ed；原件字节保持，final-target-state.txt原始尾空行保留。
- 本轮实现d092f6272d43e7f1bd2196005a954187384a8993：hook先独立读取/保全所有owner原件与源码对象，安全持久化后release，再对原件做decode/export；前一个调用失败不阻断其余原件，设备与派生pending分开。追加不可变attempt记录与可原子替换index，重试沿原目录、不重放应用；readback重试遵守共同剩余时限。
- CPU故障合同6个：首decoder失败全owner先释放/其它照常解码、原件只读重试、read失败仍保owner且其它调用继续、release失败保owner与pending、raw篡改检测、目录与原件持久化合同。16旧owner+4public合同normal/-O通过。
- 新独立package-finalize-v1成功，wheelSHA8cbdabc8f63282966cf047dfaea4fc8a08f3ec73dde8b0b513d585fcbfa566dd，608成员byte核，7native与原4f5b2bf实际build一致未重编native。build owner47498/start10642130，worker47502/start10642157；install owner47636/start10651535、worker47637/start10651538，terminal0。最新安装/workspace/chijin-timeline-r015/runs/install-v1/output/venv。
- 实际公开API故障恢复脚本tests/timeline/p01_nvidia_finalize_recovery.py已提交31f8743及校验字段修正39a601f：普通两stream三recurrence+GEMM、首次decoder失败，验证所有4原件先持久化/释放、其余3可解码、同原件重试无transport动作及新合法session恢复。不授予clock/边界/Perfetto资格。现已启动r015/runs/fault-recovery-v1（180s有界controller）；恢复先poll该handle及PID，不从launch记录推断终态。

### T023 修复、实际验证与收尾

- fault-recovery-v1 controller47803/start10656248、worker47804/start10656251，terminal1/4.322s：测试脚本错用用户bundle路径，修正为公开session真实staging（d06e03b），保第一次失败，不记通过。fault-recovery-v2 controller47971/start10662106、worker47972/start10662110，terminal1/4.322s：真实保存四原件/owner已全释放，但JSON重读的slot由tuple变list被物理解码器拒绝；这是真产品故障，原件/错误不覆盖、不标unsupported。
- f17071ccd6a7514507e583a71b27fe6030752ff9：规范恢复slots tuple，CPU fake decoder同样核tuple对合同，新增journal写入失败不得掩首decoder异常的第7用例。新版package-finalize-v2 owner48145/start10670187，7native仍与原实际build字节一致；wheelSHAa69d9d047c798db2fc768db1ab376bc044313c6a8c50499249464f24b757bb97。新install-v2 owner48289/start10678246、worker48290/start10678249，terminal0/19.697s；608安装成员核；normal/-O各16owner、7finalization、4public合同通过。
- 最终fault-recovery-v3 owner48456/start10681664、worker48457/start10681667，terminal0/9.730s。一次真实公开两stream workload的四数学调用先全raw/关联/编译对象持久化并release，再注入首decoder失败；其余三真实capture正常解码，index/attempt保首错/1pending/0owners。同原件重试后四capture完整，transport新增动作0、raw/input及首错SHA不变。下一正常公开session四调用通过；成功8capture共2688端点/1344区间，原数学/input/tail/合法副作用均通过。初始两失败还各执行四调用，不能当作没有发生；原失败数据一并保留。
- 原件artifacts/timeline/run-015/preflight/finalize-original-evidence.tgz，1951765B/315files/SHA1d861e0b9bd31e6730ad14d2a5eb9016c28d30bb7e53a4868c518d28118fe4eb。stdlib/Git audit核实际安装两模块、5个实际测试脚本与freeze、608成员/7native桥、normal-O日志、全部2688物理tag/tick/seq/offset/配对和两个math结果、原失败/owner终态。小证据和复现命令在integration/evidence/timeline-finalize-r015；工作机未import产品或运行oracle。
- 七个本轮build/install/device任务均真实terminal，所有owned worker missing、controller仅Z或missing；最终PRO6000 15MiB/0%/no computeapps。没有在途任务，不做无变化重复矩阵，不改论文/旧Study。
- 保持active：新路径仍NVIDIA raw-only partial_clock_unverified，边界/尺度/epoch/物理复用与普通流水扰动未核；GCU默认首末program/owner/transport、Ascend新timeline producer、标准pftrace/TP/UI、独立六数学、最终三个额外Sol6.1/xhigh代码review仍必达。重试目前为保留hook的in-process入口，不冒称独立公开cross-process恢复命令。下一步优先接GCU实际公开采集链，并继续最终机器边界/原流水扰动与真实clock/async证据。
