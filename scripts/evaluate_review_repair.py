# SPDX-License-Identifier: Apache-2.0
"""Fresh-context repair experiment; never counted as fresh implementation."""
from datetime import datetime,timezone
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.evaluate_hardening_suite import runtime_digest
from scripts.native_suite_cases import CASES,grade
from scripts.inventory_goal_audit import CRITERIA,check_inventory_goal
from scripts.inventory_extended_audit import CRITERIA as SPECIAL_CRITERIA,check_special_files
from scripts.native_observation import ProgressTracker,public_action_counts
from app.validation_results import archive_report,refresh_results


def main(with_regression=False):
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');case=CASES['inventory']
    prefix='regression-repair-inventory-' if with_regression else 'review-inventory-'
    folder=ROOT/'workspace'/(prefix+stamp);path=ROOT/'docs'/('native-'+prefix+stamp+'.json')
    source=ROOT/'workspace/native-inventory-20261012T021158830837Z'
    prompt='Review this Python project\'s existing implementation against CONTRACT.md. Find and exercise missing required behavior, correct actual defects, and run the full project tests. Existing passing tests do not prove the whole contract. Keep test_acceptance.py unchanged. Regenerate report.json by running the tool on sample_tree after changes. Finish when the requested behavior and outputs are checked.'
    if with_regression:
        prompt='Repair this existing Python project against CONTRACT.md. Run the project tests, diagnose and fix actual failures, and check the complete requested behavior. Keep test_acceptance.py and test_scan_regression.py unchanged. Regenerate report.json by running the tool on sample_tree. Finish when the requested behavior, saved output and tests are checked.'
    with httpx.Client(base_url='http://127.0.0.1:3210',trust_env=False,timeout=30) as client:
        client.get('/');status=client.get('/api/status').json()
        if status['active_job']:raise RuntimeError('Another production task is running')
        shutil.copytree(source,folder,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache'))
        (folder/'CONTRACT.md').write_text(case['prompt'])
        if with_regression:
            shutil.copyfile(ROOT/'scripts/fixtures/scan_regression_tests.py',folder/'test_scan_regression.py')
        acceptance=hashlib.sha256((folder/'test_acceptance.py').read_bytes()).hexdigest()
        seeds={str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()}
        report={'started_at':datetime.now(timezone.utc).isoformat(),'status':'starting','case':'review_inventory','cwd':str(folder),'prompt':prompt,
                'original_goal':case['prompt'],'original_report':'docs/native-inventory-20261012T021158830837Z.json','initial_files_sha256':seeds,
                'scope':'Fresh normal API context reviews an exact copy of the failed model implementation, tests, inputs and report against the original goal in CONTRACT.md. No specific defect, independent failing case or implementation fix supplied. Medium effort. This is seeded review/repair, not fresh implementation or a release-gate pass.',
                'effort':'medium','runtime_sha256_before':runtime_digest(),'acceptance_sha256':acceptance,'additional_independent_criteria':list(CRITERIA),
                'operator_interventions':[],'samples':[]}
        if with_regression:
            report['case']='regression_repair_inventory'
            report['scope']='Known-failure repair through the normal local Agent API. At task start an exact copy of the failed native project receives two calibrated public scan-error regression tests. No implementation/fix supplied; no live hints or operator edits. Original acceptance and supplied regression remain unchanged. Separate predeclared eight behavior checks include previously unseen pipe/socket handling. Seeded repair, not fresh implementation or a release-gate pass.'
            report['additional_independent_criteria']+=list(SPECIAL_CRITERIA)
            baseline=subprocess.run([str(ROOT/'.venv/bin/python'),'-m','pytest','-q'],cwd=folder,capture_output=True,text=True,timeout=180)
            report['baseline']={'exit_code':baseline.returncode,'output':(baseline.stdout+baseline.stderr)[-6000:]}
            if baseline.returncode!=1 or 'test_unreadable_nested_directory' not in baseline.stdout:
                raise RuntimeError('Required baseline regression did not reproduce')
        def save():
            temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(path)
        save()
        response=client.post('/api/sessions',json={'title':'Validation · regression-guided repair' if with_regression else 'Validation · fresh-context contract review','cwd':str(folder)});response.raise_for_status();sid=response.json()['id']
        response=client.post('/api/sessions/'+sid+'/tasks',json={'prompt':prompt,'mode':'agent','max_tokens':None,'reasoning_effort':'medium','run_until_done':True});response.raise_for_status();job=response.json()['job']
        report.update(status='running',job=job,session=sid);save()
        state_path=ROOT/'docs/STATE.json';state=json.loads(state_path.read_text());state['active_evaluation']={'job':job,'session':sid,'report':str(path.relative_to(ROOT)),'cwd':str(folder),'status':'running'};state['active_experiment']=None;state_path.write_text(json.dumps(state,indent=2)+'\n')
        print(json.dumps({'job':job,'report':str(path),'cwd':str(folder)}),flush=True)
        started=time.monotonic();tracker=ProgressTracker(folder)
        while True:
            response=client.get('/api/jobs/'+job+'/progress');response.raise_for_status();progress=response.json();live=client.get('/api/status').json()
            elapsed=round(time.monotonic()-started,1)
            sample={'seconds':elapsed,'status':progress['status'],'turns':progress['checkpoint'].get('turns'),'engine':live['engine'],'progress':progress.get('progress'),
                    'evidence':tracker.observe(progress['checkpoint'],elapsed,public_action_counts(ROOT,job))}
            report['samples'].append(sample);save();print(json.dumps(sample),flush=True)
            if progress['status']!='running':break
            time.sleep(20)
        full=client.get('/api/jobs/'+job).json()
    checks=grade(folder,'inventory',ROOT)+check_inventory_goal(folder,ROOT)
    if with_regression: checks+=check_special_files(folder,ROOT)
    result=subprocess.run([str(ROOT/'.venv/bin/python'),'-m','pytest','-q'],cwd=folder,capture_output=True,text=True,timeout=180)
    report.update(status=full['status'],seconds=round(full['finished']-full['created'],2),independent_checks=checks,
                  project_tests={'exit_code':result.returncode,'output':(result.stdout+result.stderr)[-6000:]},runtime_sha256_after=runtime_digest())
    report['checks']={'native_completion':full['status']=='complete' and full['checkpoint'].get('verified') is True,
                      'runtime_frozen':report['runtime_sha256_before']==report['runtime_sha256_after'],
                      'acceptance_unchanged':hashlib.sha256((folder/'test_acceptance.py').read_bytes()).hexdigest()==acceptance,
                      'project_tests_pass':result.returncode==0,'independent_goal_checks':all(c['passed'] for c in checks)}
    if with_regression:
        report['checks']['regression_tests_unchanged']=hashlib.sha256((folder/'test_scan_regression.py').read_bytes()).hexdigest()==seeds['test_scan_regression.py']
        report['checks']['implementation_changed']=hashlib.sha256((folder/'inventory.py').read_bytes()).hexdigest()!=seeds['inventory.py']
    report['passed']=all(report['checks'].values());save();archive_report(ROOT,path.name,'native','Known-failure regression repair' if with_regression else 'Fresh-context review of failed inventory',report['scope']);refresh_results(ROOT)
    state=json.loads(state_path.read_text());state['active_evaluation']=None;state['last_experiment']={'report':str(path.relative_to(ROOT)),'passed':report['passed'],'scope':report['scope']};state_path.write_text(json.dumps(state,indent=2)+'\n')
    print(json.dumps({'passed':report['passed'],'status':report['status'],'checks':report['checks'],'seconds':report['seconds']}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--with-regression',action='store_true');args=parser.parse_args()
    main(args.with_regression)
