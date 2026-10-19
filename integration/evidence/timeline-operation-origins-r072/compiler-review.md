# R072 limited compiler review

审阅冻结候选 `5dca71cd80dda78afafebb52b8c965ac9368b377` 相对 `38e2ffa` 的 operation-origin delta。实际阅读 `late-timeline.cpp` 的改动及 sites/member 收集、recorder 插入、mem2reg 收尾，新增 `timeline_nvidia_operation_origins.py` 全文，machine / boundaries 接入和直接绑定依赖，以及两个新增维护测试、runtime 文档 delta。实际 serving model 未暴露，未知。

**有限结论：没有发现本 delta 的具体 compiler 正确性缺陷或资格误授；支持作为原 LLVM 操作的编译位置标识与有限 native attribution 服务继续接入。当前 CPU 材料证明可生成并读取这些位置，不能代替正在进行的正常安装或新 GPU capture 闭环，也不构成 whole-goal 签字。**

## Confirmed blocker / major / minor

本次有限阅读没有此类项。

`Profiler/Dialect/tools/late-timeline/late-timeline.cpp:481` / `:491` 先保留原 site/member 的 file、directory、line、column；`:504` 才记录独立 marker。每个有 debug scope 的原 Instruction 使用独立递增 line（1–65535），以 `DILexicalBlockFile` 显式选择 synthetic 文件，保留原 scope 的所属关系与 `inlinedAt`。没有 scope 的成员显式 unavailable，未伪造归属；超出 ID 预算会失败。原数学指令、控制流和 operands 没有被这次 origin delta 改写。

新 location 直到 `:768` 才写回原 Instruction pointers，位于所有 clock、compute fences、recorder、header 和 mem2reg 之后。原成员不会被这里的 mem2reg 删除（提升的是新增 ordinal/lost allocas），其它新增插桩也没有替换或删除已保存的原成员。这样 IRBuilder 插入 clock/recorder 时读取的仍是旧用户位置，新 synthetic marker 不会被它们直接继承。clock 的 inline PTX site/phase marker 和最终 counter-map 绑定仍是独立链；没有将 origin ID 当作 clock ID 使用。

`timeline_nvidia_operation_origins.py:17`–`:109` 验证 marker inventory 的版本、唯一 ID、文件/列及 line 预算，并将 source disassembly 的完整指令、predicate、operands、函数 extent 与已 object-bound 的 JSON 再核同。source 注解会在切换 section/function 或任何新的 File 注解时重置；line 0 单列 unknown，缺失 origin 保持 missing。一个 origin 可以对应多个 compiler-attributed native instructions；mapped 状态表示至少有映射，未声称全部 53 个都有映射，missing/unavailable 列表仍保留。

`:112`–`:164` 的 matrix association 要求原 boundary 已经 checked，每个支持的 LLVM member 在自身 origin 下有恰好一个正确 HMMA（其它识别到的 matrix 家族也计入唯一性约束），函数一致，members 的 PCs 不重复且集合与既有 bounded PTX/native issues 完全相等。因此此字段补的是独立 member marker 到已检查 issue 的位置对应，没有只按 member 数量或 source 行号相同来通过。

`timeline_nvidia_machine.py:760` 在正常实际 CUBIN 检查成功后，使用同一工具、同一对象、同一 deadline 额外保留 source output；工具 bytes 前后 identity 核同，失败只令 optional origins unverified。`timeline_nvidia_operation_origins.py:167` 的离线恢复检查 binary/CUBIN/native JSON/source output hashes 和与 counter map 相同的 tool identity，再从原 source output 重算，不继承保存的 origins 成功字段。legacy plan 无 marker 时明确 unverified。所有 source region/cost、participation、hardware busy 字段都仍为 false；boundaries 的顶层 clock/valueflow/overlap/time-flow 资格也未放开。

## 实际证据范围

实际读取 `run-072/preflight/origin-map-poll-v1.json`：mapper terminal 0、0.214887087 秒；一份 SDK CPU-generated CUBIN `026466e31f6b3b02afd8be6b9655531f20220499749843c9be0743122f5a787d` 的 53 origins 中 50 有位置，40/48/50 保留 missing。site 23 的四个 members 分别由 origin lines 30/31/32/33 对应 native PCs `0x13d0/0x13f0/0x1410/0x1430`。四个显式 corruption 被拒绝：duplicate origin ID、不同 matrix-origin binary、不同 binary、unknown origin。测试代码另实际检查 missing-file 不伪造位置、missing origins 不得到 matrix identity，以及错误 LLVM operation family 保持 unverified；这些不在四项 rejected 名单中重复计数。结果明确 fixture=true、device/application replay=false。

另读取现有 `origin-poll-v3.json` 的真实 CPU codegen/反汇编收据：transform、PTXAS、PTX/source disassembly、JSON 命令均为 0，source-line contexts 确有四个独立 synthetic lines，附近 reader 仍显示用户文件。该 CPU 原型 build 使用了所列 LLVM 配置及 `_DEBUG` 等 flags；不把它称作新的正常 release 安装资格。

executed mapper/test source 与候选各自只有格式差异，stdlib AST 核同。当前 mapper SHA256 为 `96aad14ec29ad96ad72bded7fbb2600b94f747d87edaa87fd139892f10c7ba5e`。CPU native 源 `2b1e292bff0197a8f763a8c8501b98dbefc6a18509442c8d0609be57eafc287a` 与候选 `accaa7a68aac39a76595fe876f1a0c17edfd92c5a4911d088b83a7da59f7e09b` 逐项 diff 仅空白/折行。formatted archive 中六个实现/测试文件 bytes 与候选核同，format 收据的 clang-format/yapf/ruff 均为 0。

## Verification gaps / scope / optional

尚未根据本次材料关闭正常新 native tool/wheel 的安装、已安装公开 inspection/offline 路径，以及新实际 loaded CUBIN/capture 的 origin 位置链。两个维护测试的 direct/no-debug/inlined 路线已读代码；不能仅从 CLI launch 或 CPU prototype 推断新正常安装已执行它们。这里等待既有安装工作的真实终态即可，不要求新增数学矩阵。

这些是 compiler-attributed debug locations；通用 one-to-many 列表不证明每条所列 native 指令都独占地实现原操作。矩阵字段的有限一一对应也不证明 operands/value flow、loop/iteration 身份、动态次数、source all-path region、原普通流水保持、exclusive source cost 或硬件完成/忙碌。50/53 的位置覆盖不能写成完整覆盖。新 CUBIN 尚未执行 GPU，不能继承旧 CUBIN 的数学或 raw capture 资格。

本次仅做本地只读 Git/文本、stdlib JSON/hash/AST/archive 比较及本报告写入；没有 import 产品、运行测试/SDK/codegen/数学、连接服务器/设备、阅读 peer 报告或启动子 agent。没有额外 optional 扩展，也不建议通用 ISA 证明器。

## 追加：正常安装已证范围

随后实际读取了 `preflight/native-install-poll-v5.json`：terminal 为 0、77.792108511 秒，source 为已审 `5dca71cd80dda78afafebb52b8c965ac9368b377`，17 个步骤全部为 0。包含正常 `build_late_timeline_tool.py` 重新构建新 standalone recorder、正常 wheel 装配、隔离 venv 安装/import；640 installed members，wheel SHA256 `0dacd4ea6d6adf0976b3457fc92637a68b32e015fc98cc6345a5f85fbcbd1d53`。旧 compiler core 复用，但新 recorder 的实际 build 步骤与新路径明确存在，不能把此误读为沿用旧 recorder。

正常新 recorder 的 origin CLI（direct/no-debug/inlined）步骤为 0；安装后 origin mapper fixture normal / `-O` 均为 0。原 matrix rule normal / `-O`、四份既有实际原件的 matrix 检查及 legacy 公开导出也均为 0；公开导出保持 8 counter、2 dependency、reason null。它们关闭了本报告前文对应的正常 tool/wheel 安装与 fixture 执行缺口。

**尚未在本追加中关闭新实际 loaded CUBIN/capture 的自动 origin inspection—offline 恢复链。** 收到的 C1/C2 状态消息不替代尚待提供的真实链终态；没有根据部分 C1 成功预判联合 runner 或 C2 通过，也未重新跑 C1。其余 source/loop、普通流水保持与 whole-goal 边界继续独立保留。

## 追加：实际 loaded capture 的有限 origin 闭环

实际读取 `preflight/real-and-reader-poll-v1.json` 中仅 real-origins-v3 部分，以及 `real-sparse-origins-poll-v1.json` 的 terminal/result 两段连续 JSON；未把同文件内 reader probe 纳入本 delta。也读取了两个已执行 runner `real_origins_v3.py` / `real_sparse_origins_v1.py`，其 SHA256 分别与 terminal 的 `799c4ec8378ef1c5da13e335f74b039f5b84f0254afd11bee030b2f1c46b49bf` / `8a4926d6d133a1cde031a704ce5da14b4f051f8e9be6c3b38b196c0e7b1dc5fd` 核同。

real-origins-v3 为 terminal 0、75.090694969 秒，8 个步骤全部为 0，source `5dca71c`。它复用 C1 v2 的两个既有 loaded captures，没有重跑 C1；C2 两个新 captures、default 两个新 captures，以及标签为 sparse 的另两个 captures 均完成自动 source 采集与离线核对。**此处名为 sparse 的命令实际是 `--site-budget 8`，binary 与 default 同为 `0dc7aa81…`，不能作为真正稀疏配置证据。**

每份 capture 都经 `load_late_machine_map` 和产品 `load_native_boundary_report` 重算。runner 显式检查 capture 内自动采集的 operation-origins 状态，以及离线重算状态都为 mapped；另外独立执行 origins 维护检查。因此这里补上的是实际新 binary/capture 的自动 inspection → retained source output → 离线产品重算链，不只是 CPU 对象或直接调用 mapper。C1 保留 8 origins / 7 mapped / missing 3；C2 为 45 / 40 / missing 26,28,41,42,43；default 与 budget8 都为 53 / 50 / missing 40,48,50。矩阵例的四个 LLVM members 均有 checked 的独立 origin/HMMA 对应，缺失项没有被提升为完整覆盖。

真正稀疏补采单独为 terminal 0、22.302101847 秒，两步骤均为 0；命令明确 `--site-budget 1`，runner 在正常模式下还检查 plan `max_sites == 1`。两个 captures 同属新实际 binary `0e0272e41d4a786d97f67e0f06e16daae29b4371512e0b36145fc9b801c56c3f`，各 33 origins / 31 mapped，missing 31,33；site 23 的 members 0–3 通过 origin 14–17 分别对应 `0x1020,0x1040,0x1060,0x1080` 的四个 HMMA。此配置也执行了同一自动采集及离线重算检查。

**本报告此前“新实际 loaded CUBIN/capture 的自动 origin inspection—offline 恢复链”待证项，至此在上述具体 captures 与 default / explicit max_sites1 范围内闭合。** 没有发现需要重开源码审阅的新问题。新增 counter/dependency 的 TP job 尚未在本次材料中终态验收；初次 runner 在调用 TP 前的 receipt 相对路径失败不算 TP 成功或产品/verifier 缺陷。本次不预判其 v2 通过。

此追加不授予 source all-path/loop/valueflow、原普通流水保持、exclusive cost、完成/忙碌或 whole-goal 资格；所有既定 false 权利字段继续保留。没有运行产品、测试、数学、设备或服务器任务。
