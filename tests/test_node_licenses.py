# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path
import tempfile
import unittest
from scripts.node_licenses import collect_node, verify_node


class NodeLicenseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prefix = self.root / 'vendor/pi-runtime'
        self.package = self.prefix / 'node_modules/example'
        self.package.mkdir(parents=True)
        (self.package / 'package.json').write_text(json.dumps({'name':'example','version':'1.0.0','license':'MIT'}))
        (self.package / 'README.md').write_text('Permission is hereby granted: fixture license')
        (self.prefix / 'package-lock.json').write_text(json.dumps({'packages':{'node_modules/example':{'version':'1.0.0'}}}))

    def test_readme_license_is_preserved_and_verified(self):
        result = collect_node(self.root)
        self.assertEqual(len(result['packages']), 1)
        self.assertEqual(verify_node(self.root)['lock_sha256'], result['lock_sha256'])
        self.assertTrue(any(p['path'].endswith('README.md') for p in result['files']))

    def test_missing_notice_is_an_error(self):
        (self.package / 'README.md').unlink()
        with self.assertRaisesRegex(RuntimeError, 'Unresolved'):
            collect_node(self.root)

    def test_changed_lock_is_rejected(self):
        collect_node(self.root)
        with (self.prefix / 'package-lock.json').open('a') as handle:
            handle.write(' ')
        with self.assertRaisesRegex(RuntimeError, 'lock changed'):
            verify_node(self.root)

    def test_changed_notice_is_rejected(self):
        collect_node(self.root)
        (self.package / 'README.md').write_text('altered')
        with self.assertRaisesRegex(RuntimeError, 'notice missing or changed'):
            verify_node(self.root)
