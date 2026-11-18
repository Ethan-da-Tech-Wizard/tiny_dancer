# Program: tiny_dancer - tests/test_artifact_reads.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Tests for artifact reads (exercises app.agent, app.tools).
# SPDX-License-Identifier: Apache-2.0
"""Returned artifact references can be inspected without becoming product files."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from app.tools import ComputerTools,ROOT


# -------- artifact read tests --------
class ArtifactReadTests(unittest.IsolatedAsyncioTestCase):
    """Test group for artifact read."""
    async def asyncSetUp(self):
        """Test helper: asyncSetUp."""
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'run');self.root=Path(self.temp.name)
        self.artifacts=self.root/'artifacts';self.artifacts.mkdir();self.project=self.root/'project';self.project.mkdir()
        self.tools=ComputerTools();self.mock=patch('app.tools.ARTIFACTS',self.artifacts);self.mock.start()
        (self.artifacts/'check.json').write_text('{"exit_code": 1}\n')
    # Test helper: asyncTearDown.
    async def asyncTearDown(self):self.mock.stop();await self.tools.close();self.temp.cleanup()

    async def test_returned_artifact_reference_reads_real_saved_text(self):
        """Checks that returned artifact reference reads real saved text."""
        result=await self.tools.execute('read_file',{'path':'/artifacts/check.json'},str(self.project))
        self.assertIn('"exit_code": 1',result['text'])
        self.assertEqual(result['path'],str(self.artifacts/'check.json'))
        self.assertTrue(result['artifact_reference'])

    async def test_artifact_directory_reference_lists_saved_outputs(self):
        """Checks that artifact directory reference lists saved outputs."""
        result=await self.tools.execute('list_directory',{'path':'/artifacts'},str(self.project))
        self.assertIn('check.json',[x['name'] for x in result['entries']])

    async def test_alias_cannot_escape_directory_or_follow_escape_symlink(self):
        """Checks that alias cannot escape directory or follow escape symlink."""
        (self.root/'outside.txt').write_text('OUTSIDE')
        (self.artifacts/'escape.txt').symlink_to(self.root/'outside.txt')
        for path in ('/artifacts/../outside.txt','/artifacts/escape.txt'):
            with self.assertRaises(ValueError):await self.tools.execute('read_file',{'path':path},str(self.project))

    async def test_normal_project_file_still_resolves_relative_to_cwd(self):
        """Checks that normal project file still resolves relative to cwd."""
        (self.project/'product.py').write_text('PROJECT_SENTINEL\n')
        result=await self.tools.execute('read_file',{'path':'product.py'},str(self.project))
        self.assertIn('PROJECT_SENTINEL',result['text'])
        self.assertNotIn('artifact_reference',result)

    async def test_artifact_observation_does_not_pollute_source_hash_proof(self):
        """Checks that artifact observation does not pollute source hash proof."""
        from types import SimpleNamespace
        import threading
        from app.agent import AgentRun
        run=AgentRun(SimpleNamespace(config={}),self.tools,str(self.project),SimpleNamespace(prompt='Build a Python program.',mode='agent',max_tokens=None,run_until_done=True),lambda:[],lambda *a:None,lambda *a:None,lambda *a:None,threading.Event())
        await run.execute('read_file',{'path':'/artifacts/check.json'})
        self.assertNotIn(str(self.artifacts/'check.json'),run.state.get('inspected_sources',[]))


if __name__=='__main__':unittest.main()
