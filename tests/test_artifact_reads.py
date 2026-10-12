# SPDX-License-Identifier: Apache-2.0
"""Returned artifact references can be inspected without becoming product files."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from app.tools import ComputerTools,ROOT


class ArtifactReadTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'run');self.root=Path(self.temp.name)
        self.artifacts=self.root/'artifacts';self.artifacts.mkdir();self.project=self.root/'project';self.project.mkdir()
        self.tools=ComputerTools();self.mock=patch('app.tools.ARTIFACTS',self.artifacts);self.mock.start()
        (self.artifacts/'check.json').write_text('{"exit_code": 1}\n')
    async def asyncTearDown(self):self.mock.stop();await self.tools.close();self.temp.cleanup()

    async def test_returned_artifact_reference_reads_real_saved_text(self):
        result=await self.tools.execute('read_file',{'path':'/artifacts/check.json'},str(self.project))
        self.assertIn('"exit_code": 1',result['text'])
        self.assertEqual(result['path'],str(self.artifacts/'check.json'))
        self.assertTrue(result['artifact_reference'])

    async def test_artifact_directory_reference_lists_saved_outputs(self):
        result=await self.tools.execute('list_directory',{'path':'/artifacts'},str(self.project))
        self.assertIn('check.json',[x['name'] for x in result['entries']])

    async def test_alias_cannot_escape_directory_or_follow_escape_symlink(self):
        (self.root/'outside.txt').write_text('OUTSIDE')
        (self.artifacts/'escape.txt').symlink_to(self.root/'outside.txt')
        for path in ('/artifacts/../outside.txt','/artifacts/escape.txt'):
            with self.assertRaises(ValueError):await self.tools.execute('read_file',{'path':path},str(self.project))

    async def test_normal_project_file_still_resolves_relative_to_cwd(self):
        (self.project/'product.py').write_text('PROJECT_SENTINEL\n')
        result=await self.tools.execute('read_file',{'path':'product.py'},str(self.project))
        self.assertIn('PROJECT_SENTINEL',result['text'])
        self.assertNotIn('artifact_reference',result)

    async def test_artifact_observation_does_not_pollute_source_hash_proof(self):
        from types import SimpleNamespace
        import threading
        from app.agent import AgentRun
        run=AgentRun(SimpleNamespace(config={}),self.tools,str(self.project),SimpleNamespace(prompt='Build a Python program.',mode='agent',max_tokens=None,run_until_done=True),lambda:[],lambda *a:None,lambda *a:None,lambda *a:None,threading.Event())
        await run.execute('read_file',{'path':'/artifacts/check.json'})
        self.assertNotIn(str(self.artifacts/'check.json'),run.state.get('inspected_sources',[]))


if __name__=='__main__':unittest.main()
