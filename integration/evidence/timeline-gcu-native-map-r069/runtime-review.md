# R069 independent limited runtime delta review

Freeze：candidate `68faaaf953ff13fd3ef64e7a0351390e8c61a476`，相对 canonical `92329369ec170b06813731a98e70b8641598e1d7`。开始审阅时 tracked/untracked 工作区均干净；收尾看到的并发 `Profiler/docs/timeline_runtime.md` 修改不在此 freeze 结论内。设备脚本 SHA256 `ab9441068b40661a977f64bc34b7606cc5f21ebd68b9040b8dad8c4427b4aaf0` 与 device controller/输入归档一致。

**结论：本有限 runtime delta 未发现 confirmed blocker、major 或 minor。** 可以交付自动保留实际 fatbin 中 ELF 的 compiler DWARF site/phase rows；不能把它改称完整 reader 映射、reader→raw valueflow、source boundary、clock/shared epoch 或 ordinary pipeline 资格。当前代码保持这些边界，未见借未知行、重复行或 missing phases 误授资格。

本次只读代码、git diff、JSON/文本和归档，不运行 import、checker、测试、编译或 SDK，不访问服务器/设备，不读取其它 review 意见；唯一写入是本报告。未重启旧矩阵。

## Runtime 核对

- **有界 child 与失败保留：** `Debugger/python/flagtree_debugger/gcu_timeline.py:237` 的 `_native_file_stage` 使用传入的不可变 bytes 快照，输入/输出各限 16 MiB，helper wait 为 30 秒，stdin 指向 DEVNULL。它独占临时目录、保存 input/stdout/stderr/launch/terminal；`/proc` owner 登记与 launch 写入在异常清理块内。异常或超时对这个无子进程 native helper 执行 kill/wait；成功退出后仍检查 output 存在及大小、输入未变、当前 tool identity 未变。没有在非零退出、缺失 output、超预算或身份改变后发布位置 metadata 的 fallback。主程序解析/转换成功后才打开 output，close 后检查写入错误。
- **Bundle 范围与镜像选择：** `gcu_timeline.py:310` 检查 Clang offload magic、1–32 个 descriptor、完整的 24 字节 descriptor、target 长度上限、target 与 payload byte extent；再拒绝非空 payload 与最终 header 或其它 payload 重叠。Python 整数运算不发生 offset+size 回绕。仅接受唯一的非空 `tops-dtu-enflame-tops--gcu300` image，不按第一个 image 或名字近似选择。空 host 占位符不会冒充 ELF。
- **实际 binary 绑定及生命周期：** `gcu_timeline.py:344` 先保留整份 input.fatbin，再解析并把抽出的同一份 ELF bytes 交给 helper；错误链给出 retained 目录。metadata 同时保存 fatbin SHA、ELF SHA、target、native output SHA 和带 source SHA 的 child receipt。位置检查全部通过才一次更新 metadata。`integration/patches/enflame/flagtree-source.patch:90` 在 normal `make_fatbin` 读取实际编译结果后、返回 binary 前自动调用 binder，没有应用重放或额外 kernel launch。ordinary 编译不调用该 binder；原先 SDK 验证 DI 输出后再 codegen 的顺序未改变。
- **缓存身份：** identity version 仍为已建立的 v2，但 native tool、bridge 自身和 patched backend compiler 均在内容哈希绑定内，因此本次 tool/bridge/make_fatbin hook 变化不会与旧缓存身份相同。prepare/launch 的原有冻结值与当前 identity 比较仍保留；新增 native stage 前后也比较 identity。没有靠存在一个旧 marker 字段来放行另一版 recorder。
- **位置服务及 schema：** `Debugger/lib/Instrumentation/GcuNativeLocations.cpp:14` 只接受 ELF，检查 executable section extent，保留 section/index/offset 坐标；有歧义或点在 executable code 外时报错。marker 行号0和不支持的 column 分别计为 unknown/unsupported，不被转换成 endpoint。服务只报告 compiler debug rows，明确将 source region、reader valueflow、hardware busy 三项设为 false。Python `gcu_timeline.py:358`–`:409` 再检查 schema、marker、语义、这三项必须严格为 false，以及 site 来自本次 manifest、column 为整数1–4、phase 对应 column、地址/offset 非负；缺相位逐 site 列出，不补零、不复制其它 site 的端点。
- **消费者权限及原 ABI：** 搜索新增 `debug_execution_native_locations`/`missing_phase_locations` 字段，除 bridge 与集成检查外，未见现有 clock/dependency 权限消费者读取它们。本 delta 没有更改 recorder/raw ABI、发布、容量预算、timer 来源/46位声明、周期/epoch、依赖匹配或设备同步路径。DWARF row 并不被这里当作已识别的实际 clock 指令。

## 已读证据及其范围

实际打开 `native-install-poll-v1.json`、`native-device-poll-v1.json`、`native-map-build-poll-v1.json`、`native-map-check-poll-v1.json`，并读对应 install/check 输入脚本、config、设备输入归档。安装归档中的当前 Python bridge、native mapper 和 source patch SHA 与 freeze 源一致。早期 native-map-build 归档的 mapper 与当前仅格式不同，不能把早期 tool 的 SHA 直接当成当前安装 tool；本轮安装另有实际 rebuild/unit 收据。

- **实际安装：** install controller terminal/0；新 standalone recorder 实际重建，未变 core/runtime 复用；495 个安装成员与 wheel 逐字节核对并完成 matching import。wheel SHA `471e8a96679f41bc6e90206c3cda468dfcb908faee23c0a7f7b38b8349fa1d13`。安装结果的 pending-device 是安装步骤状态，设备资格单独取后续 receipt。
- **CPU fixtures：** C++ scope 五项与 native-location 五项成功；后者以 host assembler 的标准 ELF/DWARF fixture 验证 site/phase/offset、非 marker 源、unknown column、无效 ELF、output I/O。15 项 Python pytest 在 normal 与 `-O` 各通过，覆盖 bundle 截断/歧义/重叠、site/phase/type/资格拒绝、missing 明示、ordinary 路径不调用检查。其 report 测试 mock `_native_file_stage`，不冒称真实 GCU 或 Python child fault 注入证据；`-O` warning 也保留。
- **保留的实际 GCU ELF：** native-map-check 对 R068 两个原 ELF 用真实新服务得到48/62 rows、所有13个 site，并与既有独立 readelf 的有限结果比较；没有数学重跑。原行号0的计数分别10/25，未消去未知行，也未授 source boundary。
- **本轮新 installed 公开 API：** device controller terminal/0；两个新 kernel 各做 ordinary/profile 一次，共2+2数学调用；reference、输入不变、应用输出 tail、每 program 一次 state 副作用均通过。两 capture 分别22/20 events、2 observers、48/62位置点，missing phase sites 分别3/2。设备脚本 `:163`–`:178` 用 snapshot 的实际 fatbin bytes 独立复算 SHA，并与 native retention、snapshot executable SHA 相等；仍要求 source/valueflow false。这里的 guards 是应用 tail 检查，不能单独当成新 allocation-guard 故障资格。

## Missing phases 与保留的 verification gaps

`missing-native-phases-v1.json` 没被成功计数掩盖：第一 capture 的 site2/3/7，第二 capture 的 site2/3，均缺 end counter/identity 的专属位置。`shared-end-blocks-v1.txt` 显示一个 end-clock 基本块有多个 predecessor，并通过 block arguments 携带不同 record/site 数据；这支持“优化后共用 end clock/debugloc”的解释。它不支持仅按13×4与48/62的差值推断丢失 clock，也不支持给缺失的 site 自动补一个独立机器地址。当前 missing 列表和 qualification=false 是正确的保守结果。

1. **完整 reader/record 映射、source boundary、ordinary pipeline 仍未授。** DWARF row 可重复、可共享，并不说明相应地址就是 reader opcode，也没有在这里证明实际返回值流到哪个 raw record。若以后要提升这一资格，最小工作应从这两份已保存 ELF/IR/raw 出发核对具体 reader、共用块的动态 site 选择和 record valueflow；无需为本次位置诊断保留再重跑旧矩阵。本报告没有做这项机器码核对。
2. **通用 Python child 故障路径尚无本轮直接注入收据。** 15 pytest mock native stage，成功的实际编译只覆盖正常执行。静态走查未发现新生命周期缺陷；不为本有限交付新增 gate。若以后单独宣称 timeout/owner 写入失败/身份改变已经实测，最小补项是 CPU fixture 注入这些分支，核实 reap、保留件和没有有效 metadata/编译返回，不需要设备矩阵。

Optional：可用现有保留 fatbin 离线复算抽取 ELF SHA并与 native receipt 的 source SHA做显式三方比对；当前实现已经使用同一份 ELF bytes，设备测试则显式核对了 fatbin 绑定。未发现由此造成的当前错误，不把此增强建议升级为 blocker。

已读完整 delta 文件、相关 native main/header/CMake、两类 unit、设备脚本和上述收据/输入；未读 peer review，未审其它后端新工作，未本机执行产品或测试，未自行取得最终 ELF 全量反汇编或扩大原资格合同。
