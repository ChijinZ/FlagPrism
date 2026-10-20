"""Source navigation must keep fused regions and real endpoints intact."""
import copy
import unittest

from flagtree.profiler.timeline_events_enflame_native import _member_navigation


class SourceMembers(unittest.TestCase):

    def row(self):
        return dict(
            source_membership=dict(schema_version=1,
                                   status='original_execution_members_indexed',
                                   members=[
                                       dict(operation_index=17,
                                            source_op_id=15,
                                            scope_id=1,
                                            file='/source with spaces.py',
                                            line=13,
                                            column=4)
                                   ]))

    def test_original_members_preserve_identity_and_deduplicate_coordinates(
            self):
        row = self.row()
        row['source_membership']['members'].append(
            dict(row['source_membership']['members'][0],
                 operation_index=18,
                 source_op_id=18))
        before = copy.deepcopy(row)
        self.assertEqual(_member_navigation(row, [0, 0]),
                         (['loc("/source with spaces.py":13:4)'], [15, 18]))
        self.assertEqual(row, before)

    def test_unknown_and_unverified_members_never_fabricate_coordinates(self):
        row = self.row()
        for filename in ('', '-', '<unknown>'):
            row['source_membership']['members'][0]['file'] = filename
            self.assertEqual(_member_navigation(row, [0, 0])[0], [])
        row['source_membership']['status'] = 'unverified'
        self.assertEqual(_member_navigation(row, [0, 0]), ([], []))
        self.assertEqual(_member_navigation({}, [0, 0]), ([], []))

    def test_duplicate_identity_and_invalid_coordinates_are_rejected(self):
        row = self.row()
        member = row['source_membership']['members'][0]
        for field, value in [('source_op_id', True), ('scope_id', -1),
                             ('line', True), ('column', -1),
                             ('file', 'x' * 4097)]:
            invalid = copy.deepcopy(row)
            invalid['source_membership']['members'][0][field] = value
            with self.assertRaises(ValueError):
                _member_navigation(invalid, [0, 0])
        row['source_membership']['members'].append(dict(member))
        with self.assertRaises(ValueError):
            _member_navigation(row, [0, 0])

    def test_aggregate_resource_bounds_are_shared_across_sites(self):
        for budget in ([100000, 0], [0, 4 * 1024 * 1024]):
            with self.assertRaisesRegex(ValueError, 'budget'):
                _member_navigation(self.row(), budget)


if __name__ == '__main__':
    unittest.main()
