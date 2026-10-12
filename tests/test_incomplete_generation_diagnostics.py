# SPDX-License-Identifier: Apache-2.0
"""Diagnose real reply-limit recovery without leaking or executing text."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

from openai_harmony import Message, Role
from app.agent import AgentRun
from app.tools import ComputerTools, ROOT
from tests.test_agent import ScriptedEngine, call


class IncompleteGenerationDiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'workspace')
        self.folder = Path(self.temp.name)
        self.tools = ComputerTools()
        self.messages = []
        self.events = []

    async def asyncTearDown(self):
        await self.tools.close()
        self.temp.cleanup()

    async def recover(self, partial):
        final = call('finish_task', {'summary': 'Partial action rejected and checked', 'checks': ['test ! -e must-not-exist.txt']})
        request = SimpleNamespace(prompt='Check that a partial action never executes', mode='agent', max_tokens=None, run_until_done=True)
        run = AgentRun(ScriptedEngine([([partial], 'MAX_TOKENS'), final]), self.tools, str(self.folder), request,
            lambda: self.messages, lambda message, role=None: self.messages.append(message.to_dict()),
            lambda kind, data: self.events.append((kind, data)), lambda *args: None, threading.Event())
        self.assertEqual(await run.run(), 'complete')
        self.assertFalse((self.folder / 'must-not-exist.txt').exists())
        metadata = [data for kind, data in self.events if kind == 'generation_incomplete']
        self.assertEqual(len(metadata), 1)
        self.assertEqual(metadata[0]['reason'], 'MAX_TOKENS')
        self.assertEqual(run.state['generation_budget']['current'], run.recovery_max_tokens)
        return metadata[0]

    async def test_tool_phase_and_size_retained_without_partial_execution(self):
        body = json.dumps({'path': 'must-not-exist.txt', 'content': 'private partial command'})
        partial = Message.from_role_and_content(Role.ASSISTANT, body).with_channel('commentary').with_recipient('functions.write_file')
        event = await self.recover(partial)
        self.assertEqual(event['messages'], [{'channel': 'commentary', 'recipient': 'functions.write_file', 'has_recipient': True, 'characters': len(body)}])
        self.assertNotIn('private partial command', json.dumps(event))
        self.assertFalse(any(kind == 'tool_start' and data['name'] == 'write_file' for kind, data in self.events))

    async def test_analysis_phase_retained_without_private_text(self):
        text = 'private reasoning must stay private'
        partial = Message.from_role_and_content(Role.ASSISTANT, text).with_channel('analysis')
        event = await self.recover(partial)
        self.assertEqual(event['messages'], [{'channel': 'analysis', 'recipient': None, 'has_recipient': False, 'characters': len(text)}])
        self.assertNotIn(text, json.dumps(event))

    async def test_unrecognized_recipient_is_not_copied_to_diagnostics(self):
        recipient = 'functions.unrecognized_private_name'
        partial = Message.from_role_and_content(Role.ASSISTANT, 'private body').with_channel('commentary').with_recipient(recipient)
        event = await self.recover(partial)
        self.assertEqual(event['messages'][0]['recipient'], None)
        self.assertTrue(event['messages'][0]['has_recipient'])
        self.assertNotIn(recipient, json.dumps(event))

    async def test_unrecognized_channel_is_not_copied_to_diagnostics(self):
        channel = 'unrecognized_private_channel'
        partial = Message.from_role_and_content(Role.ASSISTANT, 'private body').with_channel(channel)
        event = await self.recover(partial)
        self.assertEqual(event['messages'][0]['channel'], None)
        self.assertNotIn(channel, json.dumps(event))


if __name__ == '__main__':
    unittest.main()
