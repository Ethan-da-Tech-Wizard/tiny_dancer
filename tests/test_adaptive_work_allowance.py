# ==============================================================================
# Program: test_adaptive_work_allowance.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Automated test suite verifying functional correctness, regression
#          resistance, boundary conditions, and edge cases. Automated regression and
#          functional assertion test suite verifying system stability, edge-case
#          resilience, and contract invariants. Exercises mathematical boundary
#          conditions, state graph branch coverage, and mock failure modes within
#          isolated execution fixtures. Enforces deterministic test assertions and
#          hermetic runtime lifecycle management.
# ==============================================================================

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

# ------------------------------------------------------------------------------
# AdaptiveWorkAllowanceTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class AdaptiveWorkAllowanceTests(unittest.IsolatedAsyncioTestCase):
 asyncSetUp=budget_fixtures.GenerationBudgetTests.asyncSetUp
 asyncTearDown=budget_fixtures.GenerationBudgetTests.asyncTearDown
 # ------------------------------------------------------------------------------
 # runner: Function Pipeline & Contract Specification
 # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
 # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
 # Failure Modes: Catches or propagates domain exceptions according to API contracts
 # ------------------------------------------------------------------------------
 def runner(self,actions=(),budget=None,checkpoint=None,context=8192):
  request=SimpleNamespace(prompt='Create result.py and test its behavior',mode='agent',max_tokens=budget,run_until_done=True)
  engine=ContinuingEngine(actions);engine.config['context']=context
  return AgentRun(engine,self.tools,self.temp.name,request,lambda:self.messages,
   lambda message,role=None:self.messages.append(message.to_dict()),lambda *args:None,lambda *args:None,threading.Event(),checkpoint)
 # ------------------------------------------------------------------------------
 # test_auto_work_retry_can_grow_after_current_initial_limit: Asynchronous Coroutine & Contract Specification
 # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
 # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
 # Failure Modes: Catches or propagates domain exceptions according to API contracts
 # ------------------------------------------------------------------------------
 async def test_auto_work_retry_can_grow_after_current_initial_limit(self):
  partial=call('write_file',{'path':'partial.py','content':'never run'})
  run=self.runner([([partial],'MAX_TOKENS'),call('write_file',{'path':'result.py','content':'answer=42\n'}),call('finish_task',{'summary':'Checked actual files','checks':['test -f result.py && test ! -f partial.py']})])
  self.assertEqual(await run.run(),'complete')
  self.assertEqual(run.engine.budgets,[2048,4096,4096])
  self.assertFalse((Path(self.temp.name)/'partial.py').exists())
 # ------------------------------------------------------------------------------
 # test_resume_restores_larger_learned_work_allowance: Asynchronous Coroutine & Contract Specification
 # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
 # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
 # Failure Modes: Catches or propagates domain exceptions according to API contracts
 # ------------------------------------------------------------------------------
 async def test_resume_restores_larger_learned_work_allowance(self):
  checkpoint={'generation_budget':{'requested':None,'initial':2048,'current':4096}}
  run=self.runner(checkpoint=checkpoint)
  self.assertEqual(run.current_max_tokens,4096)
  self.assertEqual(run.state['generation_budget'],checkpoint['generation_budget'])
 # ------------------------------------------------------------------------------
 # test_small_context_does_not_expand_past_half_capacity: Asynchronous Coroutine & Contract Specification
 # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
 # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
 # Failure Modes: Catches or propagates domain exceptions according to API contracts
 # ------------------------------------------------------------------------------
 async def test_small_context_does_not_expand_past_half_capacity(self):
  partial=call('write_file',{'path':'partial.py','content':'never run'})
  run=self.runner([([partial],'MAX_TOKENS'),call('finish_task',{'summary':'Partial file never executed','checks':['test ! -f partial.py']})],context=4096)
  self.assertEqual(await run.run(),'complete')
  self.assertEqual(run.engine.budgets,[2048,2048])
 # ------------------------------------------------------------------------------
 # test_larger_allowance_is_bounded_and_still_pauses_after_four_truncations: Asynchronous Coroutine & Contract Specification
 # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
 # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
 # Failure Modes: Catches or propagates domain exceptions according to API contracts
 # ------------------------------------------------------------------------------
 async def test_larger_allowance_is_bounded_and_still_pauses_after_four_truncations(self):
  partial=call('write_file',{'path':'partial.py','content':'never run'})
  run=self.runner([([partial],'MAX_TOKENS')]*4)
  self.assertEqual(await run.run(),'paused')
  self.assertEqual(run.engine.budgets,[2048,4096,4096,4096])
  self.assertFalse((Path(self.temp.name)/'partial.py').exists())

 # ------------------------------------------------------------------------------
 # test_smaller_resume_context_rejects_a_too_large_prior_allowance: Asynchronous Coroutine & Contract Specification
 # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
 # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
 # Failure Modes: Catches or propagates domain exceptions according to API contracts
 # ------------------------------------------------------------------------------
 async def test_smaller_resume_context_rejects_a_too_large_prior_allowance(self):
  checkpoint={'generation_budget':{'requested':None,'initial':2048,'current':4096}}
  run=self.runner(checkpoint=checkpoint,context=4096)
  self.assertEqual(run.current_max_tokens,2048)
 # ------------------------------------------------------------------------------
 # test_changed_numeric_choice_resets_the_learned_allowance: Asynchronous Coroutine & Contract Specification
 # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
 # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
 # Failure Modes: Catches or propagates domain exceptions according to API contracts
 # ------------------------------------------------------------------------------
 async def test_changed_numeric_choice_resets_the_learned_allowance(self):
  checkpoint={'generation_budget':{'requested':None,'initial':2048,'current':4096}}
  run=self.runner(budget=512,checkpoint=checkpoint)
  self.assertEqual(run.current_max_tokens,512)
