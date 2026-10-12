# SPDX-License-Identifier: Apache-2.0
"""Idle-only same-model executable verification probe; no production mutation."""
import asyncio
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import signal
import sys
import threading
import time
import httpx
import psutil

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from openai_harmony import Message,Role
from scripts.audit_test_probe import INSTRUCTIONS,TOOL,submitted_code,grade_verification
from scripts.llama_chat_baseline import LlamaChatBaselineEngine
from scripts.native_suite_cases import CASES
from scripts.evaluate_hardening_suite import runtime_digest
from app.working_memory import runtime_source_evidence
from app.validation_results import archive_report,refresh_results


async def evaluate(spec_only=False):
    client=httpx.AsyncClient(base_url='http://127.0.0.1:3210',trust_env=False,timeout=5)
    await client.get('/');status=(await client.get('/api/status')).json()
    if status.get('active_job') or status.get('model_pid'):
        await client.aclose();raise RuntimeError('Probe requires production idle/model unloaded')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder=ROOT/'workspace'/('audit-test-probe-'+stamp);folder.mkdir()
    source=ROOT/'workspace/native-inventory-20261012T021158830837Z/inventory.py'
    program=source.read_text();(folder/'inventory.py').write_text(program)
    conforming=(ROOT/'scripts/fixtures/inventory_reference.py').read_text()
    (folder/'CONTRACT.md').write_text(CASES['inventory']['prompt'])
    prompt='Generate executable verification of the existing program. Return audit_tests.py through write_verification.\n\nOriginal requirements (the program contract, not a request to edit the implementation):\n'+CASES['inventory']['prompt']
    if not spec_only:prompt+='\n\nCurrent implementation:\n<source>\n'+program+'\n</source>'
    prompt+='\n\nSource-derived standard-library facts (advisory, not a verdict):\n'+json.dumps(runtime_source_evidence(folder,[str(folder/'inventory.py')]))
    instructions=INSTRUCTIONS.replace('Examine the supplied current source and documented API behavior.','Use the original requirements and documented API behavior; the implementation is intentionally withheld.') if spec_only else INSTRUCTIONS
    path=ROOT/'docs'/('audit-test-probe-'+stamp+'.json');started=time.monotonic();flag=threading.Event()
    engine=LlamaChatBaselineEngine(instructions,[TOOL]);loop=asyncio.get_running_loop()
    for sig in (signal.SIGINT,signal.SIGTERM):loop.add_signal_handler(sig,flag.set)
    report={'started_at':datetime.now(timezone.utc).isoformat(),'status':'running','scope':'One local-model test-writing response receives original goal, current source and existing generic API facts. No hidden examples, outcome hints, implementation edits or pass/fail self-rating. Identical generated tests are executed against flawed and separately graded operator-written positive TEST CONTROL. Positive source is never sent to the model. Not production qualification.',
            'source_report':'docs/native-inventory-20261012T021158830837Z.json','cwd':str(folder),'runtime_sha256_before':runtime_digest(),
            'criteria':{'nonempty_same_tests':True,'assertion_failure_on_flawed':True,'no_errors_on_flawed':True,'all_pass_on_conforming':True,'zero_skips':True,'implementations_unchanged':True},
            'program_sha256':hashlib.sha256(program.encode()).hexdigest(),'conforming_sha256':hashlib.sha256(conforming.encode()).hexdigest(),
            'instructions':instructions,'prompt':prompt,'implementation_withheld':spec_only,
            'observer_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'scripts/audit_test_probe.py',ROOT/'scripts/llama_chat_baseline.py']},
            'effort':'medium','operator_interventions':[],'metrics':[],'samples':[]}
    if spec_only:report['scope']=report['scope'].replace('original goal, current source and existing generic API facts','original goal and existing generic API facts, with implementation source withheld')
    def save():
        temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(path)
    def record(kind,data):
        if kind=='metrics':report['metrics'].append(data);save()
    def emit(kind,data):loop.call_soon_threadsafe(record,kind,data)
    done=asyncio.Event()
    async def monitor():
        low_since=None;last=0
        while not done.is_set():
            now=time.monotonic()
            try:
                live=(await client.get('/api/status')).json()
                if live.get('active_job') or live.get('model_pid'):report['interruption']='Production task/model started';flag.set()
                available=psutil.virtual_memory().available/2**30
                low_since=(low_since or now) if available<1.5 else None
                if low_since and now-low_since>=6:report['interruption']='Sustained memory pressure';flag.set()
                if flag.is_set():engine.cancel()
                if now-last>=20:
                    sample={'seconds':round(now-started,1),'engine':engine.status,'available_ram_gib':round(available,3),'activity':engine.work_activity()}
                    report['samples'].append(sample);save();print(json.dumps(sample),flush=True);last=now
            except httpx.HTTPError:report['interruption']='Unable to confirm production idle';flag.set();engine.cancel()
            try:await asyncio.wait_for(done.wait(),2)
            except asyncio.TimeoutError:pass
    save();print(json.dumps({'report':str(path),'cwd':str(folder)}),flush=True);watch=asyncio.create_task(monitor())
    try:
        history=[Message.from_role_and_content(Role.USER,prompt).to_dict()]
        replies,reason=await asyncio.to_thread(engine.generate,history,str(folder),emit,flag,True,2048,
            {'kind':'work','workflow':None,'lookup_languages':['python'],'toolsets':[],'_auto_reply_continuation':True},'medium')
        if reason!='EOS' or flag.is_set():raise ValueError('No complete uncancelled verification submission')
        code=submitted_code(replies);(folder/'audit_tests.py').write_text(code)
        report['generated_test_sha256']=hashlib.sha256(code.encode()).hexdigest()
        report['private_reasoning_characters']=sum(len(c.text) for m in replies if not m.recipient and m.channel=='analysis' for c in m.content if hasattr(c,'text'))
        report['status']='generated'
    except Exception as exc:
        report.update(status='interrupted' if flag.is_set() else 'failed',error=type(exc).__name__+': '+str(exc),passed=False)
    finally:
        done.set();await watch;engine.close();await client.aclose()
    if report['status']=='generated':
        report['verification']=grade_verification(program,conforming,code,ROOT)
        report.update(status='complete',passed=report['verification']['passed'])
    report['runtime_sha256_after']=runtime_digest();report['runtime_frozen']=report['runtime_sha256_after']==report['runtime_sha256_before']
    report['passed']=report.get('passed',False) and report['runtime_frozen'] and not report.get('interruption')
    report['elapsed_seconds']=round(time.monotonic()-started,2);save()
    archive_report(ROOT,path.name,'native','Executable requirement-check generation probe',report['scope']);refresh_results(ROOT)
    print(json.dumps({'passed':report['passed'],'status':report['status'],'seconds':report['elapsed_seconds'],'report':str(path)}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--spec-only',action='store_true');args=parser.parse_args()
    asyncio.run(evaluate(args.spec_only))
