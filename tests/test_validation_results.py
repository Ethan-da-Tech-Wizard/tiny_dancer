# SPDX-License-Identifier: Apache-2.0
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.validation_results import archive_report,collect_results,evidence_path,refresh_results,evaluation_row


class ResultsHistoryTests(unittest.TestCase):
    def setUp(self): self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);(self.root/'docs/validation/runs').mkdir(parents=True);(self.root/'logs').mkdir()
    def tearDown(self): self.temp.cleanup()
    def test_unregistered_current_report_does_not_hide_its_only_archived_evidence(self):
        path=self.root/'docs/new-tool-validation.json'
        path.write_text(json.dumps({'at':'2026-10-10','passed':True,'checks':{'actual_tool':True}}))
        archived=archive_report(self.root,path.name,'automated','New local tool','Real handler check, no native generation')
        index=collect_results(self.root)
        self.assertEqual(len(index['results']),1)
        row=index['results'][0]
        self.assertEqual(row['status'],'passed');self.assertEqual(row['tests'],1)
        self.assertEqual(evidence_path(self.root,row['id'],index),archived)
    def test_pass_failure_running_and_native_pause_are_distinct_and_preserved(self):
        for number,status in enumerate(('passed','failed','running')):
            report={'title':'Run '+str(number),'started_at':'2026-10-10T20:0'+str(number)+':00+00:00','status':status,'scope':'scripted fixtures','tests_run':4}
            (self.root/'docs/validation/runs'/f'{number}.json').write_text(json.dumps(report))
        (self.root/'docs/native-coding-validation.json').write_text(json.dumps({'started_at':'2026-10-10T19:00:00+00:00','status':'paused','passed':False,'operator_interventions':[]}))
        index=refresh_results(self.root);self.assertEqual(len(index['results']),4)
        self.assertEqual({row['status'] for row in index['results']},{'passed','failed','running','paused'})
        self.assertIn('**failed**',(self.root/'docs/TEST_RESULTS.md').read_text());self.assertIn('**paused**',(self.root/'docs/TEST_RESULTS.md').read_text())
    def test_unknown_and_outside_evidence_paths_are_rejected(self):
        with self.assertRaises(ValueError): evidence_path(self.root,'../../access-token',{'evidence':{}})
        with self.assertRaises(ValueError): evidence_path(self.root,'bad',{'evidence':{'bad':'../../etc/passwd'}})
    def test_known_evidence_can_be_read_and_partial_json_does_not_crash(self):
        (self.root/'docs/validation/runs/partial.json').write_text('{')
        (self.root/'logs/curated-harness-final-tests.log').write_text('Ran 87 tests in 8.854s\n\nOK\n')
        index=collect_results(self.root);self.assertEqual(len(index['results']),1)
        path=evidence_path(self.root,index['results'][0]['id'],index);self.assertEqual(path.suffix,'.log')
    def test_native_archive_preserves_previous_outcome_when_current_report_is_replaced(self):
        path=self.root/'docs/batching-native-validation.json'
        path.write_text(json.dumps({'started_at':'2026-10-10T19:00:00+00:00','status':'complete','passed':False,'job':'old'}))
        archived=archive_report(self.root,path.name,'native','Old repair','Frozen native run')
        original=archived.read_bytes()
        self.assertEqual(len(collect_results(self.root)['results']),1)
        path.write_text(json.dumps({'started_at':'2026-10-10T20:00:00+00:00','status':'complete','passed':True,'job':'new'}))
        index=collect_results(self.root);self.assertEqual(len(index['results']),2)
        self.assertEqual({r['status'] for r in index['results']},{'passed','failed'})
        self.assertEqual(archived.read_bytes(),original)
        old=next(r for r in index['results'] if r['id'].startswith('archive-'))
        self.assertEqual(json.loads(evidence_path(self.root,old['id'],index).read_text())['job'],'old')
    def test_running_native_reports_cannot_be_archived_and_live_ui_checks_are_counted(self):
        path=self.root/'docs/batching-native-validation.json';path.write_text(json.dumps({'status':'running'}))
        with self.assertRaises(ValueError): archive_report(self.root,path.name,'native','Repair','Not done')
        (self.root/'docs/results-ui-validation.json').write_text(json.dumps({'at':'2026-10-10','passed':True,'checks':{'auth':True,'desktop':True}}))
        row=next(r for r in collect_results(self.root)['results'] if r['id'].startswith('integration-'))
        self.assertEqual(row['status'],'passed');self.assertEqual(row['tests'],2)
    def test_simultaneous_evaluation_refreshes_keep_complete_index_and_readable_report(self):
        (self.root/'docs/results-ui-validation.json').write_text(json.dumps({'at':'2026-10-10','passed':True,'checks':{'auth':True}}))
        with ThreadPoolExecutor(max_workers=8) as workers:
            results=list(workers.map(lambda _:refresh_results(self.root),range(16)))
        self.assertTrue(all(len(index['results'])==1 for index in results))
        self.assertEqual(len(json.loads((self.root/'docs/validation/index.json').read_text())['results']),1)
        self.assertIn('Results page and authentication',(self.root/'docs/TEST_RESULTS.md').read_text())
        self.assertEqual(list((self.root/'docs/validation').glob('*.tmp')),[])
    def test_running_native_row_uses_public_elapsed_turn_and_prompt_measurements(self):
        (self.root/'docs/batching-native-validation.json').write_text(json.dumps({'started_at':'2026-10-10','status':'running','samples':[{'elapsed_seconds':0,'turns':1,'progress':None},{'elapsed_seconds':42,'turns':2,'progress':{'kind':'inference','data':{'prompt_tokens':895}}}]}))
        row=collect_results(self.root)['results'][0]
        self.assertEqual((row['seconds'],row['turns'],row['prompt_tokens']),(42,2,895))
    def test_submitted_but_failed_evaluation_shows_failure_and_duration(self):
        path=self.root/'docs/pi-example.json'
        path.write_text(json.dumps({'started_at':'2026-10-12','status':'submitted','passed':False,'seconds':137.49,
            'events':[{'type':'inference'},{'type':'tool_execution_start'},{'type':'inference'}]}))
        archive_report(self.root,path.name,'native','Comparison','Actual local model')
        row=refresh_results(self.root)['results'][0]
        self.assertEqual((row['status'],row['seconds'],row['turns']),('failed',137.49,2))
        self.assertIn('**failed**',(self.root/'docs/TEST_RESULTS.md').read_text())
        self.assertIn('137.49',(self.root/'docs/TEST_RESULTS.md').read_text())
    def test_active_placeholder_failure_cannot_be_archived(self):
        for status in ('starting','running','queued'):
            path=self.root/'docs/active.json';path.write_text(json.dumps({'status':status,'passed':False}))
            with self.subTest(status=status),self.assertRaises(ValueError):
                archive_report(self.root,path.name,'native','Active task','Unfinished')
    def test_checked_at_and_named_test_count_are_visible(self):
        path=self.root/'docs/extra-integration.json'
        path.write_text(json.dumps({'checked_at':'2026-10-12T03:00:00Z','passed':True,'tests':9,'seconds':0.807}))
        archive_report(self.root,path.name,'integration','Local CLI preflight','Scripted endpoint')
        row=collect_results(self.root)['results'][0]
        self.assertEqual((row['at'],row['tests'],row['seconds']),('2026-10-12T03:00:00Z',9,0.807))
        self.assertEqual(row['kind'],'automated')
    def test_historical_categories_reach_visible_ui_lanes(self):
        for category in ('regression','tools','integration','fixtures','evaluation','native','automated'):
            with self.subTest(category=category):
                row=evaluation_row('saved',{'passed':False},'Past check','Original scope',category)
                self.assertEqual(row['kind'],'native' if category in ('evaluation','native') else 'automated')
                self.assertEqual(row['report_kind'],category)
