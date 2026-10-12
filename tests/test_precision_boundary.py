# SPDX-License-Identifier: Apache-2.0
"""Independent grader controls are CLI fixtures, not native capability evidence."""
from pathlib import Path
import tempfile
import unittest
from scripts.evaluate_precision_boundary import probe


class PrecisionBoundaryTests(unittest.TestCase):
    def folder(self,source):
        temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'workspace');self.addCleanup(temp.cleanup)
        folder=Path(temp.name);(folder/'summarize.py').write_text(source);return folder

    def test_known_fixture_outputs_are_checked_by_both_actual_cli_calls(self):
        source='import json,sys\nfrom pathlib import Path\nvalue="1.01" if Path(sys.argv[1]).name=="signed.csv" else "1234567890"*4+".03"\nprint(json.dumps({"huge":value}))\n'
        outcomes=probe(self.folder(source),40)
        self.assertTrue(all(c['passed'] for c in outcomes.values()))
        self.assertEqual(set(outcomes),{'signed','total'})

    def test_wrong_valid_json_does_not_pass(self):
        outcomes=probe(self.folder('print(\'{"huge":"9.00"}\')\n'),40)
        self.assertTrue(all(not c['passed'] and c['exit_code']==0 for c in outcomes.values()))

    def test_right_stdout_with_nonzero_exit_does_not_pass(self):
        source='import json,sys\nfrom pathlib import Path\nprint(json.dumps({"huge":"1.01" if Path(sys.argv[1]).name=="signed.csv" else "1234567890"*4+".03"}))\nsys.exit(1)\n'
        self.assertTrue(all(not c['passed'] for c in probe(self.folder(source),40).values()))

    def test_malformed_json_is_reported_as_failed_not_an_exception(self):
        outcomes=probe(self.folder('print("NOT_JSON")\n'),40)
        self.assertTrue(all(not c['passed'] for c in outcomes.values()))
