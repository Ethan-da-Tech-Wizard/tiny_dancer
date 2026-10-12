# SPDX-License-Identifier: Apache-2.0
"""Batch readable sources without hiding the implementation or losing bounds."""
import json
import tempfile
import threading
import unittest
from pathlib import Path

from openai_harmony import Message, Role
from app.batching import inspect_project
from app.prompting import compact_result
from app.engine import ContextBudgetError
from tests import test_output_reserve as reserve_fixtures

ROOT = Path(__file__).resolve().parents[1]


def source(label, size):
    begin = '# ' + label + '_START\n'
    middle = '# ' + label + '_MIDDLE\n'
    end = '# ' + label + '_END\n'
    half = (size - len(begin + middle + end)) // 2
    return begin + '# sample\n' * (half // 9) + middle + '# sample\n' * (half // 9) + end


class InspectionSourceBatchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'workspace')
        self.folder = Path(self.temp.name)
        (self.folder / 'tests').mkdir()
        self.files = {
            'main.py': source('IMPLEMENTATION', 3500),
            'test_acceptance.py': source('ACCEPTANCE', 1800),
            'tests/test_cli.py': source('CLI_TEST', 1300),
            'tests/test_errors.py': source('ERROR_TEST', 1250),
        }
        for name, text in self.files.items():
            (self.folder / name).write_text(text)

    async def asyncTearDown(self):
        self.temp.cleanup()

    async def inspection(self):
        return await inspect_project({'files': []}, str(self.folder), self.folder / 'artifacts')

    async def test_actual_inspection_and_engine_keep_four_modest_sources_complete(self):
        result = await self.inspection()
        preview = compact_result(result)
        actual = {str(Path(f['path']).relative_to(self.folder)): f['text'] for f in preview['files']}
        self.assertEqual(actual, self.files)
        self.assertTrue(result['runtime']['version'])

    async def test_large_files_have_shared_bound_and_full_saved_evidence(self):
        names = []
        for index in range(8):
            name = f'large{index}.py'; names.append(name)
            (self.folder / name).write_text(source(f'LARGE_{index}', 10000))
        result = await inspect_project({'files': names}, str(self.folder), self.folder / 'artifacts')
        preview = compact_result(result)
        self.assertLessEqual(sum(len(f.get('text', '')) for f in preview['files']), 8000)
        self.assertTrue(all(len(f.get('text', '')) <= 6000 for f in preview['files']))
        self.assertIn('LARGE_0_END', preview['files'][0]['text'])
        self.assertTrue(all(f.get('preview_truncated') and f.get('read_hint') for f in preview['files']))
        saved = json.loads((self.folder / 'artifacts' / Path(result['artifact']).name).read_text())
        self.assertEqual(saved['files'][0]['text'], (self.folder / names[0]).read_text())

    async def test_preview_is_idempotent_and_does_not_mutate_original_sources(self):
        data = {'files': [{'path': name, 'text': text} for name, text in self.files.items()], 'artifact': '/artifacts/full.json'}
        original = json.dumps(data)
        first = compact_result(data)
        self.assertEqual([f['text'] for f in first['files']], list(self.files.values()))
        self.assertEqual(compact_result(first), first)
        self.assertEqual(json.dumps(data), original)

    async def test_exhausted_budget_explains_omission_and_preserves_file_errors(self):
        data = {'files': [{'path': f'{i}.py', 'text': 'x' * 4000} for i in range(3)] + [{'path': 'bad.py', 'error': 'Binary source'}]}
        preview = compact_result(data)
        self.assertEqual([len(f['text']) for f in preview['files'][:3]], [4000, 4000, 0])
        self.assertTrue(preview['files'][2]['preview_truncated'])
        self.assertIn('read_file', preview['files'][2]['read_hint'])
        self.assertEqual(preview['files'][3], data['files'][3])

    async def test_complete_small_project_fits_real_harmony_with_full_work_reply(self):
        result = await self.inspection()
        fixture = reserve_fixtures.OutputReserveTests()
        engine, _, calls = fixture.setup_engine()
        history = [Message.from_role_and_content(Role.USER, 'Repair main.py and run its project tests.').to_dict()]
        history.append(Message.from_role_and_content(Role.ASSISTANT, '{"files":[]}').with_channel('commentary').with_recipient('functions.inspect_project').to_dict())
        history.append(fixture.tool('inspect_project', result))
        engine.generate(history, str(self.folder), lambda *a: None, threading.Event(), True, 2048, reasoning_effort='medium')
        self.assertEqual(calls[-1]['maximum'], 2048)
        self.assertLessEqual(calls[-1]['prompt_tokens'] + 2048, 8192)
        for label in ('IMPLEMENTATION', 'ACCEPTANCE', 'CLI_TEST', 'ERROR_TEST'):
            self.assertIn(label + '_MIDDLE', calls[-1]['text'])

    async def test_character_bound_cannot_bypass_native_token_reserve(self):
        fixture = reserve_fixtures.OutputReserveTests()
        engine, _, calls = fixture.setup_engine()
        text = ''.join(chr(0x4e00 + i % 512) for i in range(3990))
        result = {'files': [{'path': f'{i}.py', 'text': text} for i in range(2)]}
        history = [Message.from_role_and_content(Role.USER, 'Repair main.py and run tests.').to_dict(), fixture.tool('inspect_project', result)]
        with self.assertRaises(ContextBudgetError):
            engine.generate(history, str(self.folder), lambda *a: None, threading.Event(), True, 2048, reasoning_effort='medium')
        self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
