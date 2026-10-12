# SPDX-License-Identifier: Apache-2.0
"""Frozen real-model repair comparison or exact user JSON/editor regression."""
import argparse
import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime,timezone
from pathlib import Path

import httpx
import psutil

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.validation_results import archive_report,refresh_results
from app.facts import validate_scores


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('kind',choices=['repair','export','coding']);args=parser.parse_args()
    before_names={'repair':'native-harness-validation.json','export':'score-export-before.json','coding':'native-coding-validation.json'}
    output_names={'repair':'batching-native-validation.json','export':'score-export-validation.json','coding':'hardening-coding-validation.json'}
    before=json.loads((ROOT/'docs'/before_names[args.kind]).read_text())
    prompt=before['prompt'];report_path=ROOT/'docs'/output_names[args.kind]
    report={'started_at':datetime.now(timezone.utc).isoformat(),'prompt':prompt,'status':'starting','operator_interventions':[],'samples':[],
            'scope':'Frozen initial prompt, no operator code/recovery notes during native execution. '+({'repair':'Seeded bug/tests identical to previous repair probe; historical timing comparison.','export':'Exact original user request in the original workspace/session. Typed host export is explicitly identified; the model selects tool arguments.','coding':'Original CSV goal and input only in a fresh folder; no implementation or tests supplied. Independent/friendly-error checks run after termination.'}[args.kind])}
    def save():
        temporary=report_path.with_suffix('.tmp');temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(report_path);refresh_results(ROOT)
    with httpx.Client(base_url='http://127.0.0.1:3210',timeout=20) as client:
        client.get('/').raise_for_status();status=client.get('/api/status').json()
        if status['active_job']: raise SystemExit('Another task is active; no evaluation started')
        if 'inspect_project' not in status['tools']: raise SystemExit('Guarded deployment required before evaluation')
        if args.kind=='repair':
            folder=ROOT/'workspace'/('harness-probe-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'));folder.mkdir()
            original=Path(before['cwd'])
            for name in ('calc.py','test_calc.py'):
                content=(original/name).read_text()
                if name=='calc.py':content='def add(a, b):\n    return a - b\n'
                (folder/name).write_text(content)
            response=client.post('/api/sessions',json={'title':'Validation · batched repair','cwd':str(folder)});response.raise_for_status();sid=response.json()['id'];effort='medium'
        elif args.kind=='export':
            sid='e49878f2e88542cdaefe0fe660e32307';folder=Path(client.get('/api/sessions/'+sid).json()['cwd']);effort='auto'
        else:
            folder=ROOT/'workspace'/('native-coding-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'));folder.mkdir()
            (folder/'sample.csv').write_bytes((Path(before['cwd'])/'sample.csv').read_bytes())
            response=client.post('/api/sessions',json={'title':'Validation · hardened CSV implementation','cwd':str(folder)});response.raise_for_status();sid=response.json()['id'];effort='auto'
        response=client.post('/api/sessions/'+sid+'/tasks',json={'prompt':prompt,'mode':'agent','run_until_done':True,'max_tokens':1024,'reasoning_effort':effort});response.raise_for_status()
        job=response.json()['job'];report.update(status='running',job=job,session=sid,cwd=str(folder));save();started=time.monotonic()
        print(json.dumps({'job':job,'session':sid,'kind':args.kind}),flush=True)
        while True:
            progress=client.get('/api/jobs/'+job+'/progress').json();status=client.get('/api/status').json()
            sample={'elapsed_seconds':round(time.monotonic()-started,1),'status':progress['status'],'engine':status['engine'],'available_ram_gib':round(status['ram']['available']/2**30,3),'progress':progress['progress']}
            sample['turns']=progress['checkpoint'].get('turns')
            if status.get('model_pid'):
                try:
                    process=psutil.Process(status['model_pid']);cpu=process.cpu_times()
                    sample.update(pid=process.pid,nice=process.nice(),uss_gib=round(process.memory_full_info().uss/2**30,3),cpu_seconds=round(cpu.user+cpu.system,3),read_bytes=process.io_counters().read_bytes)
                except psutil.Error:pass
            report['samples'].append(sample);save();print(json.dumps(sample),flush=True)
            if progress['status']!='running':break
            if time.monotonic()-started>1800:
                client.post('/api/jobs/'+job+'/stop').raise_for_status();report['operator_interventions'].append('Stopped only this evaluation at its explicit 30-minute observation limit; autonomous completion not established.');save()
            time.sleep(20)
        full=client.get('/api/jobs/'+job).json();events=[{'kind':e['kind'],'data':json.loads(e['data'])} for e in full['events']]
        calls=[e['data'] for e in events if e['kind']=='tool_start'];metrics=[e['data'] for e in events if e['kind']=='metrics']
        checks={}
        if args.kind=='repair':
            independent=subprocess.run(['/usr/bin/python3','-c','from calc import add; assert all(add(a,b)==a+b for a,b in ((11,7),(-4,-7),(10**50,10**50)))'],cwd=folder,capture_output=True,text=True,timeout=15)
            names={c['name'] for c in calls};checks={'project_inspection_used':'inspect_project' in names,'checks_batched':'run_checks' in names,'patch_used':'apply_patch' in names,'unseen_arithmetic_passed':independent.returncode==0,'native_verified':full['checkpoint'].get('verified',False)}
            report['comparison']={'before_seconds':before['job_elapsed_seconds'],'before_first_prompt_tokens':before['metrics'][0]['prompt_tokens'],'before_turns':before['checkpoint']['turns'],'note':'Identical initial prompt/seeded files; separate historical runs. Not a controlled universal speed claim.'}
        elif args.kind=='export':
            checkpoint=full['checkpoint'];proof=checkpoint.get('data_check',{});path=Path(proof.get('file','/nonexistent'))
            data=json.loads(path.read_text()) if path.is_file() else {}
            requested=checkpoint['contract']['target_date'];url='https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates='+requested.replace('-','')
            source=httpx.get(url,timeout=20,follow_redirects=True);source.raise_for_status();expected=validate_scores(source.json(),requested)
            fields=('away','away_score','home','home_score')
            rows=lambda games:sorted(tuple(game[k] for k in fields) for game in games)
            checks={'requested_json_saved':path.is_file(),'correct_date':data.get('date')==requested,'every_matchup_matches_separate_fetch':rows(data.get('games',[]))==rows(expected),
                    'actual_editor_action':str(path) in checkpoint.get('editor_opened',[]),'completion_checks_passed':checkpoint.get('verified',False)}
            report.update(saved_file=str(path),games=len(expected),independent_source=url)
            from app.tools import ComputerTools
            async def inspect_editor():
                tools=ComputerTools()
                try:return await tools.desktop({'action':'windows'})
                finally:await tools.close()
            windows=asyncio.run(inspect_editor());checks['editor_window_shows_json']=any(path.name in window.get('title','') and 'code' in window.get('class','').lower() for window in windows)
        else:
            from scripts.coding_acceptance import coding_checks
            independent,errors=coding_checks(folder,ROOT)
            checks={'independent_cli_checks':bool(independent) and all(check['passed'] for check in independent),'clear_invalid_amount_errors':bool(errors) and all(check['passed'] for check in errors),'native_verified':full['checkpoint'].get('verified',False),'own_tests_created':bool(list(folder.glob('test_*.py')))}
            report.update(independent_checks=independent,clear_error_checks=errors,generated_files=[{'path':str(path),'bytes':path.stat().st_size} for path in folder.glob('*.py')])
        report.update(status=full['status'],checkpoint=full['checkpoint'],job_elapsed_seconds=round(full['finished']-full['created'],2),metrics=metrics,tool_calls=calls,checks=checks,
                      errors=[e['data'] for e in events if e['kind']=='error'],harness_continuations=[e['data'] for e in events if e['kind']=='continuation'])
        observed=[sample for sample in report['samples'] if 'uss_gib' in sample]
        report['resources']={'minimum_available_ram_gib':min(sample['available_ram_gib'] for sample in report['samples']),
                             'maximum_observed_model_uss_gib':max((sample['uss_gib'] for sample in observed),default=None),
                             'worker_nice_values':sorted({sample['nice'] for sample in observed}),
                             'scope':'20-second observations, not continuous peak measurements; whole-machine available RAM includes other applications.'}
        report['passed']=full['status']=='complete' and all(checks.values()) and not report['operator_interventions'];save()
        archive_report(ROOT,report_path.name,'native',{'repair':'Seeded repair after batching','export':'Scores → JSON → Code OSS','coding':'Fresh CSV implementation after hardening'}[args.kind],report['scope']);refresh_results(ROOT)
        print(json.dumps({k:report[k] for k in ('status','passed','checks','job_elapsed_seconds')}),flush=True)
        if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
