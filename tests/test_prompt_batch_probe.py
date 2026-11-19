# ==============================================================================
# Program: test_prompt_batch_probe.py
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
from scripts.benchmark_prompt_batches import batch_command, verdict


# ------------------------------------------------------------------------------
# PromptBatchProbeTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class PromptBatchProbeTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # test_only_declared_batch_and_microbatch_change: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_only_declared_batch_and_microbatch_change(self):
        original = ['server', '-b', '128', '-ub', '128', '-c', '32768', '-t', '8', '-ncmoe', '16']
        candidate = batch_command(original, 512)
        self.assertEqual(candidate, ['server', '-b', '512', '-ub', '512', '-c', '32768', '-t', '8', '-ncmoe', '16'])
        self.assertEqual(original[2], '128')
        for size in (True, 256, -1):
            with self.assertRaises(ValueError): batch_command(original, size)

    # ------------------------------------------------------------------------------
    # variants: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def variants(self):
        return [{'batch': b, 'receipt_passed': True, 'prefill_tokens': 1000, 'prefill_seconds': s,
                 'start_sample': {'gpu_c': 74, 'cpu_c': 85}, 'samples': [{'thermal_slowdown': False}]}
                for b, s in ((128, 40), (512, 20), (128, 30))]

    # ------------------------------------------------------------------------------
    # test_speed_requires_both_baselines_same_work_and_correct_receipts: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_speed_requires_both_baselines_same_work_and_correct_receipts(self):
        self.assertTrue(verdict(self.variants())['passed'])
        for key, value in (('receipt_passed', False), ('prefill_tokens', 900), ('prefill_seconds', 28), ('interruption', 'RAM reserve')):
            values = self.variants(); values[1][key] = value
            self.assertFalse(verdict(values)['passed'])
        self.assertFalse(verdict(self.variants()[:-1])['passed'])

    # ------------------------------------------------------------------------------
    # test_thermal_or_starting_temperature_mismatch_cannot_claim_gain: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_thermal_or_starting_temperature_mismatch_cannot_claim_gain(self):
        values = self.variants(); values[1]['samples'][0]['thermal_slowdown'] = True
        self.assertFalse(verdict(values)['passed'])

    # ------------------------------------------------------------------------------
    # storage_variants: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def storage_variants(self):
        result = self.variants()
        for record, kind in zip(result, ('original', 'cache', 'original')):
            record.update(batch=128, storage=kind, model_storage={'kind': kind, 'sha256': 'same-pinned-identity'})
        return result

    # ------------------------------------------------------------------------------
    # test_storage_comparison_requires_actual_cache_identity_and_same_batch: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_storage_comparison_requires_actual_cache_identity_and_same_batch(self):
        self.assertTrue(verdict(self.storage_variants(), storage=True)['passed'])
        values = self.storage_variants(); values[1]['model_storage']['kind'] = 'original'
        self.assertFalse(verdict(values, storage=True)['passed'])
        values = self.storage_variants(); values[1]['model_storage']['sha256'] = 'different'
        self.assertFalse(verdict(values, storage=True)['passed'])
        values = self.storage_variants(); values[1]['batch'] = 512
        self.assertFalse(verdict(values, storage=True)['passed'])

    # ------------------------------------------------------------------------------
    # test_missing_native_timings_cannot_establish_performance: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_missing_native_timings_cannot_establish_performance(self):
        values = self.variants(); values[1]['prefill_tokens'] = None
        self.assertFalse(verdict(values)['passed'])
        values = self.variants(); values[1]['start_sample']['gpu_c'] = 84
        self.assertFalse(verdict(values)['passed'])


if __name__ == '__main__':
    unittest.main()
