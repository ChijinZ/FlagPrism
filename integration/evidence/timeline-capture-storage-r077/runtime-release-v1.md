# R077 release retry：有限 runtime follow-up

请求配置 GPT-6.1-Sol / xhigh；实际 resolved 配置未暴露，unknown。只读本 delta、直接收据和所需 owner/transport 周边；没有运行产品/测试/SDK/设备、连接服务器、阅读其它席报告或修改实现。此报告不重新打开 whole review。

## 身份与结论

观察冻结 `c42ba7e5cdf319fbc409d1b1b2132531837c8a03`，相对 `16ebe2288be73a3aa992e151a56a4e4196898417` 的两文件增量：

| 文件 | 观察 SHA-256 |
| --- | --- |
| `Profiler/python/flagtree_profiler/hooks/timeline.py` | `34e56a11a86da1a995cd5d6859da57c4e08b736d9b7052d69109efa8b99fae34` |
| `tests/timeline/test_timeline_finalize.py` | `dd900653b4b7765ce36d9d31460fe2630b3a1b2dcc624246b1481fd2df576e6a` |

新 pending 分支在静态上修复了已证的 immutable-input 重写阻断：加载既有 input/CAS，检查现有原件，再尝试 transport release，保持 input 字节和 pending 不变。尚有一个具体产品检查遗漏（M2）和一个新 guard fixture 的设置问题（T1），均已即时告知 root。当前不能记为最终验证已闭；没有新增设备或数学要求。

## 已证原问题及新分支

实际打开 `preflight/enflame-install-failure-v1.txt`（SHA `97544a60ed6bd9a0e5d6a164740aa4d357e59cde7a673e4df1ac0de9e5194df4`）：49 项中 48 pass / 1 fail，失败为 `test_release_failure_is_owned_and_not_decoded`。首轮 release 错误保留 owner，后续 snapshot 新增/改变 error 和 release_status，第二轮重新序列化 input，触发不可变文件拒绝覆盖。该问题在普通假 transport 上成立，不能归因于硬件，也没有证据证明由 CAS 新引入。

新路径保持此前完成/readback 前置条件：`TimelineOwnerPool.read` 对 raw_ready 直接返回已取得的 host bytes，不重新调用设备 readback；随后比较保存的 owner 身份、descriptor metadata/launch、raw 文件名/hash/内容、guard 文件名/大小/hash/内容及 retained compiler artifact SHA，再调用 pool.release。释放成功才删除 descriptor；pending 留给正常 decode；释放失败仍被 flush 登记并跳过该 owner 的 decode，其它 owner 继续。这些顺序没有增加同步、重放或释放成功的假声明。

本 delta 不改变 native unknown-outcome 语义。已读 `Debugger/lib/Runtime/TransferEngine.cpp:1349–1385`：既有 native releaseFailure 会在再次 SDK free 之前报错，未知结果继续 quarantine；本 Python 分支不会把未知 native 释放错误变成重复 free。CPU fake transport 的可恢复释放失败不等于证明 SDK unknown outcome 可安全重试。

## Confirmed product finding

### M2 — major：pending 分支未验证会影响后续解释的 owner 采集事实

- 位置：`hooks/timeline.py:246–252` 只比较八项 `capture_id/invocation_id/binary_id/function/plan/layout/device/stream`；`_decode_timeline_original` 后续直接读取保存的 `owner.submission_outcome` 和 `owner.readback_integrity`。
- 触发：第一次保留 raw/input 后让 transport.release 报错。只改 input 的 `owner.submission_outcome`（例如 aborted → returned）或 `owner.readback_integrity`（invalid → passed）；保留 raw、guard、metadata、launch 和上述八项身份不变。当前比较不会发现该变化，可进入 release 并让 decode 消费被改的采集事实。与本轮已有 metadata/guard 篡改 negative 属于相同 retained-input 故障范围，不是新增攻击模型。
- 后果：错误/取消或 readback-invalid 的解释门可被保存文件变化绕过；也违反“核实原件后才释放”的本分支合同。读取已获得的 raw 并不能认证这两项 snapshot 事实。
- 最小修复/验证：与 live raw-ready snapshot 比较 owner 除明确可变的 `error` / `release_status` 外的全部字段，或至少补上上述影响解释的不可变事实；增加一个 CPU owner-fact tamper negative，要求不释放、不解码，恢复原 input 后按原资格处理。无需 SDK/设备/新矩阵。本席未运行复现；结论来自明确的字段读取和分支路径。

## Fixture 问题（非产品缺陷）

### T1 — guard negative 的 admission 与 readback 不一致

`collector` 使用默认 `TimelineOwnerPool(transport)`，其 guard_bytes 为 0。新 `fault='guard'` 却返回 128 字节 guard 的 `TimelineReadback`。`TimelineOwnerPool.read` 因而必记 `guard_extent_differs_from_admission`，saved owner 为 readback-integrity invalid。损坏 guard 的第二轮能拒绝 release；但恢复文件后的第三轮即使成功 release，decode 仍应抛 readback integrity ValueError，而当前测试末尾要求 flush 正常返回。

最小调整是让该 fixture 的 admission 实际声明 128 字节 guard，并保持物理预算一致，然后验证损坏拒绝与恢复成功。不能为了这个测试放松产品的 guard 检查。

其它三类新 negative 已读：raw 损坏经 bytes/hash 比较拒绝，CAS 对象损坏由 reader 拒绝，metadata 改动与 descriptor 不一致拒绝；恢复原字节后重试。原 release testcase 新增 input 字节冻结比较，覆盖“不重写原件”。这些都是 CPU fault 测试，不构成真实 SDK 释放恢复证明。

## 直接收据与仍待项

- `preflight/release-fix-poll-v1.json` SHA `003fdc412ece7fdbeb21fd51b6f656ea5c6921a4c03ecd8e009e7ac72bef6d00`：terminal 0；明确 source_loaded=true / normal_install=false / device_executed=false；normal 与 `-O` 子命令均 0。
- 实际检查了 `release-fix-input-v1.tgz`（SHA `62a57c0f09788821894fed98253a883aea4f17509c049ca170612077aa2f21ac`）的 runner、source loader、hook 和 test 成员。该包 hook SHA 为 `3cd8e10c6e6133813caf6a7c65d6a30bce4a34cc836da35fac207599ed8ecd9f`，test SHA `72c86cb86c6cee91bf1c317a7a4e2e3d1606ce73284e35178f21287f6f00c624`。它执行一个 release 正向恢复加 raw/object 两类 negative，共三项；没有覆盖后来 metadata/guard 加强版本，更没有覆盖 M2。
- 实际读了 enflame install-poll-v1、nvidia install-poll-v2、ascend install-poll-v2：三份均已 assemble/install/import 成功（分别 498/642/440 members），随后 capture-store-normal 步骤失败，whole terminal 均 1。保留该失败，不能将“产品已装包”描述为本轮验收全过。

最少剩余项：修正 M2/T1 后，最终源码与正常 wheel 字节对齐，执行定向 common recovery tests 的 normal / `-O` 并保留失败原件。既有预算修复/codec 安装 closure 沿原报告更新，不要求重数学、TP/UI 或旧 workload 矩阵。

本席只读两文件 delta、owner read/release/flush 周边、相关 native unknown-outcome 分支与上述直接收据；没有重做三后端全审。原 whole 未完成结论及 P03/ordinary 依赖边界缺口保持。

## M2 / T1 有限 closure — ea2c936，native-install-v3

本节追加新结论，不删除上述失败历史；只关闭本报告的 M2 / T1。实际读取冻结 `ea2c936edc3a5bbd695cb46a3758bfd2a6d1196c` 相对 c42ba7e 的两文件 delta、相关源码、三个 v3 输入包及以下三份完整收据/测试日志，没有运行产品或测试。

新 hook SHA 为 `b38b5726e437df3b024fb1c0bc913504f38c6fe26b3d1ebe489d655cf6d3f7e4`；新 test SHA 为 `a5cc3a0813ad8b73dabc047cd7fa555a7b7d1c1d2e085a6aa9c280146bc60452`。三个 `*-install-input-v3.tgz` 中这两文件均逐字节等于该 Git freeze。其 runner SHA `3197d2e45214177eabc4466f68d19846385758ea980a318ad60cf3fa6d82b47e` 与三份 terminal 一致。

- **M2 已关闭。** 新分支比较完整 saved/current owner snapshot，仅剔除明确可变的 `error` / `release_status`，不再限于八项 identity。submission outcome、readback integrity 及其它保留采集事实的变化都会在 release 之前拒绝。新增 `owner_submission` / `owner_integrity` 两种 negative 要求篡改时保留 owner，恢复原 input 后正常释放；显式异常/状态检查在 `-O` 下仍执行。完整等值比较也覆盖与 fixture 相反方向的事实改变，本席未要求新增矩阵。
- **T1 已关闭。** 仅 `fault='guard'` 的 fixture admission 通过 callspec 声明 guard_bytes=128，其余测试仍为 0；所返回 128 字节 guard 与 admission 一致，raw/guard 物理预算由同一 pool 正常计算。未改产品 guard 规则或上限。原件损坏拒绝、恢复后释放/解码的原测试语义得以成立。

| 直接收据（相对 R077 preflight） | 收据 SHA-256 | wheel SHA-256 / installed members | normal / `-O` |
| --- | --- | --- | --- |
| `enflame-install-poll-v7.json` | `79921bbfbadfcec1770e4c864913a2bef58c566d16ba8898b15f0e94efa89bc2` | `b2cfb644e549d91b57fdf762c8ba0381a032fc4c87a737cdbc948a557005ab46` / 498 | 各 55 passed + 11 subtests |
| `nvidia-install-poll-v8.json` | `276800c5551a5213f361a7672cf0645b790afa9c3243e5d416e3d3ffd406e451` | `a7ba28dafaa63884b8a7bb9cef3a1876c8f1f3380c31ee3ab4f545b138ef7956` / 642 | 各 55 passed + 11 subtests |
| `ascend-install-poll-v9.json` | `88c0aabc7f6e199dafdfc828f65f113ee99c76c68c222b98332940327ea89e2b` | `f789488c98351b80e1e5651b2d737ceb5db84979dbef46ecf7d80d2d480c2938` / 440 | 各 55 passed + 11 subtests |

三份 `terminal.json` 均为 terminal / returncode 0，`output/result.json.source_commit` 均精确为 ea2c936，`output/steps.json` 与 result 内 steps 一致，每一步均 0；包含 assemble、正常安装、installed import、normal 及 optimized common regressions。实际读了 runner：它移除 PYTHONPATH、以新 venv 的 `-I` Python 运行测试，并在测试前逐 wheel member 比较安装字节；不是 source-loaded 替代。日志 warning 为 `-O` 提示及 Asc 既有 escape deprecation，未出现失败；三份 stderr 为空。

这足以关闭 M2/T1 的源码及三后端正常安装 CPU 验证缺口。在这两个修复的有限范围内未发现新的具体缺陷。既有 install-v1 失败和 c42/guard 测试失败仍保留；本节不把它们改记为成功。native 输入明确复用，`device_executed=false`；没有新的 SDK/数学/TP/UI 资格，原 whole 未完成与 P03/ordinary 边界结论不变。
