# R097 finite runtime review: original source-member navigation

Requested configuration: GPT-6.1-Sol / xhigh; resolved model/configuration unknown. Observed candidate HEAD: `26a8f3008fabd8e7ed4437481bd58b8a2a298cc1`. The consumer/test changes were uncommitted when read. Reviewed consumer SHA: `3ecb46a59ee1621fa7167856f419608cf508ac68a7ca535bf267271ad201517b`; reviewed test SHA: `f5404e27faaf6187a27add2f164d33fdfa00c9d3c0504e8f6070e5449ff4909e`.

This is a static review of `_member_navigation`, its `source_refs` integration, and `tests/timeline/test_enflame_source_members.py`. I also read the producer membership schema as context and the existing canonical/Perfetto consumers. I did not review the concurrent producer/source-rule changes as a whole, read peer conclusions, execute product/import/test/checkers, or contact a server/device. Only local source/Git/SHA reads and this report were performed.

## Confirmed findings

No confirmed blocker, major or minor was found in this finite consumer delta. This finding does not authorize whole-goal/current-96 source applicability, native boundaries or source-exclusive costs.

The inspected path has the intended limited behavior:

- `timeline_events_enflame_native.py:28` accepts only schema-1 indexed membership for new navigation. Missing membership and unverified status add no locations. Placeholder filenames and nonpositive lines create no member navigation. The existing source entry from `row['location']` is always retained, including an original unknown location; membership does not replace it with an invented aggregate origin.
- Each member location is encoded from the producer's actual filename/line/column, deduplicated within the member set, and associated with the current site. A new source ID includes binary identity, site identity, the member role and coordinate. A source operation ID is a descriptive attribute, not a global source key or a time/dependency authority.
- Source records remain `relation='compiler_origin_navigation'` with no asserted source-content SHA. `source_ids` at line 178 connect those records to the existing canonical site. The unchanged Perfetto path at `timeline_perfetto.py:254` reads those referenced locations directly. Neither path constructs another interval, divides a fused duration, changes raw record associations, or infers a source operation's exclusive time.
- The site attributes explicitly retain `enflame.source_cost_verified=False` and `enflame.engine_busy_verified=False`. Raw batch clock/boundary status and event construction are unchanged. Indexed membership alone does not affect the separate source/native qualification machinery.

## Bounds and compatibility

The per-member checks reject duplicate operation indices, boolean/noninteger IDs and coordinates, out-of-range IDs and negative coordinates, and oversized filenames. The caller allocates a single budget before traversing the manifest sites, so the 100,000-member and 4 MiB text-accounting limits are shared across one capture rather than reset per site. Per-site membership is limited to 8,192 rows, with manifest sites already limited to 512. The existing final canonical serializer/validator still enforces the actual 16 MiB document ceiling; the member estimate is not represented as an exact serialized-output measurement.

The producer schema context matches the consumer's integer ranges and optional missing file coordinates. No SDK child, owner/resource lifecycle, raw storage allocation or recorder ABI is introduced by this consumer change.

For a valid old input without `source_membership`, inspection shows the same primary source, source-ID list and attributes as before, in the same construction order. The added budget is internal state only. Existing record/event/command generation and final validation are unchanged. Thus I found no static old-format compatibility regression. I have not executed a byte-equality comparison and do not present one as evidence.

The new unit fixtures cover coordinate deduplication and IDs, input immutability, placeholder/unverified/missing membership, malformed identities/coordinates, duplicate member indices, and pre-exhausted aggregate budgets. They exercise the helper directly; they are not evidence that a normal installed capture/Perfetto pipeline already exercised the new references.

## Verification status and minimum remaining receipt

Normal installed execution and matching actual two-capture receipts had not been provided when this static report was written. That is the finite remaining verification item, not a confirmed code defect.

The intended receipt should bind the installed consumer bytes, show real indexed member coordinates appearing through canonical source references in Perfetto `source_locations`, and retain the matching raw/endpoint/event facts and false cost/busy rights. A retained old input or existing regression can establish the old no-membership behavior without replaying its application. No additional mathematics/SQL/UI matrix, SSA prover or native ISA work is requested by this review.

No optional expansion is requested. The review stops at navigation data flow and its compatibility/bounds; it does not certify that every producer membership is a complete source-exclusive body or elevate a fused observer duration to per-member cost.

## Frozen source and retained-raw phase evidence addendum

The consumer is now frozen at `726ab3176c74881c92d5098a8de490f49feb21a4` (Git verified). Its exact formatted SHA is `c4f72ce782e0e524551482958d9a2c093f81f25a26bdd8a6b149659f55642b9e`; the navigation test SHA is `6fa52ec0b55769393f93e812cc1ddfe94534a513b94ded4692f8fb7dac12cace`. The preformat SHAs at the top of this report remain the identities of the initially reviewed inputs, not the frozen byte identities. Reading those exact inputs from `origins-input-v5.tar` and comparing stdlib ASTs independently confirmed both are AST-identical to the frozen formatted files.

Read `preflight/phase-receipts-v1/runs/origins-v5/terminal.json`, its result/logs, and the exact run script in `origins-input-v5.tar` (script SHA `18bcef70cd7f27837c551482d7ad8bfb69140327a21e74d4284280d3b277d8f2`). The task is terminal 0 / 3.169638845 seconds. Normal and `-O` each run four navigation fixtures successfully. All 83 indexed phase files match their local size/SHA.

The phase run uses two **retained real captures/raws**, enriching an isolated copy of metadata with membership derived by the producer inspection. It checks the unchanged site ID/kind/operation/location before that join. This is CPU evidence on real raw inputs, not a new application/device capture or proof that the normal compile hook already published those fields.

- Object 0, body site 24: capture SHA `4c42d244eaa18c17c303e26d9f68502fad2d0e5b2fa08dca2545354718a2135d`, raw SHA `d4126e6ef643047702405cced5a70d4d8055c2c6aac8728517329ab62d780550`; 34 events / 68 records. The primary `loc(unknown)` remains first, followed by four real member coordinates; descriptive op IDs are 15/18.
- Object 4, body site 26: capture SHA `e9d6af023940197cff300d156baa6046b073fa6c4c0eba9567c321d938286370`, raw SHA `584a838a2d3bb17c1cd7266ea651171627846edb551b0d8fdcaa991c22bdb9de`; 36 events / 72 records. The unknown primary remains, with six real member coordinates and op IDs 17/20/24/25.

For both, the script compares every canonical field except the intentionally extended `sources`/`sites`, and all runtime commands, against the old decode. It also checks that raw/capture bytes are unchanged. Its separate no-membership decode equals the old installed decoder output. This closes the previously unexecuted retained-input compatibility/endpoint-data check at the source-loaded phase.

Matching normal installation and the planned actual protobuf `source_locations` check remain pending. No new confirmed consumer defect was found in this addendum; the original authority limits remain unchanged.

## Matching installation and protobuf closure addendum

The preceding pending matching/protobuf items are now closed for this finite consumer delta. Product bytes remain the same `726ab31` consumer SHA `c4f72ce782e0e524551482958d9a2c093f81f25a26bdd8a6b149659f55642b9e`; I rechecked that local identity. No new consumer defect was found.

Read `preflight/installed-receipts-v1/`: all 43 indexed files match local size/SHA. The **original `normal-install-v1` controller remains terminal 1**, at 56.556414549 seconds. Its assembly, wheel install, imports, binding/rule/index regressions, original-member/preservation tests and four navigation tests in normal/`-O` all return 0. Its final actual verifier returns 1. The original `actual.py` and traceback show that verifier looked for unescaped location strings inside a JSON-array protobuf annotation; this was a checker representation mistake, not a successful whole task and not evidence of lost product data.

The corrected script in `installed-actual-input-v2/run.py` (SHA `135c42f977f5753249c167bb4daf20605019b91b2f8bebc8c307755e87e08266`, read directly) reuses that same installed environment and compares the complete compact JSON array. `runs/installed-actual-v2/terminal.json` is terminal 0 / 4.021816430 seconds. Its result binds source `726ab3176c74881c92d5098a8de490f49feb21a4`, the installed module's exact consumer SHA, 503 wheel members checked byte-for-byte, and packaged tool SHA `374ab5f9fd07e2c5c7e8ec32f82365fa5c98e5736fd36648b3ee96b7263bf8d4`. This followup does not reinstall, rebuild or replay an application; the original controller failure is retained explicitly in its result.

The installed decoder again reads the two retained real raws described above. Plain no-membership decode equals the explicitly loaded R096 installed decoder. Enriched decode preserves commands and every canonical field other than the intended sources/sites extension, retains unknown primary plus the actual member coordinates, and retains 34/36 intervals and 68/72 endpoints. The script checks original capture/raw bytes unchanged.

For protobuf generation, the script obtains existing capture-bound counter proofs using `load_counter_unit_proofs`, then calls the public counter-view/trace encoder; it does not invent a unit proof. Four retained observer `.pftrace` files are present, with sizes 37,393 / 37,476 / 39,711 / 39,792 bytes. Reading their actual bytes independently confirms recorded SHA values, the `source_locations` key, and the complete expected compact JSON array including unknown primary and member locations in each file (three array occurrences per file). This closes the requested navigation annotation connection through the real encoder. It is not a Trace Processor or UI validation claim.

The initial source-loaded check and this normally installed retained-raw/protobuf followup support the finite consumer behavior. No additional necessary test is requested. Current-96/whole applicability, native source boundaries and source-exclusive authority remain outside this report; no new mathematics/device/SQL/UI matrix was executed by this reviewer or inferred from these receipts.
