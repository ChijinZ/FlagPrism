# ruff: noqa
from __future__ import annotations

from triton import __version__
from flagtree._flagprism import register_component

from .scope import scope, cpu_timed_scope, enter_scope, exit_scope
from .state import state, enter_state, exit_state
from .profile import (
    start,
    activate,
    deactivate,
    finalize,
    profile,
    DEFAULT_PROFILE_NAME,
)
from . import context, specs, mode
from .observations import ObservationRequest

__all__ = (
    "DEFAULT_PROFILE_NAME",
    "ObservationRequest",
    "activate",
    "context",
    "cpu_timed_scope",
    "deactivate",
    "enter_scope",
    "enter_state",
    "exit_scope",
    "exit_state",
    "finalize",
    "mode",
    "profile",
    "scope",
    "specs",
    "start",
    "state",
)


class _ProfilerComponent:
    name = "profiler"
    api_version = (2, 0)
    version = __version__
    required_capabilities = frozenset({"compiler.dialects.v1"})

    @staticmethod
    def load_dialects(context) -> None:
        from .native import compiler_binding

        compiler_binding().load_dialects(context)

    @staticmethod
    def on_prepare_compiler_driver(event) -> None:
        from .ascend_compiler import prepare
        prepare(event)

    @staticmethod
    def on_finish_compiler_driver(event, *, returncode) -> None:
        from .ascend_compiler import finish
        finish(event, returncode=returncode)

    @staticmethod
    def compiler_driver_cache_key():
        from .ascend_compiler import cache_key
        return cache_key()

    @staticmethod
    def get_cann_launch_receipt_abi():
        from .ascend_launch import get_launch_receipt_abi
        return get_launch_receipt_abi()


component = register_component("profiler", _ProfilerComponent())
