# SPDX-License-Identifier: Apache-2.0
"""Frozen same-model comparison with upstream Pi; no live hints or product edits."""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import httpx
import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.engine import LocalEngine
from app.verification import test_summary
from app.validation_results import archive_report, refresh_results
from scripts.evaluate_hardening_suite import runtime_digest
from scripts.native_suite_cases import CASES, grade
from scripts.labels_goal_audit import CRITERIA as LABEL_CRITERIA, check_labels_goal
from scripts.inventory_goal_audit import CRITERIA as INVENTORY_CRITERIA, check_inventory_goal
from scripts.pi_baseline import FLAGS, child_environment, models_config, settings_config, public_event
from scripts.node_licenses import verify_node


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


async def evaluate(case_name, effort):
    verify_node(ROOT)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    case = CASES[case_name]
    folder = ROOT / 'workspace' / ('pi-' + case_name + '-' + stamp)
    report_path = ROOT / 'docs' / ('pi-' + case_name + '-' + stamp + '.json')
    private = ROOT / 'run' / ('pi-' + stamp)
    async with httpx.AsyncClient(base_url='http://127.0.0.1:3210', trust_env=False, timeout=5) as client:
        await client.get('/')
        response = await client.get('/api/status'); response.raise_for_status()
        status = response.json()
        if status.get('active_job') or status.get('model_pid'):
            raise RuntimeError('Comparison requires production idle and its model unloaded')
        folder.mkdir(); private.mkdir(mode=0o700); (private / 'tmp').mkdir(mode=0o700)
        for name, data in case['inputs'].items():
            target = folder / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
        acceptance = folder / 'test_acceptance.py'; acceptance.write_text(case['acceptance'])
        engine, cancel = LocalEngine(), threading.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM): loop.add_signal_handler(sig, cancel.set)
        started = time.monotonic()
        report = {'started_at': datetime.now(timezone.utc).isoformat(), 'case': case_name,
            'status': 'running', 'passed': False, 'cwd': str(folder), 'prompt': case['prompt'],
            'scope': 'Isolated upstream Pi1.1.0 default coding tools/system prompt, same original local GPT-OSS-20B and existing backend/context/sampler. Fresh original goal and supplied acceptance, independent grading. Several harness differences: comparison, not attribution or production qualification. No operator product edits or live hints.',
            'runtime_sha256_before': runtime_digest(), 'acceptance_sha256': file_hash(acceptance),
            'observer_sha256': {p.name:file_hash(p) for p in (Path(__file__),ROOT/'scripts/pi_baseline.py')},
            'package_lock_sha256': file_hash(ROOT/'vendor/pi-runtime/package-lock.json'),
            'reasoning_effort': effort, 'aggregate_deadline_seconds': None,
            'declared_additional_criteria': list(LABEL_CRITERIA if case_name == 'labels' else INVENTORY_CRITERIA),
            'operator_interventions': [], 'events': [], 'samples': [], 'stream_events': 0}
        def save():
            temporary = report_path.with_suffix('.tmp')
            temporary.write_text(json.dumps(report, indent=2) + '\n'); temporary.replace(report_path)
        save()
        state_path = ROOT/'docs/STATE.json'
        state = json.loads(state_path.read_text()); state['active_experiment'] = {'report':str(report_path.relative_to(ROOT)), 'scope':report['scope']}
        state_path.write_text(json.dumps(state, indent=2)+'\n')
        with (ROOT/'docs/SESSION_LOG.md').open('a') as log:
            log.write('\n'+report['started_at']+' — Isolated Pi '+case_name+' comparison launched: '+str(report_path.relative_to(ROOT))+'. Same local model, medium effort, original frozen goal/tests, no live hints or operator product edits, no aggregate cutoff. Private JSON stream is filtered before saving public evidence.\n')
        print(json.dumps({'report':str(report_path),'cwd':str(folder)}),flush=True)
        process = None; done = asyncio.Event(); last_stream = time.monotonic()

        async def stop_owned():
            cancel.set()
            if process and process.returncode is None:
                try: os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError: pass
            await asyncio.to_thread(engine.cancel)

        async def monitor():
            low_since = None; last_sample = 0; activity_previous = None; last_activity = time.monotonic()
            while not done.is_set():
                try:
                    r = await client.get('/api/status');r.raise_for_status(); live = r.json()
                    if live.get('active_job') or live.get('model_pid'):
                        report['interruption'] = 'Production task/model started; only comparison cancelled'; cancel.set()
                    now = time.monotonic(); available = psutil.virtual_memory().available / 2**30
                    low_since = (low_since or now) if available < 1.5 else None
                    if low_since and now - low_since >= 6:
                        report['interruption'] = 'Available RAM below1.5GiB for6seconds';cancel.set()
                    activity = engine.work_activity()
                    if activity != activity_previous:
                        last_activity = now; activity_previous = activity
                    if now - max(last_activity,last_stream) > 900:
                        report['interruption'] = '900seconds without observable inference activity';cancel.set()
                    if cancel.is_set(): await stop_owned()
                    if now-last_sample >= 20:
                        sample = {'seconds':round(now-started,1),'available_ram_gib':round(available,3),
                                  'stream_events':report['stream_events'],'public_actions':sum(e['type']=='tool_execution_start' for e in report['events']),
                                  'owned_model_activity':activity}
                        report['samples'].append(sample);save();print(json.dumps(sample),flush=True);last_sample=now
                except httpx.HTTPError:
                    report['interruption']='Cannot confirm production idle';await stop_owned()
                try: await asyncio.wait_for(done.wait(),2)
                except asyncio.TimeoutError: pass
        monitor_task=asyncio.create_task(monitor())
        try:
            await asyncio.to_thread(engine.load,cancel)
            if cancel.is_set(): raise RuntimeError('Comparison cancelled during model startup')
            models = models_config(str(engine.session.client.base_url))
            (private/'models.json').write_text(json.dumps(models,indent=2)+'\n')
            settings = settings_config(effort)
            (private/'settings.json').write_text(json.dumps(settings,indent=2)+'\n')
            report['configuration']={'models':models,'settings':settings,'flags':FLAGS}
            key = engine.session.client.headers['Authorization'].removeprefix('Bearer ')
            env = child_environment(ROOT,private,key)
            args=[str(ROOT/'vendor/pi-runtime/node_modules/.bin/pi'), *FLAGS, '--mode','json','--print',
                  '--provider','tiny-local','--model','gpt-oss-20b','--thinking',effort,
                  '--tools','read,bash,edit,write','--session-dir',str(private/'sessions'),case['prompt']]
            # stderr may contain private provider data; retain privately, never echo it.
            error_fd=os.open(private/'stderr.log',os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
            with os.fdopen(error_fd,'wb') as errors:
                process=await asyncio.create_subprocess_exec(*args,cwd=folder,env=env,
                    stdin=asyncio.subprocess.DEVNULL,stdout=asyncio.subprocess.PIPE,stderr=errors,
                    start_new_session=True,limit=16*1024*1024)
                while True:
                    line=await process.stdout.readline()
                    if not line:break
                    last_stream=time.monotonic();report['stream_events']+=1
                    try:event=json.loads(line)
                    except ValueError:
                        report['unparsed_lines']=report.get('unparsed_lines',0)+1
                        continue  # Never leak a raw malformed line.
                    item=public_event(event)
                    if item:
                        item['seconds']=round(time.monotonic()-started,2);report['events'].append(item);save()
                    del event,line
                report['exit_code']=await process.wait()
            reasons=[e['stop_reason'] for e in report['events'] if e['type']=='inference']
            report['status']='submitted' if report['exit_code']==0 and reasons and reasons[-1]=='stop' else 'failed'
            report['stderr_bytes']=(private/'stderr.log').stat().st_size
        except Exception as exc:
            report['status']='interrupted' if cancel.is_set() else 'error'
            report['error_type']=type(exc).__name__
        finally:
            done.set();await monitor_task
            if process and process.returncode is None:
                await stop_owned()
                try:await asyncio.wait_for(process.wait(),5)
                except asyncio.TimeoutError:
                    os.killpg(process.pid,signal.SIGKILL);await process.wait()
            await asyncio.to_thread(engine.close)
        report['seconds']=round(time.monotonic()-started,2)
        try:
            suite=subprocess.run([str(ROOT/'.venv/bin/python'),'-m','pytest','-q'],cwd=folder,
                                 capture_output=True,text=True,timeout=180)
            output=suite.stdout+suite.stderr; count=test_summary(output)
            independent=grade(folder,case_name,ROOT)+(check_labels_goal(folder) if case_name=='labels' else check_inventory_goal(folder,ROOT))
            report['project_tests']={'exit_code':suite.returncode,'summary':count,'output':output[-6000:]}
            report['independent_checks']=independent
            report['checks']={'submitted':report['status']=='submitted',
                'runtime_frozen':runtime_digest()==report['runtime_sha256_before'],
                'acceptance_unchanged':file_hash(acceptance)==report['acceptance_sha256'],
                'nonempty_own_and_supplied_tests':suite.returncode==0 and bool(count and count['passed'] and count['count']>6),
                'independent_goal_checks':bool(independent) and all(c['passed'] for c in independent),
                'no_interruption':not report.get('interruption')}
            report['passed']=all(report['checks'].values())
        except Exception as exc:
            report['grading_error_type']=type(exc).__name__;report['passed']=False
        save();archive_report(ROOT,report_path.name,'native','Upstream Pi comparison: '+case_name,report['scope']);refresh_results(ROOT)
        state=json.loads(state_path.read_text());state['active_experiment']=None
        state['last_experiment']={'report':str(report_path.relative_to(ROOT)),'passed':report['passed'],'scope':report['scope']}
        state_path.write_text(json.dumps(state,indent=2)+'\n')
        with (ROOT/'docs/SESSION_LOG.md').open('a') as log:
            log.write('\n'+datetime.now(timezone.utc).isoformat()+' — Pi '+case_name+' outcome: '+json.dumps({'passed':report['passed'],'seconds':report['seconds'],'checks':report.get('checks'),'report':str(report_path.relative_to(ROOT))})+'. No operator product edits/live hints.\n')
        print(json.dumps({'passed':report['passed'],'seconds':report['seconds'],'checks':report.get('checks'),'report':str(report_path)}),flush=True)
        return report['passed']


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('case',choices=('labels','inventory'))
    parser.add_argument('--effort',choices=('low','medium','high'),default='medium');args=parser.parse_args()
    raise SystemExit(0 if asyncio.run(evaluate(args.case,args.effort)) else 1)
