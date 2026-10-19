#include "Debugger/Instrumentation/GcuTimeline.h"
#include "llvm/DebugInfo/DWARF/DWARFContext.h"
#include "llvm/DebugInfo/DWARF/DWARFDebugLine.h"
#include "llvm/DebugInfo/DWARF/DWARFUnit.h"
#include "llvm/Object/ObjectFile.h"
#include "llvm/Support/FormatVariadic.h"
#include "llvm/Support/JSON.h"
#include "llvm/Support/MemoryBufferRef.h"
#include "llvm/Support/Path.h"
#include <limits>
#include <vector>

namespace mlir::flagtree::debugger {
llvm::Expected<std::string> mapGcuNativeLocations(llvm::StringRef input) {
  if (input.size() > 16 * 1024 * 1024)
    return llvm::createStringError(llvm::inconvertibleErrorCode(),
                                   "Native location ELF exceeds its budget");
  auto object = llvm::object::ObjectFile::createObjectFile(
      llvm::MemoryBufferRef(input, "profiled.elf"));
  if (!object)
    return object.takeError();
  if (!(*object)->isELF())
    return llvm::createStringError(llvm::inconvertibleErrorCode(),
                                   "Native locations require an ELF object");
  struct Section {
    std::string name;
    uint64_t index, address, size;
  };
  std::vector<Section> sections;
  llvm::json::Array sectionDescriptions;
  for (const auto &section : (*object)->sections()) {
    if (!section.isText())
      continue;
    auto name = section.getName();
    if (!name)
      return name.takeError();
    uint64_t address = section.getAddress(), size = section.getSize();
    if (size > std::numeric_limits<uint64_t>::max() - address)
      return llvm::createStringError(llvm::inconvertibleErrorCode(),
                                     "Executable section extent overflow");
    sections.push_back({name->str(), section.getIndex(), address, size});
    sectionDescriptions.push_back(
        llvm::json::Object{{"name", name->str()},
                           {"index", section.getIndex()},
                           {"address", address},
                           {"bytes", size}});
  }
  auto context = llvm::DWARFContext::create(**object);
  llvm::json::Array locations;
  uint64_t unknownLines = 0, unknownColumns = 0, checkedRows = 0;
  for (const auto &unit : context->compile_units()) {
    std::string recoverableErrors;
    auto table =
        context->getLineTableForUnit(unit.get(), [&](llvm::Error error) {
          recoverableErrors += llvm::toString(std::move(error)) + "\n";
        });
    if (!table)
      return table.takeError();
    if (!recoverableErrors.empty())
      return llvm::createStringError(llvm::inconvertibleErrorCode(),
                                     recoverableErrors);
    if (!*table)
      continue;
    for (const auto &row : (*table)->Rows) {
      if (++checkedRows > 1000000)
        return llvm::createStringError(llvm::inconvertibleErrorCode(),
                                       "Native location row budget exceeded");
      if (row.EndSequence)
        continue;
      std::string file;
      const char *directory = unit->getCompilationDir();
      if (!(*table)->getFileNameByIndex(
              row.File, directory ? directory : "",
              llvm::DILineInfoSpecifier::FileLineInfoKind::AbsoluteFilePath,
              file))
        return llvm::createStringError(llvm::inconvertibleErrorCode(),
                                       "Cannot resolve native location file");
      if (llvm::sys::path::filename(file) != "__flagprism_gcu_clock_v1__")
        continue;
      if (row.Line == 0) {
        ++unknownLines;
        continue;
      }
      if (row.Column < 1 || row.Column > 4) {
        ++unknownColumns;
        continue;
      }
      const Section *matched = nullptr;
      for (const auto &section : sections) {
        if (row.Address.SectionIndex !=
                llvm::object::SectionedAddress::UndefSection &&
            row.Address.SectionIndex != section.index)
          continue;
        if (row.Address.Address < section.address ||
            row.Address.Address - section.address >= section.size)
          continue;
        if (matched)
          return llvm::createStringError(
              llvm::inconvertibleErrorCode(),
              "Ambiguous executable location section");
        matched = &section;
      }
      if (!matched)
        return llvm::createStringError(
            llvm::inconvertibleErrorCode(),
            "Native clock location is outside executable code");
      const char *phases[] = {"begin_counter", "end_counter", "begin_identity",
                              "end_identity"};
      locations.push_back(llvm::json::Object{
          {"site_id", row.Line},
          {"column", row.Column},
          {"phase", phases[row.Column - 1]},
          {"address", row.Address.Address},
          {"section", matched->name},
          {"section_index", matched->index},
          {"section_offset", row.Address.Address - matched->address}});
      if (locations.size() > 65536)
        return llvm::createStringError(llvm::inconvertibleErrorCode(),
                                       "Native clock location budget exceeded");
    }
  }
  bool available = !locations.empty();
  llvm::json::Object result{
      {"schema_version", 1},
      {"status", available ? "compiler_locations_mapped" : "unavailable"},
      {"semantics", "compiler_debug_location_rows"},
      {"marker_file", "__flagprism_gcu_clock_v1__"},
      {"sections", std::move(sectionDescriptions)},
      {"locations", std::move(locations)},
      {"unknown_line_rows", unknownLines},
      {"unsupported_column_rows", unknownColumns},
      {"source_region_qualified", false},
      {"reader_valueflow_qualified", false},
      {"hardware_busy_qualified", false}};
  return llvm::formatv("{0:2}", llvm::json::Value(std::move(result))).str();
}
} // namespace mlir::flagtree::debugger
