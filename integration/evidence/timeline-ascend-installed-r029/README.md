# Installed Ascend actor-object retention (r029)

Source implementation: `96bf6f2121dbd361b98c83cd631ee0f55ddda7e6`.
This checkpoint verifies the public collection path for the new actor-object
retention. **It does not pass full P01 or certify time units, source bounds,
shared epochs or async flows.** No paper or old Study files changed.

## Actual installed result

Inside existing `chijin_v3.5.x`, NPU4 (`Ascend910B4-1`), an independent wheel and
venv pass the real default API recurrence (runtime K=3/7, same binary, two
streams) and Softmax. Numerical outputs, input/state/tails and lack of per-launch
global synchronization pass the existing real-math harness. Three captures
contain 50 raw internal intervals / 100 endpoint references and valid guards.
They now embed their real actor objects, with matching actual compiler receipt
hashes and lengths. The recurrence object is 21,432 bytes; Softmax is 19,592.

- Python: `/tmp/chijin-timeline-r029/runs/install-v2/output/venv/bin/python`
- Wheel SHA: `8d5f4ae557d0d4f4b0bfd09d395b89c34b1924ffd2638eb4c0d211e55cb99b67`
- Byte checks: 400 installed wheel members, 88 component Python files, 663
  source inputs. The unchanged three Ascend plugin sources match their actual
  prior build; existing plugin/native artifacts are reused, **not rebuilt**.
- Normal / optimized Python: 102 tests each. The compiler fixture suite loads
  its explicit source namespace; installed package bytes match that source.
  Default device math and offline consumers use the independent installation.
- Public / isolated normal / optimized offline re-exports pass on two actual
  recurrence captures. Original source/cache/compiler scratch/device-output
  roots are denied to the audited consumers. Original 14 files are unchanged,
  and there is no application replay or NPU initialization. Python audit hooks
  are not an OS sandbox. These raw decoders do not yet consume actor objects as
  clock evidence; the objects' portable bytes are separately validated.

Actual default invocation, from the same Docker and with the fixed SDK selected:

```bash
TRITON_ASCEND_COMPILER=/tmp/chijin-r15-sdk-scalar-legality/install-fixed/bin/bishengir-compile \
  /tmp/chijin-timeline-r029/runs/install-v2/output/venv/bin/python -I \
  /tmp/chijin-timeline-r029/input-v2/component/tests/timeline/p01_ascend_default_timeline.py \
  --output NEW_EMPTY_DIRECTORY
```

Full argv, source/wheel/native hashes, math and offline results, original bundles,
controller/child identities and terminal receipts are in the immutable workspace
archive indexed by `verification.json`. Run `python audit.py` for its stdlib-only
byte audit. All product imports, compilation, math and tests ran in Docker.

## Failures retained

The initial launcher had a shell-quoting error and did not start a job; directory
absence was checked before retrying. Actual `install-v1` then failed before
wheel assembly because the reduced upload omitted `cmake/FlagPrism.cmake`.
The corrected input and new parent/venv/run use `install-v2`; the first failed
run remains in the archive. SDK/network errors are not hidden or reclassified as
unsupported kernels. Existing multiplexed and fresh SSH sessions intermittently
return `no available gateway`; successful operations use the same configured
credentials without printing them.

## Clock investigation changes the next action

Five CPU-only reference compilations use the actual c220-vector SDK command and
link inputs, with no device execution. Both the generic `MOV $0, SYS_CNT` getter
and explicit X0 compile to the same 8-byte code section. X1 and X31 vary the
destination bits; the constant-zero negative reference has a different first
word. The archive retains source, objects, stderr (including data-layout
warnings), commands and exit codes. This is **encoding feasibility**, not a
machine decoder or unit certificate: three registers do not qualify arbitrary
destinations or instruction boundaries.

The SDK's unavailable disassembler need not end investigation: installed
`llvm-dwarfdump-15` can inspect real debug addresses. Next, validate a complete
small getter-reference set and bind explicit clock debug markers to actual
site/phase PCs, then check target-specific unit evidence and use the shared
Perfetto path. Never grant clocks from a byte-pattern scan alone. A proposed
larger register probe did not start (gateway errors, then confirmed absent
input/run), so there is no result claimed for it and no active owner.

GCU header searches found no global-timer unit/correlation declaration. Generic
clock properties remain unsuitable. All backend time/async gates, independent
qualification, controlled cases and the final three extra code reviewers remain
open. Collected controller/worker/child identities (20) are inactive.
