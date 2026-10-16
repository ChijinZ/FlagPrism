# C3 r15 — compiler identity / SDK 交付与安装走查

2026-10-16。当前为静态交付审查 checkpoint，等待 SDK resources / 最后 freeze / 实际安装与原样回归后的有限 delta。

本 reviewer 只读 Git、源码与已留存的公开工程证据字节；未在本机 import、py_compile、pytest、构建或执行 SDK，未运行远端 CPU/NPU/GPU，未读取私有资格数学、IR 或 PRIVATE archive，未修改产品或论文，未派生 agent。唯一写入是本报告。远端运行结果以下明确区分已留存文件与 root 的即时状态通报。

## 当前判断

compiler identity 的公开源码入口与已安装 wheel 证据相符，未发现这部分新增的已确认 major 交付缺陷。正式安装是 **Python-only refresh**，不是新的 C++ build；该边界在报告中已明确。r13 开发路径存在于本次 native reuse 审计控制器，但没有成为用户的唯一安装路径：公开 `build_from_source.py` 从固定上游 source + 显式 LLVM/CANN dependencies 构建，另有完整命令。

SDK legality 工具目前仍是进行中的工程 recipe，尚不能作为普通用户可照做的完整新 toolchain 安装。发现两个当前交付阻塞：新 prefix 缺实际 codegen resources 的明确合同；强制 baseline gate 的公开 input/reference 及完整操作链没有随 recipe 交付。它们不等同于已证明的 legality 算法错误，也不因尚缺 NPU 验收而虚构产品 bug。原 Ascend 42/44、两次 State fail 保持 open。

## 已确认交付问题

### D1 — 新 compiler prefix 的 codegen resources 尚无可执行安装合同（major，当前 open）

`tools/ascend_sdk_legality/build_unmodified.py:149–163` 显式以 `BISHENGIR_BUILD_TEMPLATE=OFF` 配置，只 build 两个 executable，再安装 publish component。`resume_template_compat.py` 与 `rebuild_fixed.py:149–153` 也只是安装该 graph 的工具；没有构建或配置新 prefix 的五个 template BC。README:39–45 明确保留了“resource paths 还需 replay”的边界，却未给普通用户 template 来源、与 CANN/SDK428 的兼容性约束、选择参数或 preflight。

root 即时通报的首次新工具 CPU replay 是实际失败：driver exit0 但无 `kernel.o`，`hivmc` compile failure、未执行 bisheng，prefix 五个 template BC absent。本 reviewer 尚未独立读取该次远端 stderr，故这里不把“缺模板就是唯一根因”升级成独立证明；静态可确定的是当前 recipe 确实不交付该资源合同，且现有 replay 没有补成成功证据。

最小收口：采用官方公开 template 构建，或采用已明确验证的 **readonly installed SDK resource** 参数接口；在用户 recipe 中写出必要 PATH、libdevice、template/resource 参数、存在性与版本检查，并在实际 baseline/fixed receipts 中保留 resolved paths/hashes。只记录 SDK BC/libs 身份，不复制其字节进 artifact。必须在全新调用环境中证明真正产出 `kernel.o`；`--version` 与进程 exit0 都不能替代。

### D2 — mandatory public baseline 的输入与端到端命令未交付（major，当前 open）

`rebuild_fixed.py:14–15,61–67` 硬性要求 input SHA `6b910a15aa5e87da20bbfc7ae29515093d362a609eae1a8c39126514f6a76b3f` 与 reference/binary SHA `05b54efee3ed790bc6c76b40110e92b2f7684d2761605bea6f1dfa31c1fe6b6e`。`replay_public.py:82–87` 要求 caller 提供 input/reference/libdevice。当前 SDK README 只给 archive build 的调用，未给 compatibility resume、baseline replay、pass checks、fixed rebuild、fixed tool 选择的实际命令，也未告知上述固定文件公开下载或提取路径。

canonical `4576e89` 起的公开 scalar diagnostic 目录仅 tracked `EXECUTION_PLAN.md`、`FINITE_RESULTS.md`、`public_state_probe.py` 与 audit JSON；实际留存 archive 和指定 MLIR/NPUBIN 不是 clean checkout 的文件。workspace 中确有公开工程字节，本 reviewer 静态核得：

```text
artifacts/usability/run-013/state-failure-forensics/cpu-replay-evidence/cpu-replay-bm16-scalar/kernel.mlir
  6b910a15aa5e87da20bbfc7ae29515093d362a609eae1a8c39126514f6a76b3f
artifacts/usability/run-013/state-failure-forensics/evidence/run/bm16-scalar-ordinary/output/compiled/npubin.npubin
  05b54efee3ed790bc6c76b40110e92b2f7684d2761605bea6f1dfa31c1fe6b6e
```

这证明 root 有材料，不证明外部用户能从公开 checkout 获得 mandatory gate 的材料。最小收口是发布该自有公开 kernel 的冻结 MLIR/reference NPUBIN 与 manifest（不含 SDK resources），或给出公开、有限、明确的材料生成/提取方式。README 以 caller 自选 `PREFIX` 给出 bootstrap → 原 build/compat → resources → baseline replay → baseline/fixed pass checks → fixed rebuild/install → `TRITON_ASCEND_COMPILER` 的可照做命令，并明确需先安装包含 a829 compiler identity patch 的 FlagTree wheel。无需把 r13 或 root artifacts 路径写成产品依赖。

### D3 — 公开 CPU regression fixture 的解释器写死（minor）

`integration/patches/ascend/test_compiler_capabilities.py:18` 生成的 executable shebang 为 `/usr/local/python3.11.15/bin/python`，而公开 contract 给出的命令是一般安装环境的 `python -m pytest ...`。在合法但解释器位置不同的 Linux aarch64/Python3.11 CANN 环境，该 fixture 会在实际外部 driver 边界得到 ENOENT。这不影响本次已验证 Docker 的 56 passes，也不是 production selector 缺陷。

最小修复：fixture 使用当前 `sys.executable`，保留真实 executable/subprocess 边界和原 flags/output 断言；在批准 Docker 重跑受影响 capability tests 即可。

## compiler identity 的安装与证据核查

审查 canonical `a829a3312af69c1b961919025053829d7096a2b1` 及 evidence-only `c39f669`。读取了 public identity contract、full parent patch、wheel assembler、source-build entry、实际安装 controller/audit、installed sources/tests、index 和日志。

- source-build 的公开说明 `integration/patches/ascend/README.md:236–275` 给出显式 component/work/LLVM22/LLVM15/CANN/JSON inputs，不读既有 FlagPrism native build。`build_from_source.py:55–57` 清理 PYTHONPATH 与开发 override，先 build native 再 assemble/install，`-I` 检查 venv 中的 product/native imports。source mirrors 只作为 Git 源，不当 binary fallback。
- advanced assembler 的 `--native-python/--core-library/--plugin` 明确是 supplied-artifact assembly；`build_automatic_wheel.py:150–169` 把新 helper、compiler、utils、两条实际 JIT 源与 stage/ZIP 对齐。它自身不证 native provenance，而文档也没有声称它做 C++ build。
- 实际 `install-v2-controller.py:12–14,78–170,191–198` 使用 r13 native artifacts，但先重新读取 native sources、compile deps、link inputs 与 artifacts，明确解析旧/新 object hashes 和实际成功 link argv，再调用 public assembler。该控制器是一次受审计 refresh 的证据，不应作为 clean user installation recipe。
- `install-v2-audit.py:15–17,25–72,93–122` 拒绝 PYTHONPATH/test parent override，核 Git blobs、source→stage→ZIP→installed bytes，并断言 product imports 均在新 venv。实际 retained `installed-audit.json` 是 1049 Git files / 380 package files / 249 Python sources / 107 unchanged native members，wheel SHA `bbd3ff08a15f2cb174be3d63d527540935f2811d8a0356772d7749a85b1a7a14`。root 独立 `root-installed-byte-check.json` 同样 passed。本 reviewer 静态阅读这些记录，没有声称重新远端执行了字节审计。
- retained `installed-56-cpu.log` 为 `56 passed in 2.01s`。driver test 只把明确的 source loader 路径重定位到 installed profiler source，identity/JIT tests 本身未改；installed audit 断言 NPU 未初始化。
- contract 与源一致：显式 selector 严格校验、realpath+SHA、默认 packaged/PATH/legacy 顺序；capabilities 来自实际 help 并按 identity/PATH/LD_LIBRARY_PATH 缓存；receipt 保留 identity。external resources/shared libraries 没有纳入 executable fingerprint，文档已写明。

这些 CPU tests 验证真实 JIT.run 的 options normalization/in-memory specialization/hash 与 fake compile/driver 边界、真实 CPU executable fixture、失败恢复、watch/fork/concurrency 等。`test_auto_blockify_cache.py:64–72` 把 `_do_compile` 替换为 fixture，因此不能将 56 passes 改写成真实 persistent SDK disk-cache 或硬件升级回归已完成。现有报告明确保留这项边界，未发现相应虚报。

## 当前 SDK 静态快照

工作树 `FlagPrism-ascend-scalar-legality`，base `926dde5`，本轮 tools/patches 尚未 commit。以下为此次读取时静态 SHA256，后续仅对 freeze 差异复审：

```text
bootstrap_sources.py            c33c044cc31d111da5009ba87ef14e0401e2e213a34824e61a4a2b9cdf0efdea
build_unmodified.py             1b1edd989107fa3bc9cf350e1052447c61f87bc82dc9d4c761b3e9426b88d21f
resume_template_compat.py       e621f1f529acae45094ff9d68c80d26dc0f256dd7433bc2c44d940a922c7d1b3
replay_public.py                0fbe7b9dc2b841f8ea4ed0e49c6f3114b2c848c2e4e9709e7ccbbd3429c3b86c
rebuild_fixed.py                a2271601d8d6819830760a116a74b7360aa1afbf360ff23a6d95cb9bdabcd5ae
check_pass.py                   98eea489bbf3480f85281220b9141228d60c351c60d6a53a22bd2a278ef50c34
README.md                       40d9df7a76b5ff9c52b18727e90674618880871cb4d973211876c365411a9322
sdk-build-explicit-collapse-instantiation.patch
                                4c6e07d319ed7b75c9a7d6ec718b8151c8abb0a5640c1e6eac360a6b17321d64
sdk-scalar-tiling-legality.patch 7ce7f7c116b9beade493b6473337e73cedff230a62b1b180d26d6f591e30a4db
```

bootstrap 已包含 `prefix.mkdir(parents=True, exist_ok=True)`，因此 C2 更早快照的 missing-prefix minor 在本轮源码已消失。SDK README 链到 compiler identity 的文件在旧 base 分支本身尚不存在；它是明确待合并的 parent patch 依赖，不另判已发布产品 broken link。

## 后续有限 delta 所需材料

SDK resources 合同与最终 public recipe；公开 baseline 材料/manifest；冻结 source/patch identities；actual legality-unmodified baseline matched receipt（必须真实 object 存在且 byteequal）；changed TU/dependencies/link/install identities；实际 fixed pass receipts/IR；fresh installed consumer 通过公开 selector 的 ordinary/profile 原样回归。D1/D2 以这些交付结果关闭，不能用静态合理性或只成功 C++ link 关闭。设备与完整资格结论仍由 root 的授权回归决定。

## 补充 delta 1 — SDK resources / 公开安装链 / fixture portability

2026-10-16。独立只读复核 SDK commit `ee877073330404a323aa6cc048d2c62a59b43fb9`（工作树 clean）、canonical fixture commit `b145ba2c33f8ff5b1afc6deca84cb0bdee635adf`，以及 `sdk428-resource-baseline/`、`sdk428-fixed-cpu/` 的已留存收据、公开 IR/NPUBIN 字节。没有执行本机 Python/测试、远端 CLI、SDK build、NPU 或 GPU。本节保留原 finding 与首次失败，更新其有限关闭状态。

| 原 finding | delta 判断 | 关闭边界 |
| --- | --- | --- |
| D1 缺 template/resource 安装合同 | **有限关闭** | 公开源码构建/安装五份 templates，真实 resource-complete baseline 与 fixed CPU driver 均产出 NPUBIN；只关闭 SDK CPU 交付 gap |
| D2 mandatory baseline 材料与命令缺失 | **有限关闭** | 自有公开 input/reference/source 已 tracked，fresh PREFIX 完整 recipe 不依赖 root artifacts/r13 native build；新 clean-entry 以源码审查 + helper 实际 fixture 和历史 full-build/增量证据支持，未冒称又完成一次全量 fresh LLVM build |
| D3 fixture shebang 写死 | **关闭** | source 改为 `sys.executable`，actual installed 14 affected CPU cases 通过；不扩大为新的全套或硬件验证 |

### D1：资源构建和实际使用已成闭环

`complete_templates.py:36–47,83–109` 明确接收 caller 的 `--bisheng-bin`，检查可执行 `ccec`/`llvm-link`，记录其 resolved path/SHA，沿 exact public CMake 的 `BISHENGIR_BUILD_TEMPLATE=ON` / `BISHENG_COMPILER_PATH` 生成资源，再把五个实际生成 BC 安装进 `install-unmodified/lib`。这是重建公开 template CPP；没有把既有 SDK BC 隐式复制成新产物。该脚本 SHA `9d719c1a0956a18d88f4c3290c3ec8dc98404f10fe6b032bb6b0c33e885f809d` 与 retained `templates-receipt.json` 的实际 recipe SHA 一致。其 configure/build/install 三条命令 returncode 均 0；工具 SHA 前后都是 `7edd1aa8…`，2619 objects reuse、changed_objects 为空。

本 reviewer 逐项核了五资源在 baseline template receipt、fixed build receipt、fixed public replay receipt 中的相同 hashes：

```text
meta_op.aic.bc      94c9885a52c9e4cfdfbc239ad104f0a4d14cd330cff9c51d141eb08e88f9ef4f
meta_op.aiv.bc      c816c724c8d0455ff1a85cd08b1f6097131f67809dfc0fbe31209d66139d04a6
meta_op.mix.aic.bc  8fae0b834a36dda0a58ce1b4acd76511ecf183db713aad35553ad7c109a91213
meta_op.mix.aiv.bc  44d1c6a3386b63ae0ae0c48a6b5081ebbd343f87ea838c3872ba5aa0a7363858
host.bc            1aa88a6b7d318fe5090666e6430b86560875583bfd331e1edb6cf0a28673b948
```

`rebuild_fixed.py:194–215` 把相同 generated resources 安装到独立 fixed prefix，先核 baseline hashes并拒绝覆盖。fixed actual replay receipt 记录真实 selected compiler `1f5cc505…`、hivmc/bisheng observed=true、actual argv 使用 fixed prefix templates，输出存在、returncode0、4528B。本 reviewer 对归档 output 重新静态 SHA，得到 `d5e366436832b147c619d65a467442a23e33a7bb0a49e27a4ebcfc27ce9169c3`，与 receipt 相同。r13 路径仅在这一次 actual `libdevice.10.bc` 外部 dependency provenance 中出现；用户 recipe 的 LIBDEVICE 是显式 matching installed backend input，没有把该 r13 路径硬编码成运行 fallback。

原 baseline 依然 **不是 bitidentical**：实际保留 4576B candidate SHA `5bdc6ab4…` 与原 reference `05b54efe…`。读取 strict ELF comparison 与 root independent audit，85 differing bytes 限于 nonallocated `.comment` payload 与其 sh_size；实际 Before/After Bind IR 的静态 SHA 仍是 `0b1f6b32…` / `03c4eddd…`。新 comparator:39–70 用显式异常排除 comment ALLOC、LOAD overlap、其他 section/metadata overlap、超文件边界及任何范围外字节变化，不通过 strip/edit 或 flags 改写取得 equality。producer-only acceptance 是单独 receipt，不覆盖失败 byteequal replay；不得把 D1 的关闭改写为 binary identity 或 device/math 证明。

### D2：clean 用户材料与命令链已补齐

`tests/data/` 的 MLIR、NPUBIN、probe source、manifest 均已 tracked。本 reviewer 重算静态 hashes，分别为 `6b910a15…`、`05b54efe…`、`b09827d6…`，完全等于 manifest 与 gate pins；reference 恰 4576B。未见 SDK executable/library/BC 文件被纳入这个公开 data 目录。MLIR 中的旧 source-location 字符串是 retained provenance；recipe 读取 committed input，未尝试打开那些历史位置。

README:23–49,74–79,100–104,121–192,204–241 已给出 caller 自选 absolute RECIPE/PATCHES/PREFIX/CANN/BISHENG/LIBDEVICE 的完整命令链：source bootstrap、首编 compatibility、official templates、公开 baseline、strict comparison/derived receipt、reviewed execution seal、pass checks、fixed build、fixed CPU driver、公开 selector。sibling imports 由直接脚本调用位置提供，没有隐式 PYTHONPATH 或 root artifacts fallback。bootstrap 创建 fresh prefix 和 source/downloads；公开 dependency 仅是匹配 CANN tools 与已安装 backend 的 libdevice，二者均已在文档中明确。

fresh `--build-compat-patch` 在实际 compile 前调用 `prepare_build_compat.apply`；它 pin 原 Utils、patch 与结果 SHA，以真实 `git apply --check/apply` 做修改，结果 `08afbdcb…` 与实际历史增量编译过的 Utils 字节一致。`validate_delivery.py:23–54` 同时接受 fresh 原 build receipt 或历史 compat receipt，前者记录 `utils_compat_sha256` 后仍会重新核 Utils；重新核实际 compiler/build/replay、source archives、五模板 generated/installed/replay、public template sources 和外部实际身份。producer-only rebuild 进一步重算 strict derived receipt并与 execution seal 的八个 hash 完整 canonical 比较；不由 `assert` 支撑生产 gate。

root 通报的 `normal/-O` clean-entry fixture 与 gate 正反例成功，本 reviewer 核过其实际测试源码，但本轮没有独立重跑。fresh first-build 准备入口是后加的：实际收据保留的构建历史仍是原 full build → explicit-template incremental link repair → resource completion → legality changed-TU incremental build；README/BUILD_VALIDATION 明确另一套 full LLVM build没有重复执行。这个证据范围可以关闭“只会复用维护者目录、用户无可执行 recipe”的缺口，不能宣称新 clean prefix 从头到尾已被实际重跑。

SDK component commit ee87707 基于旧 `926dde5`；本报告完成前 root 已把它与包含 b145/a829 的 canonical 合并。本 reviewer 随后独立静态核对 `FlagPrism-method` 为 clean `e0c218fcad8d592ebb6e55c78af8cca4096f57cb`，merge parents 为 b145ba2 / ee87707；`compiler_identity.md`、完整 parent patch 与 SDK data 均已 tracked，parent patch SHA 仍 `46d354d2…`，SDK README/data 的 hashes 与本轮所审 component 相同。因此 combined checkout 的上述 source integration dependency 已满足。recipe 仍明确要求安装含 selector 的 wheel；未将 `export TRITON_ASCEND_COMPILER=...` 当作 wheel 已安装的证据。

### D3：portable fixture 的实际有限验证

b145ba2 的唯一测试逻辑变化是 import sys 并用 `#!` + `sys.executable` 写 fixture interpreter；外部 executable、flags、NPUBIN output 与两实际 linalg 边界断言保留。retained `integration/evidence/usability-r15-compiler-identity/portable-fixture-14-cpu.log` 为 `14 passed in 8.11s`。root 明确该运行针对实际 installed product，未重新 native build。这关闭 D3，不意味着对先前 56 tests 或未启动硬件回归添加额外覆盖。

### 新发现 D4：bitidentical 路线的辅助 regression 命令分支（minor，open）

README:191–192 支持真正 bitidentical baseline 时省略 derived receipt/seal；但 :209–210 无条件建议 `tests/test_baseline_gate.py --replay <receipt>`。该测试 :63–78 对未修改 receipt 的 `key=None` 固定期望 `accept_public_baseline.py` 成功，而后者 :15–18 只接受 `state=binary_mismatch` 且 byteequal=false。因此真实 `state=matched` 的 bitidentical baseline 会在这个公开辅助测试命令失败。实际本轮 producer-only baseline 不受影响，production matched gate 也没有因此 fail-open。

最小修复可让测试根据 baseline state 选用对应实际正例/gate，或在 README 中把带 `--replay` 的这项测试明确限定 producer-only 分支。可用普通/`-O` 的 CPU-only CLI fixture 验证 matched/mismatch 两条路径，不需要 SDK build 或设备。已把这一具体分支交给 root。

本 delta 不改变设备边界：普通/profile 安装后公开原样 12 项、same-path/cache 升级与原 44 项资格均尚待各自真实结果；静态交付 closure 与 CPU codegen 成功不能替它们判 pass。

## 补充 delta 2 — D4 两条 baseline 辅助测试路线

2026-10-16。仅只读审查 `c520a0980e2d66ebaa4c726218c024813bc08e5e` 相对 ee87707 的三文件差异、六份 final suite 日志/结果与冻结源码；未执行本机 Python/tests、SDK build 或设备。canonical 实际 merge 为 clean `cb968eb8d1891bd1ec6ad2574e070747a0f80986`，parents e0c218f / c520a09。

**D4 在本次有限范围关闭。** README:191–192 的 byteequal 路线与 :209–210 的辅助测试命令现已相容；producer-only 路线仍保留其独立 strict derived IR/ELF validator。

- `rebuild_fixed.py` 将原来的实际 input/reference/output/compiler path+hash 前置检查抽成 `validate_replay_identity`，由真实 main 在任何 source mutation 前调用。无 equivalence 参数时显式 `require_matched=True`，要求 state=matched、byteequal **is True**、output SHA=public reference；这保留原合法分支并对非 bool truthy metadata 更严格。source/resource validation、execution seal、patch、编译和安装逻辑未因该提取改变。
- `tests/test_baseline_gate.py` 按原 receipt route 分派。matched case 调用上述真实 rebuild preflight；binary_mismatch case 调用原 `accept_public_baseline.py`。对两种 route 都增加 state/byteequal 反例，并保留 input/output/reference/tool hash 反例；每套内部都执行普通和 `-O` child validators，不用测试自己的替代 acceptance。
- retained `results-final.json` 的六条实际 suite 为 synthetic matched、synthetic producer、unchanged actual producer，各普通/`-O`；六条 returncode 均 0，六份 `*-final.log` 均显示两个 test methods `ok`、`OK`，无 skip。脚本 SHA `1f5975b94d92416e093f0bf8d011dcbc98e48b58fffc41f7d07ae6330e34f17b` 与 canonical / archive 两端字节相同；实际 archive rebuild SHA `bf2edc262ce40c110fbcf9e04c2b61e715a22b05f48028929e8921d555270ed2` 同样与 canonical 相同。
- synthetic receipt 明确 `synthetic_receipt=true`、test-only/no-new-compilation。静态核 synthetic matched binary SHA 是原 reference `05b54efe…`，synthetic producer binary SHA 是先前实际 candidate `5bdc6ab4…`；两份 receipt SHA 与 suite results 对齐。它们验证测试命令两分支，不是新 compiler replay，不把真实 isolated baseline 改称 bitidentical。

本次涉及 rebuild helper / tests / BUILD_VALIDATION 说明，没有修改 legality patch（SHA 仍 `7ce7f7c1…`）、SDK TU、模板或已安装工具。本报告没有重复核设备，也没有把六套辅助 gate suites 算成 native compiler/hardware tests。原 D4 finding 及其产生原因保留在上一节；当前 C3 已记录的 D1–D4 均无未关闭的 confirmed delivery major/minor，剩余设备与完整资格边界仍按 root 的实际验证单独判定。
