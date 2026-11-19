# ==============================================================================
# Program: test_finish_context.py
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
"""A factual final review can finish, remain open, or reject stale evidence."""
import json
import unittest
from openai_harmony import Message,Role
from tests.test_post_edit_checks import PostEditCheckTests
from tests.test_agent import call


# ------------------------------------------------------------------------------
# FinishContextTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class FinishContextTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=PostEditCheckTests.asyncSetUp
    asyncTearDown=PostEditCheckTests.asyncTearDown
    runner=PostEditCheckTests.runner
    prepare=PostEditCheckTests.prepare

    # ------------------------------------------------------------------------------
    # passing: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def passing(self,run):
        await self.prepare(run)
        await run.execute('write_file',{'path':'program.py','content':'def add(a,b):return a+b\n'})
        await run.check_after_edit()
        self.assertTrue(run.state['verified'])

    # ------------------------------------------------------------------------------
    # test_actual_pass_gets_goal_review_and_native_final_not_host_final: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_actual_pass_gets_goal_review_and_native_final_not_host_final(self):
        final=Message.from_role_and_content(Role.ASSISTANT,'Implemented and tested.').with_channel('final')
        run=self.runner([call('write_file',{'path':'program.py','content':'def add(a,b):return a+b\n'}),final])
        await self.prepare(run)
        self.assertEqual(await run.run(),'complete')
        self.assertEqual(run.state['completion_reviews'],1)
        self.assertEqual(run.state['completion_path'],'tested_native_final')
        prompt=json.dumps(run.prompt_history())
        self.assertIn('Review the original goal',prompt)
        self.assertIn('concise final',prompt)

    # ------------------------------------------------------------------------------
    # test_failed_real_check_never_enters_finish_review: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_failed_real_check_never_enters_finish_review(self):
        run=self.runner();await self.prepare(run)
        await run.review_completion()
        self.assertFalse(run.state['verified'])
        self.assertNotIn('completion_reviews',run.state)

    # ------------------------------------------------------------------------------
    # test_missing_requested_file_blocks_finish_review: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_missing_requested_file_blocks_finish_review(self):
        run=self.runner();run.contract['deliverables']={'json':True,'path':'report.json'}
        await self.prepare(run)
        await run.execute('write_file',{'path':'program.py','content':'def add(a,b):return a+b\n'})
        await run.check_after_edit();await run.review_completion()
        self.assertFalse(run.state['verified'])
        self.assertNotIn('completion_reviews',run.state)

    # ------------------------------------------------------------------------------
    # test_same_verified_files_get_one_review_and_external_change_invalidates: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_same_verified_files_get_one_review_and_external_change_invalidates(self):
        run=self.runner();await self.passing(run)
        await run.review_completion();await run.review_completion()
        self.assertEqual(run.state['completion_reviews'],1)
        (self.folder/'program.py').write_text('def add(a,b):return a-b\n')
        await run.review_completion()
        self.assertFalse(run.state['verified'])
        self.assertNotIn('auto_verification',run.state)
        self.assertEqual(run.state['completion_reviews'],1)

    # ------------------------------------------------------------------------------
    # test_pending_step_remains_open_then_can_be_reviewed_when_done: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_pending_step_remains_open_then_can_be_reviewed_when_done(self):
        run=self.runner();await self.passing(run)
        run.state['steps']=[{'title':'Check the requested signed case','done':False}]
        await run.review_completion()
        self.assertNotIn('completion_reviews',run.state)
        run.state['steps'][0]['done']=True
        await run.review_completion()
        self.assertEqual(run.state['completion_reviews'],1)

    # ------------------------------------------------------------------------------
    # test_recovery_reason_is_in_model_context_not_only_ui_event: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_recovery_reason_is_in_model_context_not_only_ui_event(self):
        run=self.runner()
        run.compact_context('CONTROL_REASON_SENTINEL: repair the actual failed assertions.')
        self.assertIn('CONTROL_REASON_SENTINEL',json.dumps(run.prompt_history()))

    # ------------------------------------------------------------------------------
    # test_success_review_preserves_history_instead_of_rebuilding_the_prompt: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_success_review_preserves_history_instead_of_rebuilding_the_prompt(self):
        run=self.runner();await self.passing(run)
        before=list(run.prompt_history());compactions=run.state.get('context_compactions',0)
        await run.review_completion()
        self.assertIsNone(run.compacted_history)
        self.assertEqual(run.state.get('context_compactions',0),compactions)
        self.assertEqual(run.prompt_history()[:len(before)],before)
        self.assertIn('Review the original goal',json.dumps(run.prompt_history()[len(before):]))


del PostEditCheckTests
