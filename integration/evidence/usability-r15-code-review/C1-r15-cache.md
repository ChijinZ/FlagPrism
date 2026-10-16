# C1 r15：Ascend compiler identity/cache 独立工程走查

审查对象：canonical `FlagPrism-method`，branch `detailed-profiler`，commit `2ddb52b6544ef273399757052a0f66ff3b97f2d9`（base `4576e8904398ab4aae39e6994818eb37e4756a54`）。本报告先冻结该 commit 的原始结论；后续修复只能追加带 revision/证据的 delta，不能覆盖原 finding。

结论：**1 个 confirmed major（C1-R15-01），未发现第二个已证实 blocker/major。** 原 commit 不能据现有 42-pass CPU suite 获得 compiler-selection 兼容性通过结论。其余 identity/JIT/watch/fork 实现的有限静态审查未发现已证实 stale-cache 缺陷。此结论不覆盖整体产品、fresh wheel 安装、新 SDK/native/hardware，也不关闭既有 Ascend 44 profiles 中 2 个 State failures。

## Confirmed major：C1-R15-01

**realpath 改变 compiler basename，使合法 symlink/versioned executable 被旧有类型判断误判，两个实际 linalg 编译路径都会失败。**

定位（canonical patch 行号及其实际 patched-source 行号）：

- `FlagPrism-method/integration/patches/ascend/flagtree-source-census-v2.patch:510–517`：新增 helper `executable_path()` 在 513 行 `realpath()`，返回真实文件名；对应 `final-freeze/compiler_identity.py:150–157`。
- 同 patch `569–582`：override 和既有 packaged/PATH/legacy selector 都返回上述规范化路径；对应 `final-freeze/utils.py:217–236`。
- 既有 `final-freeze/utils.py:249–255` 的 `_is_valid_bishengir_path()` 必须 basename 恰为 `bishengir-compile`；三个能力探测于 262、285、551 行使用它。被拒后探测返回 False，而不是执行实际 `--help`。
- 同 patch `226`、`263` 的 `bind_compiler_identity()` 也返回 realpath，随后既有 `endswith("bishengir-compile")` 分支继续依赖规范化后的 basename；对应 `final-freeze/compiler.py:535–541`、`752–759`。
- 输出类型由能力探测决定：`final-freeze/compiler.py:396–399`、`609–616`，误判后期待 `kernel_reloc.o` 并采用旧能力结论。

触发：例如 PATH 或 packaged 路径中的 `bishengir-compile` symlink 指向 `bishengir-compile-428`，或者显式 `TRITON_ASCEND_COMPILER` 选择该合法 symlink/versioned executable。真实程序保持相同且具有新能力，单是 real basename 不等于固定名称便足以触发。

后果：原来通过 `bishengir-compile` symlink 工作的默认 PATH 选择出现兼容性回归；新 override 也接受路径却错误组装参数。在独立 CPU 复现中，两个实际 linalg 函数都漏掉 `--enable-hfusion-compile=true` 和 `--enable-triton-kernel-compile=true`（A2/A3 同时漏 `--reg-based=true`），并在 stub 编译器退出 0、实际写出 `kernel.o` 后错误查找 `kernel_reloc.o`，抛出 `CalledProcessError(returncode=0)`。这是 selector/capability/command/output-path 的真实执行结果；并非假设真实 SDK 会采用何种错误行为。

独立复现已在服务器 Docker `chijin_v3.5.x` 的 reviewer 独立目录 `/tmp/chijin-r15-c1-cache-review` 完成，整体 exit **0**（即所有预先固定的 red/green 对照断言均成立）：

| CPU case | 结果 |
| --- | --- |
| 原 0364 utils，默认 PATH symlink → versioned target | 三个实际能力探测均 True |
| 新 utils，同一默认 PATH symlink | 三个能力探测均 False，打印 Invalid path format |
| 新 utils，直接路径 basename=`bishengir-compile` | 三个探测均 True |
| 新 utils，显式 override 同一 symlink | 三个探测均 False |
| 新 compiler，两实际 linalg 函数，直接标准 basename | 均成功返回相同 stub binary bytes，参数包含 modern flags |
| 新 compiler，两实际 linalg 函数，symlink → versioned basename | 均误等 reloc 输出而失败，参数缺失 modern flags |

两个 executable 的 stub bytes 相同（SHA256 `531930fc55db5056ceabed1c71f79195f6bfa6f0de70d71c0080e8f6450c0481`）；它真实响应 `--help` 并真实执行写出输出。仅 linalg metadata parser、NPU architecture query 和外部 SDK binary 是显式 fake 边界。实际 selector、三个能力函数、fingerprint/bind、两个 linalg 函数的命令生成、subprocess 执行和输出检查均使用原 staged 产品源码。`torch_npu.npu.is_initialized()` 在结束时为 False；无 native build、设备编译或设备 workload。运行时 import 向 stderr 输出 `can not use command: npu-smi info`，未隐藏该诊断。

最小修复建议：继续使用 realpath+SHA256 作为身份，但将“compiler family/capability”和“规范化后的文件名”解耦。让实际能力探测及两个 modern-option 分支识别选中 compiler 的真实能力，或明确保留并携带解析前的 selection kind，同时维护 legacy `npuc` 行为；仅放宽 selector 测试不能修复后续分支。增补从默认 PATH/package symlink 和 override versioned path 贯通真实 capability probe、实际命令参数、预期输出文件的 CPU regression。

## 原测试证据有效性与边界

已读取 `compiler-identity/REPORT.md`、`final-quality.log`、`final-cpu-r3.log`、`root-frozen-byte-audit.json`、freeze helper/compiler/utils，以及 canonical 6-file diff。canonical fullpatch SHA256 为 `f1202919fead694f6a430b588e2e4db8fa7764a49ac481c518b4bf72aee58b9b`，与 root 冻结审计一致。

42 passed / 0 skips 是有效的 **CPU specialization/selection/receipt** 证据，不能当作 actual SDK/native compile 或 fresh installed wheel 证据：

- `test_auto_blockify_cache.py:27–74` 为 generic/Ascend 两真实 JIT module 分别加载实际源码，并仅替换 binder、driver/compile 边界。两个真实 `JITFunction.run()` 的 normalization 在 `compute_cache_key` 前发生；`kwargs.update(options)` 把相同绑定传给 parse_options，持久 key 由含 identity 的 `NPUOptions.hash()` 生成。测试确实检验缓存选择。
- identity 新测试覆盖相同 bytes 不同路径、原路径原地同尺寸修改与 mtime 恢复、强制同 stat key、冷热复用、失效后重试、并发首读、watch init/add failure、overflow、64-watch 上限和持锁 fork。原 stat-only 两个 actual-JIT failures 的保留日志未被最终测试掩盖。
- `test_override_realpath_and_stock_precedence():47–71` 只断言 selector 返回路径。JIT 测试把外部 compile 替换成 `SimpleNamespace`，receipt 测试只检查 identity 转存，因此现有 42-pass suite 不执行本 finding 的能力探测/编译参数/输出检查路径；其全绿与本 finding 不矛盾。
- wheel assembler 添加 helper source/stage/wheel 字节映射是合理的打包约束，但已读取日志明确只是 `standard build_py` 和 Python stage；本轮不把它提升为 fresh wheel install。

watch/fork/资源有限走查：单 `_LOCK` 保护 cache/watch 变更；单 nonblocking CLOEXEC FD，无 watcher thread；watch add/init/read/overflow 失效会清 cache 并退回每次 fresh hash；hardlink 同 wd 会先清旧名称 digest；淘汰同步删除 digest；`register_at_fork` 重置 child lock/watch/cache。三次有界读取对照 open-fd/path stat 与 epoch。就所读源码和现有 CPU 证据，未确认这些路径另有 blocker/major。未将未复现的跨文件系统语义、并发安装窗口或极端 fork/FD 时序当作 confirmed finding。

## 待证和本轮未覆盖

- C1-R15-01 修复后的独立原 fixture 复核尚待精确 source/diff 与 Docker 证据。
- fresh official wheel 创建、安装及安装后测试由另一 agent 执行；当前报告未取得结果，故仍 pending。
- 新 Ascend SDK legality patch、实际 compiler/SDK output、ordinary/profile 硬件 upgrade regression、GPU 工作均未在本轮运行或审结。
- fingerprint 明确只覆盖选中 executable，不涵盖共享库、bitcode 等整个 SDK 的身份；本轮未把这个明确范围限制误列为 bug。
- 未读取论文、private qualification math/IR 或 PRIVATE archive；未改产品代码、installer 目录或运行本机 Python import/pytest/py_compile。仅运行本机 Git、文本/归档/字节检查及获准的 `study_remote.py` 传输工具。

## 可复核附件

- `C1-r15-cache-repro.sh`：固定 case 的完整 remote bootstrap/script；SHA256 `58c9b9ce28c0bba6f540138ae19a48757d62d7fde5c5e1b3cbab987bab829a85`。
- `C1-r15-cache-repro.log`：实际 stdout、actual argv、每个 subprocess exit/stdout/stderr SHA、source SHA 和 NPU initialized 断言结果；SHA256 `8f4d933f714ef9713f27c6021ee4902a092ae546cbaa92d54125dbb0097f25c0`。
- `C1-r15-cache-repro-freeze.tgz`：remote 原 script、结构化 result、三份实际 imported product source、0364 utils baseline、stub bytes 与 symlink；SHA256 `b52dbd88645abb8da1cb69dc6cacb816daec7e1b402b839499f40a620c304b70`。

执行命令（exit 0）：

```sh
python scripts/study_remote.py zhiyuan_ascend \
  --command 'sudo -n -u chijin docker exec -i chijin_v3.5.x bash -s' \
  --stdin-file artifacts/usability/run-013/final-code-review/C1-r15-cache-repro.sh \
  --stdout-file artifacts/usability/run-013/final-code-review/C1-r15-cache-repro.log \
  --timeout 90
```

执行前脚本强制校验三份 actual imported source SHA（与原 freeze 相等）：compiler `3cd803dc08d612c0e2c1056c8a0850beefe0b72b98af537948c0cfe640fa5a99`；utils `228365237261580bbdebade8ff2a4b288f9b61153fb1993c380faa843f6f99d2`；helper `9ecc943ea025c45c3c073a4a99ac47bb897c1ffb1b65272ccb813e5812c9d46b`。

## a829a331 修复与实际 installed wheel 的追加复核

审查 delta：canonical commit `a829a3312af69c1b961919025053829d7096a2b1`（parent `2ddb52b6544ef273399757052a0f66ff3b97f2d9`），完整 patch SHA256 `46d354d2c183a619f2b5494f22efc8f1cd3ac743520d9afbba745194afb89959`。**C1-R15-01 在此 revision 的已审 source、staged CPU 和实际 installed CPU 边界内关闭；未发现修复 delta 新增的 confirmed blocker/major。** 原 finding/red 证据保留，原三份附件 SHA 未改变。该关闭不表示 SDK/native/hardware 或整体产品通过。

静态修复核对：

- actual frozen/installed `utils.py:251–256` 删除 basename gate；`259–286` 用同 executable fingerprint、PATH、LD_LIBRARY_PATH 缓存最多 64 份实际 `--help` 输出，实际 subprocess 有 `timeout=30`、`check=True`，失败/timeout/OSError 显式报告并保留 stderr，不会缓存异常后静默走 legacy。探测后再校验 compiler identity，拒绝 probe 期间变化。
- 三个能力函数共用同一 helper；`compiler.py:538`、`755` 两个分支以实际 help 中同时存在两个 modern flags 为条件，不再依赖文件名。identity helper 字节未变，原 JIT/cache/watch/fork 路径未被本次差异替换。
- 新 `test_compiler_capabilities.py` 包含 8 个 actual-linalg×selector cases、2 个现代→legacy 同路径字节刷新 cases、probe stderr/retry、timeout 参数和 PATH/LD_LIBRARY_PATH 各自失效测试，共 14 项；原 42 项保留。`capabilities-final.log` 的 Docker **56 passed / 0 skips**、`capability-freeze.log` 的 fresh clone 单次完整 patch 与三份测试 source 相等检查已读取。timeout case 检查传入 30 秒并模拟 TimeoutExpired，不等价于真实等待 30 秒的 kill/lifecycle 压力测试；这是本轮证据的明确边界。

### 独立 staged red/green 对照

在原 reviewer prefix 的新子目录 `/tmp/chijin-r15-c1-cache-review/green-a829` 运行 `C1-r15-cache-green-a829.sh`，exit **0**。脚本先强制验证并冻结实际 staged `compiler.py` SHA `02d7914f9f434dbcd0e02bb354d349fd781b5544d9788232f591dd0907ad6ee9`、`utils.py` SHA `fca32bdb878c54015479c89298d97c4e69791bfbab15d65f7063c271990dfc9c` 和不变 helper SHA `9ecc943ea025c45c3c073a4a99ac47bb897c1ffb1b65272ccb813e5812c9d46b`；old 产品代码来自原 C1 red 冻结文件，并独立检查原 SHA。未改原 product/stage/source 目录。

- **原 stub 字节完全不变**（SHA `531930fc55db5056ceabed1c71f79195f6bfa6f0de70d71c0080e8f6450c0481`）：新代码对 direct、override symlink 和默认 PATH symlink 的三个能力判断均为 True；direct/symlink×两个 actual linalg 函数共 4 个调用全部成功返回 `fixture-kernel`。
- 对原 fixture 的 modern flags 预期作了必要区分：它的 help 仅含 api-change/regbased/save-IR 三个 marker，**没有 advertise 两个 modern compile flags**。新实现以实际能力为依据，因此本 fixture 正确不追加这两个 flags。输出类型恢复仍由同字节原 fixture 直接证明，未把原不完整 help 样本当成完整 SDK 能力。
- 另建完整 help fixture，仅在同一 stub 的 help 文本加入 `--enable-hfusion-compile`、`--enable-triton-kernel-compile`（SHA `ad7efc619f85f9989ae43c89c2272e66fb25dd879f9cf73ca6cb7e50ae44addc`）。同一完整 fixture 同时对 old/new source 执行：旧 2ddb direct 两函数成功，symlink 两函数重现原 missing-flags/reloc 错误；新 a829 direct/symlink 的 4 个调用全部成功且实际 argv 均有两 flags。原 red 未因调整 fixture 被抹除。

该独立脚本共 15 个固定对照 rows，包含预期重现的两个 old-source failures；整体 exit 0 表示所有预定结果断言成立。真实选择/能力/身份/命令/子进程/输出校验，fake 边界仍仅为 metadata parser、NPU architecture 与外部 stub binary；结束时 NPU initialized=False。

### 正式 wheel 证据与 reviewer 的窄 installed 检查

本轮已取得并阅读 `compiler-identity/install-v2-evidence.tgz`（SHA256 `ffbe5dddad9195715413701050c84ddffb6cc7fd94e2699a3ca7e49b51b55afb`）及展开的 controller、audit source、installed receipt、56-pass log 和 terminal confirmation。不同于上轮 Python stage，这次是从 canonical a829 archive 组建的实际 wheel，经新建 venv 中 `pip install --no-deps` 后测试：

- wheel SHA256 `bbd3ff08a15f2cb174be3d63d527540935f2811d8a0356772d7749a85b1a7a14`；import 路径位于 `/tmp/chijin-r15-compiler-identity-install-v2/venv/lib/python3.11/site-packages`。
- 保留 audit 实际比较 1049 个 Git blobs、380 个 package members 的 stage/ZIP/installed 字节、249 个 Python source 的 intended source 字节；107 个 native wheel members 与先前 audited wheel 相等。controller 明确 `native_build=False`，重用 native 由 native-source/compile-dependency/link-input bridges 约束。这是 fresh **Python-only wheel/venv install**，不宣称新的 native C++ 编译。
- 该 venv 的原 identity/JIT/capability suite 使用 installed bytes，receipt 测试只对原显式 fixture loader 作安装路径 relocation；`installed-56-cpu.log` 为 **56 passed / 0 skips / 2.01s**。terminal confirmation 的已知 controller/child PIDs 没有 live/zombie rows。

reviewer 随后独立运行一次窄 consumer 检查 `C1-r15-cache-installed-a829.sh`（新子目录 `installed-a829`），exit **0**：使用该正式 venv interpreter 的 `-B -I`，显式移除 PYTHONPATH、FLAGTREE_PLUGIN、FLAGPRISM_TEST_ASCEND_PARENT；实际 triton、flagtree、compiler、utils、helper 的路径均强制在该 venv site-packages 下，三份产品 SHA 与上述修复 source 相等。无 staged sys.path 注入、无本机 import。

此 installed 检查仅对原 stub/完整 help stub 各做 versioned-target symlink×两个 actual linalg 函数，共 **4 successes**：原 stub 正确读出 `kernel.o` 且不加未 advertise 的 modern flags，完整 help stub 的 argv 正确有两 modern flags；所有 binary SHA 相同，NPU initialized=False。未重复完整 suite。两个独立 Docker 运行仍各产生 import 的 `can not use command: npu-smi info` stderr 诊断；无设备编译或 workload。

追加证据：

| 文件 | SHA256 |
| --- | --- |
| `C1-r15-cache-green-a829.sh` | `d9766f8d7c21d4d21d06e60d44187df8cec1bd5c2ae8d24ee76ed6c4cbd83349` |
| `C1-r15-cache-green-a829.log` | `01648a28647a6b00713e69707a10809dcc2bc5ab2cf2460553e3494c9f17a818` |
| `C1-r15-cache-installed-a829.sh` | `374a8dfa78d68a078ffecb8b1058e4d1881125d4c8243c88f496af807b9ec98e` |
| `C1-r15-cache-installed-a829.log` | `4aa481807fd39133d2b4de6f1f96e5e18a0349050dc7f561a1c45202555b71cc` |
| `C1-r15-cache-a829-delta-freeze.tgz` | `30e28671a20833c56837e6bbbc7d01dff060704d821d0f8087c9a622cd1eca45` |

delta freeze 内含两份 remote script/result、实际 imported 新旧产品 source、所有 stub bytes/symlinks。原 `C1-r15-cache-repro{.sh,.log,-freeze.tgz}` 的 SHA 与初轮报告保持相等。

当前未覆盖范围保持：新 Ascend SDK legality/native patch 与实际硬件 ordinary/profile upgrade regression、本来 44-profile 中两个 State failures、GPU、整个 SDK 依赖身份。**C1-R15-01 的有限修复闭环与这些未完成事项分别记录，未以 CPU 安装通过替代硬件结论。**
