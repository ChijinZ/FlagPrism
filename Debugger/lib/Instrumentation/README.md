# Instrumentation Sources

本目录是 C 模块实现目录。
负责人：颜臻。

当前文件：

- `Collectors.cpp`
- `Passes.cpp`
- `RecordBuilder.cpp`
- `Writer.cpp`

对应公共接口：

- `third_party/FlagPrism/Debugger/include/Debugger/Instrumentation/Collectors.h`
- `third_party/FlagPrism/Debugger/include/Debugger/Instrumentation/Passes.h`
- `third_party/FlagPrism/Debugger/include/Debugger/Instrumentation/RecordBuilder.h`
- `third_party/FlagPrism/Debugger/include/Debugger/Instrumentation/Writer.h`

实现重点：

- summary collector 选择
- memory event 插桩
- full value payload 引用
- `logical_instance_id` 生成
- device 侧 record 构造
- 通过 `__debug_ctrl_ptr` 写 ring buffer

需要采集和写入的指标，见：

- `third_party/FlagPrism/Debugger/include/Debugger/Instrumentation/README.md`

## GCU original execution members

The normal late GCU recorder keeps `source_membership` for each selected site.
It is extracted before observer insertion from the original primitive or the
operations between the original paired fusion borders. Members retain original
operation indices, available source operation/scope IDs, real coordinates, and
control ancestry. A fused region has one elapsed interval and may have several
source navigation locations; those locations do not divide its duration or
certify exclusive source costs. Unknown primary locations remain visible.

For retained uninstrumented execution IR, the packaged standalone recorder also
supports `--execution-origins INPUT OUTPUT MAX_SOURCE_REGIONS`. It uses the same
site selection/order as normal rewriting and does not rewrite the input. A
historical sidecar must be bound to the original input SHA and the entire
`(id, kind, operation, location)` site sequence before use; matching a line number
alone is insufficient. Member extraction is bounded across the whole input
(100,000 visits, 4 MiB estimated serialized details) and per site (8,192 members).
Exceeded limits keep source membership explicitly unverified.

The raw decoder retains these actual member coordinates in canonical source
references, which the standard Perfetto exporter includes in `source_locations`.
Record identities, raw offsets, ticks, occurrence order, and observer semantics
are unchanged. Membership is navigation and producer provenance; final LLVM,
SDK, and native boundary checks remain separate.
