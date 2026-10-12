# SPDX-License-Identifier: Apache-2.0
import asyncio
import json
import shlex
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from app.tools import ComputerTools,ROOT,shell
from app.batching import inspect_project,run_checks
from app.verification import test_summary
from tests import test_verified_final as fixtures
from tests.test_agent import call


class BatchToolTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'workspace');self.folder=Path(self.temp.name);self.artifacts=self.folder/'artifacts';self.tools=ComputerTools()
    async def asyncTearDown(self): await self.tools.close();self.temp.cleanup()

    async def test_inspection_bundles_files_and_actual_runtime_without_importing_project(self):
        (self.folder/'calc.py').write_text('raise RuntimeError("must not execute project")\n')
        (self.folder/'test_calc.py').write_text('import unittest\n# test source only\n')
        (self.folder/'.env').write_text('secret=never automatically inspected')
        result=await inspect_project({},str(self.folder),self.artifacts)
        self.assertEqual({Path(file['path']).name for file in result['files']},{'calc.py','test_calc.py'})
        self.assertTrue(result['runtime']['version']);self.assertTrue(result['test_candidates'][0]['available'])
        self.assertIn('unittest',result['test_candidates'][0]['command'])
        self.assertTrue((self.artifacts/Path(result['artifact']).name).exists())

    async def test_inspection_has_bounded_preview_full_artifact_and_individual_errors(self):
        (self.folder/'large.py').write_text('# harmless source\n'*1000)
        (self.folder/'binary.py').write_bytes(b'\0binary')
        result=await inspect_project({'files':['large.py','binary.py','missing.py']},str(self.folder),self.artifacts)
        self.assertEqual(len(result['files'][0]['text']),6000);self.assertTrue(result['files'][0]['truncated'])
        self.assertTrue(result['files'][0]['preview_truncated']);self.assertIn('read_file',result['files'][0]['read_hint'])
        full=json.loads((self.artifacts/Path(result['artifact']).name).read_text())
        self.assertGreater(len(full['files'][0]['text']),6000)
        self.assertTrue(all(file.get('error') for file in result['files'][1:]))
        with self.assertRaises(ValueError): await inspect_project({'files':['x']*9},str(self.folder),self.artifacts)

    async def test_real_related_checks_preserve_each_output(self):
        commands=[shlex.quote(sys.executable)+" -c 'assert 6*7==42;print(42)'",shlex.quote(sys.executable)+" -c 'assert 1+2==3;print(3)'"]
        result=await run_checks({'commands':commands},str(self.folder),self.artifacts,shell)
        self.assertTrue(result['complete']);self.assertEqual(result['exit_code'],0)
        self.assertEqual([r['output'].strip() for r in result['checks']],['42','3'])
        self.assertTrue(all(r['artifact'] for r in result['checks']))
        self.assertNotIn('recovery',result)

    async def test_failed_check_stops_later_command_unless_requested(self):
        commands=['exit 7','touch later']
        result=await run_checks({'commands':commands},str(self.folder),self.artifacts,shell)
        self.assertEqual(result['exit_code'],7);self.assertFalse(result['complete']);self.assertFalse((self.folder/'later').exists())
        result=await run_checks({'commands':commands,'stop_on_failure':False},str(self.folder),self.artifacts,shell)
        self.assertTrue(result['complete']);self.assertEqual(result['exit_code'],7);self.assertTrue((self.folder/'later').exists())

    async def test_timeout_and_cancel_stop_current_check_and_future_commands(self):
        result=await run_checks({'commands':['sleep 30','touch later'],'timeout':1},str(self.folder),self.artifacts,shell)
        self.assertTrue(result['timed_out']);self.assertFalse((self.folder/'later').exists())
        task=asyncio.create_task(run_checks({'commands':['sleep 30','touch later']},str(self.folder),self.artifacts,shell))
        await asyncio.sleep(0.05);task.cancel()
        with self.assertRaises(asyncio.CancelledError): await task
        self.assertFalse((self.folder/'later').exists())

    async def test_invalid_batches_do_not_execute(self):
        for args in ({'commands':[]},{'commands':['x']*9},{'commands':[None]},{'commands':['true'],'timeout':False},{'commands':['true'],'stop_on_failure':'yes'}):
            with self.subTest(args=args),self.assertRaises(ValueError): await run_checks(args,str(self.folder),self.artifacts,shell)

    async def test_long_shell_output_retains_actual_test_footer(self):
        command=shlex.quote(sys.executable)+" -c 'print(\"noise\"*5000);print(\"Ran 3 tests in 0.1s\\n\\nOK\")'"
        result=await shell(command,str(self.folder))
        self.assertTrue(result['truncated']);self.assertEqual(test_summary(result['output'])['count'],3)
        self.assertGreater((ROOT/'run/artifacts'/Path(result['artifact']).name).stat().st_size,16000)

    async def test_inspection_bundles_common_nested_source_and_unittest_files(self):
        (self.folder/'src').mkdir();(self.folder/'tests').mkdir()
        (self.folder/'src/main.py').write_text('raise RuntimeError("never import project source")\n')
        (self.folder/'tests/test_main.py').write_text('import unittest\nraise RuntimeError("never import tests")\n')
        result=await inspect_project({},str(self.folder),self.artifacts)
        self.assertEqual({str(Path(file['path']).relative_to(self.folder)) for file in result['files']},{'src/main.py','tests/test_main.py'})
        self.assertTrue(result['test_candidates'][0]['available'])
        self.assertIn('-s tests',result['test_candidates'][0]['command'])

    async def test_available_python3_command_does_not_assume_a_python_alias(self):
        (self.folder/'test_main.py').write_text('import unittest\n')
        with patch('app.batching.shutil.which',side_effect=lambda name,**kwargs:sys.executable if name=='python3' else None):
            result=await inspect_project({},str(self.folder),self.artifacts)
        self.assertTrue(result['test_candidates'][0]['available'])
        self.assertTrue(result['test_candidates'][0]['command'].startswith(shlex.quote(sys.executable)+' -m unittest'))

    async def test_missing_runner_reports_available_checks_without_running_replacements(self):
        (self.folder/'test_main.py').write_text('import unittest\nraise RuntimeError("inspection must not execute tests")\n')
        result=await run_checks({'commands':['td_validation_runner_that_does_not_exist','touch later']},str(self.folder),self.artifacts,shell)
        self.assertEqual(result['exit_code'],127)
        self.assertEqual(len(result['checks']),1)
        self.assertFalse((self.folder/'later').exists())
        self.assertTrue(result['recovery']['test_candidates'][0]['available'])
        self.assertIn('unittest',result['recovery']['test_candidates'][0]['command'])

    async def test_pytest_function_tests_do_not_receive_a_unittest_replacement(self):
        (self.folder/'tests').mkdir()
        (self.folder/'tests/test_main.py').write_text('def test_main(tmp_path):\n raise RuntimeError("must not execute test")\n')
        result=await inspect_project({},str(self.folder),self.artifacts)
        self.assertTrue(result['test_candidates'])
        self.assertTrue(all('pytest' in candidate['command'] for candidate in result['test_candidates']))

    async def test_automatic_manifest_and_readme_scan_skips_symlinks(self):
        private=self.folder/'.env';private.write_text('secret must not be automatically read')
        (self.folder/'README.md').symlink_to(private)
        (self.folder/'pyproject.toml').symlink_to(private)
        result=await inspect_project({},str(self.folder),self.artifacts)
        self.assertEqual(result['files'],[])

    async def test_zero_test_discovery_reports_nested_runner_without_executing_it(self):
        (self.folder/'empty').mkdir();(self.folder/'tests').mkdir()
        (self.folder/'tests/test_main.py').write_text('import unittest\nraise RuntimeError("must not run replacement tests")\n')
        result=await run_checks({'commands':[shlex.quote(sys.executable)+' -m unittest discover -s empty']},str(self.folder),self.artifacts,shell)
        self.assertTrue(test_summary(result['checks'][0]['output'])['empty'])
        self.assertEqual(len(result['checks']),1)
        self.assertIn('-s tests',result['recovery']['test_candidates'][0]['command'])

    async def test_bounded_scan_keeps_test_runner_evidence_with_many_root_sources(self):
        for number in range(20):(self.folder/f'module_{number:02d}.py').write_text('value=42\n')
        (self.folder/'tests').mkdir()
        (self.folder/'tests/test_main.py').write_text('import unittest\n')
        result=await inspect_project({},str(self.folder),self.artifacts)
        self.assertEqual(len(result['files']),8)
        self.assertIn('-s tests',result['test_candidates'][0]['command'])


class BatchedVerificationTests(fixtures.VerifiedFinalTests):
    # Inherit real file/test fixtures and source-mutation guard coverage.
    def setup_actions(self):
        actions=super().setup_actions()
        command=json.loads(actions[-1].content[0].text)['command']
        return actions[:-1]+[call('run_checks',{'commands':[command,shlex.quote(sys.executable)+" -c 'from result import answer;assert answer()==42'"]})]

    async def test_later_failure_invalidates_passing_suite(self):
        actions=self.setup_actions();args=json.loads(actions[-1].content[0].text);args['commands'].append('exit 3');actions[-1]=call('run_checks',args)
        run=self.runner(actions+[self.final(),self.final()])
        self.assertEqual(await run.run(),'paused');self.assertFalse(run.state['verified'])

    async def test_source_change_inside_batch_invalidates_passing_suite(self):
        actions=self.setup_actions();args=json.loads(actions[-1].content[0].text);args['commands'].append("printf 'def answer():\\n    return 0\\n' > result.py");actions[-1]=call('run_checks',args)
        run=self.runner(actions+[self.final(),self.final()])
        self.assertEqual(await run.run(),'paused');self.assertFalse(run.state['verified'])
