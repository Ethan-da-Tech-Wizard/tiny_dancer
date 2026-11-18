# Program: tiny_dancer - tests/test_sampling.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Tests for sampling (exercises app.sampling).
# SPDX-License-Identifier: Apache-2.0
"""Tests for sampling (exercises app.sampling)."""
import unittest
from app.sampling import native_temperature


# -------- sampling profile tests --------
class SamplingProfileTests(unittest.TestCase):
    """Test group for sampling profile."""
    def test_absent_profile_preserves_the_recorded_greedy_control(self):
        """Checks that absent profile preserves the recorded greedy control."""
        self.assertEqual(native_temperature({}),0.0)
        self.assertEqual(native_temperature({'native_sampling_profile':'greedy'}),0.0)

    def test_recommended_profile_is_independent_of_context_and_thread_settings(self):
        """Checks that recommended profile is independent of context and thread settings."""
        for context in (8192,32768):
            self.assertEqual(native_temperature({'native_sampling_profile':'recommended','context':context,'threads':8}),1.0)

    def test_malformed_profile_does_not_silently_select_a_different_sampler(self):
        """Checks that malformed profile does not silently select a different sampler."""
        for profile in ('unknown',None,True,1,['recommended']):
            with self.subTest(profile=profile),self.assertRaisesRegex(ValueError,'native_sampling_profile'):
                native_temperature({'native_sampling_profile':profile})


if __name__=='__main__':unittest.main()
