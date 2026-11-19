# ==============================================================================
# Program: test_test_authority.py
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
import unittest
import threading
from types import SimpleNamespace
from pathlib import Path
from app.test_authority import failure_test_origins,snapshot
from app.agent import AgentRun
from app.tools import ComputerTools
from tests.test_agent import ScriptedEngine


# ------------------------------------------------------------------------------
# TestAuthorityTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class TestAuthorityTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # setUp: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'run')
        self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.seed=self.root/'test_acceptance.py'
        self.seed.write_text('def test_seed():\n    assert 1 == 1\n')
        self.baseline=snapshot(self.root)

    # ------------------------------------------------------------------------------
    # result: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def result(self, path):
        return {'exit_code':1,'output':'FAIL: test_expected (test_extra.Extra.test_expected)\nTraceback (most recent call last):\n  File "'+str(path)+'", line 3, in test_expected\nAssertionError: actual != expected\n'}

    # ------------------------------------------------------------------------------
    # test_new_test_is_an_observation_not_authority: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_new_test_is_an_observation_not_authority(self):
        new=self.root/'test_extra.py';new.write_text('def test_expected():\n    assert 1 == 2\n')
        report=failure_test_origins(self.result(new),self.baseline,snapshot(self.root),self.root)
        self.assertEqual(report['failures'][0]['origin'],'added_since_task_start')
        self.assertEqual(report['failures'][0]['path'],'test_extra.py')

    # ------------------------------------------------------------------------------
    # test_existing_unchanged_test_remains_distinct: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_existing_unchanged_test_remains_distinct(self):
        report=failure_test_origins(self.result(self.seed),self.baseline,snapshot(self.root),self.root)
        self.assertEqual(report['failures'][0]['origin'],'unchanged_since_task_start')

    # ------------------------------------------------------------------------------
    # test_changed_existing_assertion_is_identified: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_changed_existing_assertion_is_identified(self):
        self.seed.write_text('def test_seed():\n    assert 2 == 1\n')
        report=failure_test_origins(self.result(self.seed),self.baseline,snapshot(self.root),self.root)
        self.assertEqual(report['failures'][0]['origin'],'changed_since_task_start')

    # ------------------------------------------------------------------------------
    # test_changed_module_constant_is_identified: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_changed_module_constant_is_identified(self):
        self.seed.write_text('EXPECTED=1\ndef test_seed():\n    assert 1 == EXPECTED\n')
        before=snapshot(self.root)
        self.seed.write_text('EXPECTED=2\ndef test_seed():\n    assert 1 == EXPECTED\n')
        report=failure_test_origins(self.result(self.seed),before,snapshot(self.root),self.root)
        self.assertEqual(report['failures'][0]['origin'],'changed_since_task_start')

    # ------------------------------------------------------------------------------
    # test_incomplete_baseline_never_claims_new_test: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_incomplete_baseline_never_claims_new_test(self):
        report=failure_test_origins(self.result(self.seed),{'complete':False,'sources':{}},snapshot(self.root),self.root)
        self.assertEqual(report['failures'][0]['origin'],'unknown')

    # ------------------------------------------------------------------------------
    # test_success_and_unrelated_stack_do_not_create_a_warning: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_success_and_unrelated_stack_do_not_create_a_warning(self):
        self.assertIsNone(failure_test_origins({'exit_code':0,'output':'all pass'},self.baseline,snapshot(self.root),self.root))
        self.assertIsNone(failure_test_origins(self.result('/usr/lib/external.py'),self.baseline,snapshot(self.root),self.root))

    # ------------------------------------------------------------------------------
    # test_snapshot_never_executes_test_source: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_snapshot_never_executes_test_source(self):
        target=self.root/'test_extra.py';target.write_text('raise RuntimeError("never import")\ndef test_value():\n    assert False\n')
        report=failure_test_origins(self.result(target),self.baseline,snapshot(self.root),self.root)
        self.assertEqual(report['failures'][0]['origin'],'added_since_task_start')


# ------------------------------------------------------------------------------
# TestAuthorityIntegrationTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class TestAuthorityIntegrationTests(unittest.IsolatedAsyncioTestCase):
    # ------------------------------------------------------------------------------
    # test_real_failure_marks_new_test_and_passing_recheck_clears_it: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_real_failure_marks_new_test_and_passing_recheck_clears_it(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'run') as temporary:
            root=Path(temporary)
            (root/'program.py').write_text('def add(a,b):\n    return a+b\n')
            (root/'test_seed.py').write_text('import unittest\nfrom program import add\nclass Tests(unittest.TestCase):\n def test_sum(self):self.assertEqual(add(1,2),3)\n')
            computer=ComputerTools();messages=[]
            try:
                run=AgentRun(ScriptedEngine([]),computer,str(root),
                    SimpleNamespace(prompt='Fix this Python project and run its tests.',mode='agent',max_tokens=None,run_until_done=True),
                    lambda:messages,lambda m,role=None:messages.append(m.to_dict()),lambda k,v:None,lambda s:None,threading.Event())
                await run.execute('inspect_project',{})
                source=(root/'program.py').read_bytes()
                test='import unittest\nfrom program import add\nclass Tests(unittest.TestCase):\n def test_extra(self):self.assertEqual(add(4,5),8)\n'
                await run.execute('write_file',{'path':'test_extra.py','content':test})
                result=await run.execute('run_checks',{'commands':['python3 -m unittest discover -q']})
                self.assertNotEqual(result['exit_code'],0)
                self.assertEqual(result['failure_test_origins']['failures'][0]['origin'],'added_since_task_start')
                self.assertFalse(run.state['verified']);self.assertEqual((root/'program.py').read_bytes(),source)
                run.compact_context('test checkpoint')
                self.assertIn('failure_test_origins',str(run.compacted_history))
                await run.execute('write_file',{'path':'test_extra.py','content':test.replace('),8)', '),9)')})
                passed=await run.execute('run_checks',{'commands':['python3 -m unittest discover -q']})
                self.assertEqual(passed['exit_code'],0)
                self.assertNotIn('failure_test_origins',run.state)
            finally:await computer.close()
