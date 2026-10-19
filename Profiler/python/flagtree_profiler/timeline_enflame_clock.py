"""Profiler-owned GCU timer anchors, independent of user-kernel duration.

Internal kernels use the installed CompiledKernel launch ABI with no launch
metadata callbacks. Global user hooks and session activation are never changed.
"""
import copy
import hashlib
from pathlib import Path
import tempfile
import time

SOURCE = 'module {\n llvm.func @_ZN4tops12global_timerEv() -> i64\n llvm.func @flagprism_gcu_clock_identity_v1() -> i32\n tt.func public @flagprism_clock_anchor(%T: !tt.ptr<i32>) {\n  %pid = tt.get_program_id x : i32\n  %four = arith.constant 5 : i32\n  %offset = arith.muli %pid, %four : i32\n  %P = tt.addptr %T, %offset : !tt.ptr<i32>, i32\n  %actor = gpu.thread_id x\n  %zero_index = arith.constant 0 : index\n  %selected = arith.cmpi eq, %actor, %zero_index : index\n  scf.if %selected {\n   %clock = llvm.call @_ZN4tops12global_timerEv() : () -> i64\n   %low = llvm.trunc %clock : i64 to i32\n   %shift = llvm.mlir.constant(32 : i64) : i64\n   %upper = llvm.lshr %clock, %shift : i64\n   %high = llvm.trunc %upper : i64 to i32\n   tt.store %P, %low : !tt.ptr<i32>\n   %one = arith.constant 1 : i32\n   %next = tt.addptr %P, %one : !tt.ptr<i32>, i32\n   tt.store %next, %high : !tt.ptr<i32>\n   %two = arith.constant 2 : i32\n   %actorptr = tt.addptr %P, %two : !tt.ptr<i32>, i32\n   %zero = arith.constant 0 : i32\n   tt.store %actorptr, %pid : !tt.ptr<i32>\n   %three = arith.constant 3 : i32\n   %tagptr = tt.addptr %P, %three : !tt.ptr<i32>, i32\n   %tag = arith.constant 1179665217 : i32\n   %identity = llvm.call @flagprism_gcu_clock_identity_v1() : () -> i32\n   tt.store %tagptr, %identity : !tt.ptr<i32>\n   %four_words = arith.constant 4 : i32\n   %sealptr = tt.addptr %P, %four_words : !tt.ptr<i32>, i32\n   tt.store %sealptr, %tag : !tt.ptr<i32>\n  }\n  tt.return\n }\n}\n'
PROGRAMS = 64


class EnflameClockAnchors:
    """A finite session window; its observations confer no future clock rights."""

    def __init__(self):
        import torch
        import torch_gcu  # noqa: F401
        import triton
        from triton.runtime import driver
        self.torch, self.driver = torch, driver
        self.device = int(torch.gcu.current_device())
        self.stream = int(driver.active.get_current_stream(self.device))
        library = Path('/opt/tops/llvm11/lib/krt/gcu300_api_profile.bc')
        target = driver.active.get_current_target()
        if getattr(target, 'backend', None) != 'gcu' or 'gcu300' not in str(
                target.arch):
            raise ValueError('Clock anchor requires the actual gcu300 target')
        library_sha = hashlib.sha256(library.read_bytes()).hexdigest()
        from flagtree.debugger.gcu_clock import identity_library
        identity = identity_library()
        self.identity_library = identity
        with tempfile.TemporaryDirectory(
                prefix='flagprism-clock-anchor-') as temp:
            path = Path(temp) / 'anchor.ttir'
            path.write_text(SOURCE)
            self.kernel = triton.compile(
                str(path),
                target=target,
                options=dict(num_warps=4,
                             num_stages=1,
                             enable_i64=False,
                             extern_libs=(('sdk_readonly_global_timer',
                                           str(library)),
                                          ('owned_clock_identity',
                                           identity['file']))))
        if self.kernel.metadata.enable_i64 is not False:
            raise ValueError(
                'Clock anchor requires its guarded split-i64 lowering')
        # Initialized before a profiling session installs load/launch callbacks.
        self.kernel._init_handles()
        self.values = torch.full((5 * PROGRAMS + 8, ),
                                 0x55AA55,
                                 dtype=torch.int32,
                                 device='gcu')
        self.output = self.values[4:4 + 5 * PROGRAMS]
        self.evidence = dict(schema_version=2,
                             device=self.device,
                             stream=self.stream,
                             target=repr(target),
                             sdk_library_sha256=library_sha,
                             sdk_symbol='_ZN4tops12global_timerEv',
                             identity_library_sha256=identity['sha256'],
                             identity_symbol='flagprism_gcu_clock_identity_v1',
                             identity_register='llvm.dtu.movs.sipinfo',
                             anchor_programs=PROGRAMS,
                             timer_bits=46,
                             anchor_source_sha256=hashlib.sha256(
                                 SOURCE.encode()).hexdigest(),
                             anchor_binary_id=self.kernel.hash,
                             anchor_binary_sha256=hashlib.sha256(
                                 bytes(self.kernel.kernel)).hexdigest(),
                             anchor_binary_base64=None,
                             training=[],
                             heldout=[],
                             status='started',
                             read_precision_verified=False,
                             cross_actor_epoch_verified=False)
        import base64
        self.evidence['anchor_binary_base64'] = base64.b64encode(
            bytes(self.kernel.kernel)).decode()
        self.evidence['identity_library_base64'] = base64.b64encode(
            Path(identity['file']).read_bytes()).decode()
        self.evidence['identity_library_inputs'] = identity['inputs']
        self.evidence['warmup'] = self.sample('warmup', 0)
        for index in range(4):
            if index:
                time.sleep(.05)
            self.evidence['training'].append(self.sample('training', index))
        self._validate_domain_rows(self.evidence['training'])
        self.evidence['status'] = 'training_frozen'

    def sample(self, purpose, index):
        if (self.torch.gcu.current_device() != self.device
                or int(self.driver.active.get_current_stream(
                    self.device)) != self.stream):
            raise ValueError('Clock anchor device/default stream changed')
        self.values.fill_(0x55AA55)
        self.torch.gcu.synchronize()
        before = time.monotonic_ns()
        # The same low-level ABI used by the actual installed __getitem__
        # runner, explicitly without user metadata/enter/exit callbacks.
        self.kernel.run(PROGRAMS, 1, 1, self.stream, self.kernel.function,
                        self.kernel.packed_metadata, None, None, None,
                        self.output)
        self.torch.gcu.synchronize()
        after = time.monotonic_ns()
        words = self.values.cpu().tolist()
        if words[:4] != [0x55AA55] * 4 or words[-4:] != [0x55AA55] * 4:
            raise ValueError('Clock anchor allocation guard failed')
        by_domain, raw_rows = {}, []
        for program in range(PROGRAMS):
            row = words[4 + 5 * program:9 + 5 * program]
            if row[2] != program or row[4] != 1179665217:
                raise ValueError(
                    'Clock anchor program identity/publication failed')
            tick = (row[0] & 0xffffffff) | ((row[1] & 0xffffffff) << 32)
            if not 0 < tick < 1 << 46:
                raise ValueError('Clock anchor counter width changed')
            domain = row[3] & 0xffffffff
            observation = dict(program=program,
                               raw_tick=tick,
                               full_sipinfo=domain,
                               raw_words=row)
            raw_rows.append(observation)
            # One actual observation per physical identity and host bracket.
            # No averaging, logical-program parity rule, or epoch merging.
            if domain not in by_domain:
                by_domain[domain] = observation
        return dict(index=index,
                    purpose=purpose,
                    before_ns=before,
                    after_ns=after,
                    domains=list(by_domain.values()),
                    raw_rows=raw_rows,
                    guard_checked=True)

    @staticmethod
    def _validate_domain_rows(samples):
        from .timeline_calibration import empirical_period_bounds
        identities = set.intersection(
            *[{row['full_sipinfo']
               for row in sample['domains']} for sample in samples])
        if not identities:
            raise ValueError(
                'Clock anchor samples have no recurring physical identity')
        for identity in identities:
            rows = []
            for sample in samples:
                match = next(row for row in sample['domains']
                             if row['full_sipinfo'] == identity)
                rows.append(
                    dict(raw_tick=match['raw_tick'],
                         before_ns=sample['before_ns'],
                         after_ns=sample['after_ns']))
            empirical_period_bounds(rows, bits=46)

    def finish(self):
        if self.evidence['status'] == 'window_closed':
            return copy.deepcopy(self.evidence)
        if self.evidence['status'] != 'training_frozen':
            raise ValueError(
                'Clock calibration is not retryable after a failed close')
        self.evidence['status'] = 'closing'
        try:
            for index in range(4):
                if index:
                    time.sleep(.05)
                self.evidence['heldout'].append(self.sample('heldout', index))
            # Includes cross-window pairs separately for each recurring physical identity.
            self._validate_domain_rows(self.evidence['training'] +
                                       self.evidence['heldout'])
            self.evidence['status'] = 'window_closed'
        except BaseException:
            self.evidence['status'] = 'close_failed'
            raise
        return copy.deepcopy(self.evidence)
