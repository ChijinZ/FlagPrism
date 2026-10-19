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

### NVIDIA physical records and shared-view payloads

The physical record version is distinct from the common event schema. Readers
select it from the binary-bound compiler plan, never by guessing from bytes.

| Physical version | Header magic | Record bytes | Contents |
| --- | --- | --- | --- |
| 2 | `0x46505432` | 16 | site/phase, timer low/high, absolute sequence |
| 3 | `0x46505433` | 32 | v2 fields followed by payload kind, runtime shared-view byte origin, two zero reserved words |

Version 3 kind 0 has no association and all remaining words zero. Kind 1
describes a shared-memory view origin in address space 3; address zero is valid.
The decoder retains the payload's exact 16-byte span within its 32-byte record.
The NVIDIA adapter requires kind 1 on selected copy destinations/local-load
sources and rejects it on other operations, mismatched entry/exit addresses,
unknown kinds, nonzero reserved words and wrong-version headers.

`*.async.json` retains shared-view generations per invocation, program and
recording warp. One generation represents the submits to one observed origin
within one committed group; repeated commits to that origin create subsequent
generations. A local load is associated only with a recorded same-origin
generation covered by a preceding wait and with no intervening uncommitted
same-origin submit. Missing history produces no generation assignments.
These are committed **attempts**: masks can suppress byte movement. Equal
origins alone do not establish matching footprints, absence of aliasing,
completion visibility across actors or safe reuse. The data is a mechanism
input, not a source-boundary, clock or hardware-busy certificate, and does not
authorize a verified Perfetto flow.

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
`gcu_first_last_timeline_v2` legacy compact layout. Matching GCU300 installations
now also decode the late `gcu_execution_timeline_v3` publisher through
`timeline_events_enflame_native`, retaining the same common raw schema 2.
The decoder remains pure. Feature-1 compact captures additionally support the
separate empirical unit provider described in [runtime](timeline_runtime.md#gcu-per-physical-counter-time-views).
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

The execution-v3 physical record is 128 bytes. It retains native primitive
kind, two real clock fields, full SIPINFO at both endpoints, tag base/index,
buffer descriptor addresses/IR spaces and commit words. Its manifest versions
the buffer operands and address encoding separately from the common schema.
`gcu_ptr2int_i64_v1` carries full device pointers; older index-width values remain
explicitly unverified for buffer associations. `sdk_private_tag_index` is an
issuer-local tag identity. The decoder returns these native command arguments
separately from canonical timestamps; the GCU dependency mapper establishes
observed tag relations. Neither decoding nor source navigation grants engine
busy, consumer readiness or a shared epoch between programs.

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
identities and an optional provider implementation digest. An optional rational
rate uncertainty produces a separate elapsed conversion-scale error; it never
changes unknown hardware read precision into a known endpoint error. The current NVIDIA
provider supplies that digest and revalidates actual sm_120 machine inputs. A
codec receiving a typed proof checks projection fidelity; it is not itself a
hardware evidence authority.

`derive_counter_ns_views` preserves raw/canonical ordering and integer ticks,
subtracts the origin before rational conversion and keeps unknown endpoint
error/precision explicit. Each observer has its own file-relative coordinate.
No cross-observer epoch, certified source cost or temporal flow is granted.
The standard exporter receives the independently validated proof object;
recomputing a forged view with its own changed period does not validate it.

For feature-1 GCU compact records, `physical_identity` preserves full SIPINFO
and the exact 32-bit raw identity-word offsets. The canonical observer still
represents logical work-item 0; the physical ID does not replace logical identity
or prove another observer shares an epoch. The new provider validates those
raw words and a retained per-identity calibration window before granting units.

Raw schemas are unchanged. Canonical reader upgrades and proof/exporter changes
produce separate immutable revisions, while the original `.events.json` remains
intact. See [runtime and offline re-export](timeline_runtime.md#offline-decoding-and-versioned-counter-traces)
for the implemented command, retention scope and limitations.


## Ascend paired producer and public canonical adapter

`ascend_source_timeline_v1` is a real paired device producer connected to the
public CANN timeline collector and shared canonical schema 2. Its physical
layout is separate from both census and NVIDIA/GCU storage. The dedicated
transport uses real NPU stream completion and deferred readback with retained
allocation guards; the legacy debugger allocator rejects the new compact
protocol. The earlier explicitly synchronized development probe remains
historical producer evidence, not the default collection path.

The pure adapter in `timeline_events_ascend.py` validates the retained
source/carrier/actor manifests and exact layout before interpreting bytes.
It preserves both endpoint field offsets (start at pair+16, end at pair+24),
actual logical coordinates, separate physical block identity, source navigation
and unobserved actor slots. No device access or compiler-cache files are needed
to decode a saved complete input. The public offline re-export creates a new
canonical revision without modifying originals or replaying the application.
Clock-unit, final boundary, comparable epoch and async proofs remain absent;
these captures do not yet export a qualified Perfetto timeline.

The frontend reuses `source_census_site.v3` only to transport the actual selected
source identity and six program/grid coordinates through the SDK. The late pass
records non-empty lowered basic-block fragments up to the next carrier or block
terminator. A fragment is source-linked; it is not a certified source-operation
cost. Empty fragments are listed as skipped, not fabricated as durations.

Physical storage selects logical program zero and the actual last program, using
one compact slot for a one-program grid and two otherwise. Each slot reserves
three actor segments: AIC=0 and AIV=`GET.SUBBLOCKID+1`. Every segment consists of
one 64-byte header followed by `capacity` 64-byte pair records. Source-program
selection uses the real carrier coordinates; `GET.BLOCK.IDX` is retained as a
separate physical identity. This layout's exclusive-writer conditions still need
qualification for the broader ordinary-kernel matrix.

- Header u64 words: magic, committed pairs, attempted pairs, dropped pairs,
  logical program, actor, physical block, flags. Flags are arrival=1,
  count saturation=2, overflow=4. Counts saturate at `2^63-1`. With the optional
  manifest `runtime_participation.version=1`, bits 8–9 publish the device AIV
  subblock count (`GET.SUBBLOCKDIM`, one or two); AIC publishes one. All other
  flag bits remain invalid. The segment/record extents are unchanged. A missing
  feature declaration never authorizes these bits or reclassifies legacy empty
  slots. Consistent device cardinality may exclude AIV slot 2 only after its
  entire segment is verified zero; absent expected publishers remain unknown.
- Pair u64 words: descriptor (low32 site/high32 semantic), attempt sequence,
  start tick, end tick, logical program, actor, physical block, commit tag.
  The tag binds descriptor/sequence/program/actor/block; it is not a checksum of
  every payload byte. Actual completion and memory visibility remain necessary.
- Headers are zero-initialized; a zero segment does not prove that an actor
  executed. Each published pair retains its real two tick fields. Physical
  counts are pairs; the canonical adapter counts their two endpoint
  references explicitly. Neither append order nor site occurrence is a loop ID.

On 910B, the ordinary runtime-K recurrence probe retained six static fragment
sites and actual first/last-program records: K=3/7 yielded 8/12 pairs per observed
actor, with the loop site visited 3/7 times in one profiled binary. Math, input,
side effects, tails and allocation guards passed. LLVM15 construction/JIT,
AIC/AIV transformation, old census transformation and device census regression
have separate evidence. Raw values remain SYS_CNT ticks; source boundaries,
unit/precision, cross-observer epoch and async associations are unverified.
See the workspace `timeline_impl_record.md` T031–T034 and
[public raw evidence](../../integration/evidence/timeline-ascend-public-r020/README.md)
for exact versions, first failures and actual API/CLI/offline/recovery results.
