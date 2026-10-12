# SPDX-License-Identifier: Apache-2.0
import unittest
from app.sampling import native_temperature


class SamplingProfileTests(unittest.TestCase):
    def test_absent_profile_preserves_the_recorded_greedy_control(self):
        self.assertEqual(native_temperature({}),0.0)
        self.assertEqual(native_temperature({'native_sampling_profile':'greedy'}),0.0)

    def test_recommended_profile_is_independent_of_context_and_thread_settings(self):
        for context in (8192,32768):
            self.assertEqual(native_temperature({'native_sampling_profile':'recommended','context':context,'threads':8}),1.0)

    def test_malformed_profile_does_not_silently_select_a_different_sampler(self):
        for profile in ('unknown',None,True,1,['recommended']):
            with self.subTest(profile=profile),self.assertRaisesRegex(ValueError,'native_sampling_profile'):
                native_temperature({'native_sampling_profile':profile})


if __name__=='__main__':unittest.main()
