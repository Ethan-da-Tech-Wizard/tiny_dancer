# SPDX-License-Identifier: Apache-2.0
import tempfile
from pathlib import Path
import unittest

from app.deliverables import inspect_deliverables,verification_paths
from app.task_policy import contract_for


class DependencyCompletionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'report.json').write_text('[]\n')
        self.goal='Create a standard-library-only Rust Cargo application. Run tests and save the JSON output to report.json. Do not add external dependencies.'
        self.state={'goal':self.goal,'cwd':str(self.root),'files_written':[str(self.root/'report.json')]}
        self.contract=contract_for(self.goal)

    def issue(self,manifest):
        (self.root/'Cargo.toml').write_text(manifest)
        return inspect_deliverables(self.contract,self.state)[0]

    def test_saved_json_cannot_hide_forbidden_dependencies(self):
        issue=self.issue('[package]\nname="ranges"\nversion="0.1.0"\n[dependencies]\nserde_json="1.0"\n')
        self.assertIsNotNone(issue);self.assertIn('serde_json',issue)

    def test_actual_manifest_is_part_of_source_proof(self):
        self.issue('[package]\nname="ranges"\nversion="0.1.0"\n')
        self.assertIn(str(self.root/'Cargo.toml'),verification_paths(self.contract,self.state))

    def test_removing_dependency_repairs_constraint_and_preserves_json_check(self):
        self.assertIsNone(self.issue('[package]\nname="ranges"\nversion="0.1.0"\n[dependencies]\n'))
        (self.root/'report.json').unlink()
        self.assertIn('Save the requested JSON',inspect_deliverables(self.contract,self.state)[0])

    def test_target_and_test_dependencies_are_checked(self):
        issue=self.issue('[package]\nname="ranges"\nversion="0.1.0"\n[target."cfg(unix)".dev-dependencies]\nhelper="1.0"\n')
        self.assertIsNotNone(issue);self.assertIn('helper',issue)

    def test_unreadable_manifest_does_not_establish_compliance(self):
        self.assertIsNotNone(self.issue('this is not TOML'))

    def test_dependencies_remain_allowed_when_user_allows_them(self):
        self.state['goal']='Create a Rust Cargo application; dependencies are allowed. Write report.json.'
        self.contract=contract_for(self.state['goal'])
        self.assertIsNone(self.issue('[dependencies]\nserde_json="1.0"\n'))

    def test_python_goal_does_not_inspect_unrelated_cargo_manifest(self):
        self.state['goal']='Write a standard-library-only Python script and report.json.'
        self.contract=contract_for(self.state['goal'])
        self.assertIsNone(self.issue('[dependencies]\nserde_json="1.0"\n'))


    def test_existing_dependencies_allowed_when_only_new_ones_forbidden(self):
        self.state['goal']='Fix a Rust application. Do not add external dependencies. Write report.json.'
        self.contract=contract_for(self.state['goal'])
        self.assertIsNone(self.issue('[dependencies]\nserde_json="1.0"\n'))


if __name__=='__main__':unittest.main()
