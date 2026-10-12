# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path
import tempfile
import unittest

from scripts.prepare_agent_feedback import prepare, public_evidence
from scripts.run_agent_feedback import valid_feedback
from app.batching import project_snapshot
from app.baseline_preview import baseline_preview
from app.native_chat import chat_history
from openai_harmony import Message, Role


class AgentFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / 'run')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'docs').mkdir(); (self.root / 'app').mkdir()
        self.report = self.root / 'docs/result.json'
        self.report.write_text(json.dumps({'status': 'complete', 'passed': False,
                                          'checks': {'instruction_retained': False}}))
        (self.root / 'app/example.py').write_text('value = 1\n')

    def test_only_public_selected_fields_leave_report(self):
        report = {'passed': False, 'status': 'complete', 'checks': {'real_check': False, 'private': 'SECRET'},
                  'checkpoint': {'messages': ['SECRET']}, 'reasoning': 'SECRET', 'finding': 'SECRET',
                  'errors': ['SECRET'], 'metrics': [{'analysis': 'SECRET'}],
                  'independent_checks': [{'check': 'observable requirement', 'passed': False, 'stderr': 'SECRET'}],
                  'tool_calls': [{'name': 'shell', 'arguments': {'command': 'SECRET'}}]}
        data = public_evidence(report)
        self.assertNotIn('SECRET', json.dumps(data))
        self.assertEqual(data['checks'], {'real_check': False})
        self.assertEqual(data['tool_counts'], {'shell': 1})

    def test_active_or_incomplete_evidence_cannot_start_review(self):
        for report in ({'status': 'running', 'passed': False}, {'status': 'complete'}, []):
            with self.assertRaises(ValueError): public_evidence(report)

    def test_copies_are_independent_and_manifest_preserves_original(self):
        folder = prepare(self.root, self.report, ['app/example.py'], 'Preserve required input')
        (folder / 'candidate/app/example.py').write_text('value = 2\n')
        self.assertEqual((self.root / 'app/example.py').read_text(), 'value = 1\n')
        self.assertEqual((folder / 'source/app/example.py').read_text(), 'value = 1\n')
        self.assertEqual(json.loads((folder / 'manifest.json').read_text())['sources'][0]['path'], 'app/example.py')
        self.assertIn('TD_REVIEW_SOURCE_ROOT', (folder / 'AGENTS.md').read_text())

    def test_private_paths_traversal_and_symlinks_are_rejected_before_creation(self):
        (self.root / 'app/link.py').symlink_to(self.root / 'app/example.py')
        for path in ('../outside.py', '/etc/passwd', 'run/private.py', 'app/link.py'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                prepare(self.root, self.report, [path], 'A requirement')
        self.assertFalse((self.root / 'workspace').exists())

    def test_external_report_and_empty_source_are_rejected(self):
        with self.assertRaises(ValueError): prepare(self.root, self.root / 'app/example.py', ['app/example.py'], 'A requirement')
        with self.assertRaises(ValueError): prepare(self.root, self.report, [], 'A requirement')

    def test_actual_initial_inspection_receives_brief_and_exact_paths(self):
        folder = prepare(self.root, self.report, ['app/example.py'], 'Preserve required input')
        inspection = project_snapshot({}, folder)
        readme = next(f for f in inspection['files'] if Path(f['path']).name == 'README.md')
        self.assertIn('Preserve required input', readme['text'])
        self.assertIn('candidate/app/example.py', readme['text'])
        self.assertIn('TD_REVIEW_SOURCE_ROOT', readme['text'])
        observation = baseline_preview('inspect_project', inspection)
        observation['origin'] = 'automatic_initial_project'
        message = Message.from_role_and_content(Role.TOOL, json.dumps(observation))
        message.author.name = 'inspect_project'
        converted = chat_history([message.to_dict()])
        self.assertEqual(converted[0]['role'], 'user')
        for required in ('Preserve required input', 'candidate/app/example.py', 'TD_REVIEW_SOURCE_ROOT'):
            self.assertIn(required, converted[0]['content'])

    def test_proposal_requires_concrete_evidence_change_and_test_command(self):
        data = {'verdict': 'proposal', 'summary': 'An instruction is absent',
                'evidence': ['missing marker check'], 'proposed_change': 'Handle the omitted role',
                'test_command': 'python -m pytest test_feedback.py', 'risks': [], 'limitations': ['Formatter only']}
        self.assertTrue(valid_feedback(data))
        for key in ('evidence', 'proposed_change', 'test_command'):
            changed = dict(data); changed[key] = [] if key == 'evidence' else ''
            self.assertFalse(valid_feedback(changed))

    def test_honest_no_change_is_valid_but_missing_or_wrong_fields_are_not(self):
        data = {'verdict': 'insufficient_evidence', 'summary': 'Need an observable failure',
                'evidence': [], 'proposed_change': '', 'test_command': '', 'risks': [], 'limitations': []}
        self.assertTrue(valid_feedback(data))
        for changed in ({}, None, dict(data, risks='none'), dict(data, verdict='approved')):
            self.assertFalse(valid_feedback(changed))


if __name__ == '__main__':
    unittest.main()
