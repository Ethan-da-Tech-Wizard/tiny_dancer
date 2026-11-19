# ==============================================================================
# Program: test_native_observation.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Automated test suite verifying functional correctness, regression
#          resistance, boundary conditions, and edge cases. Automated regression and
#          functional assertion test suite verifying system stability, edge-case
#          resilience, and contract invariants. Exercises mathematical boundary
#          conditions, state graph branch coverage, and mock failure modes within
#          isolated execution fixtures. Enforces deterministic test assertions and
#          hermetic runtime lifecycle management.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import tempfile
import unittest
from scripts.native_observation import ProgressTracker, limit_reached, observation_delay, observation_limit
from app.tools import ROOT
from scripts.evaluate_hardening_suite import parse_options
from run.evaluate_precision_retest import parse_options as precision_options


# ------------------------------------------------------------------------------
# ObservationTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class ObservationTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # test_continuous_run_has_no_aggregate_deadline: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_continuous_run_has_no_aggregate_deadline(self):
        limit=observation_limit(900,True)
        self.assertIsNone(limit)
        for elapsed in (900,1800,86400,10**9):
            self.assertFalse(limit_reached(elapsed,limit))
            self.assertEqual(observation_delay(elapsed,limit),20)

    # ------------------------------------------------------------------------------
    # test_bounded_benchmark_preserves_its_declared_stop: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_bounded_benchmark_preserves_its_declared_stop(self):
        limit=observation_limit(900,False)
        self.assertFalse(limit_reached(899,limit));self.assertTrue(limit_reached(900,limit))
        self.assertEqual(observation_delay(899,limit),1)
        self.assertEqual(observation_delay(950,limit,stopped=True),20)

    # ------------------------------------------------------------------------------
    # test_actual_evaluator_exposes_continuous_mode_and_keeps_benchmark_optional: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_actual_evaluator_exposes_continuous_mode_and_keeps_benchmark_optional(self):
        args=parse_options(['labels','--until-terminal','--effort','low'])
        self.assertTrue(args.until_terminal);self.assertEqual(args.effort,'low')
        self.assertFalse(parse_options(['inventory','--observation-seconds','900']).until_terminal)

    # ------------------------------------------------------------------------------
    # test_original_precision_observer_supports_the_same_no_deadline_policy: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_original_precision_observer_supports_the_same_no_deadline_policy(self):
        self.assertTrue(precision_options(['--until-terminal']).until_terminal)
        self.assertFalse(precision_options(['--observation-seconds','900']).until_terminal)

    # ------------------------------------------------------------------------------
    # test_native_observers_default_to_no_aggregate_deadline: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_native_observers_default_to_no_aggregate_deadline(self):
        for args in (parse_options(['inventory']),precision_options([])):
            self.assertIsNone(observation_limit(args.observation_seconds,args.until_terminal))

    # ------------------------------------------------------------------------------
    # test_explicit_deadline_and_continuous_policy_cannot_be_combined: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_explicit_deadline_and_continuous_policy_cannot_be_combined(self):
        import contextlib
        import io
        for parser,initial in ((parse_options,['inventory']),(precision_options,[])):
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                parser(initial+['--until-terminal','--observation-seconds','900'])

    # ------------------------------------------------------------------------------
    # test_explicit_benchmark_deadline_is_validated: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_explicit_benchmark_deadline_is_validated(self):
        import contextlib
        import io
        for parser,initial in ((parse_options,['inventory']),(precision_options,[])):
            for seconds in ('59','7201'):
                with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                    parser(initial+['--observation-seconds',seconds])

    # ------------------------------------------------------------------------------
    # setUp: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'run');self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name);self.tracker=ProgressTracker(self.folder)

    # ------------------------------------------------------------------------------
    # test_tokens_turns_and_repeated_actions_are_not_changed_product_evidence: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_tokens_turns_and_repeated_actions_are_not_changed_product_evidence(self):
        self.tracker.observe({'turns':1},0)
        result=self.tracker.observe({'turns':80},3600,{'tool_result':80})
        self.assertFalse(result['changed_evidence']);self.assertEqual(result['seconds_since_changed_evidence'],3600)
        self.assertEqual(result['action_counts']['tool_result'],80)

    # ------------------------------------------------------------------------------
    # test_actual_source_change_is_observed_even_if_checkpoint_paths_stay_the_same: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_actual_source_change_is_observed_even_if_checkpoint_paths_stay_the_same(self):
        path=self.folder/'example.py';path.write_text('value=1\n')
        checkpoint={'edited_sources':['example.py']}
        self.tracker.observe(checkpoint,0);path.write_text('value=2\n')
        result=self.tracker.observe(checkpoint,600)
        self.assertTrue(result['changed_evidence']);self.assertEqual(result['seconds_since_changed_evidence'],0)
        self.assertFalse(self.tracker.observe(checkpoint,900)['changed_evidence'])

    # ------------------------------------------------------------------------------
    # test_new_checked_plan_step_and_real_test_receipt_are_visible: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_new_checked_plan_step_and_real_test_receipt_are_visible(self):
        self.tracker.observe({},0)
        result=self.tracker.observe({'steps':[{'title':'Build','done':True}],
                                     'latest_project_checks':{'test_count':9,'passed':True},'verified':False},120)
        self.assertTrue(result['changed_evidence']);self.assertEqual(result['completed_plan_steps'],1)
        self.assertEqual(result['latest_test_count'],9);self.assertTrue(result['latest_tests_passed'])
        self.assertFalse(result['native_verified'])

    # ------------------------------------------------------------------------------
    # test_artifact_name_change_alone_does_not_count_as_better_tests: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_artifact_name_change_alone_does_not_count_as_better_tests(self):
        self.tracker.observe({'latest_project_checks':{'artifact':'a','test_count':6,'passed':True}},0)
        result=self.tracker.observe({'latest_project_checks':{'artifact':'b','test_count':6,'passed':True}},300)
        self.assertFalse(result['changed_evidence'])

    # ------------------------------------------------------------------------------
    # test_external_and_missing_files_are_not_read_as_product_evidence: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_external_and_missing_files_are_not_read_as_product_evidence(self):
        result=self.tracker.observe({'edited_sources':['/etc/hostname','missing.py','../other.py']},0)
        self.assertEqual(result['edited_files'],0)


if __name__=='__main__':unittest.main()
