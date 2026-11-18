# Program: tiny_dancer - tests/test_scan_regression.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Tests for scan regression (exercises scripts.inventory_extended_audit).
# SPDX-License-Identifier: Apache-2.0
"""Tests for scan regression (exercises scripts.inventory_extended_audit)."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from scripts.inventory_extended_audit import check_special_files

ROOT=Path(__file__).resolve().parents[1]


# -------- scan regression controls --------
class ScanRegressionControls(unittest.TestCase):
    """Helper type scan regression controls."""
    def setUp(self):
        """Prepare the fixtures for each test."""
        self.temporary=tempfile.TemporaryDirectory(dir=ROOT/'run');self.addCleanup(self.temporary.cleanup)
        self.folder=Path(self.temporary.name)
        shutil.copyfile(ROOT/'scripts/fixtures/inventory_reference.py',self.folder/'inventory.py')
        shutil.copyfile(ROOT/'scripts/fixtures/scan_regression_tests.py',self.folder/'test_scan_regression.py')

    def run_regression(self):
        """Test helper: run regression."""
        return subprocess.run([str(ROOT/'.venv/bin/python'),'-m','unittest','test_scan_regression','-v'],
                              cwd=self.folder,capture_output=True,text=True,timeout=20)

    def test_conforming_control_passes_actual_error_tests(self):
        """Checks that conforming control passes actual error tests."""
        result=self.run_regression();self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Ran 2 tests',result.stderr)

    def test_silent_walk_error_is_detected(self):
        """Checks that silent walk error is detected."""
        program=self.folder/'inventory.py';source=program.read_text()
        self.assertIn('onerror=fail_scan',source)
        program.write_text(source.replace('onerror=fail_scan','onerror=None'))
        result=self.run_regression();self.assertNotEqual(result.returncode,0)
        self.assertIn('FAIL: test_unreadable_nested_directory',result.stderr)
        self.assertIn('test_unreadable_file (test_scan_regression.ScanErrorRegressionTests.test_unreadable_file) ... ok',result.stderr)

    def test_special_files_calibrated_against_good_and_bad_programs(self):
        """Checks that special files calibrated against good and bad programs."""
        self.assertTrue(check_special_files(self.folder,ROOT)[0]['passed'])
        (self.folder/'inventory.py').write_text('import sys\nfrom pathlib import Path\nfor p in Path(sys.argv[1]).iterdir():p.read_bytes()\n')
        result=check_special_files(self.folder,ROOT)[0]
        self.assertFalse(result['passed']);self.assertTrue(result['timed_out'])
