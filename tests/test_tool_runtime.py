# SPDX-License-Identifier: Apache-2.0
import os
from pathlib import Path
import shutil
import sys
import tempfile
import subprocess
import json
import unittest
from unittest.mock import patch

from app.tool_runtime import tool_environment
from app.tools import ROOT,shell
from app.batching import inspect_project


class ToolRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'workspace')
        self.folder=Path(self.temp.name)

    async def asyncTearDown(self):
        self.temp.cleanup()

    async def test_absent_project_wrapper_preserves_host_path_and_project_storage(self):
        with patch('app.tool_runtime.ROOT',self.folder):
            original=dict(os.environ);env=tool_environment()
            for key,value in original.items():
                if key not in ('TMPDIR','CARGO_HOME'):self.assertEqual(env[key],value)
            self.assertEqual(env['TMPDIR'],str(self.folder/'run/tool-tmp'))
            self.assertEqual(env['CARGO_HOME'],str(self.folder/'cache/cargo'))

    async def test_project_runner_is_visible_to_inspection_and_shell_without_changing_python(self):
        folder=self.folder/'run/tool-bin';folder.mkdir(parents=True)
        wrapper=folder/'pytest';wrapper.write_text('#!/bin/sh\nprintf runner-visible\n');wrapper.chmod(0o755)
        (self.folder/'test_demo.py').write_text('def test_demo(): assert True\n')
        original_python=shutil.which('python') or shutil.which('python3')
        with patch('app.tool_runtime.ROOT',self.folder):
            env=tool_environment()
            self.assertEqual(shutil.which('python',path=env['PATH']) or shutil.which('python3',path=env['PATH']),original_python)
            result=await inspect_project({},str(self.folder),self.folder/'artifacts')
            self.assertEqual(result['runtime']['pytest_command'],str(wrapper))
            self.assertTrue(result['test_candidates'][0]['available'])
            self.assertEqual(result['test_candidates'][0]['command'],str(wrapper))
            executed=await shell('pytest',str(self.folder))
        self.assertEqual(executed['exit_code'],0)
        self.assertEqual(executed['output'],'runner-visible')

    async def test_actual_child_tempfile_stays_on_project_drive(self):
        with patch('app.tool_runtime.ROOT',self.folder):env=tool_environment()
        result=subprocess.run([sys.executable,'-c','import tempfile,json; f=tempfile.NamedTemporaryFile(); print(json.dumps({"temporary":tempfile.gettempdir(),"file":f.name}))'],env=env,capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr);data=json.loads(result.stdout)
        self.assertEqual(data['temporary'],env['TMPDIR']);self.assertTrue(Path(data['file']).is_relative_to(self.folder))
        self.assertEqual(Path(env['TMPDIR']).stat().st_mode & 0o777,0o700)

    async def test_existing_rust_toolchain_resolves_with_project_cargo_cache(self):
        if not shutil.which('cargo'):self.skipTest('No host Cargo installed')
        with patch('app.tool_runtime.ROOT',self.folder):env=tool_environment()
        original=subprocess.run(['cargo','--version'],capture_output=True,text=True,timeout=10)
        redirected=subprocess.run(['cargo','--version'],env=env,capture_output=True,text=True,timeout=10)
        self.assertEqual(redirected.returncode,0,redirected.stderr);self.assertEqual(redirected.stdout,original.stdout)
        self.assertEqual(env.get('HOME'),os.environ.get('HOME'))
