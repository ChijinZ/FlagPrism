"""CANN/Enflame detailed sessions reject capture before JIT compilation or launch."""
from functools import wraps
from triton.runtime.jit import JITFunction
from .hook import Hook


class DetailedGraphGuard(Hook):
    priority = 110

    def __init__(self, backend):
        self.backend = backend
        self.wrapper = None
        self.previous = None
        self.state = None

    def activate(self):
        if self.wrapper is not None:
            return
        previous = JITFunction.run
        state = {'enabled': True}

        @wraps(previous)
        def guarded_run(kernel, *args, **kwargs):
            if state['enabled']:
                from flagtree.debugger.graph_guard import require_eager
                require_eager(self.backend)
            return previous(kernel, *args, **kwargs)

        self.previous, self.state, self.wrapper = previous, state, guarded_run
        JITFunction.run = guarded_run

    def deactivate(self):
        if self.wrapper is None:
            return
        self.state['enabled'] = False
        if JITFunction.run is self.wrapper:
            JITFunction.run = self.previous
        self.wrapper = self.previous = self.state = None

    def init_handle(self, *args, **kwargs):
        pass

    def enter(self, metadata):
        pass

    def exit(self, metadata):
        pass


graph_guards = {
    backend: DetailedGraphGuard(backend)
    for backend in ('cann', 'enflame')
}
