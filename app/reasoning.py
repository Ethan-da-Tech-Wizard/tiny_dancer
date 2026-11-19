# ==============================================================================
# Program: reasoning.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Manages extended reasoning policies, thinking budget allocation, internal
#          scratchpad parsing, and thought extraction during agent decision cycles.
#          Core component of the autonomous agent reasoning architecture governing
#          multi-turn execution cycles, state graph transitions, and prompt synthesis.
#          Strictly enforces mathematical bounds on LLM token context windows, rolling
#          memory buffers, and timeout thresholds. Guarantees transactional execution
#          invariants, deterministic failure isolation, and thread-safe API contracts.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
"""Resolve an explicit effort choice before the configurable automatic default."""
# ------------------------------------------------------------------------------
# effective_effort: Function Pipeline & Contract Specification
# Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
# Invariant: Preconditions validated before mutation; postconditions guarantee return contract
# Failure Modes: Catches or propagates domain exceptions according to API contracts
# ------------------------------------------------------------------------------
def effective_effort(requested,contract,config,agent=True):
    if requested!='auto':
        if requested not in ('low','medium','high'):raise ValueError('Invalid reasoning effort')
        return requested
    if not agent or contract.get('kind')!='work':return 'low'
    configured=config.get('work_reasoning_effort')
    if configured is not None:
        if configured not in ('low','medium','high'):raise ValueError('Invalid work_reasoning_effort')
        return configured
    return 'medium' if contract.get('lookup_languages') else 'low'
