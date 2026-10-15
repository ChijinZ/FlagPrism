// Exercise production Session/SessionManager with fault-injected profiler/data.
// SDK calls alone are replaced; manager and lifecycle methods are not modeled.
#include "Session/Session.h"
#include "Profiler/Profiler.h"
#include "gtest/gtest.h"
#include <stdexcept>
#include <functional>

namespace proton {
struct SessionLifecycleTestPeer {
  static size_t insert(SessionManager &manager, Profiler &profiler,
                       std::unique_ptr<Data> data) {
    const size_t id = manager.nextSessionId++;
    auto path = data->getPath();
    manager.sessions[id] = std::unique_ptr<Session>(new Session(
        id, path, &profiler, nullptr, std::move(data), "test", "test", "test", ""));
    manager.sessionPaths[path] = id;
    return id;
  }
  static size_t sessions(const SessionManager &manager) {
    return manager.sessions.size();
  }
  static bool clean(const SessionManager &manager) {
    return manager.sessions.empty() && manager.sessionPaths.empty() &&
           manager.activeSessions.empty() && manager.scopeInterfaceCounts.empty() &&
           manager.opInterfaceCounts.empty() &&
           manager.instrumentationInterfaceCounts.empty() &&
           manager.contextSourceCounts.empty();
  }
};
namespace {
struct Fault { int identity; };
class FaultProfiler : public Profiler, public OpInterface {
public:
  bool flushFault{false}, stopFault{false}, startFault{false};
  int starts{0}, stops{0}, flushes{0}, callbacks{0};
  void doStart() override {
    ++starts;
    if (startFault) { startFault = false; throw Fault{10}; }
  }
  void doFlush() override {
    ++flushes;
    if (flushFault) { flushFault = false; throw Fault{20}; }
  }
  void doStop() override {
    ++stops;
    if (stopFault) { stopFault = false; throw Fault{30}; }
  }
  void startOp(const Scope &) override { ++callbacks; }
  void stopOp(const Scope &) override {}
};
class FaultData : public Data {
public:
  FaultData(const std::string &path, bool dumpFault = false,
            int *dumpCount = nullptr) : Data(path), dumpFault(dumpFault), dumpCount(dumpCount) {}
  size_t addOp(size_t, const std::string &) override { return 0; }
  size_t addOp(size_t, const std::vector<Context> &) override { return 0; }
  void addMetric(size_t, std::shared_ptr<Metric>) override {}
  void addMetrics(size_t, const std::map<std::string, MetricValueType> &) override {}
  void enterScope(const Scope &) override {}
  void exitScope(const Scope &) override {}
  void clear() override {}
protected:
  void doDump(std::ostream &, OutputFormat) const override {
    if (dumpCount) ++*dumpCount;
    if (dumpFault) throw Fault{40};
  }
  OutputFormat getDefaultOutputFormat() const override { return OutputFormat::Hatchet; }
private:
  bool dumpFault;
  int *dumpCount;
};
size_t add(SessionManager &manager, FaultProfiler &profiler, bool badDump = false,
           int *dumps = nullptr) {
  static size_t n = 0;
  return SessionLifecycleTestPeer::insert(manager, profiler,
      std::make_unique<FaultData>("/tmp/chijin-session-lifecycle-" + std::to_string(n++), badDump, dumps));
}
void expectFault(const std::function<void()> &operation, int identity) {
  try { operation(); FAIL() << "expected original lifecycle fault"; }
  catch (const Fault &fault) { EXPECT_EQ(fault.identity, identity); }
}
TEST(SessionLifecycleTest, FlushFailureDetachesAndFinalizesWithoutDanglingCallbacks) {
  FaultProfiler profiler;
  SessionManager manager;
  auto id = add(manager, profiler);
  manager.activateSession(id);
  profiler.flushFault = true;
  expectFault([&] { manager.finalizeSession(id, ""); }, 20);
  EXPECT_TRUE(profiler.getDataSet().empty());
  EXPECT_TRUE(SessionLifecycleTestPeer::clean(manager));
  EXPECT_EQ(profiler.stops, 1);
  manager.enterOp(Scope(1, "after_failed_finalize"));
  EXPECT_EQ(profiler.callbacks, 0);
  auto next = add(manager, profiler);
  manager.activateSession(next);
  manager.finalizeSession(next, "");
  EXPECT_TRUE(SessionLifecycleTestPeer::clean(manager));
}
TEST(SessionLifecycleTest, FinalizeAllAttemptsOtherSessionsAndKeepsFirstFailure) {
  FaultProfiler first, second;
  SessionManager manager;
  int firstDumps = 0, secondDumps = 0;
  auto a = add(manager, first, true, &firstDumps);
  auto b = add(manager, second, false, &secondDumps);
  manager.activateSession(a); manager.activateSession(b);
  first.flushFault = true; first.stopFault = true;
  expectFault([&] { manager.finalizeAllSessions(""); }, 20);
  EXPECT_EQ(first.stops, 1); EXPECT_EQ(second.stops, 1);
  EXPECT_EQ(secondDumps, 1);
  EXPECT_TRUE(first.getDataSet().empty()); EXPECT_TRUE(second.getDataSet().empty());
  EXPECT_TRUE(SessionLifecycleTestPeer::clean(manager));
}
TEST(SessionLifecycleTest, ExportFailureStillFinalizesOtherSession) {
  FaultProfiler profiler;
  SessionManager manager;
  int dumps = 0;
  auto a = add(manager, profiler, true);
  auto b = add(manager, profiler, false, &dumps);
  manager.activateSession(a); manager.activateSession(b);
  expectFault([&] { manager.finalizeAllSessions(""); }, 40);
  EXPECT_EQ(dumps, 1); EXPECT_EQ(profiler.stops, 1);
  EXPECT_TRUE(SessionLifecycleTestPeer::clean(manager));
}
TEST(SessionLifecycleTest, SharedProfilerSurvivesFailedSessionFinalization) {
  FaultProfiler profiler;
  SessionManager manager;
  auto a = add(manager, profiler); auto b = add(manager, profiler);
  manager.activateSession(a); manager.activateSession(b);
  profiler.flushFault = true;
  expectFault([&] { manager.finalizeSession(a, ""); }, 20);
  EXPECT_EQ(profiler.getDataSet().size(), 1); EXPECT_EQ(profiler.stops, 0);
  manager.enterOp(Scope(2, "survivor")); EXPECT_EQ(profiler.callbacks, 1);
  manager.finalizeSession(b, "");
  EXPECT_TRUE(SessionLifecycleTestPeer::clean(manager)); EXPECT_EQ(profiler.stops, 1);
}
TEST(SessionLifecycleTest, ActivationFlushFailureRollsBackAndCanRetry) {
  FaultProfiler profiler;
  SessionManager manager;
  auto id = add(manager, profiler);
  profiler.flushFault = true;
  expectFault([&] { manager.activateSession(id); }, 20);
  EXPECT_TRUE(profiler.getDataSet().empty()); EXPECT_EQ(profiler.stops, 1);
  manager.activateSession(id); EXPECT_EQ(profiler.starts, 2);
  manager.finalizeSession(id, ""); EXPECT_TRUE(SessionLifecycleTestPeer::clean(manager));
}
TEST(SessionLifecycleTest, StopFailureRemovesSessionAndAllowsNextStart) {
  FaultProfiler profiler;
  SessionManager manager;
  auto id = add(manager, profiler);
  manager.activateSession(id); profiler.stopFault = true;
  expectFault([&] { manager.finalizeSession(id, ""); }, 30);
  EXPECT_TRUE(SessionLifecycleTestPeer::clean(manager));
  auto next = add(manager, profiler); manager.activateSession(next);
  EXPECT_EQ(profiler.starts, 2); manager.finalizeSession(next, "");
}
TEST(SessionLifecycleTest, DeactivateAllCleansEverySessionAfterFlushFailure) {
  FaultProfiler first, second;
  SessionManager manager;
  auto a = add(manager, first), b = add(manager, second);
  manager.activateSession(a); manager.activateSession(b);
  first.flushFault = true;
  expectFault([&] { manager.deactivateAllSessions(); }, 20);
  EXPECT_TRUE(first.getDataSet().empty()); EXPECT_TRUE(second.getDataSet().empty());
  manager.enterOp(Scope(3, "inactive"));
  EXPECT_EQ(first.callbacks, 0); EXPECT_EQ(second.callbacks, 0);
  manager.finalizeAllSessions(""); EXPECT_TRUE(SessionLifecycleTestPeer::clean(manager));
}
TEST(SessionLifecycleTest, FailedStartAllowsSameSessionRetry) {
  FaultProfiler profiler;
  SessionManager manager;
  auto id = add(manager, profiler); profiler.startFault = true;
  expectFault([&] { manager.activateSession(id); }, 10);
  EXPECT_TRUE(profiler.getDataSet().empty());
  manager.activateSession(id); EXPECT_EQ(profiler.starts, 2);
  manager.finalizeSession(id, ""); EXPECT_TRUE(SessionLifecycleTestPeer::clean(manager));
}
class ConfigurationProfiler : public FaultProfiler {
public:
  std::string committed;
  void doSetMode(const std::vector<std::string> &mode) override {
    if (mode.at(0) == "reject") throw Fault{50};
    committed = mode.at(0);
  }
};
TEST(SessionLifecycleTest, RejectedModePreservesLastCommittedConfiguration) {
  ConfigurationProfiler profiler;
  profiler.setMode({"initial"});
  expectFault([&] { profiler.setMode({"reject"}); }, 50);
  EXPECT_EQ(profiler.getMode(), std::vector<std::string>({"initial"}));
  EXPECT_EQ(profiler.committed, "initial");
  profiler.setMode({"next"});
  EXPECT_EQ(profiler.getMode(), std::vector<std::string>({"next"}));
}
} // namespace
} // namespace proton
