# Program: tiny_dancer - tests/test_labels_goal_audit.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Tests for labels goal audit (exercises scripts.labels_goal_audit).
# SPDX-License-Identifier: Apache-2.0
"""Tests for labels goal audit (exercises scripts.labels_goal_audit)."""
import tempfile
import unittest
from pathlib import Path
from scripts.labels_goal_audit import check_labels_goal


# -------- labels goal audit tests --------
class LabelsGoalAuditTests(unittest.TestCase):
    """Test group for labels goal audit."""
    def setUp(self):
        """Prepare the fixtures for each test."""
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'run')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def product(self, expression):
        """Test helper: product."""
        (self.folder/'labels.py').write_text('def normalize_label(text):\n    return '+expression+'\n')
        return check_labels_goal(self.folder)

    def test_correct_unicode_behavior(self):
        """Checks that correct unicode behavior."""
        self.assertTrue(all(c['passed'] for c in self.product("' '.join(text.split()).lower()")))

    def test_test_tailored_dot_removal_fails(self):
        """Checks that test tailored dot removal fails."""
        checks = self.product("' '.join(text.split()).lower().replace('i\\u0307', 'i')")
        self.assertFalse(checks[0]['passed']); self.assertFalse(checks[1]['passed'])
        self.assertFalse(checks[3]['passed'])

    def test_casefold_is_not_lowercase(self):
        """Checks that casefold is not lowercase."""
        self.assertFalse(self.product("' '.join(text.split()).casefold()")[2]['passed'])

    def test_missing_product_cannot_pass(self):
        """Checks that missing product cannot pass."""
        self.assertTrue(all(not c['passed'] for c in check_labels_goal(self.folder)))
