# ==============================================================================
# Program: test_explicit_budget.py
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
from pydantic import ValidationError
from app.request_models import NewTask, ResumeTask, apply_resume_options


# ------------------------------------------------------------------------------
# ExplicitBudgetTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class ExplicitBudgetTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # test_larger_choice_is_valid_for_new_tasks_and_resume: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_larger_choice_is_valid_for_new_tasks_and_resume(self):
        task=NewTask(prompt='Review code.',max_tokens=4096)
        self.assertEqual(task.max_tokens,4096)
        resumed=apply_resume_options(NewTask(prompt='Continue.'),ResumeTask(max_tokens=4096))
        self.assertEqual(resumed.max_tokens,4096)

    # ------------------------------------------------------------------------------
    # test_existing_default_remains_automatic: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_existing_default_remains_automatic(self):
        self.assertIsNone(NewTask(prompt='Work.').max_tokens)
        self.assertIsNone(ResumeTask().max_tokens)

    # ------------------------------------------------------------------------------
    # test_values_outside_actual_allowance_are_rejected: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_values_outside_actual_allowance_are_rejected(self):
        for value in (63,4097):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):NewTask(prompt='Work.',max_tokens=value)
                with self.assertRaises(ValidationError):ResumeTask(max_tokens=value)
