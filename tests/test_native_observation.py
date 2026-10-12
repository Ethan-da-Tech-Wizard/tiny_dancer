# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import tempfile
import unittest
from scripts.native_observation import ProgressTracker, limit_reached, observation_delay, observation_limit
from app.tools import ROOT
from scripts.evaluate_hardening_suite import parse_options
from run.evaluate_precision_retest import parse_options as precision_options


class ObservationTests(unittest.TestCase):
    def test_continuous_run_has_no_aggregate_deadline(self):
        limit=observation_limit(900,True)
        self.assertIsNone(limit)
        for elapsed in (900,1800,86400,10**9):
            self.assertFalse(limit_reached(elapsed,limit))
            self.assertEqual(observation_delay(elapsed,limit),20)

    def test_bounded_benchmark_preserves_its_declared_stop(self):
        limit=observation_limit(900,False)
        self.assertFalse(limit_reached(899,limit));self.assertTrue(limit_reached(900,limit))
        self.assertEqual(observation_delay(899,limit),1)
        self.assertEqual(observation_delay(950,limit,stopped=True),20)

    def test_actual_evaluator_exposes_continuous_mode_and_keeps_benchmark_optional(self):
        args=parse_options(['labels','--until-terminal','--effort','low'])
        self.assertTrue(args.until_terminal);self.assertEqual(args.effort,'low')
        self.assertFalse(parse_options(['inventory','--observation-seconds','900']).until_terminal)

    def test_original_precision_observer_supports_the_same_no_deadline_policy(self):
        self.assertTrue(precision_options(['--until-terminal']).until_terminal)
        self.assertFalse(precision_options(['--observation-seconds','900']).until_terminal)

    def test_native_observers_default_to_no_aggregate_deadline(self):
        for args in (parse_options(['inventory']),precision_options([])):
            self.assertIsNone(observation_limit(args.observation_seconds,args.until_terminal))

    def test_explicit_deadline_and_continuous_policy_cannot_be_combined(self):
        import contextlib
        import io
        for parser,initial in ((parse_options,['inventory']),(precision_options,[])):
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                parser(initial+['--until-terminal','--observation-seconds','900'])

    def test_explicit_benchmark_deadline_is_validated(self):
        import contextlib
        import io
        for parser,initial in ((parse_options,['inventory']),(precision_options,[])):
            for seconds in ('59','7201'):
                with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                    parser(initial+['--observation-seconds',seconds])

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'run');self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name);self.tracker=ProgressTracker(self.folder)

    def test_tokens_turns_and_repeated_actions_are_not_changed_product_evidence(self):
        self.tracker.observe({'turns':1},0)
        result=self.tracker.observe({'turns':80},3600,{'tool_result':80})
        self.assertFalse(result['changed_evidence']);self.assertEqual(result['seconds_since_changed_evidence'],3600)
        self.assertEqual(result['action_counts']['tool_result'],80)

    def test_actual_source_change_is_observed_even_if_checkpoint_paths_stay_the_same(self):
        path=self.folder/'example.py';path.write_text('value=1\n')
        checkpoint={'edited_sources':['example.py']}
        self.tracker.observe(checkpoint,0);path.write_text('value=2\n')
        result=self.tracker.observe(checkpoint,600)
        self.assertTrue(result['changed_evidence']);self.assertEqual(result['seconds_since_changed_evidence'],0)
        self.assertFalse(self.tracker.observe(checkpoint,900)['changed_evidence'])

    def test_new_checked_plan_step_and_real_test_receipt_are_visible(self):
        self.tracker.observe({},0)
        result=self.tracker.observe({'steps':[{'title':'Build','done':True}],
                                     'latest_project_checks':{'test_count':9,'passed':True},'verified':False},120)
        self.assertTrue(result['changed_evidence']);self.assertEqual(result['completed_plan_steps'],1)
        self.assertEqual(result['latest_test_count'],9);self.assertTrue(result['latest_tests_passed'])
        self.assertFalse(result['native_verified'])

    def test_artifact_name_change_alone_does_not_count_as_better_tests(self):
        self.tracker.observe({'latest_project_checks':{'artifact':'a','test_count':6,'passed':True}},0)
        result=self.tracker.observe({'latest_project_checks':{'artifact':'b','test_count':6,'passed':True}},300)
        self.assertFalse(result['changed_evidence'])

    def test_external_and_missing_files_are_not_read_as_product_evidence(self):
        result=self.tracker.observe({'edited_sources':['/etc/hostname','missing.py','../other.py']},0)
        self.assertEqual(result['edited_files'],0)


if __name__=='__main__':unittest.main()
