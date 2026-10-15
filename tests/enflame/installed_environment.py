"""Check installed import, native dependency and backend ABI provenance.

Run from outside compiler/component source with PYTHONPATH unset. Installed
vendor Torch/SDK packages are allowed; source checkouts and editable hooks are
not used by this audit.
"""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--wheel-manifest', type=Path, required=True)
args = parser.parse_args()
assert not os.environ.get('PYTHONPATH'), os.environ.get('PYTHONPATH')
assert sys.prefix != sys.base_prefix, (sys.prefix, sys.base_prefix)
installed = Path(sys.prefix).resolve()
modules = ('triton', 'flagtree', 'flagtree.profiler', 'flagtree.debugger',
           'flagtree.profiler.profile', 'flagtree.debugger.compiler',
           'triton._C.libtriton', 'triton.backends.enflame.compiler',
           'flagtree.profiler._native', 'flagtree.debugger._native')
paths = {
    name: Path(importlib.import_module(name).__file__).resolve()
    for name in modules
}
assert all(path.is_relative_to(installed) for path in paths.values()), paths
import triton
from triton.backends.enflame.backend import _triton_version
assert _triton_version() == tuple(
    int(part) for part in triton.__version__.split('.')[:2])
manifest = json.loads(args.wheel_manifest.read_text())
site = paths['triton'].parent.parent
for relative, digest in manifest['files'].items():
    assert hashlib.sha256(
        (site / relative).read_bytes()).hexdigest() == digest, relative
assert (site / 'flagtree/profiler/_cann_launch_receipt.h').is_file()
assert (site / 'triton/backends/enflame/VERSION').is_file()
loaded = sorted({
    line.split()[-1]
    for line in Path('/proc/self/maps').read_text().splitlines()
    if '.so' in line and any(
        name in line for name in ('libtriton', '_triton_gcu', 'flagtree/'))
})
assert loaded and all(Path(path).is_relative_to(installed)
                      for path in loaded), loaded
print(
    json.dumps(
        {
            'prefix': sys.prefix,
            'paths': {
                name: str(path)
                for name, path in paths.items()
            },
            'sys_path': sys.path,
            'loaded_compiler_native': loaded,
            'verified_wheel_files': manifest['files']
        },
        indent=2))
