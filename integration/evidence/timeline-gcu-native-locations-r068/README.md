# GCU automatic native location integration (R068, finite native-location acceptance)

The initial product commit 4fbc8e8 adds a DI-only native bridge, automatic
site/phase clock markers, a real SDK validation step, and cache identity v2.
A new Release tool and matching wheel were built and installed in an isolated
GCU Docker environment. Unchanged shared native inputs were checked/reused.
Two new math kernels passed ordinary/profile runs with input/tail/once checks;
the captures contain 22 and 20 internal events.

The first native object audit found no synthetic-file markers despite LLIR
retention. This is a confirmed functionality defect, preserved in the actual
receipts and three independent finite reviews of 4fbc8e8. The current fix adds
explicit lexical file scopes. CPU-only compilation of retained real LLIR now
shows all 13 site lines in the final ELF, including 48 positive-line rows and
10 compiler line-zero rows. It does not alter or qualify the old capture.
The fixed b4c5f81 wheel was subsequently built and installed normally. Both real
math captures pass again. Their actual ELF line tables cover all 13 sites each,
with 48/62 positive-site rows and 10/25 unknown line-zero rows. An actual rawline
excerpt also retains site10 columns 1/2/3/4 at separate native addresses. The
compiler reviewer closes the original missing-synthetic-file defect on this
finite device chain; broader phase/valueflow/all-path rights remain ungranted.
The maintained parameterized object checker was executed successfully on these
same captures without workload replay.

Five actual native CLI tests and SDK roundtrip checks pass. The initial
custom-form fixture failure remains; the bridge consumes the SDK's generic
IR. Formatting checks were refreshed after the ownership cleanup change.
No full source/raw, all-path region, hardware busy, shared epoch, ordinary
pipeline preservation, new SQL/UI or whole-goal qualification is granted here.
Only our source, bounded diagnostics and identities are tracked; linked SDK
IR, complete native dumps and actual raw bundles stay on the server.
