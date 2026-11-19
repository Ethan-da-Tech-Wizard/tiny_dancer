# ==============================================================================
# Program: test_pi_baseline.py
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
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from scripts.pi_baseline import child_environment, models_config, public_event


# ------------------------------------------------------------------------------
# PiBaselineTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class PiBaselineTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # test_private_drafts_and_thinking_are_not_emitted: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_private_drafts_and_thinking_are_not_emitted(self):
        event = {'type':'message_end','message':{'role':'assistant','stopReason':'stop',
                 'content':[{'type':'thinking','thinking':'secret reasoning'}, {'type':'text','text':'unverified answer'}],
                 'usage':{'input':12,'output':34,'unexpected':'private'}}}
        encoded = json.dumps(public_event(event))
        self.assertNotIn('secret', encoded)
        self.assertNotIn('unverified', encoded)
        self.assertNotIn('unexpected', encoded)
        self.assertEqual(public_event(event)['private_characters'], 16)
        self.assertIsNone(public_event({'type':'message_update','message':event['message']}))
        self.assertEqual(public_event({'type':'agent_end','messages':[event['message']]}), {'type':'agent_end'})

    # ------------------------------------------------------------------------------
    # test_only_completed_tool_calls_and_results_are_public: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_only_completed_tool_calls_and_results_are_public(self):
        self.assertEqual(public_event({'type':'tool_execution_start','toolName':'bash','args':{'command':'pytest'}})['args'], {'command':'pytest'})
        value = public_event({'type':'tool_execution_end','result':{'content':[{'type':'text','text':'7 passed'}, {'type':'image','data':'private-image'}]}})
        self.assertEqual(value['result_text'], '7 passed')
        self.assertIsNone(public_event({'type':'tool_execution_update','partialResult':'unfinished'}))

    # ------------------------------------------------------------------------------
    # test_cloud_keys_proxy_and_shell_hooks_not_inherited: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_cloud_keys_proxy_and_shell_hooks_not_inherited(self):
        with patch.dict('os.environ', {'OPENAI_API_KEY':'cloud-secret','HTTP_PROXY':'proxy','BASH_ENV':'inject'}):
            env = child_environment(Path('/project'), Path('/project/run/pi'), 'local-secret')
        for key in ('OPENAI_API_KEY','HTTP_PROXY','BASH_ENV'):
            self.assertNotIn(key, env)
        self.assertEqual(env['TINY_DANCER_TEST_API_KEY'], 'local-secret')
        self.assertEqual(env['PI_OFFLINE'], '1')

    # ------------------------------------------------------------------------------
    # test_local_provider_canonical_sampler_and_large_context: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_local_provider_canonical_sampler_and_large_context(self):
        for url in ('https://example.com','http://localhost:3210','http://user:pass@127.0.0.1'):
            with self.assertRaises(ValueError): models_config(url)
        provider = models_config('http://127.0.0.1:12345')['providers']['tiny-local']
        self.assertEqual(provider['apiKey'], '$TINY_DANCER_TEST_API_KEY')
        model = provider['models'][0]
        self.assertEqual(model['maxTokens'], model['contextWindow'])
        self.assertEqual(model['samplingParams']['repeat_penalty'], 1.0)
        self.assertFalse(model['compat']['requiresThinkingAsText'])
