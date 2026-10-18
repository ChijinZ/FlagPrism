"""Actual LLVM15 marker checks; not device, clock or region qualification."""
import argparse
import json
import os
from pathlib import Path
import subprocess

PLAIN = '''source_filename = "fixture"
define void @kernel(ptr addrspace(1) %log, ptr addrspace(1) %data,
                    i64 %x, i64 %gx) {
entry:
 call void asm sideeffect "/* flagprism.source_census_site.v3:11:0:3 */", "l,l,l,l,l,l"(i64 %x,i64 0,i64 0,i64 %gx,i64 1,i64 1)
 %v = load i64, ptr addrspace(1) %data
 call void asm sideeffect "/* flagprism.source_census_site.v3:12:1:3 */", "l,l,l,l,l,l"(i64 %x,i64 0,i64 0,i64 %gx,i64 1,i64 1)
 %w = add i64 %v, 7
 store i64 %w, ptr addrspace(1) %data
 call void asm sideeffect "/* flagprism.source_census_site.v3:13:2:3 */", "l,l,l,l,l,l"(i64 %x,i64 0,i64 0,i64 %gx,i64 1,i64 1)
 ret void
}
!hivm.annotations = !{!0}
!0 = !{ptr @kernel, !"kernel"}
'''
DEBUG = '''
!llvm.dbg.cu = !{!1}
!llvm.module.flags = !{!2}
!1 = distinct !DICompileUnit(language: DW_LANG_C, file: !3, producer: "fixture", isOptimized: true, runtimeVersion: 0, emissionKind: FullDebug)
!2 = !{i32 2, !"Debug Info Version", i32 3}
!3 = !DIFile(filename: "fixture.py", directory: "/fixture")
!4 = distinct !DISubprogram(name: "kernel", scope: !3, file: !3, line: 1, type: !5, scopeLine: 1, spFlags: DISPFlagDefinition, unit: !1)
!5 = !DISubroutineType(types: !6)
!6 = !{}
!7 = !DILocation(line: 10, column: 4, scope: !4)
!8 = !DILocation(line: 20, column: 4, scope: !4)
!9 = !DILocation(line: 30, column: 4, scope: !4)
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugin', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    steps, results = [], []

    def run(label, command, env=None):
        with (args.output / (label + '.stdout')).open('wb') as out, (
                args.output / (label + '.stderr')).open('wb') as err:
            child = subprocess.Popen(command, stdout=out, stderr=err, env=env)
            fields = Path('/proc/' + str(child.pid) +
                          '/stat').read_text().rsplit(')', 1)[1].split()
            row = dict(label=label,
                       argv=command,
                       pid=child.pid,
                       startticks=int(fields[19]))
            steps.append(row)
            (args.output / 'steps.json').write_text(json.dumps(steps,
                                                               indent=2))
            row['returncode'] = child.wait(timeout=30)
        (args.output / 'steps.json').write_text(json.dumps(steps, indent=2))
        if row['returncode']:
            raise RuntimeError(label + ' failed')

    debug = PLAIN.replace('i64 %x, i64 %gx) {', 'i64 %x, i64 %gx) !dbg !4 {')
    for site, loc in ((11, 7), (12, 8), (13, 9)):
        lines = debug.splitlines()
        debug = '\n'.join(
            line + ', !dbg !' + str(loc) if 'source_census_site.v3:' +
            str(site) + ':' in line else line for line in lines) + '\n'
    debug += DEBUG
    for actor in ('AIC', 'AIV'):
        stripped = {}
        for kind, text in (('plain', PLAIN), ('debug', debug)):
            work = args.output / (actor + '-' + kind)
            work.mkdir()
            source, dest = work / 'input.ll', work / 'output.ll'
            source.write_text(text)
            env = os.environ.copy()
            env.update(
                FLAGPRISM_ASCEND_TRACE_MODE='source_timeline_v1',
                FLAGPRISM_ASCEND_TRACE_SEMANTICS='source_control_interval',
                FLAGPRISM_ASCEND_COMPILER_OUTPUT=str(work),
                FLAGPRISM_ASCEND_ACTOR_KIND=actor,
                FLAGPRISM_ASCEND_TRACE_ARGUMENT_INDEX='0',
                FLAGPRISM_ASCEND_TRACE_CAPACITY='2',
                FLAGPRISM_ASCEND_CENSUS_COLUMNS='3')
            run(actor + '-' + kind, [
                '/usr/bin/opt-15', '-load-pass-plugin',
                str(args.plugin),
                '-passes=flagprism-ascend-late-observer,verify', '-S',
                str(source), '-o',
                str(dest)
            ], env)
            manifests = [
                json.loads(p.read_text()) for p in work.glob('*.json')
            ]
            if len(manifests) != 1:
                raise RuntimeError('Missing or ambiguous manifest')
            manifest = manifests[0]
            sites = manifest['dynamic_sites']
            if len(sites) != 2 or manifest['boundary_status'] != 'unverified':
                raise RuntimeError(
                    'Unexpected source fragments or qualification')
            for site in sites:
                marker = site['clock_marker']
                if kind == 'plain':
                    if marker['status'] != 'missing_debug_scope' or marker[
                            'entry_line'] or marker['exit_line']:
                        raise RuntimeError(
                            'No-debug input manufactured machine markers')
                else:
                    ident = site['site_id']
                    if (marker['status'] != 'debug_locations_emitted'
                            or marker['entry_line'] != 2 * ident - 1
                            or marker['exit_line'] != 2 * ident
                            or site['debug_file'] != 'fixture.py'):
                        raise RuntimeError(
                            'Clock markers changed source provenance')
            output = dest.read_text()
            if kind == 'debug':
                if '__flagprism_sys_cnt_v1__' not in output:
                    raise RuntimeError('Missing private clock marker file')
                calls = [
                    line for line in output.splitlines()
                    if 'asm sideeffect "MOV $0, SYS_CNT"' in line
                ]
                if len(calls) != 4 or any('!dbg !' not in line
                                          for line in calls):
                    raise RuntimeError(
                        'Clock calls lack distinct debug bindings')
            cleaned = work / 'stripped.ll'
            run(actor + '-' + kind + '-strip', [
                '/usr/bin/opt-15', '-strip-debug', '-S',
                str(dest), '-o',
                str(cleaned)
            ])
            # Module flags/file tables are deliberately different. Compare
            # the complete transformed fixture function after strip-debug.
            body = cleaned.read_text()
            first = body.index('define void @kernel(')
            last = body.index('\n}', first) + 2
            stripped[kind] = body[first:last]
            results.append(
                dict(actor=actor,
                     mode=kind,
                     sites=len(sites),
                     clock_marker_status=sites[0]['clock_marker']['status']))
        if stripped['plain'] != stripped['debug']:
            raise RuntimeError(
                'Debug markers changed executable LLVM instructions')
    (args.output / 'result.json').write_text(
        json.dumps(dict(
            status=
            'actual_llvm15_marker_checks_passed_not_machine_or_device_qualification',
            results=results,
            debug_stripped_instruction_equivalence=True),
                   indent=2))


if __name__ == '__main__':
    main()
