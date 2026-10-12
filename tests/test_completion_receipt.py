# SPDX-License-Identifier: Apache-2.0
"""Passing tests must report actual remaining work, without relaxing completion."""
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from openai_harmony import Message, Role
from app.agent import AgentRun
from app.tools import ComputerTools, ROOT


class CompletionReceiptTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'workspace');self.cwd=Path(self.temp.name)
        (self.cwd/'product.py').write_text('def double(n):return n*2\n')
        (self.cwd/'test_product.py').write_text('import unittest\nfrom product import double\nclass Tests(unittest.TestCase):\n def test_existing(self):self.assertEqual(double(3),6)\n')
        self.tools=ComputerTools();self.messages=[]
        def save(m,*a):self.messages.append(m.to_dict())
        request=SimpleNamespace(prompt='Implement a Python double function. Add relevant tests and run them.',mode='agent',max_tokens=None,run_until_done=True)
        self.run=AgentRun(SimpleNamespace(config={}),self.tools,str(self.cwd),request,lambda:self.messages,save,lambda *a:None,lambda *a:None,threading.Event())
        await self.run.execute('inspect_project',{})

    async def asyncTearDown(self):await self.tools.close();self.temp.cleanup()

    async def check(self):return await self.run.execute('run_checks',{'commands':['python3 -m unittest -q test_product']})

    async def test_actual_pass_names_missing_tests_without_claiming_completion(self):
        result=await self.check()
        self.assertEqual(result['exit_code'],0)
        guide=result['test_verification']
        self.assertFalse(guide['verified'])
        self.assertIn('added',guide['next_action'])
        self.assertIn('tests',guide['next_action'])
        self.assertFalse(self.run.state['verified'])
        self.assertTrue(self.run.state['latest_project_checks']['passed'])

    async def test_checkpoint_keeps_newer_passing_evidence_and_remaining_requirement(self):
        result=await self.check()
        from openai_harmony import Author,TextContent
        self.messages.append(Message(author=Author.new(Role.TOOL,'functions.run_checks'),content=[TextContent(text=json.dumps(result))]).with_recipient('assistant').to_dict())
        self.run.compact_context('Context refreshed.')
        prompt=json.dumps(self.run.prompt_history())
        self.assertIn('latest_project_checks',prompt)
        self.assertIn('remaining_requirement',prompt)
        self.assertIn('added',prompt)
        self.assertFalse(self.run.state['verified'])

    async def test_added_real_tests_clear_requirement_and_allow_verified_completion(self):
        await self.check()
        await self.run.execute('write_file',{'path':'test_product.py','content':(self.cwd/'test_product.py').read_text()+' def test_signed(self):self.assertEqual(double(-3),-6)\n'})
        result=await self.check()
        self.assertTrue(result['test_verification']['verified'])
        self.assertTrue(self.run.state['verified'])
        self.assertIsNone(self.run.state['latest_project_checks']['remaining_requirement'])

    async def test_edit_after_passing_checks_is_explicitly_unverified_in_checkpoint(self):
        await self.check()
        await self.run.execute('write_file',{'path':'product.py','content':'def double(n):return n+2\n'})
        self.run.compact_context('Context refreshed.')
        prompt=json.dumps(self.run.prompt_history())
        self.assertIn('sources_unchanged',prompt)
        self.assertIn('false',prompt)
        self.assertFalse(self.run.state['verified'])

    async def test_updated_import_notes_survive_passing_checks_and_checkpoint(self):
        await self.run.execute('write_file',{'path':'product.py','content':'from decimal import getcontext\ngetcontext().prec=123\ndef double(n):return n*2\n'})
        result=await self.check()
        self.assertEqual(result['runtime_notes'][0]['precision_assignments'][0]['constant'],123)
        self.run.compact_context('Context refreshed.')
        prompt=json.dumps(self.run.prompt_history())
        self.assertIn('runtime_notes',prompt)
        self.assertIn('123',prompt)
        self.assertIn('not a proven defect',prompt)

    async def test_import_notes_parse_without_executing_source_and_respect_scope(self):
        from app.working_memory import runtime_source_evidence
        marker=self.cwd/'MUST_NOT_EXIST'
        path=self.cwd/'unsafe.py'
        path.write_text('from decimal import Decimal\nfrom pathlib import Path\nPath('+repr(str(marker))+').write_text("EXECUTED")\n')
        notes=runtime_source_evidence(str(self.cwd),[str(path)])
        self.assertEqual(notes[0]['library'],'decimal')
        self.assertFalse(marker.exists())
        with tempfile.TemporaryDirectory(dir=ROOT/'run') as outside:
            target=Path(outside)/'outside.py';target.write_text('from decimal import Decimal\n')
            alias=self.cwd/'alias.py';alias.symlink_to(target)
            self.assertEqual(runtime_source_evidence(str(self.cwd),[str(alias),str(target)]),[])


if __name__=='__main__':unittest.main()
