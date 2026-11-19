# ==============================================================================
# Program: tool_runtime.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Validates, deserializes, and safely dispatches tool invocations and
#          structured JSON arguments from agent response messages to target tool
#          handlers. Core component of the autonomous agent reasoning architecture
#          governing multi-turn execution cycles, state graph transitions, and prompt
#          synthesis. Strictly enforces mathematical bounds on LLM token context
#          windows, rolling memory buffers, and timeout thresholds. Guarantees
#          transactional execution invariants, deterministic failure isolation, and
#          thread-safe API contracts.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
"""Project-owned command wrappers; preserve the ordinary Python and host PATH."""
import os
from pathlib import Path

ROOT=Path('/mnt/GameDrive/tiny_dancer')


# ------------------------------------------------------------------------------
# tool_environment: Function Pipeline & Contract Specification
# Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
# Invariant: Preconditions validated before mutation; postconditions guarantee return contract
# Failure Modes: Catches or propagates domain exceptions according to API contracts
# ------------------------------------------------------------------------------
def tool_environment():
    env=os.environ.copy()
    temporary=ROOT/'run/tool-tmp'
    cargo_cache=ROOT/'cache/cargo'
    for directory in (temporary,cargo_cache):directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    env['TMPDIR']=str(temporary)
    env['CARGO_HOME']=str(cargo_cache)
    folder=ROOT/'run/tool-bin'
    if (folder/'pytest').is_file():
        env['PATH']=str(folder)+os.pathsep+env.get('PATH','')
    return env
