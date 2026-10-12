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


class TaskDateCacheTests(unittest.TestCase):
    def setup(self):
        engine, _, calls = reserve_fixtures.OutputReserveTests().setup_engine()
        keeps = []
        original = engine.session.turn
        def turn(ids, maximum, keep, callback, temperature=0):
            keeps.append(keep)
            return original(ids, maximum, keep, callback, temperature)
        engine.session.turn = turn
        goal = 'Repair main.py and run tests.'
        history = [Message.from_role_and_content(Role.USER, goal).to_dict()]
        return engine, calls, keeps, history, contract_for(goal)

    def test_same_task_reuses_its_prefix_across_midnight(self):
        engine, calls, keeps, history, contract = self.setup()
        contract['today'] = '2026-10-10'
        clock = SimpleNamespace(today=Mock(side_effect=[date(2026,10,10), date(2026,10,11)]))
        with patch('app.engine.date', clock):
            for _ in range(2):
                engine.generate(history, '/project', lambda *a: None, threading.Event(), True, 2048, reasoning_effort='medium', task_contract=contract)
        self.assertGreaterEqual(keeps[1], calls[0]['prompt_tokens'] - 2)
        self.assertEqual(calls[1]['maximum'], 2048)

    def test_new_task_uses_its_own_date_not_an_older_task_anchor(self):
        engine, calls, _, history, contract = self.setup()
        contract['today'] = '2026-10-11'
        with patch('app.engine.date', SimpleNamespace(today=Mock(return_value=date(2026,10,12)))):
            engine.generate(history, '/project', lambda *a: None, threading.Event(), True, 2048, reasoning_effort='medium', task_contract=contract)
        self.assertIn('Current date: 2026-10-11', calls[0]['text'])

    def test_missing_date_anchor_uses_the_current_local_date(self):
        engine, calls, _, history, contract = self.setup()
        contract.pop('today')
        with patch('app.engine.date', SimpleNamespace(today=Mock(return_value=date(2026,10,12)))):
            engine.generate(history, '/project', lambda *a: None, threading.Event(), True, 2048, reasoning_effort='medium', task_contract=contract)
        self.assertIn('Current date: 2026-10-12', calls[0]['text'])


if __name__ == '__main__':
    unittest.main()
