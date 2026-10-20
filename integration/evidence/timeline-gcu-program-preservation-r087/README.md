# GCU program preservation and observer memory isolation

The normally packaged recorder now verifies its actual transformation. Original
operation identities are captured before rewriting. Erasing added operations
from a clone must restore the complete original generic IR core, including SSA,
control flow, types and operation properties. Added observer effects are limited
to fresh allocations and publication to the unused hidden trace argument.
Reserved getter calls must resolve to exact external non-variadic declarations.
The manifest records this GCU-IR check; it does not certify allocation bounds,
SDK lowering, final native timing boundaries or the whole goal.

The offline checker reproduces the checked transformation and compares the
complete typed IR core with the retained actual output. Navigation locations
may differ; byte equality is reported separately. Historical input/output SHA,
math/host-once and loaded-object bindings remain explicit. Of 109 registered
historical profiling calls, 97 passed this transform check; 12 older q05 calls
remain unverified because their recorder output core differs. There are 37
distinct transform inputs. These counts do not grant physical State-writer
qualification. The independent delivery note describes the remaining link to
actual State transfer/guard/descriptor checks, including original address uses.

A separate CPU comparison found all 37 current installed-recorder outputs
byte-identical to the new recorder for the same retained inputs. It does not
upgrade the 12 historical failures. No device, mathematics, SDK, Trace Processor
or UI workload was replayed for this change.

The source version is 3b65197ad4ef03fdaeb2bc222e365bf63d0055b0. The changed
standalone native recorder was genuinely rebuilt and normally installed in a
new wheel/environment. All 500 installed package members matched wheel bytes;
normal and optimized Python each passed 10 actual native CLI tests. The native
probe, normal native build and installed tool are byte-identical. Existing
compiler/runtime libraries and system SDK were reused after native-input checks.

Tests cover real recorder address payloads, exact reproduction, altered original
State values, added reads/writes, stored bits used as an address offset, unknown
helpers, location-only changes, hidden-index overflow and reserved getter
shadowing/signature rejection. AFTER mutations are rejected by reproduction;
they are not represented as direct execution of every internal isolation guard.
Independent compiler review records the confirmed fixes and these limits.

Full private IR and all old failed receipts stay in root/server artifacts. The
555-file receipt archive was extracted with regular-member/path checks and its
SHA index verified. This directory keeps code, finite reports, compact summaries
and a compressed per-call transform index. Final three-reviewer whole-goal
acceptance remains open.
