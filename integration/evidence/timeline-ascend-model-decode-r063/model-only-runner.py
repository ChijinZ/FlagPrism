"""One bounded CPU-model decoder probe on the unchanged actual C1 object.

Model times are never accepted as hardware times or exported as product views.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True)
sdk = Path('/usr/local/Ascend/cann-9.0.0')
model = sdk / 'tools/simulator/Ascend910B4/lib'
source = Path(__file__).parent / 'host.cpp'
timeline = Path('/tmp/chijin-timeline-r060-ascend/runs/participation-device-v1/output/device/vector/capture/timeline')
index = json.loads((timeline / 'index.json').read_text())
capture_file = timeline / index['captures'][0]['capture_file']
capture = json.loads(capture_file.read_text())
original = timeline / 'machine' / capture['owner']['binary_id'] / 'loaded.elf'
expected = '73c2d8d27a949359f22fce1095c56706240d065cad492e73f97653848d682b0d'
if hashlib.sha256(original.read_bytes()).hexdigest() != expected:
    raise RuntimeError('The existing actual vector object changed')
if capture['metadata']['compiler_metadata']['name'] != 'recurrence':
    raise RuntimeError('Unexpected public controlled example')
raw_bytes = (timeline / capture['raw_file']).stat().st_size
if raw_bytes != 786816 or capture['owner']['layout']['grid'] != [3, 1, 1]:
    raise RuntimeError('Actual launch geometry or raw allocation changed')
local_image = args.output / 'actual-recorded-vector.elf'
local_image.write_bytes(original.read_bytes())
runtime_links = args.output / 'model-link'
runtime_links.mkdir()
(runtime_links / 'libruntime.so').symlink_to(model / 'libruntime_camodel.so')
environment = dict(os.environ)
environment['LD_LIBRARY_PATH'] = ':'.join([str(runtime_links), str(model),
                                         str(sdk / 'lib64'), environment.get('LD_LIBRARY_PATH', '')])
for name in ['ASCEND_RT_VISIBLE_DEVICES', 'ASCEND_VISIBLE_DEVICES', 'PYTHONPATH']:
    environment.pop(name, None)
model_configuration = model / 'config.json'
configuration_data = model_configuration.read_bytes()
configuration_sha = hashlib.sha256(configuration_data).hexdigest()
(args.output / 'vendor-model-config-before.json').write_bytes(configuration_data)
deadline_path = Path('/tmp/chijin-timeline-r019/input/Profiler/python/flagtree_profiler/_deadline.py')
spec = importlib.util.spec_from_file_location('owned_model_deadline', deadline_path)
deadline = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = deadline
spec.loader.exec_module(deadline)
steps = []


def run(name, command, timeout):
    with (args.output / (name + '.stdout')).open('xb') as out, (args.output / (name + '.stderr')).open('xb') as err:
        child = subprocess.Popen(command, env=environment, cwd=args.output,
                                 stdout=out, stderr=err, start_new_session=True)
        fields = Path('/proc', str(child.pid), 'stat').read_text().rsplit(')', 1)[1].split()
        record = dict(name=name, argv=command, pid=child.pid,
                      pgid=int(fields[2]), startticks=int(fields[19]), timeout_seconds=timeout)
        steps.append(record)
        (args.output / 'steps.json').write_text(json.dumps(steps, indent=2))
        try:
            record['returncode'] = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            deadline._stop_worker(child)
            record.update(returncode=child.returncode, timed_out=True)
        (args.output / 'steps.json').write_text(json.dumps(steps, indent=2))
    return record['returncode']


binding = dict(actual_capture_file=str(capture_file),
               actual_capture_sha256=hashlib.sha256(capture_file.read_bytes()).hexdigest(),
               actual_binary_id=capture['owner']['binary_id'],
               actual_ELF_sha256=expected, host_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
               raw_bytes=raw_bytes, grid=[3, 1, 1], runtime_steps=3,
               model_directory=str(model), original_model_configuration_sha256=configuration_sha,
               hardware_kernel_executed=False, product_changed=False,
               purpose='SDK instruction decoding only; never hardware duration or new hardware qualification')
(args.output / 'binding.json').write_text(json.dumps(binding, indent=2))
executable = args.output / 'model-only-host'
command = ['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Wno-deprecated-declarations',
           '-I' + str(sdk / 'pkg_inc/runtime'), '-I' + str(sdk / 'pkg_inc'), '-I' + str(sdk / 'include'), '-I' + str(sdk / 'pkg_inc/profiling'),
           '-I' + str(sdk / 'include/experiment'), '-I' + str(sdk / 'include/experiment/msprof'),
           str(source), '-L' + str(runtime_links),
           '-Wl,-rpath,' + str(runtime_links), '-Wl,-rpath,' + str(model),
           '-lruntime', '-o', str(executable)]
if run('host-build', command, 45):
    raise RuntimeError('Host-only model loader build failed; preserve diagnostics')
model_report = args.output / 'MODEL-only-result.json'
application = shlex.join([str(executable), str(local_image), str(raw_bytes),
                          str(model_report), str(model)])
profiler = sdk / 'tools/msopprof/bin/msopprof'
command = [str(profiler), 'simulator', '--soc-version=Ascend910B4',
           '--core-id=0', '--kernel-name=recurrence', '--launch-count=1',
           '--timeout=1', '--output=' + str(args.output / 'SDK-MODEL-output'),
           '--application=' + application]
code = run('SDK-MODEL', command, 105)
model_result = json.loads(model_report.read_text()) if model_report.exists() else None
files = [dict(path=str(p.relative_to(args.output)), bytes=p.stat().st_size)
         for p in sorted(args.output.rglob('*')) if p.is_file() and not p.is_symlink()]
result = dict(status='CPU_model_probe_returned', SDK_returncode=code,
              model_result=model_result, files=files, **binding)
(args.output / 'result.json').write_text(json.dumps(result, indent=2))
if hashlib.sha256(original.read_bytes()).hexdigest() != expected:
    raise RuntimeError('Original actual object mutated')
if hashlib.sha256(model_configuration.read_bytes()).hexdigest() != configuration_sha:
    raise RuntimeError('Vendor model configuration changed unexpectedly')
if code or model_result is None or not model_result.get('model_math_state_and_guards_passed'):
    raise RuntimeError('SDK model probe is incomplete; do not claim native boundary qualification')
