"""Evidence-preserving static execution mapping for Enflame compiler artifacts.

GCU work-items execute vectors; compiler ``num_warps`` is not NVIDIA SIMT.
Exact source identity requires surviving compiler IDs. Debug locations provide
origin candidates, including ambiguity; they never establish exclusive cost.
Missing location serialization remains explicitly partial.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping

_SSA = r"%[\w.$]+(?:#[0-9]+)?"
_OP = re.compile(r'^\s*(?:(?P<result>' + _SSA + r')(?:\:\d+)?\s*=\s*)?"(?P<op>[\w.]+)"\((?P<args>[^)]*)\)')
_CUSTOM_OP = re.compile(r'^\s*(?:' + _SSA + r'(?:\:\d+)?\s*=\s*)?(?P<op>(?:arith|tt|math|scf|func|gpu)\.[\w.]+)\b')
_LOC_DEF = re.compile(r'^\s*(#[\w.$]+)\s*=\s*(loc\(.*\))\s*$')
_FILE_LOC = re.compile(r'"((?:\\.|[^"\\])*)"\s*:\s*(\d+)\s*:\s*(\d+)')
_BINARY = {"arith.addi": "+", "arith.subi": "-", "arith.muli": "*",
           "arith.remsi": "%", "arith.remui": "%", "arith.divsi": "//",
           "arith.divui": "//", "arith.minsi": "min", "arith.maxsi": "max"}
_CASTS = {"arith.index_cast", "arith.extsi", "arith.extui", "arith.trunci"}
_MEMORY = {"vector.load", "vector.store", "memref.load", "memref.store",
           "memref_ext.slice_pad_start", "memref_ext.slice_deslice_start",
           "memref.dma_start", "memref.dma_wait"}


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _outside_quotes(text):
    """Yield lexical positions without treating quoted alias/name text as IR."""
    quoted = escaped = False
    for index, character in enumerate(text):
        if escaped:
            escaped = False
            continue
        if character == '\\' and quoted:
            escaped = True
        elif character == '"':
            quoted = not quoted
        elif not quoted:
            yield index


def _location_on_operation(line):
    for start in _outside_quotes(line):
        if not line.startswith('loc(', start):
            continue
        depth = 0
        for index in _outside_quotes(line[start:]):
            character = line[start + index]
            depth += (character == '(') - (character == ')')
            if depth == 0 and index >= 3:
                return line[start:start + index + 1]
    return None


def _decode_mlir_string(value):
    output = bytearray()
    index = 0
    while index < len(value):
        if value[index] == '\\' and index + 1 < len(value):
            if re.fullmatch(r'[0-9a-fA-F]{2}', value[index + 1:index + 3]):
                output.append(int(value[index + 1:index + 3], 16))
                index += 3
                continue
            output.extend({'n': '\n', 'r': '\r', 't': '\t'}.get(value[index + 1], value[index + 1]).encode())
            index += 2
        else:
            output.extend(value[index].encode())
            index += 1
    try:
        return output.decode()
    except UnicodeDecodeError:
        return value  # Preserve malformed bytes rather than guessing a path.


def _location_evidence(location, aliases):
    missing = set()

    def expand(value, active):
        outside = set(_outside_quotes(value))
        def substitute(match):
            identity = match[0]
            if match.start() not in outside:
                return identity
            if identity in active or identity not in aliases or len(active) > 64:
                missing.add(identity)
                return identity
            return expand(aliases[identity], active | {identity})
        return re.sub(r'#[\w.$]+', substitute, value)

    expanded = expand(location or '', set())
    atoms = sorted({(_decode_mlir_string(match[1]), int(match[2]), int(match[3]))
                    for match in _FILE_LOC.finditer(expanded)})
    return {'raw': location, 'expanded': expanded,
            'locations': [{'file': file, 'line': line, 'column': column} for file, line, column in atoms],
            'unresolved_aliases': sorted(missing)}, set(atoms)


def _source_origins(artifacts, compiler_metadata, source_operations):
    rows = source_operations
    if not rows:
        rows = compiler_metadata.get('debug_tracked_table')
    if isinstance(rows, str):
        try:
            rows = json.loads(rows)
        except ValueError:
            rows = None
    origins = []
    if isinstance(rows, Mapping):
        rows = [dict(value, _origin_id=str(identity)) for identity, value in rows.items()
                if isinstance(value, Mapping)]
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            identity = row.get('_origin_id', row.get('opId', row.get('op_id')))
            location = row.get('sourceLoc', row.get('source_loc'))
            if identity is None or not isinstance(location, str):
                continue
            evidence, atoms = _location_evidence(location, {})
            if atoms:
                origins.append({'id': str(identity), 'identity_kind': 'compiler_assigned_within_binary',
                                'opcode': row.get('mlirOpName'), 'location': evidence, '_atoms': atoms})
    if origins:
        return origins
    text = artifacts.get('ttir', '')
    aliases = dict(match.groups() for line in text.splitlines()
                   if (match := _LOC_DEF.match(line)))
    function = 0
    for line_number, line in enumerate(text.splitlines(), 1):
        if _LOC_DEF.match(line):
            continue
        match = _OP.match(line) or _CUSTOM_OP.match(line)
        if not match:
            continue
        opcode = match['op']
        if opcode in {'tt.func', 'func.func', 'gpu.func'}:
            function += 1
            continue
        evidence, atoms = _location_evidence(_location_on_operation(line), aliases)
        if atoms:
            origins.append({'id': f"ttir:{_digest(text)}:function-{function}:{line_number}",
                            'identity_kind': 'ttir_operation_with_debug_origin', 'opcode': opcode,
                            'location': evidence, '_atoms': atoms})
    return origins


def build_execution_mapping(asm: Mapping[str, str], compiler_metadata: Mapping,
                            *, binary_id=None, source_operations=None) -> dict:
    """Return compiler evidence, symbolic ownership and explicit coverage.

    ``asm`` is CompiledKernel.asm, not paths or Study replacement output.
    Expressions are compiler SSA expressions, not dynamic element counts.
    Exact association requires explicit ``flagprism.source_op_id`` attributes.
    Actual location chains link possible origins to compiler-assigned source IDs
    or binary-scoped TTIR nodes, without claiming instruction/cost exclusivity.
    Uninterpreted expressions retain their original SSA spelling.
    """
    artifacts = {key: value for key, value in asm.items()
                 if key in {"ttir", "ttgir", "gcuir", "llir"} and isinstance(value, str)}
    evidence = {key: {"sha256": _digest(value), "bytes": len(value.encode())}
                for key, value in artifacts.items()}
    text = artifacts.get("gcuir", "")
    expressions = {}
    regions = []
    sites = []
    associations = []
    origin_associations = []
    unresolved = []
    supplied_ids = set(source_operations or ())
    origins = _source_origins(artifacts, compiler_metadata, source_operations)
    aliases = dict(match.groups() for line in text.splitlines()
                   if (match := _LOC_DEF.match(line)))
    work_items = []
    function = 0
    for line_number, line in enumerate(text.splitlines(), 1):
        match = _OP.search(line)
        if not match:
            continue
        result, op = match["result"], match["op"]
        if op in {"func.func", "gpu.func"}:
            expressions.clear()  # SSA identifiers are local to a function.
            function += 1
        args = re.findall(_SSA, match["args"])
        values = [expressions.get(arg, arg) for arg in args]
        expression = None
        if op == "arith.constant":
            constant = re.search(r'value\s*=\s*(-?\d+)\s*:\s*(?:index|i\d+)', line)
            if constant:
                expression = constant[1]
        elif op in {"gpu.thread_id", "gpu.block_id"}:
            dim = re.search(r'#gpu<dim ([xyz])>', line)
            if dim:
                expression = ("work_item" if op == "gpu.thread_id" else "program") + "." + dim[1]
                if op == "gpu.thread_id":
                    work_items.append({"axis": dim[1], "ssa": result, "line": line_number})
        elif op in _CASTS and len(values) == 1:
            expression = values[0]
        elif op in _BINARY and len(values) == 2:
            operator = _BINARY[op]
            expression = (f"{operator}({values[0]}, {values[1]})" if operator in {"min", "max"}
                          else f"({values[0]} {operator} {values[1]})")
        if result and expression is not None:
            # Cap expansion, retaining SSA identity for complex/pipelined graphs.
            expressions[result] = expression if len(expression) < 2048 else result
        elif result:
            expressions.pop(result, None)
        if op == "gcu.border":
            border = re.search(r'(enter|leave)\s*=\s*"([^"]+)"', line)
            if border:
                regions.append({"direction": border[1], "lowered_opcode": border[2],
                                "line": line_number, "source_association": "unknown"})
        is_shared = bool(re.search(r'memref<[^>]*,\s*2\s*>', line))
        interesting = (op in _MEMORY or op in {"gpu.barrier", "gcu.vector_movsft", "memref.alloc"}
                       or is_shared)
        if not interesting:
            continue
        source = re.search(r'flagprism\.source_op_id\s*=\s*"([^"]+)"', line)
        source_id = source[1] if source else None
        site_id = f"gcuir:{evidence['gcuir']['sha256']}:{line_number}"
        location, atoms = _location_evidence(_location_on_operation(line), aliases)
        candidates = [origin for origin in origins if atoms & origin['_atoms']]
        origin_status = ('unique_origin' if len(candidates) == 1 and not location['unresolved_aliases']
                         else 'ambiguous' if candidates else 'missing')
        if candidates:
            origin_associations.append({
                'lowered_site_id': site_id, 'status': origin_status,
                'candidate_source_ids': [origin['id'] for origin in candidates],
                'basis': 'compiler_debug_location_chain', 'exclusive_cost': False,
                'matched_locations': {origin['id']: [dict(file=file, line=number, column=column)
                                                      for file, number, column in sorted(atoms & origin['_atoms'])]
                                      for origin in candidates},
                'unresolved_location_aliases': location['unresolved_aliases'],
            })
        kind = ("barrier" if op == "gpu.barrier" else
                "partial_exchange_storage" if is_shared else
                "vector_exchange" if op == "gcu.vector_movsft" else
                "allocation" if op == "memref.alloc" else "memory")
        sites.append({"id": site_id, "line": line_number, "function_scope": function, "opcode": op,
                      "kind": kind, "operands": args, "operand_expressions": values,
                      "ownership_status": "symbolic" if any("work_item." in v for v in values) else "unknown",
                      "evidence": line.strip(), "source_op_id": source_id,
                      'location': location, 'source_origin_status': origin_status,
                      'source_origin_candidates': [origin['id'] for origin in candidates]})
        if source_id and (not supplied_ids or source_id in supplied_ids):
            associations.append({"source_op_id": source_id, "lowered_site_id": site_id,
                                 "basis": "explicit_compiler_attribute"})
        else:
            unresolved.append(site_id)
    llir_sites = []
    for line_number, line in enumerate(artifacts.get("llir", "").splitlines(), 1):
        if '"llvm.call"' not in line:
            continue
        callee = re.search(r'callee\s*=\s*@([\w.$]+)', line)
        if callee and callee[1] in {"tops_syncthreads", "tops_mfence", "tops_clock_begin", "tops_clock_end", "_ZN4tops12global_timerEv"}:
            llir_sites.append({"line": line_number, "callee": callee[1], "evidence": line.strip(),
                               "source_association": "unknown", "dynamic_observation": False})
    # Read launch organization from emitted target attributes, never kernel name.
    organization = {}
    for key in ("num-warps", "threads-per-warp", "num-ctas"):
        hits = re.findall(r'"?ttg\.' + key + r'"?\s*=\s*(\d+)\s*:\s*i32', text)
        if len(set(hits)) == 1:
            organization[key] = int(hits[0])
    count = organization.get("num-warps")
    width = organization.get("threads-per-warp")
    work_item_count = count * width if count is not None and width is not None else None
    if work_item_count == 1:
        for site in sites:
            if site["opcode"] in _MEMORY and site["ownership_status"] == "unknown":
                site["ownership_status"] = "single_work_item"
                site["owner"] = "work_item.x = 0"
    return {"schema_version": 1, "backend": "enflame", "binary_id": binary_id,
            "status": "partial" if text else "unsupported", "artifacts": evidence,
            "execution_model": "vector_work_items", "organization": organization,
            "work_item_count": work_item_count, "work_item_coordinates": work_items,
            "sites": sites, "lowered_regions": regions, "source_associations": associations,
            'source_origin_associations': origin_associations,
            'origin_source_operations': [{key: value for key, value in origin.items() if key != '_atoms'}
                                         for origin in origins],
            'origin_coverage': {status: sum(site['source_origin_status'] == status for site in sites)
                                for status in ('unique_origin', 'ambiguous', 'missing')},
            "unassociated_sites": unresolved, "llvm_primitive_sites": llir_sites,
            "resources": {"basis": "compiler_metadata", "values": dict(compiler_metadata),
                          "measured": False},
            "limitations": ["Exact source identities require explicit surviving compiler attributes.",
                            "Debug-location candidates describe origins, not exclusive operation cost or completion.",
                            "TTIR fallback identities are scoped to an actual IR artifact; they are not AST-operation IDs.",
                            "Border opcode regions describe lowering, not source op identity.",
                            "Ownership expressions retain SSA/control conditions; they are not observed element counts.",
                            "Address space 2 is compiler shared exchange storage; physical traffic is not inferred.",
                            "Static primitive sites are not dynamic occurrences or measured durations."]}
