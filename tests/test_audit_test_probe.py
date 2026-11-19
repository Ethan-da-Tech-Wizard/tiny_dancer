# ==============================================================================
# Program: test_audit_test_probe.py
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
import json
from pathlib import Path
import tempfile
import unittest
from openai_harmony import Message,Role
from scripts.audit_test_probe import submitted_code,grade_verification


# ------------------------------------------------------------------------------
# AuditTestProbeTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class AuditTestProbeTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # test_only_completed_tool_content_can_be_submitted: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_only_completed_tool_content_can_be_submitted(self):
        call=Message.from_role_and_content(Role.ASSISTANT,json.dumps({'content':'import unittest\n'})).with_recipient('functions.write_verification')
        private=Message.from_role_and_content(Role.ASSISTANT,'private').with_channel('analysis')
        self.assertEqual(submitted_code([private,call]),'import unittest\n')
        for messages in ([private],[call,call]):
            with self.assertRaises(ValueError):submitted_code(messages)

    # ------------------------------------------------------------------------------
    # test_real_assertion_distinguishes_controls_without_source_changes: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_real_assertion_distinguishes_controls_without_source_changes(self):
        code='import unittest,inventory\nclass TestContract(unittest.TestCase):\n def test_behavior(self):self.assertEqual(inventory.value(),2)\n'
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'run').mkdir()
            result=grade_verification('def value():return 1\n','def value():return 2\n',code,root)
        self.assertTrue(result['passed'],result)

    # ------------------------------------------------------------------------------
    # test_vacuous_or_broken_tests_do_not_qualify: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_vacuous_or_broken_tests_do_not_qualify(self):
        for code in ['import unittest\n','import unittest\nclass Tests(unittest.TestCase):\n def test_nothing(self):pass\n','raise RuntimeError("broken setup")\n']:
            with tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary);(root/'run').mkdir()
                result=grade_verification('x=1\n','x=1\n',code,root)
            self.assertFalse(result['passed'],result)

    # ------------------------------------------------------------------------------
    # test_always_failing_tests_reject_conforming_control: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_always_failing_tests_reject_conforming_control(self):
        code='import unittest\nclass Tests(unittest.TestCase):\n def test_bad_expectation(self):self.fail("always wrong")\n'
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'run').mkdir()
            result=grade_verification('x=1\n','x=1\n',code,root)
        self.assertFalse(result['passed']);self.assertFalse(result['checks']['accepts_conforming_control'])
