# Independent qualification checkpoint, R057

This checkpoint is not final acceptance. Runtime source is `4bc9286`.

NVIDIA's twelve previously saturated supplemental q08 calls now pass the
original numerical, host-once, retained-input, raw, nanosecond, actual-writer,
and size-budget gates. Sampled allocation uses four actors and 4096 records
per actor: maximum raw 1,048,960 bytes, trace 4,678,164 bytes, complete capture
51,868,047 bytes. All twelve controller exits are zero and all 25 owned
identities are inactive. The original failures remain retained. No ordinary,
q07, or original-six calls were replayed in this delta. There are no modeled
async copies in these calls; their zero dependency-export count does not prove
a different asynchronous mechanism.

All three backend providers have actual retained-capture offline regressions.
NVIDIA's eight, GCU's two, and Ascend's two counter traces retain their exact
original bytes under normal, optimized, and denied-original-environment fresh
processes. These storage/provider changes do not require repeating unchanged
UI sessions. The original application is never replayed by offline export.

Ascend's forty compiled immediate reference tuples bind the marked primitives,
but some final SDK images contain additional unobserved synchronization
instructions. In the original six-kernel set, 24 captures have dependency
exports and 48 retain an explicit unavailable reason. Their existing numerical,
internal counter-time, observed-writer and budget results remain separate.
No unknown instruction is silently accepted, and unavailable is not renamed
"no async". The added event-extension rejection passes both normal and optimized
actual-image fault tests on a closed q01 image. The q03 positive test's initial
failure is retained rather than claimed fixed. Additional CPU SDK references
identify its unobserved SET/WAIT(1,0,7) words; they do not authorize dynamic
edges. Other unknown register-control encodings remain unqualified.

Per-capture numerical/time gates and each backend's dedicated real asynchronous
reuse gate are distinct requirements in `timeline_testing.md` sections 4 and 5.
The original contract does not require an arrow for every ordinary kernel.
Dedicated asynchronous cases must still pass their full gates. Ascend's last
two frozen supplemental kernels and the three fresh final code reviews remain
pending at this checkpoint. Performance/overhead certification on NVIDIA is
still deferred by user instruction. No paper or Study files were modified.

`results.json` indexes small immutable receipts. Private SDK objects and full
captures remain in the referenced existing server Docker filesystems.
