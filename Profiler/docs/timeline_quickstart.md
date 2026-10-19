# Profile an ordinary kernel's internal timeline

Use a matching integrated FlagTree/FlagPrism wheel in your existing development
environment. Keep your kernel and its ordinary launch script unchanged. The
compiler selects internal observation sites; you do not supply scopes, site IDs
or scratch arguments. This guide describes the implemented capture path, not
final three-backend qualification or an overhead guarantee.

## Install the matching integration

Follow the source and wheel instructions for your backend:

- [NVIDIA](../../integration/patches/nvidia/README.md): include the optimized-LLVM
  patch and package the late recorder, not just the count/native wheel. The
  exercised nanosecond provider is for SM120 and uses the documented matching
  `nvdisasm` installation. Other targets do not inherit that qualification.
- [Ascend](../../integration/patches/ascend/README.md): use the pinned source
  recipe and packaged late observer with its matching SDK/compiler resources.
- [Enflame](../../integration/patches/enflame/README.md): use the current native
  execution recorder and full physical-counter identity helper.

Replacing Python files alone does not install the native instrumentation.
Do not add source trees to `PYTHONPATH` to compensate for a mismatched wheel.

## Capture your existing launch script

Use the installed environment's Python. Select the compiler backend before
starting Python, and use the same logical device in the application and CLI.

| Device runtime | Compiler environment | CLI collector name | Example device |
| --- | --- | --- | --- |
| NVIDIA CUDA | leave `FLAGTREE_BACKEND` unset | `cupti` | `0` |
| Ascend NPU | `FLAGTREE_BACKEND=ascend` | `cann` | `4` |
| Enflame GCU | `FLAGTREE_BACKEND=enflame` | `enflame` | `0` |

The CLI collector name and compiler backend are different settings. In
particular, `--backend ascend` is not a valid CLI collector selection.

```bash
# NVIDIA example; replace the Python and application paths.
/path/to/runtime/bin/python -I -m flagtree.profiler.cli \
  --backend cupti --device 0 --detail timeline \
  -n /tmp/my-timeline /path/to/my_script.py

# Ascend example, after activating the matching SDK environment.
FLAGTREE_BACKEND=ascend /path/to/runtime/bin/python -I \
  -m flagtree.profiler.cli --backend cann --device 4 --detail timeline \
  -n /tmp/my-npu-timeline /path/to/my_script.py

# Enflame example, after activating the matching SDK environment.
FLAGTREE_BACKEND=enflame /path/to/runtime/bin/python -I \
  -m flagtree.profiler.cli --backend enflame --device 0 --detail timeline \
  -n /tmp/my-gcu-timeline /path/to/my_script.py
```

Alternatively, wrap the ordinary launch in a session:

```python
from flagtree import profiler

session = profiler.start('/tmp/my-timeline', detail='timeline')
try:
    run_my_ordinary_workload()
finally:
    profiler.finalize(session)
```

For the session API, select the vendor runtime device before starting the
session. Import `torch_npu` before importing Triton in an Ascend application.
The capture has bounded program, observer and record selection; it is not an
unbounded recording of every block in a long application.

## Open and interpret the result

Open `my-timeline/timeline/index.html` to find the standard `.pftrace` files,
then open a selected file in standard Perfetto. `report/index.html` also links
the captured timelines. The index and per-invocation JSON keep the status and
reason when a particular time view is unavailable.

Prefer an observed-dependency view when one is qualified. It contains actual
submission/wait relationships and their recorded generations. A shared-counter
view can compare the covered observers in its stated scope. An isolated
counter-ns view describes one observer; it does not establish overlap with a
separate file. Do not align separate traces by their displayed zero point.

Select a slice or checkpoint to inspect its source hint, program/observer,
raw timestamp references, occurrence and clock qualifications. A counter
bracket measures elapsed time between reads in instrumented execution. An
issue bracket is not engine busy time; a wait return is a completion-observed
checkpoint, not the exact hardware completion instant. Source navigation alone
does not establish an operation's exclusive cost.

Use the timeline to identify repeated regions, long brackets and recorded
waiting or dependency patterns, then change a legal kernel configuration and
compare the same observation semantics. Confirm any speedup separately using
ordinary execution. The [controlled examples](timeline_runtime.md#reading-the-controlled-examples)
show actual measurements and these interpretation limits.

## Missing or incomplete views

- Missing time-unit evidence leaves raw ticks available with a diagnostic;
  they are not relabelled as nanoseconds.
- Unknown observer slots and incomplete observed writers are different states.
  Inspect the retained completeness, loss and overflow fields before interpreting
  a trace as covering the requested execution.
- A full record buffer remains visibly incomplete. It is not repaired by
  dropping the loss flag or filling missing intervals from whole-kernel time.
- No dependency view can mean that this kernel has no modeled native async
  operations, or that its mechanism could not be qualified. Read the recorded
  reason; neither case supplies an inferred arrow.

The [runtime reference](timeline_runtime.md) gives backend-specific clock and
dependency semantics, lifecycle limits and retained evidence fields.

Retained captures can be re-exported without executing the application:

```bash
/path/to/runtime/bin/python -I -m flagtree.profiler.timeline_reexport \
  /tmp/my-timeline/timeline
```

Derived exports preserve the original attempt and report their own revision.
Large exact duplicate fields in timeline bundles use explicit metadata
references. For the restored logical JSON view, use the public reader:

```python
from flagtree.profiler.bundle_metadata import load_bundle_json

report = load_bundle_json('/tmp/my-timeline', 'report/report.json')
```
