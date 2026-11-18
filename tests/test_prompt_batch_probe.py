# Program: tiny_dancer - tests/test_prompt_batch_probe.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Tests for prompt batch probe (exercises scripts.benchmark_prompt_batches).
# SPDX-License-Identifier: Apache-2.0
"""Tests for prompt batch probe (exercises scripts.benchmark_prompt_batches)."""
import unittest
from scripts.benchmark_prompt_batches import batch_command, verdict


# -------- prompt batch probe tests --------
class PromptBatchProbeTests(unittest.TestCase):
    """Test group for prompt batch probe."""
    def test_only_declared_batch_and_microbatch_change(self):
        """Checks that only declared batch and microbatch change."""
        original = ['server', '-b', '128', '-ub', '128', '-c', '32768', '-t', '8', '-ncmoe', '16']
        candidate = batch_command(original, 512)
        self.assertEqual(candidate, ['server', '-b', '512', '-ub', '512', '-c', '32768', '-t', '8', '-ncmoe', '16'])
        self.assertEqual(original[2], '128')
        for size in (True, 256, -1):
            with self.assertRaises(ValueError): batch_command(original, size)

    def variants(self):
        """Test helper: variants."""
        return [{'batch': b, 'receipt_passed': True, 'prefill_tokens': 1000, 'prefill_seconds': s,
                 'start_sample': {'gpu_c': 74, 'cpu_c': 85}, 'samples': [{'thermal_slowdown': False}]}
                for b, s in ((128, 40), (512, 20), (128, 30))]

    def test_speed_requires_both_baselines_same_work_and_correct_receipts(self):
        """Checks that speed requires both baselines same work and correct receipts."""
        self.assertTrue(verdict(self.variants())['passed'])
        for key, value in (('receipt_passed', False), ('prefill_tokens', 900), ('prefill_seconds', 28), ('interruption', 'RAM reserve')):
            values = self.variants(); values[1][key] = value
            self.assertFalse(verdict(values)['passed'])
        self.assertFalse(verdict(self.variants()[:-1])['passed'])

    def test_thermal_or_starting_temperature_mismatch_cannot_claim_gain(self):
        """Checks that thermal or starting temperature mismatch cannot claim gain."""
        values = self.variants(); values[1]['samples'][0]['thermal_slowdown'] = True
        self.assertFalse(verdict(values)['passed'])

    def storage_variants(self):
        """Test helper: storage variants."""
        result = self.variants()
        for record, kind in zip(result, ('original', 'cache', 'original')):
            record.update(batch=128, storage=kind, model_storage={'kind': kind, 'sha256': 'same-pinned-identity'})
        return result

    def test_storage_comparison_requires_actual_cache_identity_and_same_batch(self):
        """Checks that storage comparison requires actual cache identity and same batch."""
        self.assertTrue(verdict(self.storage_variants(), storage=True)['passed'])
        values = self.storage_variants(); values[1]['model_storage']['kind'] = 'original'
        self.assertFalse(verdict(values, storage=True)['passed'])
        values = self.storage_variants(); values[1]['model_storage']['sha256'] = 'different'
        self.assertFalse(verdict(values, storage=True)['passed'])
        values = self.storage_variants(); values[1]['batch'] = 512
        self.assertFalse(verdict(values, storage=True)['passed'])

    def test_missing_native_timings_cannot_establish_performance(self):
        """Checks that missing native timings cannot establish performance."""
        values = self.variants(); values[1]['prefill_tokens'] = None
        self.assertFalse(verdict(values)['passed'])
        values = self.variants(); values[1]['start_sample']['gpu_c'] = 84
        self.assertFalse(verdict(values)['passed'])


if __name__ == '__main__':
    unittest.main()
