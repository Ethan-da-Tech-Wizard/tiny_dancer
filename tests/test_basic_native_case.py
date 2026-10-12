# SPDX-License-Identifier: Apache-2.0
import tempfile
from pathlib import Path
import unittest
from scripts.native_suite_cases import CASES, grade
from app.tools import ROOT


class BasicNativeGraderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'run');self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)

    def test_correct_fixture_proves_the_independent_grader_witness(self):
        (self.folder/'labels.py').write_text('def normalize_label(text):\n return " ".join(text.split()).lower()\n')
        checks=grade(self.folder,'labels',ROOT)
        self.assertEqual(len(checks),4);self.assertTrue(all(c['passed'] for c in checks))

    def test_missing_function_is_a_nonempty_failure(self):
        checks=grade(self.folder,'labels',ROOT)
        self.assertEqual(len(checks),4);self.assertTrue(all(not c['passed'] for c in checks))

    def test_ascii_only_implementation_cannot_hide_unicode_failure(self):
        (self.folder/'labels.py').write_text('def normalize_label(text):\n return " ".join(text.split()).encode("ascii","ignore").decode().lower()\n')
        checks=grade(self.folder,'labels',ROOT)
        self.assertFalse(all(c['passed'] for c in checks))

    def test_debug_output_cannot_be_mistaken_for_a_correct_json_receipt(self):
        (self.folder/'labels.py').write_text('print("debug")\ndef normalize_label(text):\n return " ".join(text.split()).lower()\n')
        self.assertTrue(all(not c['passed'] for c in grade(self.folder,'labels',ROOT)))

    def test_small_frozen_goal_has_six_seeds_and_requires_new_tests(self):
        case=CASES['labels']
        self.assertEqual(case['acceptance'].count(' def test_'),6)
        self.assertIn('Add your own relevant tests',case['prompt'])
        self.assertEqual(case['kind'],'module')


if __name__=='__main__':unittest.main()
