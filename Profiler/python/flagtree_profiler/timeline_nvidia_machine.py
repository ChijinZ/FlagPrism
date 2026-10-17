"""Bind compiler counter identities to actual cubin/PTX debug-line SASS.

A counter PC map is not a source-region, clock, participant or hardware-completion
certificate. All validation is explicit under -O. No application replay or guessed
nearest-clock matching is permitted.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import time

LIMIT = 32 * 1024 * 1024
MAX_CALL_REFERENCES = 65536
_MARKER = re.compile(r'flagprism_timeline_v1_site_(\d+)_(entry|exit)\s*;?\s*\Z')
_GETTER = re.compile(r'(?:@!?%[\w.$]+\s+)?mov\.(?:u64|b64)\s+[%\w.$]+,\s*%globaltimer\s*;\Z')


def _need(value, message):
    if not value:
        raise ValueError(message)


def _int(value, field, maximum=(1 << 32)-1):
    _need(type(value) is int and 0 <= value <= maximum, 'Invalid ' + field)
    return value


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _elf_section(cubin, section_name, *, executable=False):
    """Read exactly one bounded uncompressed CUDA ELF64 section."""
    _need(type(cubin) is bytes and 64 <= len(cubin) <= LIMIT, 'Invalid cubin bytes')
    _need(cubin[:7] == b'\x7fELF\x02\x01\x01', 'Expected little-endian ELF64 v1')
    _need(struct.unpack_from('<H', cubin, 18)[0] == 190, 'Expected CUDA ELF machine')
    offset = struct.unpack_from('<Q', cubin, 40)[0]
    size, count, names_index = struct.unpack_from('<HHH', cubin, 58)
    _need(size == 64 and 0 < count <= 8192 and names_index < count,
          'Unsupported ELF section table')
    _need(64 <= offset <= len(cubin)-count*size, 'Truncated ELF section table')
    headers = [struct.unpack_from('<IIQQQQIIQQ', cubin, offset+i*size)
               for i in range(count)]

    def data(header):
        start, extent = header[4:6]
        _need(header[1] != 8 and start <= len(cubin) and extent <= len(cubin)-start,
              'Invalid ELF section extent')
        return cubin[start:start+extent]

    names = data(headers[names_index])
    matches = []
    for header in headers:
        pos = header[0]
        end = names.find(b'\0', pos)
        _need(pos < len(names) and pos <= end <= pos+1024, 'Invalid ELF section name')
        if names[pos:end] == section_name.encode('utf-8'):
            _need(not header[2] & 0x800, 'Compressed ELF section is unsupported')
            _need(not executable or header[2] & 4, 'Code section is not executable')
            matches.append(data(header))
    _need(len(matches) == 1, 'Missing or ambiguous cubin section: ' + section_name)
    return matches[0]


def embedded_ptx(cubin):
    """Read the canonical uncompressed CUDA ELF64 debug-text section as bytes."""
    raw = _elf_section(cubin, '.nv_debug_ptx_txt')
    _need(raw.endswith(b'\0') and b'\n' not in raw and b'\r' not in raw,
          'Unsupported PTX debug line encoding')
    return raw


def _lex(text):
    """Remove comments/outer whitespace while preserving line numbers/strings."""
    lines, markers = [], []
    block = False
    for number, line in enumerate(text.splitlines(), 1):
        out, quote, escape, pos = [], None, False, 0
        while pos < len(line):
            char = line[pos]
            pair = line[pos:pos+2]
            if block:
                if pair == '*/':
                    block = False
                    pos += 2
                else:
                    pos += 1
                continue
            if quote:
                out.append(char)
                if escape:
                    escape = False
                elif char == '\\':
                    escape = True
                elif char == quote:
                    quote = None
                pos += 1
                continue
            if pair == '/*':
                block = True
                pos += 2
            elif pair == '//':
                annotation = line[pos+2:].strip()
                match = _MARKER.fullmatch(annotation)
                if match:
                    _need(not out, 'Counter marker must occupy a separate line')
                    markers.append((number, int(match[1]), match[2]))
                pos = len(line)
            else:
                if char in ('"', "'"):
                    quote = char
                if not char.isspace():
                    out.append(char)
                pos += 1
        _need(quote is None, 'Unterminated PTX string')
        lines.append(''.join(out))
    _need(not block, 'Unterminated PTX block comment')
    return lines, markers


def _bind_debug_lines(source, debug):
    """Accept PTXAS's erased debug metadata, preserving every instruction line.

    PTXAS retains line slots but removes .loc/.file and DWARF data declarations.
    Only those specific non-executable forms may differ, and only by becoming
    empty. Debug section braces/headers, executable tokens and line count must
    match. This does not certify the contents of source/DWARF metadata.
    """
    _need(len(source) == len(debug), 'PTX line count differs from cubin debug text')
    pending_debug, in_debug, omissions = False, False, []
    for number, (left, right) in enumerate(zip(source, debug), 1):
        if re.fullmatch(r'\.section\.debug_[a-zA-Z0-9_.]+', left):
            _need(not pending_debug and not in_debug, 'Nested PTX debug section')
            pending_debug = True
        elif left == '{' and pending_debug:
            pending_debug, in_debug = False, True
        elif left == '}' and in_debug:
            in_debug = False
        elif left and pending_debug:
            raise ValueError('Invalid PTX debug section opening')
        if left == right:
            continue
        kind = None
        if re.fullmatch(r'\.loc[0-9]+', left):
            kind = 'location_directive'
        elif re.fullmatch(r'\.file[0-9]+"(?:[^"\\]|\\.)*"', left):
            kind = 'file_directive'
        elif in_debug and re.fullmatch(r'\.b(?:8|16|32|64)(?:-?[0-9]+|\.debug_[a-zA-Z0-9_.]+)', left):
            kind = 'dwarf_data'
        _need(right == '' and kind is not None,
              'PTX executable tokens/line numbers differ from cubin debug text')
        omissions.append(dict(line=number, kind=kind))
    _need(not pending_debug and not in_debug, 'Unterminated PTX debug section')
    return omissions


def counter_map(*, cubin, ptx, sass_lines, sass_json, binary_id, scope_ids,
                expected_sm, marker_version=1):
    """Pure bounded validation, binding input hashes and every actual getter PC."""
    _need(type(marker_version) is int and marker_version == 1, 'Unknown marker version')
    _need(type(binary_id) is str and re.fullmatch(r'[0-9a-f]{64}', binary_id),
          'Invalid actual binary identity')
    _need(type(scope_ids) is tuple and scope_ids and len(scope_ids) <= 128,
          'Invalid selected scope identities')
    for site in scope_ids:
        _int(site, 'scope id', 0x7fffffff)
    _need(len(set(scope_ids)) == len(scope_ids), 'Duplicate selected scope identity')
    _need(type(expected_sm) is tuple and len(expected_sm) == 2, 'Missing target SM')
    for value in expected_sm:
        _int(value, 'SM component', 99)
    for label, value in [('PTX', ptx), ('SASS lines', sass_lines), ('SASS JSON', sass_json)]:
        _need(type(value) is bytes and 0 < len(value) <= LIMIT, 'Invalid ' + label)
    raw_debug = embedded_ptx(cubin)
    # PTXAS removes comments but retains their blank lines. Comparing all actual
    # per-line tokens binds raw annotations to the debug table inside this cubin.
    source_lines, annotations = _lex(ptx.decode('utf-8'))
    debug_text = '\n'.join(raw_debug.decode('utf-8').split('\0')[:-1])
    debug_lines, _ = _lex(debug_text)
    debug_omissions = _bind_debug_lines(source_lines, debug_lines)
    sites = set(scope_ids)
    by_line, pending = {}, None
    marker_lines = {number: (site, phase) for number, site, phase in annotations}
    _need(len(marker_lines) == len(annotations), 'Duplicate marker line')
    for number, line in enumerate(ptx.decode('utf-8').splitlines(), 1):
        if number in marker_lines:
            _need(pending is None, 'Marker has no corresponding getter')
            site, phase = marker_lines[number]
            _need(site in sites, 'Marker refers to an unknown scope')
            pending = (site, phase, number)
        tokens = source_lines[number-1]
        if '%globaltimer' in tokens:
            # Reconstruct normal spaces only for lexical instruction validation.
            clean = re.sub(r'//.*$', '', line).strip()
            _need(_GETTER.fullmatch(clean) and pending is not None,
                  'Unmarked or non-64-bit globaltimer getter')
            site, phase, annotation_line = pending
            by_line[number] = dict(site_id=site, phase=phase,
                ptx_line=number, annotation_line=annotation_line,
                ptx_collection_predicate=(clean.split()[0] if clean.startswith('@') else None))
            pending = None
    _need(pending is None and by_line, 'Missing marked globaltimer getter')
    _need({(v['site_id'], v['phase']) for v in by_line.values()} ==
          {(s, p) for s in sites for p in ('entry', 'exit')}, 'Missing scope phase')
    doc = json.loads(sass_json)
    _need(type(doc) is list and len(doc) == 2 and type(doc[0]) is dict and
          type(doc[1]) is list and doc[1], 'Unsupported nvdisasm JSON')
    meta, functions = doc
    version = meta.get('SchemaVersion')
    _need(type(version) is dict and all(type(v) is int for v in version.values()),
          'Invalid nvdisasm schema version types')
    sm = meta.get('SM', {}).get('version')
    _need(type(sm) is dict and all(type(v) is int for v in sm.values()),
          'Invalid nvdisasm target types')
    _need(meta.get('SchemaVersion') == {'major': 13, 'minor': 2, 'revision': 0},
          'Unsupported nvdisasm schema version')
    _need(meta.get('SM', {}).get('version') ==
          {'major': expected_sm[0], 'minor': expected_sm[1]}, 'Actual SM mismatch')
    instructions, ranges = {}, {}
    for function in functions:
        _need(type(function) is dict, 'Invalid function descriptor')
        name = function.get('function-name')
        body = function.get('sass-instructions')
        _need(type(name) is str and name and name not in instructions and
              type(body) is list and body, 'Invalid or duplicate function')
        start = _int(function.get('start'), 'function start', LIMIT)
        extent = _int(function.get('length'), 'function length', LIMIT)
        _need(start % 16 == 0 and extent % 16 == 0 and extent >= len(body)*16,
              'Unsupported function offsets or instruction stride')
        # A root's declared extent may include explicitly named child functions.
        # Its actual instruction body must never absorb those child bodies.
        instructions[name] = {start+i*16: instruction for i, instruction in enumerate(body)}
        ranges[name] = dict(function=name, start=start, declared_length=extent,
                            instruction_bytes=len(body)*16)
    function, ptx_line, pcs, seen = None, None, [], set()
    current_section, function_sections, section_bytes = None, {}, {}
    calls, synchronization = [], []
    for line in sass_lines.decode('utf-8').splitlines():
        section = re.match(r'^\s*\.section\s+([^,\s]+)', line)
        if section:
            name = section[1]
            current_section = name if name.startswith('.text.') else None
            function = name[6:] if current_section else None
            ptx_line = None
        # nvdisasm prints nested device functions within their parent's .text
        # section. Only an explicit exact function symbol may switch identity.
        label = re.fullmatch(r'\s*([^\s:]+):\s*', line)
        if label and label[1] in instructions:
            _need(current_section is not None, 'Function symbol outside code section')
            function, ptx_line = label[1], None
        match = re.match(r'\s*//## File "\.nv_debug_ptx_txt", line (\d+)\s*$', line)
        if match:
            ptx_line = int(match[1])
        instruction = re.match(r'\s*/\*([0-9a-fA-F]+)\*/\s*(.*?)\s*;\s*$', line)
        if not instruction or function is None:
            continue
        pc = int(instruction[1], 16)
        _need(current_section is not None, 'Instruction outside code section')
        if current_section not in section_bytes:
            section_bytes[current_section] = _elf_section(cubin, current_section, executable=True)
        _need(function in instructions, 'Unknown disassembled function')
        previous_section = function_sections.setdefault(function, current_section)
        _need(previous_section == current_section, 'Function occurs in multiple code sections')
        limits = ranges[function]
        _need(limits['start'] + limits['declared_length'] <= len(section_bytes[current_section]),
              'Function extent exceeds actual code section')
        _need(function in instructions and pc in instructions[function],
              'SASS line PC absent from actual JSON')
        key = (function, pc)
        _need(key not in seen, 'Duplicate disassembled PC')
        seen.add(key)
        actual = instructions[function][pc]
        _need(type(actual) is dict, 'Invalid JSON instruction')
        text = instruction[2]
        parts = text.split(None, 1)
        predicate = parts.pop(0) if parts and parts[0].startswith('@') else None
        opcode = (parts[0].split(None, 1)[0] if parts else None)
        _need(opcode == actual.get('opcode') and predicate == actual.get('predicate'),
              'Text/JSON instruction mismatch')
        operands = actual.get('operands', '')
        _need(type(operands) is str, 'Invalid JSON instruction operands')
        without_predicate = text.split(None, 1)[1] if predicate else text
        fields = without_predicate.split(None, 1)
        text_operands = fields[1] if len(fields) == 2 else ''
        position = dict(function=function, section=current_section, pc=pc,
                        relative_pc=pc-ranges[function]['start'],
                        opcode=opcode, predicate=predicate)
        if opcode.startswith('CALL'):
            # nvdisasm JSON names a direct callee without the text's `(symbol).
            # Indirect/unknown calls are retained, not guessed from a prefix.
            target = re.fullmatch(r'`\(([^()\s]+)\)', text_operands.strip())
            callee = target[1] if target else None
            if callee is not None:
                _need(callee == operands, 'Text/JSON direct call target mismatch')
            elif operands in instructions:
                raise ValueError('Known direct call lacks an explicit text target')
            calls.append(dict(position, callee=callee, operands=operands,
                              target_status=('resolved' if callee in instructions
                                             else 'unresolved')))
        if opcode.startswith(('BAR.', 'MEMBAR', 'DEPBAR', 'LDGDEPBAR', 'WARPSYNC')):
            _need(re.sub(r'\s+', '', text_operands) == re.sub(r'\s+', '', operands),
                  'Text/JSON synchronization operands mismatch')
            synchronization.append(dict(position, operands=operands))
        is_timer = 'SR_GLOBALTIMER' in operands
        _need(is_timer == ('SR_GLOBALTIMER' in text), 'Text/JSON getter mismatch')
        if not is_timer:
            continue
        without_predicate = text.split(None, 1)[1] if predicate else text
        operands = without_predicate.split(None, 1)[1]
        _need(re.sub(r'\s+', '', operands) == re.sub(r'\s+', '', actual['operands']),
              'Text/JSON getter operands mismatch')
        _need(opcode == 'CS2R' and 'SR_GLOBALTIMERLO' in actual.get('operands', '') and
              ptx_line in by_line, 'Unmapped actual globaltimer read')
        pcs.append(dict(by_line[ptx_line], function=function, pc=pc,
                        section=current_section, function_start=ranges[function]['start'],
                        relative_pc=pc-ranges[function]['start'],
                        sass_predicate=predicate, opcode=opcode,
                        operands=actual['operands']))
    _need(seen == {(f, pc) for f, body in instructions.items() for pc in body},
          'Incomplete disassembly text coverage')
    _need({p['ptx_line'] for p in pcs} == set(by_line), 'Getter eliminated or lost debug mapping')
    occupied = set()
    for name, body in instructions.items():
        section = function_sections[name]
        ranges[name]['section'] = section
        for pc in body:
            key = (section, pc)
            _need(key not in occupied, 'Overlapping function instruction bodies')
            occupied.add(key)
    _need(pcs, 'No actual mapped counter PCs')
    # Bind a read to all of its exact direct call sites. A callee can contain
    # multiple reads and a read can have multiple callers; neither is collapsed.
    counter_calls, callers = [], {}
    for call in calls:
        if call['target_status'] == 'resolved':
            callers.setdefault(call['callee'], []).append(call)
    reference_count = 0
    for counter in pcs:
        direct = callers.get(counter['function'], ())
        reference_count += len(direct)
        _need(reference_count <= MAX_CALL_REFERENCES, 'Counter call reference budget exceeded')
        references = [dict(call) for call in direct]
        counter_calls.append(dict(function=counter['function'], pc=counter['pc'],
                                  site_id=counter['site_id'], phase=counter['phase'],
                                  direct_call_sites=references))
    return dict(schema_version=1, static_model_version=1,
        status='counter_mapping_complete_region_unverified',
        binary_id=binary_id, marker_version=1, expected_sm=list(expected_sm),
        artifacts={'cubin_sha256': _sha(cubin), 'ptx_sha256': _sha(ptx),
            'embedded_ptx_sha256': _sha(raw_debug), 'sass_lines_sha256': _sha(sass_lines),
            'sass_json_sha256': _sha(sass_json)}, counter_pcs=pcs,
        ptx_debug_omissions=debug_omissions, function_ranges=list(ranges.values()),
        call_sites=calls, counter_call_sites=counter_calls,
        synchronization_sites=synchronization,
        region_boundaries_verified=False, clock_qualified=False,
        notes=['Static counter PCs are not exact dynamic PC attribution when code is duplicated.',
               'PTX collection predication does not prove SASS read suppression.',
               'Source-region, participation and completion proofs remain separate.'])


def find_nvdisasm():
    explicit = os.environ.get('FLAGTREE_NVDISASM')
    if explicit:
        path = Path(explicit)
        _need(path.is_absolute() and path.is_file() and os.access(path, os.X_OK),
              'FLAGTREE_NVDISASM must name an executable absolute path')
        return path
    packaged = Path(sys.prefix)/'lib'/('python'+str(sys.version_info.major)+'.'+str(sys.version_info.minor))/'site-packages/nvidia/cu13/bin/nvdisasm'
    if packaged.is_file() and os.access(packaged, os.X_OK):
        return packaged
    found = shutil.which('nvdisasm')
    return Path(found) if found else None


def _run_tool(tool, flags, directory, name, deadline, commands):
    from ._deadline import _stop_worker
    path = directory/(name+'.stdout')
    error_path = directory/(name+'.stderr')
    remaining = min(20.0, deadline-time.monotonic())
    _need(remaining > 0, 'Machine inspection export deadline exceeded')
    argv = [str(tool), *flags]
    started = time.monotonic_ns()
    with path.open('xb') as out, error_path.open('xb') as err:
        process = subprocess.Popen(argv, stdout=out, stderr=err, start_new_session=True)
        fields = Path('/proc/'+str(process.pid)+'/stat').read_text().rsplit(')', 1)[1].split()
        receipt = dict(name=name, argv=argv, pid=process.pid, pgid=int(fields[2]),
            startticks=int(fields[19]), timeout_seconds=remaining, state='running')
        commands.append(receipt)
        (directory/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        try:
            stop = time.monotonic()+remaining
            while process.poll() is None:
                _need(path.stat().st_size+error_path.stat().st_size <= LIMIT,
                      'nvdisasm exceeded output budget')
                _need(time.monotonic() < stop, 'nvdisasm command timed out')
                time.sleep(0.02)
            process.wait()
            _need(path.stat().st_size+error_path.stat().st_size <= LIMIT,
                  'nvdisasm exceeded output budget')
            _need(process.returncode == 0, 'nvdisasm command failed: '+name)
            receipt['state'] = 'terminal'
        finally:
            if process.poll() is None:
                _stop_worker(process)
                receipt['state'] = 'stopped'
            if receipt['state'] == 'running':
                receipt['state'] = 'failed'
            receipt.update(returncode=process.returncode, wall_ns=time.monotonic_ns()-started)
            (directory/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    return path.read_bytes()


def inspect_capture_binary(directory, *, metadata, plan, deadline=None):
    """Optional postprocessing. Preserve raw captures if the tool is unavailable."""
    try:
        tool = find_nvdisasm()
    except ValueError as error:
        return {'status': 'unavailable_tool_invalid', 'reason': str(error),
                'region_boundaries_verified': False}
    if tool is None:
        return {'status': 'unavailable_tool_missing', 'region_boundaries_verified': False}
    binary = metadata['binary_id']
    _need(type(binary) is str and re.fullmatch(r'[0-9a-f]{64}', binary), 'Invalid binary identity')
    prefix = Path('machine')/binary
    target = Path(directory)/prefix
    # A retry reuses the exact durable diagnostic instead of invoking the tool
    # again or replacing an earlier failure. It never reruns user math.
    if (target/'status.json').exists():
        return json.loads((target/'status.json').read_text())
    target.mkdir(parents=True, exist_ok=True)
    status = {'status': 'counter_mapping_unavailable', 'binary_id': binary,
              'region_boundaries_verified': False}
    try:
        artifacts = metadata['timeline_artifacts']
        def artifact(suffix):
            rows = [r for r in artifacts if r['retained_file'].endswith(suffix)]
            _need(len(rows) == 1, 'Missing or ambiguous machine artifact: '+suffix)
            row = rows[0]
            raw = (Path(directory)/row['retained_file']).read_bytes()
            _need(_sha(raw) == row['sha256'], 'Retained machine artifact changed')
            return row, raw
        cubin_row, cubin = artifact('.cubin')
        _, ptx = artifact('.ptx')
        output = {}
        commands = [('version', ['--version']),
                    ('lines', ['--print-code', '--print-line-info-ptx', str(Path(directory)/cubin_row['retained_file'])]),
                    ('json', ['--emit-json', str(Path(directory)/cubin_row['retained_file'])])]
        tool_hash = _sha(tool.read_bytes())
        receipts = []
        deadline = time.monotonic()+20 if deadline is None else deadline
        for name, flags in commands:
            output[name] = _run_tool(tool, flags, target, name, deadline, receipts)
        target_info = metadata['compiler_metadata']['target']
        arch = _int(target_info['arch'], 'compiler target', 9999)
        _need(target_info['backend'] == 'cuda', 'Wrong compiler target backend')
        proof = counter_map(cubin=cubin, ptx=ptx, sass_lines=output['lines'],
            sass_json=output['json'], binary_id=binary,
            scope_ids=tuple(int(k) for k, _ in metadata['scope_id_names']),
            expected_sm=(arch//10, arch % 10), marker_version=plan.get('timeline_marker_version'))
        proof.update(tool_sha256=tool_hash, tool_path=str(tool),
                     tool_version_sha256=_sha(output['version']))
        (target/'counter-map.json').write_text(json.dumps(proof, indent=2)+'\n')
        status.update(status=proof['status'], counter_map_file=str(prefix/'counter-map.json'))
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, subprocess.SubprocessError) as error:
        status.update(reason=str(error), exception=type(error).__name__)
    (target/'status.json').write_text(json.dumps(status, indent=2)+'\n')
    return status
