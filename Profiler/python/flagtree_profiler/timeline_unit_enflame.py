"""Capture-bound empirical GCU global-timer units; no shared-epoch rights."""
import hashlib
import copy
import json
from pathlib import Path
import struct

from .timeline_calibration import frozen_window_scale
from .timeline_events import validate_raw_batch, _sha, stable_id
from .timeline_store import read_artifact
from .timeline_views import CounterUnitProof, document_sha256


def _need(value, message):
    if not value:
        raise ValueError(message)


def load_counter_unit_proofs(directory, capture, batch):
    batch = validate_raw_batch(batch)
    owner, metadata = capture['owner'], capture['metadata']
    evidence = json.loads(
        read_artifact(directory, metadata['clock_calibration_file']))
    _need(
        type(evidence) is dict and type(evidence.get('schema_version')) is int
        and evidence['schema_version'] == 2
        and evidence.get('status') == 'window_closed',
        'No closed GCU clock anchor window')
    initial = copy.deepcopy(evidence)
    initial.pop('initial_snapshot_sha256', None)
    initial.pop('error', None)
    initial.update(status='training_frozen', heldout=[])
    _need(
        document_sha256(initial) == evidence['initial_snapshot_sha256'] ==
        metadata['clock_calibration_initial_sha256'],
        'Frozen clock training snapshot changed')
    compiler = metadata['compiler_metadata']
    _need(
        type(compiler.get('debug_clock_identity_version')) is int
        and compiler['debug_clock_identity_version'] == 1
        and compiler.get('debug_clock_identity_primitive')
        == 'llvm.dtu.movs.sipinfo'
        and compiler.get('debug_clock_identity_library_sha256')
        == evidence['identity_library_sha256'],
        'Capture and clock anchors do not use the same full hardware identity getter'
    )
    _sha(evidence['sdk_library_sha256'])
    _need(
        compiler.get('debug_clock_library_sha256')
        == evidence['sdk_library_sha256']
        and compiler.get('debug_clock_primitive') == evidence['sdk_symbol'],
        'Capture compiler and calibration use different retained SDK getters')
    _need(
        compiler.get('debug_clock_domain') == 'enflame.sdk.global_timer'
        and compiler.get('debug_clock_bits') == 46
        and evidence.get('timer_bits') == 46
        and evidence.get('sdk_symbol') == '_ZN4tops12global_timerEv'
        and type(evidence.get('device')) is int
        and evidence['device'] == owner['device'],
        'Clock anchors and capture use different targets/devices/getters')
    _need(
        owner.get('host_window_clock') == 'python.monotonic_ns',
        'Missing capture host window')
    # GCU's canonical namespace binds the actual native launch scope/session;
    # the physical buffer owner's ID is deliberately a different namespace.
    association = capture['launch']
    invocation = stable_id((owner['capture_id'], ), 'enflame-invocation',
                           association['invocation_id'],
                           association['scope_id'],
                           sorted(association['session_ids']))
    _need(
        all(batch['identity'][key] == owner[key]
            for key in ('capture_id', 'binary_id'))
        and batch['identity']['invocation_id'] == invocation
        and association['binary_id'] == owner['binary_id']
        and association['evidence'] == 'same_launch_metadata_object'
        and batch['raw_artifact']['sha256'] == capture['raw_sha256'],
        'Clock inputs belong to different captures')
    raw = read_artifact(directory, capture['raw_file'])
    _need(
        hashlib.sha256(raw).hexdigest() == capture['raw_sha256'],
        'GCU unit raw bytes changed')
    _need(batch['records'], 'No counter records to convert')
    _need(all(row['timer_bits'] == 46 for row in batch['observers']),
          'GCU counter encoding differs from the calibrated getter')
    for record in batch['records']:
        _need(
            0 <= record['offset'] <= len(raw) - 8 and struct.unpack_from(
                '<Q', raw, record['offset'])[0] == record['tick'],
            'Counter unit canonical tick differs from raw bytes')
    import base64
    _need(
        type(evidence.get('anchor_binary_base64')) is str
        and 0 < len(evidence['anchor_binary_base64']) <= 1024 * 1024,
        'Clock anchor executable budget exceeded')
    binary = base64.b64decode(evidence['anchor_binary_base64'], validate=True)
    _need(
        binary and hashlib.sha256(binary).hexdigest()
        == evidence['anchor_binary_sha256'],
        'Retained clock anchor executable seal changed')
    _need(
        type(evidence.get('identity_library_base64')) is str
        and 0 < len(evidence['identity_library_base64']) <= 1024 * 1024,
        'Clock identity library budget exceeded')
    identity_binary = base64.b64decode(evidence['identity_library_base64'],
                                       validate=True)
    _need(
        identity_binary[:4] == b'BC\xc0\xde'
        and hashlib.sha256(identity_binary).hexdigest()
        == evidence['identity_library_sha256'],
        'Retained actual clock identity library seal changed')

    def domain_rows(phase, identity):
        rows = []
        count = evidence['anchor_programs']
        _need(
            type(count) is int and 1 <= count <= 1024,
            'Clock anchor program budget invalid')
        for sample in evidence[phase]:
            raw_rows = sample['raw_rows']
            _need(
                type(raw_rows) is list and len(raw_rows) == count,
                'Clock anchor publication count changed')
            by_domain = {}
            for program, row in enumerate(raw_rows):
                words = row['raw_words']
                _need(
                    type(words) is list and len(words) == 5 and all(
                        type(word) is int and -0x80000000 <= word <= 0x7fffffff
                        for word in words)
                    and words[2] == program == row['program']
                    and words[4] == 1179665217
                    and words[3] & 0xffffffff == row['full_sipinfo']
                    and ((words[0] & 0xffffffff) |
                         ((words[1] & 0xffffffff) << 32)) == row['raw_tick'],
                    'Clock anchor identity/tick differs from actual raw words')
                by_domain.setdefault(row['full_sipinfo'], row)
            _need(
                list(by_domain.values()) == sample['domains'],
                'Clock domain selection differs from actual publications')
            _need(
                identity in by_domain,
                'No enclosing calibration for this actual physical counter identity'
            )
            rows.append(
                dict(raw_tick=by_domain[identity]['raw_tick'],
                     before_ns=sample['before_ns'],
                     after_ns=sample['after_ns']))
        return rows

    implementation = document_sha256({
        'provider':
        hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'arithmetic':
        hashlib.sha256(
            Path(__file__).with_name(
                'timeline_calibration.py').read_bytes()).hexdigest()
    })
    proofs = []
    for observer in batch['observers']:
        physical = observer['physical_identity']
        _need(
            type(physical) is dict
            and physical.get('enflame.kind') == 'dtu.full_sipinfo.v1',
            'Actual observer has no full physical counter identity')
        identity = physical['enflame.full_sipinfo']
        _need(
            type(identity) is int and 0 <= identity < 1 << 32,
            'Invalid full SIPINFO identity')
        offsets = physical['enflame.identity_word_offsets']
        _need(
            type(offsets) is list and offsets and all(
                type(offset) is int and 0 <= offset <= len(raw) -
                4 and struct.unpack_from('<I', raw, offset)[0] == identity
                for offset in offsets),
            'Observer physical identity differs from its actual record words')
        ticks = [
            row['tick'] for row in batch['records']
            if row['observer_id'] == observer['id']
        ]
        _need(ticks, 'Observer has no actual counter records')
        scale = frozen_window_scale(
            domain_rows('training', identity),
            domain_rows('heldout', identity),
            bits=46,
            admission_ns=owner['host_admission_ns'],
            completion_ns=owner['host_completion_observed_ns'],
            raw_min=min(ticks),
            raw_max=max(ticks))
        period, uncertainty = scale['nominal_period_ns'], scale[
            'period_uncertainty_ns']
        proofs.append(
            CounterUnitProof(
                **batch['identity'],
                raw_sha256=capture['raw_sha256'],
                observer_id=observer['id'],
                period_numerator_ns=period[0],
                period_denominator=period[1],
                period_uncertainty_numerator_ns=uncertainty[0],
                period_uncertainty_denominator=uncertainty[1],
                max_elapsed_ns=owner['host_completion_observed_ns'] -
                owner['host_admission_ns'],
                provider=
                'enflame.sdk.global_timer.empirical_physical_scope_window.v2',
                evidence_ids=('retained_clock_anchors:' +
                              document_sha256(evidence),
                              'retained_anchor_executable:' +
                              evidence['anchor_binary_sha256'],
                              'sdk_library:' + evidence['sdk_library_sha256'],
                              'full_physical_sipinfo:' + str(identity),
                              'frozen_scale:' + document_sha256(scale)),
                implementation_sha256=implementation))
    return proofs
