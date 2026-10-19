"""Native CLI origin-location regressions; run in the matching SDK Docker.

These LLVM fixtures check metadata and navigation, not device timing.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile

IR = '''target triple = "nvptx64-nvidia-cuda"
define ptx_kernel void @kernel(ptr addrspace(1) %out, ptr addrspace(1) %scratch) #0 !dbg !4 {
entry:
  %v = load float, ptr addrspace(1) %out, align 4, !dbg !5
  %x = fmul float %v, 1.250000e+00, !dbg !5
  store float %x, ptr addrspace(1) %out, align 4, !dbg !5
  ret void, !dbg !5
}
attributes #0 = { "nvvm.reqntid"="4" }
!llvm.dbg.cu = !{!1}
!llvm.module.flags = !{!0}
!0 = !{i32 2, !"Debug Info Version", i32 3}
!1 = distinct !DICompileUnit(language: DW_LANG_C, file: !2, producer: "origin-fixture", isOptimized: true, runtimeVersion: 0, emissionKind: LineTablesOnly)
!2 = !DIFile(filename: "user.py", directory: "/fixture")
!3 = !DISubroutineType(types: !{})
!4 = distinct !DISubprogram(name: "kernel", scope: !2, file: !2, line: 1, type: !3, scopeLine: 1, spFlags: DISPFlagDefinition, unit: !1)
!5 = !DILocation(line: 4, column: 2, scope: !4)
'''


def run(tool, output):
    output.mkdir(parents=True)
    reports = []
    cases = [('direct', IR),
             ('no_debug',
              IR.split('!llvm.dbg.cu')[0].replace(' !dbg !4',
                                                  '').replace(', !dbg !5',
                                                              ''))]
    inline = IR.replace(
        '!5 = !DILocation(line: 4, column: 2, scope: !4)',
        '''!5 = !DILocation(line: 4, column: 2, scope: !7, inlinedAt: !6)
!6 = !DILocation(line: 8, column: 3, scope: !4)
!7 = distinct !DISubprogram(name: "helper", scope: !2, file: !2, line: 3, type: !3, scopeLine: 3, spFlags: DISPFlagDefinition, unit: !1)'''
    )
    cases.append(('inlined', inline))
    for name, source in cases:
        with tempfile.TemporaryDirectory(
                prefix='flagprism-origin-cli-') as tmp:
            root = Path(tmp)
            src, dst, manifest = root / 'input.ll', root / 'output.ll', root / 'plan.json'
            src.write_text(source)
            command = [
                str(tool),
                str(src), '--output',
                str(dst), '--manifest',
                str(manifest), '--flagtree-profile-abi=1', '--batch-records',
                '--group-matrix', '--compact-programs'
            ]
            result = subprocess.run(command, capture_output=True, timeout=20)
            if result.returncode:
                raise RuntimeError(name + ': ' + result.stderr.decode())
            plan = json.loads(manifest.read_text())
            members = [m for site in plan['sites'] for m in site['members']]
            if len(members) < 3 or plan['native_origin_marker_version'] != 1:
                raise RuntimeError('Missing native origin inventory')
            markers = [m['native_origin_marker'] for m in members]
            transformed = dst.read_text()
            if name == 'no_debug':
                if any(m['status'] != 'unavailable_no_debug_scope'
                       for m in markers):
                    raise RuntimeError('Missing scope acquired origin rights')
            else:
                if any(
                        m.get('file') != 'user.py' or m.get('line') != 4
                        or m.get('column') != 2 for m in members):
                    raise RuntimeError('User source navigation overwritten')
                if any(m['status'] != 'compiler_location_assigned'
                       for m in markers):
                    raise RuntimeError('Actual LLVM origin marker unavailable')
                lines = [m['line'] for m in markers]
                if len(set(lines)) != len(lines):
                    raise RuntimeError(
                        'Original operations share an origin ID')
                if '__flagprism_native_origin_v1__' not in transformed:
                    raise RuntimeError('Native marker file missing from LLVM')
                file_id = re.findall(
                    r'!(\d+) = !DIFile\(filename: "__flagprism_native_origin_v1__"',
                    transformed)
                if len(file_id) != 1:
                    raise RuntimeError('Ambiguous native origin DIFile')
                scopes = {
                    m[1]
                    for m in re.finditer(
                        r'!(\d+) = !DILexicalBlockFile\([^\n]*file: !' +
                        file_id[0] + r'[,)]', transformed)
                }
                locations = {
                    m[1]
                    for m in re.finditer(
                        r'!(\d+) = !DILocation\([^\n]*scope: !(\d+)[,)]',
                        transformed) if m[2] in scopes
                }
                if len(locations) != len(lines):
                    raise RuntimeError('Origin locations do not cover members')
                for line in transformed.splitlines():
                    if 'flagprism_late_probe_site_' in line:
                        dbg = re.search(r'!dbg !(\d+)', line)
                        if dbg and dbg[1] in locations:
                            raise RuntimeError(
                                'Clock inherited original-operation marker')
            reports.append(
                dict(case=name,
                     members=len(members),
                     native_marker_statuses=[m['status'] for m in markers],
                     stderr=result.stderr.decode()))
    (output / 'result.json').write_text(
        json.dumps(dict(status='native_origin_marker_CLI_fixtures_passed',
                        checks=reports,
                        device_executed=False),
                   indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tool', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.tool, args.output)


if __name__ == '__main__':
    main()
