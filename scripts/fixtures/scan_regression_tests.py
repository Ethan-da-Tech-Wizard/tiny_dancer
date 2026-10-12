# SPDX-License-Identifier: Apache-2.0
"""Known filesystem error regressions supplied before a native repair task."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent


class ScanErrorRegressionTests(unittest.TestCase):
    def check_denied(self, directory):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            base = Path(temporary); tree = base/'tree'; tree.mkdir()
            denied = tree/'restricted'
            if directory:
                denied.mkdir(); (denied/'record.txt').write_text('must be scanned')
            else:
                denied.write_text('must be scanned')
            out = base/'out.json'; original = b'previous successful export'; out.write_bytes(original)
            mode = denied.stat().st_mode & 0o777
            denied.chmod(0)
            try:
                with self.assertRaises(PermissionError):
                    list(denied.iterdir()) if directory else denied.read_bytes()
                result = subprocess.run([sys.executable,str(ROOT/'inventory.py'),str(tree),str(out)],
                                        cwd=ROOT,capture_output=True,text=True,timeout=15)
                self.assertNotEqual(result.returncode,0,'A real scan error must report failure')
                self.assertTrue(result.stderr.strip(),'Report the scan error')
                self.assertNotIn('Traceback',result.stderr)
                self.assertEqual(out.read_bytes(),original,'A failed scan must preserve the earlier export')
            finally:
                denied.chmod(mode)

    def test_unreadable_nested_directory(self):
        self.check_denied(True)

    def test_unreadable_file(self):
        self.check_denied(False)


if __name__ == '__main__':
    unittest.main()
