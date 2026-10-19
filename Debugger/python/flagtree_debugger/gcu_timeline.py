"""Late GCU recorder bridge; the native tool consumes actual SDK execution IR."""
import hashlib
import json
import struct
from pathlib import Path
import subprocess
import tempfile
import threading

_hash_cache = {}
_hash_lock = threading.Lock()


def _file_hash(path):
    path = path.resolve(strict=True)

    def stamp():
        value = path.stat()
        return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns

    with _hash_lock:
        before = stamp()
        saved = _hash_cache.get(path)
        if saved is not None and saved[0] == before:
            return saved[1]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if stamp() != before:
            raise RuntimeError("Compiler/SDK input changed while hashing: " +
                               str(path))
        _hash_cache[path] = before, digest
        return digest


def packaged_tool():
    return Path(__file__).with_name('_bin') / 'gcu-timeline'


def tool_identity():
    """Bind the tool, bridge, compiler and SDK before timeline cache lookup."""
    from triton._C import libtriton
    from .gcu_clock import IDENTITY_SOURCE
    paths = [
        packaged_tool(),
        Path(__file__),
        Path(__file__).with_name('compiler.py'),
        Path(__file__).with_name('gcu_clock.py'),
        Path(libtriton.__file__),
        Path('/opt/tops/bin/opt'),
        Path('/opt/triton_gcu/bin/gcu-compiler-opt'),
        Path('/opt/triton_gcu/bin/gcu-compiler-compile'),
        Path('/opt/tops/llvm11/lib/krt/gcu300_api_profile.bc')
    ]
    from importlib.util import find_spec
    backend = Path(find_spec('triton.backends.enflame').origin).parent
    paths.extend(backend / name
                 for name in ('compiler.py', 'driver.py', 'triton-gcu300-opt'))
    paths.extend(backend.glob('_triton_gcu300*.so'))
    paths.extend(backend.glob('libtriton_gcu300*.so'))
    files = {str(path.resolve()): _file_hash(path) for path in paths}
    return dict(version=2,
                files=files,
                clock_helper_source_sha256=hashlib.sha256(
                    IDENTITY_SOURCE.encode()).hexdigest())


def prepare_ttir(module, metadata, request, binding):
    from triton._C.libtriton import ir, passes
    from .compiler import _run_pass_manager
    from .native import runtime_binding
    # GCU's generic GPUTarget arch is the driver's architecture label. The
    # SDK execution pipeline is selected by the resolved GCUOptions.arch,
    # which Triton copies into compilation metadata before this callback.
    if metadata.get('arch') != 'gcu300':
        raise ValueError(
            'Late GCU timeline currently requires the actual gcu300 target')
    if getattr(runtime_binding(), 'GCU_EXECUTION_TIMELINE_VERSION', None) != 1:
        raise RuntimeError(
            'Late GCU timeline requires its matching runtime and packaged native tool'
        )
    if (request.get('semantics') != ['source_control_interval']
            or request.get('programs') is not None
            or request.get('sample_every') != 1
            or request.get('automatic') is not True
            or type(request.get('max_events_per_instance')) is not int):
        raise ValueError(
            'Late GCU timeline requires automatic unsampled first/last selection'
        )
    identity = tool_identity()
    mode = metadata.get('instrumentation_mode', '')
    frozen = json.loads(mode.split('|config=',
                                   1)[1]).get('debug_gcu_execution_identity')
    if frozen != identity:
        raise RuntimeError(
            'GCU execution recorder changed after compile option freezing')
    manager = ir.pass_manager(module.context)
    passes.common.add_inliner(manager)
    passes.common.add_symbol_dce(manager)
    binding.add_resolve_debug_scope(manager)
    binding.add_assign_debug_op_id(manager)
    _run_pass_manager(manager, module, 'FlagPrism GCU timeline preparation')
    metadata['debug_metadata_json'] = binding.get_debug_kernel_metadata_json(
        module)
    metadata['debug_tracked_table'] = json.loads(
        binding.get_debug_tracked_op_table_json(module))
    metadata['debug_kernel_id'] = binding.get_debug_kernel_id(module)
    hidden = binding.prepare_late_observation_abi(module)
    # A bounded on-chip ring replaces mid-kernel publication. The user-requested
    # maximum is an upper bound; loss is reported if the selected stream fills.
    capacity = min(request['max_events_per_instance'], 512)
    if capacity < 1:
        raise ValueError('GCU execution capacity must be positive')
    metadata.update(debug_launch_hidden_arg=True,
                    debug_protocol_version=2,
                    debug_record_level=1,
                    debug_record_size=128,
                    debug_record_layout='gcu_execution_timeline_v3',
                    debug_records_per_instance=0,
                    debug_record_capacity=capacity,
                    debug_record_plan=[],
                    debug_export_mode='POST_KERNEL_EXPORT',
                    debug_dynamic_storage_version=3,
                    debug_dynamic_publisher_version=3,
                    debug_dynamic_index_bits=32,
                    debug_dynamic_program_policy='runtime_first_last',
                    debug_dynamic_selected_actor=0,
                    debug_dynamic_sample_every=1,
                    debug_dynamic_slot_bytes=32 + capacity * 128,
                    debug_clock_carrier='llvm_i64_words',
                    debug_clock_domain='enflame.sdk.global_timer',
                    debug_clock_bits=46,
                    debug_clock_unit='tick',
                    debug_clock_identity_version=1,
                    debug_clock_identity_primitive='llvm.dtu.movs.sipinfo',
                    debug_execution_version=1,
                    debug_execution_hidden_argument=int(hidden),
                    debug_execution_max_sites=request["max_sites"],
                    debug_execution_tool_identity=identity)


def rewrite_execution_ir(text, metadata):
    if metadata.get('debug_execution_version') != 1:
        return text
    expected = metadata['debug_execution_tool_identity']
    if tool_identity() != expected:
        raise RuntimeError(
            'Late GCU recorder changed before execution IR rewriting')
    if not isinstance(text, str) or len(text.encode()) > 16 * 1024 * 1024:
        raise ValueError('GCU execution IR exceeds its budget')
    # Keep failed inputs and native diagnostics. Offline export uses the
    # retained bundle copies, never these live compilation directories.
    root = Path(tempfile.mkdtemp(prefix='flagprism-gcu-execution-'))
    source = root / 'input.mlir'
    output = root / 'output.mlir'
    manifest = root / 'manifest.json'
    source.write_text(text)
    command = [
        str(packaged_tool()),
        str(source),
        str(output),
        str(manifest),
        str(metadata['debug_execution_hidden_argument']),
        str(metadata['debug_record_capacity']),
        str(metadata['debug_execution_max_sites'])
    ]
    with (root / 'stdout').open('wb') as out, (root /
                                               'stderr').open('wb') as err:
        child = subprocess.Popen(command,
                                 stdout=out,
                                 stderr=err,
                                 start_new_session=True)
        stat = Path('/proc') / str(child.pid) / 'stat'
        fields = stat.read_text().rsplit(')', 1)[1].split()
        receipt = dict(pid=child.pid,
                       pgid=int(fields[2]),
                       startticks=int(fields[19]),
                       argv=command,
                       tool_identity=expected,
                       source_sha256=hashlib.sha256(text.encode()).hexdigest())
        (root / 'launch.json').write_text(json.dumps(receipt, indent=2))
        try:
            result = child.wait(timeout=30)
        except BaseException:
            child.kill()
            child.wait()
            (root / 'terminal.json').write_text(
                json.dumps(dict(receipt,
                                state='failed_or_timed_out',
                                returncode=child.returncode),
                           indent=2))
            raise
    receipt.update(state='terminal', returncode=result)
    (root / 'terminal.json').write_text(json.dumps(receipt, indent=2))
    if result:
        raise RuntimeError('Late GCU execution rewrite failed; retained at ' +
                           str(root) + ': ' +
                           (root / 'stderr').read_text()[-8192:])
    if output.stat().st_size > 16 * 1024 * 1024 or manifest.stat(
    ).st_size > 8 * 1024 * 1024:
        raise ValueError(
            'Late GCU recorder output exceeds its budget; retained at ' +
            str(root))
    rewritten = output.read_text()
    plan = json.loads(manifest.read_text())
    if (plan.get('schema_version') != 1
            or plan.get('record_layout') != 'gcu_execution_timeline_v3'
            or plan.get('hidden_argument_index')
            != metadata['debug_execution_hidden_argument']
            or plan.get('capacity') != metadata['debug_record_capacity']
            or plan.get('record_size') != 128
            or plan.get('slot_bytes') != metadata['debug_dynamic_slot_bytes']):
        raise ValueError(
            'Native execution manifest contradicts the prepared ABI')
    if tool_identity() != expected:
        raise RuntimeError(
            'GCU recorder/compiler/SDK changed during rewriting; retained at '
            + str(root))
    metadata['debug_execution_source_tracked_table'] = metadata.get(
        'debug_tracked_table', [])
    metadata['debug_tracked_table'] = [
        dict(opId=site['id'],
             scopeId=1,
             mlirOpName=site['operation'],
             sourceLoc=site['location'],
             recordLevel=1,
             addrLevel=0) for site in plan['sites']
    ]
    metadata.update(debug_execution_manifest=plan,
                    debug_execution_input_ir=text,
                    debug_execution_rewrite_receipt=receipt,
                    debug_execution_input_sha256=hashlib.sha256(
                        text.encode()).hexdigest(),
                    debug_execution_output_sha256=hashlib.sha256(
                        rewritten.encode()).hexdigest())
    return rewritten


def _native_file_stage(data, metadata, mode, root):
    """Run the packaged child on one immutable, bounded input snapshot."""
    expected = metadata['debug_execution_tool_identity']
    if tool_identity() != expected:
        raise RuntimeError('GCU toolchain changed before native inspection')
    if type(data) is not bytes or len(data) > 16 * 1024 * 1024:
        raise ValueError('GCU native inspection input exceeds its budget')
    native = mode == '--native-locations'
    source = root / ('input.elf' if native else 'input.mlir')
    output = root / ('output.json' if native else 'output.mlir')
    source.write_bytes(data)
    command = [str(packaged_tool()), mode, str(source), str(output)]
    with (root / 'stdout').open('wb') as out, (root /
                                               'stderr').open('wb') as err:
        child = subprocess.Popen(command,
                                 stdin=subprocess.DEVNULL,
                                 stdout=out,
                                 stderr=err,
                                 start_new_session=True)
        receipt = dict(pid=child.pid,
                       argv=command,
                       tool_identity=expected,
                       source_sha256=hashlib.sha256(data).hexdigest(),
                       input_kind='ELF' if native else 'LLVM_MLIR')
        try:
            # The packaged native helper has no subprocesses. Always reap it,
            # including errors while recording ownership or writing receipts.
            fields = (Path('/proc') / str(child.pid) /
                      'stat').read_text().rsplit(')', 1)[1].split()
            receipt.update(pgid=int(fields[2]), startticks=int(fields[19]))
            (root / 'launch.json').write_text(json.dumps(receipt, indent=2))
            result = child.wait(timeout=30)
        except BaseException:
            child.kill()
            child.wait()
            receipt.update(state='failed_or_timed_out',
                           returncode=child.returncode)
            (root / 'terminal.json').write_text(json.dumps(receipt, indent=2))
            raise
    receipt.update(state='terminal', returncode=result)
    (root / 'terminal.json').write_text(json.dumps(receipt, indent=2))
    if result:
        raise RuntimeError('GCU native inspection failed; retained at ' +
                           str(root) + ': ' +
                           (root / 'stderr').read_text()[-8192:])
    if not output.is_file() or output.stat().st_size > 16 * 1024 * 1024:
        raise ValueError(
            'GCU native inspection output is missing/oversized: ' + str(root))
    if source.read_bytes() != data or tool_identity() != expected:
        raise RuntimeError(
            'GCU native inspection inputs changed; retained at ' + str(root))
    return output.read_bytes(), receipt


def preserve_native_locations(text, metadata):
    """Add DI scopes; the caller must use the real SDK verifier before codegen."""
    if metadata.get('debug_execution_version') != 1:
        return text
    if not isinstance(text, str):
        raise ValueError('GCU debug scopes require serialized LLVM MLIR')
    source_bytes = text.encode()
    root = Path(tempfile.mkdtemp(prefix='flagprism-gcu-debug-scopes-'))
    scoped, receipt = _native_file_stage(source_bytes, metadata,
                                         '--debug-scopes', root)
    metadata.update(debug_execution_native_marker_version=1,
                    debug_execution_native_scope_receipt=receipt,
                    debug_execution_native_scope_input_sha256=hashlib.sha256(
                        source_bytes).hexdigest(),
                    debug_execution_native_scope_output_sha256=hashlib.sha256(
                        scoped).hexdigest())
    return scoped.decode()


def _gcu300_bundle_image(binary):
    """Extract the unique current SDK GCU300 image with checked byte extents."""
    magic = b'__CLANG_OFFLOAD_BUNDLE__'
    if not binary.startswith(magic) or len(binary) < len(magic) + 8:
        raise ValueError('Unknown GCU native bundle format')
    count, = struct.unpack_from('<Q', binary, len(magic))
    if not 0 < count <= 32:
        raise ValueError('Invalid GCU native bundle image count')
    cursor, images = len(magic) + 8, []
    for _ in range(count):
        if cursor + 24 > len(binary):
            raise ValueError('Truncated GCU bundle header')
        offset, size, length = struct.unpack_from('<QQQ', binary, cursor)
        cursor += 24
        if length > 1024 or cursor + length > len(
                binary) or offset + size > len(binary):
            raise ValueError('Invalid GCU bundle byte extent')
        target = binary[cursor:cursor + length].decode()
        cursor += length
        if size:
            images.append((offset, size, target))
    end = cursor
    for offset, size, _ in sorted(images):
        if offset < end:
            raise ValueError('Overlapping GCU bundle header/images')
        end = offset + size
    selected = [(offset, size, target) for offset, size, target in images
                if target == 'tops-dtu-enflame-tops--gcu300']
    if len(selected) != 1:
        raise ValueError('Missing or ambiguous GCU300 native image')
    offset, size, target = selected[0]
    return binary[offset:offset + size], target


def bind_native_clock_locations(binary, metadata):
    """Keep final ELF site/phase rows automatically; no new timing rights."""
    if metadata.get('debug_execution_version') != 1:
        return
    if not isinstance(binary,
                      (bytes, bytearray)) or len(binary) > 64 * 1024 * 1024:
        raise ValueError('GCU executable inspection exceeds its budget')
    binary = bytes(binary)
    root = Path(tempfile.mkdtemp(prefix='flagprism-gcu-native-locations-'))
    (root / 'input.fatbin').write_bytes(binary)
    try:
        elf, target = _gcu300_bundle_image(binary)
        output, receipt = _native_file_stage(elf, metadata,
                                             '--native-locations', root)
        report = json.loads(output)
        if (type(report) is not dict
                or type(report.get('schema_version')) is not int
                or report['schema_version'] != 1 or report.get('status')
                not in ('compiler_locations_mapped', 'unavailable')
                or report.get('semantics') != 'compiler_debug_location_rows'
                or report.get('marker_file') != '__flagprism_gcu_clock_v1__'
                or any(
                    report.get(k) is not False
                    for k in ('source_region_qualified',
                              'reader_valueflow_qualified',
                              'hardware_busy_qualified'))
                or type(report.get('locations')) is not list):
            raise ValueError('Invalid GCU native location report')
        sites = {
            s['id']
            for s in metadata['debug_execution_manifest']['sites']
        }
        phases = ('begin_counter', 'end_counter', 'begin_identity',
                  'end_identity')
        present = set()
        for point in report['locations']:
            site, column = point.get('site_id'), point.get('column')
            if (type(site) is not int or site not in sites
                    or type(column) is not int or not 1 <= column <= 4
                    or point.get('phase') != phases[column - 1]
                    or type(point.get('address')) is not int
                    or point['address'] < 0
                    or type(point.get('section_offset')) is not int
                    or point['section_offset'] < 0):
                raise ValueError(
                    'Native location does not match the generated execution manifest'
                )
            present.add((site, column))
        missing = [
            dict(site_id=site,
                 columns=[c for c in range(1, 5) if (site, c) not in present])
            for site in sorted(sites)
            if any((site, c) not in present for c in range(1, 5))
        ]
        metadata.update(
            debug_execution_native_locations=dict(
                schema_version=1,
                coordinate_system='ELF_sectioned_code_address',
                fatbin_sha256=hashlib.sha256(binary).hexdigest(),
                elf_sha256=hashlib.sha256(elf).hexdigest(),
                target=target,
                report=report,
                missing_phase_locations=missing),
            debug_execution_native_locations_receipt=receipt,
            debug_execution_native_locations_output_sha256=hashlib.sha256(
                output).hexdigest())
    except Exception as error:
        raise RuntimeError('GCU native location binding failed; retained at ' +
                           str(root)) from error
