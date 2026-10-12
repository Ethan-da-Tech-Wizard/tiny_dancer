# SPDX-License-Identifier: Apache-2.0
import json
import shlex
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

from openai_harmony import Message,Role
from app.agent import AgentRun
from app.tools import ROOT,ComputerTools
from app.verification import test_summary,test_command
from tests.test_agent import ScriptedEngine,call


class TestEvidenceTests(unittest.TestCase):
    def test_summary_uses_real_passes_and_ignores_skipped_or_failed_suites(self):
        for output,count,passed in (
            ('Ran 4 tests in 0.1s\n\nOK\n',4,True),
            ('Ran 0 tests in 0.1s\n\nOK\n',0,False),
            ('Ran 4 tests in 0.1s\n\nOK (skipped=4)\n',0,False),
            ('Ran 1 test in 0.1s\n\nFAILED (failures=1)\n',1,False),
            ('=== 3 passed in 0.2s ===\n',3,True),
            ('=== 2 passed, 1 failed in 0.2s ===\n',2,False),
            ('test result: ok. 4 passed; 0 failed;\ntest result: ok. 0 passed; 0 failed;\n',4,True),
            ('Ran 0 tests in 0.1s\n\nOK\nRan 3 tests in 0.2s\n\nOK\n',3,True),
        ):
            with self.subTest(output=output):
                result=test_summary(output);self.assertEqual(result['count'],count);self.assertEqual(result['passed'],passed)
        self.assertIsNone(test_summary('Just source data, no test result.'))

    def test_log_readers_and_complex_shell_commands_are_not_test_runs(self):
        for cmd in ('python -m unittest discover -q',"bash -lc 'python -m unittest test_calc.py -q'",'cargo test','pytest -q'):
            self.assertTrue(test_command(cmd),cmd)
        for cmd in ('cat unittest.log','echo "Ran 4 tests"','python -m unittest || true','python -m unittest; echo success'):
            self.assertFalse(test_command(cmd),cmd)


class VerifiedFinalTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'workspace');self.folder=Path(self.temp.name)
        self.tools=ComputerTools();self.messages=[];self.events=[]

    async def asyncTearDown(self): await self.tools.close();self.temp.cleanup()

    def setup_actions(self):
        return [call('write_file',{'path':'result.py','content':'def answer():\n    return 42\n'}),
                call('write_file',{'path':'test_result.py','content':'import unittest\nfrom result import answer\nclass Behavior(unittest.TestCase):\n    def test_answer(self):\n        self.assertEqual(answer(),42)\n'}),
                call('shell',{'command':shlex.quote(sys.executable)+' -m unittest discover -q'})]

    def final(self): return Message.from_role_and_content(Role.ASSISTANT,'Created result.py and verified answer() returns 42 with the real test suite.').with_channel('final')

    def runner(self,actions):
        request=SimpleNamespace(prompt='Create result.py with answer() returning 42 and test it',mode='agent',max_tokens=512,run_until_done=True)
        return AgentRun(ScriptedEngine(actions),self.tools,str(self.folder),request,lambda:self.messages,
            lambda m,role=None:self.messages.append(m.to_dict()),lambda k,d:self.events.append((k,d)),lambda *a:None,threading.Event())

    async def test_native_final_completes_after_actual_tests_without_finish_tool(self):
        run=self.runner(self.setup_actions()+[call('read_file',{'path':'result.py'}),self.final()])
        self.assertEqual(await run.run(),'complete')
        self.assertTrue(run.state['verified']);self.assertEqual(run.state['completion_path'],'tested_native_final')
        self.assertEqual(run.state['auto_verification']['test_count'],1)
        self.assertFalse(any(k=='tool_start' and d['name']=='finish_task' for k,d in self.events))
        self.assertIn('returns 42',self.messages[-1]['content'][0]['text'])

    async def test_file_changes_after_tests_invalidate_native_final(self):
        run=self.runner(self.setup_actions()+[self.final(),self.final()]);original=run.engine.generate
        def generate(*args,**kwargs):
            result=original(*args,**kwargs)
            if any(m.channel=='final' for m in result[0]): (self.folder/'result.py').write_text('def answer():\n    return 0\n')
            return result
        run.engine.generate=generate
        self.assertEqual(await run.run(),'paused');self.assertFalse(run.state['verified'])
        self.assertIn('changed after tests',run.state['next_action'])
        self.assertFalse(any(k=='delta' for k,d in self.events))
        self.assertEqual(sum(k=='completion_draft' for k,d in self.events),2)

    async def test_reading_test_output_never_counts_as_running_tests(self):
        run=self.runner(self.setup_actions()[:2]+[
            call('write_file',{'path':'log.txt','content':'Ran 4 tests in 0.1s\n\nOK\n'}),
            call('shell',{'command':'cat log.txt'}),self.final(),self.final()])
        self.assertEqual(await run.run(),'paused');self.assertFalse(run.state['verified'])
        self.assertNotIn('auto_verification',run.state)

    async def test_successful_app_run_keeps_checks_when_all_tracked_files_are_unchanged(self):
        actions=self.setup_actions()
        actions.insert(2,call('write_file',{'path':'report.json','content':json.dumps({'answer':42})+'\n'}))
        program="import json; from pathlib import Path; from result import answer; Path('report.json').write_text(json.dumps({'answer':answer()})+'\\n')"
        run=self.runner(actions+[call('shell',{'command':shlex.quote(sys.executable)+' -c '+shlex.quote(program)}),
                                 call('read_file',{'path':'report.json'}),self.final(),self.final()])
        self.assertEqual(await run.run(),'complete')
        self.assertTrue(run.state['verified'])
        self.assertEqual(run.state['auto_verification']['test_count'],1)

    async def test_successful_shell_source_mutation_invalidates_earlier_checks(self):
        program="from pathlib import Path; Path('result.py').write_text('def answer():\\n    return 0\\n')"
        run=self.runner(self.setup_actions()+[call('shell',{'command':shlex.quote(sys.executable)+' -c '+shlex.quote(program)}),self.final(),self.final()])
        self.assertEqual(await run.run(),'paused')
        self.assertFalse(run.state['verified']);self.assertNotIn('auto_verification',run.state)

    async def test_failed_shell_action_does_not_restore_earlier_checks(self):
        run=self.runner(self.setup_actions()+[call('shell',{'command':'exit 3'}),self.final(),self.final()])
        self.assertEqual(await run.run(),'paused')
        self.assertFalse(run.state['verified']);self.assertNotIn('auto_verification',run.state)

    async def test_failing_later_suite_does_not_restore_earlier_checks(self):
        command=shlex.quote(sys.executable)+' -m unittest test_result.Behavior.test_absent -q'
        run=self.runner(self.setup_actions()+[call('shell',{'command':command}),self.final(),self.final()])
        self.assertEqual(await run.run(),'paused')
        self.assertFalse(run.state['verified']);self.assertNotIn('auto_verification',run.state)

    async def test_pending_plan_steps_prevent_completion_after_passing_tests(self):
        plan=call('task_progress',{'steps':[{'title':'Create and test program','done':False}]})
        run=self.runner([plan]+self.setup_actions()+[self.final(),self.final()])
        self.assertEqual(await run.run(),'paused');self.assertIn('Pending plan',run.state['next_action'])

