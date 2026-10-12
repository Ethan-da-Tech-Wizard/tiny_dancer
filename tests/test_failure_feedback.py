# SPDX-License-Identifier: Apache-2.0
"""Real failing runners and repair checkpoints, rather than model approval."""
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from app.baseline_preview import baseline_preview
from app.prompting import compact_result
from app.working_memory import checkpoint_evidence


class FailureFeedbackTests(unittest.TestCase):
    def failures(self):
        class Broken(unittest.TestCase):
            def test_long_first(self): self.assertEqual('A' * 9000, 'B' * 9000)
            def test_middle(self):
                for item in (3, 7):
                    with self.subTest(item=item): self.assertEqual(item + 1, item)
            def test_last(self): raise ValueError('FINAL_ERROR_SENTINEL')
        stream = io.StringIO()
        unittest.TextTestRunner(stream=stream).run(unittest.defaultTestLoader.loadTestsFromTestCase(Broken))
        return stream.getvalue()

    def test_all_failure_identities_survive_baseline_and_repeated_projection(self):
        output = self.failures()
        result = {'exit_code': 1, 'artifact': '/artifacts/full.json', 'checks': [
            {'command': 'python3 -m unittest', 'exit_code': 1, 'output': output}]}
        original = json.dumps(result)
        value = baseline_preview('run_checks', result)
        for _ in range(3): value = compact_result(value)
        evidence = value['checks'][0]['failure_evidence']
        shown = json.dumps(evidence)
        for name in ('test_long_first', 'test_middle', 'item=3', 'item=7', 'test_last', 'FINAL_ERROR_SENTINEL'):
            self.assertIn(name, shown)
        self.assertLessEqual(len(json.dumps(evidence, ensure_ascii=False, separators=(',', ':'))), 2400)
        self.assertEqual(json.dumps(result), original)
        self.assertNotIn('verified', evidence)

    def test_checkpoint_keeps_middle_failure_even_with_small_raw_output_budget(self):
        result = baseline_preview('run_checks', {'exit_code': 1, 'checks': [
            {'exit_code': 1, 'output': self.failures()}], 'artifact': '/artifacts/full.json'})
        with tempfile.TemporaryDirectory() as folder:
            memory = checkpoint_evidence([('run_checks', result)], folder, [], failure_budget=400)
        failure = memory['last_failed_result']
        self.assertLessEqual(len(failure['preview']), 400)
        self.assertIn('item=7', json.dumps(failure['failure_evidence']))
        self.assertEqual(failure['result']['artifact'], '/artifacts/full.json')

    def test_real_pytest_failure_preserves_mismatch_and_location(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'test_real.py'
            path.write_text('def test_real():\n    assert {"answer": 2} == {"answer": 3}\n')
            result = subprocess.run([__import__('sys').executable, '-m', 'pytest', '-q', str(path)],
                                    capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        value = compact_result({'exit_code': result.returncode, 'output': result.stdout + result.stderr})
        evidence = json.dumps(value['failure_evidence'])
        self.assertIn('test_real', evidence)
        self.assertIn('answer', evidence)
        self.assertIn('AssertionError', evidence)

    def test_passing_or_non_test_output_cannot_create_failure_or_verification(self):
        for result in ({'exit_code': 0, 'output': self.failures()},
                       {'exit_code': 1, 'output': 'network refused connection'},
                       {'exit_code': 0, 'output': 'Ran 4 tests in 0.1s\nOK'}):
            self.assertNotIn('failure_evidence', compact_result(result))

    def test_rust_assertion_has_actual_sides_and_test_identity(self):
        output = "---- tests::boundary stdout ----\nthread 'tests::boundary' panicked at src/lib.rs:21:9:\nassertion `left == right` failed\n  left: 3\n right: 5\n\nfailures:\n tests::boundary\ntest result: FAILED. 0 passed; 1 failed; 0 ignored\n"
        evidence = json.dumps(compact_result({'exit_code': 101, 'output': output})['failure_evidence'])
        for value in ('tests::boundary', 'src/lib.rs:21:9', 'left: 3', 'right: 5'):
            self.assertIn(value, evidence)

    def test_large_failure_list_marks_omissions_without_fabricating_details(self):
        output = ''.join(f'FAIL: test_{i} (suite.Tests.test_{i})\n'+'-'*70+'\nAssertionError: actual != expected\n' for i in range(100))
        evidence = compact_result({'exit_code': 1, 'output': output})['failure_evidence']
        self.assertGreater(evidence['omitted'], 0)
        self.assertIn('read_hint', evidence)
        self.assertLessEqual(len(json.dumps(evidence, ensure_ascii=False, separators=(',', ':'))), 2400)


if __name__ == '__main__': unittest.main()
