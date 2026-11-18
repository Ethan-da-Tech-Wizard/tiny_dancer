# Program: tiny_dancer - tests/test_preserved_files.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Tests for preserved files (exercises app.agent, app.tools).
# SPDX-License-Identifier: Apache-2.0
"""Tests for preserved files (exercises app.agent, app.tools)."""
import tempfile
import threading
import unittest
import shlex
import sys
from pathlib import Path
from types import SimpleNamespace

from app.agent import AgentRun
from app.tools import ComputerTools,ROOT


# -------- preserved file tests --------
class PreservedFileTests(unittest.IsolatedAsyncioTestCase):
    """Test group for preserved file."""
    async def asyncSetUp(self):
        """Test helper: asyncSetUp."""
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'workspace');self.folder=Path(self.temp.name)
        self.tools=ComputerTools();self.messages=[]
        (self.folder/'test_acceptance.py').write_text('value = 1\n')
        (self.folder/'program.py').write_text('value = 1\n')

    async def asyncTearDown(self):
        """Test helper: asyncTearDown."""
        await self.tools.close();self.temp.cleanup()

    def runner(self,prompt='Build a Python app. Keep the supplied test_acceptance.py unchanged and add your own tests.'):
        """Test helper: runner."""
        return AgentRun(SimpleNamespace(config={}),self.tools,str(self.folder),
                        SimpleNamespace(prompt=prompt,mode='agent',max_tokens=None,run_until_done=True),
                        lambda:self.messages,lambda m,role=None:self.messages.append(m.to_dict()),
                        lambda *a:None,lambda *a:None,threading.Event())

    async def test_user_preserved_file_rejects_direct_overwrite_before_mutation(self):
        """Checks that user preserved file rejects direct overwrite before mutation."""
        run=self.runner()
        with self.assertRaisesRegex(ValueError,'unchanged'):
            await run.execute('write_file',{'path':'test_acceptance.py','content':'value = 0\n'})
        self.assertEqual((self.folder/'test_acceptance.py').read_text(),'value = 1\n')

    async def test_multi_file_patch_rejects_all_writes_when_one_target_is_preserved(self):
        """Checks that multi file patch rejects all writes when one target is preserved."""
        patch='*** Begin Patch\n*** Update File: program.py\n@@\n-value = 1\n+value = 2\n*** Update File: test_acceptance.py\n@@\n-value = 1\n+value = 0\n*** End Patch'
        with self.assertRaisesRegex(ValueError,'unchanged'):
            await self.runner().execute('apply_patch',{'patch':patch})
        self.assertEqual((self.folder/'program.py').read_text(),'value = 1\n')
        self.assertEqual((self.folder/'test_acceptance.py').read_text(),'value = 1\n')

    async def test_new_test_file_and_reads_of_preserved_file_remain_available(self):
        """Checks that new test file and reads of preserved file remain available."""
        run=self.runner()
        result=await run.execute('read_file',{'path':'test_acceptance.py'})
        self.assertIn('value = 1',result['text'])
        await run.execute('write_file',{'path':'test_own.py','content':'import unittest\nclass Own(unittest.TestCase):\n    def test_behavior(self):\n        self.assertEqual(1+1,2)\n'})
        self.assertTrue((self.folder/'test_own.py').is_file())

    async def test_new_goal_can_edit_a_file_without_a_preservation_directive(self):
        """Checks that new goal can edit a file without a preservation directive."""
        await self.runner('Edit test_acceptance.py in this Python project.').execute('write_file',{'path':'test_acceptance.py','content':'value = 2\n'})
        self.assertEqual((self.folder/'test_acceptance.py').read_text(),'value = 2\n')

    async def test_quoted_relative_file_is_preserved(self):
        """Checks that quoted relative file is preserved."""
        with self.assertRaisesRegex(ValueError,'unchanged'):
            await self.runner('Build Python code. Leave `./test_acceptance.py` unchanged.').execute('write_file',{'path':'test_acceptance.py','content':'bad\n'})

    async def test_ordinary_filename_mentions_do_not_create_a_preservation_rule(self):
        """Checks that ordinary filename mentions do not create a preservation rule."""
        await self.runner('Edit test_acceptance.py and describe what was unchanged.').execute('write_file',{'path':'test_acceptance.py','content':'value = 2\n'})
        self.assertEqual((self.folder/'test_acceptance.py').read_text(),'value = 2\n')

    async def test_rejected_edit_preserves_real_passing_test_receipt(self):
        """Checks that rejected edit preserves real passing test receipt."""
        run=self.runner()
        for name in ('program.py','test_acceptance.py'):
            await run.execute('read_file',{'path':name})
        content='import unittest\nimport program\nimport test_acceptance\nclass Own(unittest.TestCase):\n    def test_values(self):\n        self.assertEqual((program.value,test_acceptance.value),(1,1))\n'
        await run.execute('write_file',{'path':'test_own.py','content':content})
        await run.execute('shell',{'command':shlex.quote(sys.executable)+' -m unittest discover -q'})
        self.assertTrue(run.state['verified']);proof=dict(run.state['auto_verification'])
        with self.assertRaisesRegex(ValueError,'unchanged'):
            await run.execute('write_file',{'path':'test_acceptance.py','content':'value = 0\n'})
        self.assertTrue(run.state['verified']);self.assertEqual(run.state['auto_verification'],proof)
