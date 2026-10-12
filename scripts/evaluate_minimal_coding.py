# SPDX-License-Identifier: Apache-2.0
"""Same-model minimal baseline; original goals, no live hints, held-out grading."""
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
from unittest.mock import patch
import httpx
import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.engine import LocalEngine, Cancelled
from app.tools import ComputerTools, TOOLS
from app.task_policy import contract_for
from app.verification import test_summary
from app.validation_results import archive_report, refresh_results
from scripts.evaluate_hardening_suite import runtime_digest
from scripts.native_suite_cases import CASES, grade
from scripts.labels_goal_audit import CRITERIA as LABEL_CRITERIA, check_labels_goal
from scripts.inventory_goal_audit import CRITERIA as INVENTORY_CRITERIA, check_inventory_goal
from scripts.minimal_coding import INSTRUCTIONS, run_loop


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


async def evaluate(case_name, effort, protocol='raw'):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    case = CASES[case_name]
    folder = ROOT/'workspace'/('minimal-'+case_name+'-'+stamp)
    path = ROOT/'docs'/('minimal-'+case_name+'-'+stamp+'.json')
    private = ROOT/'run'/('minimal-'+stamp+'.history.json')
    client = httpx.AsyncClient(base_url='http://127.0.0.1:3210', trust_env=False, timeout=5)
    await client.get('/')
    response = await client.get('/api/status'); response.raise_for_status()
    status = response.json()
    if status.get('active_job') or status.get('model_pid'):
        await client.aclose()
        raise RuntimeError('Baseline requires production idle and its model unloaded')
    folder.mkdir()
    for name, data in case['inputs'].items():
        target = folder/name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
    acceptance = folder/'test_acceptance.py'; acceptance.write_text(case['acceptance'])
    if protocol=='chat':
        from scripts.llama_chat_baseline import LlamaChatBaselineEngine
        engine=LlamaChatBaselineEngine(INSTRUCTIONS,[t for t in TOOLS if t['name']=='shell'])
    else:engine=LocalEngine()
    computer, flag = ComputerTools(), threading.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM): loop.add_signal_handler(sig, flag.set)
    started = time.monotonic()
    report = {'started_at':datetime.now(timezone.utc).isoformat(), 'status':'running', 'case':case_name,
        'cwd':str(folder), 'prompt':case['prompt'], 'instructions':INSTRUCTIONS,
        'scope':'Experimental minimal shell-only loop inspired by mini-SWE-agent, using the unchanged local GPT-OSS-20B and existing Harmony/backend adapter. Original frozen goals and acceptance seeds. Multiple harness components differ; this is a baseline comparison, not a one-variable attribution or production qualification. No operator source edits or live hints.',
        'runtime_sha256_before':runtime_digest(), 'observer_sha256':{p.name:file_hash(p) for p in (Path(__file__),ROOT/'scripts/minimal_coding.py')},
        'acceptance_sha256':file_hash(acceptance), 'reasoning_effort':effort,
        'protocol':protocol, 'grammar_adapter_sha256':file_hash(ROOT/'scripts/llama_chat_baseline.py') if protocol=='chat' else None,
        'additional_independent_criteria':list(LABEL_CRITERIA if case_name=='labels' else INVENTORY_CRITERIA),
        'operator_interventions':[], 'events':[], 'samples':[]}
    def save():
        temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(path)
    def record(kind, data):
        # No token text, private reasoning or unaccepted final drafts.
        if kind not in ('turn','tool_start','tool_result','inference','metrics'): return
        report['events'].append({'kind':kind,'data':data,'seconds':round(time.monotonic()-started,2)});save()
    def emit(kind, data): loop.call_soon_threadsafe(record, kind, data)
    def save_history(history):
        fd=os.open(private,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w') as handle:json.dump(history,handle)
    contract=contract_for(case['prompt'],'work',cwd=str(folder));contract['_auto_reply_continuation']=True
    def generate(history):
        return engine.generate(history,str(folder),emit,flag,True,2048,contract,effort)
    async def execute(name,args):return await computer.execute(name,args,str(folder))
    monitor_done=asyncio.Event()
    async def monitor():
        low_since=None;last_sample=0
        while not monitor_done.is_set():
            try:
                r=await client.get('/api/status');r.raise_for_status();live=r.json()
                if live.get('active_job') or live.get('model_pid'):
                    report['interruption']='Production model or user task started; only baseline cancelled';flag.set()
                available=psutil.virtual_memory().available/2**30
                now=time.monotonic()
                low_since=(low_since or now) if available<1.5 else None
                if low_since and now-low_since>=6:
                    report['interruption']='Sustained available RAM below1.5GiB';flag.set()
                if flag.is_set():engine.cancel()
                if now-last_sample>=20:
                    sample={'seconds':round(now-started,1),'engine':engine.status,'available_ram_gib':round(available,3),'activity':engine.work_activity()}
                    report['samples'].append(sample);save();print(json.dumps(sample),flush=True);last_sample=now
            except httpx.HTTPError:
                report['interruption']='Cannot confirm production idle';flag.set();engine.cancel()
            try:await asyncio.wait_for(monitor_done.wait(),2)
            except asyncio.TimeoutError:pass
    save();print(json.dumps({'report':str(path),'cwd':str(folder)}),flush=True)
    monitor_task=asyncio.create_task(monitor())
    try:
        with patch('app.engine.instructions_for',lambda c,p:INSTRUCTIONS+'\nWorking folder: '+str(p)), patch('app.engine.tools_for',lambda c,t:[v for v in t if v['name']=='shell']):
            report.update(await run_loop(generate,execute,case['prompt'],flag,record,save_history))
    except Exception as exc:
        report.update(status='interrupted' if flag.is_set() else 'error',error=type(exc).__name__+': '+str(exc))
    finally:
        monitor_done.set();await monitor_task;engine.close();await computer.close();await client.aclose()
    report['seconds']=round(time.monotonic()-started,2)
    suite=subprocess.run([str(ROOT/'.venv/bin/python'),'-m','pytest','-q'],cwd=folder,capture_output=True,text=True,timeout=180)
    output=suite.stdout+suite.stderr
    independent=grade(folder,case_name,ROOT)+(check_labels_goal(folder) if case_name=='labels' else check_inventory_goal(folder,ROOT))
    count=test_summary(output)
    report['project_tests']={'exit_code':suite.returncode,'output':output[-6000:],'summary':count}
    report['independent_checks']=independent
    report['checks']={'submitted':report['status']=='submitted','runtime_frozen':runtime_digest()==report['runtime_sha256_before'],
        'acceptance_unchanged':file_hash(acceptance)==report['acceptance_sha256'],
        'nonempty_own_and_supplied_tests':suite.returncode==0 and bool(count and count['passed'] and count['count']>6),
        'independent_goal_checks':bool(independent) and all(c['passed'] for c in independent),
        'no_interruption':not report.get('interruption')}
    report['passed']=all(report['checks'].values());save()
    archive_report(ROOT,path.name,'native','Minimal local coding baseline: '+case_name,report['scope']);refresh_results(ROOT)
    print(json.dumps({'passed':report['passed'],'checks':report['checks'],'seconds':report['seconds'],'report':str(path)}),flush=True)
    return report['passed']


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('case',choices=('labels','inventory'))
    parser.add_argument('--effort',choices=('medium','high'),default='medium')
    parser.add_argument('--protocol',choices=('raw','chat'),default='raw');args=parser.parse_args()
    raise SystemExit(0 if asyncio.run(evaluate(args.case,args.effort,args.protocol)) else 1)
