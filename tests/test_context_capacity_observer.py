# ==============================================================================
# Program: test_context_capacity_observer.py
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
"""A capacity claim requires real final, token and memory witnesses."""
import unittest
from openai_harmony import HarmonyEncodingName, load_harmony_encoding
from scripts.evaluate_context_capacity import EXPECTED, checks_for, make_prompt
from app.request_models import NewTask


# ------------------------------------------------------------------------------
# ContextObserverTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class ContextObserverTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # grade: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def grade(self, **overrides):
        values = dict(status='complete', finals=[EXPECTED],
                      metrics=[{'backend': 'llama.cpp-native-mxfp4', 'prompt_tokens': 16000}],
                      before='frozen-source', after='frozen-source',
                      samples=[{'available_ram_gib': 4.5, 'free_vram_mib': 2200}], interventions=[])
        values.update(overrides)
        return checks_for(**values)

    # ------------------------------------------------------------------------------
    # test_frozen_real_receipts_are_required: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_frozen_real_receipts_are_required(self):
        self.assertTrue(all(self.grade().values()))
        for changes in ({'metrics': []}, {'samples': []}, {'before': '', 'after': ''},
                        {'after': 'changed-source'}, {'interventions': ['stopped at deadline']}):
            with self.subTest(changes=changes):
                self.assertFalse(all(self.grade(**changes).values()))

    # ------------------------------------------------------------------------------
    # test_old_context_or_non_native_receipt_cannot_pass: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_old_context_or_non_native_receipt_cannot_pass(self):
        for metrics in ([{'backend': 'llama.cpp-native-mxfp4', 'prompt_tokens': 8192}],
                        [{'backend': 'fixture', 'prompt_tokens': 16000}]):
            self.assertFalse(all(self.grade(metrics=metrics).values()))

    # ------------------------------------------------------------------------------
    # test_pause_or_incorrect_final_is_not_capacity_success: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_pause_or_incorrect_final_is_not_capacity_success(self):
        for changes in ({'status': 'paused'}, {'finals': []}, {'finals': ['ALPHA=29; OMEGA=17']},
                        {'finals': [EXPECTED, EXPECTED]}):
            self.assertFalse(all(self.grade(**changes).values()))

    # ------------------------------------------------------------------------------
    # test_desktop_reserves_cannot_be_ignored: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_desktop_reserves_cannot_be_ignored(self):
        for sample in ({'available_ram_gib': 1.49, 'free_vram_mib': 2200},
                       {'available_ram_gib': 4.5, 'free_vram_mib': 1499}):
            self.assertFalse(all(self.grade(samples=[sample]).values()))

    # ------------------------------------------------------------------------------
    # test_declared_prompt_exceeds_old_capacity_and_fits_candidate: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_declared_prompt_exceeds_old_capacity_and_fits_candidate(self):
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
