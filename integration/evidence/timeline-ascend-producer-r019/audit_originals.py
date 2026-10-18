"""Stdlib byte audit of retained development evidence; no product imports."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import tarfile


def need(value, message):
    if not value:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('archive', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with tarfile.open(args.archive) as archive:
        files = {}
        for member in archive.getmembers():
            need(member.isfile() and member.size <= 16 * 1024 * 1024,
                 'Unexpected evidence member')
            data = archive.extractfile(member).read()
            need(member.name not in files or files[member.name] == data,
                 'Conflicting evidence path')
            files[member.name] = data
    def read(name):
        return json.loads(files[name])
    process_rows = read('audits/processes.json')
    need(all(r['current_state'] in ('missing', 'Z', 'different_process')
             for r in process_rows), 'A recorded owner is still live')
    binding = read('audits/source-native-binding.json')
    need(len(binding['reused_members']) == 97, 'Unexpected native bridge scope')
    checks = read('runs/checks-v3/terminal.json')
    need(checks['state'] == 'terminal' and checks['returncode'] == 0,
         'Final checks did not terminate successfully')
    root = 'runs/checks-v3/output/'
    for mode in ('normal', 'optimized'):
        need('22 passed' in files[root + mode + '.stdout'].decode(),
             'Installed regression result missing')
    result = read(root + 'device-probe/result.json')
    need(len(result['calls']) == 4 and len(result['captures']) == 2,
         'Actual call matrix changed')
    for offset in (0, 2):
        need(result['calls'][offset]['binary'] == result['calls'][offset + 1]['binary'],
             'Runtime K changed binary')
    pair_counts, positive = [], 0
    for capture_index, k in enumerate((3, 7)):
        prefix = root + 'device-probe/capture-' + str(capture_index)
        raw = files[prefix + '.raw']
        meta = read(prefix + '.metadata.json')
        need(hashlib.sha256(raw).hexdigest() == result['captures'][capture_index]['raw_sha256'],
             'Retained raw differs from producer receipt')
        need(meta['hash'] == result['calls'][2 + capture_index]['binary'],
             'Compiler/call identity mismatch')
        handoff = meta['flagprism_ascend_handoff']
        need(handoff['phase'] == 'finished', 'Compiler handoff incomplete')
        for artifact in handoff['artifacts']:
            need(hashlib.sha256(artifact['llir'].encode()).hexdigest() == artifact['sha256'],
                 'Original LLVM changed')
            need(hashlib.sha256(artifact['manifest_text'].encode()).hexdigest() == artifact['manifest_sha256'],
                 'Manifest changed')
            need(json.loads(artifact['manifest_text']) == artifact['metadata'],
                 'Manifest representations disagree')
            need(hashlib.sha256(artifact['adapted']['llir'].encode()).hexdigest() == artifact['adapted']['sha256'],
                 'Actual adapted LLVM changed')
            need('MOV $0, SYS_CNT' in artifact['adapted']['llir'],
                 'Device clock reader missing')
        stride = 64 + 128 * 64
        need(len(raw) == 2 * 3 * stride, 'Physical extent mismatch')
        observed = []
        for slot, program in enumerate((0, 4)):
            for actor in range(3):
                base = (slot * 3 + actor) * stride
                header = struct.unpack_from('<8Q', raw, base)
                if not any(header):
                    need(not any(raw[base:base + stride]), 'Unpublished slot has payload')
                    continue
                magic, committed, attempted, dropped, pid, who, block, flags = header
                need((magic, committed, attempted, dropped, pid, who, flags) ==
                     (0x46505441314c4f47, k + 5, k + 5, 0, program, actor, 1),
                     'Actual header/counter mismatch')
                sites = Counter()
                for pair_index in range(committed):
                    record = struct.unpack_from('<8Q', raw, base + 64 + pair_index * 64)
                    descriptor, sequence, start, end, p, a, physical, tag = record
                    need(sequence == pair_index and descriptor >> 32 == 1 and
                         (p, a, physical) == (program, actor, block) and end >= start and
                         tag == (0x46505441434f4d31 ^ descriptor ^ sequence ^ p ^ a ^ physical),
                         'Actual committed pair mismatch')
                    sites[descriptor & 0xffffffff] += 1
                    positive += int(end > start)
                need(sorted(sites.values()) == [1, 1, 1, 1, 1, k],
                     'Dynamic source visit structure differs from runtime K')
                observed.append((program, actor, committed))
        need(observed == [(0, 1, k + 5), (4, 1, k + 5)],
             'First/last real writers differ from the retained claim')
        pair_counts.append(observed)
    need(positive > 0, 'Only zero-width device intervals were retained')
    census = json.loads(files[root + 'census-regression.stdout'].decode().splitlines()[-1])
    need(census['status'] == 'pass' and census['state_elements'] == 1024,
         'Old public census regression missing')
    args.output.write_text(json.dumps(dict(
        scope='development producer byte audit, not P01 or physical clock qualification',
        archive_sha256=hashlib.sha256(args.archive.read_bytes()).hexdigest(),
        archive_bytes=args.archive.stat().st_size, files=len(files),
        pair_counts=pair_counts, pairs=40, positive_intervals=positive,
        native_members_reused=97, cpu_normal=22, cpu_optimized=22,
        old_census_math='passed', recorded_processes=len(process_rows),
        boundary_status='unverified', clock_units='unverified',
        public_collector='not_connected'), indent=2) + '\n')


if __name__ == '__main__':
    main()
