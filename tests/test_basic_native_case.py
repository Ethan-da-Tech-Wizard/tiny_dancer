# ==============================================================================
# Program: test_basic_native_case.py
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
import tempfile
from pathlib import Path
import unittest
from scripts.native_suite_cases import CASES, grade
from app.tools import ROOT


# ------------------------------------------------------------------------------
# BasicNativeGraderTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class BasicNativeGraderTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # setUp: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'run');self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)

    # ------------------------------------------------------------------------------
    # test_correct_fixture_proves_the_independent_grader_witness: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_correct_fixture_proves_the_independent_grader_witness(self):
        (self.folder/'labels.py').write_text('def normalize_label(text):\n return " ".join(text.split()).lower()\n')
        checks=grade(self.folder,'labels',ROOT)
        self.assertEqual(len(checks),4);self.assertTrue(all(c['passed'] for c in checks))

    # ------------------------------------------------------------------------------
    # test_missing_function_is_a_nonempty_failure: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_missing_function_is_a_nonempty_failure(self):
        checks=grade(self.folder,'labels',ROOT)
        self.assertEqual(len(checks),4);self.assertTrue(all(not c['passed'] for c in checks))

    # ------------------------------------------------------------------------------
    # test_ascii_only_implementation_cannot_hide_unicode_failure: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_ascii_only_implementation_cannot_hide_unicode_failure(self):
        (self.folder/'labels.py').write_text('def normalize_label(text):\n return " ".join(text.split()).encode("ascii","ignore").decode().lower()\n')
        checks=grade(self.folder,'labels',ROOT)
        self.assertFalse(all(c['passed'] for c in checks))

    # ------------------------------------------------------------------------------
    # test_debug_output_cannot_be_mistaken_for_a_correct_json_receipt: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_debug_output_cannot_be_mistaken_for_a_correct_json_receipt(self):
        (self.folder/'labels.py').write_text('print("debug")\ndef normalize_label(text):\n return " ".join(text.split()).lower()\n')
        self.assertTrue(all(not c['passed'] for c in grade(self.folder,'labels',ROOT)))

    # ------------------------------------------------------------------------------
    # test_small_frozen_goal_has_six_seeds_and_requires_new_tests: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_small_frozen_goal_has_six_seeds_and_requires_new_tests(self):
        case=CASES['labels']
        self.assertEqual(case['acceptance'].count(' def test_'),6)
        self.assertIn('Add your own relevant tests',case['prompt'])
        self.assertEqual(case['kind'],'module')


if __name__=='__main__':unittest.main()
