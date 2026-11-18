# Program: tiny_dancer - tests/test_reasoning_policy.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Tests for reasoning policy (exercises app.reasoning).
# SPDX-License-Identifier: Apache-2.0
"""Tests for reasoning policy (exercises app.reasoning)."""
import unittest
from app.reasoning import effective_effort


# -------- reasoning policy tests --------
class ReasoningPolicyTests(unittest.TestCase):
    """Test group for reasoning policy."""
    def test_auto_work_uses_configured_effort_for_any_language(self):
        """Checks that auto work uses configured effort for any language."""
        for languages in ([],['python'],['rust']):
            self.assertEqual(effective_effort('auto',{'kind':'work','lookup_languages':languages},{'work_reasoning_effort':'high'}),'high')

    def test_explicit_quick_and_balanced_choices_are_preserved(self):
        """Checks that explicit quick and balanced choices are preserved."""
        for choice in ('low','medium','high'):
            self.assertEqual(effective_effort(choice,{'kind':'work'},{'work_reasoning_effort':'high'}),choice)

    def test_chat_and_questions_keep_light_default(self):
        """Checks that chat and questions keep light default."""
        self.assertEqual(effective_effort('auto',{'kind':'answer'},{'work_reasoning_effort':'high'}),'low')
        self.assertEqual(effective_effort('auto',{'kind':'work'},{'work_reasoning_effort':'high'},False),'low')

    def test_legacy_config_remains_compatible(self):
        """Checks that legacy config remains compatible."""
        self.assertEqual(effective_effort('auto',{'kind':'work','lookup_languages':['python']},{}),'medium')
        self.assertEqual(effective_effort('auto',{'kind':'work','lookup_languages':[]},{}),'low')

    def test_invalid_value_is_not_silently_treated_as_low(self):
        """Checks that invalid value is not silently treated as low."""
        with self.assertRaises(ValueError):effective_effort('auto',{'kind':'work'},{'work_reasoning_effort':'invalid'})
