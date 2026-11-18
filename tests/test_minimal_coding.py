# Program: tiny_dancer - tests/test_minimal_coding.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Tests for minimal coding (exercises app.engine, scripts.minimal_coding).
# SPDX-License-Identifier: Apache-2.0
"""Tests for minimal coding (exercises app.engine, scripts.minimal_coding)."""
import json
import threading
import unittest
from openai_harmony import Message, Role
from scripts.minimal_coding import run_loop
from app.engine import Cancelled


def call(command='pwd', name='shell'):
    """Test helper: call."""
    return Message.from_role_and_content(Role.ASSISTANT,json.dumps({'command':command})).with_channel('analysis').with_recipient('functions.'+name)


# -------- minimal coding tests --------
class MinimalCodingTests(unittest.IsolatedAsyncioTestCase):
    """Test group for minimal coding."""
    async def drive(self, replies, flag=None):
        """Test helper: drive."""
        self.executed=[];self.events=[];self.saved=[];sequence=iter(replies)
        async def execute(name,args):
            """Test helper: execute."""
            self.executed.append((name,args));return {'exit_code':0,'output':'actual result'}
        return await run_loop(lambda history:next(sequence),execute,'original task',flag or threading.Event(),
            lambda kind,data:self.events.append((kind,data)),lambda history:self.saved.append(list(history)))

    async def test_actual_calls_then_submission_without_publishing_draft(self):
        """Checks that actual calls then submission without publishing draft."""
        private=Message.from_role_and_content(Role.ASSISTANT,'private reasoning').with_channel('analysis')
        final=Message.from_role_and_content(Role.ASSISTANT,'unaccepted final').with_channel('final')
        result=await self.drive([([private,call()], 'EOS'),([final],'EOS')])
        self.assertEqual(result['status'],'submitted');self.assertEqual(len(self.executed),1)
        self.assertNotIn('private reasoning',json.dumps(self.events));self.assertNotIn('unaccepted final',json.dumps(result))
        self.assertIn('actual result',json.dumps(self.saved[-1]))

    async def test_truncated_call_does_not_execute(self):
        """Checks that truncated call does not execute."""
        result=await self.drive([([call()], 'MAX_TOKENS')])
        self.assertEqual(result['status'],'incomplete_generation');self.assertEqual(self.executed,[])

    async def test_unavailable_tool_does_not_execute(self):
        """Checks that unavailable tool does not execute."""
        result=await self.drive([([call(name='write_file')], 'EOS')])
        self.assertEqual(result['status'],'unsupported_tool');self.assertEqual(self.executed,[])

    async def test_cancel_before_execution(self):
        """Checks that cancel before execution."""
        flag=threading.Event();flag.set()
        with self.assertRaises(Cancelled):await self.drive([],flag)
        self.assertEqual(self.executed,[])

    async def test_repeated_action_without_changed_result_stops(self):
        """Checks that repeated action without changed result stops."""
        result=await self.drive([([call()], 'EOS')]*4)
        self.assertEqual(result['status'],'unchanged_actions');self.assertEqual(len(self.executed),4)

    async def test_empty_response_does_not_submit(self):
        """Checks that empty response does not submit."""
        result=await self.drive([([], 'EOS')]);self.assertEqual(result['status'],'missing_final')
