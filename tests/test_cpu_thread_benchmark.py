# SPDX-License-Identifier: Apache-2.0
import copy
import subprocess
import unittest
from unittest.mock import Mock, patch

from scripts.benchmark_cpu_threads import candidate_config, comparison, cooldown_ready, gpu_state, resource_issue, stop_owned


class CPUThreadBenchmarkTests(unittest.TestCase):
    def sample(self, **updates):
        result = {'gpu_c': 68, 'cpu_c': 73, 'gpu_total_mib': 8192,
                  'gpu_used_mib': 5200, 'available_ram_gib': 6}
        return dict(result, **updates)

    def variants(self):
        result = []
        for threads, seconds in ((8, 20), (4, 15), (6, 17), (8, 21)):
            turn = {'token_count': 384, 'tokens_sha256': 'a'*64,
                    'reason': 'MAX_TOKENS', 'timings': {'total_seconds': seconds}}
            result.append({'threads': threads, 'completed': True, 'start_sample': self.sample(),
                           'samples': [self.sample()], 'turns': [copy.deepcopy(turn) for _ in range(3)]})
        return result

    def test_only_threads_change_and_baseline_config_is_retained(self):
        config = {'threads': 8, 'context': 8192, 'backend': 'llama.cpp',
                  'model_path': 'same weights', 'model_nice': 5, 'gpu': True}
        before = copy.deepcopy(config)
        result = candidate_config(config, 4)
        self.assertEqual(config, before)
        self.assertEqual({k for k in config if config[k] != result[k]}, {'threads'})

    def test_undeclared_or_different_baseline_is_rejected(self):
        config = {'threads': 8, 'context': 8192, 'backend': 'llama.cpp'}
        for threads in (True, '4', 2, 0, -1):
            with self.subTest(threads=threads), self.assertRaises(ValueError):
                candidate_config(config, threads)
        for key, value in (('threads', 6), ('context', 4096), ('backend', 'picchio')):
            with self.subTest(key=key), self.assertRaises(ValueError):
                candidate_config(dict(config, **{key: value}), 4)

    def test_full_stable_comparison_can_pass_speed_probe(self):
        result = comparison(self.variants())
        self.assertTrue(result['passed'])
        self.assertTrue(result['comparison_complete'])
        self.assertTrue(result['greedy_token_parity'])
        self.assertEqual([c['threads'] for c in result['candidates']], [4, 6])

    def test_incomplete_or_failed_runs_cannot_become_speed_success(self):
        for mutation in ('missing_variant', 'failed', 'missing_turn', 'missing_sample', 'zero_time'):
            variants = self.variants()
            if mutation == 'missing_variant': variants.pop()
            elif mutation == 'failed': variants[1]['completed'] = False
            elif mutation == 'missing_turn': variants[1]['turns'].pop()
            elif mutation == 'missing_sample': variants[1]['samples'] = []
            else: variants[1]['turns'][0]['timings']['total_seconds'] = 0
            with self.subTest(mutation=mutation):
                self.assertFalse(comparison(variants)['passed'])

    def test_faster_different_answers_are_rejected_for_that_candidate(self):
        variants = self.variants()
        for turn in variants[1]['turns']: turn['tokens_sha256'] = 'b'*64
        result = comparison(variants)
        self.assertFalse(result['greedy_token_parity'])
        self.assertFalse(result['candidates'][0]['speed_probe_passed'])
        self.assertTrue(result['candidates'][1]['speed_probe_passed'])

    def test_changed_or_unstable_baseline_rejects_every_candidate(self):
        for index in (0, -1):
            variants = self.variants()
            variants[index]['turns'][0]['tokens_sha256'] = 'b'*64
            with self.subTest(index=index):
                result = comparison(variants)
                self.assertFalse(result['passed'])
                self.assertFalse(result['baseline_token_stable'])

    def test_average_speed_cannot_hide_slower_result_against_first_baseline(self):
        variants = self.variants()
        for turn in variants[0]['turns']: turn['timings']['total_seconds'] = 10
        for turn in variants[-1]['turns']: turn['timings']['total_seconds'] = 30
        result = comparison(variants)
        self.assertFalse(result['passed'])
        self.assertTrue(all(c['time_reduction_fraction_vs_bracket_mean'] > 0 for c in result['candidates']))

    def test_missing_or_mismatched_start_temperatures_reject_success(self):
        for mutation in ('unknown_cpu', 'hot_start', 'unequal_gpu', 'unequal_cpu'):
            variants = self.variants()
            if mutation == 'unknown_cpu': variants[1]['start_sample']['cpu_c'] = None
            elif mutation == 'hot_start': variants[1]['start_sample']['gpu_c'] = 75
            elif mutation == 'unequal_gpu': variants[1]['start_sample']['gpu_c'] = 59
            else: variants[1]['start_sample']['cpu_c'] = 87
            with self.subTest(mutation=mutation):
                self.assertFalse(comparison(variants)['passed'])

    def test_resource_and_deadline_guards(self):
        self.assertIsNone(resource_issue(self.sample()))
        for updates in ({'available_ram_gib': 1}, {'gpu_used_mib': 7000}, {'gpu_c': 93}, {'cpu_c': 100}):
            with self.subTest(updates=updates):
                self.assertIsNotNone(resource_issue(self.sample(**updates)))
        self.assertIn('User task', resource_issue(self.sample(), user_job=True))
        self.assertIn('Variant', resource_issue(self.sample(), elapsed=150))
        self.assertIn('Experiment', resource_issue(self.sample(), experiment_elapsed=720))

    def test_cooling_wait_does_not_start_hot_run_or_exceed_its_limit(self):
        # Actual first trial remained too hot after 45 seconds.
        self.assertFalse(cooldown_ready(self.sample(gpu_c=78), 45))
        self.assertFalse(cooldown_ready(self.sample(gpu_c=74), 90))
        self.assertTrue(cooldown_ready(self.sample(gpu_c=72), 110))
        with self.assertRaisesRegex(RuntimeError, 'cooldown limit'):
            cooldown_ready(self.sample(gpu_c=73), 120)
        self.assertIn('Experiment', resource_issue(self.sample(gpu_c=74), experiment_elapsed=720))

    def test_only_explicit_owned_live_processes_receive_stop(self):
        live, exited, unrelated = Mock(), Mock(), Mock()
        live.poll.return_value = None
        exited.poll.return_value = 0
        stop_owned([live, exited])
        live.terminate.assert_called_once_with()
        exited.terminate.assert_not_called()
        unrelated.terminate.assert_not_called()

    def test_gpu_parser_preserves_real_thermal_flag(self):
        response = subprocess.CompletedProcess([], 0, stdout='90, 210, 5200, 8192, Active\n')
        with patch('scripts.benchmark_cpu_threads.subprocess.run', return_value=response):
            result = gpu_state()
        self.assertTrue(result['thermal_slowdown'])
        self.assertEqual(result['sm_mhz'], 210)

    def test_incomplete_or_invalid_gpu_observation_fails_closed(self):
        for output in ('90, 210, 5200, 8192, Unknown\n', '90, 210, 9000, 8192, Active\n',
                       'nan, 210, 5200, 8192, Active\n', '90, 210\n'):
            response = subprocess.CompletedProcess([], 0, stdout=output)
            with self.subTest(output=output), patch('scripts.benchmark_cpu_threads.subprocess.run', return_value=response), self.assertRaises(ValueError):
                gpu_state()


if __name__ == '__main__':
    unittest.main()
