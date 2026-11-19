# ==============================================================================
# Program: test_requested_test_additions.py
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
import tempfile
import threading
from types import SimpleNamespace
import unittest

from app.agent import AgentRun
from app.deliverables import inspect_deliverables,verification_paths


SEED='import unittest\nclass Seed(unittest.TestCase):\n def test_seed(self): self.assertEqual(2+2,4)\n'
EXTRA='import unittest\nclass Extra(unittest.TestCase):\n def test_negative(self): self.assertEqual(abs(-3),3)\n'


# ------------------------------------------------------------------------------
# RequestedTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class RequestedTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # setUp: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'test_seed.py').write_text(SEED)
        (self.root/'report.json').write_text('[]\n')
        self.goal='Build a Python program. Add your own relevant tests and save report.json.'

    # ------------------------------------------------------------------------------
    # runner: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def runner(self,checkpoint=None):
        request=SimpleNamespace(prompt=self.goal,mode='agent',max_tokens=None,run_until_done=True)
        run=AgentRun(SimpleNamespace(config={}),SimpleNamespace(),str(self.root),request,lambda:[],lambda *a:None,lambda *a:None,lambda *a:None,threading.Event(),checkpoint)
        run.state['cwd']=str(self.root);run.state['files_written']=[str(self.root/'report.json')]
        return run

    # ------------------------------------------------------------------------------
    # issue: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def issue(self,run):return inspect_deliverables(run.contract,run.state)[0]

    # ------------------------------------------------------------------------------
    # test_preexisting_supplied_tests_do_not_satisfy_add_own_tests: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_preexisting_supplied_tests_do_not_satisfy_add_own_tests(self):
        run=self.runner();self.assertIsNotNone(self.issue(run))
        self.assertIn('test',self.issue(run).lower())

    # ------------------------------------------------------------------------------
    # test_new_actual_test_source_satisfies_presence_and_enters_hash_proof: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_new_actual_test_source_satisfies_presence_and_enters_hash_proof(self):
        run=self.runner();(self.root/'test_extra.py').write_text(EXTRA)
        self.assertIsNone(self.issue(run))
        self.assertIn(str(self.root/'test_extra.py'),verification_paths(run.contract,run.state))

    # ------------------------------------------------------------------------------
    # test_comment_only_edit_does_not_count_as_added_testing: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_comment_only_edit_does_not_count_as_added_testing(self):
        run=self.runner();(self.root/'test_seed.py').write_text(SEED+'# More tests added\n')
        self.assertIsNotNone(self.issue(run))

    # ------------------------------------------------------------------------------
    # test_adding_a_test_to_an_existing_file_is_supported: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_adding_a_test_to_an_existing_file_is_supported(self):
        run=self.runner();(self.root/'test_seed.py').write_text(SEED+' def test_negative(self): self.assertEqual(abs(-3),3)\n')
        self.assertIsNone(self.issue(run))

    # ------------------------------------------------------------------------------
    # test_explicit_no_new_tests_does_not_require_them: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_explicit_no_new_tests_does_not_require_them(self):
        self.goal='Fix a Python program. Do not add tests. Save report.json.'
        self.assertIsNone(self.issue(self.runner()))

    # ------------------------------------------------------------------------------
    # test_rust_unit_request_does_not_accept_only_python_tests: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_rust_unit_request_does_not_accept_only_python_tests(self):
        self.goal='Create a Rust Cargo application. Add relevant Rust unit tests. Save report.json.'
        run=self.runner();(self.root/'test_extra.py').write_text(EXTRA)
        self.assertIsNotNone(self.issue(run))
        (self.root/'src').mkdir();(self.root/'src/main.rs').write_text('fn main() {}\n#[test]\nfn edge() { assert_eq!(2+2,4); }\n')
        self.assertIsNone(self.issue(run))

    # ------------------------------------------------------------------------------
    # test_rust_comment_marker_cannot_fabricate_a_unit_test: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_rust_comment_marker_cannot_fabricate_a_unit_test(self):
        self.goal='Create a Rust Cargo application. Add relevant Rust unit tests. Save report.json.'
        run=self.runner();(self.root/'src').mkdir();(self.root/'src/main.rs').write_text('fn main() {}\n// #[test] fn fake() {}\n')
        self.assertIsNotNone(self.issue(run))

    # ------------------------------------------------------------------------------
    # test_resume_keeps_original_baseline_instead_of_recapturing_additions: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_resume_keeps_original_baseline_instead_of_recapturing_additions(self):
        run=self.runner();(self.root/'test_extra.py').write_text(EXTRA)
        run.state['turns']=2;resumed=self.runner(run.state)
        self.assertIsNone(self.issue(resumed))

    # ------------------------------------------------------------------------------
    # test_legacy_resume_does_not_invent_an_original_baseline: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_legacy_resume_does_not_invent_an_original_baseline(self):
        resumed=self.runner({'turns':2})
        self.assertIsNone(self.issue(resumed))

    # ------------------------------------------------------------------------------
    # test_conditional_test_request_does_not_require_unnecessary_additions: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_conditional_test_request_does_not_require_unnecessary_additions(self):
        self.goal='Fix a Python program. Add tests only if necessary. Save report.json.'
        self.assertIsNone(self.issue(self.runner()))
