# SPDX-License-Identifier: Apache-2.0
import unittest
from pydantic import ValidationError
from app.request_models import NewTask, ResumeTask, apply_resume_options


class ExplicitBudgetTests(unittest.TestCase):
    def test_larger_choice_is_valid_for_new_tasks_and_resume(self):
        task=NewTask(prompt='Review code.',max_tokens=4096)
        self.assertEqual(task.max_tokens,4096)
        resumed=apply_resume_options(NewTask(prompt='Continue.'),ResumeTask(max_tokens=4096))
        self.assertEqual(resumed.max_tokens,4096)

    def test_existing_default_remains_automatic(self):
        self.assertIsNone(NewTask(prompt='Work.').max_tokens)
        self.assertIsNone(ResumeTask().max_tokens)

    def test_values_outside_actual_allowance_are_rejected(self):
        for value in (63,4097):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):NewTask(prompt='Work.',max_tokens=value)
                with self.assertRaises(ValidationError):ResumeTask(max_tokens=value)
