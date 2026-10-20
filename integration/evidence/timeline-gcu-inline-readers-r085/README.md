# GCU inline clock reader register inference

`inspect_inline_reader` recognizes a bounded low/high/low sequence, its unsigned
rollover comparison and fallback high/low rereads, then the physical identity
read. It derives registers from actual definitions rather than their names.
Fast and fallback states are merged for all registers; fallback-only values
cannot be used as constants on the fast path. Ambiguous words, changed outputs,
unsupported instructions or unproved intra-packet forwarding remain unverified.

`inspect_inline_record_fields` connects the inferred registers through a bounded
scalar guard prefix to the prior relative-record tail checker. It rejects
output clobbers, calls, cyclic guard targets and branches into the tail.

Normal and `-O` each passed 37 semantic fixtures in the existing GCU Docker.
Both unchanged loaded ELF/native views were checked instruction-by-instruction
against executable bytes. Reader inference passed 5/11 and 9/12 unique end
markers, leaving seven address relationships and two incomplete identity paths
unverified. The retained shared end inferred its three registers automatically,
kept them through 32 bridge instructions and reached the original 219-row tail.
The first source version had a fast/fallback merge defect found by independent
review; the final matching run contains its full semantic regression.

This is still source-loaded internal boundary-inspection code. Its actual tail
bounds are caller-selected; physical MMIO base, external entries, real selection,
ring allocation/sequence, incoming begin/site tuple and source/loop paths remain
unqualified. No normal-installed or whole-goal claim is made. SDK/native builds,
device execution, mathematics, Trace Processor and UI were not repeated.
Full retained native/LLVM objects and controller archives remain outside Git.
