# 公开固定12单元结果与有限结构对照

2026-10-16，已执行root授权的固定表一次，未增加shape、warmup、retry、sidecar、marker-only或native构建。controller PID/PGID1877649，argv SHA256 `392424de287536610001651796a8bf330001b8915a79fcac79329c911b154fd2`。源冻结`b09827d6…`、controller冻结`f2976564…`、launcher冻结`2bebd3ce…`。

## 实际结果

全部12单元的数学、a/b/bias输入与左右output/state canary严格检查通过，各进程target host ledger attempted=returned=1且synchronized=true，各cell exit0且terminal_confirmed=true；无finalize异常、unsupported、timeout或device fault。**exit0的含义仅是diagnostic_completed；State从来不是此程序的通过断言，原资格gate未更改。**

| config | State形式 | ordinary实际State | default实际State |
|---|---|---|---|
| BM16/M32,N32,K32/grid2 | scalar非原子 | [1,1] | [1,2] |
| BM32/M64,N32,K32/grid2 | scalar非原子 | [2,1] | [1,1] |
| BM16 | vector | 1024元素全1 | 1024元素全1 |
| BM32 | vector | 2048元素全1 | 2048元素全1 |
| BM16 | scalar atomic_add | [1,1] | [1,1] |
| BM32 | scalar atomic_add | [1,1] | [1,1] |

第一组形成公开普通1/profile2的最小复现；第二组表明同公开source结构的普通backend本身也可能出现2。两者都需要解释，不能把普通2拿来关闭既有eligible profile失败，也不能仅凭profile2推replay。多physical writer即使最终证实，也不自动等于用户Triton源码有合法race。

## atomic为何不是简单的“两writer计数对照”

本次BM16 default真实SDK original AIV LLVM：`public-bm16-atomic-original-aiv.ll:352` 有`%44=GET.SUBBLOCKID()`，`%45=icmp eq %44,0`；367行的branch以此predicate支配51块，只有51块执行State formal7的`store_ubuf_to_gm_1d_int32_t(...len1,stride1,atomicKind=1)`。相同predicate也guard整个float output store。适配LLVM保留同一结构（约508、545、548行），新增counter没有移除该election。

BM32 default original AIV SHA `193685510e68d3854063c16d86b4418035de6cc76cdecddc2dc2b674c3fdcb9c` 也有相同SUB0 guard（352–370行）。BM16 atomic original AIC entry中State formal7没有use，实际State副作用在AIV。

普通atomic的实际TTAdapter `public-bm16-atomic-ordinary-ttadapter.mlir:57` 为`hivm.hir.store ... atomic=<add>`；非原子scalar则是memref1 load、tensor1 insert、materialize destination。SDK atomic路径还使整个float output采用SUB0 full-tile store，而非非原子路径的SUB*256分区。因此atomic1/1有不同lowering/election的实际依据，不能据它反证非原子scalar复制，也不能直接用atomic替换原State作为修复。

**边界**：普通API没有启用late compiler capture，因此本包保存了普通实际TTIR/TTAdapter/bcmlir/npubin，没有普通原始SDK actor LLVM。上述明确SUB0 guard是本次default实际SDK原/适配证据；普通atomic的早期hivm atomic属性虽已直接保存，不能冒称普通最终LLVM也已直接留存。

## 非原子scalar的实际可见结构

BM16 default original AIV SHA `fcabf71ef75a52168526caa1796a379cd05d7ca51e49590ba6f49efa89ba569e`：State formal7，scalar GEP index由BLOCK-derived logical pid生成；实际load为`llvm.hivm.LD.DEV.u32.GM`，加1后先UB scalar store，再调用同名GM store wrapper，但atomicKind=0。State tail没有branch或caller SUB0 election。原/适配一致。输出floatstore另有SUBBLOCKID*256地址分区。

BM32 default original AIV SHA `b618a01f794ec65a85f81620773cdf8423151e28545adc49f0bdf7b9375ed506` 也没有State caller branch/election，GM State index依赖BLOCK、不依赖SUB。对应ciface的真正body仍只declare；本轮没有重新扫描SDK/反汇编，也**未直接证明helper内部有或没有election**。因此当前证据更聚焦“source scalar的partition/election路径与atomic不同”，仍不把实际多个GM writer当作已完成证明。

## 已建立及尚缺的ABI指针链

每个cell `launch-arguments.json`直接记录Python实际a/b/bias/out/state参数指针、storage base/extent、argument extent和shape/dtype。公开TTIR保持5个原user formals；TTAdapter加sync/workspace两formal，default还追加trace；最终LLVM加FFTS前缀。本probe实际final State=7、trace=8；原AIV State GM load/store使用formal7，适配counter GEP使用formal8。`generated/binaries-receipts.json`保留source/final角色与marker metadata，可以逐case独立核对；不会把不同私有样例的formal8 State误搬到本公开probe。

这建立了Python参数inventory、source formal语义、compiler ABI prefix关系及实际LLVM GEP/use链。**没有独立留到运行时隐藏trace地址或完整generated launcher C++ pack源码**（本次各cell TRITON cache未发现`.c/.cpp/.cxx`）；不能把类型验证和独立allocation源码替代本次actual runtime pointer identity证明。现有数学/input/canary通过只能作为有限反向证据。此缺口不通过加私有hook或新GPU变体偷偷补齐。

## 原始安全证据与终态

本地`public-state-finite-evidence.tgz`：actual SHA256 `a11ae5e6f40fc35dbba6bf4ba349303370358a431c048b1b8b006aded15df7e6`，1,173,031 bytes，247 files。已原样解出到本目录`evidence/`。内部`evidence-index.json`逐文件SHA；每cell的`result.json`、outer `receipt.json`、hostledger、launchargs、source、日志均保留。user `CompiledKernel.asm['npubin']`实际字节保留为`.npubin`，其hash与JIT cachehash分别标识；不能把cachehash冒充binary SHA。

default各自实际SDK原/适配actor LLVM来自本次明确artifact、producer SHA验证、白名单root/suffix/无symlink。SDK/libs/archives/BC未收；不扫描cache。SDK actor `.o`因producer path不在冻结outputroot或suffix不在白名单而不复制，原hash及excluded reason仍在index；这不等同于该object实际不存在。完整binaries.json可能含producer payload，故包里仅保留移除data/llir的receipts副本。

远端`run/summary.json`状态`finite_table_finished`、12 completed、remaining_descendants={}。`device-release-receipt.json`在实际`/proc`查controller+12cell的13PID/13PGID，owned_live=0、rows=[]、zombies=[]。NPU4 lease已明确归还root；本任务之后只有CPU归档/只读分析，不再设备执行。

通用修复层判断见`SOURCE_SEMANTICS.md`。root另行指定的compiler agent已收到全部公开IR和FLIR路径，继续只读验证可实现的语义保留/physical election落点。本轮没有产品修改，原完整资格中的两次State失败仍open。
