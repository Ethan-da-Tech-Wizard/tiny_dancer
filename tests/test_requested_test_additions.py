# Program: tiny_dancer - tests/test_requested_test_additions.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Tests for requested test additions (exercises app.agent, app.deliverables).
# SPDX-License-Identifier: Apache-2.0
"""Tests for requested test additions (exercises app.agent, app.deliverables)."""
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest

from app.agent import AgentRun
from app.deliverables import inspect_deliverables,verification_paths


SEED='import unittest\nclass Seed(unittest.TestCase):\n def test_seed(self): self.assertEqual(2+2,4)\n'
EXTRA='import unittest\nclass Extra(unittest.TestCase):\n def test_negative(self): self.assertEqual(abs(-3),3)\n'


# -------- requested tests --------
class RequestedTests(unittest.TestCase):
    """Test group for requested."""
    def setUp(self):
        """Prepare the fixtures for each test."""
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'test_seed.py').write_text(SEED)
        (self.root/'report.json').write_text('[]\n')
        self.goal='Build a Python program. Add your own relevant tests and save report.json.'

    def runner(self,checkpoint=None):
        """Test helper: runner."""
        request=SimpleNamespace(prompt=self.goal,mode='agent',max_tokens=None,run_until_done=True)
        run=AgentRun(SimpleNamespace(config={}),SimpleNamespace(),str(self.root),request,lambda:[],lambda *a:None,lambda *a:None,lambda *a:None,threading.Event(),checkpoint)
        run.state['cwd']=str(self.root);run.state['files_written']=[str(self.root/'report.json')]
        return run

    # Test helper: issue.
    def issue(self,run):return inspect_deliverables(run.contract,run.state)[0]

    def test_preexisting_supplied_tests_do_not_satisfy_add_own_tests(self):
        """Checks that preexisting supplied tests do not satisfy add own tests."""
        run=self.runner();self.assertIsNotNone(self.issue(run))
        self.assertIn('test',self.issue(run).lower())

    def test_new_actual_test_source_satisfies_presence_and_enters_hash_proof(self):
        """Checks that new actual test source satisfies presence and enters hash proof."""
        run=self.runner();(self.root/'test_extra.py').write_text(EXTRA)
        self.assertIsNone(self.issue(run))
        self.assertIn(str(self.root/'test_extra.py'),verification_paths(run.contract,run.state))

    def test_comment_only_edit_does_not_count_as_added_testing(self):
        """Checks that comment only edit does not count as added testing."""
        run=self.runner();(self.root/'test_seed.py').write_text(SEED+'# More tests added\n')
        self.assertIsNotNone(self.issue(run))

    def test_adding_a_test_to_an_existing_file_is_supported(self):
        """Checks that adding a test to an existing file is supported."""
        run=self.runner();(self.root/'test_seed.py').write_text(SEED+' def test_negative(self): self.assertEqual(abs(-3),3)\n')
        self.assertIsNone(self.issue(run))

    def test_explicit_no_new_tests_does_not_require_them(self):
        """Checks that explicit no new tests does not require them."""
        self.goal='Fix a Python program. Do not add tests. Save report.json.'
        self.assertIsNone(self.issue(self.runner()))

    def test_rust_unit_request_does_not_accept_only_python_tests(self):
        """Checks that rust unit request does not accept only python tests."""
        self.goal='Create a Rust Cargo application. Add relevant Rust unit tests. Save report.json.'
        run=self.runner();(self.root/'test_extra.py').write_text(EXTRA)
        self.assertIsNotNone(self.issue(run))
        (self.root/'src').mkdir();(self.root/'src/main.rs').write_text('fn main() {}\n#[test]\nfn edge() { assert_eq!(2+2,4); }\n')
        self.assertIsNone(self.issue(run))

    def test_rust_comment_marker_cannot_fabricate_a_unit_test(self):
        """Checks that rust comment marker cannot fabricate a unit test."""
        self.goal='Create a Rust Cargo application. Add relevant Rust unit tests. Save report.json.'
        run=self.runner();(self.root/'src').mkdir();(self.root/'src/main.rs').write_text('fn main() {}\n// #[test] fn fake() {}\n')
        self.assertIsNotNone(self.issue(run))

    def test_resume_keeps_original_baseline_instead_of_recapturing_additions(self):
        """Checks that resume keeps original baseline instead of recapturing additions."""
        run=self.runner();(self.root/'test_extra.py').write_text(EXTRA)
        run.state['turns']=2;resumed=self.runner(run.state)
        self.assertIsNone(self.issue(resumed))

    def test_legacy_resume_does_not_invent_an_original_baseline(self):
        """Checks that legacy resume does not invent an original baseline."""
        resumed=self.runner({'turns':2})
        self.assertIsNone(self.issue(resumed))

    def test_conditional_test_request_does_not_require_unnecessary_additions(self):
        """Checks that conditional test request does not require unnecessary additions."""
        self.goal='Fix a Python program. Add tests only if necessary. Save report.json.'
        self.assertIsNone(self.issue(self.runner()))
