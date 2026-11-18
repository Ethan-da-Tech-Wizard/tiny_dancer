# Program: tiny_dancer - tests/test_native_observation.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Tests for native observation (exercises app.tools, scripts.evaluate_hardening_suite, scripts.native_observation).
# SPDX-License-Identifier: Apache-2.0
"""Tests for native observation (exercises app.tools, scripts.evaluate_hardening_suite, scripts.native_observation)."""
from pathlib import Path
import tempfile
import unittest
from scripts.native_observation import ProgressTracker, limit_reached, observation_delay, observation_limit
from app.tools import ROOT
from scripts.evaluate_hardening_suite import parse_options
from run.evaluate_precision_retest import parse_options as precision_options


# -------- observation tests --------
class ObservationTests(unittest.TestCase):
    """Test group for observation."""
    def test_continuous_run_has_no_aggregate_deadline(self):
        """Checks that continuous run has no aggregate deadline."""
        limit=observation_limit(900,True)
        self.assertIsNone(limit)
        for elapsed in (900,1800,86400,10**9):
            self.assertFalse(limit_reached(elapsed,limit))
            self.assertEqual(observation_delay(elapsed,limit),20)

    def test_bounded_benchmark_preserves_its_declared_stop(self):
        """Checks that bounded benchmark preserves its declared stop."""
        limit=observation_limit(900,False)
        self.assertFalse(limit_reached(899,limit));self.assertTrue(limit_reached(900,limit))
        self.assertEqual(observation_delay(899,limit),1)
        self.assertEqual(observation_delay(950,limit,stopped=True),20)

    def test_actual_evaluator_exposes_continuous_mode_and_keeps_benchmark_optional(self):
        """Checks that actual evaluator exposes continuous mode and keeps benchmark optional."""
        args=parse_options(['labels','--until-terminal','--effort','low'])
        self.assertTrue(args.until_terminal);self.assertEqual(args.effort,'low')
        self.assertFalse(parse_options(['inventory','--observation-seconds','900']).until_terminal)

    def test_original_precision_observer_supports_the_same_no_deadline_policy(self):
        """Checks that original precision observer supports the same no deadline policy."""
        self.assertTrue(precision_options(['--until-terminal']).until_terminal)
        self.assertFalse(precision_options(['--observation-seconds','900']).until_terminal)

    def test_native_observers_default_to_no_aggregate_deadline(self):
        """Checks that native observers default to no aggregate deadline."""
        for args in (parse_options(['inventory']),precision_options([])):
            self.assertIsNone(observation_limit(args.observation_seconds,args.until_terminal))

    def test_explicit_deadline_and_continuous_policy_cannot_be_combined(self):
        """Checks that explicit deadline and continuous policy cannot be combined."""
        import contextlib
        import io
        for parser,initial in ((parse_options,['inventory']),(precision_options,[])):
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                parser(initial+['--until-terminal','--observation-seconds','900'])

    def test_explicit_benchmark_deadline_is_validated(self):
        """Checks that explicit benchmark deadline is validated."""
        import contextlib
        import io
        for parser,initial in ((parse_options,['inventory']),(precision_options,[])):
            for seconds in ('59','7201'):
                with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                    parser(initial+['--observation-seconds',seconds])

    def setUp(self):
        """Prepare the fixtures for each test."""
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'run');self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name);self.tracker=ProgressTracker(self.folder)

    def test_tokens_turns_and_repeated_actions_are_not_changed_product_evidence(self):
        """Checks that tokens turns and repeated actions are not changed product evidence."""
        self.tracker.observe({'turns':1},0)
        result=self.tracker.observe({'turns':80},3600,{'tool_result':80})
        self.assertFalse(result['changed_evidence']);self.assertEqual(result['seconds_since_changed_evidence'],3600)
        self.assertEqual(result['action_counts']['tool_result'],80)

    def test_actual_source_change_is_observed_even_if_checkpoint_paths_stay_the_same(self):
        """Checks that actual source change is observed even if checkpoint paths stay the same."""
        path=self.folder/'example.py';path.write_text('value=1\n')
        checkpoint={'edited_sources':['example.py']}
        self.tracker.observe(checkpoint,0);path.write_text('value=2\n')
        result=self.tracker.observe(checkpoint,600)
        self.assertTrue(result['changed_evidence']);self.assertEqual(result['seconds_since_changed_evidence'],0)
        self.assertFalse(self.tracker.observe(checkpoint,900)['changed_evidence'])

    def test_new_checked_plan_step_and_real_test_receipt_are_visible(self):
        """Checks that new checked plan step and real test receipt are visible."""
        self.tracker.observe({},0)
        result=self.tracker.observe({'steps':[{'title':'Build','done':True}],
                                     'latest_project_checks':{'test_count':9,'passed':True},'verified':False},120)
        self.assertTrue(result['changed_evidence']);self.assertEqual(result['completed_plan_steps'],1)
        self.assertEqual(result['latest_test_count'],9);self.assertTrue(result['latest_tests_passed'])
        self.assertFalse(result['native_verified'])

    def test_artifact_name_change_alone_does_not_count_as_better_tests(self):
        """Checks that artifact name change alone does not count as better tests."""
        self.tracker.observe({'latest_project_checks':{'artifact':'a','test_count':6,'passed':True}},0)
        result=self.tracker.observe({'latest_project_checks':{'artifact':'b','test_count':6,'passed':True}},300)
        self.assertFalse(result['changed_evidence'])

    def test_external_and_missing_files_are_not_read_as_product_evidence(self):
        """Checks that external and missing files are not read as product evidence."""
        result=self.tracker.observe({'edited_sources':['/etc/hostname','missing.py','../other.py']},0)
        self.assertEqual(result['edited_files'],0)


if __name__=='__main__':unittest.main()
