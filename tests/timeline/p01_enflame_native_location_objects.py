"""Check actual GCU executable snapshots for automatic native marker sites.

Run after p01_enflame_native_locations.py, without replaying the application:
  python p01_enflame_native_location_objects.py --timeline BUNDLE/timeline --output OUT

Requires the matching GCU SDK Docker's readelf and LLVM11 objdump. This checks
actual file/site line retention, not reader value flow or all-path regions.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--output', type=Path, required=True)
p.add_argument('--timeline', type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True)
root = a.timeline
index = json.loads((root / 'index.json').read_text())
results = []
for number, entry in enumerate(index['captures']):
    capture = json.loads((root / entry['capture_file']).read_text())
    if capture['metadata']['compiler_metadata'].get(
            'debug_execution_native_marker_version') != 1:
        raise RuntimeError('Capture predates native clock marker generation')
    snapshot = capture['metadata']['compiled_snapshot']
    binary = base64.b64decode(snapshot['binary_base64'], validate=True)
    if hashlib.sha256(
            binary).hexdigest() != snapshot['executable']['binary_sha256']:
        raise RuntimeError('Actual capture executable digest mismatch')
    dest = a.output / str(number)
    dest.mkdir()
    (dest / 'actual.fatbin').write_bytes(binary)
    magic = b'__CLANG_OFFLOAD_BUNDLE__'
    if not binary.startswith(magic):
        raise RuntimeError('Unexpected actual bundle format')
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
        path = dest / (str(part) + '.elf')
        path.write_bytes(elf)
        commands = [
            ('line-rows', [
                '/usr/bin/readelf', '--wide', '--debug-dump=decodedline',
                str(path)
            ]),
            ('line-program',
             ['/usr/bin/readelf', '--wide', '--debug-dump=rawline',
              str(path)]),
            ('native', [
                '/opt/tops/llvm11/bin/llvm-objdump', '-d', '--triple=dtu',
                '--mcpu=gcu300', '--demangle', '--line-numbers',
                str(path)
            ])
        ]
        tools = []
        for name, argv in commands:
            out = dest / (name + '.stdout')
            err = dest / (name + '.stderr')
            with out.open('xb') as stdout, err.open('xb') as stderr:
                done = subprocess.run(argv,
                                      stdout=stdout,
                                      stderr=stderr,
                                      timeout=30)
            tools.append(
                dict(name=name,
                     argv=argv,
                     returncode=done.returncode,
                     bytes=out.stat().st_size,
                     sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
                     stderr=err.read_text()[:1500]))
            if done.returncode:
                raise RuntimeError('Actual object inspection failed: ' + name)
        text = (dest / 'line-rows.stdout').read_text()
        rows = []
        unknown_rows = []
        for line in text.splitlines():
            match = re.match(
                r'__flagprism_gcu_clock_v1__\s+(\d+)\s+(0x[0-9a-f]+)', line)
            if match:
                row = dict(site=int(match[1]), address=int(match[2], 16))
                (rows if row['site'] else unknown_rows).append(row)
        manifest = capture['metadata']['compiler_metadata'][
            'debug_execution_manifest']
        expected = sorted(s['id'] for s in manifest['sites'])
        present = sorted({r['site'] for r in rows})
        images.append(
            dict(target=target,
                 elf_sha256=hashlib.sha256(elf).hexdigest(),
                 tools=tools,
                 expected_manifest_sites=expected,
                 sites_in_actual_line_table=present,
                 missing_manifest_sites=sorted(set(expected) - set(present)),
                 actual_marker_rows=rows,
                 compiler_unknown_line_rows=unknown_rows))
    results.append(
        dict(capture_file=entry['capture_file'],
             binary_id=capture['owner']['binary_id'],
             fatbin_sha256=hashlib.sha256(binary).hexdigest(),
             images=images))
(a.output / 'result.json').write_text(
    json.dumps(dict(status='actual_capture_native_location_inspection',
                    captures=results,
                    application_replayed=False,
                    device_executed=False,
                    reader_to_raw_valueflow_qualified=False,
                    all_path_region_qualified=False),
               indent=2))

if any(i['missing_manifest_sites'] for c in results for i in c['images']):
    raise RuntimeError(
        'Actual capture ELF did not retain every automatic marker site')
