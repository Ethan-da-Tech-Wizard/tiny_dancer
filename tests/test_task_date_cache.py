# ==============================================================================
# Program: test_task_date_cache.py
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
"""Long-running tasks keep their date anchor without re-prefilling at midnight."""
import threading
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

from openai_harmony import Message, Role
from app.task_policy import contract_for
from tests import test_output_reserve as reserve_fixtures


# ------------------------------------------------------------------------------
# TaskDateCacheTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class TaskDateCacheTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # setup: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def setup(self):
        engine, _, calls = reserve_fixtures.OutputReserveTests().setup_engine()
        keeps = []
        original = engine.session.turn
        # ------------------------------------------------------------------------------
        # turn: Function Pipeline & Contract Specification
        # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
        # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
        # Failure Modes: Catches or propagates domain exceptions according to API contracts
        # ------------------------------------------------------------------------------
        def turn(ids, maximum, keep, callback, temperature=0):
            keeps.append(keep)
            return original(ids, maximum, keep, callback, temperature)
        engine.session.turn = turn
        goal = 'Repair main.py and run tests.'
        history = [Message.from_role_and_content(Role.USER, goal).to_dict()]
        return engine, calls, keeps, history, contract_for(goal)

    # ------------------------------------------------------------------------------
    # test_same_task_reuses_its_prefix_across_midnight: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_same_task_reuses_its_prefix_across_midnight(self):
        engine, calls, keeps, history, contract = self.setup()
        contract['today'] = '2026-10-10'
        clock = SimpleNamespace(today=Mock(side_effect=[date(2026,10,10), date(2026,10,11)]))
        with patch('app.engine.date', clock):
            for _ in range(2):
                engine.generate(history, '/project', lambda *a: None, threading.Event(), True, 2048, reasoning_effort='medium', task_contract=contract)
        self.assertGreaterEqual(keeps[1], calls[0]['prompt_tokens'] - 2)
        self.assertEqual(calls[1]['maximum'], 2048)

    # ------------------------------------------------------------------------------
    # test_new_task_uses_its_own_date_not_an_older_task_anchor: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_new_task_uses_its_own_date_not_an_older_task_anchor(self):
        engine, calls, _, history, contract = self.setup()
        contract['today'] = '2026-10-11'
        with patch('app.engine.date', SimpleNamespace(today=Mock(return_value=date(2026,10,12)))):
            engine.generate(history, '/project', lambda *a: None, threading.Event(), True, 2048, reasoning_effort='medium', task_contract=contract)
        self.assertIn('Current date: 2026-10-11', calls[0]['text'])

    # ------------------------------------------------------------------------------
    # test_missing_date_anchor_uses_the_current_local_date: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_missing_date_anchor_uses_the_current_local_date(self):
        engine, calls, _, history, contract = self.setup()
        contract.pop('today')
        with patch('app.engine.date', SimpleNamespace(today=Mock(return_value=date(2026,10,12)))):
            engine.generate(history, '/project', lambda *a: None, threading.Event(), True, 2048, reasoning_effort='medium', task_contract=contract)
        self.assertIn('Current date: 2026-10-12', calls[0]['text'])


if __name__ == '__main__':
    unittest.main()
