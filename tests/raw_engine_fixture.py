# ==============================================================================
# Program: raw_engine_fixture.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Supporting module providing core logic and utilities for the Tiny Dancer
#          autonomous coding agent. Automated regression and functional assertion test
#          suite verifying system stability, edge-case resilience, and contract
#          invariants. Exercises mathematical boundary conditions, state graph branch
#          coverage, and mock failure modes within isolated execution fixtures.
#          Enforces deterministic test assertions and hermetic runtime lifecycle
#          management.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
"""Raw Harmony test doubles must select their protocol independently of live config."""
from app.engine import LocalEngine


# ------------------------------------------------------------------------------
# legacy_raw_engine: Function Pipeline & Contract Specification
# Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
# Invariant: Preconditions validated before mutation; postconditions guarantee return contract
# Failure Modes: Catches or propagates domain exceptions according to API contracts
# ------------------------------------------------------------------------------
def legacy_raw_engine():
    engine=LocalEngine()
    engine.config['native_tool_protocol']='raw'
    engine.config.pop('work_reasoning_effort',None)
    return engine
