# FlagPrism 时间线工程记录

## 当前恢复摘要（T000，仅设计，未启动实现）

- 目标：执行 `timeline_goal_prompt.md` 后补齐三后端真实内部时间、动态依赖和Perfetto可用性；目前用户要求的是设计和待执行命令。
- 设计基线：`FlagPrism-method` / `detailed-profiler`，准备前HEAD `e6aa804b203d3147925611423c2fcd20cf96bea2`。当前基础usability已完成，新timeline能力未实现、未验收。
- 文档：`Profiler/docs/timeline_design.md`；`Profiler/docs/timeline_testing.md`；根合同与 `integration/plans/timeline/goal_prompt.md` 同字节快照。
- 已做：只读当前代码/公开文档，核Perfetto官方格式/时钟说明，写设计/测试/执行合同。
- 未做：未create_goal，未连接服务器，未启动build/install/import/test/oracle/GPU/browser/Perfetto采集，没有新真实时间线、截图或性能数字。
- 活动owner/PID/日志/设备：无本阶段任务。
- 保留边界：旧count/SDK/资格/论文/Study数据不改；NVIDIA性能/开销认证仍暂缓，时间线功能与时钟验证为新目标必达。
- 待启动：用户复制 /goal 后先读合同、记录与实际Git/任务；不得把设计当实现或把旧24/48结果当timeline已过。

## T000 需求与设计准备

用户要求真实、详细、可在Perfetto理解的内部流水线，而不是只看count或整体kernel。设计把observer elapsed、issue、wait、completion和native engine区分，三后端都要时间尺度与真实异步案例；clock未证明不能拼接。

测试要求真实数学开发集合+独立六新数学，每后端两shape×两config/24ordinary及cold一次warm两次/最多72profile；实际raw/clock/SQL/UI门、两项受控时序干预、三个最终独立Sol6.1/xhigh代码审阅。所有执行留待新goal。

后续每次T编号追加：需求/修改类、freeze/commit、实际安装身份、容器设备owner、PID/startticks/argv、预算/日志、原失败/结果、证据哈希、下一步；恢复先poll权威终态，不盲重启。
