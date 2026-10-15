"""Synthetic contract rejection tests; never substitute for actual device evidence."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import check_common_report as c


class PublicChecker(unittest.TestCase):
    def test_clock_requires_conversion_evidence(self):
        row = dict(clock=None, start_tick=1, end_tick=3, duration_ticks=2,
                   duration_ns=4, relative_start_ns=None)
        with self.assertRaises(c.ContractError):
            c.verify_clock(row)
        row['clock'] = dict(domain='device', scope='actor', alignment='unknown', tick_ns=2)
        c.verify_clock(row)
        row['duration_ns'] = 5
        with self.assertRaises(c.ContractError):
            c.verify_clock(row)
        row['duration_ns'] = 4
        row['clock']['alignment'] = 'verified_shared'
        with self.assertRaises(c.ContractError):
            c.verify_clock(row)

    def test_primitive_accounting_does_not_accept_interval_counts(self):
        cap = dict(decoded=dict(losses=[dict(program=0, sm=0, warp=0,
                    written_records=4, retained_records=4, dropped_records=0, capacity_records=8)],
                    unpaired_records=[], dropped_records=0))
        self.assertEqual(c.verify_loss(cap, 'nvidia')['primitive_records_retained'], 4)
        cap['decoded']['losses'][0]['written_records'] = 2
        with self.assertRaises(c.ContractError):
            c.verify_loss(cap, 'nvidia')

    def test_actor_loss_and_false_unexecuted_rejected(self):
        cap = dict(capture_status='decoded', decode_error=None, counter_saturated=False,
                   actors=[dict(state='committed', attempted=2, committed=2, dropped=0)], dropped=0)
        c.verify_loss(cap, 'ascend')
        cap['actors'][0].update(attempted=3, dropped=1)
        with self.assertRaises(c.ContractError):
            c.verify_loss(cap, 'ascend')
        cap['actors'][0] = dict(state='no_records', attempted=0, committed=0, dropped=0,
                               execution_status='unexecuted')
        with self.assertRaises(c.ContractError):
            c.verify_loss(cap, 'ascend')

    def test_sampling_is_distinct_from_overflow(self):
        cap = dict(capture_status='decoded', decode_error=None, counter_saturated=False,
                   record_layout='selected_dynamic_timeline_v1',
                   header=dict(write_idx=4, capacity=8, overflow_count=0, flags=0, reserved0=4))
        c.verify_loss(cap, 'enflame')
        cap['header']['reserved0'] = 8
        with self.assertRaisesRegex(c.ContractError, 'sampled'):
            c.verify_loss(cap, 'enflame')
        cap['header'].update(reserved0=9, write_idx=9, overflow_count=0)
        with self.assertRaisesRegex(c.ContractError, 'overflow arithmetic'):
            c.verify_loss(cap, 'enflame')

    def test_manifest_hash_and_complete_file_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'raw').mkdir()
            (root / 'raw' / 'capture').write_bytes(b'evidence')
            manifest = dict(files={'raw/capture': dict(bytes=8, sha256=hashlib.sha256(b'evidence').hexdigest())})
            (root / 'manifest.json').write_text(json.dumps(manifest))
            c.verify_manifest(root)
            (root / 'extra').write_text('unlisted')
            with self.assertRaisesRegex(c.ContractError, 'complete bundle'):
                c.verify_manifest(root)
            (root / 'extra').unlink()
            (root / 'raw' / 'capture').write_bytes(b'tampered')
            with self.assertRaisesRegex(c.ContractError, 'hash mismatch'):
                c.verify_manifest(root)

    def test_manifest_paths_and_primitive_types_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(c.ContractError):
                c.inside(Path(tmp), '../escape')
        self.assertFalse(c.integer(True))
        self.assertFalse(c.number(float('nan')))
        self.assertFalse(c.preserves({'captures': []}, {'captures': [{'id': 'raw'}]}))


if __name__ == '__main__':
    unittest.main()
