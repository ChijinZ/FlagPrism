"""Publication/recovery contracts. Synthetic fixtures are not device evidence."""
import copy
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from flagtree.profiler import timeline_store as store
from flagtree.profiler import timeline_perfetto as perfetto
from flagtree.profiler.timeline_views import CounterUnitProof, derive_counter_ns_views


def fixture():
    path = Path(__file__).with_name('test_timeline_perfetto.py')
    spec = importlib.util.spec_from_file_location('counter_fixture', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    batch = module.batch_fixture()
    return batch, module.proof_for(batch)


def publish(root, batch, proof):
    return perfetto.write_counter_exports(root, Path('captures')/'test',
        derive_counter_ns_views(batch, [proof]), batch, proofs=[proof])


class TimelineStoreTests(unittest.TestCase):
    def test_provider_enumeration_order_does_not_change_revision_or_receipt(self):
        batch, proof = fixture()
        second = copy.deepcopy(batch['observers'][0])
        second['id'] += '-second';second['local_id'] = 'second'
        second['program_coordinates'] = [1, 0, 0]
        second['clock_domain_id'] += '-second';second['epoch_id'] += '-second'
        extra_records = []
        for record in batch['records']:
            row = dict(record, id=record['id']+'-second', observer_id=second['id'],
                       offset=record['offset']+batch['raw_artifact']['bytes'])
            extra_records.append(row)
        extra_events = [dict(event, id=event['id']+'-second', observer_id=second['id'],
            record_ids=[key+'-second' for key in event['record_ids']]) for event in batch['events']]
        batch['raw_artifact']['bytes'] *= 2
        batch['observers'].append(second)
        batch['records'].extend(extra_records);batch['events'].extend(extra_events)
        args = asdict(proof);args['observer_id'] = second['id']
        proofs = [proof, CounterUnitProof(**args)]
        views = derive_counter_ns_views(batch, proofs)
        with tempfile.TemporaryDirectory() as directory:
            first = perfetto.write_counter_exports(directory, Path('capture'), views,
                batch, proofs=proofs)
            second = perfetto.write_counter_exports(directory, Path('capture'), views[::-1],
                batch, proofs=proofs[::-1])
            self.assertEqual(first, second)
            self.assertEqual(len(store.committed_exports(directory)), 2)

    def test_idempotent_and_new_proof_preserves_first_revision(self):
        batch, proof = fixture()
        before = copy.deepcopy(batch)
        with tempfile.TemporaryDirectory() as directory:
            first = publish(directory, batch, proof)
            old = {str(p):p.read_bytes() for p in Path(directory).rglob('*') if p.is_file()}
            self.assertEqual(publish(directory, batch, proof), first)
            args = asdict(proof);args['period_numerator_ns'] = 2
            second = publish(directory, batch, CounterUnitProof(**args))
            self.assertNotEqual(first[0]['revision_id'], second[0]['revision_id'])
            for path, raw in old.items():
                if not path.endswith('index.html'):
                    self.assertEqual(Path(path).read_bytes(), raw)
            self.assertEqual(len(store.committed_exports(directory)), 2)
            index = (Path(directory)/'index.html').read_text()
            self.assertTrue(all(row[0]['trace_file'] in index for row in [first, second]))
        self.assertEqual(batch, before)

    def test_recomputed_forged_view_cannot_supply_its_own_proof(self):
        batch, proof = fixture()
        args = asdict(proof);args['period_numerator_ns'] = 2
        forged = derive_counter_ns_views(batch, [CounterUnitProof(**args)])[0]
        with self.assertRaises(ValueError):
            perfetto.validate_counter_view(forged, batch, proof)

    def test_implementation_fingerprint_changes_revision_without_version_bump(self):
        batch, proof = fixture()
        with tempfile.TemporaryDirectory() as directory:
            args = asdict(proof);args['implementation_sha256'] = 'a'*64
            first = publish(directory, batch, CounterUnitProof(**args))
            args['implementation_sha256'] = 'b'*64
            second = publish(directory, batch, CounterUnitProof(**args))
            self.assertNotEqual(first[0]['revision_id'], second[0]['revision_id'])

    def test_interrupted_before_receipt_is_hidden_and_retry_completes(self):
        batch, proof = fixture()
        original = store.persist
        def fail_receipt(directory, relative, payload, **kwargs):
            if relative.endswith('/complete.json'):
                raise OSError('controlled receipt publication failure')
            return original(directory, relative, payload, **kwargs)
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(store, 'persist', fail_receipt), self.assertRaises(OSError):
                publish(directory, batch, proof)
            self.assertTrue(list(Path(directory).rglob('*.pftrace')))
            self.assertEqual(store.committed_exports(directory), [])
            saved = {str(p):p.read_bytes() for p in Path(directory).rglob('*.pftrace')}
            row = publish(directory, batch, proof)[0]
            self.assertIn(row['trace_file'], (Path(directory)/'index.html').read_text())
            for name, raw in saved.items():
                self.assertEqual(Path(name).read_bytes(), raw)

    def test_receipt_committed_before_index_failure_is_rediscovered(self):
        batch, proof = fixture()
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(perfetto, '_write_committed_index', side_effect=OSError('controlled index failure')):
                with self.assertRaises(OSError):
                    publish(directory, batch, proof)
            self.assertEqual(len(store.committed_exports(directory)), 1)
            perfetto.write_trace_index(directory, [])
            row = publish(directory, batch, proof)[0]
            self.assertIn(row['trace_file'], (Path(directory)/'index.html').read_text())

    def test_changed_committed_bytes_are_not_silently_repaired(self):
        batch, proof = fixture()
        with tempfile.TemporaryDirectory() as directory:
            row = publish(directory, batch, proof)[0]
            path = Path(directory)/row['trace_file'];path.write_bytes(b'corrupted fixture')
            with self.assertRaises(ValueError):
                publish(directory, batch, proof)
            self.assertEqual(path.read_bytes(), b'corrupted fixture')

    def test_path_and_lock_inputs_are_explicitly_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ['/tmp/outside', '../outside', 'a/../outside', './x', 'a//b', 'a\\b']:
                with self.assertRaises(ValueError):
                    store.bundle_path(directory, name)
            (Path(directory)/'link').symlink_to('/tmp')
            with self.assertRaises(ValueError):
                store.bundle_path(directory, 'link/outside')
            for timeout in [True, 0, float('nan'), float('inf'), 61]:
                with self.assertRaises(ValueError), store.export_lock(directory, timeout):
                    self.fail('Invalid lock input was accepted')

    def test_lock_timeout_and_process_exit_release(self):
        with tempfile.TemporaryDirectory() as directory:
            code = ("import sys;from flagtree.profiler.timeline_store import export_lock;"
                    "\nwith export_lock(sys.argv[1]):\n print('LOCKED',flush=True);sys.stdin.read()")
            child = subprocess.Popen([sys.executable, '-I', '-c', code, directory],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                ready, _, _ = select.select([child.stdout], [], [], 10)
                self.assertTrue(ready, 'Owned lock subprocess did not start')
                self.assertEqual(child.stdout.readline(), b'LOCKED\n')
                with self.assertRaises(TimeoutError), store.export_lock(directory, timeout=0.03):
                    self.fail('Another process owns the lock')
                child.terminate();child.wait(timeout=10)
                with store.export_lock(directory, timeout=0.1):
                    pass
            finally:
                if child.poll() is None:
                    child.kill();child.wait(timeout=10)
                for stream in [child.stdin, child.stdout, child.stderr]:
                    stream.close()

    def test_two_fresh_processes_publish_without_lost_index_entries(self):
        batch, proof = fixture()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'fixture.json'
            source.write_text(json.dumps(dict(batch=batch, proof=asdict(proof))))
            code = '''import sys,json
from pathlib import Path
from flagtree.profiler.timeline_views import CounterUnitProof,derive_counter_ns_views
from flagtree.profiler.timeline_perfetto import write_counter_exports
d=json.loads(Path(sys.argv[1]).read_text());p=d['proof'];p['evidence_ids']=tuple(p['evidence_ids']);p['period_numerator_ns']=int(sys.argv[2]);p=CounterUnitProof(**p)
write_counter_exports(Path(sys.argv[1]).parent,Path('captures')/'fixture',derive_counter_ns_views(d['batch'],[p]),d['batch'],proofs=[p])
'''
            children = [subprocess.Popen([sys.executable, '-I', '-c', code, str(source), str(period)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE) for period in (1, 2)]
            try:
                for child in children:
                    _, error = child.communicate(timeout=20)
                    self.assertEqual(child.returncode, 0, error.decode())
                rows = store.committed_exports(directory)
                self.assertEqual(len(rows), 2)
                index = (Path(directory)/'index.html').read_text()
                self.assertTrue(all(row['trace_file'] in index for row in rows))
            finally:
                for child in children:
                    if child.poll() is None:
                        child.kill();child.wait(timeout=10)
                    for stream in (child.stdout, child.stderr):
                        stream.close()


if __name__ == '__main__':
    unittest.main()
