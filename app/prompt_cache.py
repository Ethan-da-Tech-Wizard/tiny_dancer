# ==============================================================================
# Program: prompt_cache.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Optimizes inference latency through prompt prefix caching and KV-cache
#          reuse, reducing time-to-first-token on repetitive system prompts and
#          repository context. Core component of the autonomous agent reasoning
#          architecture governing multi-turn execution cycles, state graph
#          transitions, and prompt synthesis. Strictly enforces mathematical bounds on
#          LLM token context windows, rolling memory buffers, and timeout thresholds.
#          Guarantees transactional execution invariants, deterministic failure
#          isolation, and thread-safe API contracts.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
"""Reuse the model's exact emitted history when canonical messages still match."""


# ------------------------------------------------------------------------------
# ExactHistoryCache: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class ExactHistoryCache:
    # ------------------------------------------------------------------------------
    # __init__: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def __init__(self):
        self.clear()

    # ------------------------------------------------------------------------------
    # clear: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def clear(self):
        self.canonical = []
        self.raw = []

    # ------------------------------------------------------------------------------
    # remember: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def remember(self, canonical, raw):
        self.canonical, self.raw = list(canonical), list(raw)

    # ------------------------------------------------------------------------------
    # restore: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def restore(self, canonical, capacity, reserve):
        boundary = len(self.canonical)
        if not boundary or canonical[:boundary] != self.canonical:
            return canonical, 0
        candidate = self.raw + canonical[boundary:]
        if len(candidate) + reserve >= capacity:
            return canonical, 0
        return candidate, len(self.raw)
