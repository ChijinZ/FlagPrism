# R103 finite runtime review: raw fragment observation summaries

Requested configuration: GPT-6.1-Sol / xhigh; resolved model/configuration unknown. Observed candidate HEAD: `b36388ad2fc5584c2f7e9ae8d2803ed65e41e741`. The new observation store/test changes were uncommitted when inspected. Store SHA: `348e71dbd3bfa3c3cc7cc1e2857c91249aa945812f0e427a92d3ef34902a7df8`; observation-test SHA: `d068e1a154a60eb075d6e5f700e58f4755e79538712e8650a2d5f4a70b954ce9`.

Scope: `_attach_observations` and the new raw read/decode/report identity/rule hashes in `load_fragment_paths`, plus their test. I read the relevant existing canonical decoder/site/observer construction as context. R102 tool/JSON/cleanup gates and the new loop structure rule were not reopened; no peer report was read. This was source/Git/text/JSON/SHA inspection only, with no local product import/execution, tests/checkers, server connection or SDK/device/mathematics/UI matrix.

## Confirmed finding

**M1 — Minor: summary boundary ticks can refer to different events than their accompanying IDs.**

- Location: `_attach_observations`, the updates of `first_tick`/`last_tick` and `first_event_id`/`last_event_id` plus corresponding record-ID fields.
- Trigger: for one site/observer, interval `[20,30]` appears before `[10,40]` in the paired-record stream. This has increasing completion ticks and is admitted by the canonical paired-endpoint model, which does not require monotonically increasing start ticks. An equivalent event-order permutation exposes the helper's same assumption.
- Evidence: `first_tick` becomes the minimum start, but `first_event_id` and `first_record_ids` remain the first encountered event's references. In this example the summary says first tick 10 while referencing the event whose start is 20. The last fields are likewise based on encounter order rather than the condition that updates the maximum. The current test verifies the min/max tick values but never validates the associated event/record references.
- Consequence: the aggregate count and tick sum remain correct, but a consumer following a reported boundary reference can reach another interval. This is a narrow provenance inconsistency, not a cross-observer clock merge or a whole-goal failure.
- Minimum correction/verification: update the corresponding event/record references when choosing each min/max boundary, with deterministic tie handling; alternatively name/document record-order references separately from time-boundary references. Add one CPU reordered/nested-interval summary case that checks both references and ticks. No device, loop/SSA or native proof is required.

No other confirmed blocker/major/minor was found in the requested dynamic join scope. The finding was sent to root before report completion.

## Reviewed behavior

The actor/site lookup uses `compiler_actors`' actual backend identities. Physical AIV slots with the same function/site must agree on that identity. Canonical backend-site identities must be unique. The report's source operation is checked against the canonical site's source operation, and every joined observer must identify the same actual actor function. There is no nearest-site or source-line-only join.

Observations are grouped by exact `(canonical_site_id, observer_id)`. The elapsed-tick sum exists only within each observer row, with that row's clock domain, epoch, timer width and program coordinates. Region-level aggregation sums counts, not ticks across observers. The unit stays `raw_counter_ticks`, and source iteration IDs remain unverified. Overlapping intervals are descriptive observed durations, not an exclusive source cost claim.

Completeness and dropped-record counts are copied from the canonical observer, and the occurrence basis remains the decoder's complete-pair/retained-prefix basis. Capture-level completeness is separate. Missing intervals produce `not_observed`, an empty observer list and zero counts, without constructing an interval or synthetic timestamp. The copied dropped-record count uses canonical endpoint-record units; interval counts remain pair counts.

The raw bytes are read through the retained-artifact path and checked against the original raw SHA before fresh decode. That decode already checks owner/compiler/launch/geometry and raw protocol identities. Report model v2 includes capture, invocation, binary and raw identities, so static graphs can be reused by binary without reusing another invocation's dynamic observations. The raw is added to the retain callback's input closure. The content-addressed report includes hashes of the current store, Ascend decoder, fragment/tuple helper and loop modules, in addition to the original indexed-input header/tool identity. No cached dynamic status is used as authority.

The static helper's unverified regions can carry a separate truthful raw-observation count without acquiring a stronger structural status. Native scheduling/value-equivalence and source-iteration authority are not raised by this new summary.

## Tests and evidence scope

The observation test compares each real-capture per-observer count, positive count, tick sum, min/max, domain/epoch, completeness and unit to fresh decoded intervals. It checks the model/invocation/raw identity, empty observations, changed source-site identity and changed raw rejection. Its interval/clock assertions are aligned with this consumer's limited claim. It does not yet check M1's event/record boundary references. Its empty-event mutation is a helper-level missing-observation test, not evidence of a newly captured empty raw stream.

Read `preflight/observations-status-v1.txt` and the source QA launcher/child scripts: the retained poll reports terminal 0 / 20.205629937 seconds, normal/`-O` each succeeding with 46 checked observer summaries, four indexed loop contexts, two positive repeated contexts, and wrong-site/changed-raw/not-observed checks. These scripts load candidate source modules over the R102 installed environment. They are source QA, not a new normal product installation. The loop-context numbers are recorded evidence scope here, not this seat's independent loop-rule approval.

The exact new normal-install terminal/complete receipt had not been supplied to this report. The necessary remaining work is M1's narrow reference correction/test and the already planned matching frozen-source distribution evidence. No new SDK/math/SQL/UI matrix or old R102 checks are requested. Optional expansion: none. This finite review does not grant whole/current-96, loop, SSA, native, clock-unit or source-exclusive qualification.

## M1 source correction addendum

The candidate source correction is sufficient by inspection. Observed working-tree store SHA is now `fd04a7536168cb4f76f3738c0cf696f473bbe67c7b6682ec6b840a6f059bff6a`; observation-test SHA is `c19eb192aa18d76c1dfb1c1acd2e489656694a76da2ee2a4fdd177f5c08556a9`. These are uncommitted source identities, not a newly installed/frozen product claim.

When an interval has a strictly smaller start, the implementation now updates `first_tick`, `first_event_id` and `first_record_ids` together. A strictly larger end similarly updates the three last-bound fields. Equal bounds keep the first encountered witness, matching stable Python min/max selection and avoiding the former unconditional last-reference overwrite. Counts, duration sums and observer grouping are unchanged.

The inspected fixture adds `[20,30]`, then `[10,40]`, then a tied `[10,40]` for the same site/observer and requires both boundary references to select the second event and its record IDs. This is a CPU aggregation fixture built on the real decoded context, not a claim that these manufactured IDs form a newly captured raw stream. The real-row comparison also now checks each first/last event ID and record-ID list against stable min/max witnesses from fresh decoded events. This directly covers the reported mismatch and tie behavior.

No additional defect or necessary test was found in this narrow correction. M1's code issue is corrected; its running observations-v4 execution receipt was not yet present at this inspection, so empirical/matching-source verification is still pending rather than asserted as passed. The previously planned matching freeze/install evidence remains separate. No new execution, hardware work, whole review or extra qualification gate is requested.

## M1 and matching raw-summary installation closure

M1 and the matching frozen-source distribution check are now closed. This addendum supersedes the pending execution/install statements above; it does not enlarge the finite review scope.

Verified product freeze: `092017f9ed23a56b508e9167a974dd349b959041`. Exact formatted store SHA is `1e97d1bf179da480ee79f43f0ff816448957d21a883ea433a8c61037c92bf524`; observation-test SHA is `dc50dbf3899a9969b779ac3fc124f99080a696945918ef966395484d6891c091`. The product still synchronizes tick/event/record references on strictly smaller/larger extrema and retains the first witness on ties. Earlier working-tree SHAs in this report identify the earlier inspected bytes, not this frozen installation.

Read `preflight/observations-receipts-v4/`: all 25 index entries match local size/SHA. Its controller is terminal 0 / 20.196588736 seconds. Both normal/optimized results report 46 actual observer summaries and successful nested-reference, not-observed, wrong-site and changed-raw checks. Its retained source-identity file and source copies match the exact frozen store and test bytes above. This supplies the previously pending source QA receipt, including M1's explicit nested/tie witness checks.

Read `preflight/install-receipts-v2/`: all 33 indexed files match local size/SHA. `runs/install-v2/terminal.json` is terminal 0 / 90.905437584 seconds; all 12 recorded installation/test steps return 0. The matching installer script SHA is `a8e693073b8459289d199e52f95730b92ae96b43deb627864aa64976d1a15ddc`. The result identifies product `092017f9...`, 450 installed wheel members verified, wheel SHA `4cf35fce8fc13b235c122dc55f82bf47c6b32d8e795657f1613a552720c9b363`, and unchanged packaged actor reader `d0e82b1fdc5fc322c322bc80c44a9e5e552afc5918174e2ba0f9504cc7a99d61`. Assembly provenance explicitly lists the matching store SHA.

Both installed normal/`-O` observation runs use retained raw SHA `8bc1d954e65efd2d3a2d03e53f6fe0f3d2ddfe6b11cc052b502a543b1572941c`, check all 46 observer summaries and the repaired boundary references, and retain not-observed/wrong-site/changed-raw rejection. Each installed store run reports 11/15 static checks and 15 observed regions, ten closure members (including raw), offline operation with tool execution forbidden, ignored cached status, tamper refusal and raw unchanged. The previously closed R102 faults remain passing in this matching run; they were not made into a new gate.

The result also records four loop contexts and two positively repeated contexts. These are contextual counts from the retained-capture test; this runtime addendum does not independently approve the loop rule or upgrade source iteration IDs. All these checks are CPU work on the existing real raw capture, with `device_executed=False`; no new application/mathematics/SDK/UI matrix was performed or inferred.

No confirmed issue or necessary verification gap remains for this bounded raw-observation summary change. Whole/current-96, loop/SSA/native, clock-unit/epoch alignment and source-exclusive qualification remain outside this closure. This reviewer executed no product or tests while reading these receipts.
