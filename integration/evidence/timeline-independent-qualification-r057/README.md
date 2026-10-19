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


## Finite observation-density controls

The maintained controlled runner now accepts a logical-site budget, one of its
existing variants, repeated ordinary references, and optional SDK stream events.
NVIDIA stream-event measurements are explicitly refused while performance work
is deferred. Default mathematical functions, inputs and selection remain the
same. Formatting reached a fixed point in GCU Docker and its Python AST was
unchanged; actual executed source SHA is
`298743dc44abde27a6326f02be3b0204c1a046c855a8eb6f24fe5a27006cca50`.

GCU C2 BK32 and BK64 each ran density 1 and default 8, with three ordinary and
three profiled calls per setting: twelve ordinary and twelve profile calls.
Every mathematical result, input, tail and once-only side-effect check passed.
All profile calls retain counter-ns and two dependency exports, actual writers
are complete, and full capture sizes meet the original budget. BK32 has 194
versus 196 positive internal intervals; BK64 has 104 versus 106. Mandatory native
control observations remain additional to the logical source-site budget.

For all four settings the ordered projection of 27 `memref_ext` primitives and
`gcu.matmul` operations in ordinary, recorder-input and actual rewritten SDK-input
IR is identical. Actual rewritten SHA is checked against the captured compiler
metadata. This is an SDK-input IR observation, not a guarantee of final physical
scheduling or engine busy intervals. Full generated IR and binaries stay on the
server, with paths/hashes in the small result summary.

`gcu-density-both-summary-v1.json` includes every actual ordinary/profile stream
span and host-request duration. SDK event spans include host submission and
compilation gaps; the first process call is kept separately from later calls.
These numbers cannot be used as device-kernel overhead ratios or ordinary
optimization benefits. No exclusive-noise or throughput certification is claimed.
The two controllers returned zero and their recorded parent/child identities
are inactive. These controls extend the original C2 evidence rather than adding
independent mathematical cases or replaying an unchanged qualification matrix.
