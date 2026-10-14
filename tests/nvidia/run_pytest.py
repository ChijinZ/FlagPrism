"""Run inherited and method tests with explicit current source/native provenance."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

compiler = Path(os.environ['METHOD_COMPILER_SOURCE'])
source = Path(os.environ['METHOD_SOURCE'])
sys.path.insert(0, str(compiler / 'python'))
import triton
import triton._C.libtriton as libtriton
import flagtree

package = source / 'Profiler/python/flagtree_profiler'
spec = importlib.util.spec_from_file_location(
    'flagtree.profiler',
    package / '__init__.py',
    submodule_search_locations=[str(package)])
profiler = importlib.util.module_from_spec(spec)
sys.modules['flagtree.profiler'] = profiler
flagtree.profiler = profiler
spec.loader.exec_module(profiler)
from flagtree.profiler.native import runtime_binding

native = runtime_binding()
assert Path(triton.__file__).is_relative_to(compiler), triton.__file__
assert Path(native.__file__).is_relative_to(source), native.__file__
print(json.dumps(
    {
        'compiler_path':
        libtriton.__file__,
        'compiler_sha256':
        hashlib.sha256(Path(libtriton.__file__).read_bytes()).hexdigest(),
        'native_path':
        native.__file__,
        'native_sha256':
        hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest(),
        'profiler_path':
        profiler.__file__,
        'pid':
        os.getpid()
    },
    indent=2),
      flush=True)
import pytest
raise SystemExit(pytest.main(sys.argv[1:]))
