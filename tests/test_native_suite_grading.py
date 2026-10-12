# SPDX-License-Identifier: Apache-2.0
"""Ensure withheld graders reject plausible incomplete or incorrect products."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.native_suite_cases import CASES, grade


class NativeSuiteGradingTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]
        self.temp=tempfile.TemporaryDirectory(dir=root/'run')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'run').mkdir()
        self.folder=self.root/'task';self.folder.mkdir()

    def inventory_fixture(self, skip_unreadable=False, wrong_digest=False):
        def invoke(args, **kwargs):
            source,out=map(Path,args[-2:])
            if not source.is_dir():return subprocess.CompletedProcess(args,1,'','invalid root')
            rows=[]
            for p in source.rglob('*'):
                if p.is_symlink() or not p.is_file() or p==out:continue
                if not p.stat().st_mode & 0o444:
                    if skip_unreadable:continue
                    return subprocess.CompletedProcess(args,1,'','unreadable input')
                data=p.read_bytes();rows.append({'path':p.relative_to(source).as_posix(),'size':len(data),'sha256':'wrong' if wrong_digest else hashlib.sha256(data).hexdigest()})
            out.write_text(json.dumps(sorted(rows,key=lambda r:r['path'])))
            return subprocess.CompletedProcess(args,0,'','')
        return invoke

    def sample_inventory(self):
        rows=[{'path':p.removeprefix('sample_tree/'),'size':len(data),'sha256':hashlib.sha256(data).hexdigest()} for p,data in CASES['inventory']['inputs'].items()]
        (self.folder/'report.json').write_text(json.dumps(sorted(rows,key=lambda r:r['path'])))

    def test_inventory_accepts_complete_fixture(self):
        self.sample_inventory()
        with patch('scripts.native_suite_cases.subprocess.run',side_effect=self.inventory_fixture()):
            checks=grade(self.folder,'inventory',self.root)
        self.assertEqual(len(checks),5);self.assertTrue(all(c['passed'] for c in checks),checks)

    def test_inventory_rejects_silent_read_failure(self):
        self.sample_inventory()
        with patch('scripts.native_suite_cases.subprocess.run',side_effect=self.inventory_fixture(skip_unreadable=True)):
            checks=grade(self.folder,'inventory',self.root)
        self.assertFalse(next(c['passed'] for c in checks if c['check'].startswith('scan read failure')))

    def test_inventory_rejects_wrong_digest_and_missing_deliverable(self):
        with patch('scripts.native_suite_cases.subprocess.run',side_effect=self.inventory_fixture(wrong_digest=True)):
            checks=grade(self.folder,'inventory',self.root)
        self.assertFalse(checks[0]['passed']);self.assertFalse(checks[-1]['passed'])

    def test_ranges_rejects_missing_binary(self):
        self.assertEqual(grade(self.folder,'ranges',self.root),[{'check':'actual compiled CLI exists','passed':False}])

    def test_ranges_accepts_signed_boundary_fixture_but_rejects_partial_error_output(self):
        binary=self.folder/'target/debug/ranges';binary.parent.mkdir(parents=True);binary.touch()
        (self.folder/'ranges.json').write_text('[{"start":-1,"end":2},{"start":4,"end":5},{"start":9,"end":9}]')
        def invoke(args, **kwargs):
            try:values=sorted(set(map(int,Path(args[1]).read_text().split())))
            except ValueError:return subprocess.CompletedProcess(args,1,'','invalid integer')
            if any(v < -2**63 or v > 2**63-1 for v in values):return subprocess.CompletedProcess(args,1,'','out of range')
            groups=[]
            for value in values:
                if groups and value==groups[-1]['end']+1:groups[-1]['end']=value
                else:groups.append({'start':value,'end':value})
            return subprocess.CompletedProcess(args,0,json.dumps(groups),'')
        with patch('scripts.native_suite_cases.subprocess.run',side_effect=invoke):
            checks=grade(self.folder,'ranges',self.root)
        self.assertEqual(len(checks),4);self.assertTrue(all(c['passed'] for c in checks),checks)
        def partial(args, **kwargs):
            result=invoke(args,**kwargs)
            if result.returncode:result.stdout='[]'
            return result
        with patch('scripts.native_suite_cases.subprocess.run',side_effect=partial):
            checks=grade(self.folder,'ranges',self.root)
        self.assertFalse(checks[1]['passed']);self.assertFalse(checks[2]['passed'])


if __name__=='__main__':unittest.main()
