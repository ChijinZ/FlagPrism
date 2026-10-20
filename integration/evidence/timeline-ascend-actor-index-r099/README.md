# Read-only Ascend actor structure indexing (R099)

Development data layer, not a source/loop qualification or complete feature.
The independent LLVM15 target parses the actual adapted actor input, verifies
its IR, then exposes typed SSA, endpoints, control flow and natural loops for
the finite automatic source-region rules still to be implemented.

All builds and execution used existing server Docker `chijin_v3.5.x`. No device
launch, SDK compilation, simulation, application/math replay, SQL or UI run.
The original producer plugin, driver inputs, binaries and captures are unchanged.

V1 terminal0/8.577182458 seconds indexed four actual actor inputs from runtime-K,
reduction and matrix cases. V2 adds LLVM verification before CFG analysis;
terminal0/8.927341815 seconds, four native CLI checks pass normally and under
Python -O, followed by the same four actual inputs. Their typed graph digests
are unchanged. This checks input identification and native structural parsing,
not record-tuple/source-body/loop semantics or final native issue placement.

V2 formatted source SHA:
`99907c53281dac61a074155d200d42eebe30629d5be178cf49cca47f57a30aec`.
V2 executable SHA:
`1a0d3ce219976778097a522cb229ff8eb9699bcdc4a95b408109371acbbfe29e`.
The exact formatted compiled source was recovered to the candidate. Four actual
inputs have 164/163/166/262 blocks and 1/0/1/1 natural loops; these counts are
inventory, not coverage or qualification.

The archive contains 67 indexed regular files, each size/SHA checked on recovery:
`6d612a34d84e8e1768c79e94c79139c94893c047b63848f06f65b947cd756881`.
Full private actor graphs and inputs remain in root/server artifacts. Git text
log copies normalize trailing whitespace only; exact original hashes remain
in structure-index-v2.json and the root archive.

The scope review agrees the minimum next path is actor typed index → selected
8×i64 tuple/body/loop rules → existing final-reader/raw automatic integration.
It does not review or certify this new C++ code. A separate limited code review
is pending. Packaging, public automatic/offline rule integration, current96
applicability, final native fact composition and whole-goal review remain open.
