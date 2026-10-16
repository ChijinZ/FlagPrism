# 公开 State ownership 诊断执行表（未运行）

源文件：`public_state_probe.py`。仅用已公开 `tests/ascend_census_visibility_probe.py` 的 dot/input 构造作工程起点，删除 reduction，采用 `maximum(dot+bias,0)+0.25`。未读私有数学或 IR，未复制资格算子。代码在 root 自有 artifacts 目录，与产品和冻结 qualification 分离。

## 固定预算与运行方式

仅在 root 确认 qualification lease 已释放之后，于已验证 remote Docker 安装环境执行。当前不运行任何环境测试或设备任务。每个表格单元是一个新进程、一次 kernel 调用；不预热、不 autotune、不重复采样。选择 API，default 为 `profiler.start(... backend='cann', detail='auto')`；ordinary 不启动 profiler。两种模式都显式采用公开现有 probe 的 `enable_auto_blockify=False`，这限定本轮诊断范围，不声称覆盖 automatic blockify。

| config | M,N,K | BM,BN,BK | grid | State variants | modes |
|---|---|---|---|---|---|
| bm16 | 32,32,32 | 16,32,32 | 2,1,1 | scalar / vector / atomic | ordinary / default |
| bm32 | 64,32,32 | 32,32,32 | 2,1,1 | scalar / vector / atomic | ordinary / default |

上限共12个进程，即每个 config×State variant 的 ordinary/default 各一次。它把静态报告的第1组 scalar/vector 和第2组 atomic 合并使用同一公开源，**没有执行第3组 marker-only/counter 工程变体，也没有诊断 sidecar**。若任一变体在此安装版本上编译不支持，记录实际错误并停止该变体，不扩形状、不随机重试。任何设备故障立即交还 owner 处理。

单元命令模板（在远端批准的 Docker 内执行；`REMOTE_OUTPUT_ROOT` 由 root 指定，必须为新目录）：

```bash
python public_state_probe.py --device 4 --config bm16 --state scalar --mode ordinary --output "$REMOTE_OUTPUT_ROOT/bm16-scalar-ordinary"
```

仅按表格替换 config/state/mode，各单元一次。程序 `mkdir(exist_ok=False)` 拒绝覆盖既有单元。不要将单元失败改成额外 warm/cold重复，本轮没有随机 retry budget。实际设备、镜像、产品 commit/native/plugin hashes 和安装来源须由调度层保存，不由程序猜测。

## 实际记录与判读

- `source.py`、`plan.json`：保存本次源的 SHA、明确数学/shape/tile/grid/options/mode/State variant。
- `host-ledger.json`：唯一 call 前写 attempted=1，返回后 returned=1，同步成功后 synchronized=true。它仅是 host 调用证据，不能独自证明物理无重复执行。
- `launch-arguments.json`：记录 a/b/bias/out/state 的 Python实际指针、各 storage 范围、argument范围、shape/dtype。out/state 均有左右64元素 canary，State interior 独立清零。未提供actor probe。
- `result.json`：记录完整 State values（scalar/atomic为2元素，vector为1024/2048元素）、unique和观察性 equals_one；**State没有期望值断言，exit0只表示诊断完成且严格数学/input/canary通过，绝不是 qualification通过**。数学、输入和四个canary都用真实 `torch.testing.assert_close`；失败保存 traceback 并exit1。编译/launch/finalize失败均记录；未确认同步后不读取设备buffer。
- `compiled/`：保存本次 `CompiledKernel.asm` 可得格式的实际字节、hash，以及 metadata repr和compiled.hash，适用于ordinary和default。没有可得内容就不称保留完整原生编译产物。
- default 的 `capture/` 保留公开正常API原始产物；`generated/` 只从本次明确 `handoff.artifacts[].original_input/adapted` 物化LLVM，且必须是声明在本次 `/tmp/flagprism-ascend-compiler-*` output root内的`.ll`、通过SHA/LLVM文本检查。对象只取该artifacts的`driver_job.object`且必须处于同一声明root、suffix为`.o/.ll/.npubin`；所有路径和祖先拒绝symlink，解析后不可逃root。SDK/lib/archive/BC以及未知suffix（包括通用`output.bin`）均不复制，只留hash/明确excluded reason。`binaries-receipts.json`删去所有通用`data/llir`payload；不存在任意base64递归解码或cache扫描。缺字节明确标为不可得，不等同于不存在。

## 下一次有限静态审读清单

1. 对每种变体、每个mode定位 State最终GM目标和`SUBBLOCKID`/logical-pid定义；沿call与helper内部检查支配guard、election、每次实际执行次数。不能仅凭source rank0、helper名字、logger actor槽或State值推ownership。
2. scalar/vector先比较地址：vector能证明disjoint时只作control；scalar两个AIV相同地址且无election才支持多个physical writer。atomic必须独立审其helper/election，不预设“atomic一定两个actor都加”。只有actual lowering/actor证据匹配时才解释ordinary=1/profile=2的竞争机制。
3. 对default从`compiler_metadata.flagprism_ascend_handoff.artifacts[].argument_roles`及原/适配LLVM逐一绑定source index、FFTS prefix、final formal，追State与trace的GEP/GM地址及program/actor范围；比较用户state指针与本次launch inventory。**程序尚不能证明actual generated C++ launcher pack和运行时隐藏trace pointer的完整身份链**，这部分须从本次实际launcher/运行时可得产物另补；不修改default hook或用私有默认函数替代公开API。
4. 比较ordinary与default的user State helper、实际guard、SET/WAIT FLAG和barrier顺序，定位新增counter位置。留存真正可得的object/LLVM/launcher身份；无新decoder证据时不重试历史359项不支持的反汇编。

若实际普通lowering已非法复制rank0 State，仍需区分上游compiler source semantics缺陷与profiler增量问题；多physical writer不是用户源码合法race的自动证明。原资格失败gate、私有样例和论文保持不变。

## CPU-only静态审阅（本轮）

仅阅读源码完成以下检查，**未运行Python、syntax checker、imports、CPU数学或tests**；安装环境验证全部留给remote Docker。

- 唯一 `state_probe[(programs,)](...)` 调用点；没有warmup、定时API、循环launch、autotune装饰器或重试。
- 三个State分支由constexpr完全选择；scalar为 `State+pid` 普通RMW；vector为二维masked per-element RMW；atomic为 `atomic_add(State+pid,1)`，没有虚构actor intrinsic。
- 输入确定、无随机数；参考数学与公开kernel expression匹配；M恰为2*BM，N/K=32，所有tile和mask显式。
- 设备观测发生在同步成功之后且API finalize之后；finalize异常不会隐藏State观测，State观测本身不变成通过oracle。
- 产品路径无编辑；未改现有CPU/GPU资格测试；未进行任何设备调用或构建。

静态版本 source SHA256：`b09827d6f088e3b1d6484e8a3dbd8b341ce467e6eb6821164028dee2e49b774e`。该hash仅由文件静态hash命令取得，没有执行Python。
