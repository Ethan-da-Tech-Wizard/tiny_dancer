# Program: tiny_dancer - tests/test_context_capacity_observer.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Tests for context capacity observer (exercises app.request_models, scripts.evaluate_context_capacity).
# SPDX-License-Identifier: Apache-2.0
"""A capacity claim requires real final, token and memory witnesses."""
import unittest
from openai_harmony import HarmonyEncodingName, load_harmony_encoding
from scripts.evaluate_context_capacity import EXPECTED, checks_for, make_prompt
from app.request_models import NewTask


# -------- context observer tests --------
class ContextObserverTests(unittest.TestCase):
    """Test group for context observer."""
    def grade(self, **overrides):
        """Test helper: score."""
        values = dict(status='complete', finals=[EXPECTED],
                      metrics=[{'backend': 'llama.cpp-native-mxfp4', 'prompt_tokens': 16000}],
                      before='frozen-source', after='frozen-source',
                      samples=[{'available_ram_gib': 4.5, 'free_vram_mib': 2200}], interventions=[])
        values.update(overrides)
        return checks_for(**values)

    def test_frozen_real_receipts_are_required(self):
        """Checks that frozen real receipts are required."""
        self.assertTrue(all(self.grade().values()))
        for changes in ({'metrics': []}, {'samples': []}, {'before': '', 'after': ''},
                        {'after': 'changed-source'}, {'interventions': ['stopped at deadline']}):
            with self.subTest(changes=changes):
                self.assertFalse(all(self.grade(**changes).values()))

    def test_old_context_or_non_native_receipt_cannot_pass(self):
        """Checks that old context or non native receipt cannot pass."""
        for metrics in ([{'backend': 'llama.cpp-native-mxfp4', 'prompt_tokens': 8192}],
                        [{'backend': 'fixture', 'prompt_tokens': 16000}]):
            self.assertFalse(all(self.grade(metrics=metrics).values()))

    def test_pause_or_incorrect_final_is_not_capacity_success(self):
        """Checks that pause or incorrect final is not capacity success."""
        for changes in ({'status': 'paused'}, {'finals': []}, {'finals': ['ALPHA=29; OMEGA=17']},
                        {'finals': [EXPECTED, EXPECTED]}):
            self.assertFalse(all(self.grade(**changes).values()))

    def test_desktop_reserves_cannot_be_ignored(self):
        """Checks that desktop reserves cannot be ignored."""
        for sample in ({'available_ram_gib': 1.49, 'free_vram_mib': 2200},
                       {'available_ram_gib': 4.5, 'free_vram_mib': 1499}):
            self.assertFalse(all(self.grade(samples=[sample]).values()))

    def test_declared_prompt_exceeds_old_capacity_and_fits_candidate(self):
        """Checks that declared prompt exceeds old capacity and fits candidate."""
        encoding = load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
        prompt = make_prompt()
        self.assertLessEqual(len(prompt), 30000)
        self.assertEqual(NewTask(prompt=prompt, mode='chat', max_tokens=256).prompt, prompt)
        count = len(encoding.encode(prompt))
        self.assertGreater(count, 8192)
        self.assertLess(count + 2048, 32768)
        self.assertEqual(prompt.count('ALPHA=17'), 1)
        self.assertEqual(prompt.count('OMEGA=29'), 1)


if __name__ == '__main__':
    unittest.main()
