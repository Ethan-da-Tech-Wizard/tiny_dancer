# Program: tiny_dancer - coding_preflight.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Select bounded local baseline checks from actual project inspection.
# SPDX-License-Identifier: Apache-2.0
"""Select bounded local baseline checks from actual project inspection."""
# ---- Imports ----
from app.verification import test_command


# ---- Definitions ----
def baseline_commands(inspection, limit=3):
    """Step: baseline commands. Inputs: inspection, limit."""
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
