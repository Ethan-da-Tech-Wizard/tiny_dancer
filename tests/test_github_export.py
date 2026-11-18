# Program: tiny_dancer - tests/test_github_export.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Tests for github export (exercises scripts.export_github).
# SPDX-License-Identifier: Apache-2.0
"""Tests for github export (exercises scripts.export_github)."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.export_github import export, public_report, OMITTED


# -------- git hub export tests --------
class GitHubExportTests(unittest.TestCase):
    """Test group for git hub export."""
    def setUp(self):
        """Prepare the fixtures for each test."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.put('README.md', '# Example\n')
        self.put('app/main.py', 'print("hello")\n')
        self.put('licenses/LICENSE', 'Exact upstream notice.\n')

    def put(self, name, data):
        """Test helper: put."""
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
        return path

    def test_source_licenses_and_executable_exact_runtime_omitted(self):
        """Checks that source licenses and executable exact runtime omitted."""
        self.put('scripts/start.sh', '#!/bin/sh\nexit 0\n').chmod(0o755)
        for name in ['run/access-token', 'logs/private.log', 'workspace/file.py',
                     'models/model.gguf', 'cache/data', 'vendor/source', 'build/bin',
                     '.venv/pyvenv.cfg', 'docs/screenshot.png']:
            self.put(name, 'local-only-data')
        result = export(self.root)
        dest = Path(result['destination'])
        for name in ['README.md', 'app/main.py', 'licenses/LICENSE', 'scripts/start.sh']:
            self.assertEqual((dest/name).read_bytes(), (self.root/name).read_bytes())
        self.assertTrue((dest/'scripts/start.sh').stat().st_mode & 0o100)
        self.assertFalse((dest/'run').exists())
        self.assertFalse((dest/'docs/screenshot.png').exists())

    def test_reports_keep_failures_metrics_and_do_not_mutate_originals(self):
        """Checks that reports keep failures metrics and do not mutate originals."""
        original = {'status': 'failed', 'passed': False, 'checks': {'works': False},
                    'tests_run': 3, 'metrics': {'tokens': 42, 'seconds': 1.5},
                    'checkpoint': {'status': 'PRIVATE'},
                    'output': 'PRIVATE', 'reasoning': 'PRIVATE',
                    'unknown_future_field': 'PRIVATE', 'tokens': [1,2,3],
                    'results': [{'test': 'test_failure', 'status': 'failed', 'detail': 'PRIVATE'}]}
        src = self.put('docs/trial.json', json.dumps(original))
        before = src.read_bytes()
        dest = Path(export(self.root)['destination'])
        result = json.loads((dest/'docs/trial.json').read_text())
        self.assertFalse(result['passed'])
        self.assertEqual(result['checks'], {'works':False})
        self.assertEqual(result['metrics'], {'tokens':42, 'seconds':1.5})
        self.assertEqual(result['checkpoint'], {})
        self.assertEqual(result['results'][0]['status'], 'failed')
        self.assertNotIn('PRIVATE', (dest/'docs/trial.json').read_text())
        self.assertEqual(src.read_bytes(), before)

    def test_private_markers_omitted_even_in_metadata_strings(self):
        """Checks that private markers omitted even in metadata strings."""
        self.assertEqual(public_report({'name': '<think>private'}), {'name': OMITTED})
        self.assertEqual(public_report({'unknown': '{"checkpoint":"private"}'}), {'unknown': OMITTED})

    def test_credentials_refuse_entire_export_without_printing_value(self):
        """Checks that credentials refuse entire export without printing value."""
        secret = 'ghp_' + 'a' * 36
        self.put('app/accident.py', 'value = "'+secret+'"')
        with self.assertRaises(ValueError) as error:
            export(self.root)
        self.assertNotIn(secret, str(error.exception))
        self.assertFalse((self.root/'run/github/tiny_dancer').exists())

    def test_local_token_checked_even_without_recognized_token_format(self):
        """Checks that local token checked even without recognized token format."""
        secret = 'unique-local-' + 'z' * 32
        self.put('run/access-token', secret)
        self.put('docs/note.md', secret)
        with self.assertRaisesRegex(ValueError, 'Local credential'):
            export(self.root)

    def test_task_report_slug_is_not_misclassified_as_an_api_key(self):
        """Checks that task report slug is not misclassified as an api key."""
        self.put('docs/trial.json', json.dumps({'report':'docs/task-'+'long-name-'*5+'.json'}))
        self.assertGreater(export(self.root)['files'], 0)

    def test_symlinks_and_private_file_types_rejected(self):
        """Checks that symlinks and private file types rejected."""
        target = self.put('run/private', 'secret')
        link = self.root/'app/link.py'
        link.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            export(self.root)
        link.unlink()
        self.put('app/.env.local', 'TOKEN=secret')
        with self.assertRaisesRegex(ValueError, 'Private file type'):
            export(self.root)

    def test_repeat_export_updates_owned_files_preserving_git(self):
        """Checks that repeat export updates owned files preserving git."""
        dest = Path(export(self.root)['destination'])
        (dest/'.git').mkdir()
        (dest/'.git/keep').write_text('git metadata')
        self.put('app/main.py', 'print("updated")\n')
        (self.root/'licenses/LICENSE').unlink()
        export(self.root)
        self.assertEqual((dest/'app/main.py').read_text(), 'print("updated")\n')
        self.assertFalse((dest/'licenses/LICENSE').exists())
        self.assertEqual((dest/'.git/keep').read_text(), 'git metadata')

    def test_collaborator_edits_are_not_overwritten(self):
        """Checks that collaborator edits are not overwritten."""
        dest = Path(export(self.root)['destination'])
        (dest/'app/main.py').write_text('collaborator work')
        with self.assertRaisesRegex(ValueError, 'unreviewed local edits'):
            export(self.root)
        self.assertEqual((dest/'app/main.py').read_text(), 'collaborator work')

    def test_refuses_destination_outside_owned_publication_area(self):
        """Checks that refuses destination outside owned publication area."""
        with self.assertRaisesRegex(ValueError, 'run/github'):
            export(self.root, self.root/'app')

    def test_publication_directory_symlink_cannot_redirect_writes(self):
        """Checks that publication directory symlink cannot redirect writes."""
        dest = Path(export(self.root)['destination'])
        outside = self.root/'outside'
        outside.mkdir()
        (dest/'scripts').symlink_to(outside, target_is_directory=True)
        self.put('scripts/new.py', 'print("new")')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            export(self.root)
        self.assertFalse((outside/'new.py').exists())

    def test_manifest_cannot_remove_files_outside_checkout(self):
        """Checks that manifest cannot remove files outside checkout."""
        dest = Path(export(self.root)['destination'])
        path = dest/'docs/github-export-manifest.json'
        manifest = json.loads(path.read_text())
        manifest['files'].append({'path':'../../outside', 'export_sha256':'0'*64})
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'Invalid path'):
            export(self.root)

    def test_index_regenerated_instead_of_copying_raw_previews(self):
        """Checks that index regenerated instead of copying raw previews."""
        self.put('docs/TEST_RESULTS.md', 'PRIVATE <think> output')
        self.put('docs/fail.json', json.dumps({'status':'failed','passed':False,'tests_run':2}))
        dest = Path(export(self.root)['destination'])
        text = (dest/'docs/TEST_RESULTS.md').read_text()
        self.assertNotIn('PRIVATE', text)
        self.assertIn('failed | False | 2', text)
        manifest = json.loads((dest/'docs/github-export-manifest.json').read_text())
        self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), manifest['results_index_sha256'])


if __name__ == '__main__':
    unittest.main()
