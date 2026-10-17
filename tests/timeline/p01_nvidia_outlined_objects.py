"""Inspect real automatic counter call sites; static evidence, not region proof.

Run inside the server Docker after the ordinary public/type math regressions.
No device launch, application replay, clock qualification or hardware-busy claim.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import time


def need(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--capture-root', type=Path, action='append')
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    roots = args.capture_root or [
        Path('/workspace/chijin-timeline-r012/runs/boundary-math-v1/output'),
        Path('/workspace/chijin-timeline-r012/runs/public-outlined-v1/output')]
    from flagtree.profiler.timeline_nvidia_machine import find_nvdisasm, _run_tool
    tool = find_nvdisasm()
    need(tool is not None, 'Pinned actual nvdisasm is required')
    deadline = time.monotonic()+180
    objects = {}
    for root in roots:
        for path in root.rglob('*.cubin'):
            need(path.stat().st_size <= 32*1024*1024, 'Unexpected object size')
            objects.setdefault(sha(path), path)
    maps = {}
    for root in roots:
        for path in root.rglob('counter-map.json'):
            value = json.loads(path.read_text())
            identity = value['artifacts']['cubin_sha256']
            maps.setdefault(identity, (path, value))
    need(maps, 'Actual automatic counter maps are required')
    results = []
    for identity, (map_path, mapping) in sorted(maps.items()):
        need(identity in objects, 'Mapped actual cubin was not retained')
        need(not mapping['clock_qualified'] and not mapping['region_boundaries_verified'],
             'This inspection must not inherit unearned certificates')
        cubin = objects[identity]
        directory = args.output/identity
        directory.mkdir()
        receipts = []
        cfg = _run_tool(tool, ['--output-control-flow-graph', '--print-instr-offsets-cfg',
                             str(cubin)], directory, 'cfg', deadline, receipts)
        need(b'digraph' in cfg and len(cfg) > 100, 'Actual CFG is absent')
        original_json = map_path.with_name('json.stdout')
        original_text = map_path.with_name('lines.stdout')
        need(sha(original_json) == mapping['artifacts']['sass_json_sha256'] and
             sha(original_text) == mapping['artifacts']['sass_lines_sha256'],
             'Actual machine inputs changed')
        functions = json.loads(original_json.read_bytes())[1]
        descriptors = {f['function-name']: f for f in functions}
        calls = []
        for f in functions:
            for i, instruction in enumerate(f['sass-instructions']):
                opcode = instruction['opcode']
                if not opcode.startswith('CALL'):
                    continue
                callee = instruction.get('operands')
                # JSON stores the exact symbol; text uses CUDA's `(symbol).
                need(type(callee) is str and callee in descriptors,
                     'Unresolved actual call target; do not infer by name prefix')
                pc = f['start']+16*i
                pattern = (r'/\*0*'+format(pc, 'x')+r'\*/\s*'+re.escape(opcode)+
                           r'\s+`\('+re.escape(callee)+r'\)\s*;')
                need(re.search(pattern, original_text.read_text()),
                     'Actual text/JSON call target mismatch')
                calls.append(dict(caller=f['function-name'], pc=pc, callee=callee,
                                  opcode=opcode))
        need(calls, 'Automatic noinline calls are absent')
        counters = []
        for counter in mapping['counter_pcs']:
            owners = [c for c in calls if c['callee'] == counter['function']]
            need(owners, 'Counter helper has no explicit direct caller')
            counters.append(dict(counter, direct_call_sites=owners))
        barriers = [dict(function=f['function-name'], pc=f['start']+16*i,
                         opcode=ins['opcode'])
                    for f in functions for i, ins in enumerate(f['sass-instructions'])
                    if ins['opcode'].startswith('MEMBAR')]
        # These development inputs have no baseline MEMBAR. Do not replace this
        # with a universal rule rejecting ordinary kernels with their own fences.
        need(not barriers, 'Unexpected completion/memory barrier in these inputs')
        row = dict(cubin_sha256=identity, cubin=str(cubin), counter_map=str(map_path),
                   counter_map_sha256=sha(map_path), functions=len(functions),
                   nonzero_function_starts=sum(f['start'] != 0 for f in functions),
                   calls=calls, counters=counters, membar_instructions=barriers,
                   cfg_sha256=hashlib.sha256(cfg).hexdigest(),
                   region_boundaries_verified=False, clock_qualified=False)
        (directory/'object.json').write_text(json.dumps(row, indent=2)+'\n')
        results.append(row)
    (args.output/'result.json').write_text(json.dumps(dict(
        status='actual_automatic_calls_and_cfg_retained_not_region_or_clock_certified',
        device_launches=0, objects=results, nvdisasm=str(tool), nvdisasm_sha256=sha(tool),
        limitations=['Static calls and counter PCs do not prove dynamic source region boundaries.',
                     'No clock scale, epoch, endpoint error or hardware completion qualification.']),
        indent=2)+'\n')


if __name__ == '__main__':
    main()
