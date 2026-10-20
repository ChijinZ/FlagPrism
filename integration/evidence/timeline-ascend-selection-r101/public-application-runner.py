"""One original q05 through the normally installed public timeline CLI."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

p = argparse.ArgumentParser()
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True)
payload = Path(__file__).parent
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
config = json.loads((payload/'config.json').read_text())
for name, digest in config['application_sha256'].items():
    if sha(payload/'app'/name) != digest:
        raise ValueError('Frozen application changed: '+name)
env = dict(os.environ, **config['environment'])
env.pop('PYTHONPATH', None)
env.update(USE_FLAGCX='OFF', USE_FLIR='OFF', USE_FLAGPRISM='OFF')
env['PATH'] = str(Path(sys.executable).parent)+':'+env['PATH']
env['TRITON_CACHE_DIR'] = str(a.output/'cache')
command = [sys.executable, '-m', 'flagtree.profiler.cli', '--backend', 'cann',
           '--detail', 'timeline', '--device', '4', '--compile-timeout', '120',
           '--export-timeout', '60', '-n', str(a.output/'capture'),
           str(payload/'app/launch.py'), '--backend', 'ascend', '--torch-device',
           'npu:4', '--case', 'q05', '--shape', '0', '--config', '0',
           '--runtime-k', '3', '--result', str(a.output/'math.json')]
started = time.monotonic_ns()
with (a.output/'application.log').open('xb') as log:
    child = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT)
    fields = Path('/proc/'+str(child.pid)+'/stat').read_text().rsplit(')', 1)[1].split()
    owner = dict(argv=command, pid=child.pid, startticks=int(fields[19]),
                 installed_python=sys.executable, source_commit=config['commit'],
                 application_sha256=config['application_sha256'])
    (a.output/'application-owner.json').write_text(json.dumps(owner, indent=2))
    try:
        code = child.wait(timeout=260)
    except subprocess.TimeoutExpired:
        spec = importlib.util.spec_from_file_location('owned_cleanup', config['deadline'])
        cleanup = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cleanup
        spec.loader.exec_module(cleanup)
        cleanup._stop_worker(child)
        raise
    finally:
        (a.output/'application-terminal.json').write_text(json.dumps(
            dict(owner, returncode=child.returncode, wall_ns=time.monotonic_ns()-started), indent=2))
if code:
    raise RuntimeError('Public CLI failed; retain its original output')
math = json.loads((a.output/'math.json').read_text())
for key in ('guard_pass', 'input_immutable', 'state_unique_logical_index_pass'):
    if math[key] is not True:
        raise ValueError('Math check failed: '+key)
if math['source_sha256'] != config['application_sha256']:
    raise ValueError('Actual source identity differs')
if len(list(a.output.glob('*.host-once.json'))) != 1:
    raise ValueError('Host invocation count differs')
from flagtree.profiler.timeline_capture_store import load_capture
from flagtree.profiler.timeline_store import read_artifact
from flagtree.profiler.timeline_ascend_offline import decode_capture
timeline = a.output/'capture/timeline'
index = json.loads((timeline/'index.json').read_text())
if len(index['captures']) != 1 or any(index.get(k) for k in ('retained_owners','pending_decode','failures')):
    raise ValueError('Public capture not finalized')
capture = load_capture(timeline, index['captures'][0]['capture_file'])
raw = read_artifact(timeline, capture['raw_file'])
batch = decode_capture(capture, raw)
guard = read_artifact(timeline, capture['readback_guard']['file'])
if guard != bytes([165])*128 or len(raw)+128 > 8388608:
    raise ValueError('Raw budget/guard mismatch')
if not batch['complete']:
    raise ValueError('Actual raw batch incomplete')
bundle_bytes = sum(f.stat().st_size for f in timeline.rglob('*') if f.is_file())
if bundle_bytes > 67108864:
    raise ValueError('Bundle budget exceeded')
(a.output/'expanded-capture.json').write_text(json.dumps(capture, indent=2))
(a.output/'fresh-batch.json').write_text(json.dumps(batch, indent=2))
(a.output/'result.json').write_text(json.dumps(dict(
    status='public_q05_new_selection_captured', source_commit=config['commit'],
    capture_file=index['captures'][0]['capture_file'], raw_sha256=hashlib.sha256(raw).hexdigest(),
    bundle_bytes=bundle_bytes, raw_bytes=len(raw), host_once=True, complete=batch['complete'],
    source_boundary_qualified=False, native_schedule_qualified=False), indent=2))
