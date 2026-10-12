# SPDX-License-Identifier: Apache-2.0
import tempfile
import unittest
from pathlib import Path
from scripts.labels_goal_audit import check_labels_goal


class LabelsGoalAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'run')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def product(self, expression):
        (self.folder/'labels.py').write_text('def normalize_label(text):\n    return '+expression+'\n')
        return check_labels_goal(self.folder)

    def test_correct_unicode_behavior(self):
        self.assertTrue(all(c['passed'] for c in self.product("' '.join(text.split()).lower()")))

    def test_test_tailored_dot_removal_fails(self):
        checks = self.product("' '.join(text.split()).lower().replace('i\\u0307', 'i')")
        self.assertFalse(checks[0]['passed']); self.assertFalse(checks[1]['passed'])
        self.assertFalse(checks[3]['passed'])

    def test_casefold_is_not_lowercase(self):
        self.assertFalse(self.product("' '.join(text.split()).casefold()")[2]['passed'])

    def test_missing_product_cannot_pass(self):
        self.assertTrue(all(not c['passed'] for c in check_labels_goal(self.folder)))
