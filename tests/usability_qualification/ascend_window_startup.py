"""Ordinary vendor initialization for unchanged Q0a pointwise reserve."""
import sys
from pathlib import Path
import runpy

import torch  # noqa: F401
import torch_npu  # noqa: F401

directory = Path(__file__).resolve().parent
sys.path.insert(0, str(directory))
runpy.run_path(str(directory / 'reserve_window.py'), run_name='__main__')
