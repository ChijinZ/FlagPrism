# Native launch header origins and lossless auxiliary reports (r046)

The late NVIDIA adapter now checks the actual entry parameter table, bank
symbol and PTX signature to bind the reserved scratch parameter. A bounded
native slice evaluates the full-width header address and hardware program /
thread identity stores against this invocation's admitted grid and block.
The header must have exactly one unscaled scratch-pointer root. The native
magic and source-bound shared-symbol materialization are checked separately.
The parameter-bank field references a symbol-table entry, whose actual section
must be this kernel's constant bank; no parameter index, bank address, source
path, operator, shape, register or instruction PC is fixed in the product.

The default hook retains invocation-specific `native_header_origins_file`,
independently of clock-unit qualification. Public retained-only export adds
`native_header_origins`. Header origin is a distinct fact: record ordinals,
timer/payload value flow, native boundaries, byte lifetimes and clocks must
still be joined before granting temporal flows. This delta does not turn
observer intervals into hardware-engine activity or source cost.

## Real execution and corruption checks

The first source probe checked actual native headers. The next probe exposed
a missing shared-symbol materialization step: the actual getter is followed by
ULEA. Its failed input and logs remain retained. The corrected probe checks the
actual source-bound operation and header value flow. The first formatting job
also rejected six single-line E701 conditions; its diagnostic text and a valid
full failure archive remain in preflight. These failed inputs were not installed.

Final source and test bytes passed cached full precommit fixed point and AST
preservation in the existing GCU Docker. An independent NVIDIA wheel then
passed actual default API numerical tests, runtime-K GEMM, receipt faults and
recovery, prior native wait/boundary/value/record/address contracts, the new
header origin contracts and public offline Trace Processor. Normal and
optimized Python each reject 29 bad header/object/metadata/layout cases. Both
real captures check 256 actual actor headers. The extra 48 asymmetric-grid
contexts per capture are CPU algebra fixtures, not recorded intermediate
programs or the independent six-new-mathematics qualification.

## Lossless budget improvement

Decoded JSON was already compact; removing whitespace could not fix its size.
New late captures explicitly declare `gzip-json-v1` for this auxiliary full
decoded report. The common bounded reader accepts old plain JSON as well.
New and old real captures pass complete field/value roundtrips in normal and
optimized Python; each cohort/mode rejects 21 malformed/unknown/oversized
cases. CRC errors, truncation, extra members and trailing bytes are rejected.
All raw records, actors, values and raw references remain present.

For these two new captures, 16,956,532 decoded JSON bytes become 2,351,517 gzip
bytes. Their complete default timeline bundle is 43,078,475 bytes, and the
retained offline bundle is 50,683,554 bytes, both below 64 MiB. The largest
single trace is 1,760,385 bytes. These are finite sample storage measurements,
not device performance or overhead certification.

All imports, installation, numerical/device tests, CPU fixtures, recovery and
actual Trace Processor ran in the existing NVIDIA Docker. The workstation only
edited, used Git, orchestrated and inspected/hashed retained bytes with the
standard library. Exact unchanged core r024 and standalone r036 builds were
reused with source/executable receipts. r045 originals remain hash-identical;
three fresh retained-only exporters replay no application and preserve 16
isolated trace bytes. No encoder/canonical/UI changed and no new browser run
is claimed. Exact versions, source/archive/wheel hashes and terminal identities
are in verification.json. Full three-backend pipelines, independent mathematics,
controlled cases and three fresh final reviewers remain outstanding. Paper and
Study data were untouched.
