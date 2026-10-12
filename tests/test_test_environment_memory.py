# SPDX-License-Identifier: Apache-2.0
"""Keep actual runner discovery through context changes without fake passes."""
import copy
import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

from openai_harmony import Author, Message, Role, TextContent
from app.agent import AgentRun
from app.tools import ComputerTools, ROOT
from app.working_memory import inspection_test_evidence
from tests.test_agent import ScriptedEngine, call


class TestEnvironmentMemoryTests(unittest.TestCase):
    def test_real_receipt_fields_retained_without_mutating_input(self):
        raw = {'runtime': {'python': '/usr/bin/python', 'version': '3.14.7', 'pytest_module': False, 'pytest_command': '/project/run/tool-bin/pytest', 'cargo': None}, 'test_candidates': [{'command': "python -m unittest discover -s . -p 'test_*.py'", 'available': True, 'evidence': 'actual unittest imports'}], 'artifact': '/artifacts/inspection.json'}
        original = copy.deepcopy(raw)
        evidence = inspection_test_evidence(raw)
        self.assertIsNotNone(evidence)
        self.assertEqual(evidence['runtime'], raw['runtime'])
        self.assertEqual(evidence['test_candidates'], raw['test_candidates'])
        self.assertEqual(evidence['artifact'], raw['artifact'])
        self.assertEqual(raw, original)

    def test_malformed_optional_data_never_raises_or_invents_availability(self):
        for raw in (None, [], {'runtime': []}, {'test_candidates': [None, 1, []]}):
            with self.subTest(raw=raw):
                self.assertIsNone(inspection_test_evidence(raw))
        evidence = inspection_test_evidence({'test_candidates': [{'command': 'pytest', 'available': 'true', 'evidence': {}}]})
        self.assertIsNotNone(evidence)
        self.assertNotIn('available', evidence['test_candidates'][0])

    def test_large_commands_are_omitted_whole_and_total_receipt_is_bounded(self):
        raw = {'runtime': {'python': 'P' * 5000, 'version': '3.14'}, 'artifact': '/artifacts/full.json', 'test_candidates': [{'command': 'echo ' + 'x' * 5000, 'available': True}] + [{'command': 'echo ' + str(n) + 'x' * 300, 'available': True, 'evidence': 'e' * 1000} for n in range(12)]}
        evidence = inspection_test_evidence(raw)
        self.assertIsNotNone(evidence)
        self.assertLessEqual(len(json.dumps(evidence, ensure_ascii=False)), 2500)
        self.assertTrue(evidence['truncated'])
        self.assertGreater(evidence['commands_omitted'], 0)
        self.assertEqual(evidence['artifact'], raw['artifact'])
        original_commands = {item['command'] for item in raw['test_candidates']}
        for candidate in evidence['test_candidates']:
            self.assertIn(candidate['command'], original_commands)


class TestEnvironmentRunnerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'workspace')
        self.folder = Path(self.temp.name)
        (self.folder / 'program.py').write_text('message = "source"\n')
        (self.folder / 'test_program.py').write_text('import unittest\n')
        self.tools = ComputerTools()
        self.messages = []
        self.events = []

    async def asyncTearDown(self):
        await self.tools.close()
        self.temp.cleanup()

    def runner(self, actions=(), checkpoint=None):
        request = SimpleNamespace(prompt='Create and test a Python program', mode='agent', max_tokens=None, run_until_done=True)
        return AgentRun(ScriptedEngine(actions), self.tools, str(self.folder), request,
            lambda: self.messages, lambda message, role=None: self.messages.append(message.to_dict()),
            lambda kind, data: self.events.append((kind, data)), lambda *args: None, threading.Event(), checkpoint)

    def notes(self, run):
        for value in reversed(run.prompt_history()):
            message = Message.from_dict(value)
            text = ''.join(content.text for content in message.content)
            if text.startswith('Continue the same user task'):
                return json.loads(text[text.index('{'):])
        self.fail('No actual checkpoint note')

    async def test_actual_inspection_survives_two_compactions_and_resume(self):
        run = self.runner()
        inspection = await run.execute('inspect_project', {})
        run.record_evidence('inspect_project', inspection)
        expected = inspection_test_evidence(inspection)
        self.assertIsNotNone(expected)
        for n in range(2):
            run.compact_context('test recovery ' + str(n))
            self.assertEqual(self.notes(run)['test_environment'], expected)
        resumed = self.runner(checkpoint=json.loads(json.dumps(run.state)))
        resumed.compact_context('resume without old inspection transaction')
        self.assertEqual(self.notes(resumed)['test_environment'], expected)
        self.assertFalse(resumed.state['verified'])

    async def test_available_runner_receipt_cannot_complete_work_without_checks(self):
        final = Message.from_role_and_content(Role.ASSISTANT, 'Tests passed.').with_channel('final')
        run = self.runner([call('inspect_project', {}), final, final])
        self.assertEqual(await run.run(), 'paused')
        self.assertTrue(run.state.get('test_environment'))
        self.assertFalse(run.state['verified'])
        self.assertFalse(run.state.get('auto_verification'))
        self.assertFalse(any(kind == 'tool_start' and data['name'] in ('shell', 'run_checks') for kind, data in self.events))

    async def test_actual_empty_suite_recovery_updates_cached_environment(self):
        run = self.runner()
        (self.folder / 'empty').mkdir()
        result = await run.execute('run_checks', {'commands': ["python -m unittest discover -s empty -p 'test_*.py'"]})
        self.assertTrue(result.get('empty_test_suite'))
        self.assertIsInstance(result.get('recovery'), dict)
        run.record_evidence('run_checks', result)
        self.assertEqual(run.state.get('test_environment'), inspection_test_evidence(result['recovery']))
        self.assertTrue(run.state.get('test_environment'))
        self.assertFalse(run.state['verified'])

    async def test_legacy_history_receipt_is_carried_without_new_execution(self):
        run = self.runner()
        inspection = await run.execute('inspect_project', {})
        message = Message(author=Author.new(Role.TOOL, 'functions.inspect_project'), content=[TextContent(text=json.dumps(inspection))]).with_recipient('assistant')
        self.messages.append(message.to_dict())
        self.assertNotIn('test_environment', run.state)
        run.compact_context('legacy history with real inspection')
        self.assertEqual(self.notes(run)['test_environment'], inspection_test_evidence(inspection))
        self.assertFalse(run.state['verified'])


if __name__ == '__main__':
    unittest.main()
