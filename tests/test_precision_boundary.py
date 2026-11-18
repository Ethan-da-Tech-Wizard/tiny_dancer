# Program: tiny_dancer - tests/test_precision_boundary.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Tests for precision boundary (exercises scripts.evaluate_precision_boundary).
# SPDX-License-Identifier: Apache-2.0
"""Independent grader controls are CLI fixtures, not native capability evidence."""
from pathlib import Path
import tempfile
import unittest
from scripts.evaluate_precision_boundary import probe


# -------- precision boundary tests --------
class PrecisionBoundaryTests(unittest.TestCase):
    """Test group for precision boundary."""
    def folder(self,source):
        """Test helper: folder."""
        temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'workspace');self.addCleanup(temp.cleanup)
        folder=Path(temp.name);(folder/'summarize.py').write_text(source);return folder

    def test_known_fixture_outputs_are_checked_by_both_actual_cli_calls(self):
        """Checks that known fixture outputs are checked by both actual cli calls."""
        source='import json,sys\nfrom pathlib import Path\nvalue="1.01" if Path(sys.argv[1]).name=="signed.csv" else "1234567890"*4+".03"\nprint(json.dumps({"huge":value}))\n'
        outcomes=probe(self.folder(source),40)
        self.assertTrue(all(c['passed'] for c in outcomes.values()))
        self.assertEqual(set(outcomes),{'signed','total'})

    def test_wrong_valid_json_does_not_pass(self):
        """Checks that wrong valid json does not pass."""
        outcomes=probe(self.folder('print(\'{"huge":"9.00"}\')\n'),40)
        self.assertTrue(all(not c['passed'] and c['exit_code']==0 for c in outcomes.values()))

    def test_right_stdout_with_nonzero_exit_does_not_pass(self):
        """Checks that right stdout with nonzero exit does not pass."""
        source='import json,sys\nfrom pathlib import Path\nprint(json.dumps({"huge":"1.01" if Path(sys.argv[1]).name=="signed.csv" else "1234567890"*4+".03"}))\nsys.exit(1)\n'
        self.assertTrue(all(not c['passed'] for c in probe(self.folder(source),40).values()))

    def test_malformed_json_is_reported_as_failed_not_an_exception(self):
        """Checks that malformed json is reported as failed not an exception."""
        outcomes=probe(self.folder('print("NOT_JSON")\n'),40)
        self.assertTrue(all(not c['passed'] for c in outcomes.values()))
