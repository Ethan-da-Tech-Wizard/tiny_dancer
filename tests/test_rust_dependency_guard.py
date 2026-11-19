# ==============================================================================
# Program: test_rust_dependency_guard.py
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
import tempfile
from pathlib import Path
import unittest

from app.deliverables import inspect_deliverables,verification_paths
from app.task_policy import contract_for


# ------------------------------------------------------------------------------
# DependencyCompletionTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class DependencyCompletionTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # setUp: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'report.json').write_text('[]\n')
        self.goal='Create a standard-library-only Rust Cargo application. Run tests and save the JSON output to report.json. Do not add external dependencies.'
        self.state={'goal':self.goal,'cwd':str(self.root),'files_written':[str(self.root/'report.json')]}
        self.contract=contract_for(self.goal)

    # ------------------------------------------------------------------------------
    # issue: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def issue(self,manifest):
        (self.root/'Cargo.toml').write_text(manifest)
        return inspect_deliverables(self.contract,self.state)[0]

    # ------------------------------------------------------------------------------
    # test_saved_json_cannot_hide_forbidden_dependencies: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_saved_json_cannot_hide_forbidden_dependencies(self):
        issue=self.issue('[package]\nname="ranges"\nversion="0.1.0"\n[dependencies]\nserde_json="1.0"\n')
        self.assertIsNotNone(issue);self.assertIn('serde_json',issue)

    # ------------------------------------------------------------------------------
    # test_actual_manifest_is_part_of_source_proof: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_actual_manifest_is_part_of_source_proof(self):
        self.issue('[package]\nname="ranges"\nversion="0.1.0"\n')
        self.assertIn(str(self.root/'Cargo.toml'),verification_paths(self.contract,self.state))

    # ------------------------------------------------------------------------------
    # test_removing_dependency_repairs_constraint_and_preserves_json_check: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_removing_dependency_repairs_constraint_and_preserves_json_check(self):
        self.assertIsNone(self.issue('[package]\nname="ranges"\nversion="0.1.0"\n[dependencies]\n'))
        (self.root/'report.json').unlink()
        self.assertIn('Save the requested JSON',inspect_deliverables(self.contract,self.state)[0])

    # ------------------------------------------------------------------------------
    # test_target_and_test_dependencies_are_checked: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_target_and_test_dependencies_are_checked(self):
        issue=self.issue('[package]\nname="ranges"\nversion="0.1.0"\n[target."cfg(unix)".dev-dependencies]\nhelper="1.0"\n')
        self.assertIsNotNone(issue);self.assertIn('helper',issue)

    # ------------------------------------------------------------------------------
    # test_unreadable_manifest_does_not_establish_compliance: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_unreadable_manifest_does_not_establish_compliance(self):
        self.assertIsNotNone(self.issue('this is not TOML'))

    # ------------------------------------------------------------------------------
    # test_dependencies_remain_allowed_when_user_allows_them: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_dependencies_remain_allowed_when_user_allows_them(self):
        self.state['goal']='Create a Rust Cargo application; dependencies are allowed. Write report.json.'
        self.contract=contract_for(self.state['goal'])
        self.assertIsNone(self.issue('[dependencies]\nserde_json="1.0"\n'))

    # ------------------------------------------------------------------------------
    # test_python_goal_does_not_inspect_unrelated_cargo_manifest: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_python_goal_does_not_inspect_unrelated_cargo_manifest(self):
        self.state['goal']='Write a standard-library-only Python script and report.json.'
        self.contract=contract_for(self.state['goal'])
        self.assertIsNone(self.issue('[dependencies]\nserde_json="1.0"\n'))


    # ------------------------------------------------------------------------------
    # test_existing_dependencies_allowed_when_only_new_ones_forbidden: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_existing_dependencies_allowed_when_only_new_ones_forbidden(self):
        self.state['goal']='Fix a Rust application. Do not add external dependencies. Write report.json.'
        self.contract=contract_for(self.state['goal'])
        self.assertIsNone(self.issue('[dependencies]\nserde_json="1.0"\n'))


if __name__=='__main__':unittest.main()
