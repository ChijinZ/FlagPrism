# R105 limited compiler review: lean Ascend default collection

Reviewed commit **`6e78f136214da74254211fa19b90a3f7b7353fa2`**. Scope is its three deleted collector lines and the accompanying runtime-documentation change. No old native/13-case/whole review was reopened; no product/import/tests/SDK/device/server/math/TP/UI was executed and no peer report read. Requested model/effort GPT-6.1-Sol/xhigh; actual resolved configuration is not exposed, so **unknown**.

## Conclusion

**No confirmed blocker, major or minor defect in this delta.** Removing automatic optional fragment-graph generation preserves the actual compiler/source-association/clock/dependency collection chain and avoids unnecessary default bundle growth. The new documentation correctly describes an explicit auxiliary analysis, without treating its absence or unknown results as loss of the real timeline. No new qualification is granted by the change.

## Source and documentation checks

`Profiler/python/flagtree_profiler/timeline_ascend.py` deletes only the import/call assigning `capture['source_fragment_paths'] = inspect_capture_fragments(...)` from normal collection. It still:

- decodes the actual returned raw through `attach_ascend_timeline_export` and persists the canonical event batch;
- retains source/launch/compiler metadata and actual machine-counter inspection;
- derives counter-ns views from their existing proofs and writes the same counter exports;
- attempts observed-dependency derivation/export under the existing qualification checks;
- persists the capture and its original invocation/owner status.

The delta changes no compiler pass, planner, marker, original/adapted actor, SDK/native input, timer, hidden ABI, raw publication or pairing. Its effect occurs after readback and canonical decode. It therefore does not need a new compile-selection policy/cache revision: the compiled observer program is unchanged. No remaining product consumer requires the deleted capture key; the offline path treats fragment analysis as an optional result.

`timeline_ascend_fragment_store.inspect_capture_fragments` remains callable explicitly. `timeline_ascend_offline` still calls only `load_fragment_paths`, whose implementation reads retained indexed inputs and recomputes facts without launching the indexer/SDK. Missing inputs are caught as an unavailable auxiliary result; the existing raw/ns/dependency paths are separate. Thus an old bundle with retained analysis can still use it, while ordinary offline export of a lean capture does not regenerate static graphs.

The revised `timeline_runtime.md` example correctly names the explicit API and its bundle-writing effect, recommends an owned copy of frozen evidence, and preserves unverified/opaque/ambiguous outcomes and the rule's limited endpoint-path semantics. It does not remove the original source navigation or claim SSA equivalence, full source cost, native schedule or engine activity. Keeping `partial`/boundary details is consistent with the document's existing observer-bracket explanation.

The reviewed file SHA256 values are:

| File | SHA256 |
| --- | --- |
| `timeline_ascend.py` | `a8719ce609e9bf519d3ad10ae8c3daf00934f5ce3bdd81c2838ccd7d53718154` |
| `Profiler/docs/timeline_runtime.md` | `7db1ec6c1aee50dac8590aedb70841daedeacfb4235ecadadd6803856cd929d1` |

## Actual installation/public-result scope read

Read local primary status/result copies `run-105/preflight/install-status-v1.txt` and `profile-q11-s0-c0-status-v2.txt`; did not run their commands.

- Normal `install-v1` is terminal **0 / 51.183600540 s**, source commit matching this review, **450** installed members checked by the installer. Wheel SHA256 is `433c500d8d4ba66ad4e6ca613cd5c94723ed3006548028d61f73a5f0f88e5543`. It accurately reports reuse of unchanged native/compiler inputs rather than a new native build.
- The new q11 shape/config 0/0 three-capture job is terminal **0 / 123.364283970 s**. Cold/warm1/warm2 public child return codes are all zero. All three records report actual mathematical/input/guard/host-once success, seven distinct positive source origins, the selected dot source44, and two actual observers each having four dot intervals/four positive values. They retain two actual MMA calls and the same compiler binary ID across the three captures.
- Each raw is **786,816 B**; bundles are **2,463,517 / 2,463,544 / 2,463,534 B**. Every row explicitly confirms default auxiliary graphs are absent while six counter-ns/standard Perfetto files remain. Engine-busy and source-exclusive-cost qualifications are false.

These are positive observations for the changed default behavior and one new q11 configuration. This report does not turn cold/warm repetition into a runtime-input-change proof, claim a new TP/UI examination, or pre-approve the in-progress complete q11/q12 profile set. It also does not require rerunning the unchanged native cases just to validate this three-line removal.

## Remaining scope

No new necessary verification gap was identified for this deletion/documentation delta. More detailed static type/order certificates remain optional analysis, not a prerequisite for retaining the source-linked raw/Perfetto timeline. Existing historical missing-observation cases and the broader final fact index are separate; this small change neither repairs them by declaration nor adds a new requirement to make every static check green.
