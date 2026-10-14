"""Small, lazy capture extensions; SDK activity normalization stays in collectors."""
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class CaptureBackend:
    software_modules: tuple[str, ...] = ()
    collect_counters: Optional[Callable] = None


def _enflame_counters(command, output, *, metrics, replay_mode, env):
    from .tcu import collect
    if replay_mode not in ("none", "application"):
        raise ValueError("TCU supports replay modes none and application")
    return collect(command,
                   output,
                   metrics=metrics or "SIP/BUSY",
                   replay_mode=replay_mode,
                   env=env)


def _ascend_counters(command, output, *, metrics, replay_mode, env):
    from .cann import collect_msprof
    if replay_mode not in ("none", "independent"):
        raise ValueError("CANN counter collection supports independent replay only")
    if isinstance(metrics, str):
        metrics = tuple(part.strip() for part in metrics.split(",") if part.strip())
    return collect_msprof(
        command, output,
        metrics=metrics or ("ArithmeticUtilization", "PipeUtilization"),
        replay_mode="independent", env=env)


_DEFAULT = CaptureBackend()
_ENFLAME = CaptureBackend(("torch_gcu", ), _enflame_counters)
_BACKENDS = dict.fromkeys(("enflame", "gcu", "tops"), _ENFLAME)
_ASCEND = CaptureBackend(("torch_npu", ), _ascend_counters)
_BACKENDS.update(dict.fromkeys(("ascend", "npu", "cann"), _ASCEND))


def capture_backend(name):
    return _BACKENDS.get(str(name or "").lower(), _DEFAULT)
