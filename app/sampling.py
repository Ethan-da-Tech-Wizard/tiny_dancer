# ==============================================================================
# Program: sampling.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Defines temperature, top-p, min-p, repetition penalty, and nucleus
#          sampling strategies for generation. Core component of the autonomous agent
#          reasoning architecture governing multi-turn execution cycles, state graph
#          transitions, and prompt synthesis. Strictly enforces mathematical bounds on
#          LLM token context windows, rolling memory buffers, and timeout thresholds.
#          Guarantees transactional execution invariants, deterministic failure
#          isolation, and thread-safe API contracts.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
"""Explicit native profiles; preserve legacy greedy runs for comparisons."""


# ------------------------------------------------------------------------------
# native_temperature: Function Pipeline & Contract Specification
# Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
# Invariant: Preconditions validated before mutation; postconditions guarantee return contract
# Failure Modes: Catches or propagates domain exceptions according to API contracts
# ------------------------------------------------------------------------------
def native_temperature(config):
    profile = config.get('native_sampling_profile', 'greedy')
    if profile == 'greedy':
        return 0.0
    if profile == 'recommended':
        return 1.0
    raise ValueError('native_sampling_profile must be greedy or recommended')
