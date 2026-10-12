# SPDX-License-Identifier: Apache-2.0
"""Regression scenarios derived from observed native waste and completion risks."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

from openai_harmony import Message,Role
from app.agent import AgentRun
from app.batching import inspect_project
from app.deliverables import inspect_deliverables
from app.task_policy import contract_for,tools_for
from app.tools import ComputerTools,ROOT,TOOLS
from tests.test_agent import ScriptedEngine,call


class CapabilityHardeningTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'workspace');self.folder=Path(self.temp.name)
        self.tools=ComputerTools();self.messages=[];self.events=[]
    async def asyncTearDown(self):
        await self.tools.close();self.temp.cleanup()
    def runner(self,actions,prompt='Create and test a local script'):
        request=SimpleNamespace(prompt=prompt,mode='agent',max_tokens=1024,run_until_done=True)
        return AgentRun(ScriptedEngine(actions),self.tools,str(self.folder),request,lambda:self.messages,
                        lambda message,role=None:self.messages.append(message.to_dict()),lambda kind,data:self.events.append((kind,data)),
                        lambda *args:None,threading.Event())
    async def test_empty_optional_file_list_uses_automatic_source_and_test_scan(self):
        (self.folder/'calc.py').write_text('def add(a,b): return a-b\n')
        (self.folder/'test_calc.py').write_text('import unittest\n')
        snapshot=await inspect_project({'path':'','files':[]},str(self.folder),self.folder/'artifacts')
        self.assertEqual({Path(item['path']).name for item in snapshot['files']},{'calc.py','test_calc.py'})
        self.assertIn('unittest',snapshot['test_candidates'][0]['command'])
    async def test_automatic_scan_handles_native_and_web_sources_without_hidden_files(self):
        (self.folder/'main.cpp').write_text('int main(){return 0;}\n')
        (self.folder/'client.js').write_text('throw new Error("source must never execute");\n')
        (self.folder/'.env.js').write_text('private=1')
        (self.folder/'linked.cpp').symlink_to(self.folder/'main.cpp')
        snapshot=await inspect_project({},str(self.folder),self.folder/'artifacts')
        self.assertEqual({Path(item['path']).name for item in snapshot['files']},{'main.cpp','client.js'})
    async def test_check_timeout_schema_has_seconds_bounds_and_default(self):
        schema=next(tool for tool in TOOLS if tool['name']=='run_checks')['parameters']['properties']['timeout']
        self.assertEqual((schema.get('minimum'),schema.get('maximum'),schema.get('default')),(1,300,120))
        self.assertIn('seconds',schema.get('description',''))
    async def test_non_python_work_keeps_small_context_patch_capability(self):
        for prompt in ('Repair main.cpp','Fix this JavaScript module','Create a grocery list'):
            names={tool['name'] for tool in tools_for(contract_for(prompt),TOOLS)}
            with self.subTest(prompt=prompt):self.assertIn('apply_patch',names)
    async def test_answer_can_discover_desktop_without_executing_any_action(self):
        run=self.runner([],prompt='What are my available tools?')
        await run.execute('discover_tools',{'toolset':'desktop'})
        self.assertIn('desktop',run.allowed_tools)
        self.assertFalse(any(kind=='tool_start' for kind,data in self.events))
    async def test_every_original_tool_remains_available_through_discovery_for_work(self):
        run=self.runner([])
        for language in ('python','rust'):await run.execute('discover_tools',{'language':language})
        for group in ('web','desktop','editor'):await run.execute('discover_tools',{'toolset':group})
        self.assertEqual(run.allowed_tools,{tool['name'] for tool in TOOLS})
    async def test_repeated_same_reads_pause_despite_json_spacing_and_key_order(self):
        args={'path':'missing.txt','max_lines':20,'start_line':1}
        actions=[]
        for number in range(8):
            text=json.dumps(dict(reversed(list(args.items()))) if number%2 else args,indent=number)
            actions.append(Message.from_role_and_content(Role.ASSISTANT,text).with_channel('commentary').with_recipient('functions.read_file'))
        run=self.runner(actions)
        self.assertEqual(await run.run(),'paused');self.assertEqual(run.state['turns'],4)
    async def prepared_script(self,actions):
        run=self.runner(actions)
        await run.execute('write_file',{'path':'answer.sh','content':'#!/bin/sh\nprintf 42\n'})
        await run.execute('write_file',{'path':'test_answer.py','content':"import subprocess,unittest\nclass ScriptTest(unittest.TestCase):\n def test_answer(self):\n  self.assertEqual(subprocess.check_output(['sh','answer.sh'],text=True),'42')\n"})
        await run.execute('run_checks',{'commands':['python -m unittest -q test_answer']})
        self.assertTrue(run.state['verified'])
        return run
    async def test_non_python_script_and_tests_are_both_in_verified_hash_proof(self):
        run=await self.prepared_script([])
        proof=run.state['auto_verification']['files_sha256']
        self.assertEqual({Path(name).name for name in proof},{'answer.sh','test_answer.py'})
    async def test_external_non_python_edit_after_tests_blocks_native_completion(self):
        final=Message.from_role_and_content(Role.ASSISTANT,'Script created and tests passed.').with_channel('final')
        run=await self.prepared_script([final,final])
        (self.folder/'answer.sh').write_text('#!/bin/sh\nprintf wrong\n')
        self.assertEqual(await run.run(),'paused');self.assertFalse(run.state['verified'])
    async def test_named_json_output_cannot_be_replaced_by_other_json_file(self):
        run=self.runner([],prompt='Save the results to reports/answer.json')
        await run.execute('write_file',{'path':'wrong.json','content':'{"answer":42}'})
        self.assertIsNotNone(inspect_deliverables(run.contract,run.state)[0])
        await run.execute('write_file',{'path':'reports/answer.json','content':'{"answer":42}'})
        self.assertIsNone(inspect_deliverables(run.contract,run.state)[0])
    async def test_valid_json_scalars_remain_supported_for_explicit_file_outputs(self):
        for content in ('42','"hello"','true','null','[]','{}'):
            run=self.runner([],prompt='Save JSON to output.json')
            await run.execute('write_file',{'path':'output.json','content':content})
            with self.subTest(content=content):self.assertIsNone(inspect_deliverables(run.contract,run.state)[0])
    async def test_editing_preexisting_inspected_tests_invalidates_verified_completion(self):
        final=Message.from_role_and_content(Role.ASSISTANT,'Program and tests pass.').with_channel('final')
        run=self.runner([final,final])
        await run.execute('write_file',{'path':'answer.sh','content':'#!/bin/sh\nprintf 42\n'})
        test="import subprocess,unittest\nclass ScriptTest(unittest.TestCase):\n def test_answer(self):\n  self.assertEqual(subprocess.check_output(['sh','answer.sh'],text=True),'42')\n"
        (self.folder/'test_answer.py').write_text(test)
        await run.execute('inspect_project',{})
        await run.execute('run_checks',{'commands':['python -m unittest -q test_answer']})
        self.assertTrue(run.state['verified'])
        (self.folder/'test_answer.py').write_text(test.replace("'42')","'43')"))
        self.assertEqual(await run.run(),'paused');self.assertFalse(run.state['verified'])
    async def test_finish_checks_cannot_change_program_after_passing_tests(self):
        run=await self.prepared_script([])
        result=await run.execute('finish_task',{'summary':'Done','checks':['python -m unittest -q test_answer',"printf '#!/bin/sh\\nprintf wrong\\n' > answer.sh"]})
        self.assertFalse(result['verified'])
        self.assertNotIn('auto_verification',run.state)
    async def test_finish_checks_can_format_before_final_real_tests(self):
        run=await self.prepared_script([])
        result=await run.execute('finish_task',{'summary':'Formatted and tested','checks':["printf '\\n# verified comment\\n' >> answer.sh",'python -m unittest -q test_answer']})
        self.assertTrue(result['verified'])
        self.assertNotIn('auto_verification',run.state)
    async def test_json_created_by_shell_is_verified_at_the_requested_path(self):
        run=self.runner([],prompt='Save the result as output.json')
        await run.execute('shell',{'command':"printf '{\"answer\":42}' > output.json"})
        result=await run.execute('finish_task',{'summary':'Saved and checked output.json','checks':['python3 -c "import json;assert json.load(open(\'output.json\'))=={\'answer\':42}"']})
        self.assertTrue(result['verified'])
    async def test_unnamed_shell_json_can_be_verified_after_actual_file_inspection(self):
        run=self.runner([],prompt='Save the result as JSON')
        await run.execute('shell',{'command':"printf '{\"answer\":42}' > shell-result.json"})
        await run.execute('read_file',{'path':'shell-result.json'})
        self.assertIsNone(inspect_deliverables(run.contract,run.state)[0])
    async def test_named_shell_json_cannot_change_after_completion_checks(self):
        run=self.runner([],prompt='Save the result as output.json')
        await run.execute('shell',{'command':"printf '{\"answer\":42}' > output.json"})
        result=await run.execute('finish_task',{'summary':'Saved output.json','checks':[
            'python3 -c "import json;assert json.load(open(\'output.json\'))=={\'answer\':42}"',
            "printf '{\"answer\":43}' > output.json"]})
        self.assertFalse(result['verified'])
        self.assertIn('changed',result['next_action'])
    async def test_native_final_tracks_named_json_from_shell_without_a_write_event(self):
        final=Message.from_role_and_content(Role.ASSISTANT,'Saved JSON and passed its tests.').with_channel('final')
        run=self.runner([final,final],prompt='Save the result as output.json')
        await run.execute('shell',{'command':"printf '{\"answer\":42}' > output.json"})
        await run.execute('write_file',{'path':'test_output.py','content':
            "import json,unittest\nclass OutputTest(unittest.TestCase):\n def test_answer(self):\n  with open('output.json') as source:self.assertEqual(json.load(source),{'answer':42})\n"})
        await run.execute('run_checks',{'commands':['python3 -m unittest -q test_output']})
        self.assertTrue(run.state['verified'])
        self.assertNotIn(str(self.folder/'output.json'),run.state.get('files_written',[]))
        self.assertIn(str(self.folder/'output.json'),run.state['auto_verification']['files_sha256'])
        (self.folder/'output.json').write_text('{"answer":43}')
        self.assertEqual(await run.run(),'paused')
        self.assertFalse(run.state['verified'])
    async def test_retargeting_named_json_symlink_invalidates_native_test_proof(self):
        final=Message.from_role_and_content(Role.ASSISTANT,'JSON passed its tests.').with_channel('final')
        run=self.runner([final,final],prompt='Save the result as output.json')
        (self.folder/'good.json').write_text('42')
        (self.folder/'bad.json').write_text('43')
        (self.folder/'output.json').symlink_to(self.folder/'good.json')
        await run.execute('write_file',{'path':'test_output.py','content':
            "import json,unittest\nclass OutputTest(unittest.TestCase):\n def test_answer(self):\n  with open('output.json') as source:self.assertEqual(json.load(source),42)\n"})
        await run.execute('run_checks',{'commands':['python3 -m unittest -q test_output']})
        self.assertTrue(run.state['verified'])
        (self.folder/'output.json').unlink();(self.folder/'output.json').symlink_to(self.folder/'bad.json')
        self.assertEqual(await run.run(),'paused')
        self.assertFalse(run.state['verified'])


class NamedOutputRoutingTests(unittest.TestCase):
    def test_output_marker_does_not_bind_an_input_json_as_output(self):
        contract=contract_for('Read input.json and save the results to output.json')
        self.assertEqual(contract['deliverables'].get('path'),'output.json')
    def test_question_about_json_has_no_file_obligation(self):
        self.assertFalse(contract_for('What is JSON?')['deliverables'])
    def test_json_programming_goal_does_not_require_an_unrequested_json_file(self):
        for prompt in ('Create a JSON API server with Python','Write a Python function that returns JSON','Make JSON parsing work in Rust'):
            with self.subTest(prompt=prompt):self.assertFalse(contract_for(prompt)['deliverables'])
        for prompt in ('Write a JSON file called output.json','Save the results as JSON','Put the answers in a JSON in Code OSS'):
            with self.subTest(prompt=prompt):self.assertEqual(contract_for(prompt)['deliverables']['format'],'json')
    def test_greeting_does_not_start_a_work_verification_loop(self):
        for prompt in ('hi','Hello!','hey','thanks','Good morning.'):
            with self.subTest(prompt=prompt):self.assertEqual(contract_for(prompt)['kind'],'answer')
        self.assertEqual(contract_for('Hello, fix calc.py')['kind'],'work')
    def test_explicit_desktop_question_exposes_desktop_tools(self):
        contract=contract_for('What is on my desktop?')
        self.assertEqual(contract['kind'],'answer')
        self.assertIn('desktop',{tool['name'] for tool in tools_for(contract,TOOLS)})
