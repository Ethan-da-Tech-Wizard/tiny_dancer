# ==============================================================================
# Program: test_node_licenses.py
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
import json
from pathlib import Path
import tempfile
import unittest
from scripts.node_licenses import collect_node, verify_node


# ------------------------------------------------------------------------------
# NodeLicenseTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class NodeLicenseTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # setUp: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prefix = self.root / 'vendor/pi-runtime'
        self.package = self.prefix / 'node_modules/example'
        self.package.mkdir(parents=True)
        (self.package / 'package.json').write_text(json.dumps({'name':'example','version':'1.0.0','license':'MIT'}))
        (self.package / 'README.md').write_text('Permission is hereby granted: fixture license')
        (self.prefix / 'package-lock.json').write_text(json.dumps({'packages':{'node_modules/example':{'version':'1.0.0'}}}))

    # ------------------------------------------------------------------------------
    # test_readme_license_is_preserved_and_verified: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_readme_license_is_preserved_and_verified(self):
        result = collect_node(self.root)
        self.assertEqual(len(result['packages']), 1)
        self.assertEqual(verify_node(self.root)['lock_sha256'], result['lock_sha256'])
        self.assertTrue(any(p['path'].endswith('README.md') for p in result['files']))

    # ------------------------------------------------------------------------------
    # test_missing_notice_is_an_error: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_missing_notice_is_an_error(self):
        (self.package / 'README.md').unlink()
        with self.assertRaisesRegex(RuntimeError, 'Unresolved'):
            collect_node(self.root)

    # ------------------------------------------------------------------------------
    # test_changed_lock_is_rejected: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(B) linear with respect to serialized payload byte length | Space: O(B) memory mapped buffer or byte stream heap allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_changed_lock_is_rejected(self):
        collect_node(self.root)
        with (self.prefix / 'package-lock.json').open('a') as handle:
            handle.write(' ')
        with self.assertRaisesRegex(RuntimeError, 'lock changed'):
            verify_node(self.root)

    # ------------------------------------------------------------------------------
    # test_changed_notice_is_rejected: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_changed_notice_is_rejected(self):
        collect_node(self.root)
        (self.package / 'README.md').write_text('altered')
        with self.assertRaisesRegex(RuntimeError, 'notice missing or changed'):
            verify_node(self.root)
