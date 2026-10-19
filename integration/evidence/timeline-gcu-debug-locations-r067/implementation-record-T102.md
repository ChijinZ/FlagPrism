
## T102 GCU 调试位置保留原型取得最终 ELF 行号（run067，未接入产品）

- 当前正式/远端产品基线 b0aa0b6；本轮只做已有燧原 Docker 内 CPU 编译诊断，不启动设备数学、性能、SQL、浏览器，不改论文。
- v1 小 LLVM IR：public MLIR DI scope pass 与真实 SDK roundtrip 都成功且输出逐字节一致。v2 完整原 IR 被 public 工具拒绝：缺厂商 gcu.target 类型。v3 薄 C++ bridge 能只添加位置，但 typed LLVM printer 改写 overflowFlags 的编码，被实际 SDK 拒绝；原失败保留，不放宽最终验证。
- v4 使用两个 MLIR context：typed context 生成 DI scope；opaque context 保留原 SDK 运算/属性，只按相同 walk/name 转移位置。去掉位置后前后 IR 相同，实际 SDK 完整解析/验证返回0。configure/build/bridge/SDK四步均0，controller557320/worker557321 terminal0，7.528s，均missing。只验证原型兼容性，不代表产品实现完成。
- v5 把 v4 原型输出交正常 SDK CPU compile，controller557406/worker557407 terminal0，2.068s；fatbin a9739d6c2abc1b73ef2bdc939e9bb1d64ea8f67bac5493af3dc652e8c1eb3ecb。最终 ELF 含 .debug_line/.debug_info 等；.text 地址/大小/字节 SHA 与原真机 ELF 完全相同，但 .eh_frame 大小以及 .bss/.dynamic 地址等发生变化。因此不把新 ELF 直接视作原执行对象或完整 sidecar 资格。
- LLVM11 native-lines 返回0且能定位 input.llir:207/227 的内联 low/high/low clock 读取与211/231的sipinfo；stderr同时有 failed to parse debug information，必须保留。独立 /usr/bin/readelf --debug-dump=decodedline 返回0、stderr空，187336B/SHA349c6b7bbeb5788433f93a28f14257e856dd33376ede89911be42bfa8695f09b，确认实际行号表存在；缺 llvm-dwarfdump 未当作可用工具。
- 当前不是新的运行时产品版本：尚无 per-site/phase 唯一 marker、完整 native reader→raw 数据流绑定或自动公共编译入口接入。下一步以此可行路径实现位置保留/定位，不能只把原型当完成。NV ordinary pipeline preservation 与 Asc 全边界仍开放。只复用原数学和1740 TP/UI，不重跑无关矩阵。
