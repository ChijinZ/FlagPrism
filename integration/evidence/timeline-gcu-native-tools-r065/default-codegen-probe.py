"""One CPU SDK diagnostic on retained IR; no device/application execution.

Generated linked SDK LLVM stays private on the server. No SDK/source mutation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import importlib.util
import sys

p = argparse.ArgumentParser()
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True)
original = Path('/tmp/chijin-timeline-r061-gcu/runs/final-inspect-v1/output/32-8')
source = original / 'input.llir'
source_bytes = source.read_bytes()
(a.output / 'retained-input.mlir').write_bytes(source_bytes)
dump = a.output / 'sdk-generated-private-dump'
dump.mkdir()
env = dict(os.environ)
env['TRITON_DISABLE_LINE_INFO'] = '1'
env['CUTE_DUMP_ASM'] = str(dump)
env.pop('DUMP_ASM_DIR', None)
compiler = Path('/opt/triton_gcu/bin/gcu-compiler-compile')
command = [str(compiler), '--device-only', '--is-triton-backend', '--arch=gcu300', '--toolkit-path=/opt/triton_gcu', '--output=' + str(a.output / 'debug.fatbin')]
deadline_path = '/workspace/chijin-r15-python-alignment/venv/lib/python3.12/site-packages/flagtree/profiler/_deadline.py'
spec = importlib.util.spec_from_file_location('gcu_probe_deadline', deadline_path)
deadline = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = deadline
spec.loader.exec_module(deadline)
with (a.output / 'compile.stdout').open('xb') as out, (a.output / 'compile.stderr').open('xb') as err:
    child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=out, stderr=err, env=env, cwd=a.output, start_new_session=True)
    try:
        child.communicate(source_bytes, timeout=120)
    except subprocess.TimeoutExpired:
        deadline._stop_worker(child)
        raise RuntimeError('Bounded CPU diagnostic compilation timed out')
code = child.returncode
files = [dict(path=str(q.relative_to(a.output)), bytes=q.stat().st_size, sha256=hashlib.sha256(q.read_bytes()).hexdigest()) for q in sorted(a.output.rglob('*')) if q.is_file()]
result = dict(status='CPU_SDK_default_codegen_dump_returned', compiler_returncode=code, source_sha256=hashlib.sha256(source_bytes).hexdigest(), compiler_sha256=hashlib.sha256(compiler.read_bytes()).hexdigest(), source_original_unchanged=source.read_bytes() == source_bytes, files=files, application_replayed=False, device_executed=False, SDK_modified=False, original_executable_modified=False, original_execution_or_region_qualification=False, debug_information_enabled=False, argv=command)
(a.output / 'result.json').write_text(json.dumps(result, indent=2))
if code:
    raise RuntimeError('SDK diagnostic compilation failed; preserve original result')
