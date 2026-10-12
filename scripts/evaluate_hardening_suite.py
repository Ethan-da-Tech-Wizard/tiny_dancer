# SPDX-License-Identifier: Apache-2.0
"""Run one predeclared native coding case; preserve every run independently."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import tomllib

import httpx
import psutil

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.validation_results import archive_report,refresh_results
from scripts.native_suite_cases import CASES,grade
from scripts.inventory_goal_audit import CRITERIA as INVENTORY_GOAL_CRITERIA,check_inventory_goal
from scripts.inventory_extended_audit import CRITERIA as SPECIAL_FILE_CRITERIA,check_special_files
from scripts.labels_goal_audit import CRITERIA as LABEL_GOAL_CRITERIA,check_labels_goal
from scripts.native_observation import ProgressTracker,limit_reached,observation_delay,observation_limit,public_action_counts


def runtime_digest():
    digest=hashlib.sha256()
    paths=sorted((ROOT/'app').rglob('*.py'))+[ROOT/'config.json']
    paths+=sorted((ROOT/'app/static').glob('*'))
    for path in paths:
        if path.is_file():digest.update(str(path.relative_to(ROOT)).encode());digest.update(path.read_bytes())
    return digest.hexdigest()


def parse_options(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument('case',choices=CASES)
    policy=parser.add_mutually_exclusive_group()
    policy.add_argument('--observation-seconds',type=int,default=None,help='Explicit bounded benchmark; omitted observes until terminal.')
    policy.add_argument('--until-terminal',action='store_true',help='Observe until completion, a real blocker or Stop; the default has no aggregate deadline.')
    parser.add_argument('--effort',choices=('auto','low','medium','high'),default='auto')
    args=parser.parse_args(argv)
    if args.observation_seconds is not None and not 60<=args.observation_seconds<=7200:
        parser.error('observation-seconds must be between60 and7200')
    return args


def main():
    args=parse_options()
    limit=observation_limit(args.observation_seconds,args.until_terminal)
    case=CASES[args.case];stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder=ROOT/'workspace'/('native-'+args.case+'-'+stamp)
    report_path=ROOT/'docs'/('native-'+args.case+'-'+stamp+'.json')
    with httpx.Client(base_url='http://127.0.0.1:3210',trust_env=False,timeout=30) as client:
        client.get('/').raise_for_status();status=client.get('/api/status');status.raise_for_status()
        if status.json()['active_job']:raise SystemExit('Refusing concurrent native evaluation')
        folder.mkdir()
        for name,data in case['inputs'].items():
            path=folder/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        acceptance=folder/'test_acceptance.py';acceptance.write_text(case['acceptance'])
        acceptance_hash=hashlib.sha256(acceptance.read_bytes()).hexdigest();before=runtime_digest()
        report={'started_at':datetime.now(timezone.utc).isoformat(),'status':'starting','case':args.case,'prompt':case['prompt'],
                'cwd':str(folder),'acceptance_sha256':acceptance_hash,'runtime_sha256_before':before,'independent_criteria':case['independent'],
                'backend':status.json()['config'].get('backend','picchio'),'serving_model_path':status.json()['config']['model_path'],
                'scope':'Fresh implementation from a frozen goal, sample input and operator-seeded acceptance tests only. No implementation supplied, no operator runtime hints, actual local GPT-OSS-20B. Generic project baseline/importfacts may be supplied by the configured harness. Independent checks withheld until termination.',
                'operator_interventions':[],'observation_limit_seconds':limit,'observation_policy':'until_terminal' if limit is None else 'bounded_benchmark',
                'execution':{'reasoning_effort':args.effort,'initial_budget':'Auto: remaining physical context for native chat work'},'samples':[]}
        report['additional_independent_criteria']=list(INVENTORY_GOAL_CRITERIA) if args.case=='inventory' else list(LABEL_GOAL_CRITERIA) if args.case=='labels' else []
        if args.case=='inventory': report['additional_independent_criteria']+=list(SPECIAL_FILE_CRITERIA)
        def save():
            temp=report_path.with_suffix('.tmp');temp.write_text(json.dumps(report,indent=2)+'\n');temp.replace(report_path)
        save()
        session=client.post('/api/sessions',json={'title':'Validation · '+args.case+' generalization','cwd':str(folder)});session.raise_for_status();sid=session.json()['id']
        response=client.post('/api/sessions/'+sid+'/tasks',json={'prompt':case['prompt'],'mode':'agent','max_tokens':None,'run_until_done':True,'reasoning_effort':args.effort});response.raise_for_status();job=response.json()['job']
        report.update(status='running',job=job,session=sid);save()
        state_path=ROOT/'docs/STATE.json';state=json.loads(state_path.read_text());state['active_evaluation']={k:report[k] for k in ('job','session','cwd','status')};state['active_evaluation']['report']=str(report_path.relative_to(ROOT));state['updated_at']=datetime.now(timezone.utc).isoformat();state_path.write_text(json.dumps(state,indent=2)+'\n')
        policy='No aggregate observation deadline' if limit is None else str(limit)+'-second observation limit'
        with (ROOT/'docs/SESSION_LOG.md').open('a') as output:output.write('\n## '+report['started_at']+' — Frozen '+args.case+' native evaluation launched\n\n- Report '+str(report_path.relative_to(ROOT))+', job '+job+', folder '+str(folder)+'. Fresh implementation, supplied tests/input only; no operator runtime hints. Generic preconfigured project baseline and import-derived library facts may be supplied by the harness. Runtime SHA256 '+before+'. '+policy+', unchanged acceptance hash and independently checked outputs required.\n')
        print(json.dumps({'job':job,'case':args.case,'report':str(report_path),'cwd':str(folder)}),flush=True)
        started=time.monotonic();stopped=False;tracker=ProgressTracker(folder)
        while True:
            response=client.get('/api/jobs/'+job+'/progress');response.raise_for_status();progress=response.json()
            response=client.get('/api/status');response.raise_for_status();status=response.json()
            sample={'elapsed_seconds':round(time.monotonic()-started,1),'status':progress['status'],'turns':progress['checkpoint'].get('turns'),
                    'engine':status['engine'],'available_ram_gib':round(status['ram']['available']/2**30,3),'progress':progress['progress']}
            sample['evidence']=tracker.observe(progress['checkpoint'],sample['elapsed_seconds'],public_action_counts(ROOT,job))
            if status.get('model_pid'):
                try:
                    process=psutil.Process(status['model_pid']);sample.update(nice=process.nice(),uss_gib=round(process.memory_full_info().uss/2**30,3))
                except psutil.Error:pass
            report['samples'].append(sample);save();print(json.dumps(sample),flush=True)
            if progress['status']!='running':break
            if limit_reached(time.monotonic()-started,limit) and not stopped:
                client.post('/api/jobs/'+job+'/stop').raise_for_status();stopped=True
                report['operator_interventions'].append('Stopped only this evaluation at its predeclared '+str(args.observation_seconds)+'-second observation limit; not autonomous completion.');save()
            time.sleep(observation_delay(time.monotonic()-started,limit,stopped))
        response=client.get('/api/jobs/'+job);response.raise_for_status();full=response.json()
    acceptance_run=subprocess.run([str(ROOT/'.venv/bin/python'),'-m','unittest','-v','test_acceptance'],cwd=folder,capture_output=True,text=True,timeout=180)
    acceptance_output=acceptance_run.stdout+acceptance_run.stderr
    independent=grade(folder,args.case,ROOT)
    additional=check_inventory_goal(folder,ROOT) if args.case=='inventory' else check_labels_goal(folder) if args.case=='labels' else []
    if args.case=='inventory': additional+=check_special_files(folder,ROOT)
    independent+=additional
    report['additional_goal_checks']=additional
    seeded_key='all_seeded_behavior_tests' if case.get('kind')=='module' else 'all_seeded_cli_tests'
    independent_key='all_independent_behavior_checks' if case.get('kind')=='module' else 'all_independent_cli_checks'
    checks={'native_verified':full['status']=='complete' and full['checkpoint'].get('verified',False),
            'acceptance_unchanged':hashlib.sha256(acceptance.read_bytes()).hexdigest()==acceptance_hash,
            'runtime_frozen':runtime_digest()==before,seeded_key:acceptance_run.returncode==0 and bool(re.search(r'Ran 6 tests',acceptance_output)),
            independent_key:bool(independent) and all(check['passed'] for check in independent)}
    if args.case=='ranges':
        manifest=tomllib.loads((folder/'Cargo.toml').read_text()) if (folder/'Cargo.toml').is_file() else {}
        lock=tomllib.loads((folder/'Cargo.lock').read_text()) if (folder/'Cargo.lock').is_file() else {}
        sections=[manifest]+list(manifest.get('target',{}).values())
        checks['no_external_rust_dependencies']=bool(manifest) and not any(section.get(key) for section in sections for key in ('dependencies','dev-dependencies','build-dependencies')) and all(p.get('name')=='ranges' for p in lock.get('package',[]))
        cargo=subprocess.run(['cargo','test','--offline'],cwd=folder,capture_output=True,text=True,timeout=180)
        cargo_output=cargo.stdout+cargo.stderr
        checks['nonempty_passing_rust_unit_tests']=cargo.returncode==0 and bool(re.search(r'test result: ok\. [1-9]\d* passed',cargo_output))
        report['independent_cargo_tests']={'exit_code':cargo.returncode,'output':cargo_output[-8000:]}
    else:
        suite=subprocess.run([str(ROOT/'.venv/bin/python'),'-m','pytest','-q'],cwd=folder,capture_output=True,text=True,timeout=180)
        suite_output=suite.stdout+suite.stderr;count=re.search(r'(\d+) passed',suite_output)
        checks['additional_nonempty_passing_project_tests']=suite.returncode==0 and bool(count and int(count[1])>6)
        report['independent_project_tests']={'exit_code':suite.returncode,'output':suite_output[-8000:]}
    events=[{'kind':e['kind'],'data':json.loads(e['data'])} for e in full['events']]
    report.update(status=full['status'],passed=all(checks.values()) and not report['operator_interventions'],checks=checks,
                  acceptance_after={'exit_code':acceptance_run.returncode,'output':acceptance_output[-12000:]},independent_checks=independent,
                  checkpoint=full['checkpoint'],job_elapsed_seconds=round(full['finished']-full['created'],2),
                  metrics=[e['data'] for e in events if e['kind']=='metrics'],tool_calls=[e['data'] for e in events if e['kind']=='tool_start'],
                  errors=[e['data'] for e in events if e['kind']=='error'])
    save();archive_report(ROOT,report_path.name,'native',case['title'],report['scope']);refresh_results(ROOT)
    state=json.loads(state_path.read_text());state['active_evaluation']=None;state['last_evaluation']={k:report[k] for k in ('case','job','status','passed','checks','job_elapsed_seconds')};state['last_evaluation']['report']=str(report_path.relative_to(ROOT));state['updated_at']=datetime.now(timezone.utc).isoformat();state_path.write_text(json.dumps(state,indent=2)+'\n')
    with (ROOT/'docs/SESSION_LOG.md').open('a') as output:output.write('\n- Frozen '+args.case+' outcome: '+json.dumps({k:report[k] for k in ('status','passed','checks','job_elapsed_seconds')})+'. Evidence archived; no implementation/hints injected during execution.\n')
    print(json.dumps({k:report[k] for k in ('status','passed','checks','job_elapsed_seconds')}),flush=True)
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
