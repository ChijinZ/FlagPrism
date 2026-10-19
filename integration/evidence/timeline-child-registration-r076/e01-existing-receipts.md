# NVIDIA E01 既有实际收据索引（R036）

范围：仅本地读取根 record T050、R036 Git/测试源、原 archive 的 JSON/raw/header/guard/SHA，索引既有 E01 事实。未 import/运行产品、checker/test、编译或连接设备；未新建测试、读取其它席报告或重跑数学/TP。请求配置沿用 GPT-6.1-Sol/xhigh，resolved unknown。

**NVIDIA 确实已有“同一 session 10次、两 specialization 交错”的真实 E01 正例。** 本席 R075 的“本次未定位精确收据”现已由本索引补上；不能继续表述为 NVIDIA 从未做过，或泛称三家均无此证据。本索引未审 GCU/Ascend 的精确10调用收据，不对它们作存在/不存在判断。

## 原件及源码身份

工作区根 archive：`artifacts/timeline/run-036/preflight/default-late-evidence-v1.tgz`，44,762,378 bytes；本席独立计算 SHA 为 `2262871440873535e387b47ebebf18b4e375814372fecf94f23ce22018809542`，与已跟踪 `FlagPrism-method/integration/evidence/timeline-default-late-r036/README.md`、根 T050 一致。

原实际 v3 测试源在 archive 内：

`inputs/install-public-input-v3/source/tests/timeline/p01_nvidia_late_default.py`

SHA `76e71dc20cd0edcb24154efe2a3e114625c5dae73c057dfd8b451a04a245e15f`，与 Git `a3da48d:tests/timeline/p01_nvidia_late_default.py` 逐字节相同。不是以今天已加强的 `inspect()` 倒填旧检查：Git diff 显示后续增添了 compiler receipt、64MiB bundle、counter-ns 检查及压缩 decoded reader；数学、10次交错循环和逐call oracle 未改。

实际原调用循环位于上述旧源109–116行：ordinary10、profile10、warm_session2；profile 与 warm 各只有一次 `profiler.start(..., detail='timeline')`，并在循环结束后 finalize。偶数次使用 `(N=1003, B=512, num_warps=4)`，奇数次 `(N=513, B=256, num_warps=8)`；对应 grid2与grid3，实际首末 program 为 `[0,1]`、`[0,2]`。`N/B` 为 constexpr，因此是同一普通 nonlinear kernel 的两种真实 specialization，不是10个独立 session。

每个 nonlinear 调用均有独立 CPU-double reference/tolerance、input 不变、输出 tail、每 program 的合法 atomic call count `[1]*grid+[0]` 检查。host-once 文件在测试 workload 开头写入；每个 phase 的数学/input SHA 保存在 frozen-inputs。普通与profile各自生成输入，不能据此说两phase输入字节相同；E01所需的逐调用合法性及隔离检查仍成立。

## 两次已有实际成功，不重跑

以下路径均为上述 archive 的 member。

| 原 attempt | terminal / installed result | 实际数学和 capture |
| --- | --- | --- |
| `runs/install-public-v1` | terminal0；610 wheel members；wheel SHA `5eab7acda5f8df9ee64364cf49470a064db1929d39cf76be1cd2ad880ba21cec` | ordinary10 + profile nonlinear10 + Softmax1 + warm2，共23个显式数学调用；首profile session11 captures，warm session2。 |
| `runs/install-public-v3` | terminal0；611 wheel members；wheel SHA `f6bedc677e2615f01234709a05dd38d6cc4ca996eab2ddc8186f6238ae49f306` | 相同23调用结构及逐call oracle全部通过；前10 capture 两binary严格A/B交替，第11个为独立Softmax binary；warm2复用这两个nonlinear binary。 |

可直接定位的 v3 原收据：

- `runs/install-public-v3/terminal.json`，SHA `b9e929ee99f50cde65f12d1621c9ba3ea9bbc56c5715e0667f0567ce82438003`。
- `runs/install-public-v3/output/result.json`，SHA `58f0e5aae5865e4eade76fba3dc28229b883d0cf86759764857a24d7dccca693`，标明正常 wheel/611成员、新 standalone native 实际构建、core ABI3复用。
- `runs/install-public-v3/output/default-device/result.json`，SHA `508a3f0726a6b334b792c67854900031e6034a9cd82546afb5167066b2bfdaa2`；23条数学结果均 `math/guard/input=true`、`explicit_launches=1`。
- 同目录 `frozen-inputs.json`，SHA `f58e6a6996581b48cb14efaac3f980f90a4e0288a28f99700daa83e29978d8e8`，逐项保留phase/index/两组参数/input SHA。
- 同目录 `profile/timeline/index.json`，SHA `4e284e48a5bca87ddfd4a4bfacf749ce4c576a8585bd2aadab29db1a4b003132`：11 captures，同一 capture_id，pending_decode/retained_owners/failures 均空。
- 同目录 `warm_session/timeline/index.json`，SHA `c50c082b219e82d94d385b5526fd51da99e535bd5ef5753d57c8fddadb5047d7`：独立warm session2 captures，无待解码/残留owner/失败。

v3 的A binary为 `688269621aa8df7a64ad68e7919482d8323e75b54d29fc3c12da0447f2e1237a`；B为 `fb7bda257efb6c6472acc804c18d79cf337ece5eb4aeea7b46a6d60301bc820e`。前10项各5次，分别绑定实际stream `96401628726688`、`96401628252336`；Softmax为第三binary且stream0。13个capture各有独立 owner invocation，launch association 的 binary 与 owner/index一致；warm 的session_ids为[1]，首session为[0]，不是把warm两项补进首session十次。

本席用 stdlib 读取 v3 的13份原raw及guard：每份raw SHA/长度与capture/owner一致，guard均为128个0xA5；4actor、capacity256、header magic/program/actor/count/overflow字段均与 admitted slots一致且无overflow。前10项 A/B 每次分别80/32个实际记录，Softmax456；首11份raw共725,120 bytes，warm2共131,840 bytes。该核对没有调用产品 decoder，也没有新设备执行。

## E01可复用的精确范围

可复用：在当时正常安装的公开默认timeline路径上，同一session十次交错specialization的独立调用/二进制/stream/program/raw归属，逐call数学/input/tail/once和安全finalize；另有独立warm session的同binary复用。该证据是实际设备正例，不是CPU fixture或R056十个独立任务的合计。

不由它授予：十个同时pending owner、无host wait的并发保持、源边界、当前ns/clock/shared epoch、动态时间箭头或UI。测试每次以`.cpu()`检查结果，不能把它称为十次全在途并发测试。R036本身明确是raw stage，无当前晚期时间资格；这些资格使用各自已有后续证据，不能从E01外推。

## 当前预算差异的范围说明

原每capture是4actor/cap256/首末两slot，raw65,920B，另guard128B。当前source61cb831沿用的 sampled default为cap4096（`timeline_nvidia_late_compile._automatic_pair_budget`），同两slot变为raw1,048,960B+guard128B；`LateTimelineHook` 与公共pool继续限制session累计物理记录8MiB。

据当前静态公式，原几何8次需8,392,704B，已超过8,388,608B，故在该次launch前拒绝是正确预算行为。R036历史成功不能改称“当前default用原几何可完成10/11capture”。这只是版本/容量适用范围变化，**不推翻历史E01、不构成新confirmed bug，也不新增预算桥或扩maxraw工程要求**。

E01允许使用一个program的两种合法constexpr specialization。当前4actor/cap4096的单program每capture raw524,480B+guard128B，十次合计5,246,080B，理论上在原8MiB内；该计算不冒充当前实际捕获。若后续确需当前版本的精确10call收据，只须定位已有预算合规收据，或按root后续授权使用这类最小已有recurrence场景；不要求重跑R036的23数学/旧13capture、独立数学矩阵或已通过TP/UI，更不要求改预算。

本索引关闭的是“NV尚未定位任何精确E01历史正例”这一证据检索缺口。未执行当前producer或离线产品重导，因此不声称本轮新取得当前10call设备资格。P03、ordinary关键依赖及其它backend的具体E01范围均不在本次补项中改变。
