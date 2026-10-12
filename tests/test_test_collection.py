# SPDX-License-Identifier: Apache-2.0
"""Real collector mismatch must not produce a verified final."""
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from openai_harmony import Message,Role
from app.agent import AgentRun
from app.tools import ComputerTools,ROOT
from tests.test_agent import ScriptedEngine,call


class TestCollectionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'workspace');self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name);self.tools=ComputerTools()
        (self.folder/'program.py').write_text('def value():return 1\n')
        (self.folder/'test_seed.py').write_text('import unittest\nfrom program import value\nclass Seed(unittest.TestCase):\n def test_seed(self):self.assertEqual(value(),1)\n')
        self.messages=[];self.events=[]

    async def asyncTearDown(self):await self.tools.close()

    def runner(self,command,newtest):
        goal='Create a Python program.py and add relevant tests. Run the project tests before finishing.'
        final=Message.from_role_and_content(Role.ASSISTANT,'Finished and tested.').with_channel('final')
        actions=[call('write_file',{'path':'test_added.py','content':newtest}),
                 call('run_checks',{'commands':[command],'timeout':30})]+[final]*4
        self.messages=[Message.from_role_and_content(Role.USER,goal).to_dict()]
        def save(message,role=None):self.messages.append(message.to_dict())
        return AgentRun(ScriptedEngine(actions),self.tools,str(self.folder),
                        SimpleNamespace(prompt=goal,mode='agent',max_tokens=None,run_until_done=True),
                        lambda:self.messages,save,lambda k,d:self.events.append((k,d)),lambda s:None,threading.Event())

    async def test_passing_unittest_seeds_cannot_verify_an_uncollected_failing_function(self):
        run=self.runner('python -m unittest discover -s . -p "test_*.py"','def test_added():\n assert False, "new test never ran"\n')
        self.assertEqual(await run.run(),'paused')
        self.assertFalse(run.state['verified'])
        results=[json.loads(d['result']) for k,d in self.events if k=='tool_result' and d['name']=='run_checks']
        self.assertEqual(results[-1]['exit_code'],0)
        self.assertFalse(results[-1]['test_verification']['verified'])
        self.assertIn('test_added.py',results[-1]['test_verification']['next_action'])

    async def test_real_full_pytest_can_verify_new_plain_function_tests(self):
        run=self.runner(str(ROOT/'.venv/bin/python')+' -m pytest -q','from program import value\ndef test_added():\n assert value()==1\n')
        self.assertEqual(await run.run(),'complete');self.assertTrue(run.state['verified'])

    async def test_real_pytest_failure_keeps_the_task_open(self):
        run=self.runner(str(ROOT/'.venv/bin/python')+' -m pytest -q','def test_added():\n assert False\n')
        self.assertEqual(await run.run(),'paused');self.assertFalse(run.state['verified'])

    async def test_pytest_of_only_the_old_seed_cannot_witness_new_tests(self):
        run=self.runner(str(ROOT/'.venv/bin/python')+' -m pytest -q test_seed.py','def test_added():\n assert False\n')
        self.assertEqual(await run.run(),'paused');self.assertFalse(run.state['verified'])

    async def test_old_plain_test_receipt_is_invalid_after_product_change(self):
        run=self.runner('', '')
        await run.execute('read_file',{'path':'program.py'})
        await run.execute('write_file',{'path':'test_added.py','content':'import program\ndef test_added():\n assert not hasattr(program,"untested")\n'})
        result=await run.execute('run_checks',{'commands':[str(ROOT/'.venv/bin/python')+' -m pytest -q'],'timeout':30})
        self.assertTrue(result['test_verification']['verified'])
        (self.folder/'program.py').write_text('def value():return 1\nuntested=True\n')
        result=await run.execute('run_checks',{'commands':['python -m unittest -q test_seed'],'timeout':30})
        self.assertEqual(result['exit_code'],0);self.assertFalse(result['test_verification']['verified'])

    async def test_finish_task_can_run_the_actual_compatible_checks(self):
        run=self.runner('', '')
        await run.execute('write_file',{'path':'test_added.py','content':'from program import value\ndef test_added():\n assert value()==1\n'})
        result=await run.execute('finish_task',{'summary':'Implemented and tested','checks':[str(ROOT/'.venv/bin/python')+' -m pytest -q']})
        self.assertTrue(result['verified'])


if __name__=='__main__':unittest.main()
