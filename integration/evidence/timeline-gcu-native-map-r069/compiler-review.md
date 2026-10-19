R069 有限独立 compiler delta review

审阅快照：候选 `68faaaf953ff13fd3ef64e7a0351390e8c61a476`；不重新审计此前 canonical `9232936` 的完整功能。结论：未确认这个 delta 存在阻止提交的 blocker/major/minor。可以作为**绑定正常编译产物、允许不完整结果的 compiler debug-location row 服务**提交；它没有提供独立的 native getter、source-region、值流或 engine-busy 资格。

**实际阅读／未运行。** 完整读取 `GcuNativeLocations.cpp`、对应 header/main/CMake delta、Python `_native_file_stage` / bundle 提取 / `bind_native_clock_locations`、normal-fatbin 父仓 hook、两份新增 native/Python 测试和公开数学测试的本次改动。读取 R069 native-map build/check、native install/device、patch-check、formatter 收据及相关安装/检查脚本、`missing-native-phases-v1.json`、`clock-origin-aliases-v1.json` 相关记录、`shared-end-blocks-v1.txt`。核对安装源包与 formatter 包的三个关键文件字节。未读 peer 报告。未执行 import、构建、SDK、测试、数学、设备、SQL/UI 或服务器命令；只进行本地只读检查并新增本报告。实际服务模型未暴露，未知。

**代码判断。**

- `GcuNativeLocations.cpp:14–47` 在同一输入快照上使用 LLVM Object 读取 ELF，限制输入大小，收集 executable/text sections 并检查地址范围溢出。`:51–119` 读取标准 DWARF 行表，处理行表解析错误，略过 end-sequence，以 synthetic 文件名筛选；line0 与不支持的 column 分别计数，不生成伪 site0。column 1/2/3/4 只被标为对应 compiler phase，地址必须唯一落入匹配的 executable section；输出保留 section/index/offset，未把 section offset 冒充宿主或设备绝对加载地址。行数/输出点数设有边界。
- 多个 row 可以具有同一 site/phase，没有被错误压成唯一 getter，也没有以行表地址包围关系证明 source region。`:122–134` 的状态明确是 `compiler_locations_mapped` / `unavailable`，semantics 为 `compiler_debug_location_rows`，三项资格保持 false。CLI 只读输入并检查输出 I/O；CMake 明确编入新增源并链接 LLVMObject / DWARF 库。
- Python `gcu_timeline.py:310–341` 对 offload bundle 的计数、目标名长度、header/payload extent、重叠和唯一 GCU300 image 作检查；使用实际 ELF 字节运行 packaged helper。`:344–409` 绑定 fatbin/ELF/report 摘要和 tool identity，将输出 site/column 与 manifest 对照，严格拒绝不匹配 phase、bool 冒充 column 或资格升级；保留实际缺失位置集合，不补造地址。它信任被绑定的本地 C++ helper 已检查 section extent，没有另建机器码证明器。
- 父仓 patch 在正常 SDK fatbin 已产生并读入后调用 binder，之后返回原 `binary` 字节；包括原有已受限数学兼容 fallback 之后的正常返回位置。没有通过另编译的副本替代实际产物，也不修改算子数学或新增 device synchronization。ordinary 路径不调用 mapper；现有 tool/source fingerprint 随新 helper/Python/parent 字节改变而变，helper 前后仍重查身份。已读取输入、诊断和错误路径继续保留。

**共享 end-clock：不是本 delta 的时钟缺失缺陷。** Python `:391–406` 的 `missing_phase_locations` 计算的是不存在的 `(site,column)` **debug rows**。实际第一个新 capture 缺 site2/3/7 的 columns 2/4，第二个缺 site2/3 的同两列；其中确有已观察到 interval 的 site，不能从缺行推出没有 end timestamp。

`shared-end-blocks-v1.txt` 的 `^bb16` 有三个前驱：传入不同 site ID 及各自 begin words，block 内共享一个 global_timer call 和一个 clock_identity call，然后继续记录；`^bb53` 的另一对前驱同样共享 end calls。共享 call 只有一组保留 debugloc，不能在纯行表服务中自然同时列成所有来源 site 的独立位置。当前代码诚实保留原 rows，并将缺失关联列出，没有宣称这些 call 不存在，也没有把一个 row 无依据复制给所有 site。这不要求在本 delta 中关闭优化、禁止合并或恢复所有一对一 debugloc。未来若要建立动态 source-site→共享 end reader→raw 的关系，需要独立关联证据；本服务并未授予该关系。

**已核对的真实证据。**

- 新 C++ mapper SHA `7ace4e5e…`、Python bridge SHA `7c0377b2…`、parent patch SHA `c09dd3d8…` 在候选、正常安装输入源包与 formatter 包中逐字节一致。格式检查的 clang-format/yapf/ruff 均返回 0。实际正常 Release build、5 个 scope CLI 测试及 5 个标准 DWARF CLI 测试通过；后者使用 host ELF fixture，明确不是 GCU 指令执行证明。
- 新 mapper 在前一轮两份真实 GCU ELF 上的结果为 48/62 rows、site1–13、unknown line10/25；与独立 readelf 记录相符，site10 column/address 示例一致。第二个对象的 begin_counter 可有多个 row，当前服务没有据此授予唯一 PC。
- 本次 native install 收据 terminal0：重建 standalone recorder，检查共享 native/core 源后复用原对象，495 个 wheel 成员经字节核对，wheel SHA `471e8a96…`，隔离安装/import/guard feature 检查通过。实际安装环境的 Python binding 测试 normal 与 `-O` 各15项通过；`-O` 的 pytest warning 保留，未将其解释成产品 assert 替代验证。
- R069 新安装入口的 polynomial / weighted_moment 各 ordinary/profile 一次，四次数学、input/tail/state-once 检查通过。两个 actual capture 分别有22/20 events、各两个展示 observer；自动保留的 native locations 为48/62 points，fatbin 摘要与 capture executable snapshot 一致。报告明确保留3/2个 missing-phase sites，`final_machine_boundary_qualified=false`。这些数据支持有限服务的实际接入，不代表旧数学矩阵被重跑。
- pinned parent 的 patch-check 成功。`gcu-fatbin-hook-v1.json` 展示的是旧安装的函数文本，不能单独用来证明新 hook 已接入；本次接入依据为当前 patch、真实安装步骤及正常编译产物中已出现且已绑定摘要的 metadata。

**Verification gaps／明确未授予的范围。** 标准 DWARF row 的地址、phase 标签和完整性不能替代实际 getter 解码、all-path 控制、native reader→raw valueflow 或运行时 occurrence 绑定。重复/缺失 phase 行仍可能由共享、复制、优化或 debug-location 丢失产生；本报告只接受已经观察到的行，不给未知情况补解释。原普通流水保持问题、source/loop region 和整体 G1 继续独立开放。当前资格字段为 false，缺失位置透明可见，因此这些限制不阻止以现有有限语义提交此服务。

**Optional。** 后续消费者应继续使用“compiler location rows／缺少 location association”的表述，保留多个地址和 unknown 状态，不把 `missing_phase_locations` 显示成“missing clocks”，也不从 `compiler_locations_mapped` 推导任何新的时间或物理资格。本次未发现需要修改实现的具体问题；不建议为使缺失集合变空而加入逐算子规则或扩大验收矩阵。
