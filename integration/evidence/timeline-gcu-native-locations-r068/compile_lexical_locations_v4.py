"""Compile one retained real LLIR with explicit marker file scopes; no GPU."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
from flagtree.profiler._deadline import _stop_worker

p = argparse.ArgumentParser()
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True)
root = Path('/tmp/chijin-timeline-r068-gcu/runs/native-device-v1/output/profile/timeline')
index = json.loads((root / 'index.json').read_text())
capture = json.loads((root / index['captures'][0]['capture_file']).read_text())
original = capture['metadata']['compiled_snapshot']['compiler_artifacts']['llir']
(a.output / 'actual-input.mlir').write_text(original)
steps = []


def run(name, argv, data=None):
    with (a.output / (name + '.stdout')).open('xb') as out, (a.output / (name + '.stderr')).open('xb') as err:
        env = dict(os.environ, TRITON_DISABLE_LINE_INFO='1')
        child = subprocess.Popen(argv, stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                                 stdout=out, stderr=err, env=env, start_new_session=True)
        try:
            child.communicate(data, timeout=60)
        except subprocess.TimeoutExpired:
            _stop_worker(child)
            raise RuntimeError('Owned CPU compilation timed out: ' + name)
    steps.append(dict(name=name, argv=argv, returncode=child.returncode))
    (a.output / 'steps.json').write_text(json.dumps(steps, indent=2))
    if child.returncode:
        raise RuntimeError('CPU stage failed: ' + name)


tool = '/tmp/chijin-timeline-r068-gcu/runs/scopes-build-v3/output/build/flagprism-gcu-timeline'
scoped = a.output / 'scoped.mlir'
validated = a.output / 'validated.mlir'
run('scopes', [tool, '--debug-scopes', str(a.output / 'actual-input.mlir'), str(scoped)])
run('SDK-validate', ['/opt/triton_gcu/bin/gcu-compiler-opt', str(scoped), '--mlir-print-debuginfo', '-o', str(validated)])
fatbin = a.output / 'scoped.fatbin'
run('SDK-compile', ['/opt/triton_gcu/bin/gcu-compiler-compile', '--device-only', '--is-triton-backend',
                    '--arch=gcu300', '--toolkit-path=/opt/triton_gcu', '--output=' + str(fatbin)], validated.read_bytes())
binary = fatbin.read_bytes()
magic = b'__CLANG_OFFLOAD_BUNDLE__'
if not binary.startswith(magic):
    raise RuntimeError('Bad CPU diagnostic fatbin')
count = struct.unpack_from('<Q', binary, len(magic))[0]
cursor = len(magic) + 8
images = []
for part in range(count):
    offset, size, length = struct.unpack_from('<QQQ', binary, cursor)
    cursor += 24
    target = binary[cursor:cursor + length].decode()
    cursor += length
    if not size:
        continue
    elf = binary[offset:offset + size]
    path = a.output / (str(part) + '.elf')
    path.write_bytes(elf)
    run('line-rows', ['/usr/bin/readelf', '--wide', '--debug-dump=decodedline', str(path)])
    text = (a.output / 'line-rows.stdout').read_text()
    marker_lines = [s for s in text.splitlines() if '__flagprism_gcu' in s]
    rows = []
    for line in text.splitlines():
        match = re.match(r'__flagprism_gcu_clock_v1__\s+(\d+)\s+(0x[0-9a-f]+)', line)
        if match:
            rows.append(dict(site=int(match[1]), address=int(match[2], 16)))
    images.append(dict(target=target, elf_sha256=hashlib.sha256(elf).hexdigest(),
                       marker_rows=rows, marker_line_examples=marker_lines[:15], marker_line_count=len(marker_lines)))
result = dict(status='CPU_retained_LLIR_explicit_marker_scope_compiled', steps=steps,
              original_capture_file=index['captures'][0]['capture_file'],
              input_sha256=hashlib.sha256(original.encode()).hexdigest(),
              tool_sha256=hashlib.sha256(Path(tool).read_bytes()).hexdigest(),
              scoped_sha256=hashlib.sha256(scoped.read_bytes()).hexdigest(),
              validated_sha256=hashlib.sha256(validated.read_bytes()).hexdigest(),
              fatbin_sha256=hashlib.sha256(binary).hexdigest(), images=images,
              device_executed=False, original_capture_or_binary_modified=False,
              original_capture_native_mapping_qualified=False)
(a.output / 'result.json').write_text(json.dumps(result, indent=2))
