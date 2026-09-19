#ifdef FLAGPRISM_BACKEND_ENFLAME
#include "Profiler/Vendor/EnflameProfiler.h"
#endif
#include "Profiler/Vendor/Adapter.h"

#if !defined(FLAGPRISM_BACKEND_ENFLAME) &&                                     \
    !defined(FLAGPRISM_BACKEND_TIANSHU) &&                                     \
    !defined(FLAGPRISM_BACKEND_MTHREADS)
#include "Profiler/Vendor/CannAdapter.h"
#endif
#if !defined(FLAGPRISM_BACKEND_ENFLAME) &&                                     \
    !defined(FLAGPRISM_BACKEND_ASCEND) && !defined(FLAGPRISM_BACKEND_MTHREADS)
#include "Profiler/Vendor/TianshuAdapter.h"
#endif
#if !defined(FLAGPRISM_BACKEND_ENFLAME) &&                                     \
    !defined(FLAGPRISM_BACKEND_ASCEND) && !defined(FLAGPRISM_BACKEND_TIANSHU)
#include "Profiler/Vendor/MthreadsAdapter.h"
#endif
#include "Utility/String.h"

namespace proton {

const VendorAdapter *VendorAdapterRegistry::find(const std::string &name) {
  auto lower = toLower(name);
#ifdef FLAGPRISM_BACKEND_ENFLAME
  if (lower == "enflame" || lower == "gcu" || lower == "tops")
    return &EnflameAdapter::instance();
#endif
#if !defined(FLAGPRISM_BACKEND_ENFLAME) &&                                     \
    !defined(FLAGPRISM_BACKEND_TIANSHU) &&                                     \
    !defined(FLAGPRISM_BACKEND_MTHREADS)
  if (lower == "cann") {
    return &CannAdapter::instance();
  }
#endif
#if !defined(FLAGPRISM_BACKEND_ENFLAME) &&                                     \
    !defined(FLAGPRISM_BACKEND_ASCEND) && !defined(FLAGPRISM_BACKEND_MTHREADS)
  if (lower == "tianshu" || lower == "corex" || lower == "iluvatar") {
    return &TianshuAdapter::instance();
  }
#endif
#if !defined(FLAGPRISM_BACKEND_ENFLAME) &&                                     \
    !defined(FLAGPRISM_BACKEND_ASCEND) && !defined(FLAGPRISM_BACKEND_TIANSHU)
  if (lower == "mthreads" || lower == "musa") {
    return &MthreadsAdapter::instance();
  }
#endif
  return nullptr;
}

std::vector<std::string> VendorAdapterRegistry::names() {
  std::vector<std::string> result;
#ifdef FLAGPRISM_BACKEND_ENFLAME
  result.push_back("enflame");
#endif
#if !defined(FLAGPRISM_BACKEND_ENFLAME) &&                                     \
    !defined(FLAGPRISM_BACKEND_TIANSHU) &&                                     \
    !defined(FLAGPRISM_BACKEND_MTHREADS)
  result.push_back("cann");
#endif
#if !defined(FLAGPRISM_BACKEND_ENFLAME) &&                                     \
    !defined(FLAGPRISM_BACKEND_ASCEND) && !defined(FLAGPRISM_BACKEND_MTHREADS)
  result.push_back("tianshu");
#endif
#if !defined(FLAGPRISM_BACKEND_ENFLAME) &&                                     \
    !defined(FLAGPRISM_BACKEND_ASCEND) && !defined(FLAGPRISM_BACKEND_TIANSHU)
  result.push_back("mthreads");
#endif
  return result;
}

} // namespace proton
