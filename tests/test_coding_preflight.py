# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

from openai_harmony import Message, Role
from app.agent import AgentRun
from app.coding_preflight import baseline_commands
from app.engine import Cancelled
from app.source_diagnostics import python_runtime_notes
from app.tools import ComputerTools, ROOT
from tests.test_agent import ScriptedEngine, call


FINAL=Message.from_role_and_content(Role.ASSISTANT,'Repaired and tested.').with_channel('final')


class PreflightSelectionTests(unittest.TestCase):
    def test_only_actual_available_safe_test_candidates_are_selected(self):
        inspection={'test_candidates':[None,{'command':'python -m pytest','available':False},
            {'command':'python -m unittest; touch outside','available':True},
            {'command':'cat old-test.log','available':True},
            {'command':'python -m unittest -q test_program','available':True},
            {'command':'python -m unittest -q test_program','available':True},
            {'command':'cargo test','available':True}]}
        self.assertEqual(baseline_commands(inspection),['python -m unittest -q test_program','cargo test --offline'])
        self.assertEqual(baseline_commands({}),[])

    def test_three_command_bound(self):
        candidates=[{'command':f'python -m unittest test_{i}','available':True} for i in range(8)]
        self.assertEqual(len(baseline_commands({'test_candidates':candidates})),3)

    def test_decimal_notes_are_static_and_import_specific(self):
        files=[{'path':'program.py','text':'from decimal import Decimal, getcontext as gc\nraise RuntimeError("Do not execute")\ngc().prec=123\n'},
               {'path':'unrelated.py','text':'message="from decimal import Decimal"\n'},
               {'path':'relative.py','text':'from .decimal import Decimal\n'},
               {'path':'broken.py','text':'from decimal import Decimal\nx=)\n'},
               {'path':'large.py','text':'import decimal\n','truncated':True}]
        notes=python_runtime_notes(files)
        self.assertEqual(len(notes),1)
        self.assertEqual(notes[0]['path'],'program.py')
        self.assertEqual(notes[0]['precision_assignments'][0]['constant'],123)
        self.assertEqual(notes[0]['precision_assignments'][0]['line'],3)
        self.assertIn('not a proven defect',notes[0]['scope'])

    def test_dynamic_context_expression_is_not_mislabeled_as_fixed(self):
        notes=python_runtime_notes([{'path':'main.py','text':'import decimal as d\nd.getcontext().prec = needed_digits\n'}])
        self.assertIsNone(notes[0]['precision_assignments'][0]['constant'])
        self.assertEqual(len(python_runtime_notes([{'path':f'{i}.py','text':'import decimal\n'} for i in range(20)])),8)


class CapturingEngine(ScriptedEngine):
    def __init__(self,actions):
        super().__init__(actions)
        self.config={**self.config,'coding_preflight':True}
        self.seen=[]

    def generate(self,history,*args,**kwargs):
        self.seen.append(list(history))
        return super().generate(history,*args,**kwargs)


class CodingPreflightTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'workspace')
        self.folder=Path(self.temp.name)
        (self.folder/'program.py').write_text('def add(a,b):return a-b\n')
        (self.folder/'test_program.py').write_text('import unittest\nfrom program import add\nclass Tests(unittest.TestCase):\n def test_sum(self):self.assertEqual(add(2,3),5)\n')
        self.tools=ComputerTools();self.messages=[];self.events=[]

    async def asyncTearDown(self):
        await self.tools.close();self.temp.cleanup()

    def runner(self,actions=(),checkpoint=None,prompt='Repair program.py and run its Python tests.',mode='agent'):
        engine=CapturingEngine(actions)
        request=SimpleNamespace(prompt=prompt,mode=mode,max_tokens=1024,run_until_done=True)
        def save(message,role=None):self.messages.append(message.to_dict())
        run=AgentRun(engine,self.tools,str(self.folder),request,lambda:self.messages,save,
                     lambda kind,data:self.events.append((kind,data)),lambda state:None,threading.Event(),checkpoint)
        return run,engine

    async def test_first_model_turn_sees_real_sources_and_failing_tests(self):
        run,engine=self.runner([call('write_file',{'path':'program.py','content':'def add(a,b):return a+b\n'}),FINAL])
        self.assertEqual(await run.run(),'complete')
        first=json.dumps(engine.seen[0])
        self.assertIn('return a-b',first)
        self.assertIn('FAILED',first)
        self.assertIn('automatic_initial_project',first)
        self.assertEqual(run.state['coding_preflight']['exit_code'],1)
        self.assertTrue(run.state['verified'])
        self.assertEqual(run.state['turns'],2)
        initial=[data for kind,data in self.events if kind=='tool_start' and data.get('origin')=='automatic_initial_project']
        after=[data for kind,data in self.events if kind=='tool_start' and data.get('origin')=='automatic_post_edit']
        self.assertEqual([data['name'] for data in initial],['inspect_project','run_checks'])
        self.assertEqual(len(after),1)
        # New automatic observations still render as actual Harmony tool data.
        self.assertTrue(any(Message.from_dict(m).author.role==Role.TOOL for m in engine.seen[0]))

    async def test_passing_baseline_never_verifies_unfinished_goal(self):
        (self.folder/'program.py').write_text('def add(a,b):return a+b\n')
        run,_=self.runner()
        await run.initial_project_checks()
        self.assertEqual(run.state['coding_preflight']['exit_code'],0)
        self.assertFalse(run.state['verified'])
        self.assertNotIn('auto_verification',run.state)
        results=[json.loads(data['result']) for kind,data in self.events if kind=='tool_result']
        self.assertTrue(all(result['baseline_only'] for result in results))
        self.assertTrue(all('test_verification' not in result for result in results))

    async def test_native_chat_accepts_actual_initial_and_post_edit_receipts(self):
        from app.native_chat import chat_history
        run,engine=self.runner([call('write_file',{'path':'program.py','content':'def add(a,b):return a+b\n'}),FINAL])
        self.assertEqual(await run.run(),'complete')
        first=chat_history(engine.seen[0])
        last=chat_history(engine.seen[-1])
        self.assertEqual(sum('Automatic local tool observation' in (r.get('content') or '') for r in first),2)
        self.assertEqual(sum('Automatic local tool observation' in (r.get('content') or '') for r in last),3)
        self.assertTrue(any(r['role']=='tool' for r in last))

    async def test_resume_does_not_repeat_completed_or_partial_baseline(self):
        run,_=self.runner();await run.initial_project_checks()
        count=len(self.events)
        for status in ('complete','started','cancelled'):
            state=json.loads(json.dumps(run.state));state['coding_preflight']['status']=status
            resumed,_=self.runner(checkpoint=state)
            await resumed.initial_project_checks()
            self.assertEqual(len(self.events),count)
        old,_=self.runner(checkpoint={'turns':2})
        await old.initial_project_checks();self.assertEqual(len(self.events),count)

    async def test_questions_chat_and_unrelated_work_skip_automatic_execution(self):
        for prompt,mode in [('What is Python?','agent'),('Repair program.py','chat'),('Create notes.txt','agent')]:
            run,_=self.runner(prompt=prompt,mode=mode)
            await run.initial_project_checks()
            self.assertNotIn('coding_preflight',run.state)
        self.assertEqual(self.events,[])

    async def test_stop_before_start_executes_nothing(self):
        run,engine=self.runner();run.flag.set()
        with self.assertRaises(Cancelled):await run.run()
        self.assertEqual(self.events,[]);self.assertEqual(engine.seen,[])

    async def test_baseline_error_is_saved_and_does_not_abort_agent(self):
        run,_=self.runner()
        run.tools=SimpleNamespace(execute=AsyncMock(side_effect=OSError('test fixture inspection error')))
        await run.initial_project_checks()
        self.assertEqual(run.state['coding_preflight']['status'],'failed')
        self.assertFalse(run.state['verified'])
        self.assertTrue(any(kind=='project_baseline_failed' for kind,_ in self.events))

    async def test_empty_suite_never_becomes_selected_post_edit_check(self):
        (self.folder/'test_program.py').write_text('import unittest\n')
        run,_=self.runner();await run.initial_project_checks()
        self.assertFalse(run.state['verified'])
        self.assertNotIn('selected_project_tests',run.state)

    async def test_inspection_artifact_retains_runtime_notes(self):
        (self.folder/'program.py').write_text('from decimal import Decimal\n')
        result=await self.tools.execute('inspect_project',{},str(self.folder))
        self.assertEqual(result['runtime_notes'][0]['path'],str(self.folder/'program.py'))
        saved=json.loads((ROOT/'run/artifacts'/Path(result['artifact']).name).read_text())
        self.assertEqual(saved['runtime_notes'],result['runtime_notes'])
