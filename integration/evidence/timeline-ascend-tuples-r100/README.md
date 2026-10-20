# Ascend actor tuple associations and source-coverage diagnosis (R100)

Product freeze `25c76ee978715ae6229af5e2f5e1b1fe16a14ccd` includes the native
text-limit fix and new internal tuple consumer. This is a development milestone,
not normal-install/public-source/loop/native qualification or a whole-goal vote.
All execution used existing Docker `chijin_v3.5.x`; no SDK build, model, device,
application/math replay, performance, SQL or UI run occurred.

The native index now charges target-triple text to its existing limit. A valid
4097-character triple is explicitly rejected, with empty stdout and the text
budget diagnostic. Five native CLI checks pass normally and under Python -O;
the four actual actor index bytes match the earlier R099 inputs. The compiler
review closes this one data-layer issue with exact build/source receipts.

The Python consumer associates complete eight-word typed volatile records with
actual marked SYS_CNT endpoints and their start PHI. It checks the declared
actor function/explicit trace pointer, contiguous offsets, descriptor and
commit fields. Selection, source-body containment, actor-role semantics, loops
and native scheduling remain explicitly false. It is not publicly wired yet.

Runtime review found two necessary fixes: computed descriptors could hide a
second tuple; nested shared expression DAGs could expand outside the repr sort
budget. Both are fixed and independently rechecked. V4 uses the exact formatted
helper `15eeb9e91036548d6c9324eabe4a4c8c1b6072b16c0d1141a9f7df8e5b857482`.
In each Python mode, 97 tuple associations over four actual actor inputs and
11 semantic negatives pass. These include computed/opaque duplicate descriptors,
interrupted uniqueness discovery and early rejection of a 24-level expression
DAG. V4 terminal0 in 3.570416604 seconds. V2/V3 outcomes remain historical,
covering only the earlier 8 negatives, not these fixes.

The final probe binds the native index cache to the original R099 result SHA
`db9199e99367b8c36b8b70ad15d618b1163d5d31ffbc85928e345db5618c5092`,
each graph SHA, actual actor input and compiled artifact's adapted LLVM.
No unsealed graph cache is used to grant the final association result.

Original, pre-instrumentation actor inputs were independently read from the
retained base64 bytes, SHA checked and indexed with the same tool. Four inputs
contain eight original carriers each, with 6/6/6/7 nonempty fragments. This is
new input evidence, not another device or SDK run. It exposed an actual coverage
issue: q05's matrix call precedes the next selected carrier and lies outside
the timed same-basic-block fragments. Its source dot operation43 was not among
the eight selected operations; source selection shared the memory-first census
policy. The scope review recommends first reserving a repeated aggregate for
timeline intent within the same max_sites, then checking real dot-to-MMA
lowering. Adding independent SDK-call intervals is only a fallback if needed.
No producer/planner change or new q05 success is claimed in this commit.

Indexed archive SHA256s (all member sizes/hashes checked on recovery):
- phase V1, 92 files: `3817585aa47fed70f310541e49d218737127881a9eb30edc89e937d6154b2866`;
- phase V2, 26 files: `7b3e948cc3b1b12fab35fcc985b79c5b1f12ee17b4e4aabdef76c7a282724f06`;
- phase V3, 26 files: `7cdb331349b3d4ec3c0bd2b930fb108c77d9ed26fc0e538209298ae0fdf06540`;
- original actor, 18 files: `ed79b874c5fff6334ca5dd533b6650e8e5447c35406dbb5ac0eea7494729ac05`.
Full original IR, private graphs and SDK inputs stay in root/server artifacts.
Git text copies normalize trailing whitespace only; indices identify originals.

Still required: meaningful source-body/loop observation and automatic/offline
integration, applicable native facts and original qualification coverage, and
final three-reviewer whole-goal closure. Existing unchanged math/clock/State/
Perfetto results are reused only for their original inputs and scope.
