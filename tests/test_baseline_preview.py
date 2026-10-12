# SPDX-License-Identifier: Apache-2.0
import json
import unittest
from app import baseline_preview as module


class ProjectionTests(unittest.TestCase):
    def test_source_outcome_paths_and_full_evidence_survive(self):
        result={'artifact':'/artifacts/full.json','exit_code':1,'runtime_notes':[{'library':'decimal'}],
                'files':[{'path':'/project/main.py','text':'PRODUCT_SOURCE'},
                         {'path':'/project/test_acceptance.py','text':'TEST_BODY'},
                         {'path':'/project/tests/helper.rs','text':'OTHER_TEST_BODY'},
                         {'path':'/project/contest.py','text':'OTHER_SOURCE'}]}
        original=json.dumps(result,sort_keys=True)
        preview=module.baseline_preview('inspect_project',result)
        self.assertEqual(json.dumps(result,sort_keys=True),original)
        self.assertEqual(preview['artifact'],result['artifact'])
        self.assertEqual(preview['runtime_notes'],result['runtime_notes'])
        self.assertEqual(preview['files'][0]['text'],'PRODUCT_SOURCE')
        self.assertEqual(preview['files'][3]['text'],'OTHER_SOURCE')
        for item in preview['files'][1:3]:
            self.assertNotIn('text',item)
            self.assertTrue(item['preview_omitted'])
            self.assertIn('read_file',item['read_hint'])

    def test_failure_status_summary_and_both_output_ends_survive(self):
        output='ERROR_SENTINEL\n'+'x'*10000+'\nRan 6 tests\nFAILED (failures=6)'
        result={'exit_code':1,'test_count':6,'failed_test_suite':True,'artifact':'/artifacts/checks.json',
                'checks':[{'command':'python -m unittest','exit_code':1,'output':output}]}
        preview=module.baseline_preview('run_checks',result)
        self.assertEqual(result['checks'][0]['output'],output)
        self.assertEqual(preview['exit_code'],1)
        self.assertEqual(preview['test_count'],6)
        self.assertTrue(preview['failed_test_suite'])
        self.assertTrue(preview['checks'][0]['output_truncated'])
        self.assertIn('ERROR_SENTINEL',preview['checks'][0]['output'])
        self.assertIn('FAILED (failures=6)',preview['checks'][0]['output'])
        self.assertLess(len(preview['checks'][0]['output']),1400)
        self.assertEqual(json.loads(json.dumps(preview)),preview)

    def test_small_output_and_missing_source_are_not_reclassified(self):
        result={'exit_code':0,'checks':[{'output':'Ran 0 tests\nOK','exit_code':0}]}
        self.assertEqual(module.baseline_preview('run_checks',result),result)
        result={'files':[{'path':'/project/test_missing.py','error':'not found'}]}
        self.assertEqual(module.baseline_preview('inspect_project',result),result)

    def test_product_inside_a_parent_named_tests_keeps_source(self):
        result={'path':'/projects/tests','files':[{'path':'/projects/tests/main.py','text':'PRODUCT'},
                {'path':'/projects/tests/test_main.py','text':'TEST_BODY'}]}
        preview=module.baseline_preview('inspect_project',result)
        self.assertEqual(preview['files'][0]['text'],'PRODUCT')
        self.assertNotIn('text',preview['files'][1])


