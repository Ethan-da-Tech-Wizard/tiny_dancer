# Program: tiny_dancer - tests/test_explicit_budget.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Tests for explicit budget (exercises app.request_models).
# SPDX-License-Identifier: Apache-2.0
"""Tests for explicit budget (exercises app.request_models)."""
import unittest
from pydantic import ValidationError
from app.request_models import NewTask, ResumeTask, apply_resume_options


# -------- explicit budget tests --------
class ExplicitBudgetTests(unittest.TestCase):
    """Test group for explicit budget."""
    def test_larger_choice_is_valid_for_new_tasks_and_resume(self):
        """Checks that larger choice is valid for new tasks and resume."""
        task=NewTask(prompt='Review code.',max_tokens=4096)
        self.assertEqual(task.max_tokens,4096)
        resumed=apply_resume_options(NewTask(prompt='Continue.'),ResumeTask(max_tokens=4096))
        self.assertEqual(resumed.max_tokens,4096)

    def test_existing_default_remains_automatic(self):
        """Checks that existing default remains automatic."""
        self.assertIsNone(NewTask(prompt='Work.').max_tokens)
        self.assertIsNone(ResumeTask().max_tokens)

    def test_values_outside_actual_allowance_are_rejected(self):
        """Checks that values outside actual allowance are rejected."""
        for value in (63,4097):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):NewTask(prompt='Work.',max_tokens=value)
                with self.assertRaises(ValidationError):ResumeTask(max_tokens=value)
