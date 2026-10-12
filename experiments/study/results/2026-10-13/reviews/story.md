# 独立审阅2：Study → 问题故事 → profiler方法要求

**判断：限定范围的动机成立；系统创新与方法有效性尚未成立。** 已独立读 Introduction/Study、实验入口、紧凑结果、timing_probe.py/plot_deep.py，检查选定原始输出与IR，并查看五张最终PNG；未读其他审阅输出。现稿诚实保留了证据边界，但“两个具体案例 → 同一请求后果”只部分贯通。

## 成立的箭头

- 六算子、三形状、两配置 → 问题来自一组真实算子，而非单个玩具例子。device-duration说明值得深入检查；速度差异本身不能推出profiler缺陷。阶段参数在GCU可能生成相同二进制，配置标签也不能充当等价干预。
- fused源区域 → V100单入口FMA、GCU单kernel、Ascend AIC/AIV＋workspace/set-wait → 原生capture仍为一个kernel/task区间 → 逻辑区域、编译函数、活动记录需要分开表达。`evidence/fused-128-debug.hivm.mlir`的实际函数和依赖支持此要求；它没有测到内部执行/等待。
- 同一Outer256/Inner128请求 → GCU通用嵌套减法外层约0.467–0.496、内层约1 → 单区间分开capture与移动q核验 → 必须声明counter的嵌套协议。原始`enflame/nested/q64/result.json`两次begin均为0、两次end均约2212；单outer约4682，直接支持“不能当独立时间戳使用”，尚不能唯一确定SDK内部机制。
- 固定开始屏障、仅改结束屏障、零工作控制 → bracket读数受端点约定影响 → contract需要端点与单位。零工作也有读数，不能把差值全部称为完成等待。
- 固定GCU输入/BK、tile16²→64² → counter-free时长明显降低，同时TCU呈现不同指令族效率 → 保留原生指标/设备/调用/per-SIP及其定义。TCU原始CSV确实已有这些细节；这是保存已有观测的要求。

## 最弱转折与具体修改

**P0：fused案例与nested案例是两条证据链，不是同一个融合算子的请求贯穿。** Case1问“matmul/epilogue如何映射与观测”，Case2换成向量递推问“嵌套区间如何计量”；后者既未测前者AIC/AIV，也未展示前者导致的错误归属。03-study在两者之间加一句箭头：`映射决定观察什么 → 独立受控递推隔离观察协议 → 分别导出映射/计量契约`。若要更强连贯故事，必须实际把一个命名region请求贯穿fused的lowering、采集、重建，给出缺失/歧义结果与适配后结果；当前不要暗示已完成。

**P0：需求不能替代新方法。** 目前末尾三条是合理设计约束；尚无适配后的nested结果、动态映射重建、busy/wait观察或归属错误率。保留Introduction中的planned/proposed边界。系统章节应具体给出`请求 → 编译锚点/实例ID → backend lowering → 记录 → 程序关联结果/unsupported`，评估再验证，不能把study探针或通用导出器直接升级为新profiler贡献。

**P1：把native-detail接到可解释的输出要求。** 约59.6×/55.0×时长改善是tile干预的结果；没有证据说明由profiler诊断引导，也不能把1D/MSF百分比当busy/wait分解或因果瓶颈。图保留TCU细节是优点；正文补`capture内ID可保留 → 跨capture关联未建立 → 结果必须显式报告关联范围`。不要靠同名kernel连接TCU与TOPSPTI。

**P1：把requirements收敛成可检验承诺。** `一源多执行对象 → provenance映射`；`counter协议不同 → 支持/拒绝nested与明确endpoint/unit`；`native细节有效 → 原定义与capture内身份保真`。可以由现有证据导出；“完整生命周期/统一所有行为/精确还原重叠”需另行实验。

## 新颖性与范围

最强反驳：把三个vendor采集API包起来、整理IR并导出已有TCU指标，也能产生当前study；为何需要新compiler–profiler机制？当前没有baseline复现或适配结果，不能回答。

[Proton官方文档](https://github.com/triton-lang/triton/blob/main/third_party/proton/docs/intra-kernel.md)已有IR注入、scope/异步event，并明确讨论高层IR变换影响插桩；[KPerfIR原论文](https://www.usenix.org/system/files/osdi25-guan.pdf)已有compiler-centric细粒度profiling。因此“需要IR”“支持scope”“统一接口”本身不能作为区别。潜在贡献是这些具体backend上可验证的映射/计量契约与lowering，但实现、版本锁定和能力对比仍待补证；不要断言现有工具原则上无法扩展。

现有结论限三套backend/software stack、受插桩影响的区间。单区间参照使用同一clock另次capture，不是独立物理真值；V100/Ascend接近1只是此探针一致性；无AIC/AIV busy/wait、无同SIMT多厂商证明、无长期运营或自动优化证据。故事定位为真实profiler的可移植观测问题，勿转成AI诊断故事。
