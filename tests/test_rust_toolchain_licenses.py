# SPDX-License-Identifier: Apache-2.0
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.rust_toolchain_licenses import collect_rust_entries,verify_rust_versions


class RustLicenseTests(unittest.TestCase):
    def test_missing_toolchain_is_not_invented(self):
        with patch('scripts.rust_toolchain_licenses.shutil.which',return_value=None):
            self.assertEqual(collect_rust_entries('/unused',lambda *args:None),[])

    def test_partial_toolchain_rejected(self):
        with patch('scripts.rust_toolchain_licenses.shutil.which',side_effect=lambda name:'/bin/rustc' if name=='rustc' else None):
            with self.assertRaisesRegex(RuntimeError,'Incomplete'):collect_rust_entries('/unused',lambda *args:None)

    def test_changed_version_rejected(self):
        with patch('scripts.rust_toolchain_licenses.tool_version',return_value='2.0'):
            with self.assertRaisesRegex(RuntimeError,'version changed'):verify_rust_versions([{'name':'cargo','version':'1.96.0'}])

    def test_existing_version_and_unrelated_tools_accepted(self):
        with patch('scripts.rust_toolchain_licenses.tool_version',return_value='1.96.0') as version:
            verify_rust_versions([{'name':'cargo','version':'1.96.0'},{'name':'bash','version':'5'}])
        version.assert_called_once_with('cargo')

    def test_tampered_pinned_rustup_license_rejected(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root/'run') as d:
            base=Path(d);folder=base/'licenses/system/rustup';folder.mkdir(parents=True)
            license_path=folder/'LICENSE-MIT';license_path.write_text('changed')
            (folder/'upstream-source.json').write_text(json.dumps({'version':'1.29.0','files':[{'path':str(license_path.relative_to(base)),'sha256':hashlib.sha256(b'original').hexdigest()}]}))
            with patch('scripts.rust_toolchain_licenses.shutil.which',return_value='/bin/tool'),patch('scripts.rust_toolchain_licenses.subprocess.check_output',return_value=d),patch('scripts.rust_toolchain_licenses.tool_version',return_value='1.29.0'):
                with self.assertRaisesRegex(RuntimeError,'differs'):collect_rust_entries(base,lambda *args:{})


if __name__=='__main__':unittest.main()
