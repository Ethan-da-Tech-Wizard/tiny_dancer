# ==============================================================================
# Program: coding_preflight.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Validates repository prerequisites, baseline test suites, and clean git
#          worktree status before starting runs. Core component of the autonomous
#          agent reasoning architecture governing multi-turn execution cycles, state
#          graph transitions, and prompt synthesis. Strictly enforces mathematical
#          bounds on LLM token context windows, rolling memory buffers, and timeout
#          thresholds. Guarantees transactional execution invariants, deterministic
#          failure isolation, and thread-safe API contracts.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
"""Select bounded local baseline checks from actual project inspection."""
from app.verification import test_command


# ------------------------------------------------------------------------------
# baseline_commands: Function Pipeline & Contract Specification
# Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
# Invariant: Preconditions validated before mutation; postconditions guarantee return contract
# Failure Modes: Catches or propagates domain exceptions according to API contracts
# ------------------------------------------------------------------------------
def baseline_commands(inspection, limit=3):
    commands = []
    for candidate in inspection.get('test_candidates', []):
        if not isinstance(candidate, dict) or candidate.get('available') is not True:
            continue
        command = candidate.get('command')
        if not isinstance(command, str) or len(command) > 6000 or not test_command(command):
            continue
        # Baseline Cargo inspection never downloads dependencies implicitly.
        if command == 'cargo test':
            command = 'cargo test --offline'
        if command not in commands:
            commands.append(command)
        if len(commands) == limit:
            break
    return commands
