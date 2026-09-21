"""Small, lazy capture extensions; SDK activity normalization stays in collectors."""
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class CaptureBackend:
    software_modules: tuple[str, ...] = ()
    collect_counters: Optional[Callable] = None


def _enflame_counters(command, output, *, metrics, replay_mode, env):
    from .tcu import collect
    return collect(command,
                   output,
                   metrics=metrics or "SIP/BUSY",
                   replay_mode=replay_mode,
                   env=env)


_DEFAULT = CaptureBackend()
_ENFLAME = CaptureBackend(("torch_gcu", ), _enflame_counters)
_BACKENDS = dict.fromkeys(("enflame", "gcu", "tops"), _ENFLAME)


def capture_backend(name):
    return _BACKENDS.get(str(name or "").lower(), _DEFAULT)
