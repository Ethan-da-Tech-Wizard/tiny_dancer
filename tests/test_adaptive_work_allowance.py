# SPDX-License-Identifier: Apache-2.0
"""Scripted recovery boundaries; no native task or implementation injected."""
from pathlib import Path
import threading
from types import SimpleNamespace
from app.agent import AgentRun
from tests.test_continuation import ContinuingEngine
import unittest
import tests.test_generation_budget as budget_fixtures
from tests.test_agent import call

class AdaptiveWorkAllowanceTests(unittest.IsolatedAsyncioTestCase):
 asyncSetUp=budget_fixtures.GenerationBudgetTests.asyncSetUp
 asyncTearDown=budget_fixtures.GenerationBudgetTests.asyncTearDown
 def runner(self,actions=(),budget=None,checkpoint=None,context=8192):
  request=SimpleNamespace(prompt='Create result.py and test its behavior',mode='agent',max_tokens=budget,run_until_done=True)
  engine=ContinuingEngine(actions);engine.config['context']=context
  return AgentRun(engine,self.tools,self.temp.name,request,lambda:self.messages,
   lambda message,role=None:self.messages.append(message.to_dict()),lambda *args:None,lambda *args:None,threading.Event(),checkpoint)
 async def test_auto_work_retry_can_grow_after_current_initial_limit(self):
  partial=call('write_file',{'path':'partial.py','content':'never run'})
  run=self.runner([([partial],'MAX_TOKENS'),call('write_file',{'path':'result.py','content':'answer=42\n'}),call('finish_task',{'summary':'Checked actual files','checks':['test -f result.py && test ! -f partial.py']})])
  self.assertEqual(await run.run(),'complete')
  self.assertEqual(run.engine.budgets,[2048,4096,4096])
  self.assertFalse((Path(self.temp.name)/'partial.py').exists())
 async def test_resume_restores_larger_learned_work_allowance(self):
  checkpoint={'generation_budget':{'requested':None,'initial':2048,'current':4096}}
  run=self.runner(checkpoint=checkpoint)
  self.assertEqual(run.current_max_tokens,4096)
  self.assertEqual(run.state['generation_budget'],checkpoint['generation_budget'])
 async def test_small_context_does_not_expand_past_half_capacity(self):
  partial=call('write_file',{'path':'partial.py','content':'never run'})
  run=self.runner([([partial],'MAX_TOKENS'),call('finish_task',{'summary':'Partial file never executed','checks':['test ! -f partial.py']})],context=4096)
  self.assertEqual(await run.run(),'complete')
  self.assertEqual(run.engine.budgets,[2048,2048])
 async def test_larger_allowance_is_bounded_and_still_pauses_after_four_truncations(self):
  partial=call('write_file',{'path':'partial.py','content':'never run'})
  run=self.runner([([partial],'MAX_TOKENS')]*4)
  self.assertEqual(await run.run(),'paused')
  self.assertEqual(run.engine.budgets,[2048,4096,4096,4096])
  self.assertFalse((Path(self.temp.name)/'partial.py').exists())

 async def test_smaller_resume_context_rejects_a_too_large_prior_allowance(self):
  checkpoint={'generation_budget':{'requested':None,'initial':2048,'current':4096}}
  run=self.runner(checkpoint=checkpoint,context=4096)
  self.assertEqual(run.current_max_tokens,2048)
 async def test_changed_numeric_choice_resets_the_learned_allowance(self):
  checkpoint={'generation_budget':{'requested':None,'initial':2048,'current':4096}}
  run=self.runner(budget=512,checkpoint=checkpoint)
  self.assertEqual(run.current_max_tokens,512)
