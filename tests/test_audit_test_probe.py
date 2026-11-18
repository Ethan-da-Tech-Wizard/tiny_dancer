# Program: tiny_dancer - tests/test_audit_test_probe.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Tests for audit test probe (exercises scripts.audit_test_probe).
# SPDX-License-Identifier: Apache-2.0
"""Tests for audit test probe (exercises scripts.audit_test_probe)."""
import json
from pathlib import Path
import tempfile
import unittest
from openai_harmony import Message,Role
from scripts.audit_test_probe import submitted_code,grade_verification


# -------- audit test probe tests --------
class AuditTestProbeTests(unittest.TestCase):
    """Test group for audit test probe."""
    def test_only_completed_tool_content_can_be_submitted(self):
        """Checks that only completed tool content can be submitted."""
        call=Message.from_role_and_content(Role.ASSISTANT,json.dumps({'content':'import unittest\n'})).with_recipient('functions.write_verification')
        private=Message.from_role_and_content(Role.ASSISTANT,'private').with_channel('analysis')
        self.assertEqual(submitted_code([private,call]),'import unittest\n')
        for messages in ([private],[call,call]):
            with self.assertRaises(ValueError):submitted_code(messages)

    def test_real_assertion_distinguishes_controls_without_source_changes(self):
        """Checks that real assertion distinguishes controls without source changes."""
        code='import unittest,inventory\nclass TestContract(unittest.TestCase):\n def test_behavior(self):self.assertEqual(inventory.value(),2)\n'
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'run').mkdir()
            result=grade_verification('def value():return 1\n','def value():return 2\n',code,root)
        self.assertTrue(result['passed'],result)

    def test_vacuous_or_broken_tests_do_not_qualify(self):
        """Checks that vacuous or broken tests do not qualify."""
        for code in ['import unittest\n','import unittest\nclass Tests(unittest.TestCase):\n def test_nothing(self):pass\n','raise RuntimeError("broken setup")\n']:
            with tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary);(root/'run').mkdir()
                result=grade_verification('x=1\n','x=1\n',code,root)
            self.assertFalse(result['passed'],result)

    def test_always_failing_tests_reject_conforming_control(self):
        """Checks that always failing tests reject conforming control."""
        code='import unittest\nclass Tests(unittest.TestCase):\n def test_bad_expectation(self):self.fail("always wrong")\n'
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'run').mkdir()
            result=grade_verification('x=1\n','x=1\n',code,root)
        self.assertFalse(result['passed']);self.assertFalse(result['checks']['accepts_conforming_control'])
