独立有限 compiler review（R067 DI bridge 原型）

结论：当前材料支持“在这一份保留 SDK IR 上，双 context 的位置桥接可被真实 SDK 接受并生成行表”。未发现跨 context 直接复用 `Location` 对象或把新版 LLVM 的非位置属性打印回 SDK 输入的错误，也未发现否定这一原型路线的 blocker/major。它尚不是可直接接入产品的实现，更不构成原 capture 的完整 native/source/raw 资格证明。

**实际阅读与未运行范围。** 完整读取 `scope-bridge-prototype.cpp`、`build-prototype.py`、`compile-prototype.py`、`bridge-result.json`、`section-comparison.json`、`native-line-result.json`、`readelf-line-result.json` 和 README；另读 `prototype-CMakeLists.txt`、`compile-result.json` 及保留 v3 拒绝中的相关诊断片段。未读其他 reviewer 报告。仅作本地文本/JSON/哈希检查；未 import 产品、构建、调用 SDK、运行测试/数学/模拟/设备、访问服务器、重放应用或执行 SQL/UI。只新增本报告。

本次读取的 C++ SHA-256 为 `6ab1bb6f47101b8a56a095b88697cc1a44f48a35f52645daa8f756114104d460`；build/compile Python 的 SHA 分别为 `3af1142b…` / `64de040d…`，与对应 terminal 的 script SHA 一致。实际服务模型未暴露，未知。

**实现判断。** 第一 context 注册 LLVM dialect，运行 DI scope pass；`coreText` 使用不带 debug-location 的 generic 表示，在 pass 前后比较非位置 IR。随后将带位置、禁用外部别名的文本重新解析进第二个 opaque context。`original` 与 `located` 都属于这个第二 context，因而第 81 行 `setLoc` 不跨 context 持有 location。输出的操作、属性、类型和 SDK properties 来自 opaque original，只有 location 被转移；第二次 core 比较检查这一路径的非位置表示未变。v3 的 overflow-property 拒绝说明了避免直接输出新版 typed printer 的实际必要性，v4 的 SDK roundtrip 成功是该有限输入的正面证据。关闭第一阶段 verifier 是明确的兼容性选择，必须继续保留真实 SDK 的后续验证，不能把它单独解释成验证过的 SDK IR。

**Confirmed minor M1：两次读取没有固定同一输入快照。** 位置：`scope-bridge-prototype.cpp:28` 与 `:61`，映射检查在 `:76–81`。触发：输入路径在两次 `getFile` 之间被替换，两个版本具有相同的 walk 操作数量/名称，但操作内容或位置不同。第一版生成的 location 会被应用于第二版；后面的 core 比较只比较第二版在 `setLoc` 前后，因此仍可输出成功。这是可由代码推出的输入一致性缺口，不是本次保留文件确已变化的证据，也不否定当前 SDK 收据。后果：未来接入时可能保留了非位置操作，却附上另一输入版本的源位置。最小修正是只读取一次不可变字节快照，并用它构造两个 parser 的输入；无需引入通用 IR 等价器。最小验证是确认两次 parse 共享该快照、收据记录同一个输入 SHA，再复用既有 SDK roundtrip。

**Verification gaps／接入边界。**

- 当前成功链可串接：bridge 输出 `with-scope.mlir` SHA 为 `279cfc6e…`，compile 输入与 retained-input 使用相同 SHA；SDK parse/roundtrip 与正常 codegen 均返回 0。编译 stderr 另有 identity.bc data-layout warning，不能把它写成完全无告警。所读小收据没有单独记录 bridge C++ 输入和生成可执行文件的 SHA；这限制了构建源身份的独立闭环，不等于实际运行了其他代码。接入时将桥接实现、工具链/SDK 及有效选项纳入现有编译身份和 cache 规则即可，不需公开 SDK 私有源码或完整 linked IR/native dump。
- 新旧 `.text` 都是 245024 字节、地址 0、SHA `f85f3db4…`；但整个 ELF 不同，`.eh_frame` 从 52 增至 108 字节，`.dynamic`/`.bss` 地址均移动 56 字节，`.dynsym` 也不同。因此可说该有限 `.text` 未变，不能说新旧加载映像等价、原 capture 已获同一身份的完整 source/raw 映射，或新 ELF 已经真机验证。
- LLVM11 objdump 虽返回 0 并显示行注释，仍报告 debug-info parse warning；另一 dwarf 工具为 unavailable。readelf 独立行表解码返回 0、stderr 空，支持“确有可读行表”，不覆盖完整 DI 语义、clock→raw 值流、all-path/source-loop region 或 ordinary pipeline preservation。README 已保留这些主要边界。

**Optional：保留副本的复现入口。** 本目录保存的是 `prototype-CMakeLists.txt` / `scope-bridge-prototype.cpp`，而 build 脚本对脚本目录执行 `cmake -S`，CMake 内容又引用 `bridge.cpp`；直接在本目录执行会缺少所需文件名。真实 server staging 使用了 `CMakeLists.txt` / `bridge.cpp`，其成功收据不因此失效。未来整理复现入口时，说明这两个文件的 staging 重命名或统一文件名，并参数化现有硬编码输入/工具路径即可；当前不能把这里的保存目录描述为开箱即用的构建包。

有限建议：保留这条桥接路线，先固定输入快照和接入身份/SDK 验证边界。没有证据要求重写桥接架构；也没有依据现在提升产品资格、原 capture 完整等价性或普通流水保持结论。
