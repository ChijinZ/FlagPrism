"""CPU synthetic exact-visit acceptance/rejection fixtures, not device evidence."""
import unittest
import check_dynamic_report as d


def records(counts):
    return [dict(site=site,invocation_id=inv,program=0,actor=0,occurrence=visit)
            for site,inv,count in counts for visit in range(count)]


class DynamicChecks(unittest.TestCase):
    def test_single_visits_do_not_demonstrate_loop(self):
        with self.assertRaises(d.common.ContractError):
            d.exact_runtime_sites(records([(3,'a',1),(3,'b',1)]))

    def test_static_identity_splits_do_not_demonstrate_one_site(self):
        with self.assertRaises(d.common.ContractError):
            d.exact_runtime_sites(records([(3,'a',2),(4,'b',5)]))

    def test_exact_body_or_header_with_repeated_occurrences(self):
        self.assertEqual(d.exact_runtime_sites(records([(3,'a',2),(3,'b',5)])),[3])
        self.assertEqual(d.exact_runtime_sites(records([(4,'a',3),(4,'b',6)])),[4])
        duplicated=records([(3,'a',2),(3,'b',5)])*2
        self.assertEqual(d.exact_runtime_sites(duplicated),[3])


if __name__=='__main__': unittest.main()
