# Program: tiny_dancer - tests/test_continuation.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Tests for continuation (exercises app.agent, app.engine, app.history).
# SPDX-License-Identifier: Apache-2.0
"""Tests for continuation (exercises app.agent, app.engine, app.history)."""
import json
import time
import sys
import shlex
import tempfile
import threading
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from openai_harmony import Message, Role
from app.agent import AgentRun
from app.engine import ContextBudgetError, ResourcePressure, LocalEngine
from app.history import task_history
from app.task_policy import contract_for
from app.tools import ComputerTools, ROOT
from tests.test_agent import ScriptedEngine, call


# -------- continuing engine --------
class ContinuingEngine(ScriptedEngine):
    """Helper type continuing engine."""
    def __init__(self, actions):
        """Test helper: init."""
        super().__init__(actions)
        self.prompts, self.budgets = [], []

    def cancel(self):
        """Test helper: cancel."""
        pass

    def generate(self, history, cwd, emit, flag, agent, max_tokens, **kwargs):
        """Test helper: generate."""
        self.prompts.append(json.dumps(history)); self.budgets.append(max_tokens)
        item = next(self.actions)
        if isinstance(item,Exception): raise item
        return item if isinstance(item,tuple) else ([item],'RETURN')


# -------- continuation tests --------
class ContinuationTests(unittest.IsolatedAsyncioTestCase):
    """Test group for continuation."""
    async def asyncSetUp(self):
        """Test helper: asyncSetUp."""
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'workspace')
        self.tools=ComputerTools();self.messages=[];self.events=[]

    async def asyncTearDown(self):
        """Test helper: asyncTearDown."""
        await self.tools.close();self.temp.cleanup()

    def runner(self, actions, **options):
        """Test helper: runner."""
        request=SimpleNamespace(prompt='Create and verify result.txt',mode='agent',max_tokens=512,run_until_done=True,max_turns=1,max_seconds=.001,**options)
        return AgentRun(ContinuingEngine(actions),self.tools,self.temp.name,request,lambda:self.messages,
                        lambda m,role=None:self.messages.append(m.to_dict()),lambda k,d:self.events.append((k,d)),lambda s:None,threading.Event())

    def finish(self):
        """Test helper: finish."""
        return call('finish_task',{'summary':'Created result.txt and checked its contents',
                    'checks':["test \"$(cat result.txt)\" = verified"]})

    async def test_until_done_passes_job_time_and_turn_caps_and_verifies(self):
        """Checks that until done passes job time and turn caps and verifies."""
        run=self.runner([call('write_file',{'path':'result.txt','content':'verified'}),self.finish()])
        self.assertEqual(await run.run(),'complete')
        self.assertEqual(run.state['turns'],2)
        self.assertTrue(run.state['verified'])
        self.assertIsNone(run.state['max_seconds'])

    async def test_context_full_keeps_plan_and_does_not_execute_partial_call(self):
        """Checks that context full keeps plan and does not execute partial call."""
        run=self.runner([
            call('task_progress',{'steps':[{'title':'Create result.txt','done':True}],'summary':'Created result.txt'}),
            call('write_file',{'path':'result.txt','content':'verified'}),
            ([call('write_file',{'path':'partial.txt','content':'bad'})],'CONTEXT_FULL'),self.finish()])
        self.assertEqual(await run.run(),'complete')
        self.assertEqual(run.state['context_compactions'],1)
        self.assertFalse(Path(self.temp.name,'partial.txt').exists())
        compacted=run.engine.prompts[-1]
        self.assertIn('Create and verify result.txt',compacted)
        self.assertIn('Created result.txt',compacted)
        self.assertNotIn('partial.txt',compacted)
        self.assertEqual(sum(k=='tool_start' and d['name']=='write_file' for k,d in self.events),1)

    async def test_oversized_transaction_automatically_recovers(self):
        """Checks that oversized transaction automatically recovers."""
        run=self.runner([ContextBudgetError('too much old tool output'),call('write_file',{'path':'result.txt','content':'verified'}),self.finish()])
        self.assertEqual(await run.run(),'complete')
        self.assertEqual(run.state['context_compactions'],1)

    async def test_impossible_minimal_context_reports_real_blocker(self):
        """Checks that impossible minimal context reports real blocker."""
        run=self.runner([ContextBudgetError('does not fit')]*3)
        self.assertEqual(await run.run(),'paused')
        self.assertIn('saved goal/checkpoint',run.state['next_action'])
        self.assertEqual(run.state['context_compactions'],2)

    async def test_reply_limit_adapts_without_executing_incomplete_actions(self):
        """Checks that reply limit adapts without executing incomplete actions."""
        partial=call('write_file',{'path':'partial.txt','content':'bad'})
        run=self.runner([([partial],'MAX_TOKENS'),([partial],'MAX_TOKENS'),call('write_file',{'path':'result.txt','content':'verified'}),self.finish()])
        self.assertEqual(await run.run(),'complete')
        self.assertEqual(run.engine.budgets[:3],[512,1024,2048])
        self.assertFalse(Path(self.temp.name,'partial.txt').exists())

    async def test_until_done_still_stops_when_actions_fail_repeatedly(self):
        """Checks that until done still stops when actions fail repeatedly."""
        run=self.runner([call('read_file',{'path':f'missing-{n}.txt'}) for n in range(8)])
        self.assertEqual(await run.run(),'paused')
        self.assertIn('Eight consecutive',run.state['next_action'])

    async def test_nonzero_shell_outcomes_count_as_failed_actions(self):
        """Checks that nonzero shell outcomes count as failed actions."""
        run=self.runner([call('shell',{'command':f'exit {n+1}'}) for n in range(8)])
        self.assertEqual(await run.run(),'paused')
        self.assertIn('Eight consecutive',run.state['next_action'])
        self.assertEqual(run.state['last_failure']['exit_code'],8)

    async def test_zero_test_success_is_rejected_then_real_tests_complete(self):
        """Checks that zero test success is rejected then real tests complete."""
        folder=Path(self.temp.name)/'tests';folder.mkdir()
        command=shlex.quote(sys.executable)+' -m unittest discover -s tests -q'
        run=self.runner([
            call('write_file',{'path':'result.txt','content':'verified'}),
            # Simulate runners/wrappers that report zero tests with exit 0.
            call('finish_task',{'summary':'Claimed tested','checks':[command+' || true']}),
            call('write_file',{'path':'tests/test_actual.py','content':'import unittest\nfrom pathlib import Path\nclass Real(unittest.TestCase):\n    def test_value(self):\n        self.assertEqual(Path("result.txt").read_text(),"verified")\n'}),
            call('finish_task',{'summary':'Executed the real test suite','checks':[command]})])
        self.assertEqual(await run.run(),'complete')
        results=[json.loads(d['result']) for k,d in self.events if k=='tool_result' and d['name']=='finish_task']
        self.assertFalse(results[0]['verified'])
        self.assertTrue(results[0]['checks'][0]['empty_test_suite'])
        self.assertEqual(results[0]['checks'][0]['exit_code'],0)
        self.assertTrue(results[-1]['verified'])

    async def test_live_generation_progress_extends_watchdog(self):
        """Checks that live generation progress extends watchdog."""
        run=self.runner([call('write_file',{'path':'result.txt','content':'verified'}),self.finish()])
        run.engine.config={'inference_stall_seconds':.04}
        original=run.engine.generate
        def generate(history,cwd,emit,*args,**kwargs):
            """Test helper: generate."""
            for n in range(6):
                time.sleep(.015);emit('progress',{'tokens':n,'seconds':n*.015})
            return original(history,cwd,emit,*args,**kwargs)
        run.engine.generate=generate
        self.assertEqual(await run.run(),'complete')

    async def test_stalled_inference_saves_progress_and_can_be_resumed(self):
        """Checks that stalled inference saves progress and can be resumed."""
        released=threading.Event()
        run=self.runner([])
        run.engine.config={'inference_stall_seconds':.02}
        def generate(*args,**kwargs):
            """Test helper: generate."""
            released.wait(1);return [],'RETURN'
        run.engine.generate=generate;run.engine.cancel=released.set
        self.assertEqual(await run.run(),'paused')
        self.assertTrue(released.is_set())
        self.assertIn('observable progress',run.state['next_action'])

    async def test_worker_timeout_is_reported_without_retrying_poll_loop(self):
        """Checks that worker timeout is reported without retrying poll loop."""
        run=self.runner([TimeoutError('native worker timed out')])
        run.engine.cancel=lambda:None
        run.engine.config={'inference_stall_seconds':30}
        started=time.monotonic()
        self.assertEqual(await run.run(),'paused')
        self.assertLess(time.monotonic()-started,1)

    async def test_memory_guard_releases_only_model_and_saves_goal(self):
        """Checks that memory guard releases only model and saves goal."""
        released=threading.Event()
        run=self.runner([])
        run.engine.config={'memory_pressure_seconds':0}
        run.engine.memory_issue=lambda:'Model released: only 0.5 GiB available. Free memory and Resume.'
        def generate(*args,**kwargs):
            """Test helper: generate."""
            released.wait(5);return [],'RETURN'
        run.engine.generate=generate;run.engine.cancel=released.set
        self.assertEqual(await run.run(),'paused')
        self.assertTrue(released.is_set())
        self.assertIn('Free memory and Resume',run.state['next_action'])
        self.assertEqual(run.state['goal'],'Create and verify result.txt')

    async def test_cold_start_pressure_is_resumable(self):
        """Checks that cold start pressure is resumable."""
        run=self.runner([ResourcePressure('Model loading deferred: free memory and Resume')])
        self.assertEqual(await run.run(),'paused')
        self.assertIn('loading deferred',run.state['next_action'])

    async def test_memory_guard_also_covers_chat(self):
        """Checks that memory guard also covers chat."""
        released=threading.Event();run=self.runner([]);run.request.mode='chat'
        run.engine.config={'memory_pressure_seconds':0}
        run.engine.memory_issue=lambda:'Low RAM; free memory and Resume'
        def generate(*args,**kwargs):
            """Test helper: generate."""
            released.wait(5);return [],'RETURN'
        run.engine.generate=generate
        run.engine.cancel=released.set
        self.assertEqual(await run.run(),'paused')
        self.assertTrue(released.is_set())


    async def test_database_boundary_compaction_and_resume_preserve_goal(self):
        """Checks that database boundary compaction and resume preserve goal."""
        rows=[{'id':1,'harmony':json.dumps(Message.from_role_and_content(Role.USER,'Create and verify result.txt').to_dict())}]
        # Test helper: history.
        def history(): return task_history(rows,run.request.prompt,'agent',run.state)
        def save(message,role=None):
            """Test helper: save."""
            rows.append({'id':len(rows)+1,'harmony':json.dumps(message.to_dict())});return len(rows)
        request=SimpleNamespace(prompt='Create and verify result.txt',mode='agent',max_tokens=512,run_until_done=True)
        run=AgentRun(ContinuingEngine([ContextBudgetError('full'),call('write_file',{'path':'result.txt','content':'verified'}),self.finish()]),
            self.tools,self.temp.name,request,history,save,lambda *a:None,lambda *a:None,threading.Event(),{'context_start':1})
        self.assertEqual(await run.run(),'complete')
        self.assertEqual(run.state['context_start'],2)
        self.assertTrue(run.state['context_insert_goal'])
        self.assertIn('Continue the same user task',run.engine.prompts[-1])
        self.assertIn('Create and verify result.txt',run.engine.prompts[-1])
        self.assertGreater(len(rows),4)


# -------- memory preflight tests --------
class MemoryPreflightTests(unittest.TestCase):
    """Test group for memory preflight."""
    def test_configured_startup_allows_previous_blocked_memory_without_ignoring_floor(self):
        """Checks that configured startup allows previous blocked memory without ignoring floor."""
        engine=LocalEngine()
        with patch('psutil.virtual_memory',return_value=SimpleNamespace(available=5.85*2**30)), \
                patch('app.engine.load_harmony_encoding',return_value=object()), \
                patch('app.llama_session.LlamaReferenceSession') as native:
            engine.load()
            native.assert_called_once()
            self.assertEqual(engine.status,'ready')
        engine=LocalEngine()
        with patch('psutil.virtual_memory',return_value=SimpleNamespace(available=4.49*2**30)), \
                patch('app.llama_session.LlamaReferenceSession') as native:
            with self.assertRaisesRegex(ResourcePressure,'loading deferred'):
                engine.load()
            native.assert_not_called()

    def test_lower_startup_floor_keeps_runtime_pressure_protection(self):
        """Checks that lower startup floor keeps runtime pressure protection."""
        engine=LocalEngine()
        with patch('psutil.virtual_memory',return_value=SimpleNamespace(available=1.49*2**30)):
            self.assertIn('desktop responsive',engine.memory_issue())
        with patch('psutil.virtual_memory',return_value=SimpleNamespace(available=1.51*2**30)):
            self.assertIsNone(engine.memory_issue())

    def test_low_available_memory_never_launches_native_child(self):
        """Checks that low available memory never launches native child."""
        engine=LocalEngine();engine.config['min_start_available_ram_gb']=6
        with patch('psutil.virtual_memory',return_value=SimpleNamespace(available=2*2**30)), patch('app.engine.PicchioSession') as session:
            with self.assertRaisesRegex(ResourcePressure,'2.00 GiB'):
                engine.load()
            session.assert_not_called()

    def test_preflight_uses_available_rather_than_free_memory(self):
        """Checks that preflight uses available rather than free memory."""
        engine=LocalEngine();engine.config['min_start_available_ram_gb']=6
        with patch('psutil.virtual_memory',return_value=SimpleNamespace(available=8*2**30,free=.2*2**30)):
            self.assertIsNone(engine.memory_issue(before_start=True))



# -------- date tests --------
class DateTests(unittest.TestCase):
    """Test group for date."""
    def test_counted_completed_weekdays_accept_typos_without_guessing_scores(self):
        """Checks that counted completed weekdays accept typos without guessing scores."""
        for phrase in ('2 sundays ago','two Sundays ago','Sunday before last'):
            c=contract_for('what were the scroes of the nfl games '+phrase,today=date(2026,10,10))
            self.assertEqual(c['target_date'],'2026-09-27')
            self.assertEqual(c['workflow'],'nfl_scores')
        self.assertEqual(contract_for('NFL games three Sundays ago',today=date(2026,10,10),kind='answer')['target_date'],'2026-09-20')
        for phrase in ('this Sunday','next Sunday','Sundays since last month','Sunday 2026-10-11'):
            self.assertIsNone(contract_for('What were the NFL scores '+phrase,today=date(2026,10,10))['workflow'])
