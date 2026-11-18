# Program: tiny_dancer - tests/test_agent.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Tests for agent (exercises app.agent, app.engine, app.tools).
# SPDX-License-Identifier: Apache-2.0
"""Tests for agent (exercises app.agent, app.engine, app.tools)."""
import asyncio
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest

from openai_harmony import Author, Message, Role, TextContent, HarmonyEncodingName, load_harmony_encoding
from app.agent import AgentRun
from app.engine import LocalEngine, Cancelled
from app.tools import ComputerTools, ROOT
from tests.raw_engine_fixture import legacy_raw_engine


def call(name, args):
    """Test helper: call."""
    return Message.from_role_and_content(Role.ASSISTANT, json.dumps(args)).with_channel('commentary').with_recipient('functions.' + name)


# -------- scripted engine --------
class ScriptedEngine:
    """Helper type scripted engine."""
    config = {'max_tool_steps':24, 'max_repeated_actions':4}

    def __init__(self, actions):
        """Test helper: init."""
        self.actions = iter(actions)

    def generate(self, history, cwd, emit, flag, agent, max_tokens, **kwargs):
        """Test helper: generate."""
        item = next(self.actions)
        return item if isinstance(item, tuple) else ([item], 'RETURN')


# -------- agent loop tests --------
class AgentLoopTests(unittest.IsolatedAsyncioTestCase):
    """Test group for agent loop."""
    async def asyncSetUp(self):
        """Test helper: asyncSetUp."""
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'workspace', prefix='loop-validation-')
        self.cwd = self.temp.name
        self.tools = ComputerTools()
        self.messages = [Message.from_role_and_content(Role.USER, 'Create and verify result.txt').to_dict()]
        self.events = []
        self.saved = None

    async def asyncTearDown(self):
        """Test helper: asyncTearDown."""
        await self.tools.close()
        self.temp.cleanup()

    def runner(self, actions, mode='agent', checkpoint=None, flag=None):
        # Test helper: save.
        """Test helper: runner."""
        def save(message, role=None): self.messages.append(message.to_dict())
        # Test helper: checkpoint saved.
        def checkpoint_saved(state): self.saved = json.loads(json.dumps(state))
        return AgentRun(ScriptedEngine(actions), self.tools, self.cwd,
            SimpleNamespace(mode=mode, prompt='Create and verify result.txt', max_tokens=1024, max_turns=40),
            lambda:self.messages, save, lambda kind,data:self.events.append((kind,data)),
            checkpoint_saved, flag or threading.Event(), checkpoint)

    async def test_failed_check_is_repaired_before_completion(self):
        """Checks that failed check is repaired before completion."""
        run = self.runner([
            call('finish_task', {'summary':'Done', 'checks':["test -f result.txt"]}),
            call('write_file', {'path':'result.txt','content':'verified'}),
            call('finish_task', {'summary':'Created and checked result.txt',
                 'checks':["python3 -c \"from pathlib import Path; assert Path('result.txt').read_text() == 'verified'\""]}),
        ])
        self.assertEqual(await run.run(), 'complete')
        self.assertTrue(self.saved['verified'])
        self.assertEqual(self.saved['checks'][0]['exit_code'], 0)
        checks=[json.loads(d['result'])['exit_code'] for k,d in self.events if k=='tool_result' and d['name']=='verification']
        self.assertEqual(checks,[1,0])

    async def test_continues_beyond_old_24_step_limit(self):
        """Checks that continues beyond old 24 step limit."""
        run = self.runner([call('write_file', {'path':f'part-{n}.txt','content':str(n)}) for n in range(26)]
            + [call('finish_task', {'summary':'All 26 parts verified',
                 'checks':["python3 -c \"from pathlib import Path; assert len(list(Path('.').glob('part-*.txt'))) == 26\""]})])
        self.assertEqual(await run.run(), 'complete')
        self.assertEqual(self.saved['turns'],27)
        self.assertTrue(any(k=='continuation' for k,_ in self.events))

    async def test_final_claim_alone_cannot_complete_agent_task(self):
        """Checks that final claim alone cannot complete agent task."""
        final=Message.from_role_and_content(Role.ASSISTANT,'Done!').with_channel('final')
        run=self.runner([final]*4)
        self.assertEqual(await run.run(),'paused')
        self.assertFalse(self.saved['verified'])
        self.assertFalse(any(m.get('channel')=='final' for m in self.messages))

    async def test_truncated_tool_call_is_never_executed(self):
        """Checks that truncated tool call is never executed."""
        partial=call('write_file',{'path':'must-not-exist.txt','content':'unsafe partial action'})
        run=self.runner([([partial],'MAX_TOKENS'),
            call('finish_task', {'summary':'Incomplete action was not executed','checks':['test ! -f must-not-exist.txt']})])
        self.assertEqual(await run.run(),'complete')
        self.assertFalse((Path(self.cwd)/'must-not-exist.txt').exists())

    async def test_chat_cannot_execute_computer_tools(self):
        """Checks that chat cannot execute computer tools."""
        run=self.runner([call('write_file',{'path':'not-allowed.txt','content':'x'})],mode='chat')
        with self.assertRaisesRegex(RuntimeError,'chat mode'): await run.run()
        self.assertFalse((Path(self.cwd)/'not-allowed.txt').exists())

    async def test_repeated_failure_pauses_and_checkpoint_can_resume(self):
        """Checks that repeated failure pauses and checkpoint can resume."""
        action=call('read_file',{'path':'missing.txt'})
        run=self.runner([action]*4)
        self.assertEqual(await run.run(),'paused')
        checkpoint=json.loads(json.dumps(self.saved))
        resumed=self.runner([call('write_file',{'path':'result.txt','content':'resumed'}),
            call('finish_task',{'summary':'Resumed and verified','checks':['test -s result.txt']})],checkpoint=checkpoint)
        self.assertEqual(await resumed.run(),'complete')
        self.assertEqual(self.saved['turns'],6)

    async def test_pending_plan_prevents_false_completion(self):
        """Checks that pending plan prevents false completion."""
        run=self.runner([
            call('task_progress',{'steps':[{'title':'Write the file','done':False}]}),
            call('finish_task',{'summary':'Done','checks':['exit 0']}),
            call('write_file',{'path':'result.txt','content':'done'}),
            call('task_progress',{'steps':[{'title':'Write the file','done':True}]}),
            call('finish_task',{'summary':'Done','checks':['test -s result.txt']}),
        ])
        self.assertEqual(await run.run(),'complete')
        self.assertEqual(sum(k=='tool_start' and d['name']=='verification' for k,d in self.events),1)

    async def test_stop_prevents_any_further_actions(self):
        """Checks that stop prevents any further actions."""
        flag=threading.Event();flag.set()
        run=self.runner([call('write_file',{'path':'not-run.txt','content':'x'})],flag=flag)
        with self.assertRaises(Cancelled): await run.run()
        self.assertFalse((Path(self.cwd)/'not-run.txt').exists())

    async def test_alternating_unchanged_actions_pause_instead_of_spinning(self):
        """Checks that alternating unchanged actions pause instead of spinning."""
        actions=[call('read_file',{'path':'missing-a.txt'}),call('read_file',{'path':'missing-b.txt'})]*4
        run=self.runner(actions)
        self.assertEqual(await run.run(),'paused')
        self.assertEqual(self.saved['turns'],8)


# -------- context tests --------
class ContextTests(unittest.TestCase):
    """Test group for context."""
    def test_agent_checkpoint_keeps_goal_and_saved_plan_when_history_outgrows_context(self):
        """Checks that agent checkpoint keeps goal and saved plan when history outgrows context."""
        encoding=load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
        messages=[Message.from_role_and_content(Role.USER,'GOAL: verify each saved file'),
                  call('task_progress',{'steps':[{'title':'UNIQUE_SAVED_PLAN','done':False}]})]
        messages.append(Message(author=Author.new(Role.TOOL,'functions.task_progress'),content=[TextContent(text='saved')]).with_recipient('assistant'))
        for n in range(10):
            messages.extend([call('read_file',{'path':f'{n}.txt'}),
                Message(author=Author.new(Role.TOOL,'functions.read_file'),content=[TextContent(text='old-output '*800)]).with_recipient('assistant')])
        engine=legacy_raw_engine()
        captured=[]
        # -------- session --------
        class Session:
            """Helper type session."""
            ctx=4500
            proc=SimpleNamespace(poll=lambda:None)
            last_timing={}
            def turn(self, ids, maximum, keep, callback, temperature=0):
                """Test helper: turn."""
                captured.append(encoding.decode(ids));return [],'MAX_TOKENS',None
        engine.session=Session();engine.encoding=encoding;engine.load=lambda cancel=None:None
        events=[]
        from app.engine import ContextBudgetError
        history=[m.to_dict() for m in messages]
        with self.assertRaises(ContextBudgetError):
            engine.generate(history,str(ROOT/'workspace'),lambda k,d:events.append((k,d)),threading.Event(),True,512)
        self.assertEqual(captured,[])
        saved=list(history)
        request=SimpleNamespace(prompt='GOAL: verify each saved file',mode='agent',max_tokens=512,run_until_done=True)
        run=AgentRun(engine,SimpleNamespace(),str(ROOT/'workspace'),request,lambda:saved,
                     lambda message,role=None:saved.append(message.to_dict()),lambda k,d:events.append((k,d)),lambda *a:None,threading.Event(),
                     checkpoint={'steps':[{'title':'UNIQUE_SAVED_PLAN','done':False}]})
        run.compact_context('Context was full.')
        engine.generate(run.prompt_history(),str(ROOT/'workspace'),lambda k,d:events.append((k,d)),threading.Event(),True,512)
        self.assertIn('GOAL: verify each saved file',captured[0])
        self.assertIn('UNIQUE_SAVED_PLAN',captured[0])
        self.assertNotIn('"path": "0.txt"',captured[0])
        self.assertTrue(any(k=='context' for k,_ in events))
