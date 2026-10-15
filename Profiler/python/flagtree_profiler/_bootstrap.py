"""Order the Ascend runtime imports before its vendor compiler is discovered."""
import importlib
import importlib.util
import os
from pathlib import Path
import sys


def prepare_runtime_imports():
    # Existing Triton imports already own their initialization sequence. In a
    # fresh CLI process the vendor backend imports TorchDynamo, which requires
    # Torch/NPU initialization before Triton's package starts loading.
    if 'triton' in sys.modules:
        return
    backend = os.environ.get('FLAGTREE_BACKEND')
    if backend is None:
        spec = importlib.util.find_spec('triton')
        if spec is not None and spec.origin:
            marker = Path(spec.origin).with_name('FLAGTREE_BACKEND')
            if marker.is_file():
                backend = marker.read_text().strip()
    if backend == 'ascend':
        importlib.import_module('torch')
        importlib.import_module('torch_npu')
