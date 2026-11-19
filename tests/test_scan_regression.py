# ==============================================================================
# Program: test_scan_regression.py
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
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from scripts.inventory_extended_audit import check_special_files

ROOT=Path(__file__).resolve().parents[1]


# ------------------------------------------------------------------------------
# ScanRegressionControls: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class ScanRegressionControls(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # setUp: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(dir=ROOT/'run');self.addCleanup(self.temporary.cleanup)
        self.folder=Path(self.temporary.name)
        shutil.copyfile(ROOT/'scripts/fixtures/inventory_reference.py',self.folder/'inventory.py')
        shutil.copyfile(ROOT/'scripts/fixtures/scan_regression_tests.py',self.folder/'test_scan_regression.py')

    # ------------------------------------------------------------------------------
    # run_regression: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def run_regression(self):
        return subprocess.run([str(ROOT/'.venv/bin/python'),'-m','unittest','test_scan_regression','-v'],
                              cwd=self.folder,capture_output=True,text=True,timeout=20)

    # ------------------------------------------------------------------------------
    # test_conforming_control_passes_actual_error_tests: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_conforming_control_passes_actual_error_tests(self):
        result=self.run_regression();self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Ran 2 tests',result.stderr)

    # ------------------------------------------------------------------------------
    # test_silent_walk_error_is_detected: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_silent_walk_error_is_detected(self):
        program=self.folder/'inventory.py';source=program.read_text()
        self.assertIn('onerror=fail_scan',source)
        program.write_text(source.replace('onerror=fail_scan','onerror=None'))
        result=self.run_regression();self.assertNotEqual(result.returncode,0)
        self.assertIn('FAIL: test_unreadable_nested_directory',result.stderr)
        self.assertIn('test_unreadable_file (test_scan_regression.ScanErrorRegressionTests.test_unreadable_file) ... ok',result.stderr)

    # ------------------------------------------------------------------------------
    # test_special_files_calibrated_against_good_and_bad_programs: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_special_files_calibrated_against_good_and_bad_programs(self):
        self.assertTrue(check_special_files(self.folder,ROOT)[0]['passed'])
        (self.folder/'inventory.py').write_text('import sys\nfrom pathlib import Path\nfor p in Path(sys.argv[1]).iterdir():p.read_bytes()\n')
        result=check_special_files(self.folder,ROOT)[0]
        self.assertFalse(result['passed']);self.assertTrue(result['timed_out'])
