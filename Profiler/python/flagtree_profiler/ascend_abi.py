"""Read compiler-emitted source formal roles before CANN's bare-pointer lowering.

No actor/kernel names or fixed hidden-argument counts participate in mapping.
Final LLVM verifies the pointer prefix and actual runtime FFTS configuration;
the compiler's removed trailing coordinate scalars remain partial.
"""
from __future__ import annotations
import hashlib
import re


def _split(text):
    parts, start, depth, quoted, escaped = [], 0, 0, False, False
    for index, character in enumerate(text):
        if escaped:
            escaped = False
            continue
        if character == '\\' and quoted:
            escaped = True
            continue
        if character == '"':
            quoted = not quoted
            continue
        if quoted:
            continue
        if character in '(<[{':
            depth += 1
        elif character in ')>]}':
            depth -= 1
        elif character == ',' and depth == 0:
            parts.append(text[start:index].strip())
            start = index+1
    parts.append(text[start:].strip())
    return parts


def source_abi(text, *, trace_source_argument=None):
    """Parse standard func.func formal syntax and compiler-owned index attrs.

    Roles come from the actual emitted SyncBlockLockArgIdx/WorkspaceArgIdx and
    optional explicit dynamic marker. An unknown or compound scalar ABI fails
    validation later rather than shifting arguments by a guessed constant.
    """
    headers = []
    for match in re.finditer(r'\bfunc\.func\s+@[^\s(]+\(', text):
        begin = match.end()
        depth = 1
        quoted = False
        for position in range(begin, len(text)):
            char = text[position]
            if char == '"':
                quoted = not quoted
            if quoted:
                continue
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    end = position
                    break
        else:
            raise ValueError('unterminated compiler function signature')
        tail = text[end+1:text.find('\n', end+1)]
        if 'global_kernel' in tail:
            headers.append((text[begin:end],tail))
    if len(headers) != 1:
        raise ValueError('source ABI requires one compiler global entry; multi-entry mapping is ambiguous')
    arguments, attributes = headers[0]
    roles = {}
    for attribute, role in [('SyncBlockLockArgIdx','synchronization_lock'),('WorkspaceArgIdx','workspace'),('flagtree.profile.dynamic_arg_index','dynamic_trace')]:
        match = re.search(r'"?' + re.escape(attribute) + r'"?\s*=\s*(\d+)\s*:\s*i(?:32|64)', attributes)
        if match:
            position = int(match[1])
            if position in roles:
                raise ValueError('compiler formal role attributes overlap')
            roles[position] = role
    formals = []
    for index, argument in enumerate(_split(arguments)):
        if not argument:
            continue
        value = argument.split(':',1)[1].strip()
        kind = 'global_pointer' if value.startswith('memref<') else (re.match(r'(i\d+|f\d+|index)\b', value)[0] if re.match(r'(i\d+|f\d+|index)\b', value) else 'unsupported')
        formals.append({'source_formal_index': index, 'kind': kind, 'role': roles.get(index), 'evidence': argument})
    if any(position >= len(formals) for position in roles):
        raise ValueError('compiler formal role attribute is outside the signature')
    ordinary = [item for item in formals if item['role'] not in {'synchronization_lock','workspace'}]
    for ordinal, item in enumerate(ordinary):
        item['source_argument_index'] = ordinal
    if trace_source_argument is not None:
        if not {'synchronization_lock','workspace'} <= set(roles.values()):
            raise ValueError('dynamic source identity requires explicit compiler synchronization/workspace formal roles')
        if type(trace_source_argument) is not int or trace_source_argument < 0 or trace_source_argument >= len(ordinary):
            raise ValueError('dynamic source argument is outside compiler formals')
        item = ordinary[trace_source_argument]
        if item['kind'] != 'global_pointer':
            raise ValueError('dynamic source argument must be a global pointer')
        if any(formal['role'] == 'dynamic_trace' and formal is not item for formal in formals):
            raise ValueError('compiler dynamic formal marker contradicts source argument identity')
        item['role'] = 'dynamic_trace'
        item['role_basis'] = 'explicit_compiler_source_argument_identity'
    return {'schema_version': 1, 'source_sha256': hashlib.sha256(text.encode()).hexdigest(), 'basis': 'compiler_emitted_func_signature_and_index_attributes', 'formals': formals}
