from __future__ import annotations

import importlib
from types import ModuleType


def _optional_module(name: str, errors=None) -> ModuleType | None:
    try:
        return importlib.import_module(name)
    except (ImportError, OSError) as error:
        if errors is not None:
            errors.append((name, error))
        return None


def runtime_binding() -> ModuleType:
    errors = []
    _optional_module("triton._C.libtriton", errors)
    binding = _optional_module("flagtree.profiler._native", errors)
    if binding is None:
        raise RuntimeError(
            "FlagTree profiler native support is unavailable. Reinstall FlagTree "
            "with `TRITON_BUILD_FLAGPRISM=ON`. Loader diagnostics: " +
            "; ".join(f"{name}: {type(error).__name__}: {error}"
                      for name, error in errors)) from errors[-1][1]
    return binding


def compiler_binding() -> ModuleType:
    errors = []
    libtriton = _optional_module("triton._C.libtriton", errors)
    binding = getattr(libtriton, "proton",
                      None) if libtriton is not None else None
    if binding is None:
        message = "FlagTree profiler compiler interface is unavailable in this FlagTree build."
        if errors:
            name, error = errors[-1]
            raise RuntimeError(
                f"{message} Loader diagnostics: {name}: {type(error).__name__}: {error}"
            ) from error
        raise RuntimeError(
            message + " Loaded triton._C.libtriton has no proton interface; "
            "build with TRITON_BUILD_FLAGPRISM=ON.")
    return binding
