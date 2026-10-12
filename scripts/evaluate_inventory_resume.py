# SPDX-License-Identifier: Apache-2.0
"""Observe a saved native inventory task's Resume; no fresh-coding claim."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time

import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.validation_results import archive_report,refresh_results
from scripts.check_native_release import runtime_fingerprint
from scripts.native_suite_cases import grade
from scripts.inventory_goal_audit import CRITERIA as INVENTORY_GOAL_CRITERIA,check_inventory_goal
from scripts.native_observation import ProgressTracker,public_action_counts


def main():
    if len(sys.argv)!=2:raise SystemExit('Provide the saved inventory evaluation report path')
    original=json.loads(Path(sys.argv[1]).read_text());assert original['case']=='inventory' and original['status']!='running'
    job=original['job'];folder=Path(original['cwd']);acceptance=folder/'test_acceptance.py'
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');path=ROOT/'docs'/('native-resume-inventory-'+stamp+'.json')
    report={'started_at':datetime.now(timezone.utc).isoformat(),'status':'starting','case':'inventory_resume',
            'scope':'Targeted Resume/completion repair from previously saved local-model inventory code. Original goal and supplied tests retained; no operator implementation or live hints. Not a fresh implementation and not eligible for the fresh inventory release gate.',
            'original_report':str(Path(sys.argv[1])),'job':job,'cwd':str(folder),'runtime_sha256_before':runtime_fingerprint(ROOT),
            'acceptance_sha256':hashlib.sha256(acceptance.read_bytes()).hexdigest(),'observation_limit_seconds':None,
            'prior_operator_interventions':original.get('operator_interventions',[]),'operator_interventions':[],'samples':[]}
    report['additional_independent_criteria']=list(INVENTORY_GOAL_CRITERIA)
    def save():
        temp=path.with_suffix('.tmp');temp.write_text(json.dumps(report,indent=2)+'\n');temp.replace(path)
    with sqlite3.connect(f'file:{ROOT/"run/workspace.sqlite3"}?mode=ro',uri=True) as db:
        boundary=db.execute('SELECT COALESCE(MAX(id),0) FROM events WHERE job=?',(job,)).fetchone()[0]
    with httpx.Client(base_url='http://127.0.0.1:3210',trust_env=False,timeout=15) as client:
        client.get('/').raise_for_status();response=client.get('/api/status');response.raise_for_status()
        status=response.json()
        if status['active_job']:raise SystemExit('Refusing concurrent Resume evaluation')
        report['memory_policy']={key:status['config'].get(key) for key in ('min_start_available_ram_gb','min_available_ram_gb','memory_pressure_seconds')}
        report['available_ram_before_gib']=round(status['ram']['available']/2**30,3)
        response=client.post('/api/jobs/'+job+'/resume',json={});response.raise_for_status()
        report.update(status='running',event_boundary=boundary);save()
        state_path=ROOT/'docs/STATE.json';state=json.loads(state_path.read_text());state['active_evaluation']={'job':job,'case':'inventory_resume','status':'running','report':str(path.relative_to(ROOT)),'cwd':str(folder)};state['updated_at']=report['started_at'];state_path.write_text(json.dumps(state,indent=2)+'\n')
        print(json.dumps({'job':job,'report':str(path),'scope':'saved-source Resume, not fresh coding'}),flush=True)
        started=time.monotonic();tracker=ProgressTracker(folder)
        while True:
            response=client.get('/api/jobs/'+job+'/progress');response.raise_for_status();progress=response.json()
            response=client.get('/api/status');response.raise_for_status();status=response.json()
            sample={'elapsed_seconds':round(time.monotonic()-started,1),'status':progress['status'],
                    'engine':status['engine'],'available_ram_gib':round(status['ram']['available']/2**30,3),
                    'run_until_done':progress['checkpoint'].get('run_until_done'),
                    'evidence':tracker.observe(progress['checkpoint'],time.monotonic()-started,public_action_counts(ROOT,job))}
            report['samples'].append(sample);save()
            if progress['status']!='running':break
            time.sleep(20)
    suite=subprocess.run([str(ROOT/'.venv/bin/python'),'-m','pytest','-q'],cwd=folder,capture_output=True,text=True,timeout=180)
    output=suite.stdout+suite.stderr;count=re.search(r'(\d+) passed',output);independent=grade(folder,'inventory',ROOT)
    additional=check_inventory_goal(folder,ROOT);independent+=additional;report['additional_goal_checks']=additional
    checks={'native_verified':progress['status']=='complete' and progress['checkpoint'].get('verified',False),
            'continuous_saved_policy':all(s['run_until_done'] is True for s in report['samples']),
            'acceptance_unchanged':hashlib.sha256(acceptance.read_bytes()).hexdigest()==original['acceptance_sha256']==report['acceptance_sha256'],
            'all_independent_checks':bool(independent) and all(c['passed'] for c in independent),
            'additional_passing_project_tests':suite.returncode==0 and bool(count and int(count[1])>6),
            'runtime_frozen':runtime_fingerprint(ROOT)==report['runtime_sha256_before'],
            'no_operator_runtime_hints':not report['operator_interventions']}
    with sqlite3.connect(f'file:{ROOT/"run/workspace.sqlite3"}?mode=ro',uri=True) as db:
        metrics=[json.loads(r[0]) for r in db.execute("SELECT data FROM events WHERE job=? AND id>? AND kind='metrics' ORDER BY id",(job,boundary))]
    report.update(status=progress['status'],passed=all(checks.values()),checks=checks,independent_checks=independent,
                  project_tests={'exit_code':suite.returncode,'output':output[-8000:]},metrics=metrics,
                  min_observed_available_ram_gib=min(s['available_ram_gib'] for s in report['samples']),
                  elapsed_seconds=round(time.monotonic()-started,2),runtime_sha256_after=runtime_fingerprint(ROOT))
    save();archive_report(ROOT,path.name,'native','Inventory Resume and completion repair',report['scope']);refresh_results(ROOT)
    state=json.loads(state_path.read_text());state['active_evaluation']=None;state['last_evaluation']={k:report[k] for k in ('case','job','status','passed','checks','elapsed_seconds')};state['last_evaluation']['report']=str(path.relative_to(ROOT));state_path.write_text(json.dumps(state,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','passed','checks','elapsed_seconds')}),flush=True)
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
