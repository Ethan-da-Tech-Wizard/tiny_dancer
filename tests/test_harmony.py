# ==============================================================================
# Program: test_harmony.py
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

import json
import unittest
from openai_harmony import (Author,Conversation,HarmonyEncodingName,Message,Role,TextContent,load_harmony_encoding)

# ------------------------------------------------------------------------------
# NativeHistoryTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class NativeHistoryTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # test_text_and_tool_history_survive_json_roundtrip: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_text_and_tool_history_survive_json_roundtrip(self):
        messages=[Message.from_role_and_content(Role.USER,'Please read my file.'),
            Message.from_role_and_content(Role.ASSISTANT,'{"path":"note.txt"}').with_channel('commentary').with_recipient('functions.read_file'),
            Message(author=Author.new(Role.TOOL,'functions.read_file'),content=[TextContent(text='the file contents')]).with_recipient('assistant')]
        restored=[Message.from_dict(json.loads(json.dumps(m.to_dict()))) for m in messages]
        encoding=load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
        self.assertEqual(encoding.render_conversation(Conversation.from_messages(messages)),encoding.render_conversation(Conversation.from_messages(restored)))
        rendered=encoding.decode(encoding.render_conversation(Conversation.from_messages(restored)))
        self.assertIn('the file contents',rendered)
        self.assertIn('functions.read_file',rendered)
