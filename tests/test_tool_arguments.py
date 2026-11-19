# ==============================================================================
# Program: test_tool_arguments.py
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

# SPDX-License-Identifier: Apache-2.0
"""Native malformed-call recovery with unchanged command values and audit."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

from openai_harmony import Message, Role
from app.agent import AgentRun
from app.tool_arguments import parse_tool_arguments
from app.tools import ComputerTools, ROOT
from tests.test_agent import ScriptedEngine, call


# ------------------------------------------------------------------------------
# ToolArgumentDecodingTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class ToolArgumentDecodingTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # repaired: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def repaired(self, text):
        try:
            args, repair = parse_tool_arguments(text)
        except (ValueError, TypeError) as exc:
            self.fail('Observed harmless closer defect still prevents decoding: ' + str(exc))
        self.assertIsNotNone(repair)
        return args, repair

    # ------------------------------------------------------------------------------
    # test_valid_nested_json_stays_unchanged: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_valid_nested_json_stays_unchanged(self):
        original = {'commands': ['printf "]}"', 'echo \\\\'], 'nested': {'array': [1, None, {'x': True}]}}
        args, repair = parse_tool_arguments(json.dumps(original))
        self.assertEqual(args, original)
        self.assertIsNone(repair)

    # ------------------------------------------------------------------------------
    # test_observed_native_shell_closer_preserves_exact_command: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_observed_native_shell_closer_preserves_exact_command(self):
        command = "python - <<'PY'\nfrom decimal import Decimal\nprint(str(Decimal('1.2').quantize(Decimal('0.00'))))\nprint(str(Decimal('1').quantize(Decimal('0.00'))))\nPY"
        original = json.dumps({'command': command}, separators=(',', ':'))
        bad = original[:-1] + ']}'
        args, repair = self.repaired(bad)
        self.assertEqual(args, {'command': command})
        self.assertEqual(repair['removed_at'], len(bad) - 2)
        self.assertEqual(repair['kind'], 'removed_unmatched_final_array_closer')

    # ------------------------------------------------------------------------------
    # test_unicode_quotes_newlines_and_brackets_inside_values_survive: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_unicode_quotes_newlines_and_brackets_inside_values_survive(self):
        original = {'content': 'snowman ☃; literal ]}; quote "; newline\n; slash \\', 'path': 'bracket].txt'}
        bad = json.dumps(original, ensure_ascii=False)[:-1] + '] \n } \t'
        args, repair = self.repaired(bad)
        self.assertEqual(args, original)
        self.assertEqual(bad[repair['removed_at']], ']')

    # ------------------------------------------------------------------------------
    # test_legitimate_nested_array_then_extra_closer_is_unambiguous: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_legitimate_nested_array_then_extra_closer_is_unambiguous(self):
        original = {'commands': ['true', 'printf "]}"'], 'timeout': 120}
        args, _ = self.repaired(json.dumps(original)[:-1] + ']}')
        self.assertEqual(args, original)

    # ------------------------------------------------------------------------------
    # test_other_corruption_never_gets_guessed: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_other_corruption_never_gets_guessed(self):
        for text in ('{"command":"true"]]}', '{"command":"true"', '{"command":true,}', '{"command":"true"} trailing', '{"command":"unescaped\nnewline"]}', '{"command": "unterminated]}'):
            with self.subTest(text=text), self.assertRaises(json.JSONDecodeError):
                parse_tool_arguments(text)

    # ------------------------------------------------------------------------------
    # test_duplicate_fields_prevent_repair: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_duplicate_fields_prevent_repair(self):
        with self.assertRaises(json.JSONDecodeError):
            parse_tool_arguments('{"command":"safe","command":"different"]}')

    # ------------------------------------------------------------------------------
    # test_non_object_inputs_remain_rejected: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_non_object_inputs_remain_rejected(self):
        for text in ('[]', '["true"]', 'null', '42', '"string"'):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, 'must be an object'):
                parse_tool_arguments(text)


# ------------------------------------------------------------------------------
# ToolArgumentRunnerTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class ToolArgumentRunnerTests(unittest.IsolatedAsyncioTestCase):
    # ------------------------------------------------------------------------------
    # asyncSetUp: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'workspace')
        self.folder = Path(self.temp.name)
        self.tools = ComputerTools()
        self.messages = []
        self.events = []

    # ------------------------------------------------------------------------------
    # asyncTearDown: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def asyncTearDown(self):
        await self.tools.close()
        self.temp.cleanup()

    # ------------------------------------------------------------------------------
    # raw: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def raw(self, name, body):
        return Message.from_role_and_content(Role.ASSISTANT, body).with_channel('commentary').with_recipient('functions.' + name)

    # ------------------------------------------------------------------------------
    # runner: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def runner(self, actions):
        request = SimpleNamespace(prompt='Create and verify result.txt', mode='agent', max_tokens=1024, run_until_done=True)
        return AgentRun(ScriptedEngine(actions), self.tools, str(self.folder), request,
            lambda: self.messages, lambda message, role=None: self.messages.append(message.to_dict()),
            lambda kind, data: self.events.append((kind, data)), lambda *args: None, threading.Event())

    # ------------------------------------------------------------------------------
    # test_actual_repaired_command_runs_once_and_original_call_is_audited: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_actual_repaired_command_runs_once_and_original_call_is_audited(self):
        command = "printf verified > result.txt"
        body = json.dumps({'command': command})[:-1] + ']}'
        finish = call('finish_task', {'summary': 'Created and checked file', 'checks': ["python -c \"from pathlib import Path; assert Path('result.txt').read_text() == 'verified'\""]})
        run = self.runner([self.raw('shell', body), finish, finish, finish, finish])
        self.assertEqual(await run.run(), 'complete')
        self.assertEqual((self.folder / 'result.txt').read_text(), 'verified')
        starts = [data for kind, data in self.events if kind == 'tool_start' and data['name'] == 'shell']
        self.assertEqual(len(starts), 1)
        self.assertEqual(starts[0]['arguments'], body)
        repairs = [data for kind, data in self.events if kind == 'tool_arguments_repaired']
        self.assertEqual(len(repairs), 1)
        self.assertEqual(repairs[0]['repair']['removed_at'], len(body) - 2)
        outcome = next(json.loads(data['result']) for kind, data in self.events if kind == 'tool_result' and data['name'] == 'shell')
        self.assertEqual(outcome['exit_code'], 0)
        self.assertEqual(outcome['argument_repair'], {'kind': 'removed_unmatched_final_array_closer', 'values_unchanged': True})

    # ------------------------------------------------------------------------------
    # test_ambiguous_command_cannot_execute: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_ambiguous_command_cannot_execute(self):
        body = json.dumps({'command': 'touch must-not-exist.txt'})[:-1] + ']]}'
        finish = call('finish_task', {'summary': 'Rejected malformed command', 'checks': ['test ! -e must-not-exist.txt']})
        run = self.runner([self.raw('shell', body), finish])
        self.assertEqual(await run.run(), 'complete')
        self.assertFalse((self.folder / 'must-not-exist.txt').exists())
        self.assertFalse(any(kind == 'tool_arguments_repaired' for kind, data in self.events))

    # ------------------------------------------------------------------------------
    # test_repair_positions_do_not_defeat_repeated_failure_guard: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_repair_positions_do_not_defeat_repeated_failure_guard(self):
        actions = []
        for space in ('', ' ', '  ', '   ', '    ', '     ', '      ', '       '):
            body = json.dumps({'command': 'exit 1'})[:-1] + space + ']}'
            actions.append(self.raw('shell', body))
        run = self.runner(actions)
        self.assertEqual(await run.run(), 'paused')
        self.assertEqual(run.state['turns'], 4)
        self.assertFalse(run.state['verified'])
        self.assertEqual(sum(kind == 'tool_arguments_repaired' for kind, data in self.events), 4)


if __name__ == '__main__':
    unittest.main()
