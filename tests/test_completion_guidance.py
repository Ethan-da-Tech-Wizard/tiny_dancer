# Program: tiny_dancer - tests/test_completion_guidance.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Tests for completion guidance (exercises app.agent, app.tools).
# SPDX-License-Identifier: Apache-2.0
"""Tests for completion guidance (exercises app.agent, app.tools)."""
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest

from app.agent import AgentRun
from app.tools import ComputerTools


# -------- completion guidance tests --------
class CompletionGuidanceTests(unittest.IsolatedAsyncioTestCase):
    """Test group for completion guidance."""
    async def asyncSetUp(self):
        """Test helper: asyncSetUp."""
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'workspace')
        self.cwd=Path(self.temp.name);self.tools=ComputerTools()
        request=SimpleNamespace(prompt='Build a Python program, add tests and save report.json.',mode='agent',max_tokens=None,run_until_done=True)
        self.run=AgentRun(SimpleNamespace(config={}),self.tools,str(self.cwd),request,lambda:[],lambda *a:None,lambda *a:None,lambda *a:None,threading.Event())
        await self.run.execute('write_file',{'path':'calc.py','content':'def double(n): return n*2\n'})
        await self.run.execute('write_file',{'path':'test_calc.py','content':'import unittest\nfrom calc import double\nclass Tests(unittest.TestCase):\n def test_double(self): self.assertEqual(double(3),6)\n'})

    async def asyncTearDown(self):
        """Test helper: asyncTearDown."""
        await self.tools.close();self.temp.cleanup()

    async def checks(self):
        """Test helper: checks."""
        return await self.run.execute('run_checks',{'commands':['python -m unittest -q test_calc'],'timeout':15})

    async def test_verified_checks_expose_goal_review_and_stop_direction(self):
        """Checks that verified checks expose goal review and stop direction."""
        await self.run.execute('write_file',{'path':'report.json','content':'[]\n'})
        result=await self.checks();guide=result['test_verification']
        self.assertTrue(guide['verified']);self.assertEqual(guide['test_count'],1)
        self.assertEqual(guide['pending_steps'],[])
        self.assertIn('original goal',guide['next_action'])
        self.assertIn('concise final',guide['next_action'])
        self.assertTrue(self.run.state['verified'])

    async def test_pending_plan_steps_are_named_instead_of_final_direction(self):
        """Checks that pending plan steps are named instead of final direction."""
        await self.run.execute('write_file',{'path':'report.json','content':'[]\n'})
        self.run.state['steps']=[{'title':'Review error handling','done':False},{'title':'Save output','done':True}]
        result=await self.checks();guide=result['test_verification']
        self.assertEqual(guide['pending_steps'],['Review error handling'])
        self.assertIn('pending plan',guide['next_action'])
        self.assertNotIn('concise final',guide['next_action'])

    async def test_missing_requested_output_never_gets_finish_guidance(self):
        """Checks that missing requested output never gets finish guidance."""
        result=await self.checks()
        self.assertEqual(result['exit_code'],0);self.assertFalse(result['test_verification']['verified'])
        self.assertIn('JSON',result['test_verification']['next_action'])
        self.assertFalse(self.run.state['verified'])

    async def test_failed_real_check_never_gets_finish_guidance(self):
        """Checks that failed real check never gets finish guidance."""
        await self.run.execute('write_file',{'path':'report.json','content':'[]\n'})
        await self.run.execute('write_file',{'path':'calc.py','content':'def double(n): return n+1\n'})
        result=await self.checks()
        self.assertNotEqual(result['exit_code'],0);self.assertNotIn('test_verification',result)
        self.assertFalse(self.run.state['verified'])

    async def test_checked_work_requires_a_pending_requirement_before_more_file_edits(self):
        """Checks that checked work requires a pending requirement before more file edits."""
        await self.run.execute('write_file',{'path':'report.json','content':'[]\n'})
        await self.checks();before=(self.cwd/'calc.py').read_text()
        with self.assertRaisesRegex(ValueError,'task_progress'):
            await self.run.execute('write_file',{'path':'calc.py','content':'# optional polish\ndef double(n):return n*2\n'})
        self.assertEqual((self.cwd/'calc.py').read_text(),before)
        self.assertTrue(self.run.state['verified'])

    async def test_pending_goal_step_keeps_legitimate_edits_available(self):
        """Checks that pending goal step keeps legitimate edits available."""
        await self.run.execute('write_file',{'path':'report.json','content':'[]\n'})
        await self.checks()
        await self.run.execute('task_progress',{'steps':[{'title':'Check remaining user-requested error handling','done':False}]})
        await self.run.execute('write_file',{'path':'calc.py','content':'def double(n):return n*2\n# required handling reviewed\n'})
        self.assertFalse(self.run.state['verified'])

    async def test_external_change_invalidates_proof_and_does_not_block_repair(self):
        """Checks that external change invalidates proof and does not block repair."""
        await self.run.execute('write_file',{'path':'report.json','content':'[]\n'})
        await self.checks();(self.cwd/'calc.py').write_text('def double(n):return n+2\n')
        await self.run.execute('write_file',{'path':'calc.py','content':'def double(n):return n*2\n'})
        self.assertFalse(self.run.state['verified'])
