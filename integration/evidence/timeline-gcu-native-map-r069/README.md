# GCU automatic final-ELF debug positions (R069)

Implementation: `68faaaf953ff13fd3ef64e7a0351390e8c61a476`; canonical base `9232936`.
Normal make_fatbin automatically retains the unique target ELF's sectioned DWARF
marker rows, original fatbin/ELF identities, tool identity and missing phases.
This is a compiler debug-location service; all source-region, reader-valueflow
and hardware-busy qualification flags remain false.

Normal four-TU build and wheel install passed; 495 installed members matched.
Ten native CLI tests and 15 bridge tests in normal Python and -O passed.
Two ordinary/two profiled mathematical calls through the public API passed
reference, input, tail and once-only checks. Their actual executable metadata
contains 48/62 native points, 13 manifest sites each. No per-operator hook.

Missing independent end-phase rows are retained explicitly. Actual final LLVM
has shared end-recording blocks: bb16 selects three paths' site/begin values;
bb53 selects two. A common timer/identity remains but has only one debug
location. This explains these missing independent rows; it does not establish
complete native alias/valueflow mapping. Raw excerpts are in shared-end-blocks.

The eight new original exports passed the unchanged pinned verifiers using real
Trace Processor: four counter traces (42 intervals), four dependency traces
(16 endpoints, eight flows). Original raw words, time conversions, protobuf,
SQL identity/endpoints/flows and full importer stats are checked. No positive
error/data_loss. No application replay or device execution for this check.
Initial orchestration failures are retained: v1 wrong controller path; v2
wrapper output parent missing; v3 attempted counter verifier on dependency view;
v4 omitted raw files during transfer. V5 corrected input preparation and passed;
these are not device or product failures. No new UI run; unchanged exporter/UI
coverage is reused from R059, without claiming the new bytes were shown there.

Final server formatting changed only Python formatting of the two summary
fields. The returned file has SHA d47fcb4838c15013e1cc9a61b5ba8340325505358332b6d31e2c6297c3927dad;
its AST equals the actual device-run script SHA ab9441068b40661a977f64bc34b7606cc5f21ebd68b9040b8dad8c4427b4aaf0.
The format receipt intentionally records changed bytes. No math replay needed.

Three original independent final reviewers support this finite delta; reports
are retained. This is not whole-goal signoff. Original finite source/loop native
boundary and ordinary/sparse/default dependency-preservation requirements remain
open; arbitrary-ISA proof and identical issue order are not added requirements.
No paper/Study changes. NVIDIA exclusive performance/overhead remains deferred.
