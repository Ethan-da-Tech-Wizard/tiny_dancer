# SPDX-License-Identifier: Apache-2.0
"""Native repair of observed CSV defects; immutable operator-seeded criteria."""
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

import httpx
import psutil

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.validation_results import archive_report,refresh_results
from scripts.coding_acceptance import coding_checks

ACCEPTANCE='''import csv,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class AcceptanceTests(unittest.TestCase):
 def invoke(self,rows):
  with tempfile.TemporaryDirectory(dir=ROOT) as folder:
   path=Path(folder)/"input.csv"
   with path.open("w",newline="") as stream:
    writer=csv.writer(stream);writer.writerow(["category","amount"]);writer.writerows(rows)
   return subprocess.run(["/usr/bin/python3",str(ROOT/"summarize.py"),str(path)],cwd=ROOT,capture_output=True,text=True,timeout=10)
 def totals(self,rows):
  result=self.invoke(rows);self.assertEqual(result.returncode,0,result.stderr)
  return json.loads(result.stdout)
 def test_large_exact_carry(self):
  for width in (40,100,1000):
   with self.subTest(width=width):
    self.assertEqual(self.totals([("large","9"*width+".98"),("large","0.02")]),{"large":"1"+"0"*width+".00"})
 def test_large_signed_cancellation(self):
  whole="1234567890"*100
  self.assertEqual(self.totals([("large",whole+".01"),("large","-"+whole+".00"),("large","0.02")]),{"large":"0.03"})
 def test_quoted_sorted_signed_categories(self):
  result=self.totals([("zebra","-1.25"),("a,b","0.01"),("zebra","2.50"),("a,b","0.02")])
  self.assertEqual(result,{"a,b":"0.03","zebra":"1.25"});self.assertEqual(list(result),["a,b","zebra"])
 def test_repeated_small_signed_amounts(self):
  self.assertEqual(self.totals([("money","0.01")]*500+[("money","-1.25")]),{"money":"3.75"})
 def test_empty_input(self):self.assertEqual(self.totals([]),{})
 def test_clear_invalid_amount_errors(self):
  for value in ("NaN","Infinity","1.234","","oops"):
   with self.subTest(value=value):
    result=self.invoke([("bad",value)]);self.assertNotEqual(result.returncode,0)
    self.assertTrue(result.stderr.strip());self.assertNotIn("Traceback",result.stderr)
if __name__=="__main__":unittest.main()
'''


def main():
    baseline=json.loads((ROOT/'docs/hardening-coding-validation.json').read_text())
    assert baseline['status']!='running' and baseline['passed'] is False
    with httpx.Client(base_url='http://127.0.0.1:3210',timeout=20) as client:
        client.get('/').raise_for_status()
        if client.get('/api/status').json()['active_job']:raise SystemExit('Another task is active')
        folder=ROOT/'workspace'/('precision-repair-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
        shutil.copytree(baseline['cwd'],folder,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache','*.pyc'))
        acceptance=folder/'test_acceptance.py';acceptance.write_text(ACCEPTANCE)
        expected_hash=hashlib.sha256(acceptance.read_bytes()).hexdigest()
        preflight=subprocess.run(['/usr/bin/python3','-m','unittest','-q','test_acceptance'],cwd=folder,capture_output=True,text=True,timeout=30)
        assert preflight.returncode!=0,'The seeded failure must reproduce before native repair'
        prompt=baseline['prompt']+'\nExisting acceptance tests are in test_acceptance.py. Keep them unchanged. Fix product defects and run the relevant project tests until they pass.'
        report={'started_at':datetime.now(timezone.utc).isoformat(),'status':'starting','prompt':prompt,'cwd':str(folder),'operator_interventions':[],
                'scope':'Native repair on copies of the failed native implementation, with operator-seeded acceptance tests from its requirements. New local runner/harness; not an unassisted implementation or comparable full-build speed benchmark. No code or hints injected during execution.',
                'baseline':'docs/hardening-coding-validation.json','acceptance_sha256':expected_hash,'samples':[]}
        report['acceptance_before_repair']={'exit_code':preflight.returncode,'output':(preflight.stdout+preflight.stderr)[-8000:]}
        path=ROOT/'docs/precision-repair-validation.json'
        def save():
            temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(path);refresh_results(ROOT)
        session=client.post('/api/sessions',json={'title':'Validation · exact-money repair','cwd':str(folder)});session.raise_for_status();sid=session.json()['id']
        created=client.post('/api/sessions/'+sid+'/tasks',json={'prompt':prompt,'mode':'agent','max_tokens':None,'run_until_done':True,'reasoning_effort':'auto'});created.raise_for_status();job=created.json()['job']
        report.update(status='running',job=job,session=sid);save();start=time.monotonic();print(json.dumps({'job':job,'session':sid,'cwd':str(folder)}),flush=True)
        while True:
            progress=client.get('/api/jobs/'+job+'/progress').json();status=client.get('/api/status').json()
            sample={'elapsed_seconds':round(time.monotonic()-start,1),'status':progress['status'],'engine':status['engine'],'turns':progress['checkpoint'].get('turns'),
                    'available_ram_gib':round(status['ram']['available']/2**30,3),'progress':progress['progress']}
            if status.get('model_pid'):
                try:
                    process=psutil.Process(status['model_pid']);sample.update(nice=process.nice(),uss_gib=round(process.memory_full_info().uss/2**30,3),read_bytes=process.io_counters().read_bytes)
                except psutil.Error:pass
            report['samples'].append(sample);save();print(json.dumps(sample),flush=True)
            if progress['status']!='running':break
            if time.monotonic()-start>3600:
                client.post('/api/jobs/'+job+'/stop').raise_for_status();report['operator_interventions'].append('Stopped only this evaluation at its one-hour observation limit; not autonomous completion.');save()
            time.sleep(20)
        full=client.get('/api/jobs/'+job).json();events=[{'kind':e['kind'],'data':json.loads(e['data'])} for e in full['events']]
    independent,friendly=coding_checks(folder,ROOT)
    # An unseen width and signed cancellation beyond every supplied test width.
    with tempfile.TemporaryDirectory(dir=ROOT/'run') as temporary:
        input_path=Path(temporary)/'unseen.csv';whole='1234567890'*160
        input_path.write_text('category,amount\nhuge,'+whole+'.99\nhuge,-'+whole+'.00\nhuge,0.02\n')
        unseen=subprocess.run(['/usr/bin/python3',str(folder/'summarize.py'),str(input_path)],cwd=folder,capture_output=True,text=True,timeout=10)
        try:actual=json.loads(unseen.stdout)
        except ValueError:actual=None
    checks={'native_verified':full['checkpoint'].get('verified',False),'acceptance_unchanged':hashlib.sha256(acceptance.read_bytes()).hexdigest()==expected_hash,
            'independent_cli_checks':all(check['passed'] for check in independent),'clear_errors':all(check['passed'] for check in friendly),
            'unseen_1600_digit_signed_case':unseen.returncode==0 and actual=={'huge':'1.01'},
            'automatic_initial_work_allowance':full['checkpoint'].get('generation_budget',{}).get('initial')==2048}
    report.update(status=full['status'],passed=full['status']=='complete' and all(checks.values()) and not report['operator_interventions'],checks=checks,
                  checkpoint=full['checkpoint'],job_elapsed_seconds=round(full['finished']-full['created'],2),independent_checks=independent,clear_error_checks=friendly,
                  unseen={'exit_code':unseen.returncode,'actual':actual,'stderr':unseen.stderr[-1500:]},metrics=[e['data'] for e in events if e['kind']=='metrics'],
                  tool_calls=[e['data'] for e in events if e['kind']=='tool_start'],errors=[e['data'] for e in events if e['kind']=='error'])
    save();archive_report(ROOT,path.name,'native','Precision repair after local-runner hardening',report['scope']);refresh_results(ROOT)
    print(json.dumps({k:report[k] for k in ('status','passed','checks','job_elapsed_seconds')}),flush=True)
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
