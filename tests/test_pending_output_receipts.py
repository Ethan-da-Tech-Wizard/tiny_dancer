# Program: tiny_dancer - tests/test_pending_output_receipts.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Tests for pending output receipts (exercises app.agent, app.tools, app.verification).
# SPDX-License-Identifier: Apache-2.0
"""Tests for pending output receipts (exercises app.agent, app.tools, app.verification)."""
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest

from openai_harmony import Message,Role
from app.agent import AgentRun
from app.tools import ComputerTools,ROOT
from app.verification import source_hashes
from tests.test_agent import ScriptedEngine,call

FINAL=Message.from_role_and_content(Role.ASSISTANT,'Implemented and checked.').with_channel('final')


# -------- pending output receipts tests --------
class PendingOutputReceiptsTests(unittest.IsolatedAsyncioTestCase):
    """Test group for pending output receipts."""
    async def asyncSetUp(self):
        """Test helper: asyncSetUp."""
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'workspace')
        self.folder=Path(self.temp.name)
        (self.folder/'program.py').write_text('def add(a,b):return a-b\n')
        (self.folder/'test_program.py').write_text('import unittest\nfrom program import add\nclass Tests(unittest.TestCase):\n def test_sum(self):self.assertEqual(add(2,3),5)\n')
        self.tools=ComputerTools();self.messages=[];self.events=[]

    async def asyncTearDown(self):
        """Test helper: asyncTearDown."""
        await self.tools.close();self.temp.cleanup()

    def runner(self,actions=()):
        """Test helper: runner."""
        engine=ScriptedEngine(actions);engine.config={**engine.config,'coding_preflight':True}
        # Test helper: save.
        def save(message,role=None):self.messages.append(message.to_dict())
        return AgentRun(engine,self.tools,str(self.folder),
            SimpleNamespace(prompt='Repair program.py and run the Python tests. Write report.json in this folder.',mode='agent',max_tokens=1024,run_until_done=True),
            lambda:self.messages,save,lambda kind,data:self.events.append((kind,data)),lambda state:None,threading.Event())

    async def test_missing_named_output_keeps_real_failing_baseline_receipt(self):
        """Checks that missing named output keeps real failing baseline receipt."""
        run=self.runner();await run.initial_project_checks()
        receipt=run.state.get('selected_project_tests')
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt['files_sha256'][str(self.folder/'report.json')],None)
        self.assertFalse(run.state['verified'])
        self.assertFalse((self.folder/'report.json').exists())

    async def test_post_edit_tests_run_before_output_but_completion_waits(self):
        """Checks that post edit tests run before output but completion waits."""
        run=self.runner([call('write_file',{'path':'program.py','content':'def add(a,b):return a+b\n'}),
                         FINAL,call('write_file',{'path':'report.json','content':'{"checked":true}\n'}),FINAL])
        self.assertEqual(await run.run(),'complete')
        automatic=[json.loads(data['result']) for kind,data in self.events if kind=='tool_result' and data.get('origin')=='automatic_post_edit']
        self.assertEqual(len(automatic),2)
        self.assertTrue(all(result['exit_code']==0 and result['test_count']==1 for result in automatic))
        self.assertFalse(automatic[0]['test_verification']['verified'])
        self.assertIn('report.json',automatic[0]['test_verification']['next_action'])
        self.assertTrue(run.state['verified'])
        self.assertEqual(run.state['turns'],4)
        drafts=[data for kind,data in self.events if kind=='completion_draft']
        self.assertTrue(drafts)
        self.assertFalse(drafts[0]['accepted'])


# -------- receipt hash tests --------
class ReceiptHashTests(unittest.TestCase):
    """Test group for receipt hash."""
    def test_optional_output_marker_never_relaxes_default_verification(self):
        """Checks that optional output marker never relaxes default verification."""
        with tempfile.TemporaryDirectory(dir=ROOT/'workspace') as temp:
            folder=Path(temp);source=folder/'main.py';source.write_text('pass\n');out=folder/'report.json'
            self.assertIsNone(source_hashes([str(source),str(out)]))
            receipt=source_hashes([str(source),str(out)],optional_missing=[str(out)])
            self.assertIsNone(receipt[str(out)])
            self.assertEqual(len(receipt[str(source)]),64)
            self.assertIsNone(source_hashes([str(source),str(out)]))

    def test_deleted_source_is_not_an_optional_output(self):
        """Checks that deleted source is not an optional output."""
        with tempfile.TemporaryDirectory(dir=ROOT/'workspace') as temp:
            folder=Path(temp);source=folder/'missing.py';out=folder/'report.json'
            self.assertIsNone(source_hashes([str(source),str(out)],optional_missing=[str(out)]))

    def test_dangling_symlink_is_not_treated_as_missing_output(self):
        """Checks that dangling symlink is not treated as missing output."""
        with tempfile.TemporaryDirectory(dir=ROOT/'workspace') as temp:
            folder=Path(temp);out=folder/'report.json';out.symlink_to(folder/'missing-target')
            self.assertIsNone(source_hashes([str(out)],optional_missing=[str(out)]))
