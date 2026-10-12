# SPDX-License-Identifier: Apache-2.0
import unittest
from app.reasoning import effective_effort


class ReasoningPolicyTests(unittest.TestCase):
    def test_auto_work_uses_configured_effort_for_any_language(self):
        for languages in ([],['python'],['rust']):
            self.assertEqual(effective_effort('auto',{'kind':'work','lookup_languages':languages},{'work_reasoning_effort':'high'}),'high')

    def test_explicit_quick_and_balanced_choices_are_preserved(self):
        for choice in ('low','medium','high'):
            self.assertEqual(effective_effort(choice,{'kind':'work'},{'work_reasoning_effort':'high'}),choice)

    def test_chat_and_questions_keep_light_default(self):
        self.assertEqual(effective_effort('auto',{'kind':'answer'},{'work_reasoning_effort':'high'}),'low')
        self.assertEqual(effective_effort('auto',{'kind':'work'},{'work_reasoning_effort':'high'},False),'low')

    def test_legacy_config_remains_compatible(self):
        self.assertEqual(effective_effort('auto',{'kind':'work','lookup_languages':['python']},{}),'medium')
        self.assertEqual(effective_effort('auto',{'kind':'work','lookup_languages':[]},{}),'low')

    def test_invalid_value_is_not_silently_treated_as_low(self):
        with self.assertRaises(ValueError):effective_effort('auto',{'kind':'work'},{'work_reasoning_effort':'invalid'})
