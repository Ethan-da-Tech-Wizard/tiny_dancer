# SPDX-License-Identifier: Apache-2.0
"""Exercise automatic starting allowances through actual runner/tool paths."""
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest

from openai_harmony import Message, Role
from app.agent import AgentRun
from app.tools import ComputerTools, ROOT
from tests.test_agent import call
from tests.test_continuation import ContinuingEngine


class GenerationBudgetTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'workspace')
        self.tools = ComputerTools()
        self.messages = []

    async def asyncTearDown(self):
        await self.tools.close()
        self.temp.cleanup()

    def runner(self, actions=(), prompt='Create result.py and test its behavior', mode='agent', budget=None, checkpoint=None):
        request = SimpleNamespace(prompt=prompt, mode=mode, max_tokens=budget, run_until_done=True)
        return AgentRun(ContinuingEngine(actions), self.tools, self.temp.name, request,
                        lambda: self.messages, lambda message, role=None: self.messages.append(message.to_dict()),
                        lambda *args: None, lambda *args: None, threading.Event(),checkpoint)

    async def test_automatic_work_allowance_is_available_for_the_first_write(self):
        run = self.runner([call('write_file', {'path': 'result.py', 'content': 'answer = 42\n'}),
                           call('finish_task', {'summary': 'Created and checked result.py',
                                                'checks': ['python3 -c "from result import answer; assert answer == 42"']})])
        self.assertEqual(await run.run(), 'complete')
        self.assertEqual(run.engine.budgets, [2048, 2048])
        self.assertEqual(run.state.get('generation_budget'), {'requested': None, 'initial': 2048, 'current': 2048})
        self.assertNotIn('model_limit_retries', run.state)

    async def test_automatic_questions_keep_a_small_allowance(self):
        final = Message.from_role_and_content(Role.ASSISTANT, 'Hello!').with_channel('final')
        run = self.runner([final], prompt='hi')
        self.assertEqual(await run.run(), 'complete')
        self.assertEqual(run.engine.budgets, [512])

    async def test_automatic_chat_keeps_a_small_allowance(self):
        final = Message.from_role_and_content(Role.ASSISTANT, 'I can explain that.').with_channel('final')
        run = self.runner([final], mode='chat')
        self.assertEqual(await run.run(), 'complete')
        self.assertEqual(run.engine.budgets, [512])

    async def test_explicit_starting_allowance_is_preserved(self):
        for budget in (64, 512, 1024, 2048):
            run = self.runner(budget=budget)
            with self.subTest(budget=budget):
                self.assertEqual(run.current_max_tokens, budget)
                self.assertEqual(run.state.get('generation_budget'), {'requested': budget, 'initial': budget, 'current': budget})

    async def test_retry_allowance_is_recorded_and_partial_action_never_runs(self):
        partial = call('write_file', {'path': 'partial.py', 'content': 'must never execute'})
        final = call('finish_task', {'summary': 'Checked that the partial action never executed', 'checks': ['test ! -f partial.py']})
        run = self.runner([([partial], 'MAX_TOKENS'), final], budget=1024)
        self.assertEqual(await run.run(), 'complete')
        self.assertEqual(run.engine.budgets, [1024, 2048])
        self.assertEqual(run.state.get('generation_budget'), {'requested': 1024, 'initial': 1024, 'current': 2048})
        self.assertFalse((Path(self.temp.name) / 'partial.py').exists())

    async def test_automatic_allowance_applies_to_work_in_every_language(self):
        for prompt in ('Repair main.cpp and run its tests', 'Implement a JavaScript module', 'Create a grocery list'):
            with self.subTest(prompt=prompt):
                self.assertEqual(self.runner(prompt=prompt).current_max_tokens, 2048)

    async def test_resume_preserves_a_grown_allowance_when_requested_budget_is_unchanged(self):
        checkpoint={'generation_budget':{'requested':1024,'initial':1024,'current':2048}}
        run=self.runner(budget=1024,checkpoint=checkpoint)
        self.assertEqual(run.current_max_tokens,2048)
        self.assertEqual(run.state['generation_budget'],checkpoint['generation_budget'])

    async def test_changed_resume_choice_resets_the_starting_allowance(self):
        checkpoint={'generation_budget':{'requested':1024,'initial':1024,'current':2048}}
        run=self.runner(budget=512,checkpoint=checkpoint)
        self.assertEqual(run.current_max_tokens,512)
        self.assertEqual(run.state['generation_budget'],{'requested':512,'initial':512,'current':512})
