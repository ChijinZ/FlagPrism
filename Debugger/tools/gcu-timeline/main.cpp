#include "Debugger/Instrumentation/GcuTimeline.h"
#include "llvm/Support/MemoryBuffer.h"
#include "llvm/Support/raw_ostream.h"
#include <charconv>

int main(int argc, char **argv) {
  if (argc == 5 && llvm::StringRef(argv[1]) == "--execution-origins") {
    uint32_t regions = 0;
    const char *value = argv[4];
    auto length = std::char_traits<char>::length(value);
    auto parsed = std::from_chars(value, value + length, regions);
    if (parsed.ec != std::errc{} || parsed.ptr != value + length)
      return 2;
    auto input = llvm::MemoryBuffer::getFile(argv[2]);
    if (!input)
      return 1;
    auto result = mlir::flagtree::debugger::indexGcuExecutionOrigins(
        (*input)->getBuffer(), regions);
    if (!result) {
      llvm::errs() << llvm::toString(result.takeError()) << '\n';
      return 1;
    }
    std::error_code error;
    llvm::raw_fd_ostream output(argv[3], error);
    if (error)
      return 1;
    output << *result;
    output.close();
    return output.has_error() ? 1 : 0;
  }
  if (argc == 8 && llvm::StringRef(argv[1]) == "--check-preservation") {
    uint32_t hidden = 0, capacity = 0, regions = 0;
    for (auto [value, target] :
         {std::pair<const char *, uint32_t *>{argv[5], &hidden},
          {argv[6], &capacity},
          {argv[7], &regions}}) {
      auto length = std::char_traits<char>::length(value);
      auto number = std::from_chars(value, value + length, *target);
      if (number.ec != std::errc{} || number.ptr != value + length)
        return 2;
    }
    auto before = llvm::MemoryBuffer::getFile(argv[2]);
    auto after = llvm::MemoryBuffer::getFile(argv[3]);
    if (!before || !after) {
      llvm::errs() << "Cannot read GCU preservation inputs\n";
      return 1;
    }
    auto result = mlir::flagtree::debugger::checkGcuExecutionPreservation(
        (*before)->getBuffer(), (*after)->getBuffer(), hidden, capacity,
        regions);
    if (!result) {
      llvm::errs() << llvm::toString(result.takeError()) << '\n';
      return 1;
    }
    std::error_code error;
    llvm::raw_fd_ostream output(argv[4], error);
    if (error) {
      llvm::errs() << error.message() << '\n';
      return 1;
    }
    output << *result << '\n';
    output.close();
    return output.has_error() ? 1 : 0;
  }
  if (argc == 4 && (llvm::StringRef(argv[1]) == "--debug-scopes" ||
                    llvm::StringRef(argv[1]) == "--execution-structure" ||
                    llvm::StringRef(argv[1]) == "--native-locations")) {
    auto input = llvm::MemoryBuffer::getFile(argv[2]);
    if (!input) {
      llvm::errs() << input.getError().message() << '\n';
      return 1;
    }
    auto result = llvm::StringRef(argv[1]) == "--debug-scopes"
                      ? mlir::flagtree::debugger::addGcuNativeDebugScopes(
                            (*input)->getBuffer())
                  : llvm::StringRef(argv[1]) == "--execution-structure"
                      ? mlir::flagtree::debugger::indexGcuExecutionStructure(
                            (*input)->getBuffer())
                      : mlir::flagtree::debugger::mapGcuNativeLocations(
                            (*input)->getBuffer());
    if (!result) {
      llvm::errs() << llvm::toString(result.takeError()) << '\n';
      return 1;
    }
    std::error_code error;
    llvm::raw_fd_ostream output(argv[3], error);
    if (error) {
      llvm::errs() << error.message() << '\n';
      return 1;
    }
    output << *result;
    output.close();
    return output.has_error() ? 1 : 0;
  }
  if (argc != 6 && argc != 7) {
    llvm::errs() << "Usage: flagprism-gcu-timeline INPUT OUTPUT MANIFEST "
                    "HIDDEN_INDEX CAPACITY [MAX_SOURCE_REGIONS]\n";
    return 2;
  }
  uint32_t hidden = 0, capacity = 0;
  for (auto [value, target] :
       {std::pair<const char *, uint32_t *>{argv[4], &hidden},
        {argv[5], &capacity}}) {
    auto length = std::char_traits<char>::length(value);
    auto result = std::from_chars(value, value + length, *target);
    if (result.ec != std::errc{} || result.ptr != value + length)
      return 2;
  }
  uint32_t regions = 8;
  if (argc == 7) {
    const char *value = argv[6];
    auto length = std::char_traits<char>::length(value);
    auto result = std::from_chars(value, value + length, regions);
    if (result.ec != std::errc{} || result.ptr != value + length)
      return 2;
  }
  auto input = llvm::MemoryBuffer::getFile(argv[1]);
  if (!input) {
    llvm::errs() << input.getError().message() << '\n';
    return 1;
  }
  auto result = mlir::flagtree::debugger::rewriteGcuExecutionTimeline(
      (*input)->getBuffer(), hidden, capacity, regions);
  if (!result) {
    llvm::errs() << llvm::toString(result.takeError()) << '\n';
    return 1;
  }
  std::error_code error;
  llvm::raw_fd_ostream output(argv[2], error);
  if (error) {
    llvm::errs() << error.message() << '\n';
    return 1;
  }
  output << result->ir;
  llvm::raw_fd_ostream manifest(argv[3], error);
  if (error) {
    llvm::errs() << error.message() << '\n';
    return 1;
  }
  manifest << result->manifest << '\n';
  return 0;
}
