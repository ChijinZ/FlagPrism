"""Installed compiler fallback plumbing; mocked SDK calls are not device tests."""
import ast
import hashlib
from importlib.util import find_spec
import os
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from flagtree.debugger import gcu_timeline as bridge


@pytest.mark.parametrize('fallback', [False, True])
def test_installed_fatbin_binds_the_input_actually_sent_to_codegen(fallback):
    path = Path(find_spec('triton.backends.enflame.compiler').origin)
    tree = ast.parse(path.read_text())
    names = {'make_fatbin', '_compile_with_debugger_fabs'}
    functions = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    assert len(functions) == 2
    original = 'gcu.shared_memory_size = 0 gcu.local_memory_size = 0, targets = [#fixture]'
    linked = 'fixture actual relinked SDK LLVM input'
    inputs = []
    compatibility = []

    def compile_input(text, *args):
        inputs.append(text)
        if fallback and len(inputs) == 1:
            raise RuntimeError('ld.lld: error: relocation for fabs(float)')
        output = next(
            arg.split('=', 1)[1] for arg in args
            if arg.startswith('--output='))
        Path(output).write_bytes(b'fixture-binary')

    def attach(text, option):
        assert 'targets' not in text
        library = option.rsplit(' l=', 1)[1]
        compatibility.append(Path(library).read_bytes())
        return linked

    namespace = dict(os=os,
                     re=re,
                     tempfile=tempfile,
                     hashlib=hashlib,
                     toolkit=SimpleNamespace(datadir='/fixture',
                                             compile=compile_input,
                                             gcu_compiler_opt=attach))
    exec(
        compile(ast.Module(body=functions, type_ignores=[]), str(path),
                'exec'), namespace)
    state = dict(tle_raw=False,
                 debug_execution_version=1,
                 debug_execution_native_ir_sha256=hashlib.sha256(
                     original.encode()).hexdigest())
    options = SimpleNamespace(arch='gcu300',
                              instrumentation_mode='debugger',
                              max_shared=100,
                              max_local=100,
                              extern_libs=())
    expected = linked if fallback else original

    def bind_binary(binary, metadata):
        assert binary == b'fixture-binary'
        assert metadata['debug_execution_native_ir_sha256'] == hashlib.sha256(
            expected.encode()).hexdigest()

    with patch.object(bridge, 'bind_execution_structure') as structure, \
            patch.object(bridge, 'bind_native_clock_locations', side_effect=bind_binary):
        result = namespace['make_fatbin'](original, state, options)
    assert result == b'fixture-binary'
    assert inputs == ([original, linked] if fallback else [original])
    if fallback:
        structure.assert_called_once_with(linked, state)
        assert state['debug_execution_codegen_ir'] == linked
        assert state[
            'debug_execution_pre_fallback_ir_sha256'] == hashlib.sha256(
                original.encode()).hexdigest()
        assert state['debug_execution_math_compat_sha256'] == hashlib.sha256(
            compatibility[0]).hexdigest()
    else:
        structure.assert_not_called()
        assert 'debug_execution_codegen_ir' not in state
