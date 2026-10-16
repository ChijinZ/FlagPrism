// Actual CuptiProfiler/PCSampling/SessionManager with only SDK dispatch
// replaced.
#include "CuptiSdkTestShim.h"
#include "Profiler/Cupti/CuptiPCSampling.h"
#include "Profiler/Cupti/CuptiProfiler.h"
#include "Session/Session.h"
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
namespace {
void require(bool condition, const char *message) {
  if (!condition)
    throw std::runtime_error(message);
}
std::string failure(const std::function<void()> &operation) {
  try {
    operation();
  } catch (const std::runtime_error &e) {
    return e.what();
  }
  throw std::runtime_error("Expected failure was ignored");
}
} // namespace
int main(int argc, char **argv) {
  try {
    require(argc == 3, "Case and SDK shim directory required");
    std::string test = argv[1], path = argv[2];
    auto &profiler = proton::CuptiProfiler::instance();
    profiler.setLibPath(path);
    if (test == "probe-active" || test == "probe-shared") {
      proton::SessionManager manager;
      const bool pc = test == "probe-shared";
      auto id =
          manager.addSession("/tmp/chijin-r7-" + test, "cupti", path, "shadow",
                             "tree", pc ? "pcsampling:interval=1000" : "");
      manager.activateSession(id);
      const int enable = r7Calls("pc-enable"), disable = r7Calls("pc-disable");
      const int context = r7Calls("ctx-current"),
                subscribe = r7Calls("subscribe");
      if (pc) {
        profiler.validatePCSamplingSupport(path, "pcsampling:interval=1000");
        failure([&] {
          profiler.validatePCSamplingSupport(path, "pcsampling:interval=2000");
        });
        failure([&] {
          profiler.validatePCSamplingSupport(path + "/wrong",
                                             "pcsampling:interval=1000");
        });
      } else {
        failure([&] {
          profiler.validatePCSamplingSupport(path, "pcsampling:interval=1000");
        });
      }
      require(r7Calls("pc-enable") == enable &&
                  r7Calls("pc-disable") == disable &&
                  r7Calls("ctx-current") == context &&
                  r7Calls("subscribe") == subscribe,
              "Live collector preflight mutated SDK/context state");
      require(profiler.isPCSamplingEnabled() == pc,
              "Preflight changed the active collector selection");
      profiler.flush();
      manager.finalizeSession(id, "");
    } else if (test == "probe-idle" || test == "probe-enable-failure") {
      r7Context(1);
      if (test == "probe-enable-failure") {
        r7Fail("pc-enable", 1);
        failure(
            [&] { profiler.validatePCSamplingSupport(path, "pcsampling"); });
        require(r7Calls("pc-disable") == 0 &&
                    !proton::CuptiPCSampling::instance()
                         .hasPendingSupportProbeCleanup(),
                "Failed enable was treated as owned probe resources");
      } else {
        profiler.validatePCSamplingSupport(path, "pcsampling");
        require(r7Calls("pc-enable") == 1 && r7Calls("pc-disable") == 1,
                "Idle probe did not release its acquired SDK resource");
      }
      require(r7Calls("subscribe") == 0 && r7Calls("finalize") == 0,
              "Capability probe acquired/finalized a collector lifecycle");
    } else if (test == "probe-pending" || test == "probe-start" ||
               test == "probe-config") {
      r7Context(1);
      const bool unsupported = test == "probe-pending";
      if (unsupported)
        r7StallReasons(0);
      r7Fail("pc-disable", 2);
      auto first = failure(
          [&] { profiler.validatePCSamplingSupport(path, "pcsampling"); });
      require(
          proton::CuptiPCSampling::instance().hasPendingSupportProbeCleanup(),
          "Failed probe disable lost its context ownership");
      const int context = r7Calls("ctx-current");
      std::string second;
      if (test == "probe-start")
        second = failure([&] { profiler.start(); });
      else if (test == "probe-config")
        second = failure([&] { profiler.setLibPath(path + "/wrong"); });
      else
        second = failure([&] {
          profiler.validatePCSamplingSupport(path + "/wrong", "pcsampling");
        });
      require(second == first,
              "Pending cleanup replaced the original probe failure");
      require(r7Calls("pc-enable") == 1 && r7Calls("pc-disable") == 2 &&
                  r7Calls("ctx-current") == context &&
                  r7Calls("subscribe") == 0 && profiler.getLibPath() == path,
              "Failed cleanup issued fresh probe/subscription or changed path");
      if (unsupported) {
        r7StallReasons(1);
        profiler.validatePCSamplingSupport(path, "pcsampling");
        require(r7Calls("pc-enable") == 2 && r7Calls("pc-disable") == 4,
                "New probe started without first releasing old probe context");
      } else {
        profiler.start();
        profiler.stop();
        require(
            r7Calls("subscribe") == 1,
            "Collector did not recover after one successful pending cleanup");
      }
      require(
          !proton::CuptiPCSampling::instance().hasPendingSupportProbeCleanup(),
          "Successful cleanup did not release pending ownership");
    } else if (test == "external" || test == "external-partial") {
      r7ExternalSubscriber(test == "external-partial" ? 2 : 1);
      failure([&] { profiler.start(); });
      require(r7Calls("finalize") == 0 && r7Calls("unsubscribe") == 0,
              "Failed acquisition finalized another subscriber's SDK state");
      require(r7LiveResources() == 1, "Another subscriber was destroyed");
      if (test == "external-partial") {
        auto error = failure([&] { profiler.start(); });
        require(error.find("ownership") != std::string::npos,
                "Ambiguous handle must explicitly refuse restart");
        require(r7Calls("subscribe") == 1 && r7Calls("unsubscribe") == 0 &&
                    r7Calls("finalize") == 0,
                "Unknown ownership triggered a new subscription or teardown");
      }
      r7ExternalSubscriber(0);
    } else if (test == "disable" || test == "unsubscribe" ||
               test == "callback" || test == "repeat") {
      profiler.start();
      std::string operation = test == "disable"    ? "activity-disable"
                              : test == "callback" ? "callback-disable"
                                                   : "unsubscribe";
      r7Fail(operation.c_str(), test == "repeat" ? 2 : 1);
      if (test == "repeat")
        r7Fail("finalize", 2);
      const int callbacks = r7Calls("callback-enable");
      auto error = failure([&] { profiler.stop(); });
      require(!error.empty(), "Original error lost");
      require(r7Calls("callback-disable") == callbacks,
              "Early SDK error skipped callback cleanup");
      require(r7Calls("unsubscribe") == 1 && r7Calls("finalize") == 1,
              "Early SDK error skipped unsubscribe/finalize");
      if (test == "repeat") {
        require(r7LiveResources() > 0,
                "Failed finalization must retain real handle");
        failure([&] { profiler.start(); });
        require(r7Calls("subscribe") == 1,
                "Fresh subscription overwrote unresolved SDK resources");
      } else
        require(r7LiveResources() == 0,
                "Successful global finalize left owned resources");
      profiler.start();
      require(r7Calls("subscribe") == 2,
              "Cleanup recovery did not allow a fresh subscription");
      profiler.stop();
    } else if (test == "partial") {
      r7Fail("callback-enable", 1);
      r7Fail("unsubscribe", 1);
      r7Fail("finalize", 1);
      auto error = failure([&] { profiler.start(); });
      require(error.find("cuptiEnableCallback") != std::string::npos,
              "Partial cleanup replaced original start error");
      require(r7Calls("activity-disable") == 1 && r7Calls("unsubscribe") == 1 &&
                  r7Calls("finalize") == 1,
              "Partial-start cleanup skipped owned resource");
      require(r7LiveResources() > 0,
              "Failed partial-start handle was forgotten");
      profiler.start();
      require(r7Calls("subscribe") == 2,
              "Partial-start recovery subscribed before pending cleanup");
      profiler.stop();
    } else if (test == "pc-release") {
      auto &pc = proton::CuptiPCSampling::instance();
      auto context = reinterpret_cast<CUcontext>(0x789a);
      pc.initialize(context);
      pc.finalize(context);
      require(r7Calls("pc-disable") == 1,
              "PC context was not disabled before releasing host allocations");
    } else if (test == "pc-finalize") {
      auto &pc = proton::CuptiPCSampling::instance();
      auto context = reinterpret_cast<CUcontext>(0x789a);
      pc.initialize(context);
      r7Fail("pc-disable", 1);
      failure([&] { pc.finalize(context); });
      require(r7LiveResources() > 0,
              "Failed PC disable should still own SDK resources");
      pc.finalize(context);
      require(r7Calls("pc-disable") == 2,
              "Failed PC finalization forgot context before SDK release");
    } else {
      proton::SessionManager manager;
      auto add = [&](const std::string &name, const std::string &backend,
                     const std::string &mode, const std::string &library) {
        return manager.addSession("/tmp/chijin-r7-cupti-" + test + name,
                                  backend, library, "shadow", "tree", mode);
      };
      const bool pc = test == "pc-to-normal";
      auto a = add("a", pc ? "cupti_pcsampling" : "cupti", "", path);
      manager.activateSession(a);
      if (pc) {
        require(profiler.isPCSamplingEnabled(),
                "PC alias did not select PC sampling");
        manager.finalizeSession(a, "");
        a = add("c", "cupti", "", path);
        manager.activateSession(a);
        require(!profiler.isPCSamplingEnabled(),
                "Ordinary session inherited previous PC mode");
      } else if (test == "path-after-load") {
        manager.finalizeSession(a, "");
        auto error = failure(
            [&] { add("other", "cupti", "", path + "/different-library"); });
        require(error.find("already loaded") != std::string::npos,
                "Loaded SDK path change was not explicitly rejected");
        a = add("recovered", "cupti", "", path);
        manager.activateSession(a);
        require(r7Calls("subscribe") == 2,
                "Rejected path change poisoned the original SDK path");
      } else if (test == "shared") {
        auto b = add("b", "cupti", "", path);
        manager.activateSession(b);
        require(r7Calls("subscribe") == 1,
                "Same configuration restarted the shared SDK");
        manager.finalizeSession(b, "");
        require(r7Calls("finalize") == 0, "Finalizing shared B stopped live A");
      } else if (test == "mode" || test == "alias" || test == "path") {
        auto error = failure([&] {
          add("b", test == "alias" ? "cupti_pcsampling" : "cupti",
              test == "mode" ? "pcsampling:interval=1000" : "",
              test == "path" ? path + "/incompatible" : path);
        });
        require(error.find("different mode") != std::string::npos,
                "Wrong mode/path rejection");
        require(!profiler.isPCSamplingEnabled(),
                "Rejected B changed active A sampling selection");
        require(r7Calls("subscribe") == 1, "Rejected B restarted active SDK");
      } else
        throw std::runtime_error("Unknown case");
      manager.finalizeSession(a, "");
    }
    require(r7LiveResources() == 0, "Final SDK resources still live");
    require(r7Calls("unexpected-device-init") == 0,
            "CPU shim test initialized a device");
    std::cout << "PASS " << test << " subscribe=" << r7Calls("subscribe")
              << " finalize=" << r7Calls("finalize") << '\n';
    return 0;
  } catch (const std::exception &error) {
    std::cerr << "FAIL " << (argc > 1 ? argv[1] : "unknown") << ": "
              << error.what() << '\n';
    return 1;
  }
}
