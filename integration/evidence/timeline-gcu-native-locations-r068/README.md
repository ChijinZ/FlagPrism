# GCU automatic native location integration (R068, pending final integration acceptance)

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
The fixed wheel and device/object recheck remain pending at this checkpoint.

Five actual native CLI tests and SDK roundtrip checks pass. The initial
custom-form fixture failure remains; the bridge consumes the SDK's generic
IR. Formatting checks were refreshed after the ownership cleanup change.
No full source/raw, all-path region, hardware busy, shared epoch, ordinary
pipeline preservation, new SQL/UI or whole-goal qualification is granted here.
Only our source, bounded diagnostics and identities are tracked; linked SDK
IR, complete native dumps and actual raw bundles stay on the server.
