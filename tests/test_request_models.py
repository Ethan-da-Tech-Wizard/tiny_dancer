# ==============================================================================
# Program: test_request_models.py
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
"""Validate API inputs without importing the server or touching job state."""
import unittest
from pydantic import ValidationError
from app.request_models import NewTask,ResumeTask,apply_resume_options


# ------------------------------------------------------------------------------
# RequestModelTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class RequestModelTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # test_new_api_agent_defaults_to_continuous_work: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_new_api_agent_defaults_to_continuous_work(self):
        self.assertTrue(NewTask.model_validate_json('{"prompt":"Build an app"}').run_until_done)

    # ------------------------------------------------------------------------------
    # test_chat_and_explicit_bounded_choice_remain_available: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_chat_and_explicit_bounded_choice_remain_available(self):
        self.assertFalse(NewTask(prompt='Hello',mode='chat').run_until_done)
        self.assertFalse(NewTask(prompt='Build an app',run_until_done=False).run_until_done)
        self.assertTrue(NewTask(prompt='Hello',mode='chat',run_until_done=True).run_until_done)

    # ------------------------------------------------------------------------------
    # test_saved_explicit_bounded_mode_survives_resume_and_round_trip: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_saved_explicit_bounded_mode_survives_resume_and_round_trip(self):
        saved=NewTask.model_validate_json('{"prompt":"Old task","run_until_done":false}')
        apply_resume_options(saved,ResumeTask())
        self.assertFalse(NewTask.model_validate_json(saved.model_dump_json()).run_until_done)

    # ------------------------------------------------------------------------------
    # test_omitted_and_null_budget_select_auto: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_omitted_and_null_budget_select_auto(self):
        self.assertIsNone(NewTask(prompt='Create a file').max_tokens)
        self.assertIsNone(NewTask(prompt='Create a file',max_tokens=None).max_tokens)

    # ------------------------------------------------------------------------------
    # test_numeric_budget_bounds_are_preserved: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_numeric_budget_bounds_are_preserved(self):
        for number in (64,512,1024,2048,4096):
            with self.subTest(number=number):self.assertEqual(NewTask(prompt='Task',max_tokens=number).max_tokens,number)
        for number in (0,63,4097,100000):
            for model in (NewTask,ResumeTask):
                with self.subTest(number=number,model=model.__name__),self.assertRaises(ValidationError):
                    model(**({'prompt':'Task'} if model is NewTask else {}),max_tokens=number)

    # ------------------------------------------------------------------------------
    # test_omitted_resume_options_preserve_saved_settings: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_omitted_resume_options_preserve_saved_settings(self):
        task=NewTask(prompt='Task',max_tokens=1024,run_until_done=True,reasoning_effort='medium')
        apply_resume_options(task,ResumeTask())
        self.assertEqual((task.max_tokens,task.run_until_done,task.reasoning_effort),(1024,True,'medium'))

    # ------------------------------------------------------------------------------
    # test_explicit_resume_auto_clears_the_saved_numeric_budget: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_explicit_resume_auto_clears_the_saved_numeric_budget(self):
        task=NewTask(prompt='Task',max_tokens=1024)
        apply_resume_options(task,ResumeTask(max_tokens=None))
        self.assertIsNone(task.max_tokens)
        self.assertIsNone(NewTask.model_validate_json(task.model_dump_json()).max_tokens)

    # ------------------------------------------------------------------------------
    # test_resume_updates_explicit_choices_without_changing_original_goal: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_resume_updates_explicit_choices_without_changing_original_goal(self):
        task=NewTask(prompt='Original task',max_tokens=None)
        apply_resume_options(task,ResumeTask(max_tokens=512,run_until_done=True,reasoning_effort='low'))
        self.assertEqual(task.prompt,'Original task')
        self.assertEqual((task.max_tokens,task.run_until_done,task.reasoning_effort),(512,True,'low'))
