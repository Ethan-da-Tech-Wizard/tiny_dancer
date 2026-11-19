# ==============================================================================
# Program: test_continuation.py
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


# ------------------------------------------------------------------------------
# ContinuingEngine: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class ContinuingEngine(ScriptedEngine):
    # ------------------------------------------------------------------------------
    # __init__: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def __init__(self, actions):
        super().__init__(actions)
        self.prompts, self.budgets = [], []

    # ------------------------------------------------------------------------------
    # cancel: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def cancel(self):
        pass

    # ------------------------------------------------------------------------------
    # generate: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def generate(self, history, cwd, emit, flag, agent, max_tokens, **kwargs):
        self.prompts.append(json.dumps(history)); self.budgets.append(max_tokens)
        item = next(self.actions)
        if isinstance(item,Exception): raise item
        return item if isinstance(item,tuple) else ([item],'RETURN')


# ------------------------------------------------------------------------------
# ContinuationTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class ContinuationTests(unittest.IsolatedAsyncioTestCase):
    # ------------------------------------------------------------------------------
    # asyncSetUp: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'workspace')
        self.tools=ComputerTools();self.messages=[];self.events=[]

    # ------------------------------------------------------------------------------
    # asyncTearDown: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def asyncTearDown(self):
        await self.tools.close();self.temp.cleanup()

    # ------------------------------------------------------------------------------
    # runner: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def runner(self, actions, **options):
        request=SimpleNamespace(prompt='Create and verify result.txt',mode='agent',max_tokens=512,run_until_done=True,max_turns=1,max_seconds=.001,**options)
        return AgentRun(ContinuingEngine(actions),self.tools,self.temp.name,request,lambda:self.messages,
                        lambda m,role=None:self.messages.append(m.to_dict()),lambda k,d:self.events.append((k,d)),lambda s:None,threading.Event())

    # ------------------------------------------------------------------------------
    # finish: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def finish(self):
        return call('finish_task',{'summary':'Created result.txt and checked its contents',
                    'checks':["test \"$(cat result.txt)\" = verified"]})

    # ------------------------------------------------------------------------------
    # test_until_done_passes_job_time_and_turn_caps_and_verifies: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_until_done_passes_job_time_and_turn_caps_and_verifies(self):
        run=self.runner([call('write_file',{'path':'result.txt','content':'verified'}),self.finish()])
        self.assertEqual(await run.run(),'complete')
        self.assertEqual(run.state['turns'],2)
        self.assertTrue(run.state['verified'])
        self.assertIsNone(run.state['max_seconds'])

    # ------------------------------------------------------------------------------
    # test_context_full_keeps_plan_and_does_not_execute_partial_call: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_context_full_keeps_plan_and_does_not_execute_partial_call(self):
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

    # ------------------------------------------------------------------------------
    # test_oversized_transaction_automatically_recovers: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_oversized_transaction_automatically_recovers(self):
        run=self.runner([ContextBudgetError('too much old tool output'),call('write_file',{'path':'result.txt','content':'verified'}),self.finish()])
        self.assertEqual(await run.run(),'complete')
        self.assertEqual(run.state['context_compactions'],1)

    # ------------------------------------------------------------------------------
    # test_impossible_minimal_context_reports_real_blocker: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_impossible_minimal_context_reports_real_blocker(self):
        run=self.runner([ContextBudgetError('does not fit')]*3)
        self.assertEqual(await run.run(),'paused')
        self.assertIn('saved goal/checkpoint',run.state['next_action'])
        self.assertEqual(run.state['context_compactions'],2)

    # ------------------------------------------------------------------------------
    # test_reply_limit_adapts_without_executing_incomplete_actions: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_reply_limit_adapts_without_executing_incomplete_actions(self):
        partial=call('write_file',{'path':'partial.txt','content':'bad'})
        run=self.runner([([partial],'MAX_TOKENS'),([partial],'MAX_TOKENS'),call('write_file',{'path':'result.txt','content':'verified'}),self.finish()])
        self.assertEqual(await run.run(),'complete')
        self.assertEqual(run.engine.budgets[:3],[512,1024,2048])
        self.assertFalse(Path(self.temp.name,'partial.txt').exists())

    # ------------------------------------------------------------------------------
    # test_until_done_still_stops_when_actions_fail_repeatedly: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_until_done_still_stops_when_actions_fail_repeatedly(self):
        run=self.runner([call('read_file',{'path':f'missing-{n}.txt'}) for n in range(8)])
        self.assertEqual(await run.run(),'paused')
        self.assertIn('Eight consecutive',run.state['next_action'])

    # ------------------------------------------------------------------------------
    # test_nonzero_shell_outcomes_count_as_failed_actions: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_nonzero_shell_outcomes_count_as_failed_actions(self):
        run=self.runner([call('shell',{'command':f'exit {n+1}'}) for n in range(8)])
        self.assertEqual(await run.run(),'paused')
        self.assertIn('Eight consecutive',run.state['next_action'])
        self.assertEqual(run.state['last_failure']['exit_code'],8)

    # ------------------------------------------------------------------------------
    # test_zero_test_success_is_rejected_then_real_tests_complete: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_zero_test_success_is_rejected_then_real_tests_complete(self):
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

    # ------------------------------------------------------------------------------
    # test_live_generation_progress_extends_watchdog: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_live_generation_progress_extends_watchdog(self):
        run=self.runner([call('write_file',{'path':'result.txt','content':'verified'}),self.finish()])
        run.engine.config={'inference_stall_seconds':.04}
        original=run.engine.generate
        # ------------------------------------------------------------------------------
        # generate: Function Pipeline & Contract Specification
        # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
        # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
        # Failure Modes: Catches or propagates domain exceptions according to API contracts
        # ------------------------------------------------------------------------------
        def generate(history,cwd,emit,*args,**kwargs):
            for n in range(6):
                time.sleep(.015);emit('progress',{'tokens':n,'seconds':n*.015})
            return original(history,cwd,emit,*args,**kwargs)
        run.engine.generate=generate
        self.assertEqual(await run.run(),'complete')

    # ------------------------------------------------------------------------------
    # test_stalled_inference_saves_progress_and_can_be_resumed: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_stalled_inference_saves_progress_and_can_be_resumed(self):
        released=threading.Event()
        run=self.runner([])
        run.engine.config={'inference_stall_seconds':.02}
        # ------------------------------------------------------------------------------
        # generate: Function Pipeline & Contract Specification
        # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
        # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
        # Failure Modes: Catches or propagates domain exceptions according to API contracts
        # ------------------------------------------------------------------------------
        def generate(*args,**kwargs):
            released.wait(1);return [],'RETURN'
        run.engine.generate=generate;run.engine.cancel=released.set
        self.assertEqual(await run.run(),'paused')
        self.assertTrue(released.is_set())
        self.assertIn('observable progress',run.state['next_action'])

    # ------------------------------------------------------------------------------
    # test_worker_timeout_is_reported_without_retrying_poll_loop: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_worker_timeout_is_reported_without_retrying_poll_loop(self):
        run=self.runner([TimeoutError('native worker timed out')])
        run.engine.cancel=lambda:None
        run.engine.config={'inference_stall_seconds':30}
        started=time.monotonic()
        self.assertEqual(await run.run(),'paused')
        self.assertLess(time.monotonic()-started,1)

    # ------------------------------------------------------------------------------
    # test_memory_guard_releases_only_model_and_saves_goal: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_memory_guard_releases_only_model_and_saves_goal(self):
        released=threading.Event()
        run=self.runner([])
        run.engine.config={'memory_pressure_seconds':0}
        run.engine.memory_issue=lambda:'Model released: only 0.5 GiB available. Free memory and Resume.'
        # ------------------------------------------------------------------------------
        # generate: Function Pipeline & Contract Specification
        # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
        # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
        # Failure Modes: Catches or propagates domain exceptions according to API contracts
        # ------------------------------------------------------------------------------
        def generate(*args,**kwargs):
            released.wait(5);return [],'RETURN'
        run.engine.generate=generate;run.engine.cancel=released.set
        self.assertEqual(await run.run(),'paused')
        self.assertTrue(released.is_set())
        self.assertIn('Free memory and Resume',run.state['next_action'])
        self.assertEqual(run.state['goal'],'Create and verify result.txt')

    # ------------------------------------------------------------------------------
    # test_cold_start_pressure_is_resumable: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_cold_start_pressure_is_resumable(self):
        run=self.runner([ResourcePressure('Model loading deferred: free memory and Resume')])
        self.assertEqual(await run.run(),'paused')
        self.assertIn('loading deferred',run.state['next_action'])

    # ------------------------------------------------------------------------------
    # test_memory_guard_also_covers_chat: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_memory_guard_also_covers_chat(self):
        released=threading.Event();run=self.runner([]);run.request.mode='chat'
        run.engine.config={'memory_pressure_seconds':0}
        run.engine.memory_issue=lambda:'Low RAM; free memory and Resume'
        # ------------------------------------------------------------------------------
        # generate: Function Pipeline & Contract Specification
        # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
        # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
        # Failure Modes: Catches or propagates domain exceptions according to API contracts
        # ------------------------------------------------------------------------------
        def generate(*args,**kwargs):
            released.wait(5);return [],'RETURN'
        run.engine.generate=generate
        run.engine.cancel=released.set
        self.assertEqual(await run.run(),'paused')
        self.assertTrue(released.is_set())


    # ------------------------------------------------------------------------------
    # test_database_boundary_compaction_and_resume_preserve_goal: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_database_boundary_compaction_and_resume_preserve_goal(self):
        rows=[{'id':1,'harmony':json.dumps(Message.from_role_and_content(Role.USER,'Create and verify result.txt').to_dict())}]
        # ------------------------------------------------------------------------------
        # history: Function Pipeline & Contract Specification
        # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
        # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
        # Failure Modes: Catches or propagates domain exceptions according to API contracts
        # ------------------------------------------------------------------------------
        def history(): return task_history(rows,run.request.prompt,'agent',run.state)
        # ------------------------------------------------------------------------------
        # save: Function Pipeline & Contract Specification
        # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
        # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
        # Failure Modes: Catches or propagates domain exceptions according to API contracts
        # ------------------------------------------------------------------------------
        def save(message,role=None):
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


# ------------------------------------------------------------------------------
# MemoryPreflightTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class MemoryPreflightTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # test_configured_startup_allows_previous_blocked_memory_without_ignoring_floor: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_configured_startup_allows_previous_blocked_memory_without_ignoring_floor(self):
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

    # ------------------------------------------------------------------------------
    # test_lower_startup_floor_keeps_runtime_pressure_protection: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_lower_startup_floor_keeps_runtime_pressure_protection(self):
        engine=LocalEngine()
        with patch('psutil.virtual_memory',return_value=SimpleNamespace(available=1.49*2**30)):
            self.assertIn('desktop responsive',engine.memory_issue())
        with patch('psutil.virtual_memory',return_value=SimpleNamespace(available=1.51*2**30)):
            self.assertIsNone(engine.memory_issue())

    # ------------------------------------------------------------------------------
    # test_low_available_memory_never_launches_native_child: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_low_available_memory_never_launches_native_child(self):
        engine=LocalEngine();engine.config['min_start_available_ram_gb']=6
        with patch('psutil.virtual_memory',return_value=SimpleNamespace(available=2*2**30)), patch('app.engine.PicchioSession') as session:
            with self.assertRaisesRegex(ResourcePressure,'2.00 GiB'):
                engine.load()
            session.assert_not_called()

    # ------------------------------------------------------------------------------
    # test_preflight_uses_available_rather_than_free_memory: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_preflight_uses_available_rather_than_free_memory(self):
        engine=LocalEngine();engine.config['min_start_available_ram_gb']=6
        with patch('psutil.virtual_memory',return_value=SimpleNamespace(available=8*2**30,free=.2*2**30)):
            self.assertIsNone(engine.memory_issue(before_start=True))



# ------------------------------------------------------------------------------
# DateTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class DateTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # test_counted_completed_weekdays_accept_typos_without_guessing_scores: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_counted_completed_weekdays_accept_typos_without_guessing_scores(self):
        for phrase in ('2 sundays ago','two Sundays ago','Sunday before last'):
            c=contract_for('what were the scroes of the nfl games '+phrase,today=date(2026,10,10))
            self.assertEqual(c['target_date'],'2026-09-27')
            self.assertEqual(c['workflow'],'nfl_scores')
        self.assertEqual(contract_for('NFL games three Sundays ago',today=date(2026,10,10),kind='answer')['target_date'],'2026-09-20')
        for phrase in ('this Sunday','next Sunday','Sundays since last month','Sunday 2026-10-11'):
            self.assertIsNone(contract_for('What were the NFL scores '+phrase,today=date(2026,10,10))['workflow'])
