"""Ordinary Ascend SDK startup: vendor runtime before unchanged user workload.

Q1 adds only runtime import order. No profiler import, kernel/input edit, replay,
argument change, or numerical change. Use this SAME script in baseline/profile.
"""
import sys
from pathlib import Path
import runpy

import torch  # noqa: F401
import torch_npu  # noqa: F401

directory = Path(__file__).resolve().parent
sys.path.insert(0, str(directory))
runpy.run_path(str(directory / "workload.py"), run_name="__main__")
