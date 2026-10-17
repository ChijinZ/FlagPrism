# r017: NVIDIA counter-unit traces and actual Trace Processor

This records T027, not full clock/source-boundary/async/P01 qualification.
Product Python baseline `691846f58ebd7b7ebda1f02c6a73fd1d5ba55370`
used the actual native build `6e7a7aa2b2501bce525d973975e9f4c33fee1c5a`.
The independent install checked 597 installed members; wheel SHA256
`f1219f3ffc6f12d121146e4016d8e0ceb584c4af1c842e68e385acb655b78b94`.

Four real ordinary recurrence/GEMM calls produced 32 isolated observer-relative
counter-ns traces, 1,344 physical endpoint references and 672 intervals. A separate
nested-pair fixture was explicitly synthetic. Generated protobuf and pinned real
Trace Processor checked exact ns endpoints, event/raw identities, qualification
annotations and no invented flows/importer errors. Nominal units do not establish
read precision, source-region boundaries, engine activity or shared epochs.

Original archive in the workspace:
`artifacts/timeline/run-017/preflight/counter-original-evidence.tgz`,
3,087,703 bytes, 476 members, SHA256
`7ddd09873962a4cacf666b8c382a14922a82e60e5120889102358b5ed32b2a55`.
[Byte audit](raw-counter-byte-audit.json) is reproducible with
[audit_originals.py](audit_originals.py), using only stdlib byte inspection.
It does not import the product or replay math on the workstation.

Browser setup/download/library failures and subsequent real UI inspection were
closed in T029. See [r018](../timeline-reexport-ui-r018/README.md) for actual
standard UI screenshots, six-trace coverage, immutable versioned publication,
new-process re-export and newer independently installed versions. Historical
T027 live/unfinished entries are not claims that those browser jobs remain live.
Full three-backend source/clock/async qualification remains unfinished.
