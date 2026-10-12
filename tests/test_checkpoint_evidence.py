# SPDX-License-Identifier: Apache-2.0
"""Reproduce expensive rolling and lost working evidence without native inference."""
import json
from pathlib import Path
import threading
import unittest
from openai_harmony import Author,Message,Role,TextContent
from app.engine import ContextBudgetError

class CheckpointRolloverTests(unittest.TestCase):
 def test_agent_overflow_requests_checkpoint_before_any_prefill(self):
  from tests.test_output_reserve import OutputReserveTests
  helper=OutputReserveTests();engine,encoding,calls=helper.setup_engine()
  history=[Message.from_role_and_content(Role.USER,'Repair code and run tests. ORIGINAL_GOAL_SENTINEL').to_dict()]
  for i in range(12):
   history.append(Message.from_role_and_content(Role.ASSISTANT,json.dumps({'path':f'source{i}.py'})).with_channel('commentary').with_recipient('functions.read_file').to_dict())
   text=''.join(f'{n}: value_{n} = '+('1234567890'*2)+'\n' for n in range(1,91))
   history.append(helper.tool('read_file',{'path':f'/project/source{i}.py','text':text}))
  unchanged=json.dumps(history)
  with self.assertRaises(ContextBudgetError):engine.generate(history,'/project',lambda *a:None,threading.Event(),True,2048,reasoning_effort='medium')
  self.assertEqual(calls,[]);self.assertEqual(json.dumps(history),unchanged)

class CheckpointEvidenceTests(unittest.IsolatedAsyncioTestCase):
 async def test_checkpoint_keeps_current_source_and_last_failed_tests_after_diagnostics(self):
  from tests.test_continuation import ContinuationTests
  helper=ContinuationTests();await helper.asyncSetUp();self.addAsyncCleanup(helper.asyncTearDown)
  run=helper.runner([]);source=Path(helper.temp.name)/'product.py';source.write_text('CURRENT_SOURCE_SENTINEL = 42\n')
  def tool(name,payload):return Message(author=Author.new(Role.TOOL,'functions.'+name),content=[TextContent(text=json.dumps(payload))]).with_recipient('assistant').to_dict()
  helper.messages.extend([tool('read_file',{'path':str(source),'text':'1: OLD_SOURCE_SENTINEL = 0\n'}),tool('run_checks',{'exit_code':1,'checks':[{'command':'python -m unittest','exit_code':1,'output':'FAILED test_boundary FAILURE_SENTINEL'}],'artifact':'/artifacts/failed-tests.json'}),tool('shell',{'exit_code':0,'output':'diagnostic 1'}),tool('shell',{'exit_code':0,'output':'diagnostic 2'})])
  run.state['sources']=[str(source)];run.state['last_failure']={'tool':'run_checks','exit_code':1,'artifact':'/artifacts/failed-tests.json'}
  run.compact_context('Context was full.');prompt=json.dumps(run.prompt_history())
  self.assertIn('CURRENT_SOURCE_SENTINEL',prompt);self.assertIn('FAILURE_SENTINEL',prompt);self.assertNotIn('OLD_SOURCE_SENTINEL',prompt)
  self.assertIn('Create and verify result.txt',prompt);self.assertEqual(source.read_text(),'CURRENT_SOURCE_SENTINEL = 42\n')
if __name__=='__main__':unittest.main()
