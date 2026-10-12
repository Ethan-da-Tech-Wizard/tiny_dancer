# SPDX-License-Identifier: Apache-2.0
"""Native patch/cache/medium-effort capability probe with a seeded bug and tests."""
import json
import subprocess
import time
from datetime import datetime,timezone
from pathlib import Path

import httpx

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'docs/native-harness-validation.json'
PROMPT='Repair calc.py so add(a, b) returns their sum. Use apply_patch for the edit, then verify with the existing tests. Finish after the tests pass.'


def main():
    report={'started_at':datetime.now(timezone.utc).isoformat(),'prompt':PROMPT,'status':'starting',
            'scope':'Native capability probe with operator-seeded bug and tests, not an unassisted implementation evaluation. No replacement code or recovery notes supplied during execution.',
            'operator_interventions':[],'samples':[]}
    def save(): REPORT.write_text(json.dumps(report,indent=2)+'\n')
    with httpx.Client(base_url='http://127.0.0.1:3210',timeout=15) as client:
        client.get('/').raise_for_status();status=client.get('/api/status').json()
        if status['active_job']: raise SystemExit('Another task is active; no probe started')
        if not status['config'].get('exact_history_cache'): raise SystemExit('Deploy the guarded cache upgrade before this probe')
        folder=ROOT/'workspace'/('harness-probe-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'));folder.mkdir()
        (folder/'calc.py').write_text('def add(a, b):\n    return a - b\n')
        (folder/'test_calc.py').write_text('import unittest\nfrom calc import add\nclass Arithmetic(unittest.TestCase):\n    def test_sum(self):\n        for a,b in ((7,2),(-3,2),(0,0),(-4,-5)):\n            with self.subTest(a=a,b=b):\n                self.assertEqual(add(a,b),a+b)\nif __name__=="__main__":\n    unittest.main()\n')
        response=client.post('/api/sessions',json={'title':'Validation · native patch and cache','cwd':str(folder)});response.raise_for_status();sid=response.json()['id']
        response=client.post('/api/sessions/'+sid+'/tasks',json={'prompt':PROMPT,'mode':'agent','task_kind':'work','max_tokens':1024,'run_until_done':True,'reasoning_effort':'medium'})
        response.raise_for_status();job=response.json()['job'];report.update(status='running',session=sid,job=job,cwd=str(folder));save()
        print(json.dumps({k:report[k] for k in ('status','job','session')}),flush=True);started=time.monotonic()
        while True:
            progress=client.get('/api/jobs/'+job+'/progress').json();status=client.get('/api/status').json()
            sample={'elapsed_seconds':round(time.monotonic()-started,1),'status':progress['status'],'engine':status['engine'],
                    'available_ram_gib':round(status['ram']['available']/2**30,3),'progress':progress['progress']}
            report['samples'].append(sample);save();print(json.dumps(sample),flush=True)
            if progress['status']!='running': break
            if time.monotonic()-started>1800:
                client.post('/api/jobs/'+job+'/stop').raise_for_status()
                report['operator_interventions'].append('Stopped only this capability probe at its explicit 30-minute observation limit; not scored as autonomous completion.')
            time.sleep(20)
        full=client.get('/api/jobs/'+job).json();events=[{'kind':e['kind'],'data':json.loads(e['data'])} for e in full['events']]
        metrics=[e['data'] for e in events if e['kind']=='metrics'];results=[e['data'] for e in events if e['kind']=='tool_result']
        check=subprocess.run(['/usr/bin/python3','-c','from calc import add; assert all(add(a,b)==a+b for a,b in ((11,7),(-4,-7),(10**50,10**50)))'],cwd=folder,capture_output=True,text=True,timeout=15)
        patched=any(e['name']=='apply_patch' and json.loads(e['result']).get('applied') for e in results)
        cache_used=any(m.get('exact_history_cache_tokens',0)>0 for m in metrics)
        medium=bool(metrics) and all(m.get('reasoning_effort')=='medium' for m in metrics)
        report.update(status=full['status'],checkpoint=full['checkpoint'],elapsed_seconds=round(time.monotonic()-started,1),
                      job_elapsed_seconds=round(full['finished']-full['created'],2) if full.get('finished') else None,metrics=metrics,
                      tool_calls=[e['data'] for e in events if e['kind']=='tool_start'],
                      harness_continuations=[e['data'] for e in events if e['kind']=='continuation'],
                      errors=[e['data'] for e in events if e['kind']=='error'],
                      checks={'actual_patch_applied':patched,'exact_cache_used':cache_used,'native_medium_effort':medium,'unseen_arithmetic_passed':check.returncode==0},
                      saved_prefill_tokens=sum(m.get('cache_saved_prefill_tokens',0) for m in metrics),
                      cache_measurement_note='Per-turn counterfactual token work against canonical re-rendering and the current raw resident prefix. Not a cache-disabled full-run baseline, wall-time A/B benchmark or model-quality multiplier.',
                      verification_stderr=check.stderr[:1000])
        report['passed']=full['status']=='complete' and all(report['checks'].values()) and not report['operator_interventions']
        save();print(json.dumps({k:report[k] for k in ('status','elapsed_seconds','passed','checks','saved_prefill_tokens')}),flush=True)
        if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
