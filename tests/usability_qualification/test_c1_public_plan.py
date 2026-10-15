"""Synthetic typed-control budget fixtures; no device or candidate evidence."""
import copy
import unittest
import c1_public_plan as p


def entry():
    return {'binary_id':'actual-binary','module_sha256':'a'*64,'plan_kind':'control',
            'plan':{'policy':p.CONTROL_POLICY,'budget_scope':p.CONTROL_BUDGET_SCOPE,'max_sites':None,
                    'operation_max_sites_applies':False,'record_capacity_per_actor':1024,
                    'candidate_count':1,'selected_count':1,'inventory':[{'site_id':7,'selected':True,
                    'selection_reason':'requested_original_loop','public_semantic':'control_checkpoint',
                    'operation':'loop_header_occurrence'}]}}


class C1PublicPlan(unittest.TestCase):
    def test_explicit_null_control_and_empty_requested_inventory(self):
        self.assertEqual(p.selected_control_item(entry(),7,'control_checkpoint')['site_id'],7)
        e=entry(); e['plan'].update(candidate_count=0,selected_count=0,inventory=[])
        self.assertEqual(p.validate_control_entry(e),[])

    def test_operation_or_unknown_policy_cannot_use_null(self):
        for key,value in [('plan_kind','operation')]:
            e=entry(); e[key]=value
            with self.assertRaises(p.ContractError): p.validate_control_entry(e)
        for key,value in [('policy','unknown'),('budget_scope','source_operation_candidates_only'),
                          ('operation_max_sites_applies',True),('record_capacity_per_actor',None),('max_sites',8)]:
            e=entry(); e['plan'][key]=value
            with self.assertRaises(p.ContractError): p.validate_control_entry(e)
        e=entry(); del e['plan']['max_sites']
        with self.assertRaises(p.ContractError): p.validate_control_entry(e)

    def test_counts_duplicates_and_missing_semantics_rejected(self):
        for key,value in [('candidate_count',2),('selected_count',0)]:
            e=entry(); e['plan'][key]=value
            with self.assertRaises(p.ContractError): p.validate_control_entry(e)
        e=entry(); e['plan']['inventory']*=2; e['plan'].update(candidate_count=2,selected_count=2)
        with self.assertRaises(p.ContractError): p.validate_control_entry(e)
        for key in ['selection_reason','public_semantic','operation']:
            e=entry(); e['plan']['inventory'][0].pop(key)
            with self.assertRaises(p.ContractError): p.validate_control_entry(e)

    def test_unselected_or_different_site_semantic_never_skipped(self):
        e=entry(); e['plan']['inventory'][0]['selected']=False; e['plan']['selected_count']=0
        with self.assertRaises(p.ContractError): p.selected_control_item(e,7,'control_checkpoint')
        with self.assertRaises(p.ContractError): p.selected_control_item(entry(),8,'control_checkpoint')
        with self.assertRaises(p.ContractError): p.selected_control_item(entry(),7,'operation_checkpoint')


if __name__=='__main__': unittest.main()
