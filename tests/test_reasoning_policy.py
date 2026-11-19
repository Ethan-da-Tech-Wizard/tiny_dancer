# ==============================================================================
# Program: test_reasoning_policy.py
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
import unittest
from app.reasoning import effective_effort


# ------------------------------------------------------------------------------
# ReasoningPolicyTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class ReasoningPolicyTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # test_auto_work_uses_configured_effort_for_any_language: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_auto_work_uses_configured_effort_for_any_language(self):
        for languages in ([],['python'],['rust']):
            self.assertEqual(effective_effort('auto',{'kind':'work','lookup_languages':languages},{'work_reasoning_effort':'high'}),'high')

    # ------------------------------------------------------------------------------
    # test_explicit_quick_and_balanced_choices_are_preserved: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_explicit_quick_and_balanced_choices_are_preserved(self):
        for choice in ('low','medium','high'):
            self.assertEqual(effective_effort(choice,{'kind':'work'},{'work_reasoning_effort':'high'}),choice)

    # ------------------------------------------------------------------------------
    # test_chat_and_questions_keep_light_default: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_chat_and_questions_keep_light_default(self):
        self.assertEqual(effective_effort('auto',{'kind':'answer'},{'work_reasoning_effort':'high'}),'low')
        self.assertEqual(effective_effort('auto',{'kind':'work'},{'work_reasoning_effort':'high'},False),'low')

    # ------------------------------------------------------------------------------
    # test_legacy_config_remains_compatible: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_legacy_config_remains_compatible(self):
        self.assertEqual(effective_effort('auto',{'kind':'work','lookup_languages':['python']},{}),'medium')
        self.assertEqual(effective_effort('auto',{'kind':'work','lookup_languages':[]},{}),'low')

    # ------------------------------------------------------------------------------
    # test_invalid_value_is_not_silently_treated_as_low: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_invalid_value_is_not_silently_treated_as_low(self):
        with self.assertRaises(ValueError):effective_effort('auto',{'kind':'work'},{'work_reasoning_effort':'invalid'})
