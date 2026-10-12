# SPDX-License-Identifier: Apache-2.0
"""Actual execution verifies batching, failed checks, snapshots and cancellation."""
import json
import os
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest

from openai_harmony import Message, Role
from app.agent import AgentRun
from app.engine import Cancelled
from app.tools import ComputerTools, ROOT
from tests.test_agent import ScriptedEngine, call

COMMAND='python3 -m unittest -q test_program'
FINAL=Message.from_role_and_content(Role.ASSISTANT,'Implemented and tested the Python addition function.').with_channel('final')


class PostEditCheckTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'workspace')
        self.folder=Path(self.temp.name)
        (self.folder/'program.py').write_text('def add(a,b):\n    return a-b\n')
        (self.folder/'test_program.py').write_text('import unittest\nfrom program import add\nclass Tests(unittest.TestCase):\n def test_positive(self):self.assertEqual(add(2,3),5)\n def test_signed(self):self.assertEqual(add(-2,3),1)\n')
        self.tools=ComputerTools();self.messages=[];self.events=[]

    async def asyncTearDown(self):
        await self.tools.close();self.temp.cleanup()

    def runner(self,actions=(),checkpoint=None,flag=None):
        def save(message,role=None):self.messages.append(message.to_dict())
        return AgentRun(ScriptedEngine(actions),self.tools,str(self.folder),
            SimpleNamespace(prompt='Implement a Python addition function and run its tests.',mode='agent',max_tokens=1024,run_until_done=True),
            lambda:self.messages,save,lambda kind,data:self.events.append((kind,data)),lambda state:None,flag or threading.Event(),checkpoint)

    async def prepare(self,run):
        run.record_evidence('inspect_project',await run.execute('inspect_project',{}))
        result=await run.execute('run_checks',{'commands':[COMMAND]})
        self.assertEqual(result['exit_code'],1)
        self.assertFalse(run.state['verified'])

    def automatic_results(self):
        return [json.loads(data['result']) for kind,data in self.events if kind=='tool_result' and data.get('origin')=='automatic_post_edit']

    async def test_real_failed_suite_is_rerun_after_repair_then_native_final(self):
        run=self.runner([call('inspect_project',{}),call('run_checks',{'commands':[COMMAND]}),
                         call('write_file',{'path':'program.py','content':'def add(a,b):\n    return a + b\n'}),FINAL])
        self.assertEqual(await run.run(),'complete')
        results=self.automatic_results()
        self.assertEqual(len(results),1)
        self.assertEqual(results[0]['checks'][0]['command'],COMMAND)
        self.assertEqual(results[0]['test_count'],2)
        self.assertTrue(run.state['verified'])
        self.assertEqual(run.state['turns'],4)
        self.assertTrue(any(Message.from_dict(message).author.role==Role.TOOL and 'automatic_post_edit' in str(message) for message in self.messages))

    async def test_multiple_edits_in_one_native_batch_trigger_one_suite(self):
        run=self.runner([([call('write_file',{'path':'program.py','content':'def add(a,b):\n    return a + b\n'}),
                           call('write_file',{'path':'notes.txt','content':'addition implemented'})],'RETURN'),FINAL])
        await self.prepare(run)
        self.assertEqual(await run.run(),'complete')
        self.assertEqual(len(self.automatic_results()),1)

    async def test_unchanged_reads_do_not_repeat_tests(self):
        run=self.runner();await self.prepare(run)
        await run.execute('read_file',{'path':'program.py'})
        await run.check_after_edit();await run.check_after_edit()
        self.assertEqual(self.automatic_results(),[])

    async def test_failed_automatic_suite_does_not_accept_completion(self):
        run=self.runner([call('write_file',{'path':'program.py','content':'def add(a,b):\n    return 0\n'}),FINAL,FINAL])
        await self.prepare(run)
        self.assertEqual(await run.run(),'paused')
        self.assertFalse(run.state['verified'])
        self.assertEqual(len(self.automatic_results()),1)
        self.assertEqual(self.automatic_results()[0]['exit_code'],1)

    async def test_availability_empty_and_unsafe_commands_are_not_replayed(self):
        run=self.runner();run.record_evidence('inspect_project',await run.execute('inspect_project',{}))
        for commands in (['python3 -m unittest discover -s empty'],['python3 -m unittest -q test_program; true']):
            (self.folder/'empty').mkdir(exist_ok=True)
            await run.execute('run_checks',{'commands':commands})
            self.assertNotIn('selected_project_tests',run.state)
        await run.execute('write_file',{'path':'program.py','content':'def add(a,b):return a+b\n'})
        await run.check_after_edit()
        self.assertEqual(self.automatic_results(),[])

    async def test_stop_prevents_automatic_command_execution(self):
        run=self.runner();await self.prepare(run)
        await run.execute('write_file',{'path':'program.py','content':'def add(a,b):return a+b\n'})
        run.flag.set()
        with self.assertRaises(Cancelled):await run.check_after_edit()
        self.assertEqual(self.automatic_results(),[])

    async def test_resume_preserves_selected_tests_and_checks_new_edit_only(self):
        run=self.runner();await self.prepare(run)
        state=json.loads(json.dumps(run.state))
        resumed=self.runner(checkpoint=state)
        await resumed.check_after_edit();self.assertEqual(self.automatic_results(),[])
        await resumed.execute('write_file',{'path':'program.py','content':'def add(a,b):return a+b\n'})
        await resumed.check_after_edit();await resumed.check_after_edit()
        self.assertTrue(resumed.state['verified']);self.assertEqual(len(self.automatic_results()),1)

    async def test_tests_that_modify_source_cannot_verify_that_new_source(self):
        run=self.runner();await self.prepare(run)
        (self.folder/'test_program.py').write_text('import unittest\nfrom pathlib import Path\nclass Tests(unittest.TestCase):\n def test_changes_source(self):\n  Path("program.py").write_text("def add(a,b):return 42\\n")\n  self.assertTrue(True)\n')
        await run.check_after_edit()
        self.assertEqual(self.automatic_results()[0]['exit_code'],0)
        self.assertFalse(run.state['verified'])
        self.assertNotIn('auto_verification',run.state)

    async def test_same_size_same_timestamp_edit_cannot_pass_using_stale_bytecode(self):
        source=self.folder/'program.py'
        source.write_text('def add(a,b):\n    return a+b\n')
        compiled=await self.tools.execute('shell',{'command':'python3 -c "import py_compile; py_compile.compile(\'program.py\', doraise=True)"'},str(self.folder))
        self.assertEqual(compiled['exit_code'],0)
        cached=list((self.folder/'__pycache__').glob('program.*.pyc'))
        self.assertEqual(len(cached),1)
        cache_bytes=cached[0].read_bytes();stamp=source.stat()
        source.write_text('def add(a,b):\n    return a-b\n')
        os.utime(source,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
        result=await self.tools.execute('run_checks',{'commands':[COMMAND]},str(self.folder))
        self.assertEqual(result['exit_code'],1)
        self.assertIn('FAILED',result['checks'][0]['output'])
        self.assertEqual(result['checks'][0]['python_bytecode'],'fresh_source')
        self.assertEqual(cached[0].read_bytes(),cache_bytes)
