# Canonical raw time events

Public timeline captures now retain `captures/<invocation>.events.json` alongside
the original raw/decoded/async files. This is raw schema 1, validated by
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
document. The owned raw bytes and `*.input.json` identity/source snapshot are
persisted before decoding/canonicalization, so a later failure does not trigger
application replay or erase originals. Input journals explicitly say
`raw_persisted_pending_decode`; only the final capture describes decoded loss.

`test_timeline_events.py` supplies 15 CPU contract tests, including a nonwarp
role fixture; that fixture does not prove an extra chip port. The actual public
API/CLI test covers ordinary recurrence/GEMM, cached handles, two streams,
zero grid, export recovery and legacy count, plus a K=1021 recurrence that
overwrites the bounded ring and retains missing-endpoint evidence. These
development checks do not replace P01, physical clock/marker proof, independent
math or actual Perfetto SQL/UI acceptance.
