"""Exact final-ELF/DWARF SYS_CNT locations for the inspected c220 vector/mixed targets.

Locations certify neither region bounds, timestamp publication nor a shared
clock. No nearest-PC matching, application replay or device access is used.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import time

from .timeline_events_ascend import compiler_actors, retained_binary
from .timeline_store import bundle_path, read_artifact, export_lock, persist, json_bytes

LIMIT = 32 * 1024 * 1024
CLOCK_FILE = '__flagprism_sys_cnt_v1__'
# Actual CANN c220 vector and cube references: all X0..X31 destinations, with X32/X64
# rejection and a different constant-zero control. Retained in r030 evidence.
EXECUTABLE_TARGETS = {
    0x930000: frozenset({('dav-c220-vec', 'AIV')}),
    0x940000: frozenset({('dav-c220-cube', 'AIC'), ('dav-c220-vec', 'AIV')}),
}
WORDS = {0x02808880 | (register << 17): register for register in range(32)}


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _elf(raw):
    _need(
        type(raw) is bytes and 64 <= len(raw) <= LIMIT,
        'Invalid bounded final ELF bytes')
    _need(
        raw[:7] == b'\x7fELF\x02\x01\x01'
        and struct.unpack_from('<HH', raw, 16) == (2, 0x1029)
        and struct.unpack_from('<I', raw, 48)[0] in EXECUTABLE_TARGETS,
        'Expected an inspected c220 vector/mixed final executable')
    offset = struct.unpack_from('<Q', raw, 40)[0]
    size, count, names_index = struct.unpack_from('<HHH', raw, 58)
    _need(
        size == 64 and 0 < count <= 8192 and names_index < count
        and 64 <= offset <= len(raw) - count * size,
        'Invalid ELF section table')
    headers = [
        struct.unpack_from('<IIQQQQIIQQ', raw, offset + i * size)
        for i in range(count)
    ]

    def data(h):
        _need(h[4] <= len(raw) and h[5] <= len(raw) - h[4],
              'Truncated ELF section')
        return raw[h[4]:h[4] + h[5]]

    def string(table, index):
        _need(index < len(table), 'Invalid ELF string offset')
        end = table.find(b'\0', index)
        _need(end >= index, 'Unterminated ELF string')
        return table[index:end].decode('utf-8')

    names = data(headers[names_index])
    sections = {}
    for index, h in enumerate(headers):
        if not h[2] & 4:
            continue
        _need(h[1] == 1 and h[3] % 4 == 0 and h[5] % 4 == 0,
              'Unsupported executable section layout')
        code = data(h)
        if not code:
            continue
        _need(
            all(h[3] + h[5] <= old['address'] or old['address'] +
                len(old['data']) <= h[3]
                for old in sections.values()), 'Overlapping code extents')
        sections[index] = dict(name=string(names, h[0]),
                               address=h[3],
                               data=code)
    _need(sections, 'Final ELF lacks executable code')
    functions = {}
    for h in headers:
        if h[1] not in (2, 11):
            continue
        _need(h[6] < count and h[9] == 24 and h[5] % 24 == 0,
              'Invalid ELF symbol table')
        symbols, strings = data(h), data(headers[h[6]])
        for start in range(0, len(symbols), 24):
            name, info, _, section, value, length = struct.unpack_from(
                '<IBBHQQ', symbols, start)
            if info & 15 != 2 or section not in sections or not length:
                continue
            code = sections[section]
            _need(
                code['address'] <= value
                and length <= code['address'] + len(code['data']) - value,
                'Function exceeds executable section')
            key = string(strings, name)
            entry = (section, value, length)
            _need(key not in functions or functions[key] == entry,
                  'Ambiguous function symbol')
            functions[key] = entry
            _need(
                len(functions) <= 65536,
                'Excessive executable function symbols')
    return sections, functions


def _dwarf_rows(raw, *, marker_file=CLOCK_FILE):
    _need(type(raw) is bytes and len(raw) <= LIMIT, 'Invalid DWARF output')
    rows, files, current, units = [], {}, None, set()
    unit = None
    for line in raw.decode('utf-8').splitlines():
        match = re.fullmatch(r'debug_line\[(0x[0-9a-fA-F]+)\]', line)
        if match:
            unit = match[1]
            _need(unit not in units and len(units) < 1024,
                  'Duplicate or excessive DWARF line units')
            units.add(unit)
            files, current = {}, None
            continue
        match = re.fullmatch(r'file_names\[\s*(\d+)\]:', line)
        if match:
            current = int(match[1])
            _need(current < 8192 and current not in files,
                  'Duplicate or excessive DWARF file entry')
            files[current] = None
            continue
        match = re.fullmatch(r'\s*name: "([^"\r\n]*)"', line)
        if match and current is not None:
            _need(files[current] is None, 'Duplicate DWARF filename')
            files[current] = match[1]
            continue
        match = re.match(r'^(0x[0-9a-fA-F]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+', line)
        if not match or files.get(int(match[4])) != marker_file:
            continue
        number = int(match[2])
        # DWARF line zero explicitly has no source location. It must never
        # inherit the preceding marker's site/phase.
        if number == 0 or 'end_sequence' in line:
            continue
        _need(unit is not None and int(match[3]) == 0 and number <= 0xfffffffe,
              'Invalid clock marker row')
        _need(len(rows) < 65536, 'Excessive clock marker rows')
        rows.append(
            dict(unit=unit,
                 pc=int(match[1], 16),
                 line=number,
                 file_index=int(match[4])))
    return rows


def counter_map(*, binary, dwarf_lines, metadata):
    """Recompute facts from actual retained bytes; cached status grants nothing."""
    actors = compiler_actors(metadata)
    _need(re.fullmatch(r'Ascend910B[0-9-]*', str(metadata.get('arch', ''))),
          'No validated machine rule for this compiler architecture')
    _need(
        retained_binary(metadata) == binary,
        'Machine input differs from retained final compiler executable')
    sections, functions = _elf(binary)
    executable_jobs = EXECUTABLE_TARGETS[struct.unpack_from('<I', binary,
                                                            48)[0]]
    expected = {}
    observed_jobs = set()
    for artifact in metadata['flagprism_ascend_handoff']['artifacts']:
        manifest, job = artifact['metadata'], artifact.get('driver_job') or {}
        clock = manifest.get('dynamic_clock') or {}
        _need(
            clock.get('domain') == 'ascend.SYS_CNT'
            and type(clock.get('marker_version')) is int
            and clock['marker_version'] == 1
            and clock.get('marker_file') == CLOCK_FILE,
            'Producer lacks clock marker version 1')
        _need(
            job.get('state') == 'finished'
            and type(job.get('exit_code')) is int and job['exit_code'] == 0 and
            (job.get('target_arch'), job.get('actor_kind')) in executable_jobs
            and job.get('compile_id') == manifest['compile_id'],
            'No validated machine rule for this actual actor compiler job')
        observed_jobs.add((job['target_arch'], job['actor_kind']))
    _need(observed_jobs == executable_jobs,
          'Executable kind differs from actual actor compiler jobs')
    seen_actors = set()
    for actor in actors.values():
        identity = (actor['kind'], actor['function'])
        if identity in seen_actors:
            continue
        seen_actors.add(identity)
        _need(actor['function'] in functions,
              'Actual actor function symbol is absent')
        for sid, site in actor['sites'].items():
            marker = site.get('clock_marker') or {}
            _need(
                marker.get('version') == 1
                and type(marker.get('version')) is int
                and marker.get('file') == CLOCK_FILE
                and marker.get('status') == 'debug_locations_emitted'
                and type(marker.get('entry_line')) is int
                and type(marker.get('exit_line')) is int
                and marker['entry_line'] == 2 * sid - 1
                and marker['exit_line'] == 2 * sid,
                'Actor site lacks exact endpoint debug bindings')
            for phase, line in (('entry', 2 * sid - 1), ('exit', 2 * sid)):
                key = (actor['function'], line)
                _need(key not in expected,
                      'Ambiguous actor/site clock identity')
                expected[key] = dict(function=actor['function'],
                                     site_id=sid,
                                     backend_site_id=site['backend_identity'],
                                     phase=phase)
    planned_functions = {name: functions[name] for name, _ in expected}
    mapped, pc_bindings, covered = [], {}, set()
    for row in _dwarf_rows(dwarf_lines):
        pc = row['pc']
        candidates = [
            (name, value) for name, value in planned_functions.items()
            if (name, row['line']) in expected and value[1] <= pc and pc +
            4 <= value[1] + value[2]
        ]
        _need(
            len(candidates) == 1,
            'Clock marker has no unique planned actor function')
        name, (section, address, length) = candidates[0]
        key = (name, row['line'])
        _need(pc not in pc_bindings or pc_bindings[pc] == key,
              'One instruction aliases distinct endpoint phases')
        code = sections[section]
        _need(pc % 4 == 0, 'Unaligned clock address')
        word = struct.unpack_from('<I', code['data'], pc - code['address'])[0]
        _need(word in WORDS,
              'Debug row does not point to the reference SYS_CNT instruction')
        pc_bindings[pc] = key
        covered.add(key)
        entry = dict(expected[key],
                     pc=pc,
                     instruction_word=word,
                     register=WORDS[word],
                     section=code['name'],
                     function_start=address,
                     function_bytes=length)
        if entry not in mapped:
            mapped.append(entry)
    _need(expected and covered == set(expected),
          'Planned counter phases are missing')
    return dict(
        schema_version=1,
        model='ascend.c220.sys_cnt.dwarf.v1',
        status='counter_mapping_complete_region_unverified',
        binary_id=metadata['hash'],
        binary_sha256=_sha(binary),
        dwarf_sha256=_sha(dwarf_lines),
        architecture=metadata['arch'],
        marker_file=CLOCK_FILE,
        counter_pcs=sorted(mapped,
                           key=lambda r:
                           (r['function'], r['site_id'], r['phase'], r['pc'])),
        region_boundaries_verified=False,
        clock_unit_verified=False,
        clock_epoch_verified=False,
        record_value_provenance_verified=False)


def _tool():
    override = os.environ.get('FLAGPRISM_ASCEND_DWARFDUMP')
    if override:
        path = Path(override)
        _need(
            path.is_absolute() and path.is_file() and os.access(path, os.X_OK),
            'DWARF tool override must be an absolute executable')
        return path
    found = shutil.which('llvm-dwarfdump-15') or shutil.which('llvm-dwarfdump')
    return Path(found) if found else None


def _bound_binary(metadata):
    compiler = metadata['compiler_metadata']
    binary = retained_binary(compiler)
    snapshot = metadata.get('compiled_snapshot') or {}
    encoded = snapshot.get('binary_base64')
    _need(
        type(encoded) is str and len(encoded) <= 48 * 1024 * 1024,
        'Missing bounded loaded executable snapshot')
    executable = snapshot.get('executable') or {}
    _need(
        base64.b64decode(encoded, validate=True) == binary
        and executable.get('kind') == 'ascend.compiled_kernel'
        and executable.get('binary_id') == compiler['hash']
        and executable.get('binary_sha256') == _sha(binary),
        'Compiler image differs from actual loaded executable snapshot')
    return binary


def _run(tool, flags, directory, name, deadline, commands):
    from ._deadline import _stop_worker
    outpath, errpath = directory / (name + '.stdout'), directory / (name +
                                                                    '.stderr')
    remaining = min(20., deadline - time.monotonic())
    _need(remaining > 0, 'Clock inspection deadline exceeded')
    with outpath.open('xb') as out, errpath.open('xb') as err:
        process = subprocess.Popen([str(tool), *flags],
                                   stdout=out,
                                   stderr=err,
                                   start_new_session=True)
        fields = Path('/proc/' + str(process.pid) +
                      '/stat').read_text().rsplit(')', 1)[1].split()
        row = dict(name=name,
                   argv=[str(tool), *flags],
                   pid=process.pid,
                   pgid=int(fields[2]),
                   startticks=int(fields[19]),
                   state='running')
        commands.append(row)
        (directory / 'commands.json').write_text(json.dumps(commands,
                                                            indent=2))
        try:
            stop = time.monotonic() + remaining
            while process.poll() is None:
                _need(outpath.stat().st_size + errpath.stat().st_size <= LIMIT,
                      'DWARF output exceeds inspection budget')
                _need(time.monotonic() < stop, 'DWARF inspection timed out')
                time.sleep(.02)
            process.wait()
            _need(outpath.stat().st_size + errpath.stat().st_size <= LIMIT,
                  'DWARF output exceeds inspection budget')
            _need(process.returncode == 0, 'DWARF inspection failed')
            row['state'] = 'terminal'
        finally:
            if process.poll() is None:
                _stop_worker(process)
                row['state'] = 'stopped'
            if row['state'] == 'running':
                row['state'] = 'failed'
            row['returncode'] = process.returncode
            (directory / 'commands.json').write_text(
                json.dumps(commands, indent=2))
    return outpath.read_bytes()


def inspect_capture_binary(directory, *, metadata, deadline=None):
    """Optional default postprocessing: failures preserve the original raw data."""
    binary_id = metadata['compiler_metadata']['hash']
    _need(
        type(binary_id) is str and re.fullmatch(r'[0-9a-f]{64}', binary_id),
        'Invalid compiled binary identity')
    prefix = 'machine/' + binary_id
    target = bundle_path(directory, prefix)
    status_path = bundle_path(directory, prefix + '/status.json')
    status = dict(status='counter_mapping_unavailable',
                  binary_id=binary_id,
                  region_boundaries_verified=False)
    try:
        if status_path.exists():
            saved = json.loads(
                read_artifact(directory, prefix + '/status.json'))
            _need(
                type(saved) is dict and saved.get('binary_id') == binary_id
                and saved.get('region_boundaries_verified') is False
                and saved.get('status')
                in ('counter_mapping_unavailable',
                    'counter_mapping_complete_region_unverified'),
                'Invalid retained clock diagnostic status')
            return saved
        tool = _tool()
        _need(tool is not None, 'No llvm-dwarfdump executable is installed')
        compiler = metadata['compiler_metadata']
        binary = _bound_binary(metadata)
        # Validate ELF and producer scope before spawning a read-only tool.
        _elf(binary)
        compiler_actors(compiler)
        target.mkdir(parents=True, exist_ok=True)
        image = bundle_path(directory, prefix + '/loaded.elf')
        with export_lock(directory):
            persist(directory, prefix + '/loaded.elf', binary)
        commands = []
        stop = time.monotonic() + 20 if deadline is None else deadline
        version = _run(tool, ['--version'], target, 'version', stop, commands)
        dwarf = _run(tool, ['--debug-line', str(image)], target, 'dwarf', stop,
                     commands)
        result = counter_map(binary=binary,
                             dwarf_lines=dwarf,
                             metadata=compiler)
        result.update(tool_sha256=_sha(tool.read_bytes()),
                      tool_version_sha256=_sha(version))
        with export_lock(directory):
            persist(directory, prefix + '/counter-map.json',
                    json_bytes(result))
        status.update(status=result['status'],
                      counter_map_file=prefix + '/counter-map.json')
    except (ValueError, OSError, KeyError, TypeError, UnicodeError,
            struct.error, subprocess.SubprocessError) as error:
        status.update(reason=str(error), exception=type(error).__name__)
    target.mkdir(parents=True, exist_ok=True)
    # A corrupt existing status is an explicit optional-analysis failure. Never
    # rewrite its first bytes while trying to preserve an otherwise valid raw.
    if not status_path.exists():
        with export_lock(directory):
            persist(directory, prefix + '/status.json', json_bytes(status))
    return status


def load_counter_machine_map(directory, capture):
    """Offline revalidation never executes tools or reads the old SDK/cache."""
    metadata = capture['metadata']['compiler_metadata']
    prefix = 'machine/' + metadata['hash']
    binary = read_artifact(directory, prefix + '/loaded.elf', limit=LIMIT)
    _need(binary == _bound_binary(capture['metadata']),
          'Saved machine executable differs from this capture')
    dwarf = read_artifact(directory, prefix + '/dwarf.stdout', limit=LIMIT)
    return counter_map(binary=binary, dwarf_lines=dwarf, metadata=metadata)
