#include "Profiler/Vendor/CannProfiler.h"
#include "Profiler/Vendor/CannLaunchReceipt.h"

#include "Data/Data.h"
#include "Data/Metric.h"
#include "Device.h"
#include "Utility/String.h"

#include <algorithm>
#include <atomic>
#include <cctype>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <limits>
#include <map>
#include <memory>
#include <nlohmann/json.hpp>
#include <optional>
#include <set>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>

#if defined(__linux__)
#include <dlfcn.h>
#include <unistd.h>
#endif

namespace proton {

namespace {

constexpr uint64_t kAclProfAclApi = 0x00000001;
constexpr uint64_t kAclProfTaskTime = 0x00000002;
constexpr uint64_t kAclProfAicoreMetrics = 0x00000004;
constexpr uint64_t kAclProfMsprofTx = 0x00000080;
constexpr uint64_t kAclProfRuntimeApi = 0x00000100;
constexpr int kAclProfSysHardwareMemFreq = 3;

constexpr uint64_t kAclAicoreArithmeticUtilization = 0;
constexpr uint64_t kAclAicoreMemoryAccess = 8;

uint64_t nowNs() {
  auto now = std::chrono::steady_clock::now().time_since_epoch();
  return std::chrono::duration_cast<std::chrono::nanoseconds>(now).count();
}

std::string getEnvOrDefault(const char *key, const std::string &fallback) {
  const char *value = std::getenv(key);
  if (!value) {
    return fallback;
  }
  return std::string(value);
}

uint64_t parseAclProfFlags(const std::string &flags) {
  static const std::map<std::string, uint64_t> kFlagMap = {
      {"ACL_PROF_ACL_API", kAclProfAclApi},
      {"ACL_PROF_TASK_TIME", kAclProfTaskTime},
      {"ACL_PROF_AICORE_METRICS", kAclProfAicoreMetrics},
      {"ACL_PROF_MSPROFTX", kAclProfMsprofTx},
      {"ACL_PROF_RUNTIME_API", kAclProfRuntimeApi},
  };
  uint64_t mask = 0;
  for (const auto &token : split(flags, ",")) {
    auto key = trim(token);
    auto it = kFlagMap.find(key);
    if (it != kFlagMap.end()) {
      mask |= it->second;
    }
  }
  return mask;
}

bool parseBool(const std::string &value) {
  auto normalized = toLower(trim(value));
  return normalized == "true" || normalized == "1" || normalized == "yes" ||
         normalized == "on";
}

bool adapterOptionEnabled(const std::map<std::string, std::string> &options,
                          const std::vector<std::string> &keys) {
  for (const auto &key : keys) {
    auto it = options.find(key);
    if (it != options.end() && parseBool(it->second)) {
      return true;
    }
  }
  return false;
}

#if defined(__linux__)
using AclError = int;
using AclProfConfig = void;

struct AclProfApi {
  using FnInit = AclError (*)(const char *, size_t);
  using FnFinalize = AclError (*)();
  using FnCreateConfig = AclProfConfig *(*)(uint32_t *, uint32_t, uint32_t,
                                            const void *, uint64_t);
  using FnDestroyConfig = AclError (*)(const AclProfConfig *);
  using FnStart = AclError (*)(const AclProfConfig *);
  using FnStop = AclError (*)(const AclProfConfig *);
  using FnSetConfig = AclError (*)(int, const char *, size_t);
  using FnCreateStamp = void *(*)();
  using FnDestroyStamp = AclError (*)(void *);
  using FnSetStampTraceMessage = AclError (*)(void *, const char *, size_t);
  using FnRangeStart = AclError (*)(void *, uint32_t *);
  using FnRangeStop = AclError (*)(uint32_t);

  void *aclLib{nullptr};
  void *profLib{nullptr};
  FnInit init{nullptr};
  FnFinalize finalize{nullptr};
  FnCreateConfig createConfig{nullptr};
  FnDestroyConfig destroyConfig{nullptr};
  FnStart start{nullptr};
  FnStop stop{nullptr};
  FnSetConfig setConfig{nullptr};
  FnCreateStamp createStamp{nullptr};
  FnDestroyStamp destroyStamp{nullptr};
  FnSetStampTraceMessage setStampTraceMessage{nullptr};
  FnRangeStart rangeStart{nullptr};
  FnRangeStop rangeStop{nullptr};
  bool loaded{false};
  std::string loadError{};

  ~AclProfApi() {
    if (profLib) {
      dlclose(profLib);
    }
    if (aclLib) {
      dlclose(aclLib);
    }
  }

  bool load() {
    if (loaded) {
      return true;
    }

    const std::vector<std::string> searchRoots = {
        getEnvOrDefault("ASCEND_TOOLKIT_PATH", ""),
        getEnvOrDefault("ASCEND_TOOLKIT_HOME", ""),
        "/usr/local/Ascend/cann-8.5.0",
        "/usr/local/Ascend/ascend-toolkit/latest",
        "/usr/local/Ascend/ascend-toolkit/6.0.1",
    };
    std::vector<std::string> aclCandidates = {"libacl_rt.so", "libacl.so",
                                              "libascendcl.so"};
    std::vector<std::string> profCandidates = {"libmsprofiler.so",
                                               "libacl_prof.so"};
    for (const auto &root : searchRoots) {
      if (root.empty()) {
        continue;
      }
      aclCandidates.push_back(root + "/aarch64-linux/lib64/libacl_rt.so");
      aclCandidates.push_back(root + "/lib64/libacl.so");
      aclCandidates.push_back(root + "/lib64/libascendcl.so");
      aclCandidates.push_back(root + "/aarch64-linux/lib64/libacl.so");
      aclCandidates.push_back(root + "/aarch64-linux/lib64/libascendcl.so");
      profCandidates.push_back(root + "/aarch64-linux/lib64/libmsprofiler.so");
      profCandidates.push_back(root + "/lib64/libmsprofiler.so");
      profCandidates.push_back(root + "/tools/profiler/lib64/libmsprofiler.so");
      profCandidates.push_back(
          root + "/toolkit/tools/profiler/lib64/libmsprofiler.so");

      aclCandidates.push_back(root + "/aarch64-linux/devlib/libacl_rt.so");
      aclCandidates.push_back(root + "/aarch64-linux/devlib/libacl.so");
      aclCandidates.push_back(root + "/aarch64-linux/devlib/libascendcl.so");
      aclCandidates.push_back(
          root + "/aarch64-linux/devlib/linux/aarch64/libacl_rt.so");
      aclCandidates.push_back(root +
                              "/aarch64-linux/devlib/linux/aarch64/libacl.so");
      aclCandidates.push_back(
          root + "/aarch64-linux/devlib/linux/aarch64/libascendcl.so");
      profCandidates.push_back(root + "/lib64/libacl_prof.so");
      profCandidates.push_back(root + "/aarch64-linux/lib64/libacl_prof.so");
      profCandidates.push_back(root + "/aarch64-linux/devlib/libacl_prof.so");
      profCandidates.push_back(root + "/aarch64-linux/devlib/linux/aarch64/"
                                      "libacl_prof.so");
    }

    for (const auto &cand : aclCandidates) {
      aclLib = dlopen(cand.c_str(), RTLD_LAZY | RTLD_GLOBAL);
      if (aclLib) {
        break;
      }
    }
    for (const auto &cand : profCandidates) {
      profLib = dlopen(cand.c_str(), RTLD_LAZY | RTLD_GLOBAL);
      if (profLib) {
        break;
      }
    }
    if (!aclLib || !profLib) {
      loadError = "Failed to load libacl.so/libacl_prof.so";
      return false;
    }

    init = reinterpret_cast<FnInit>(dlsym(profLib, "aclprofInit"));
    finalize = reinterpret_cast<FnFinalize>(dlsym(profLib, "aclprofFinalize"));
    createConfig =
        reinterpret_cast<FnCreateConfig>(dlsym(profLib, "aclprofCreateConfig"));
    destroyConfig = reinterpret_cast<FnDestroyConfig>(
        dlsym(profLib, "aclprofDestroyConfig"));
    start = reinterpret_cast<FnStart>(dlsym(profLib, "aclprofStart"));
    stop = reinterpret_cast<FnStop>(dlsym(profLib, "aclprofStop"));
    setConfig =
        reinterpret_cast<FnSetConfig>(dlsym(profLib, "aclprofSetConfig"));
    createStamp =
        reinterpret_cast<FnCreateStamp>(dlsym(profLib, "aclprofCreateStamp"));
    destroyStamp =
        reinterpret_cast<FnDestroyStamp>(dlsym(profLib, "aclprofDestroyStamp"));
    setStampTraceMessage = reinterpret_cast<FnSetStampTraceMessage>(
        dlsym(profLib, "aclprofSetStampTraceMessage"));
    rangeStart =
        reinterpret_cast<FnRangeStart>(dlsym(profLib, "aclprofRangeStart"));
    rangeStop =
        reinterpret_cast<FnRangeStop>(dlsym(profLib, "aclprofRangeStop"));

    if (!init || !finalize || !createConfig || !destroyConfig || !start ||
        !stop) {
      loadError = "Missing aclprof symbols required for runtime profiling";
      return false;
    }

    loaded = true;
    return true;
  }
};

AclProfApi &aclProfApi() {
  static AclProfApi api;
  return api;
}

struct AclRuntimeApi {
  using FnInit = AclError (*)(const char *);
  using FnSetDevice = AclError (*)(int32_t);
  using FnGetDevice = AclError (*)(int32_t *);
  using FnCreateStream = AclError (*)(void **);
  using FnSynchronizeStream = AclError (*)(void *);
  using FnDestroyStream = AclError (*)(void *);

  void *lib{nullptr};
  FnInit init{nullptr};
  FnSetDevice setDevice{nullptr};
  FnGetDevice getDevice{nullptr};
  FnCreateStream createStream{nullptr};
  FnSynchronizeStream synchronizeStream{nullptr};
  FnDestroyStream destroyStream{nullptr};
  bool loaded{false};
  std::string loadError{};
  std::string loadedFrom{};

  ~AclRuntimeApi() {
    if (lib) {
      dlclose(lib);
    }
  }

  bool load() {
    if (loaded) {
      return true;
    }

    const std::vector<std::string> searchRoots = {
        getEnvOrDefault("ASCEND_TOOLKIT_PATH", ""),
        getEnvOrDefault("ASCEND_TOOLKIT_HOME", ""),
        "/usr/local/Ascend/cann-8.5.0",
        "/usr/local/Ascend/ascend-toolkit/latest",
        "/usr/local/Ascend/ascend-toolkit/6.0.1",
    };
    std::vector<std::string> candidates = {"libascendcl.so", "libacl.so"};
    for (const auto &root : searchRoots) {
      if (root.empty()) {
        continue;
      }
      candidates.push_back(root + "/lib64/libascendcl.so");
      candidates.push_back(root + "/lib64/libacl.so");
      candidates.push_back(root + "/aarch64-linux/lib64/libascendcl.so");
      candidates.push_back(root + "/aarch64-linux/lib64/libacl.so");
      candidates.push_back(root + "/aarch64-linux/devlib/libascendcl.so");
      candidates.push_back(root + "/aarch64-linux/devlib/libacl.so");
      candidates.push_back(
          root + "/aarch64-linux/devlib/linux/aarch64/libascendcl.so");
      candidates.push_back(root +
                           "/aarch64-linux/devlib/linux/aarch64/libacl.so");
    }

    std::set<std::string> tried;
    for (const auto &candidate : candidates) {
      if (!tried.insert(candidate).second) {
        continue;
      }
      lib = dlopen(candidate.c_str(), RTLD_LAZY | RTLD_GLOBAL);
      if (!lib) {
        continue;
      }
      setDevice = reinterpret_cast<FnSetDevice>(dlsym(lib, "aclrtSetDevice"));
      getDevice = reinterpret_cast<FnGetDevice>(dlsym(lib, "aclrtGetDevice"));
      createStream =
          reinterpret_cast<FnCreateStream>(dlsym(lib, "aclrtCreateStream"));
      destroyStream =
          reinterpret_cast<FnDestroyStream>(dlsym(lib, "aclrtDestroyStream"));
      synchronizeStream = reinterpret_cast<FnSynchronizeStream>(
          dlsym(lib, "aclrtSynchronizeStream"));
      init = reinterpret_cast<FnInit>(dlsym(lib, "aclInit"));
      if (setDevice && createStream && destroyStream) {
        loaded = true;
        loadedFrom = candidate;
        return true;
      }
      dlclose(lib);
      lib = nullptr;
    }

    loadError =
        "Failed to load AscendCL runtime stream APIs required for mstx ranges.";
    return false;
  }
};

AclRuntimeApi &aclRuntimeApi() {
  static AclRuntimeApi api;
  return api;
}

struct MstxApi {
  using RangeId = uint64_t;
  using DomainHandle = void *;
  using FnRangeStartA = RangeId (*)(const char *, void *);
  using FnRangeEnd = void (*)(RangeId);
  using FnDomainCreateA = DomainHandle (*)(const char *);
  using FnDomainDestroy = void (*)(DomainHandle);
  using FnDomainRangeStartA = RangeId (*)(DomainHandle, const char *, void *);
  using FnDomainRangeEnd = void (*)(DomainHandle, RangeId);

  std::vector<void *> libs;
  FnRangeStartA rangeStartA{nullptr};
  FnRangeEnd rangeEnd{nullptr};
  FnDomainCreateA domainCreateA{nullptr};
  FnDomainDestroy domainDestroy{nullptr};
  FnDomainRangeStartA domainRangeStartA{nullptr};
  FnDomainRangeEnd domainRangeEnd{nullptr};
  bool loaded{false};
  std::string loadError{};
  std::string loadedFrom{};

  ~MstxApi() {
    for (auto *lib : libs) {
      if (lib) {
        dlclose(lib);
      }
    }
  }

  bool resolveFrom(void *lib, const std::string &source) {
    auto candidateRangeStartA =
        reinterpret_cast<FnRangeStartA>(dlsym(lib, "mstxRangeStartA"));
    auto candidateRangeEnd =
        reinterpret_cast<FnRangeEnd>(dlsym(lib, "mstxRangeEnd"));
    if (!candidateRangeStartA || !candidateRangeEnd) {
      return false;
    }

    rangeStartA = candidateRangeStartA;
    rangeEnd = candidateRangeEnd;
    domainCreateA =
        reinterpret_cast<FnDomainCreateA>(dlsym(lib, "mstxDomainCreateA"));
    domainDestroy =
        reinterpret_cast<FnDomainDestroy>(dlsym(lib, "mstxDomainDestroy"));
    domainRangeStartA = reinterpret_cast<FnDomainRangeStartA>(
        dlsym(lib, "mstxDomainRangeStartA"));
    domainRangeEnd =
        reinterpret_cast<FnDomainRangeEnd>(dlsym(lib, "mstxDomainRangeEnd"));
    loaded = true;
    loadedFrom = source;
    return true;
  }

  bool load() {
    if (loaded) {
      return true;
    }

    const std::vector<std::string> searchRoots = {
        getEnvOrDefault("ASCEND_TOOLKIT_PATH", ""),
        getEnvOrDefault("ASCEND_TOOLKIT_HOME", ""),
        "/usr/local/Ascend/cann-8.5.0",
        "/usr/local/Ascend/ascend-toolkit/latest",
        "/usr/local/Ascend/ascend-toolkit/6.0.1",
    };
    const std::vector<std::string> libraryNames = {
        "libmstx.so", "libms_tools_ext.so", "libmsprofiler.so",
        "libprofapi.so"};

    std::vector<std::string> candidates;
    for (const auto &root : searchRoots) {
      if (root.empty()) {
        continue;
      }
      for (const auto &name : libraryNames) {
        candidates.push_back(root + "/tools/mstx/lib64/" + name);
        candidates.push_back(root + "/toolkit/tools/mstx/lib64/" + name);
        candidates.push_back(root + "/lib64/" + name);
        candidates.push_back(root + "/aarch64-linux/lib64/" + name);
        candidates.push_back(root + "/tools/profiler/lib64/" + name);
        candidates.push_back(root + "/tools/profiler/profiler_tool/lib64/" +
                             name);
        candidates.push_back(root + "/tools/mspti/lib64/" + name);
        candidates.push_back(root + "/toolkit/tools/mspti/lib64/" + name);
      }
    }
    candidates.insert(candidates.end(), libraryNames.begin(),
                      libraryNames.end());

    std::set<std::string> tried;
    for (const auto &candidate : candidates) {
      if (!tried.insert(candidate).second) {
        continue;
      }
      void *lib = dlopen(candidate.c_str(), RTLD_LAZY | RTLD_GLOBAL);
      if (!lib) {
        continue;
      }
      if (resolveFrom(lib, candidate)) {
        libs.push_back(lib);
        return true;
      }
      dlclose(lib);
    }

#if defined(RTLD_DEFAULT)
    if (resolveFrom(RTLD_DEFAULT, "global symbol table")) {
      return true;
    }
#endif

    loadError = "Failed to load CANN mstx APIs. Run the program under "
                "`msprof --msproftx=on` and ensure the mstx runtime library is "
                "visible.";
    return false;
  }
};

MstxApi &mstxApi() {
  static MstxApi api;
  return api;
}
#endif

std::string normalizeColumnName(const std::string &name) {
  std::string out;
  out.reserve(name.size());
  for (char c : name) {
    if ((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
        (c >= '0' && c <= '9')) {
      out.push_back(
          static_cast<char>(std::tolower(static_cast<unsigned char>(c))));
    }
  }
  return out;
}

std::vector<std::string> splitCsvLine(const std::string &line) {
  std::vector<std::string> values;
  std::string current;
  bool inQuotes = false;
  for (size_t i = 0; i < line.size(); ++i) {
    char c = line[i];
    if (c == '"') {
      if (inQuotes && i + 1 < line.size() && line[i + 1] == '"') {
        current.push_back('"');
        ++i;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }
    if (c == ',' && !inQuotes) {
      values.push_back(trim(current));
      current.clear();
      continue;
    }
    current.push_back(c);
  }
  values.push_back(trim(current));
  return values;
}

std::optional<double> parseDouble(const std::string &value) {
  auto cleaned = trim(value);
  if (cleaned.empty()) {
    return std::nullopt;
  }
  try {
    size_t parsedChars = 0;
    auto parsed = std::stod(cleaned, &parsedChars);
    if (parsedChars != cleaned.size() || !std::isfinite(parsed)) {
      return std::nullopt;
    }
    return parsed;
  } catch (...) {
    return std::nullopt;
  }
}

std::optional<uint64_t> parseU64(const std::string &value) {
  auto cleaned = trim(value);
  if (cleaned.empty()) {
    return std::nullopt;
  }
  try {
    size_t parsedChars = 0;
    auto parsed = std::stoull(cleaned, &parsedChars);
    if (cleaned.front() == '-' || parsedChars != cleaned.size()) {
      return std::nullopt;
    }
    return static_cast<uint64_t>(parsed);
  } catch (...) {
    return std::nullopt;
  }
}

std::string normalizeMetricKey(const std::string &name) {
  std::string out;
  out.reserve(name.size());
  bool lastUnderscore = false;
  for (char c : name) {
    auto uc = static_cast<unsigned char>(c);
    if ((uc >= 'A' && uc <= 'Z') || (uc >= 'a' && uc <= 'z') ||
        (uc >= '0' && uc <= '9')) {
      out.push_back(static_cast<char>(std::tolower(uc)));
      lastUnderscore = false;
      continue;
    }
    if (!lastUnderscore) {
      out.push_back('_');
      lastUnderscore = true;
    }
  }
  while (!out.empty() && out.front() == '_') {
    out.erase(out.begin());
  }
  while (!out.empty() && out.back() == '_') {
    out.pop_back();
  }
  return out;
}

std::optional<uint64_t>
parseMetricU64(const VendorMetricAssociation &association,
               const std::string &metricName) {
  auto it = association.metrics.find(metricName);
  if (it == association.metrics.end()) {
    return std::nullopt;
  }
  if (std::holds_alternative<uint64_t>(it->second)) {
    return std::get<uint64_t>(it->second);
  }
  if (std::holds_alternative<int64_t>(it->second)) {
    auto value = std::get<int64_t>(it->second);
    if (value >= 0) {
      return static_cast<uint64_t>(value);
    }
  }
  if (std::holds_alternative<double>(it->second)) {
    auto value = std::get<double>(it->second);
    if (value >= 0.0) {
      return static_cast<uint64_t>(value);
    }
  }
  return std::nullopt;
}

std::optional<double>
parseMetricDouble(const VendorMetricAssociation &association,
                  const std::string &metricName) {
  auto it = association.metrics.find(metricName);
  if (it == association.metrics.end()) {
    return std::nullopt;
  }
  if (std::holds_alternative<double>(it->second)) {
    return std::get<double>(it->second);
  }
  if (std::holds_alternative<uint64_t>(it->second)) {
    return static_cast<double>(std::get<uint64_t>(it->second));
  }
  if (std::holds_alternative<int64_t>(it->second)) {
    auto value = std::get<int64_t>(it->second);
    if (value >= 0) {
      return static_cast<double>(value);
    }
  }
  return std::nullopt;
}

bool metricEnabled(const std::vector<std::string> &enabledVendorMetrics,
                   const std::string &metricName) {
  return std::find(enabledVendorMetrics.begin(), enabledVendorMetrics.end(),
                   metricName) != enabledVendorMetrics.end();
}

bool looksLikeMemoryByteMetric(const std::string &key) {
  auto lower = toLower(key);
  bool memoryLike = lower.find("memory") != std::string::npos ||
                    lower.find("mem") != std::string::npos ||
                    lower.find("ddr") != std::string::npos ||
                    lower.find("hbm") != std::string::npos ||
                    lower.find("mte") != std::string::npos ||
                    lower.find("bytes") != std::string::npos ||
                    lower.find("byte") != std::string::npos;
  bool byteLike = lower.find("bytes") != std::string::npos ||
                  lower.find("byte") != std::string::npos ||
                  lower.find("_b") != std::string::npos ||
                  lower.find("_kb") != std::string::npos ||
                  lower.find("_mb") != std::string::npos ||
                  lower.find("_gb") != std::string::npos;
  bool accessLike = lower.find("access") != std::string::npos ||
                    lower.find("read") != std::string::npos ||
                    lower.find("write") != std::string::npos ||
                    lower.find("load") != std::string::npos ||
                    lower.find("store") != std::string::npos ||
                    lower.find("traffic") != std::string::npos;
  return memoryLike && byteLike && accessLike;
}

bool looksLikeBandwidthMetric(const std::string &key) {
  auto lower = toLower(key);
  return lower.find("bandwidth") != std::string::npos ||
         lower.find("throughput") != std::string::npos ||
         ((lower.find("read") != std::string::npos ||
           lower.find("write") != std::string::npos) &&
          (lower.find("_gb_s") != std::string::npos ||
           lower.find("_mb_s") != std::string::npos ||
           lower.find("_kb_s") != std::string::npos ||
           lower.find("_b_s") != std::string::npos));
}

double scaleMemoryMetricToBytes(const std::string &key, double value) {
  auto lower = toLower(key);
  if (lower.find("_gbytes") != std::string::npos ||
      lower.find("_gbyte") != std::string::npos ||
      lower.find("_gb") != std::string::npos) {
    return value * 1'000'000'000.0;
  }
  if (lower.find("_mbytes") != std::string::npos ||
      lower.find("_mbyte") != std::string::npos ||
      lower.find("_mb") != std::string::npos) {
    return value * 1'000'000.0;
  }
  if (lower.find("_kbytes") != std::string::npos ||
      lower.find("_kbyte") != std::string::npos ||
      lower.find("_kb") != std::string::npos) {
    return value * 1'000.0;
  }
  return value;
}

std::optional<double> scaleBandwidthMetricToGbps(const std::string &key,
                                                 double value) {
  auto lower = toLower(key);
  if (lower.find("_gb_s") != std::string::npos ||
      lower.find("_gbyte_s") != std::string::npos ||
      lower.find("_gbytes_s") != std::string::npos ||
      lower.find("_gbps") != std::string::npos) {
    return value;
  }
  if (lower.find("_mb_s") != std::string::npos ||
      lower.find("_mbyte_s") != std::string::npos ||
      lower.find("_mbytes_s") != std::string::npos ||
      lower.find("_mbps") != std::string::npos) {
    return value / 1'000.0;
  }
  if (lower.find("_kb_s") != std::string::npos ||
      lower.find("_kbyte_s") != std::string::npos ||
      lower.find("_kbytes_s") != std::string::npos ||
      lower.find("_kbps") != std::string::npos) {
    return value / 1'000'000.0;
  }
  if (lower.find("_b_s") != std::string::npos ||
      lower.find("_byte_s") != std::string::npos ||
      lower.find("_bytes_s") != std::string::npos ||
      lower.find("_bps") != std::string::npos) {
    return value / 1'000'000'000.0;
  }
  return std::nullopt;
}

void enrichBandwidthMetrics(
    VendorMetricAssociation &association,
    const std::vector<std::string> &enabledVendorMetrics) {
  if (!metricEnabled(enabledVendorMetrics, "bandwidth")) {
    return;
  }

  std::optional<double> directBandwidthGbps;
  std::optional<double> directReadBandwidthGbps;
  std::optional<double> directWriteBandwidthGbps;
  std::string directBandwidthKey;
  std::optional<double> readBytes;
  std::optional<double> writeBytes;
  std::optional<double> totalBytes;
  std::string totalBytesKey;

  for (const auto &[key, value] : association.metrics) {
    auto numeric = parseMetricDouble(association, key);
    if (!numeric.has_value()) {
      continue;
    }

    if (looksLikeBandwidthMetric(key)) {
      auto scaled = scaleBandwidthMetricToGbps(key, numeric.value());
      if (scaled.has_value()) {
        auto lower = toLower(key);
        if (lower.find("read") != std::string::npos) {
          directReadBandwidthGbps =
              directReadBandwidthGbps.value_or(0.0) + scaled.value();
        } else if (lower.find("write") != std::string::npos) {
          directWriteBandwidthGbps =
              directWriteBandwidthGbps.value_or(0.0) + scaled.value();
        } else if (!directBandwidthGbps.has_value()) {
          directBandwidthGbps = scaled.value();
          directBandwidthKey = key;
        }
      }
    }

    if (looksLikeMemoryByteMetric(key)) {
      auto bytes = scaleMemoryMetricToBytes(key, numeric.value());
      auto lower = toLower(key);
      if (lower.find("read") != std::string::npos ||
          lower.find("load") != std::string::npos) {
        readBytes = readBytes.value_or(0.0) + bytes;
      } else if (lower.find("write") != std::string::npos ||
                 lower.find("store") != std::string::npos) {
        writeBytes = writeBytes.value_or(0.0) + bytes;
      } else if (!totalBytes.has_value()) {
        totalBytes = bytes;
        totalBytesKey = key;
      }
    }
  }

  if (!totalBytes.has_value() &&
      (readBytes.has_value() || writeBytes.has_value())) {
    totalBytes = readBytes.value_or(0.0) + writeBytes.value_or(0.0);
    totalBytesKey = "memory_read_write_bytes";
  }

  if (readBytes.has_value() && association.metrics.find("memory_read_bytes") ==
                                   association.metrics.end()) {
    association.metrics["memory_read_bytes"] = readBytes.value();
  }
  if (writeBytes.has_value() &&
      association.metrics.find("memory_write_bytes") ==
          association.metrics.end()) {
    association.metrics["memory_write_bytes"] = writeBytes.value();
  }
  if (totalBytes.has_value() &&
      association.metrics.find("memory_access_bytes") ==
          association.metrics.end()) {
    association.metrics["memory_access_bytes"] = totalBytes.value();
  }

  if (!directBandwidthGbps.has_value() &&
      (directReadBandwidthGbps.has_value() ||
       directWriteBandwidthGbps.has_value())) {
    directBandwidthGbps = directReadBandwidthGbps.value_or(0.0) +
                          directWriteBandwidthGbps.value_or(0.0);
    directBandwidthKey = "memory_read_write_bandwidth";
  }

  if (directReadBandwidthGbps.has_value()) {
    association.metrics["memory_read_bandwidth_gb_s"] =
        directReadBandwidthGbps.value();
  }
  if (directWriteBandwidthGbps.has_value()) {
    association.metrics["memory_write_bandwidth_gb_s"] =
        directWriteBandwidthGbps.value();
  }
  if (directBandwidthGbps.has_value()) {
    association.metrics["bandwidth_gb_s"] = directBandwidthGbps.value();
    association.metrics["bandwidth_source"] =
        std::string("direct_csv_column:") + directBandwidthKey;
    return;
  }

  auto durationUs = parseMetricDouble(association, "task_duration_us");
  if (totalBytes.has_value() && durationUs.has_value() &&
      durationUs.value() > 0.0) {
    association.metrics["bandwidth_gb_s"] =
        totalBytes.value() / (durationUs.value() * 1000.0);
    association.metrics["bandwidth_source"] =
        std::string("derived_from_bytes_and_task_duration:") + totalBytesKey;
  }
}

std::optional<size_t>
findColumn(const std::vector<std::string> &headers,
           const std::unordered_set<std::string> &candidates) {
  for (size_t i = 0; i < headers.size(); ++i) {
    if (candidates.count(normalizeColumnName(headers[i])) > 0) {
      return i;
    }
  }
  return std::nullopt;
}

bool endsWithLower(const std::string &value, const std::string &suffix) {
  if (value.size() < suffix.size()) {
    return false;
  }
  return toLower(value.substr(value.size() - suffix.size())) == suffix;
}

bool isCandidateVendorCsvFileName(const std::string &fileName) {
  auto lowerName = toLower(fileName);
  return endsWithLower(lowerName, ".csv") &&
         (lowerName.find("op_summary") != std::string::npos ||
          lowerName.find("task_time") != std::string::npos ||
          lowerName.find("op_statistic") != std::string::npos ||
          lowerName.find("api_statistic") != std::string::npos ||
          lowerName.find("step_trace") != std::string::npos ||
          lowerName.find("kernel_details") != std::string::npos ||
          lowerName.find("mstx") != std::string::npos ||
          lowerName.find("msproftx") != std::string::npos ||
          lowerName.find("msprof_tx") != std::string::npos ||
          lowerName.find("aicpu") != std::string::npos ||
          lowerName.find("aicore") != std::string::npos ||
          lowerName.find("hbm") != std::string::npos ||
          lowerName.find("llc") != std::string::npos ||
          lowerName.find("bandwidth") != std::string::npos ||
          lowerName.find("memory") != std::string::npos ||
          lowerName.find("mem") != std::string::npos ||
          lowerName.find("summary") != std::string::npos);
}

uint64_t parseTimeToNs(const std::string &rawValue,
                       const std::string &rawHeader) {
  const auto cleaned = trim(rawValue);
  try {
    size_t consumed = 0;
    const auto value = std::stold(cleaned, &consumed);
    if (consumed != cleaned.size() || !std::isfinite(value) || value < 0)
      return 0;
    const auto header = toLower(rawHeader);
    const long double factor = header.find("ns") != std::string::npos ? 1.0L :
        (header.find("ms") != std::string::npos ? 1'000'000.0L : 1'000.0L);
    const auto ns = value * factor;
    if (ns > static_cast<long double>(std::numeric_limits<uint64_t>::max()))
      return 0;
    return static_cast<uint64_t>(std::round(ns));
  } catch (...) {
    return 0;
  }
}

std::vector<std::filesystem::path>
collectCandidateCsvFiles(const SessionProfileMetadata &metadata) {
  std::vector<std::filesystem::path> roots;
  std::vector<std::filesystem::path> importRoots;
  std::vector<std::filesystem::path> outputRoots;
  auto addImportRoot = [&importRoots](const std::string &value) {
    auto cleaned = trim(value);
    if (!cleaned.empty()) {
      importRoots.push_back(std::filesystem::path(cleaned));
    }
  };
  auto addOutputRoot = [&outputRoots](const std::string &value) {
    auto cleaned = trim(value);
    if (!cleaned.empty()) {
      outputRoots.push_back(std::filesystem::path(cleaned));
    }
  };

  const std::vector<std::string> importRootKeys = {
      "msprof_import_path", "cann_import_path", "vendor_import_path"};
  for (const auto &key : importRootKeys) {
    auto it = metadata.config.find(key);
    if (it != metadata.config.end()) {
      addImportRoot(it->second);
    }
  }
  addImportRoot(getEnvOrDefault("FLAGTREE_PROFILER_CANN_IMPORT_PATH", ""));

  if (!importRoots.empty()) {
    roots = std::move(importRoots);
  } else {
    const std::vector<std::string> outputRootKeys = {
        "aclprof_output_path", "output_path", "msprof_output_path"};
    for (const auto &key : outputRootKeys) {
      auto it = metadata.config.find(key);
      if (it != metadata.config.end()) {
        addOutputRoot(it->second);
      }
    }

    if (!outputRoots.empty()) {
      roots = std::move(outputRoots);
    }
  }

  if (roots.empty()) {
    auto sessionPath = std::filesystem::path(metadata.sessionName);
    if (!sessionPath.empty()) {
      if (sessionPath.has_parent_path()) {
        roots.push_back(sessionPath.parent_path());
      }
      roots.push_back(sessionPath);
    }
  }

  std::set<std::filesystem::path> uniqueRoots(roots.begin(), roots.end());
  std::set<std::string> uniqueCsvFiles;
  std::vector<std::filesystem::path> csvFiles;
  auto addCsv = [&](const std::filesystem::path &path) {
    auto key = path.lexically_normal().string();
    if (uniqueCsvFiles.insert(key).second) {
      csvFiles.push_back(path);
    }
  };

  for (const auto &root : uniqueRoots) {
    std::error_code ec;
    if (!std::filesystem::exists(root, ec)) {
      continue;
    }
    if (std::filesystem::is_regular_file(root, ec)) {
      auto fileName = toLower(root.filename().string());
      if (endsWithLower(fileName, ".csv")) {
        addCsv(root);
      }
      continue;
    }
    auto options = std::filesystem::directory_options::skip_permission_denied;
    std::filesystem::recursive_directory_iterator it(root, options, ec);
    const std::filesystem::recursive_directory_iterator end;
    while (it != end) {
      std::error_code entryEc;
      if (it->is_regular_file(entryEc) && !entryEc) {
        auto fileName = toLower(it->path().filename().string());
        if (isCandidateVendorCsvFileName(fileName)) {
          addCsv(it->path());
        }
      }
      it.increment(ec);
      if (ec) {
        ec.clear();
      }
    }
  }
  return csvFiles;
}

void parseOpSummaryCsv(const std::filesystem::path &file,
                       const std::vector<std::string> &enabledVendorMetrics,
                       VendorProfileArtifact &artifact) {
  std::ifstream in(file.string());
  if (!in.is_open()) {
    artifact.degradeReasons.push_back("Failed to open vendor CSV: " +
                                      file.string());
    return;
  }

  std::string headerLine;
  if (!std::getline(in, headerLine)) {
    return;
  }
  auto headers = splitCsvLine(headerLine);
  if (headers.empty()) {
    return;
  }

  const auto opNameIdx = findColumn(headers, {"opname", "op", "kernelname"});
  const auto taskIdIdx = findColumn(headers, {"taskid"});
  const auto corrIdIdx =
      findColumn(headers, {"correlationid", "correlation_id", "corrid"});
  const auto streamIdIdx = findColumn(headers, {"streamid"});
  const auto deviceIdIdx = findColumn(headers, {"deviceid", "device"});
  const auto startIdx =
      findColumn(headers, {"taskstarttimeus", "starttimeus", "taskstarttime"});
  const auto durationIdx =
      findColumn(headers, {"taskdurationus", "durationus", "taskduration"});
  const auto aiCoreTimeIdx =
      findColumn(headers, {"aicoretimems", "aicoretime"});
  const auto totalCycleIdx = findColumn(headers, {"totalcycle", "totalcycles"});

  size_t parsedRows = 0;
  std::string line;
  while (std::getline(in, line)) {
    auto row = splitCsvLine(line);
    if (row.empty()) {
      continue;
    }
    auto getCell = [&row](std::optional<size_t> idx) -> std::string {
      if (!idx.has_value() || idx.value() >= row.size()) {
        return {};
      }
      return trim(row[idx.value()]);
    };

    auto startRaw = getCell(startIdx);
    auto durationRaw = getCell(durationIdx);
    if (startRaw.empty() || durationRaw.empty()) {
      continue;
    }
    uint64_t startTimeNs =
        parseTimeToNs(startRaw, startIdx.has_value() ? headers[startIdx.value()]
                                                     : "start_time_us");
    uint64_t durationNs = parseTimeToNs(
        durationRaw,
        durationIdx.has_value() ? headers[durationIdx.value()] : "duration_us");
    if (startTimeNs == 0 || durationNs == 0) {
      continue;
    }

    VendorMetricAssociation association;
    association.state = VendorMetricState::Collected;
    association.source = "aclprof_op_summary";
    association.metrics["activity.kind"] = std::string("kernel");
    association.metrics["activity.semantics"] = std::string("native_device_task_lifecycle");
    association.metrics["activity.clock_domain"] = std::string("cann_export");
    association.metrics["activity.unknown_fields"] = std::string("process_id,thread_id,context_id");
    association.runtimeEvent.opName = getCell(opNameIdx);
    association.runtimeEvent.streamId =
        parseU64(getCell(streamIdIdx)).value_or(0);
    association.runtimeEvent.deviceId =
        parseU64(getCell(deviceIdIdx)).value_or(0);
    association.runtimeEvent.startTimeNs = startTimeNs;
    association.runtimeEvent.endTimeNs = startTimeNs + durationNs;

    if (auto taskId = parseU64(getCell(taskIdIdx)); taskId.has_value()) {
      association.runtimeEvent.taskId = taskId.value();
      association.metrics["task_id"] = taskId.value();
    }
    if (auto corrId = parseU64(getCell(corrIdIdx)); corrId.has_value()) {
      association.runtimeEvent.correlationId = corrId.value();
      association.metrics["correlation_id"] = corrId.value();
    }
    association.metrics["task_duration_us"] =
        static_cast<double>(durationNs) / 1000.0;
    association.metrics["runtime_base_source"] =
        std::string("aclprof_op_summary");
    association.metrics["input_file"] = file.string();

    if (std::find(enabledVendorMetrics.begin(), enabledVendorMetrics.end(),
                  "aicore") != enabledVendorMetrics.end()) {
      if (auto aiCoreTimeMs = parseDouble(getCell(aiCoreTimeIdx));
          aiCoreTimeMs.has_value()) {
        association.metrics["aicore_time_ms"] = aiCoreTimeMs.value();
      }
      if (auto totalCycles = parseU64(getCell(totalCycleIdx));
          totalCycles.has_value()) {
        association.metrics["total_cycles"] = totalCycles.value();
      }
    }

    for (size_t i = 0; i < headers.size() && i < row.size(); ++i) {
      auto key = normalizeMetricKey(headers[i]);
      auto value = trim(row[i]);
      if (key.empty() || value.empty() ||
          association.metrics.find(key) != association.metrics.end()) {
        continue;
      }
      if (auto u64Value = parseU64(value); u64Value.has_value()) {
        association.metrics[key] = u64Value.value();
      } else if (auto doubleValue = parseDouble(value);
                 doubleValue.has_value()) {
        association.metrics[key] = doubleValue.value();
      } else {
        association.metrics[key] = value;
      }
    }

    enrichBandwidthMetrics(association, enabledVendorMetrics);
    artifact.associations.push_back(std::move(association));
    ++parsedRows;
  }

  if (parsedRows == 0) {
    artifact.degradeReasons.push_back(
        "No rows with task timing fields found in " + file.string());
  }
}

void parseTaskTimeCsv(const std::filesystem::path &file,
                      std::vector<RuntimeTraceEventKey> &runtimeEvents,
                      std::vector<std::string> &degradeReasons) {
  std::ifstream in(file.string());
  if (!in.is_open()) {
    degradeReasons.push_back("Failed to open runtime task_time CSV: " +
                             file.string());
    return;
  }

  std::string headerLine;
  if (!std::getline(in, headerLine)) {
    return;
  }
  auto headers = splitCsvLine(headerLine);
  if (headers.empty()) {
    return;
  }

  const auto opNameIdx = findColumn(headers, {"opname", "op", "kernelname"});
  const auto taskIdIdx = findColumn(headers, {"taskid"});
  const auto corrIdIdx =
      findColumn(headers, {"correlationid", "correlation_id", "corrid"});
  const auto streamIdIdx = findColumn(headers, {"streamid"});
  const auto deviceIdIdx = findColumn(headers, {"deviceid", "device"});
  const auto startIdx = findColumn(headers, {"taskstarttimeus", "starttimeus",
                                             "taskstarttime", "starttime", "taskstartus"});
  const auto durationIdx = findColumn(
      headers, {"taskdurationus", "durationus", "taskduration", "duration", "tasktimeus"});
  if (!startIdx.has_value() || !durationIdx.has_value()) {
    return;
  }

  size_t parsedRows = 0;
  std::string line;
  while (std::getline(in, line)) {
    auto row = splitCsvLine(line);
    if (row.empty()) {
      continue;
    }
    auto getCell = [&row](std::optional<size_t> idx) -> std::string {
      if (!idx.has_value() || idx.value() >= row.size()) {
        return {};
      }
      return trim(row[idx.value()]);
    };

    auto startRaw = getCell(startIdx);
    auto durationRaw = getCell(durationIdx);
    if (startRaw.empty() || durationRaw.empty()) {
      continue;
    }
    uint64_t startNs = parseTimeToNs(startRaw, headers[startIdx.value()]);
    uint64_t durationNs =
        parseTimeToNs(durationRaw, headers[durationIdx.value()]);
    if (startNs == 0 || durationNs == 0) {
      continue;
    }

    RuntimeTraceEventKey event;
    event.opName = getCell(opNameIdx);
    event.taskId = parseU64(getCell(taskIdIdx)).value_or(0);
    event.correlationId = parseU64(getCell(corrIdIdx)).value_or(0);
    event.streamId = parseU64(getCell(streamIdIdx)).value_or(0);
    event.deviceId = parseU64(getCell(deviceIdIdx)).value_or(0);
    event.startTimeNs = startNs;
    event.endTimeNs = startNs + durationNs;
    runtimeEvents.push_back(std::move(event));
    parsedRows++;
  }

  if (parsedRows == 0) {
    degradeReasons.push_back(
        "No runtime rows were parsed from task_time CSV: " + file.string());
  }
}

std::string classifySupplementalSource(const std::string &fileName) {
  auto lowerName = toLower(fileName);
  if (lowerName.find("op_statistic") != std::string::npos) {
    return "msprof_op_statistic";
  }
  if (lowerName.find("api_statistic") != std::string::npos) {
    return "msprof_api_statistic";
  }
  if (lowerName.find("step_trace") != std::string::npos) {
    return "msprof_step_trace";
  }
  if (lowerName.find("kernel_details") != std::string::npos) {
    return "msprof_kernel_details";
  }
  if (lowerName.find("mstx") != std::string::npos ||
      lowerName.find("msproftx") != std::string::npos ||
      lowerName.find("msprof_tx") != std::string::npos) {
    return "msprof_mstx";
  }
  if (lowerName.find("aicore") != std::string::npos) {
    return "msprof_aicore";
  }
  if (lowerName.find("aicpu") != std::string::npos) {
    return "msprof_aicpu";
  }
  if (lowerName.find("bandwidth") != std::string::npos ||
      lowerName.find("hbm") != std::string::npos ||
      lowerName.find("llc") != std::string::npos ||
      lowerName.find("memory") != std::string::npos ||
      lowerName.find("mem") != std::string::npos) {
    return "msprof_bandwidth";
  }
  return "msprof_summary";
}

bool populateRuntimeEventFromRow(const std::vector<std::string> &headers,
                                 const std::vector<std::string> &row,
                                 RuntimeTraceEventKey &event) {
  std::unordered_map<std::string, std::string> values;
  for (size_t i = 0; i < headers.size() && i < row.size(); ++i) {
    auto key = normalizeColumnName(headers[i]);
    auto value = trim(row[i]);
    if (!key.empty() && !value.empty()) {
      values[key] = value;
    }
  }

  auto getAny = [&](const std::vector<std::string> &keys) -> std::string {
    for (const auto &key : keys) {
      auto it = values.find(key);
      if (it != values.end()) {
        return it->second;
      }
    }
    return {};
  };

  event.opName = getAny({"opname", "op", "kernelname"});
  if (event.opName.empty()) {
    event.opName =
        getAny({"name", "message", "rangename", "range", "eventname"});
  }
  // Scope identity is emitted in the range payload, independent of kernel names.
  const std::string scopePrefix = "flagprism.scope=";
  if (event.opName.rfind(scopePrefix, 0) == 0) {
    const auto end = event.opName.find(';');
    event.scopeId = parseU64(event.opName.substr(scopePrefix.size(),
        end == std::string::npos ? end : end - scopePrefix.size())).value_or(0);
  }
  event.taskId = parseU64(getAny({"taskid"})).value_or(0);
  event.correlationId =
      parseU64(getAny({"correlationid", "correlation_id", "corrid"}))
          .value_or(0);
  event.deviceId = parseU64(getAny({"deviceid", "device"})).value_or(0);
  event.streamId = parseU64(getAny({"streamid"})).value_or(0);

  uint64_t startNs = 0;
  uint64_t endNs = 0;

  for (size_t i = 0; i < headers.size() && i < row.size(); ++i) {
    auto normalized = normalizeColumnName(headers[i]);
    auto value = trim(row[i]);
    if (value.empty()) {
      continue;
    }
    if (normalized == "taskstarttimeus" || normalized == "starttimeus" ||
        normalized == "taskstarttime" || normalized == "starttime" ||
        normalized == "starttimens" || normalized == "starttimestamp") {
      startNs = parseTimeToNs(value, headers[i]);
    } else if (normalized == "taskdurationus" || normalized == "durationus" ||
               normalized == "taskduration" || normalized == "duration" ||
               normalized == "durationns") {
      auto durationNs = parseTimeToNs(value, headers[i]);
      if (startNs > 0 && durationNs > 0) {
        endNs = startNs + durationNs;
      }
    } else if (normalized == "taskendtimeus" || normalized == "endtimeus" ||
               normalized == "taskendtime" || normalized == "endtime" ||
               normalized == "endtimens" || normalized == "endtimestamp") {
      endNs = parseTimeToNs(value, headers[i]);
    }
  }

  if (startNs > 0 && endNs > startNs) {
    event.startTimeNs = startNs;
    event.endTimeNs = endNs;
    return true;
  }
  return false;
}

void parseStructuredSupplementalCsv(
    const std::filesystem::path &file, const std::string &sourceTag,
    const std::vector<std::string> &enabledVendorMetrics,
    VendorProfileArtifact &artifact) {
  std::ifstream in(file.string());
  if (!in.is_open()) {
    artifact.degradeReasons.push_back("Failed to open supplemental CSV: " +
                                      file.string());
    return;
  }

  std::string headerLine;
  if (!std::getline(in, headerLine)) {
    return;
  }
  auto headers = splitCsvLine(headerLine);
  if (headers.empty()) {
    return;
  }

  constexpr size_t kMaxSupplementalRows = 1024;
  size_t parsedRows = 0;
  std::string line;
  while (parsedRows < kMaxSupplementalRows && std::getline(in, line)) {
    auto row = splitCsvLine(line);
    if (row.empty()) {
      continue;
    }

    VendorMetricAssociation association;
    association.state = VendorMetricState::Collected;
    association.source = sourceTag;
    association.note = "Supplemental msprof row (normalized).";
    if (sourceTag == "msprof_mstx") {
      association.metrics["activity.kind"] = std::string("runtime");
      association.metrics["activity.clock_domain"] = std::string("cann_export");
    }
    association.metrics["input_file"] = file.string();
    association.metrics["summary_row_index"] =
        static_cast<uint64_t>(parsedRows);
    association.metrics["runtime_base_source"] = std::string("supplemental");

    (void)populateRuntimeEventFromRow(headers, row, association.runtimeEvent);
    if (association.runtimeEvent.taskId != 0) {
      association.metrics["task_id"] = association.runtimeEvent.taskId;
    }
    if (association.runtimeEvent.correlationId != 0) {
      association.metrics["correlation_id"] =
          association.runtimeEvent.correlationId;
    }
    if (association.runtimeEvent.startTimeNs > 0 &&
        association.runtimeEvent.endTimeNs >
            association.runtimeEvent.startTimeNs) {
      association.metrics["task_duration_us"] =
          static_cast<double>(association.runtimeEvent.endTimeNs -
                              association.runtimeEvent.startTimeNs) /
          1000.0;
    }

    bool hasMetric = false;
    for (size_t i = 0; i < headers.size() && i < row.size(); ++i) {
      auto key = normalizeMetricKey(headers[i]);
      auto value = trim(row[i]);
      if (key.empty() || value.empty()) {
        continue;
      }
      if (auto u64Value = parseU64(value); u64Value.has_value()) {
        association.metrics[key] = u64Value.value();
      } else if (auto doubleValue = parseDouble(value);
                 doubleValue.has_value()) {
        association.metrics[key] = doubleValue.value();
      } else {
        association.metrics[key] = value;
      }
      hasMetric = true;
    }
    if (hasMetric) {
      enrichBandwidthMetrics(association, enabledVendorMetrics);
      artifact.associations.push_back(std::move(association));
      parsedRows++;
    }
  }

  if (parsedRows == 0) {
    artifact.degradeReasons.push_back("No usable rows in supplemental CSV: " +
                                      file.string());
  }
}

// Import the SDK's native lifecycle and connection identities. Chrome trace
// pid is a display-lane identifier, not an OS process id.
void importNativeTrace(const std::filesystem::path &file,
                       VendorProfileArtifact &artifact) {
  using Json = nlohmann::json;
  Json events;
  try {
    std::ifstream input(file);
    input >> events;
  } catch (const std::exception &error) {
    artifact.degradeReasons.push_back("Cannot parse native CANN trace " +
        file.string() + ": " + error.what());
    return;
  }
  if (!events.is_array()) {
    artifact.degradeReasons.push_back("CANN native trace must be an event array: " + file.string());
    return;
  }
  std::optional<uint64_t> processId;
  try {
    std::ifstream input(file.parent_path().parent_path() / "host" / "info.json");
    if (input) {
      Json info;
      input >> info;
      if (info.contains("pid"))
        processId = parseU64(info["pid"].is_string() ? info["pid"].get<std::string>() : info["pid"].dump());
    }
  } catch (...) {
    artifact.degradeReasons.push_back("CANN host process identity unavailable for " + file.string());
  }
  const auto captureDomain = "cann.sdk.connection:" + file.parent_path().parent_path().filename().string();
  std::map<uint64_t, uint64_t> devices;
  for (const auto &row : events) {
    if (!row.is_object() || row.value("name", "") != "process_labels")
      continue;
    const auto args = row.value("args", Json::object());
    const auto label = args.value("labels", "");
    if (label.rfind("NPU ", 0) == 0 && row.contains("pid") && row["pid"].is_number_unsigned()) {
      if (auto device = parseU64(label.substr(4)))
        devices[row["pid"].get<uint64_t>()] = *device;
    }
  }
  auto stringValue = [](const Json &value) {
    return value.is_string() ? value.get<std::string>() : value.dump();
  };
  for (const auto &row : events) {
    if (!row.is_object() || row.value("ph", "") != "X" || !row.contains("ts") || !row.contains("dur"))
      continue;
    const auto args = row.value("args", Json::object());
    const auto name = row.value("name", "");
    const bool kernel = args.contains("Task Type");
    const bool runtime = args.contains("level") || name.rfind("flagprism.scope=", 0) == 0;
    if (!kernel && !runtime)
      continue;
    VendorMetricAssociation observation;
    observation.state = VendorMetricState::Collected;
    observation.source = "msprof_native_trace";
    auto &event = observation.runtimeEvent;
    event.opName = name;
    event.startTimeNs = parseTimeToNs(stringValue(row["ts"]), "us");
    const auto duration = parseTimeToNs(stringValue(row["dur"]), "us");
    if (duration > std::numeric_limits<uint64_t>::max() - event.startTimeNs)
      continue;
    event.endTimeNs = event.startTimeNs + duration;
    std::string unknown = "context_id";
    if (processId)
      observation.metrics["activity.process_id"] = *processId;
    else
      unknown += ",process_id";
    observation.metrics["activity.correlation_domain"] = captureDomain;
    if (row.contains("pid") && row["pid"].is_number_unsigned()) {
      const auto pid = row["pid"].get<uint64_t>();
      observation.metrics["activity.trace_lane_id"] = pid;
      auto device = devices.find(pid);
      if (kernel && device != devices.end())
        event.deviceId = device->second;
      else
        unknown += ",device_id";
    } else {
      unknown += ",device_id";
    }
    if (args.contains("Task Id"))
      event.taskId = parseU64(stringValue(args["Task Id"])).value_or(0);
    if (args.contains("Physic Stream Id"))
      event.streamId = parseU64(stringValue(args["Physic Stream Id"])).value_or(0);
    else
      unknown += ",stream_id";
    if (args.contains("connection_id"))
      event.correlationId = parseU64(stringValue(args["connection_id"])).value_or(0);
    if (args.contains("Thread Id"))
      observation.metrics["activity.thread_id"] = parseU64(stringValue(args["Thread Id"])).value_or(0);
    else
      unknown += ",thread_id";
    if (name.rfind("flagprism.scope=", 0) == 0) {
      const auto end = name.find(';');
      event.scopeId = parseU64(name.substr(16, end == std::string::npos ? end : end - 16)).value_or(0);
    }
    observation.metrics["activity.kind"] = std::string(kernel ? "kernel" : "runtime");
    observation.metrics["activity.semantics"] = std::string(kernel ? "native_device_task_lifecycle" : "native_runtime_activity");
    observation.metrics["activity.clock_domain"] = std::string("cann_export");
    observation.metrics["activity.unknown_fields"] = unknown;
    observation.metrics["activity.association"] = std::string(event.scopeId != 0 ? "explicit_scope" : "unassociated");
    observation.metrics["input_file"] = file.string();
    observation.metrics["raw_event_json"] = row.dump();
    // Merge only a unique native task with its summary in the same SDK export.
    // This preserves counters without duplicating timed kernel observations.
    VendorMetricAssociation *summary = nullptr;
    size_t candidates = 0;
    if (kernel && event.taskId != 0) {
      for (auto &association : artifact.associations) {
        const auto &key = association.runtimeEvent;
        auto input = association.metrics.find("input_file");
        if (association.source != "aclprof_op_summary" || input == association.metrics.end() || !std::holds_alternative<std::string>(input->second))
          continue;
        if (std::filesystem::path(std::get<std::string>(input->second)).parent_path() != file.parent_path())
          continue;
        if (key.taskId == event.taskId && key.streamId == event.streamId && key.deviceId == event.deviceId) {
          summary = &association;
          ++candidates;
        }
      }
    }
    if (candidates == 1) {
      summary->runtimeEvent.correlationId = event.correlationId;
      summary->metrics["raw_event_json"] = row.dump();
      summary->metrics["native_trace_file"] = file.string();
      summary->metrics["activity.association"] = std::string("native_task_identity");
      summary->metrics["activity.unknown_fields"] = unknown;
      summary->metrics["activity.correlation_domain"] = captureDomain;
      if (processId)
        summary->metrics["activity.process_id"] = *processId;
    } else {
      artifact.associations.push_back(std::move(observation));
    }
  }
}

// Native timestamps and host steady_clock are different clock domains. Only
// explicit correlation or device/stream/task identity can join their records.
void correlateVendorToRuntimeEvents(
    VendorProfileArtifact &artifact,
    const std::vector<RuntimeTraceEventKey> &runtimeEvents) {
  for (auto &association : artifact.associations) {
    if (association.source != "aclprof_op_summary" &&
        association.source != "msprof_mstx")
      continue;
    auto &event = association.runtimeEvent;
    if (event.scopeId != 0) {
      association.metrics["activity.association"] = std::string("explicit_scope");
      continue;
    }
    const RuntimeTraceEventKey *unique = nullptr;
    size_t candidates = 0;
    for (const auto &runtime : runtimeEvents) {
      const bool correlation = event.correlationId != 0 &&
          event.correlationId == runtime.correlationId;
      const bool task = event.taskId != 0 && runtime.taskId == event.taskId &&
          event.deviceId == runtime.deviceId && event.streamId == runtime.streamId;
      if (!(correlation || task))
        continue;
      unique = &runtime;
      ++candidates;
    }
    if (candidates == 1 && unique->scopeId != 0) {
      event.scopeId = unique->scopeId;
      association.metrics["activity.association"] = std::string("native_identity");
      association.note = "Unique native identity; original native timing retained.";
    } else {
      association.metrics["activity.association"] =
          std::string(candidates > 1 ? "ambiguous" : "unassociated");
      association.note = "Native observation retained without source attribution; "
                         "name/order and uncalibrated timestamps are not identities.";
    }
  }
}

void addRuntimeBaseFallbackAssociations(
    VendorProfileArtifact &artifact,
    const std::vector<RuntimeTraceEventKey> &runtimeEvents) {
  for (const auto &event : runtimeEvents) {
    if (event.endTimeNs <= event.startTimeNs) {
      continue;
    }
    VendorMetricAssociation association;
    association.runtimeEvent = event;
    association.state = VendorMetricState::Collected;
    association.source = "runtime_base_fallback";
    association.metrics["activity.kind"] = std::string("runtime");
    association.metrics["activity.semantics"] = std::string("host_launch_scope");
    association.metrics["activity.clock_domain"] = std::string("host_steady_clock");
#if defined(__linux__)
    association.metrics["activity.process_id"] = static_cast<uint64_t>(getpid());
#endif
    association.metrics["activity.unknown_fields"] = std::string("device_id,stream_id,task_id,correlation_id");
    association.note =
        "aclprof summary unavailable; using runtime_base host-timing fallback.";
    association.metrics["runtime_base_source"] =
        std::string("host_timing_fallback");
    association.metrics["runtime_base_only"] = uint64_t(1);
    artifact.associations.push_back(std::move(association));
  }
}

void addRuntimeBaseNativeAssociations(
    VendorProfileArtifact &artifact,
    const std::vector<RuntimeTraceEventKey> &runtimeEvents,
    const std::string &sourceTag, const std::string &sourceMetricTag,
    const std::string &note) {
  for (const auto &event : runtimeEvents) {
    if (event.endTimeNs <= event.startTimeNs) {
      continue;
    }
    VendorMetricAssociation association;
    association.runtimeEvent = event;
    association.state = VendorMetricState::Collected;
    association.source = sourceTag;
    association.metrics["activity.kind"] = std::string("kernel");
    association.metrics["activity.semantics"] = std::string("native_device_task_lifecycle");
    association.metrics["activity.clock_domain"] = std::string("cann_export");
    association.note = note;
    association.metrics["runtime_base_source"] = sourceMetricTag;
    association.metrics["task_duration_us"] =
        static_cast<double>(event.endTimeNs - event.startTimeNs) / 1000.0;
    if (event.taskId != 0) {
      association.metrics["task_id"] = event.taskId;
    }
    if (event.correlationId != 0) {
      association.metrics["correlation_id"] = event.correlationId;
    }
    artifact.associations.push_back(std::move(association));
  }
}

void addAssociationQualityReasons(VendorProfileArtifact &artifact) {
  size_t unmatchedCount = 0;
  size_t collectedCount = 0;
  for (const auto &association : artifact.associations) {
    if (association.state == VendorMetricState::Unmatched) {
      unmatchedCount++;
    } else if (association.state == VendorMetricState::Collected) {
      collectedCount++;
    }
  }
  if (unmatchedCount > 0) {
    artifact.degradeReasons.push_back(
        "Vendor/runtime correlation unmatched entries: " +
        std::to_string(unmatchedCount) +
        " (collected=" + std::to_string(collectedCount) + ").");
  }
}

void appendUniqueReason(std::vector<std::string> &reasons,
                        const std::string &reason) {
  if (std::find(reasons.begin(), reasons.end(), reason) == reasons.end()) {
    reasons.push_back(reason);
  }
}

#if defined(__linux__)
std::string shellQuote(const std::string &value) {
  std::string quoted = "'";
  for (char ch : value) {
    if (ch == '\'') {
      quoted += "'\\''";
    } else {
      quoted += ch;
    }
  }
  quoted += "'";
  return quoted;
}

bool looksLikeMsprofProfileDir(const std::filesystem::path &path) {
  std::error_code ec;
  if (!std::filesystem::is_directory(path, ec)) {
    return false;
  }
  if (std::filesystem::is_directory(path / "host", ec)) {
    return true;
  }
  for (const auto &entry : std::filesystem::directory_iterator(path, ec)) {
    if (ec) {
      break;
    }
    if (!entry.is_directory(ec)) {
      continue;
    }
    auto name = entry.path().filename().string();
    if (name.rfind("device_", 0) == 0) {
      return true;
    }
  }
  return false;
}

std::vector<std::filesystem::path>
collectMsprofExportRoots(const std::filesystem::path &outputPath) {
  std::vector<std::filesystem::path> roots;
  std::error_code ec;
  if (looksLikeMsprofProfileDir(outputPath)) {
    roots.push_back(outputPath);
    return roots;
  }
  if (!std::filesystem::is_directory(outputPath, ec)) {
    return roots;
  }
  for (const auto &entry :
       std::filesystem::directory_iterator(outputPath, ec)) {
    if (ec) {
      break;
    }
    if (!entry.is_directory(ec)) {
      continue;
    }
    auto name = entry.path().filename().string();
    if (name.rfind("PROF_", 0) == 0 &&
        looksLikeMsprofProfileDir(entry.path())) {
      roots.push_back(entry.path());
    }
  }
  std::sort(roots.begin(), roots.end());
  return roots;
}

void exportMsprofCsv(const std::string &outputPath,
                     std::vector<std::string> &reasons) {
  if (outputPath.empty()) {
    appendUniqueReason(
        reasons, "CANN aclprof auto-export skipped: output path is empty.");
    return;
  }
  auto exportRoots =
      collectMsprofExportRoots(std::filesystem::path(outputPath));
  if (exportRoots.empty()) {
    exportRoots.push_back(std::filesystem::path(outputPath));
  }
  for (const auto &exportRoot : exportRoots) {
    auto command =
        "msprof --export=on --type=text --summary-format=csv --output=" +
        shellQuote(exportRoot.string());
    auto ret = std::system(command.c_str());
    if (ret != 0) {
      appendUniqueReason(reasons,
                         "CANN aclprof auto-export failed with status " +
                             std::to_string(ret) + ": " + command);
    }
  }
}

std::vector<std::string> snapshotSdkCaptureRoots(const std::string &outputPath,
                                                 bool &complete) {
  complete = true;
  std::vector<std::string> roots;
  std::error_code error;
  auto root = std::filesystem::absolute(outputPath, error);
  if (error) {
    complete = false;
    return roots;
  }
  if (!std::filesystem::exists(root, error)) {
    complete = !error;
    return roots;
  }
  std::filesystem::recursive_directory_iterator iterator(root, error);
  if (error)
    complete = false;
  const std::filesystem::recursive_directory_iterator end;
  while (iterator != end) {
    std::error_code entryError;
    if (iterator->is_directory(entryError) && !entryError &&
        iterator->path().filename().string().find("PROF_") == 0) {
      roots.push_back(iterator->path().lexically_normal().string());
      iterator.disable_recursion_pending();
    }
    if (entryError)
      complete = false;
    iterator.increment(error);
    if (error) {
      complete = false;
      error.clear();
    }
  }
  std::sort(roots.begin(), roots.end());
  return roots;
}

void sealSdkCaptureDirectory(uint64_t epoch, const std::string &outputPath,
                             const std::vector<std::string> &before,
                             uint32_t selectedDevice, bool beforeScanComplete) {
  bool afterScanComplete;
  const auto after = snapshotSdkCaptureRoots(outputPath, afterScanComplete);
  std::vector<std::string> created;
  std::set_difference(after.begin(), after.end(), before.begin(), before.end(),
                      std::back_inserter(created));
  nlohmann::json evidence = {
      {"kind", "owned_native_sdk_directory_lifetime_v1"},
      {"owned_output_root", std::filesystem::absolute(outputPath).string()},
      {"capture_epoch", epoch},
      {"existing_at_sdk_start", before},
      {"before_scan_complete", beforeScanComplete},
      {"after_scan_complete", afterScanComplete},
      {"observed_after_sdk_close", after},
      {"new_capture_paths", created},
      {"selected_device_id", selectedDevice}};
  if (!beforeScanComplete || !afterScanComplete) {
    sealCannLaunchReceiptCapture(epoch, "", "capture_directory_scan_incomplete",
                                 evidence.dump());
    return;
  }
  if (created.size() != 1) {
    sealCannLaunchReceiptCapture(epoch, "", "missing_or_ambiguous_capture",
                                 evidence.dump());
    return;
  }
  try {
    const auto capture = std::filesystem::path(created[0]);
    const auto hostPath = capture / "host" / "info.json";
    const auto devicePath = capture /
                            ("device_" + std::to_string(selectedDevice)) /
                            ("info.json." + std::to_string(selectedDevice));
    nlohmann::json hostInfo, deviceInfo;
    std::ifstream hostInput(hostPath), deviceInput(devicePath);
    if (!hostInput || !deviceInput) {
      sealCannLaunchReceiptCapture(epoch, "", "capture_metadata_missing",
                                   evidence.dump());
      return;
    }
    hostInput >> hostInfo;
    deviceInput >> deviceInfo;
    std::optional<uint64_t> process;
    if (hostInfo.contains("pid")) {
      const auto &value = hostInfo["pid"];
      if (value.is_number_unsigned())
        process = value.get<uint64_t>();
      else if (value.is_number_integer() && value.get<int64_t>() >= 0)
        process = static_cast<uint64_t>(value.get<int64_t>());
      else if (value.is_string())
        process = parseU64(value.get<std::string>());
    }
    size_t deviceMatches = 0;
    for (const auto &device :
         deviceInfo.value("DeviceInfo", nlohmann::json::array()))
      if (device.is_object() && device.contains("id") &&
          device["id"].is_number_integer() &&
          device["id"].get<int64_t>() == selectedDevice)
        ++deviceMatches;
    evidence["host_info_path"] = hostPath.string();
    evidence["device_info_path"] = devicePath.string();
    evidence["host_info_snapshot"] = hostInfo;
    evidence["device_info_snapshot"] = deviceInfo;
    evidence["collector_process_id"] = static_cast<uint64_t>(getpid());
    if (!process || *process != static_cast<uint64_t>(getpid()) ||
        deviceMatches != 1) {
      sealCannLaunchReceiptCapture(epoch, "", "capture_identity_mismatch",
                                   evidence.dump());
      return;
    }
    sealCannLaunchReceiptCapture(epoch, created[0], "sealed_unique_sdk_capture",
                                 evidence.dump());
  } catch (const std::exception &error) {
    evidence["metadata_error"] = error.what();
    sealCannLaunchReceiptCapture(epoch, "", "capture_metadata_invalid",
                                 evidence.dump());
  }
}
#endif

} // namespace

CannProfiler::CannProfiler() = default;

CannProfiler::~CannProfiler() = default;

void CannProfiler::startOp(const Scope &scope) {
  MsProfTxRange range;
  bool enableMstx = false;
  void *domain = nullptr;
  void *stream = nullptr;

  {
    std::lock_guard<std::mutex> lock(mutex);
    if (hostTimingFallbackEnabled) {
      opStartTimesNs[scope.scopeId] = nowNs();
    }
    enableMstx = mstxActive && msproftxEnabled;
    domain = mstxDomain;
    stream = mstxStream;
  }

#if defined(__linux__)
  if (enableMstx) {
    const auto message = "flagprism.scope=" + std::to_string(scope.scopeId) + ";" + scope.name;
    auto &api = mstxApi();
    if (!api.rangeStartA || !api.rangeEnd) {
      std::lock_guard<std::mutex> lock(mutex);
      appendUniqueReason(
          runtimeDegradeReasons,
          "mstx APIs are unavailable; range annotations are disabled.");
    } else {
      if (domain && api.domainRangeStartA && api.domainRangeEnd) {
        range.rangeId =
            api.domainRangeStartA(domain, message.c_str(), stream);
        range.mstxDomainRange = true;
      } else {
        range.rangeId = api.rangeStartA(message.c_str(), stream);
        range.mstxDomainRange = false;
      }
      if (range.rangeId != 0) {
        range.active = true;
      } else {
        std::lock_guard<std::mutex> lock(mutex);
        appendUniqueReason(
            runtimeDegradeReasons,
            "mstx range start returned an invalid range id from " +
                api.loadedFrom + ".");
      }
    }
  }
#endif

  if (range.active) {
    std::lock_guard<std::mutex> lock(mutex);
    opRanges[scope.scopeId] = range;
  }
}

void CannProfiler::stopOp(const Scope &scope) {
  uint64_t startTimeNs = 0;
  uint64_t endTimeNs = 0;
  MsProfTxRange range;
  void *domain = nullptr;
  {
    std::lock_guard<std::mutex> lock(mutex);
    if (hostTimingFallbackEnabled) {
      auto it = opStartTimesNs.find(scope.scopeId);
      if (it != opStartTimesNs.end()) {
        startTimeNs = it->second;
        opStartTimesNs.erase(it);
      }
      endTimeNs = nowNs();
    }
    auto rangeIt = opRanges.find(scope.scopeId);
    if (rangeIt != opRanges.end()) {
      range = rangeIt->second;
      opRanges.erase(rangeIt);
    }
    domain = mstxDomain;
  }

#if defined(__linux__)
  if (range.active) {
    auto &api = mstxApi();
    if (range.mstxDomainRange && domain && api.domainRangeEnd) {
      api.domainRangeEnd(domain, range.rangeId);
    } else if (api.rangeEnd) {
      api.rangeEnd(range.rangeId);
    } else {
      std::lock_guard<std::mutex> lock(mutex);
      appendUniqueReason(runtimeDegradeReasons,
                         "mstx range end API is unavailable.");
    }
  }
#endif

  if (startTimeNs > 0 && endTimeNs > startTimeNs) {
    RuntimeTraceEventKey runtimeEvent;
    runtimeEvent.scopeId = scope.scopeId;
    runtimeEvent.opName = scope.name;
    runtimeEvent.deviceId = 0;
    runtimeEvent.streamId = 0;
    runtimeEvent.startTimeNs = startTimeNs;
    runtimeEvent.endTimeNs = endTimeNs;
    std::lock_guard<std::mutex> lock(mutex);
    runtimeEvents.push_back(runtimeEvent);
  }
}

void CannProfiler::doStart() {
  std::lock_guard<std::mutex> lock(mutex);
  opStartTimesNs.clear();
  opRanges.clear();
  runtimeEvents.clear();
  runtimeDegradeReasons.clear();
  aclprofActive = false;
  aclprofConfig = nullptr;
  mstxActive = false;
  mstxDomain = nullptr;
  mstxStream = nullptr;
  mstxStreamOwned = false;

  std::error_code ec;
  if (!outputPath.empty()) {
    std::filesystem::create_directories(outputPath, ec);
  }

#if defined(__linux__)
  if (msproftxEnabled) {
    auto &mstx = mstxApi();
    if (!mstx.load()) {
      appendUniqueReason(runtimeDegradeReasons, mstx.loadError);
    } else {
      auto &aclRuntime = aclRuntimeApi();
      if (!aclRuntime.load()) {
        appendUniqueReason(runtimeDegradeReasons, aclRuntime.loadError);
      } else {
        if (aclRuntime.init) {
          (void)aclRuntime.init(nullptr);
        }
        auto setDeviceRet =
            aclRuntime.setDevice(static_cast<int32_t>(deviceId));
        if (setDeviceRet != 0) {
          appendUniqueReason(runtimeDegradeReasons,
                             "aclrtSetDevice failed while preparing mstx "
                             "stream with error code " +
                                 std::to_string(setDeviceRet));
        } else {
          void *stream = nullptr;
          auto createStreamRet = aclRuntime.createStream(&stream);
          if (createStreamRet == 0 && stream) {
            mstxStream = stream;
            mstxStreamOwned = true;
          } else {
            appendUniqueReason(runtimeDegradeReasons,
                               "aclrtCreateStream failed while preparing mstx "
                               "stream from " +
                                   aclRuntime.loadedFrom + " with error code " +
                                   std::to_string(createStreamRet));
          }
        }
      }
      if (!mstxDomainName.empty() && mstx.domainCreateA) {
        mstxDomain = mstx.domainCreateA(mstxDomainName.c_str());
        if (!mstxDomain) {
          appendUniqueReason(runtimeDegradeReasons,
                             "mstxDomainCreateA returned nullptr from " +
                                 mstx.loadedFrom +
                                 "; using default-domain mstx ranges.");
        }
      }
      mstxActive = true;
    }
  }

  if (!aclprofRuntimeEnabled) {
    return;
  }

  auto &api = aclProfApi();
  if (!api.load()) {
    runtimeDegradeReasons.push_back(
        "Optional legacy aclprof runtime path unavailable: " + api.loadError);
    aclprofActive = false;
    aclprofConfig = nullptr;
    return;
  }

  launchReceiptSdkRootsBefore =
      snapshotSdkCaptureRoots(outputPath, launchReceiptSdkRootScanComplete);
  auto initRet = api.init(outputPath.c_str(), outputPath.size());
  if (initRet != 0) {
    runtimeDegradeReasons.push_back("aclprofInit failed with error code " +
                                    std::to_string(initRet));
    aclprofActive = false;
    aclprofConfig = nullptr;
    return;
  }

  uint32_t deviceList[1] = {deviceId};
  aclprofConfig = api.createConfig(deviceList, 1,
                                   static_cast<uint32_t>(aclprofAicoreMetricId),
                                   nullptr, aclprofDataTypeConfig);
  if (!aclprofConfig) {
    runtimeDegradeReasons.push_back("aclprofCreateConfig returned nullptr");
    api.finalize();
    aclprofActive = false;
    return;
  }

  if (api.setConfig && !memFreqHz.empty()) {
    auto setRet = api.setConfig(kAclProfSysHardwareMemFreq, memFreqHz.c_str(),
                                memFreqHz.size());
    if (setRet != 0) {
      runtimeDegradeReasons.push_back("aclprofSetConfig(ACL_PROF_SYS_HARDWARE_"
                                      "MEM_FREQ) failed with error code " +
                                      std::to_string(setRet));
    }
  }

  auto startRet =
      api.start(reinterpret_cast<const AclProfConfig *>(aclprofConfig));
  if (startRet != 0) {
    runtimeDegradeReasons.push_back("aclprofStart failed with error code " +
                                    std::to_string(startRet));
    api.destroyConfig(reinterpret_cast<const AclProfConfig *>(aclprofConfig));
    api.finalize();
    aclprofConfig = nullptr;
    aclprofActive = false;
    return;
  }

  aclprofActive = true;
  auto rollbackStartedSdk = [&](void *config) {
    (void)api.stop(reinterpret_cast<const AclProfConfig *>(config));
    (void)api.destroyConfig(reinterpret_cast<const AclProfConfig *>(config));
    (void)api.finalize();
    aclprofConfig = nullptr;
    aclprofActive = false;
    launchReceiptCaptureEpoch = 0;
    auto &mstx = mstxApi();
    if (mstxDomain && mstx.domainDestroy)
      mstx.domainDestroy(mstxDomain);
    mstxDomain = nullptr;
    if (mstxStreamOwned && mstxStream) {
      auto &runtime = aclRuntimeApi();
      if (runtime.loaded && runtime.destroyStream)
        (void)runtime.destroyStream(mstxStream);
    }
    mstxStream = nullptr;
    mstxStreamOwned = false;
    mstxActive = false;
  };
  std::unique_ptr<void, decltype(rollbackStartedSdk)> rollback(
      aclprofConfig, rollbackStartedSdk);
  launchReceiptCaptureEpoch =
      beginCannLaunchReceiptCapture(deviceId, outputPath);
  if (!launchReceiptCaptureEpoch) {
    appendUniqueReason(
        runtimeDegradeReasons,
        "SDK started but launch receipt epoch initialization failed: "
        "bounded registry exhausted or epoch counter overflowed.");
    throw std::runtime_error("CANN launch receipt epoch initialization failed; "
                             "SDK startup rolled back");
  }
  rollback.release();
#else
  if (msproftxEnabled) {
    runtimeDegradeReasons.push_back(
        "CANN mstx range annotations are only available on Linux.");
  }
  if (aclprofRuntimeEnabled) {
    runtimeDegradeReasons.push_back(
        "CANN legacy aclprof runtime path is only available on Linux.");
  }
  aclprofActive = false;
  aclprofConfig = nullptr;
#endif
}

void CannProfiler::doFlush() {}

void CannProfiler::doStop() {
  const auto receiptEpoch = launchReceiptCaptureEpoch;
  if (launchReceiptCaptureEpoch) {
    endCannLaunchReceiptCapture(launchReceiptCaptureEpoch,
                                "SDK collector closed");
    launchReceiptCaptureEpoch = 0;
  }
  std::unordered_map<size_t, MsProfTxRange> ranges;
  void *domain = nullptr;
  void *stream = nullptr;
  bool streamOwned = false;
  void *profConfig = nullptr;
  bool profActive = false;
  bool autoExport = false;
  std::string exportPath;
  std::vector<std::string> localReasons;

  {
    std::lock_guard<std::mutex> lock(mutex);
    opStartTimesNs.clear();
    ranges.swap(opRanges);
    domain = mstxDomain;
    stream = mstxStream;
    streamOwned = mstxStreamOwned;
    mstxDomain = nullptr;
    mstxStream = nullptr;
    mstxStreamOwned = false;
    mstxActive = false;
    profConfig = aclprofConfig;
    profActive = aclprofActive;
    aclprofConfig = nullptr;
    aclprofActive = false;
    autoExport = aclprofAutoExportEnabled;
    exportPath = outputPath;
  }

#if defined(__linux__)
  auto &mstx = mstxApi();
  if (mstx.loaded) {
    for (auto &[scopeId, range] : ranges) {
      (void)scopeId;
      if (!range.active) {
        continue;
      }
      if (range.mstxDomainRange && domain && mstx.domainRangeEnd) {
        mstx.domainRangeEnd(domain, range.rangeId);
      } else if (mstx.rangeEnd) {
        mstx.rangeEnd(range.rangeId);
      }
    }
  }

  if (domain && mstx.loaded && mstx.domainDestroy) {
    mstx.domainDestroy(domain);
  }

  if (streamOwned && stream) {
    auto &aclRuntime = aclRuntimeApi();
    if (aclRuntime.loaded) {
      if (aclRuntime.synchronizeStream) {
        auto syncRet = aclRuntime.synchronizeStream(stream);
        if (syncRet != 0) {
          localReasons.push_back(
              "aclrtSynchronizeStream failed for mstx stream with error code " +
              std::to_string(syncRet));
        }
      }
      auto destroyRet = aclRuntime.destroyStream(stream);
      if (destroyRet != 0) {
        localReasons.push_back(
            "aclrtDestroyStream failed for mstx stream with error code " +
            std::to_string(destroyRet));
      }
    }
  }

  auto &api = aclProfApi();
  if (profActive && api.loaded) {
    auto stopRet =
        api.stop(reinterpret_cast<const AclProfConfig *>(profConfig));
    if (stopRet != 0) {
      localReasons.push_back("aclprofStop failed with error code " +
                             std::to_string(stopRet));
    }

    auto destroyRet =
        api.destroyConfig(reinterpret_cast<const AclProfConfig *>(profConfig));
    if (destroyRet != 0) {
      localReasons.push_back("aclprofDestroyConfig failed with error code " +
                             std::to_string(destroyRet));
    }

    auto finalizeRet = api.finalize();
    if (finalizeRet != 0) {
      localReasons.push_back("aclprofFinalize failed with error code " +
                             std::to_string(finalizeRet));
    }

    if (autoExport) {
      exportMsprofCsv(exportPath, localReasons);
    }
    if (receiptEpoch)
      sealSdkCaptureDirectory(receiptEpoch, exportPath,
                              launchReceiptSdkRootsBefore, deviceId,
                              launchReceiptSdkRootScanComplete);
  }
#endif

  if (!localReasons.empty()) {
    std::lock_guard<std::mutex> lock(mutex);
    for (const auto &reason : localReasons) {
      appendUniqueReason(runtimeDegradeReasons, reason);
    }
  }
}

void CannProfiler::doSetMode(const std::vector<std::string> &modeAndOptions) {
  this->modeAndOptions = modeAndOptions;

  deviceId = 0;
  outputPath = getEnvOrDefault("FLAGTREE_PROFILER_CANN_PROFILE_OUTPUT",
                               "./flagtree_profiler_cann_profile");
  memFreqHz = "15";
  aclprofDataTypeConfig =
      kAclProfAclApi | kAclProfTaskTime | kAclProfRuntimeApi;
  aclprofAicoreMetricId = kAclAicoreArithmeticUtilization;
  msproftxEnabled = false;
  hostTimingFallbackEnabled = false;
  aclprofRuntimeEnabled = false;
  aclprofAutoExportEnabled = true;
  mstxDomainName = getEnvOrDefault("FLAGTREE_PROFILER_CANN_MSTX_DOMAIN",
                                   "flagtree_profiler");

  bool explicitDeviceId = false;
  bool wantsAicore = false;
  bool wantsBandwidth = false;
  bool msproftxExplicitlyConfigured = false;
  for (const auto &tokenRaw : modeAndOptions) {
    auto token = trim(tokenRaw);
    if (token.empty()) {
      continue;
    }
    if (token.find("vendor_metrics=") == 0) {
      auto value = trim(token.substr(std::string("vendor_metrics=").size()));
      for (const auto &metricRaw : split(value, ",")) {
        auto metric = toLower(trim(metricRaw));
        if (metric == "aicore") {
          wantsAicore = true;
        } else if (metric == "bandwidth") {
          wantsBandwidth = true;
        }
      }
      continue;
    }

    auto eqPos = token.find('=');
    if (eqPos == std::string::npos) {
      continue;
    }
    auto key = toLower(trim(token.substr(0, eqPos)));
    auto value = trim(token.substr(eqPos + 1));
    if (key == "device_id") {
      explicitDeviceId = true;
      auto parsed = parseU64(value);
      if (!parsed || *parsed > std::numeric_limits<uint32_t>::max())
        throw std::invalid_argument("CANN device_id must be a nonnegative uint32 value");
      deviceId = static_cast<uint32_t>(*parsed);
    } else if (key == "output_path" || key == "aclprof_output_path") {
      outputPath = value;
    } else if (key == "aclprof_set_config_mem_freq_hz") {
      memFreqHz = value;
    } else if (key == "aclprof_aicore_metric_id") {
      if (auto parsed = parseU64(value); parsed.has_value()) {
        aclprofAicoreMetricId = parsed.value();
      }
    } else if (key == "aclprof_data_type_flags") {
      auto flags = parseAclProfFlags(value);
      if (flags != 0) {
        aclprofDataTypeConfig = flags;
      }
    } else if (key == "aclprof_msproftx_enabled" || key == "msproftx_enabled" ||
               key == "mstx_enabled") {
      msproftxEnabled = parseBool(value);
      msproftxExplicitlyConfigured = true;
    } else if (key == "mstx_domain" || key == "mstx_domain_name") {
      mstxDomainName = value;
    } else if (key == "aclprof_runtime_enabled" ||
               key == "cann_aclprof_runtime") {
      aclprofRuntimeEnabled = parseBool(value);
    } else if (key == "aclprof_auto_export" ||
               key == "cann_aclprof_auto_export" ||
               key == "msprof_auto_export") {
      aclprofAutoExportEnabled = parseBool(value);
    } else if (key == "runtime_host_timing_fallback" ||
               key == "runtime_base_host_fallback") {
      hostTimingFallbackEnabled = parseBool(value);
    }
  }

#if defined(__linux__)
  // Select the current runtime device only at session start. Applications that
  // change devices after start must supply device_id explicitly.
  if (!explicitDeviceId) {
    auto &runtime = aclRuntimeApi();
    int32_t currentDevice = -1;
    if (runtime.load() && runtime.getDevice &&
        runtime.getDevice(&currentDevice) == 0 && currentDevice >= 0)
      deviceId = static_cast<uint32_t>(currentDevice);
  }
#endif
  if (wantsAicore || wantsBandwidth) {
    aclprofDataTypeConfig |= kAclProfAicoreMetrics;
    if (!msproftxExplicitlyConfigured) {
      msproftxEnabled = true;
    }
  }
  if (msproftxEnabled) {
    aclprofDataTypeConfig |= kAclProfMsprofTx;
  }
  if (wantsBandwidth) {
    aclprofAicoreMetricId = kAclAicoreMemoryAccess;
  }

  if (!hostTimingFallbackEnabled) {
    auto envFlag = toLower(
        getEnvOrDefault("FLAGTREE_PROFILER_CANN_RUNTIME_HOST_FALLBACK", "0"));
    hostTimingFallbackEnabled = parseBool(envFlag);
  }

  if (!aclprofRuntimeEnabled) {
    aclprofRuntimeEnabled = parseBool(
        getEnvOrDefault("FLAGTREE_PROFILER_CANN_ACLPROF_RUNTIME", "0"));
  }
}

std::vector<std::string> CannProfiler::drainRuntimeDegradeReasons() {
  std::lock_guard<std::mutex> lock(mutex);
  auto reasons = runtimeDegradeReasons;
  runtimeDegradeReasons.clear();
  return reasons;
}

std::vector<RuntimeTraceEventKey> CannProfiler::drainRuntimeEvents() {
  std::lock_guard<std::mutex> lock(mutex);
  auto events = runtimeEvents;
  runtimeEvents.clear();
  return events;
}

VendorProfileArtifact
CannProfiler::importMsprofOutput(const SessionProfileMetadata &metadata,
                                 const VendorProfilePlan &plan) {
  auto runtimeReasons = CannProfiler::instance().drainRuntimeDegradeReasons();
  auto hostRuntimeEvents = CannProfiler::instance().drainRuntimeEvents();

  VendorProfileArtifact artifact;
  artifact.backend = metadata.backend;
  artifact.requestedMetrics = plan.requested.vendorMetrics;
  artifact.enabledMetrics = plan.enabledVendorMetrics;
  artifact.degradeReasons = std::move(runtimeReasons);

  auto csvFiles = collectCandidateCsvFiles(metadata);
  std::vector<RuntimeTraceEventKey> nativeRuntimeEvents;
  for (const auto &file : csvFiles) {
    artifact.rawInputs.push_back(file.string());
    auto lowerName = toLower(file.filename().string());
    if (lowerName.find("task_time") != std::string::npos) {
      parseTaskTimeCsv(file, nativeRuntimeEvents, artifact.degradeReasons);
    } else if (lowerName.find("op_summary") != std::string::npos) {
      parseOpSummaryCsv(file, plan.enabledVendorMetrics, artifact);
    } else if (lowerName.find("summary") != std::string::npos ||
               lowerName.find("op_statistic") != std::string::npos ||
               lowerName.find("api_statistic") != std::string::npos ||
               lowerName.find("step_trace") != std::string::npos ||
               lowerName.find("kernel_details") != std::string::npos ||
               lowerName.find("mstx") != std::string::npos ||
               lowerName.find("msproftx") != std::string::npos ||
               lowerName.find("msprof_tx") != std::string::npos ||
               lowerName.find("aicore") != std::string::npos ||
               lowerName.find("aicpu") != std::string::npos ||
               lowerName.find("hbm") != std::string::npos ||
               lowerName.find("llc") != std::string::npos ||
               lowerName.find("bandwidth") != std::string::npos ||
               lowerName.find("memory") != std::string::npos ||
               lowerName.find("mem") != std::string::npos) {
      parseStructuredSupplementalCsv(file,
                                     classifySupplementalSource(lowerName),
                                     plan.enabledVendorMetrics, artifact);
    }
  }

  std::set<std::filesystem::path> traceDirectories;
  for (const auto &csv : csvFiles)
    traceDirectories.insert(csv.parent_path());
  for (const auto &directory : traceDirectories) {
    std::error_code error;
    for (const auto &entry : std::filesystem::directory_iterator(directory, error)) {
      const auto name = entry.path().filename().string();
      if (entry.is_regular_file() && name.rfind("msprof_", 0) == 0 && name.size() > 7 && std::isdigit(static_cast<unsigned char>(name[7])) && entry.path().extension() == ".json") {
        artifact.rawInputs.push_back(entry.path().string());
        importNativeTrace(entry.path(), artifact);
      }
    }
  }

  if (metricEnabled(plan.enabledVendorMetrics, "bandwidth")) {
    bool hasBandwidth = false;
    for (const auto &association : artifact.associations) {
      if (association.metrics.find("bandwidth_gb_s") !=
          association.metrics.end()) {
        hasBandwidth = true;
        break;
      }
    }
    if (!hasBandwidth) {
      artifact.degradeReasons.push_back(
          "Bandwidth requested, but no CANN memory/bandwidth CSV columns were "
          "imported. Enable msprof options such as --aic-metrics=MemoryAccess, "
          "--task-memory=on, and --sys-hardware-mem=on.");
    }
  }

  size_t opSummaryAssociationCount = 0;
  for (const auto &association : artifact.associations) {
    if (association.source == "aclprof_op_summary") {
      opSummaryAssociationCount++;
    }
  }

  if (opSummaryAssociationCount == 0 && !csvFiles.empty() &&
      !plan.enabledVendorMetrics.empty()) {
    artifact.degradeReasons.push_back(
        "Vendor CSV files were found, but no usable op_summary associations "
        "were parsed.");
  }
  if (opSummaryAssociationCount == 0 && csvFiles.empty() &&
      !plan.enabledVendorMetrics.empty()) {
    artifact.degradeReasons.push_back("No vendor summary CSV files were found. "
                                      "Expected msprof exports such as "
                                      "summary/op_summary*.csv.");
    if (adapterOptionEnabled(
            plan.requested.adapterOptions,
            {"mstx_enabled", "msproftx_enabled", "aclprof_msproftx_enabled"})) {
      artifact.degradeReasons.push_back(
          "msprof CSV exports were not visible at profiler.finalize time. When "
          "using external `msprof --msproftx=on`, summaries may only be "
          "exported after the wrapped process exits.");
    }
  }

  if (opSummaryAssociationCount > 0) {
    if (!nativeRuntimeEvents.empty()) {
      correlateVendorToRuntimeEvents(artifact, nativeRuntimeEvents);
    } else if (!hostRuntimeEvents.empty()) {
      artifact.degradeReasons.push_back(
          "task_time runtime events unavailable; native source attribution requires "
          "explicit scope/correlation; host timestamps are never matched.");
      correlateVendorToRuntimeEvents(artifact, hostRuntimeEvents);
    } else {
      const std::vector<RuntimeTraceEventKey> emptyRuntimeEvents{};
      correlateVendorToRuntimeEvents(artifact, emptyRuntimeEvents);
    }
  } else if (!nativeRuntimeEvents.empty()) {
    addRuntimeBaseNativeAssociations(
        artifact, nativeRuntimeEvents, "aclprof_task_time", "aclprof_task_time",
        "runtime_base imported from aclprof task_time events.");
  } else if (!hostRuntimeEvents.empty()) {
    artifact.degradeReasons.push_back(
        "aclprof summary unavailable; runtime_base falls back to host-timing "
        "events (runtime_host_timing_fallback=true).");
    addRuntimeBaseFallbackAssociations(artifact, hostRuntimeEvents);
  } else if (plan.runtimeBaseEnabled) {
    artifact.degradeReasons.push_back(
        "No runtime_base events could be imported from aclprof exports.");
  }
  // Host launch scopes remain source-control observations even when device
  // tasks exist. They do not inherit device-task timing or engine semantics.
  if (!hostRuntimeEvents.empty() && opSummaryAssociationCount > 0)
    addRuntimeBaseFallbackAssociations(artifact, hostRuntimeEvents);
  addAssociationQualityReasons(artifact);

  return artifact;
}

namespace {

struct ReceiptCaptureState;
struct ReceiptContext {
  std::atomic<uint64_t> references{1};
  CannLaunchReceiptSinkV1 sink;
  std::weak_ptr<ReceiptCaptureState> capture;
  std::mutex mutex;
  CannLaunchWorkerRecordV1 worker;
  uint64_t publishCount{0};
  bool lateCallback{false};
  bool cancelled{false};
  uint32_t cancellationCode{0};
  std::string cancellationReason;
  bool malformed{false};
  bool drainedAfterClose{false};
};

void retainReceipt(void *opaque) noexcept {
  static_cast<ReceiptContext *>(opaque)->references.fetch_add(
      1, std::memory_order_relaxed);
}

void releaseReceipt(void *opaque) noexcept {
  auto *context = static_cast<ReceiptContext *>(opaque);
  if (context->references.fetch_sub(1, std::memory_order_acq_rel) == 1)
    delete context;
}

struct ReceiptCaptureState {
  uint64_t epoch{0};
  uint32_t selectedDevice{0};
  std::string outputPath;
  std::string sdkCapturePath;
  std::string sdkCaptureBindingStatus{"unsealed"};
  std::string sdkCaptureBindingEvidence;
  std::atomic<bool> active{true};
  std::mutex acceptance;
  std::vector<ReceiptContext *> contexts;
  ~ReceiptCaptureState() {
    for (auto *context : contexts)
      releaseReceipt(context);
  }
};

struct ReceiptRegistry {
  std::mutex mutex;
  uint64_t nextEpoch{1};
  uint64_t nextToken{1};
  std::shared_ptr<ReceiptCaptureState> current;
  std::vector<std::shared_ptr<ReceiptCaptureState>> captures;
};

ReceiptRegistry &receiptRegistry() {
  static ReceiptRegistry registry;
  return registry;
}

void cancelReceipt(void *opaque, uint32_t reasonCode) noexcept {
  auto *context = static_cast<ReceiptContext *>(opaque);
  std::lock_guard<std::mutex> lock(context->mutex);
  context->cancelled = true;
  context->cancellationCode = reasonCode;
}

void publishReceipt(void *opaque,
                    const CannLaunchWorkerRecordV1 *worker) noexcept {
  auto *context = static_cast<ReceiptContext *>(opaque);
  auto capture = context->capture.lock();
  std::unique_lock<std::mutex> acceptance;
  if (capture)
    acceptance = std::unique_lock<std::mutex>(capture->acceptance);
  std::lock_guard<std::mutex> lock(context->mutex);
  // A retained worker may outlive its capsule/SDK collector. It can record a
  // late audit flag, but must never overwrite a closed epoch's payload.
  if (!capture || !capture->active.load(std::memory_order_acquire)) {
    context->lateCallback = true;
    return;
  }
  ++context->publishCount;
  if (!worker || worker->abiVersion != kCannLaunchReceiptAbiVersion ||
      worker->structSize != sizeof(CannLaunchWorkerRecordV1)) {
    context->malformed = true;
    return;
  }
  if (context->cancelled || context->publishCount != 1)
    return;
  context->worker = *worker;
}

void closeReceiptCapture(const std::shared_ptr<ReceiptCaptureState> &capture,
                         const std::string &reason) {
  std::lock_guard<std::mutex> acceptance(capture->acceptance);
  capture->active.store(false, std::memory_order_release);
  for (auto *context : capture->contexts) {
    std::lock_guard<std::mutex> lock(context->mutex);
    if (!context->publishCount) {
      context->cancelled = true;
      context->cancellationReason = reason;
    }
  }
}

} // namespace

uint64_t beginCannLaunchReceiptCapture(uint32_t selectedDevice,
                                       const std::string &outputPath) {
  auto &registry = receiptRegistry();
  std::lock_guard<std::mutex> lock(registry.mutex);
  if (registry.current && registry.current->active.load())
    closeReceiptCapture(registry.current, "SDK collector replaced");
  registry.current.reset();
  registry.captures.erase(
      std::remove_if(registry.captures.begin(), registry.captures.end(),
                     [](const auto &capture) {
                       if (capture->active.load())
                         return false;
                       return std::all_of(
                           capture->contexts.begin(), capture->contexts.end(),
                           [](auto *context) {
                             return context->drainedAfterClose &&
                                    context->references.load() == 1;
                           });
                     }),
      registry.captures.end());
  if (registry.captures.size() >= 4096 || !registry.nextEpoch)
    return 0;
  auto capture = std::make_shared<ReceiptCaptureState>();
  capture->epoch = registry.nextEpoch++;
  capture->selectedDevice = selectedDevice;
  capture->outputPath = outputPath;
  registry.captures.push_back(capture);
  registry.current = capture;
  return capture->epoch;
}

void endCannLaunchReceiptCapture(uint64_t captureEpoch,
                                 const std::string &reason) {
  auto &registry = receiptRegistry();
  std::lock_guard<std::mutex> lock(registry.mutex);
  for (const auto &capture : registry.captures)
    if (capture->epoch == captureEpoch)
      closeReceiptCapture(capture, reason);
}

void sealCannLaunchReceiptCapture(uint64_t captureEpoch,
                                  const std::string &sdkCapturePath,
                                  const std::string &bindingStatus,
                                  const std::string &bindingEvidence) {
  auto &registry = receiptRegistry();
  std::lock_guard<std::mutex> lock(registry.mutex);
  for (const auto &capture : registry.captures) {
    if (capture->epoch != captureEpoch)
      continue;
    if (capture->active.load())
      return;
    if (capture->sdkCaptureBindingStatus != "unsealed")
      return;
    capture->sdkCapturePath = sdkCapturePath;
    capture->sdkCaptureBindingStatus = bindingStatus;
    capture->sdkCaptureBindingEvidence = bindingEvidence;
  }
}

CannLaunchReceiptSinkV1 *createCannLaunchReceiptSink(uint64_t scopeId,
                                                     uint64_t sessionId) {
  auto &registry = receiptRegistry();
  std::lock_guard<std::mutex> lock(registry.mutex);
  auto capture = registry.current;
  if (!capture || !capture->active.load() ||
      capture->contexts.size() >= (1u << 20) || !registry.nextToken)
    return nullptr;
  auto *context = new ReceiptContext();
  context->capture = capture;
  auto &sink = context->sink;
  sink.structSize = sizeof(CannLaunchReceiptSinkV1);
  sink.context = context;
  sink.retain = retainReceipt;
  sink.release = releaseReceipt;
  sink.publish = publishReceipt;
  sink.cancel = cancelReceipt;
  sink.tokenId = registry.nextToken++;
  sink.scopeId = scopeId;
  sink.sessionId = sessionId;
  sink.captureEpoch = capture->epoch;
  try {
    capture->contexts.push_back(context);
  } catch (...) {
    releaseReceipt(context);
    throw;
  }
  retainReceipt(context); // Transfer this additional owning ref to the capsule.
  return &sink;
}

bool cannLaunchReceiptCaptureActive() noexcept {
  auto &registry = receiptRegistry();
  std::lock_guard<std::mutex> lock(registry.mutex);
  return registry.current && registry.current->active.load();
}

void cancelCannLaunchReceiptSink(CannLaunchReceiptSinkV1 *sink,
                                 const std::string &reason) {
  if (!sink || sink->abiVersion != kCannLaunchReceiptAbiVersion ||
      sink->structSize != sizeof(CannLaunchReceiptSinkV1) || !sink->context)
    return;
  auto *context = static_cast<ReceiptContext *>(sink->context);
  std::lock_guard<std::mutex> lock(context->mutex);
  context->cancelled = true;
  context->cancellationReason = reason;
}

std::vector<CannLaunchReceipt> drainCannLaunchReceipts(uint64_t sessionId) {
  auto &registry = receiptRegistry();
  std::lock_guard<std::mutex> lock(registry.mutex);
  std::vector<CannLaunchReceipt> receipts;
  for (const auto &capture : registry.captures) {
    for (auto *context : capture->contexts) {
      if (context->sink.sessionId != sessionId)
        continue;
      std::lock_guard<std::mutex> contextLock(context->mutex);
      CannLaunchReceipt receipt;
      receipt.tokenId = context->sink.tokenId;
      receipt.scopeId = context->sink.scopeId;
      receipt.sessionId = context->sink.sessionId;
      receipt.captureEpoch = context->sink.captureEpoch;
      receipt.collectorOutputPath = capture->outputPath;
      receipt.sdkCapturePath = capture->sdkCapturePath;
      receipt.sdkCaptureBindingStatus = capture->sdkCaptureBindingStatus;
      receipt.sdkCaptureBindingEvidence = capture->sdkCaptureBindingEvidence;
      receipt.worker = context->worker;
      receipt.publishCount = context->publishCount;
      receipt.lateCallback = context->lateCallback;
      if (context->lateCallback) {
        receipt.status = "late_callback";
        receipt.reason = "worker callback arrived after SDK collector closed";
      } else if (context->cancelled) {
        receipt.status = "cancelled";
        receipt.reason = context->cancellationReason.empty()
                             ? "cancelled with code " +
                                   std::to_string(context->cancellationCode)
                             : context->cancellationReason;
      } else if (context->publishCount > 1) {
        receipt.status = "duplicate_publish";
        receipt.reason =
            "one source invocation published multiple worker receipts";
      } else if (context->malformed) {
        receipt.status = "malformed_record";
        receipt.reason = "worker receipt ABI version or size mismatch";
      } else if (!context->publishCount) {
        receipt.status = "pending";
        receipt.reason = "actual SDK launch worker has not published";
      } else if (receipt.worker.launchStatus != 0) {
        receipt.status = "launch_failed";
        receipt.reason = "original SDK launch returned failure";
      } else if (receipt.worker.deviceQueryStatus != 0 ||
                 receipt.worker.streamQueryStatus != 0 ||
                 receipt.worker.taskQueryStatus != 0 ||
                 receipt.worker.deviceId < 0 || receipt.worker.streamId < 0 ||
                 !receipt.worker.processId || !receipt.worker.threadId) {
        receipt.status = "query_failed";
        receipt.reason =
            "actual worker identity query failed or was not attempted";
      } else if (static_cast<uint32_t>(receipt.worker.deviceId) !=
                 capture->selectedDevice) {
        receipt.status = "device_mismatch";
        receipt.reason =
            "actual SDK launch device differs from selected collector device";
      } else {
        receipt.status = "collected";
      }
      receipts.push_back(std::move(receipt));
      if (!capture->active.load())
        context->drainedAfterClose = true;
    }
  }
  return receipts;
}

} // namespace proton
