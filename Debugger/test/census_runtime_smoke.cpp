#include "Debugger/Decode/Decoder.h"
#include "Debugger/Runtime/TransferEngine.h"
#include <cstring>
#include <iostream>

int main() {
  using namespace mlir::flagtree::debugger;
  for (const char *layout :
       {"deterministic_compact_v1", "selected_dynamic_timeline_v1",
        "gcu_site_census_v1"}) {
    auto engine = createTransferEngine();
    BufferMeta meta{};
    meta.protocolVer = kProtocolVersion;
    meta.recordLevel = RecordLevel::LEVEL_SUMMARY;
    meta.exportMode = ExportMode::POST_KERNEL_EXPORT;
    DebugBufferPlan plan;
    plan.recordCapacity = 6;
    plan.recordSize = 64;
    DebugRuntimeMetadata runtime;
    runtime.recordLayout = layout;
    runtime.hasLaunchGrid = true;
    runtime.gridX = 2;
    runtime.recordsPerInstance = 3;
    for (int invocation = 0; invocation < 2; ++invocation) {
      auto ctx = engine->prepare(meta, plan, runtime);
      engine->initHeader(ctx);
      auto *words = reinterpret_cast<uint32_t *>(ctx.deviceCtrlPtr);
      for (unsigned i = 8; i < (32 + 6 * 64) / 4; ++i)
        if (words[i] != 0)
          return 1;
      words[8 + 4 * 16] = 5;
      words[8 + 4 * 16 + 1] = 1;
      auto exported = engine->syncExport(ctx);
      RingBufferHeader header{};
      std::memcpy(&header, exported.rawBuffer.data(), sizeof(header));
      uint32_t expectedWrite =
          std::strcmp(layout, "deterministic_compact_v1") == 0 ? 6 : 0;
      if (header.writeIdx != expectedWrite || header.capacity != 6 ||
          header.overflowCount != 0 || header.flags != 0)
        return 2;
      uint32_t count = 0;
      std::memcpy(&count, exported.rawBuffer.data() + 32 + 4 * 64,
                  sizeof(count));
      if (count != 5)
        return 3;
      if (std::strcmp(layout, "gcu_site_census_v1") == 0) {
        DecodedDebugRun decoded;
        std::string error;
        for (const char *censusLayout :
             {"gcu_site_census_v1", "ascend_source_census_v1"}) {
          exported.runtimeMetadata.recordLayout = censusLayout;
          if (decodeExportedRun(exported, decoded, &error) ||
              error.find("versioned census decoder") == std::string::npos ||
              !decoded.records.empty())
            return 4;
          auto truncated = exported;
          truncated.rawBuffer.clear();
          if (decodeExportedRun(truncated, decoded, &error) ||
              error.find("versioned census decoder") == std::string::npos)
            return 5;
        }
        exported.runtimeMetadata.recordLayout = "selected_dynamic_timeline_v1";
        if (!decodeExportedRun(exported, decoded, &error) ||
            !decoded.records.empty())
          return 6;
        exported.rawBuffer.clear();
        if (decodeExportedRun(exported, decoded, &error) ||
            error.find("RingBufferHeader") == std::string::npos)
          return 7;
      }
      engine->release(ctx);
    }
  }
  std::cout << "census header/reset and legacy synthesis regression passed\n";
}
