# SPDX-License-Identifier: Apache-2.0
"""Keep previous task instructions out of a new goal, without deleting history."""
import json
from openai_harmony import Message, Role


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
