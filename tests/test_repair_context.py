# ==============================================================================
# Program: test_repair_context.py
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
"""Failed repairs retain their prefix and real failure; capacity recovery remains."""
import json
import unittest
from openai_harmony import Message, Role
from tests.test_post_edit_checks import PostEditCheckTests, COMMAND
from tests.test_agent import call


# ------------------------------------------------------------------------------
# RepairContextTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class RepairContextTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=PostEditCheckTests.asyncSetUp
    asyncTearDown=PostEditCheckTests.asyncTearDown
    runner=PostEditCheckTests.runner
    prepare=PostEditCheckTests.prepare
    automatic_results=PostEditCheckTests.automatic_results
    # ------------------------------------------------------------------------------
    # test_failed_edit_keeps_prefix_goal_source_and_actual_failure: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_failed_edit_keeps_prefix_goal_source_and_actual_failure(self):
        run = self.runner()
        await self.prepare(run)
        self.messages.append(Message.from_role_and_content(Role.USER,run.request.prompt).to_dict())
        private = Message.from_role_and_content(Role.ASSISTANT, 'OLD_FAILED_ATTEMPT_SENTINEL').with_channel('analysis').to_dict()
        self.messages.append(private)
        self.messages.append(call('write_file',{'path':'program.py','content':'def add(a,b):\n    return 0\n'}).to_dict())
        prefix=list(self.messages)
        await run.execute('write_file', {'path': 'program.py', 'content': 'def add(a,b):\n    return 0\n'})
        await run.check_after_edit()
        prompt = json.dumps(run.prompt_history())
        self.assertEqual(run.prompt_history()[:len(prefix)],prefix)
        self.assertIn('OLD_FAILED_ATTEMPT_SENTINEL', prompt)
        self.assertIn('Implement a Python addition function', prompt)
        self.assertIn('return 0', prompt)
        self.assertIn('test_signed', prompt)
        self.assertFalse(run.state['verified'])
        self.assertEqual(run.state['repair_contexts'], 1)
        self.assertEqual(run.state.get('context_compactions',0),0)
        self.assertIsNone(run.compacted_history)
        self.assertIn(private, self.messages)  # Durable original history survives.
        await run.check_after_edit()
        self.assertEqual(run.state['repair_contexts'], 1)  # No repeat without an edit.

    # ------------------------------------------------------------------------------
    # test_failed_repair_cannot_keep_an_old_real_passing_receipt: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_failed_repair_cannot_keep_an_old_real_passing_receipt(self):
        run=self.runner();await self.prepare(run)
        await run.execute('write_file',{'path':'program.py','content':'def add(a,b):return a+b\n'})
        await run.check_after_edit()
        self.assertTrue(run.state['verified'])
        self.assertIn('auto_verification',run.state)
        (self.folder/'program.py').write_text('def add(a,b):return 0\n')
        await run.check_after_edit()
        self.assertFalse(run.state['verified'])
        self.assertNotIn('auto_verification',run.state)
        self.assertFalse(run.state['latest_project_checks']['passed'])
        self.assertEqual(run.state.get('context_compactions',0),0)

    # ------------------------------------------------------------------------------
    # test_second_distinct_failed_edit_refreshes_again_then_actual_pass_can_finish: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_second_distinct_failed_edit_refreshes_again_then_actual_pass_can_finish(self):
        final = Message.from_role_and_content(Role.ASSISTANT, 'Implemented and tested.').with_channel('final')
        run = self.runner([call('write_file', {'path':'program.py','content':'def add(a,b):\n    return a*b\n'}),
                           call('write_file', {'path':'program.py','content':'def add(a,b):\n    return a+b\n'}), final])
        await self.prepare(run)
        await run.execute('write_file', {'path':'program.py','content':'def add(a,b):\n    return 0\n'})
        self.assertEqual(await run.run(), 'complete')
        self.assertEqual(run.state['repair_contexts'], 2)
        self.assertTrue(run.state['verified'])
        self.assertEqual(len(self.automatic_results()), 3)

    # ------------------------------------------------------------------------------
    # test_passing_edit_does_not_refresh_context: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_passing_edit_does_not_refresh_context(self):
        run=self.runner(); await self.prepare(run)
        await run.execute('write_file', {'path':'program.py','content':'def add(a,b):\n    return a+b\n'})
        await run.check_after_edit()
        self.assertTrue(run.state['verified'])
        self.assertNotIn('repair_contexts', run.state)

    # ------------------------------------------------------------------------------
    # test_explicit_failed_test_in_same_edit_batch_also_refreshes: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_explicit_failed_test_in_same_edit_batch_also_refreshes(self):
        final=Message.from_role_and_content(Role.ASSISTANT,'Implemented and tested.').with_channel('final')
        run=self.runner([([call('write_file',{'path':'program.py','content':'def add(a,b):return 0\n'}),
                           call('run_checks',{'commands':[COMMAND]})],'RETURN'),
                         call('write_file',{'path':'program.py','content':'def add(a,b):return a+b\n'}),final])
        await self.prepare(run)
        self.assertEqual(await run.run(),'complete')
        self.assertEqual(run.state['repair_contexts'],1)
        self.assertTrue(run.state['verified'])
        self.assertNotIn('pending_repair_context',run.state)
        self.assertEqual(len(self.automatic_results()),1)  # No duplicate failed suite.

    # ------------------------------------------------------------------------------
    # test_repair_checkpoint_reserves_full_native_action: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_repair_checkpoint_reserves_full_native_action(self):
        import threading
        from tests.test_output_reserve import OutputReserveTests
        run=self.runner(); await self.prepare(run)
        source='def add(a,b):\n    return 0\n' + ''.join(f'# source context line {i}: observed current code\n' for i in range(95))
        await run.execute('write_file', {'path':'program.py','content':source})
        await run.check_after_edit()
        run.compact_context('Explicit recovery when the native context is full.')
        engine,encoding,calls=OutputReserveTests().setup_engine()
        engine.generate(run.prompt_history(),str(self.folder),lambda *a:None,threading.Event(),True,4096,
                        task_contract=run.contract,reasoning_effort='medium')
        self.assertLessEqual(calls[-1]['prompt_tokens']+4096,8192)
        self.assertIn('test_signed',calls[-1]['text'])
        self.assertIn('return 0',calls[-1]['text'])
        self.assertEqual(calls[-1]['maximum'],4096)


del PostEditCheckTests  # Discovery should not duplicate the imported base suite.
