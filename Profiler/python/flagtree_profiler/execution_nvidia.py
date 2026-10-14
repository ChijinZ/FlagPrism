"""Static NVIDIA organization from emitted compiler artifacts.

Layout attributes describe register/lane/warp organization. They do not prove
source identity, active lane masks, physical memory traffic, or dynamic timing.
"""
from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping

_LAYOUT = re.compile(r'^(#[\w.$]+)\s*=\s*#(?:ttg|triton_gpu)\.(blocked|nvidia_mma|slice|dot_op|linear|shared|swizzled_shared|nvmma_shared)<(.+)>\s*$', re.M)
_OPCODE = re.compile(r'(?:^|=\s*)(?:"([\w.]+)"|((?:tt|ttg|ttng|proton|proton_gpu)\.[\w.]+))(?=\s|\()')


def _array(text, key):
    match = re.search(r'\b' + re.escape(key) + r'\s*=\s*\[([^]]*)\]', text)
    if not match:
        return None
    tokens = [item.strip() for item in match[1].split(',')]
    return [int(item) for item in tokens] if tokens and all(re.fullmatch(r'\d+', item) for item in tokens) else None


def _integer(text, key):
    match = re.search(r'\b' + re.escape(key) + r'\s*=\s*(\d+)', text)
    return int(match[1]) if match else None


def _source_ids(source_operations):
    if isinstance(source_operations, Mapping):
        return set(source_operations)
    return {item if isinstance(item, str) else item.get('id')
            for item in (source_operations or ()) if isinstance(item, (str, Mapping))}


def build_execution_mapping(asm: Mapping, compiler_metadata: Mapping, *, binary_id=None, source_operations=None):
    """Accept CompiledKernel.asm and retain conservative partial mappings."""
    artifacts = {key: text for key, text in asm.items()
                 if key in {'ttir', 'ttgir', 'llir', 'ptx'} and isinstance(text, str)}
    evidence = {key: {'sha256': hashlib.sha256(text.encode()).hexdigest(), 'bytes': len(text.encode())}
                for key, text in artifacts.items()}
    text = artifacts.get('ttgir', '')
    layouts = []
    for match in _LAYOUT.finditer(text):
        name, kind, body = match.groups()
        layout = {'id': name, 'kind': kind, 'evidence': match[0], 'basis': 'emitted_ttgir_attribute', 'status': 'partial'}
        if kind == 'blocked':
            for key in ('sizePerThread', 'threadsPerWarp', 'warpsPerCTA', 'order'):
                layout[key] = _array(body, key)
            size, threads, warps, order = [layout[key] for key in ('sizePerThread', 'threadsPerWarp', 'warpsPerCTA', 'order')]
            if all(value is not None for value in (size, threads, warps, order)) and len(size) == len(threads) == len(warps) == len(order) and sorted(order) == list(range(len(size))) and all(value > 0 for values in (size, threads, warps) for value in values):
                layout['status'] = 'symbolic_nominal_tile'
                layout['warp_width'] = math.prod(threads)
                layout['warp_count'] = math.prod(warps)
                layout['nominal_tile_shape'] = [s * t * w for s, t, w in zip(size, threads, warps)]
                coords = []
                for dimension in range(len(size)):
                    earlier = order[:order.index(dimension)]
                    lane_stride = math.prod(threads[d] for d in earlier)
                    warp_stride = math.prod(warps[d] for d in earlier)
                    coords.append({'axis': dimension,
                                   'lane_coordinate': f'(lane // {lane_stride}) % {threads[dimension]}',
                                   'warp_coordinate': f'(warp // {warp_stride}) % {warps[dimension]}',
                                   'registers_per_thread_axis': size[dimension],
                                   'nominal_coordinate': f'((warp_coord[{dimension}] * {threads[dimension]} + lane_coord[{dimension}]) * {size[dimension]} + register_inner[{dimension}])'})
                layout['coordinates'] = coords
        elif kind == 'nvidia_mma':
            layout.update(version_major=_integer(body, 'versionMajor'), version_minor=_integer(body, 'versionMinor'), warps_per_cta=_array(body, 'warpsPerCTA'), instruction_shape=_array(body, 'instrShape'))
            layout['organization'] = 'compiler_mma_cooperative_warps'
            layout['lane_element_ownership'] = 'unsupported_by_this_adapter'
        else:
            parent = re.search(r'\bparent\s*=\s*(#[\w.$]+)', body)
            layout['parent_layout'] = parent[1] if parent else None
        layouts.append(layout)

    organization = {}
    for key in ('num-warps', 'threads-per-warp', 'num-ctas'):
        values = re.findall(r'"?ttg\.' + key + r'"?\s*=\s*(\d+)\s*:\s*i32', text)
        if values and len(set(values)) == 1:
            organization[key] = int(values[0])
    sites, associations, unresolved = [], [], []
    valid_ids = _source_ids(source_operations)
    for line_number, line in enumerate(text.splitlines(), 1):
        match = _OPCODE.search(line.strip())
        if not match:
            continue
        opcode = match[1] or match[2]
        if opcode not in {'tt.load', 'tt.store', 'tt.reduce', 'tt.dot', 'ttg.convert_layout', 'ttng.warp_group_dot', 'ttng.tc_gen5_mma', 'proton.record', 'proton_gpu.read_counter', 'proton_gpu.circular_store'}:
            continue
        site_id = f"ttgir:{evidence['ttgir']['sha256']}:{line_number}"
        source = re.search(r'flagprism\.source_op_id\s*=\s*"([^"]+)"', line)
        source_id = source[1] if source else None
        site = {'id': site_id, 'line': line_number, 'opcode': opcode, 'evidence': line.strip(),
                'layout_ids': sorted(set(re.findall(r'#[\w.$]+', line)) & {layout['id'] for layout in layouts}),
                'source_op_id': source_id, 'dynamic_observation': False}
        sites.append(site)
        if source_id and (not valid_ids or source_id in valid_ids):
            associations.append({'source_op_id': source_id, 'lowered_site_id': site_id, 'basis': 'explicit_compiler_attribute'})
        else:
            unresolved.append(site_id)

    mode = compiler_metadata.get('instrumentation_mode', '')
    sampling = {'basis': 'compiler_metadata', 'status': 'unavailable'}
    if isinstance(mode, str) and mode:
        options = dict(item.split('=', 1) for item in mode.split(':') if '=' in item)
        sampling = {'basis': 'compiler_metadata', 'status': 'declared', 'options': options,
                    'observed_units': False}
    scopes = compiler_metadata.get('scope_id_names', compiler_metadata.get('instrumentation_scopes', []))
    return {'schema_version': 1, 'backend': 'cuda', 'binary_id': binary_id,
            'status': 'partial' if text else 'unsupported', 'execution_model': 'simt_warps_and_compiler_cooperative_groups',
            'artifacts': evidence, 'organization': organization, 'layouts': layouts, 'sites': sites,
            'source_associations': associations, 'unassociated_sites': unresolved,
            'instrumentation_sampling': sampling, 'instrumentation_scopes': scopes,
            'resources': {'basis': 'compiler_metadata', 'values': dict(compiler_metadata), 'measured': False},
            'limitations': ['Source IDs require explicit surviving compiler provenance; kernel names and source lines are not identity.',
                            'Blocked coordinates describe a nominal tile; shape wrapping, replication, masks and pointer semantics remain explicit compiler evidence.',
                            'MMA layouts retain cooperative warp organization; exact MMA lane-element ownership is not inferred.',
                            'Instrumentation scopes are exported sites, not a claim of source operation identity or dynamic occurrence counts.',
                            'Sampling mode describes requested units; actual observed units require dynamic records.',
                            'Static resources and layouts are not hardware counters or measured memory traffic.']}
