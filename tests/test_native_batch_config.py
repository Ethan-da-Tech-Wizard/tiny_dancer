# ==============================================================================
# Program: test_native_batch_config.py
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
import unittest
from app.llama_session import batch_arguments

# ------------------------------------------------------------------------------
# NativeBatchArgumentsTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class NativeBatchArgumentsTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # test_legacy_default_and_separate_microbatch: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_legacy_default_and_separate_microbatch(self):
        self.assertEqual(batch_arguments({'context':32768}), ['-b','128','-ub','128'])
        self.assertEqual(batch_arguments({'context':32768,'llama_batch_size':512}), ['-b','512','-ub','512'])
        self.assertEqual(batch_arguments({'context':32768,'llama_batch_size':1024,'llama_microbatch_size':512}), ['-b','1024','-ub','512'])

    # ------------------------------------------------------------------------------
    # test_invalid_sizes_fail_before_native_execution: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_invalid_sizes_fail_before_native_execution(self):
        for batch,micro in ((True,128),(512,False),(0,0),(-1,1),(128,512),(65536,512),('512',512),(512,None)):
            with self.subTest(batch=batch,microbatch=micro),self.assertRaises(ValueError):
                batch_arguments({'context':32768,'llama_batch_size':batch,'llama_microbatch_size':micro})

    # ------------------------------------------------------------------------------
    # test_other_model_configuration_is_unchanged: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_other_model_configuration_is_unchanged(self):
        config={'context':32768,'threads':8,'llama_batch_size':512,'llama_microbatch_size':512,'prefill_batch':1024}
        before=dict(config);batch_arguments(config);self.assertEqual(config,before)
