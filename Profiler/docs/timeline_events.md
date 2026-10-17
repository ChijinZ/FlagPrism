# Canonical raw time events

Public timeline captures now retain `captures/<invocation>.events.json` alongside
the original raw/decoded/async files. NVIDIA continues to emit raw schema 1.
The common reader accepts versions 1 and 2, validated by
`timeline_events.validate_raw_batch`. NVIDIA's physical decoding and source/
mechanism mapping live in `timeline_events_nvidia`; the common validator has no
warp/SM hierarchy or vendor instruction parser.

| Table | Meaning |
| --- | --- |
| `sources` | Retained source snapshot/location navigation, explicitly not exact source cost attribution |
| `sites` | Binary-bound backend site, declared semantic and source references |
| `observers` | Recording role/local identity, actual program coordinates, loss state, timer width and unverified domain/epoch labels |
| `records` | Invocation-bound sequence, raw tick, site/observer and exact byte span in the SHA-bound original artifact |
| `events` | Actual paired interval, incomplete single endpoint, or producer point; occurrence stays separate from a proven loop iteration |
| `backend_record_map` | Explicit namespaced backend-record to canonical-record correspondence for mechanism facts |

The observer namespace binds capture, invocation and binary. Record IDs also
bind that observer and absolute sequence; event IDs bind their actual records.
Sites bind the binary and backend site identity. A wrong capture/binary,
dangling reference, overlapping raw span, duplicate boundary/duration, invented
endpoint/iteration, unknown required semantic or out-of-range tick fails closed
in normal and optimized Python. Source links can be M:N without duplicating a
physical interval. Descriptive backend attributes stay namespaced and cannot
override core fields.

For the NVIDIA ring, complete streams must have properly nested boundaries.
When history is overwritten, the adapter keeps real intervals wholly inside
the retained window and explicit orphan entries/exits. It never joins across
missing history or supplies a kernel-end timestamp. Occurrence is observed
entry/boundary order within that coverage, not inferred loop iteration or
physical buffer generation. Schema 1 conservatively rejects regressing raw
ticks; wrap/reset and clock qualification require separate explicit evidence,
not a reinterpretation of a decreasing counter as a duration.

`complete` means raw history/pair coverage, **not timing certification**.
`clock_status` and `boundary_status` remain `unverified`. No ns, exact source
latency, engine busy, cross-observer ordering or time arrow follows from these
records alone. Raw integer ticks, including values above 2^53, remain exact.
The future certified clock/export layer must derive a new view using proof,
integer scale/origin arithmetic and uncertainty, preserving this original.

Defaults bound validation to 65536 records, 32768 events and a 16 MiB canonical
document. In the NVIDIA public collector, owned raw bytes and `*.input.json` identity/source
snapshot are persisted before decoding/canonicalization, so a later failure does not trigger
application replay or erase originals. Input journals explicitly say
`raw_persisted_pending_decode`; only the final capture describes decoded loss.

`test_timeline_events.py` supplies 16 CPU contract tests, including a nonwarp
role fixture; that fixture does not prove an extra chip port. The actual public
API/CLI test covers ordinary recurrence/GEMM, cached handles, two streams,
zero grid, export recovery and legacy count, plus a K=1021 recurrence that
overwrites the bounded ring and retains missing-endpoint evidence. These
development checks do not replace P01, physical clock/marker proof, independent
math or actual Perfetto SQL/UI acceptance.

## Version 2: complete-pair producers and explicit loss accounting

The GCU adapter `timeline_events_enflame.canonicalize_enflame_capture` consumes
the existing `selected_dynamic_timeline_v1` native append protocol (Debugger
protocol 2, 64-byte records), and the distinct
`gcu_first_last_timeline_v2` compact layout used by the default GCU collector.
The decoder remains pure; certified time/export integration is still pending.
The caller supplies the owning capture namespace, the actual compiler metadata
and a retained capture document. It must retain the originals; the adapter does
not launch, replay, write a trace or claim ownership of device resources.

The adapter validates the raw SHA/header, actual launch/compiler association,
selection/grid, source/record plan, sample ordinals, commit tags and 46-bit
start/end/duration fields. Native invocation/session labels remain in provenance;
canonical identity also includes the owning capture namespace, because local
export labels such as `ir-capture-0`/`launch-1` can repeat across exports.

Each pair produces two canonical endpoint references to the actual 8-byte
start/end fields, not two fictitious physical records. Observer attributes retain
the physical 64-byte pair representation. Version-2 counts always count canonical
endpoint references; GCU physical-pair counts remain separately described.

| Observer field | Version-2 meaning |
| --- | --- |
| `record_order=endpoint_stream` | Sequence orders actual endpoint reads; regressing ticks fail as in v1 |
| `record_order=paired_endpoints` | Consecutive entry/exit references come from one atomic pair; append order is pair completion order, not a timestamp sort |
| `attempted_records` | Reported endpoint-reference attempts before sampling/capacity decisions |
| `committed_records` | Reported endpoint references actually committed, including any subsequently overwritten |
| `retained_records` | Endpoint references still in the retained artifact |
| `dropped_records` | Endpoint references rejected for capacity; distinct from overwriting |
| `filtered_records` | Endpoint references omitted by declared sampling; distinct from lost history |
| `overwritten_records` | Committed endpoint references removed by reuse of storage |

Without saturation, attempted = committed + dropped + filtered, and retained =
committed − overwritten. Saturated counters remain reported lower bounds and
can never yield a complete stream. Dropped/overwritten references also preclude
completeness. Sampling alone does not make the selected retained stream lossy.
Version 1 keeps its original `written_records` interpretation and validation.

For paired endpoints, an enclosing interval can start earlier than a previously
appended inner interval. The validator preserves that order and requires each
pair's own entry≤exit and nonregressing completion reads; it never sorts timestamps
to fabricate physical log order. Pair references cannot cross atomic records.
Occurrence is `complete_pair_order`/`retained_pair_order`, never an inferred source
iteration. A dropped complete pair creates loss metadata, not a synthesized
single endpoint or an invented duration. Unknown versions/orderings fail closed.

Eleven protocol tests cover nested pairs, strict endpoint streams, export-local
identity collisions, overwrite-versus-drop semantics, sampling, corrupt payloads
and type/source/header failures. These are synthetic contracts, not GPU coverage.
The installed reader separately consumed all 42 actual GCU intervals (84 exact
raw-field references) and all 26 original NVIDIA v1 batches unchanged, normal and
`-O`. Those historical results validate the shared raw consumer, not the new producer.
The subsequent [GCU owner evidence](../../integration/evidence/timeline-gcu-owner-r016/README.md)
records actual first/last publication, public default API/CLI and deferred owner
recovery separately; async/clock qualification, Perfetto and independent math
remain incomplete.

The compact producer has separate storage and publisher versions. Current
publisher 2 uses byte stride divided by the actual i32 pointer element size;
changing publisher semantics invalidates the compiler cache even without changing
the physical layout. Each selected ring retains its real program ID, actual
writer-arrival flag and per-ring commit/loss state. Host-initialized headers do
not prove that a selected program executed. Per-observer clock domains remain
unverified, never implicitly aligned by the SDK timer name.

## Counter-unit views are separate derivatives

`timeline_views.CounterUnitProof` binds capture/invocation/binary/raw/observer,
a positive rational tick period, an independent elapsed window, provider/evidence
identities and an optional provider implementation digest. The current NVIDIA
provider supplies that digest and revalidates actual sm_120 machine inputs. A
codec receiving a typed proof checks projection fidelity; it is not itself a
hardware evidence authority.

`derive_counter_ns_views` preserves raw/canonical ordering and integer ticks,
subtracts the origin before rational conversion and keeps unknown endpoint
error/precision explicit. Each observer has its own file-relative coordinate.
No cross-observer epoch, certified source cost or temporal flow is granted.
The standard exporter receives the independently validated proof object;
recomputing a forged view with its own changed period does not validate it.

Raw schemas are unchanged. Canonical reader upgrades and proof/exporter changes
produce separate immutable revisions, while the original `.events.json` remains
intact. See [runtime and offline re-export](timeline_runtime.md#offline-decoding-and-versioned-counter-traces)
for the implemented command, retention scope and limitations.
