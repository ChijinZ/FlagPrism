# Automatic internal profiling

This development branch adds automatic fine-grained profiling for kernels
compiled through its matching FlagTree integration. Operator source does not
need scopes, observer IDs, hidden arguments, or per-kernel instrumentation edits.
The compiler selects bounded internal locations from the actual specialization.

## Install the matching compiler and component

Use a wheel built from this component and the pinned backend integration in
[`integration/patches`](../../integration/patches/README.md). A stock compiler
wheel without these callbacks/passes is insufficient. Existing compatible Torch
and vendor SDK installations remain prerequisites. The automatic NVIDIA pass
and Ascend late plugin must be built; copying Python over an older installation
does not add these capabilities.

For NVIDIA, layer `nvidia/automatic-scopes.patch` on the pinned integration.
For Ascend, layer `ascend/automatic-source-origins.patch` on the complete pinned
integration, and build/package the LLVM15 observer. The observer runs out of
process with upstream opt; it must not be loaded into the vendor LLVM fork.
For Enflame, use its pinned combined compiler integration and this component's
automatic planner. Backend wheel recipes and independent installation evidence
are being qualified in this branch; development smoke tests alone are not a
claim that every supported compiler structure has passed product acceptance.

Select the installed compiler backend explicitly in multi-backend environments:

```bash
export FLAGTREE_BACKEND=enflame   # or ascend; omit for the NVIDIA build
```

This is particularly important with torch_gcu environments that redirect the
CUDA device API: otherwise both Enflame and CUDA drivers may appear active.
Select devices with the vendor runtime's visibility controls before Python
starts, or set the current device before starting a session in the API path.
The script must use logical device indices consistent with that visibility.
The CLI also accepts `--device N` before the script name to select the runtime
logical device before starting the collector. The application must use that
same logical device; for example, profiling an application that chooses NPU4
requires `--device 4`. Backend selection and device selection are separate.
Do not set line-info, plugin-path, capture-directory or publisher environment
variables for normal automatic profiling; those are advanced overrides.

## Run your own script

With the installed environment active and its SDK environment initialized:

```bash
python -m flagtree.profiler.cli --detail auto -n profile-run my_kernel_script.py
```

Normal arguments after the script name belong to the script. Use a fresh output
directory for each capture. The script executes once; the basic command does
not request an application replay or external counter collection.

Alternatively, initialize the device in your ordinary script and wrap the
launches at the outer level:

```python
import flagtree.profiler as profiler

session = profiler.start("profile-run", detail="auto")
try:
    # Launch your ordinary @triton.jit kernels here.
    run_my_kernels()
finally:
    profiler.finalize(session)
```

`detail="auto"` supplies the backend-specific observation request and hook.
Do not combine it with an explicit observation request or mode. Explicit scopes
and typed requests remain advanced interfaces. Automatic selection defaults to
eight internal sites and bounded per-instance record capacity. The actual
backend plan, selected locations, unselected inventory when available, and
protocol-specific loss evidence are retained in the bundle. A bounded selection
is not a claim that every operation was observed.

## Read the result

Open `profile-run/report/index.html` and follow **Source-linked internal dynamic
records**. The view can filter by source path, operation, invocation or actor;
each row identifies its source location, compiler operation, binary, call,
program, actor, site, semantic class and retained occurrence. The execution and
clock-group view links the related native activity when uniquely associated.

Machine-readable counterparts are:

- `ai/fine_grained.json`: normalized dynamic records and source locations.
- `ai/observation_plan.json`: automatic plans and exact capture evidence.
- `ai/observations.json`: original typed observations and backend capture/loss
  data. Raw artifacts remain under `raw/`.
- `ai/execution.json`: actual compiler execution mapping and its evidence limits.
- `ai/export_timing.json`: host finalization/export time. A complete API receipt
  measures the entire finalize call through cleanup; CLI receipts combine
  collector finalization and subsequent bundle materialization. The final timing
  receipt write is excluded. A standalone export of legacy raw files may have
  only materialization time and explicitly reports incomplete total timing.
  These values measure host engineering cost, not GPU/kernel latency.

Read the semantic and clock columns together. NVIDIA records instrumented
source-control intervals in SM-local counter ticks. Enflame records source
control using the SDK timer; its frequency is not assumed. Ascend can record
source-operation and loop checkpoints as well as existing issue/wait classes.
A checkpoint is evidence of an occurrence, not operation duration. No view
turns an issue interval into engine occupancy or an instrumented interval into
an uninstrumented performance measurement. `None` means unavailable; unverified
clock frames are not overlaid on native timelines.

`occurrence` counts retained visits of a site for its invocation/program/actor;
it is not automatically a loop iteration number. Loop conditions may execute
once more than their bodies. Sampling, unselected sites and dropped records
have different meanings. Use the original capture statistics; an unselected
site is not proof of nonexecution. An empty internal-record view does not
establish successful fine-grained profiling.

## Diagnose installation provenance

Run this in the environment used for capture, before running a workload:

```bash
python - <<'PY'
import hashlib
import torch
import triton
import flagtree.profiler
import flagtree.debugger
from flagtree.profiler.native import runtime_binding as profiler_binding
from flagtree.debugger.native import runtime_binding as debugger_binding
import triton._C.libtriton as compiler
for name, module in [('compiler', compiler), ('profiler', profiler_binding()),
                     ('debugger', debugger_binding())]:
    path = module.__file__
    with open(path, 'rb') as file:
        digest = hashlib.sha256(file.read()).hexdigest()
    print(name, path, digest)
print('Torch:', torch.__version__, 'Triton:', triton.__version__)
print('Profiler:', flagtree.profiler.__file__)
print('Debugger:', flagtree.debugger.__file__)
PY
```

Package paths must resolve to the intended installed environment. Compare native
hashes against the installation/build receipt. Include the command, SDK/compiler
versions, installation receipt, original application exception and retained
failure artifacts in a bug report; numerical correctness alone does not prove
that the internal trace is correct.
