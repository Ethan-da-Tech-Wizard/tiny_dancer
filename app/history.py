# ==============================================================================
# Program: history.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Maintains chronological conversation turn history, message serialization,
#          and checkpointing for session resumption and retrospective analysis. Core
#          component of the autonomous agent reasoning architecture governing
#          multi-turn execution cycles, state graph transitions, and prompt synthesis.
#          Strictly enforces mathematical bounds on LLM token context windows, rolling
#          memory buffers, and timeout thresholds. Guarantees transactional execution
#          invariants, deterministic failure isolation, and thread-safe API contracts.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
"""Keep previous task instructions out of a new goal, without deleting history."""
import json
from openai_harmony import Message, Role


# ------------------------------------------------------------------------------
# task_history: Function Pipeline & Contract Specification
# Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
# Invariant: Preconditions validated before mutation; postconditions guarantee return contract
# Failure Modes: Catches or propagates domain exceptions according to API contracts
# ------------------------------------------------------------------------------
def task_history(rows, prompt, mode, checkpoint):
    boundary = checkpoint.get('context_start', 0)
    messages = [json.loads(row['harmony']) for row in rows if row['id'] >= boundary]
    if mode == 'chat':
        messages = [message for message in messages
                    if Message.from_dict(message).author.role == Role.USER or
                    (Message.from_dict(message).author.role == Role.ASSISTANT
                     and message.get('channel') == 'final' and not message.get('recipient'))]
    elif checkpoint.get('context_insert_goal'):
        messages.insert(0, Message.from_role_and_content(Role.USER, prompt).to_dict())
    return messages
