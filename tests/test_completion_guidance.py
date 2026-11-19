# ==============================================================================
# Program: test_completion_guidance.py
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
import threading
from types import SimpleNamespace
import unittest

from app.agent import AgentRun
from app.tools import ComputerTools


# ------------------------------------------------------------------------------
# CompletionGuidanceTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class CompletionGuidanceTests(unittest.IsolatedAsyncioTestCase):
    # ------------------------------------------------------------------------------
    # asyncSetUp: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'workspace')
        self.cwd=Path(self.temp.name);self.tools=ComputerTools()
        request=SimpleNamespace(prompt='Build a Python program, add tests and save report.json.',mode='agent',max_tokens=None,run_until_done=True)
        self.run=AgentRun(SimpleNamespace(config={}),self.tools,str(self.cwd),request,lambda:[],lambda *a:None,lambda *a:None,lambda *a:None,threading.Event())
        await self.run.execute('write_file',{'path':'calc.py','content':'def double(n): return n*2\n'})
        await self.run.execute('write_file',{'path':'test_calc.py','content':'import unittest\nfrom calc import double\nclass Tests(unittest.TestCase):\n def test_double(self): self.assertEqual(double(3),6)\n'})

    # ------------------------------------------------------------------------------
    # asyncTearDown: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def asyncTearDown(self):
        await self.tools.close();self.temp.cleanup()

    # ------------------------------------------------------------------------------
    # checks: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def checks(self):
        return await self.run.execute('run_checks',{'commands':['python -m unittest -q test_calc'],'timeout':15})

    # ------------------------------------------------------------------------------
    # test_verified_checks_expose_goal_review_and_stop_direction: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_verified_checks_expose_goal_review_and_stop_direction(self):
        await self.run.execute('write_file',{'path':'report.json','content':'[]\n'})
        result=await self.checks();guide=result['test_verification']
        self.assertTrue(guide['verified']);self.assertEqual(guide['test_count'],1)
        self.assertEqual(guide['pending_steps'],[])
        self.assertIn('original goal',guide['next_action'])
        self.assertIn('concise final',guide['next_action'])
        self.assertTrue(self.run.state['verified'])

    # ------------------------------------------------------------------------------
    # test_pending_plan_steps_are_named_instead_of_final_direction: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_pending_plan_steps_are_named_instead_of_final_direction(self):
        await self.run.execute('write_file',{'path':'report.json','content':'[]\n'})
        self.run.state['steps']=[{'title':'Review error handling','done':False},{'title':'Save output','done':True}]
        result=await self.checks();guide=result['test_verification']
        self.assertEqual(guide['pending_steps'],['Review error handling'])
        self.assertIn('pending plan',guide['next_action'])
        self.assertNotIn('concise final',guide['next_action'])

    # ------------------------------------------------------------------------------
    # test_missing_requested_output_never_gets_finish_guidance: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_missing_requested_output_never_gets_finish_guidance(self):
        result=await self.checks()
        self.assertEqual(result['exit_code'],0);self.assertFalse(result['test_verification']['verified'])
        self.assertIn('JSON',result['test_verification']['next_action'])
        self.assertFalse(self.run.state['verified'])

    # ------------------------------------------------------------------------------
    # test_failed_real_check_never_gets_finish_guidance: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_failed_real_check_never_gets_finish_guidance(self):
        await self.run.execute('write_file',{'path':'report.json','content':'[]\n'})
        await self.run.execute('write_file',{'path':'calc.py','content':'def double(n): return n+1\n'})
        result=await self.checks()
        self.assertNotEqual(result['exit_code'],0);self.assertNotIn('test_verification',result)
        self.assertFalse(self.run.state['verified'])

    # ------------------------------------------------------------------------------
    # test_checked_work_requires_a_pending_requirement_before_more_file_edits: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_checked_work_requires_a_pending_requirement_before_more_file_edits(self):
        await self.run.execute('write_file',{'path':'report.json','content':'[]\n'})
        await self.checks();before=(self.cwd/'calc.py').read_text()
        with self.assertRaisesRegex(ValueError,'task_progress'):
            await self.run.execute('write_file',{'path':'calc.py','content':'# optional polish\ndef double(n):return n*2\n'})
        self.assertEqual((self.cwd/'calc.py').read_text(),before)
        self.assertTrue(self.run.state['verified'])

    # ------------------------------------------------------------------------------
    # test_pending_goal_step_keeps_legitimate_edits_available: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_pending_goal_step_keeps_legitimate_edits_available(self):
        await self.run.execute('write_file',{'path':'report.json','content':'[]\n'})
        await self.checks()
        await self.run.execute('task_progress',{'steps':[{'title':'Check remaining user-requested error handling','done':False}]})
        await self.run.execute('write_file',{'path':'calc.py','content':'def double(n):return n*2\n# required handling reviewed\n'})
        self.assertFalse(self.run.state['verified'])

    # ------------------------------------------------------------------------------
    # test_external_change_invalidates_proof_and_does_not_block_repair: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_external_change_invalidates_proof_and_does_not_block_repair(self):
        await self.run.execute('write_file',{'path':'report.json','content':'[]\n'})
        await self.checks();(self.cwd/'calc.py').write_text('def double(n):return n+2\n')
        await self.run.execute('write_file',{'path':'calc.py','content':'def double(n):return n*2\n'})
        self.assertFalse(self.run.state['verified'])
