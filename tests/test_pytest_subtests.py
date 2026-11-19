# ==============================================================================
# Program: test_pytest_subtests.py
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
"""Current pytest subtest summaries must preserve real pass/failure evidence."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from app.verification import test_summary


# ------------------------------------------------------------------------------
# PytestSubtestTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class PytestSubtestTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # test_actual_native_passing_footer_is_recognized: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_actual_native_passing_footer_is_recognized(self):
        self.assertEqual(test_summary('12 passed, 8 subtests passed in 0.36s\n'),
                         {'count':12,'passed':True,'empty':False,'failed':False})

    # ------------------------------------------------------------------------------
    # test_actual_native_failed_footer_is_recognized: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_actual_native_failed_footer_is_recognized(self):
        self.assertEqual(test_summary('1 failed, 11 passed, 8 subtests passed in 0.36s\n'),
                         {'count':11,'passed':False,'empty':False,'failed':True})

    # ------------------------------------------------------------------------------
    # test_subcases_are_not_counted_as_extra_top_level_tests: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_subcases_are_not_counted_as_extra_top_level_tests(self):
        self.assertEqual(test_summary('1 passed, 50 subtests passed, 1 skipped in 0.1s')['count'],1)

    # ------------------------------------------------------------------------------
    # test_failed_subcase_cannot_be_hidden_by_a_passing_primary_count: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_failed_subcase_cannot_be_hidden_by_a_passing_primary_count(self):
        result=test_summary('1 passed, 1 subtests failed in 0.1s')
        self.assertIsNotNone(result);self.assertTrue(result['failed']);self.assertFalse(result['passed'])

    # ------------------------------------------------------------------------------
    # test_all_skipped_subcases_do_not_establish_nonempty_passing_tests: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_all_skipped_subcases_do_not_establish_nonempty_passing_tests(self):
        result=test_summary('1 skipped, 8 subtests skipped in 0.1s')
        self.assertIsNotNone(result);self.assertTrue(result['empty']);self.assertFalse(result['passed'])

    # ------------------------------------------------------------------------------
    # invoke: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def invoke(self,values):
        root=Path('/mnt/GameDrive/tiny_dancer')
        with tempfile.TemporaryDirectory(dir=root/'run') as folder:
            path=Path(folder)/'test_probe.py'
            path.write_text('import unittest\nclass Probe(unittest.TestCase):\n def test_values(self):\n  for value in '+repr(values)+':\n   with self.subTest(value=value):self.assertGreater(value,0)\n')
            return subprocess.run([str(root/'.venv/bin/python'),'-m','pytest','-q',str(path)],cwd=folder,capture_output=True,text=True,timeout=20)

    # ------------------------------------------------------------------------------
    # test_installed_pytest_passing_subtests_are_recognized: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_installed_pytest_passing_subtests_are_recognized(self):
        result=self.invoke([1,2,3]);self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('subtests passed',result.stdout)
        summary=test_summary(result.stdout+result.stderr)
        self.assertIsNotNone(summary);self.assertTrue(summary['passed']);self.assertEqual(summary['count'],1)

    # ------------------------------------------------------------------------------
    # test_installed_pytest_failed_subtests_are_rejected: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_installed_pytest_failed_subtests_are_rejected(self):
        result=self.invoke([1,-1,2]);self.assertNotEqual(result.returncode,0)
        summary=test_summary(result.stdout+result.stderr)
        self.assertIsNotNone(summary);self.assertTrue(summary['failed']);self.assertFalse(summary['passed'])
