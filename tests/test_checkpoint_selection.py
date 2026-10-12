# SPDX-License-Identifier: Apache-2.0
"""Preserve actual work after test reads; inspect no code outside the project."""
import tempfile
from pathlib import Path
import unittest
from app.working_memory import checkpoint_evidence

class CheckpointSelectionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir='/mnt/GameDrive/tiny_dancer/run');self.root=Path(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def file(self,name,text='observed content'):
  p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);return p
 def names(self,result):return [Path(s['path']).name for s in result['source_snapshots']]
 def test_test_reads_keep_implementation_and_actual_failing_test(self):
  implementation=self.file('main.py','actual implementation');a=self.file('test_a.py');b=self.file('test_b.py')
  obs=[('read_file',{'path':str(implementation)}),('run_checks',{'exit_code':1,'output':'FAIL: test_a.py assertion'}),('read_file',{'path':str(a)}),('read_file',{'path':str(b)})]
  evidence=checkpoint_evidence(obs,self.root,[str(implementation)])
  self.assertEqual(self.names(evidence),['main.py','test_a.py'])
  self.assertEqual(evidence['source_snapshots'][0]['text'],'actual implementation')
 def test_changed_implementation_survives_later_diagnostic_reads(self):
  changed=self.file('core.rs');diagnostic=self.file('diagnostic.rs');test=self.file('tests.rs')
  obs=[('apply_patch',{'files':[{'path':str(changed)}]}),('read_file',{'path':str(diagnostic)}),('read_file',{'path':str(test)})]
  self.assertEqual(self.names(checkpoint_evidence(obs,self.root,[])),['core.rs','tests.rs'])
 def test_plain_documents_keep_recent_observations(self):
  a=self.file('a.txt');b=self.file('b.txt');c=self.file('c.txt')
  obs=[('read_file',{'path':str(p)}) for p in [a,b,c]]
  self.assertEqual(self.names(checkpoint_evidence(obs,self.root,[])),['c.txt','b.txt'])
 def test_aliases_do_not_use_both_snapshot_slots(self):
  a=self.file('a.txt');b=self.file('b.txt')
  obs=[('read_file',{'path':str(b)}),('read_file',{'path':'a.txt'}),('read_file',{'path':str(a)})]
  self.assertEqual(self.names(checkpoint_evidence(obs,self.root,[])),['a.txt','b.txt'])
 def test_external_source_cannot_steal_valid_document_slots(self):
  a=self.file('a.txt');b=self.file('b.txt')
  with tempfile.TemporaryDirectory(dir='/mnt/GameDrive/tiny_dancer/run') as outside:
   p=Path(outside)/'external.py';p.write_text('must not be read')
   obs=[('read_file',{'path':str(a)}),('read_file',{'path':str(b)}),('read_file',{'path':str(p)})]
   self.assertEqual(self.names(checkpoint_evidence(obs,self.root,[])),['b.txt','a.txt'])
