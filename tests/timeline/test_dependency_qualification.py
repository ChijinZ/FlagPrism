"""Synthetic store fixtures exercise recommendation state, not device proof."""
from pathlib import Path
import tempfile
import unittest

from flagtree.profiler import timeline_store as store
from flagtree.profiler import timeline_perfetto as perfetto


class DependencyQualificationTests(unittest.TestCase):

    def publish(self, directory, revision):
        files = {
            'canonical.json': b'{}',
            'view.json': b'{}',
            'trace.pftrace': revision.encode()
        }
        row = dict(invocation_id='invocation',
                   observer_id='observer',
                   program_coordinates=[0, 0, 0],
                   view_file='view.json',
                   trace_file='trace.pftrace',
                   bytes=len(revision),
                   sha256=store.sha256(revision.encode()),
                   view_kind='observed_dynamic_dependencies_ns')
        return store.publish_revision(directory, dict(revision=revision),
                                      files, [row])

    def test_failure_revokes_old_recommendation_and_success_restores_it(self):
        with tempfile.TemporaryDirectory() as directory, store.export_lock(
                directory):
            rows = self.publish(directory, 'first')
            receipt = Path(directory, rows[0]['receipt_file']).read_bytes()
            store.set_dependency_qualification(directory, 'invocation', rows)
            perfetto._write_committed_index(directory)
            index = Path(directory, 'index.html').read_text()
            self.assertIn(rows[0]['trace_file'],
                          index.split('<h2>Historical')[0])
            store.set_dependency_qualification(directory, 'invocation', [],
                                               'native bindings incomplete')
            perfetto._write_committed_index(directory)
            index = Path(directory, 'index.html').read_text()
            self.assertNotIn(rows[0]['trace_file'],
                             index.split('<h2>Historical')[0])
            self.assertIn('native bindings incomplete', index)
            self.assertEqual(
                Path(directory, rows[0]['receipt_file']).read_bytes(), receipt)
            self.assertEqual(store.committed_exports(directory), rows)
            store.set_dependency_qualification(directory, 'invocation', rows)
            perfetto._write_committed_index(directory)
            self.assertIn(
                rows[0]['trace_file'],
                Path(directory,
                     'index.html').read_text().split('<h2>Historical')[0])

    def test_new_qualification_supersedes_but_preserves_old_trace(self):
        with tempfile.TemporaryDirectory() as directory, store.export_lock(
                directory):
            first = self.publish(directory, 'first')
            second = self.publish(directory, 'second')
            store.set_dependency_qualification(directory, 'invocation', second)
            perfetto._write_committed_index(directory)
            index = Path(directory, 'index.html').read_text()
            self.assertNotIn(first[0]['trace_file'],
                             index.split('<h2>Historical')[0])
            self.assertIn(second[0]['trace_file'],
                          index.split('<h2>Historical')[0])
            self.assertIn('superseded', index)
            self.assertEqual(len(store.committed_exports(directory)), 2)

    def test_foreign_or_uncommitted_exports_cannot_be_recommended(self):
        with tempfile.TemporaryDirectory() as directory, store.export_lock(
                directory):
            rows = self.publish(directory, 'first')
            for changed in (dict(rows[0], invocation_id='other'),
                            dict(rows[0], trace_file='forged')):
                with self.assertRaises(ValueError):
                    store.set_dependency_qualification(directory, 'invocation',
                                                       [changed])
            self.assertIsNone(
                store.dependency_qualification(directory, 'invocation'))


if __name__ == '__main__':
    unittest.main()
