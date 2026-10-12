# SPDX-License-Identifier: Apache-2.0
"""Real child processes prove the broader grader detects both observed defects."""
from pathlib import Path
import tempfile
import unittest
from scripts.inventory_goal_audit import check_inventory_goal
from app.tools import ROOT

GOOD = '''import hashlib,json,os,sys,tempfile
from pathlib import Path
tree,out=map(Path,sys.argv[1:])
def scan_error(error):raise error
try:
 rows=[]
 for folder,dirs,names in os.walk(tree,onerror=scan_error):
  for name in names:
   p=Path(folder)/name
   if p.resolve()==out.resolve() or not p.is_file():continue
   data=p.read_bytes()
   rows.append(dict(path=p.relative_to(tree).as_posix(),size=len(data),sha256=hashlib.sha256(data).hexdigest()))
 rows.sort(key=lambda r:r['path'])
 fd,temporary=tempfile.mkstemp(dir=out.parent)
 with os.fdopen(fd,'w') as f:json.dump(rows,f)
 os.replace(temporary,out)
except Exception as error:
 print(str(error),file=sys.stderr);sys.exit(1)
'''


class InventoryGoalAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'run');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'run').mkdir()
        self.folder=self.root/'task';self.folder.mkdir()

    def audit(self, source):
        (self.folder/'inventory.py').write_text(source)
        return check_inventory_goal(self.folder,self.root)

    def test_real_correct_cli_passes_both_goal_checks(self):
        self.assertTrue(all(c['passed'] for c in self.audit(GOOD)))

    def test_existing_output_restriction_fails_only_replacement(self):
        source=GOOD.replace(' rows=[]',' if out.exists() and not out.resolve().is_relative_to(tree.resolve()):raise ValueError("exists")\n rows=[]')
        checks=self.audit(source)
        self.assertFalse(checks[0]['passed']);self.assertTrue(checks[1]['passed'])

    def test_silent_directory_error_fails_only_scan_preservation(self):
        checks=self.audit(GOOD.replace('os.walk(tree,onerror=scan_error)','os.walk(tree)'))
        self.assertTrue(checks[0]['passed']);self.assertFalse(checks[1]['passed'])
        self.assertFalse(checks[1]['prior_output_preserved'])

    def test_missing_program_cannot_pass_an_error_only_check(self):
        self.assertTrue(all(not c['passed'] for c in check_inventory_goal(self.folder,self.root)))
