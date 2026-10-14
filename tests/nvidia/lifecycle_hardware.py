"""Hardware-backed rejection/recovery checks for the shared detailed buffer."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
sys.path.insert(0, str(Path(os.environ['METHOD_COMPILER_SOURCE']) / 'python'))
import torch
import triton
import triton.language as tl
import flagtree
source = Path(os.environ['METHOD_SOURCE'])
package = source / 'Profiler/python/flagtree_profiler'
spec = importlib.util.spec_from_file_location('flagtree.profiler', package / '__init__.py', submodule_search_locations=[str(package)])
profiler = importlib.util.module_from_spec(spec)
sys.modules['flagtree.profiler'] = profiler
spec.loader.exec_module(profiler)
from flagtree.profiler import language as pl
from flagtree.profiler.hooks.hook import Hook, HookManager
pl.enable_semantic('triton')

@triton.jit
def kernel(X, Y, B: tl.constexpr):
    indices = tl.arange(0, B)
    pl.enter_scope('body')
    value = tl.load(X + indices) + 1
    pl.exit_scope('body')
    tl.store(Y + indices, value)

class TestHook(Hook):
    def activate(self): pass
    def deactivate(self): pass
    def init_handle(self, *args): pass
    def exit(self, metadata): pass

class PauseHook(TestHook):
    priority = 200
    def enter(self, metadata):
        entered.set()
        if not release.wait(10):
            raise RuntimeError('Test pause timed out')

class FailAfterInstrumentation(TestHook):
    priority = -10
    def enter(self, metadata):
        raise RuntimeError('controlled post-instrumentation rejection')

output = Path(sys.argv[1])
output.mkdir(parents=True, exist_ok=False)
x = torch.arange(256, device='cuda', dtype=torch.float32)
y = torch.empty_like(x)
z = torch.empty_like(x)
mode = profiler.mode.Default(sampling_strategy='selective', sampling_options='0', granularity='warp', buffer_size=256)
entered, release = threading.Event(), threading.Event()
session = profiler.start(str(output / 'concurrent'), backend='instrumentation', hook='instrumentation', mode=mode)
pause = PauseHook()
HookManager.register(pause, session)
errors = []
def first_launch():
    try:
        with torch.cuda.device(0):
            kernel[(1,)](x, y, 256, num_warps=4)
    except BaseException as error:
        errors.append(error)
worker = threading.Thread(target=first_launch)
worker.start()
assert entered.wait(10)
try:
    kernel[(1,)](x, z, 256, num_warps=4)
except RuntimeError as error:
    assert 'Concurrent NVIDIA instrumented JIT launches' in str(error), error
else:
    raise AssertionError('Concurrent launch was not explicitly rejected')
finally:
    release.set()
worker.join(10)
assert not worker.is_alive() and not errors, errors
HookManager.active_hooks.remove(pause)
HookManager.session_hooks[session].pop(pause)
profiler.finalize(session)
torch.testing.assert_close(y.cpu(), x.cpu() + 1)
captured = json.loads((output / 'concurrent/ai/observations.json').read_text())
assert len(captured['captures']) == 1
print('PASS CONCURRENT_DETAILED_REJECTED_FIRST_LAUNCH_PRESERVED', flush=True)

session = profiler.start(str(output / 'rollback'), backend='instrumentation', hook='instrumentation', mode=mode)
fail = FailAfterInstrumentation()
HookManager.register(fail, session)
try:
    kernel[(1,)](x, y, 256, num_warps=4)
except RuntimeError as error:
    assert str(error) == 'controlled post-instrumentation rejection'
else:
    raise AssertionError('Controlled pre-launch rejection did not propagate')
HookManager.active_hooks.remove(fail)
HookManager.session_hooks[session].pop(fail)
kernel[(1,)](x, y, 256, num_warps=4)
profiler.finalize(session)
torch.testing.assert_close(y.cpu(), x.cpu() + 1)
launches = json.loads((output / 'rollback/ai/launches.json').read_text())
assert sum(row.get('status') == 'rejected_before_launch' for row in launches) == 1, launches
captured = json.loads((output / 'rollback/ai/observations.json').read_text())
assert len(captured['captures']) == 1
assert captured['captures'][0]['decoded']['observations'][0]['association_status'] == 'verified'
print('PASS POST_ENTER_ROLLBACK_AND_FOLLOWUP_LAUNCH', flush=True)

# An explicit observation request requires surviving source annotations. This
# differs from a valid annotated runtime branch producing zero records.
from flagtree.profiler.observations import ObservationRequest
@triton.jit
def unannotated(X, Y, B: tl.constexpr):
    indices = tl.arange(0, B)
    tl.store(Y + indices, tl.load(X + indices) + 1)
session = profiler.start(str(output / 'unannotated'), backend='instrumentation',
                         hook='instrumentation', observation_request=ObservationRequest(max_events_per_instance=4))
try:
    unannotated[(1,)](x, y, 256, num_warps=4)
except RuntimeError as error:
    assert 'requires explicit Proton scopes' in str(error), error
else:
    raise AssertionError('Explicit request silently accepted unannotated kernel')
kernel[(1,)](x, y, 256, num_warps=4)
profiler.finalize(session)
launches = json.loads((output / 'unannotated/ai/launches.json').read_text())
assert sum(row.get('status') == 'rejected_before_launch' for row in launches) == 1, launches
captured = json.loads((output / 'unannotated/ai/observations.json').read_text())
assert len(captured['captures']) == 1
print('PASS EXPLICIT_REQUEST_REJECTS_MISSING_ANNOTATIONS_AND_RECOVERS', flush=True)

@triton.jit
def too_many_scopes(X, Y, B: tl.constexpr):
    i = tl.arange(0, B)
    value = tl.load(X + i)
    for site in tl.static_range(257):
        pl.enter_scope('repeated_annotation')
        value += 1
        pl.exit_scope('repeated_annotation')
    tl.store(Y + i, value)
session = profiler.start(str(output / 'scope-alias'), backend='instrumentation',
                         hook='instrumentation', observation_request=ObservationRequest(max_events_per_instance=4))
y.fill_(-99)
# The inherited dialect verifier rejects this ABI before a launcher exists.
# Capture the real compiler diagnostic rather than inventing a launch row.
import tempfile
saved_stderr = os.dup(2)
with tempfile.TemporaryFile() as diagnostic:
    os.dup2(diagnostic.fileno(), 2)
    try:
        try:
            too_many_scopes[(1,)](x, y, 256, num_warps=4)
        except RuntimeError as error:
            assert 'PassManager::run failed' in str(error), error
        else:
            raise AssertionError('Aliased scope identities were silently collected')
    finally:
        os.dup2(saved_stderr, 2)
        os.close(saved_stderr)
    diagnostic.seek(0)
    compiler_error = diagnostic.read().decode()
assert 'scope id must be in [0, 255]' in compiler_error, compiler_error
(output/'scope-alias-compiler-diagnostic.txt').write_text(compiler_error)
torch.testing.assert_close(y.cpu(), torch.full_like(x.cpu(), -99))
kernel[(1,)](x,y,256,num_warps=4)
profiler.finalize(session)
launches=json.loads((output/'scope-alias/ai/launches.json').read_text())
assert len(launches)==1 and launches[0].get('status')!='rejected_before_launch'
assert len(json.loads((output/'scope-alias/ai/observations.json').read_text())['captures'])==1
print('PASS_SCOPE_ALIAS_COMPILER_REJECTION_AND_RECOVERY',flush=True)
