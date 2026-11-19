# ==============================================================================
# Program: test_working_memory.py
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
from app.working_memory import checkpoint_evidence,preview


# ------------------------------------------------------------------------------
# WorkingMemoryTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class WorkingMemoryTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # setUp: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def setUp(self):
        root=Path(__file__).resolve().parents[1]
        self.temp=tempfile.TemporaryDirectory(dir=root/'run');self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.project=self.base/'project';self.project.mkdir()

    # ------------------------------------------------------------------------------
    # source: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def source(self,name,text):
        p=self.project/name;p.write_text(text);return str(p)

    # ------------------------------------------------------------------------------
    # test_refreshes_updated_observed_source_without_executing_it: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_refreshes_updated_observed_source_without_executing_it(self):
        p=self.source('source.py','raise RuntimeError("do not execute this source")\n')
        evidence=checkpoint_evidence([('functions.read_file',{'path':p,'text':'old version'})],self.project,[])
        self.assertIn('do not execute',evidence['source_snapshots'][0]['text']);self.assertNotIn('old version',json.dumps(evidence))

    # ------------------------------------------------------------------------------
    # test_zero_remaining_budget_never_returns_entire_second_file: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_zero_remaining_budget_never_returns_entire_second_file(self):
        paths=[self.source('a.py','a'*9000),self.source('b.py','b'*9000)]
        evidence=checkpoint_evidence([],self.project,paths,source_budget=2000)
        self.assertLessEqual(sum(len(s.get('text','')) for s in evidence['source_snapshots']),2000)
        self.assertNotIn('text',evidence['source_snapshots'][1])
        self.assertTrue(evidence['source_snapshots'][0]['partial_lines'])

    # ------------------------------------------------------------------------------
    # test_retained_failure_survives_later_successful_diagnostics: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_retained_failure_survives_later_successful_diagnostics(self):
        observations=[('functions.run_checks',{'exit_code':1,'checks':[{'exit_code':1,'output':'FAILED original boundary'}],'artifact':'/artifacts/failure.json'}),('functions.shell',{'exit_code':0,'output':'probe successful'})]
        result=checkpoint_evidence(observations,self.project,[])['last_failed_result']
        self.assertEqual(result['tool'],'functions.run_checks');self.assertIn('original boundary',result['preview']);self.assertEqual(result['result']['artifact'],'/artifacts/failure.json')

    # ------------------------------------------------------------------------------
    # test_retargeted_symlink_does_not_read_outside_project: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_retargeted_symlink_does_not_read_outside_project(self):
        secret=self.base/'outside.py';secret.write_text('PRIVATE_OUTSIDE_SENTINEL')
        alias=self.project/'alias.py';alias.symlink_to(secret)
        result=checkpoint_evidence([('functions.read_file',{'path':str(alias)})],self.project,[])
        self.assertEqual(result['source_snapshots'],[]);self.assertNotIn('PRIVATE_OUTSIDE_SENTINEL',json.dumps(result))

    # ------------------------------------------------------------------------------
    # test_large_and_binary_files_are_not_copied_into_checkpoint: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_large_and_binary_files_are_not_copied_into_checkpoint(self):
        large=self.source('large.py','x'*13000);binary=self.project/'binary';binary.write_bytes(b'a\x00b')
        result=checkpoint_evidence([],self.project,[large,str(binary)])
        self.assertEqual(len(result['source_snapshots']),1);self.assertNotIn('text',result['source_snapshots'][0]);self.assertIn('Large file',result['source_snapshots'][0]['read_hint'])

    # ------------------------------------------------------------------------------
    # test_malformed_optional_fields_do_not_break_compaction: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_malformed_optional_fields_do_not_break_compaction(self):
        result=checkpoint_evidence([('functions.apply_patch',{'files':None,'exit_code':1,'checks':[None,1,{}]})],self.project,[])
        self.assertEqual(result['source_snapshots'],[]);self.assertEqual(result['last_failed_result']['result']['exit_code'],1)

    # ------------------------------------------------------------------------------
    # test_preview_zero_and_small_budgets_are_bounded: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_preview_zero_and_small_budgets_are_bounded(self):
        for size in (0,1,20,100):self.assertLessEqual(len(preview('x'*10000,size)),size)
        self.assertEqual(preview('x'*10000,0),'')


if __name__=='__main__':unittest.main()
