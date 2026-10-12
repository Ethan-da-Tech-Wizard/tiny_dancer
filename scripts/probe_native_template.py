# SPDX-License-Identifier: Apache-2.0
"""Exact staged backend/template check, plus two real native instruction receipts."""
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import threading
import time
import httpx
import psutil

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.native_chat import ChatStream
from app.engine import text_of_message
from app.validation_results import archive_report,refresh_results


def main():
    stage=ROOT/'run/staging/native-read-timeout'
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    path=ROOT/'docs'/('native-template-candidate-'+stamp+'.json')
    report={'started_at':datetime.now(timezone.utc).isoformat(),'status':'running','passed':False,
        'scope':'Exact staged llama.cpp template formatting with synthetic messages, then two actual same-model instruction-following tool receipts. No coding task or general capability claim; no native private text emitted.',
        'checks':{},'receipts':[]}
    def save():
        temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(path)
    with httpx.Client(base_url='http://127.0.0.1:3210',trust_env=False,timeout=5) as control:
        control.get('/');s=control.get('/api/status').json()
        if s['active_job'] or s['model_pid']:raise RuntimeError('Probe needs production idle and model unloaded')
        if psutil.virtual_memory().available<4.5*2**30:raise RuntimeError('Startup RAM reserve unavailable')
        spec=importlib.util.spec_from_file_location('staged_llama_session',stage/'app/llama_session.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        cfg=json.loads((stage/'config.json').read_text())
        cfg['llama_chat_template_file']=str((stage/'app/templates/gpt-oss-agent.jinja').relative_to(ROOT))
        report['template_sha256']=cfg['llama_chat_template_sha256']
        save();print(json.dumps({'report':str(path),'phase':'loading staged backend'}),flush=True)
        done=threading.Event();owned={};session=None;started=time.monotonic()
        def on_start(proc):
            owned['proc']=proc;psutil.Process(proc.pid).nice(5)
        def watch():
            low_since=None;last_activity=time.monotonic();previous=None;last_sample=0
            while not done.wait(2):
                try:
                    live=control.get('/api/status').json();now=time.monotonic();available=psutil.virtual_memory().available/2**30
                    proc=owned.get('proc')
                    if proc and proc.poll() is None:
                        p=psutil.Process(proc.pid);cpu=p.cpu_times();io=p.io_counters();activity=(cpu.user+cpu.system,io.read_bytes,io.write_bytes)
                        if activity!=previous:last_activity=now;previous=activity
                    low_since=(low_since or now) if available<1.5 else None
                    reason='Production task/model started' if live['active_job'] or live['model_pid'] else 'Sustained RAM pressure' if low_since and now-low_since>=6 else 'No inference activity for900seconds' if now-last_activity>=900 else None
                    if reason:
                        report['interruption']=reason
                        if proc and proc.poll() is None:proc.terminate()
                        return
                    if now-last_sample>=20:
                        print(json.dumps({'seconds':round(now-started,1),'available_ram_gib':round(available,3),'native_receipts':len(report['receipts'])}),flush=True);last_sample=now
                except (httpx.HTTPError,psutil.Error,KeyError):
                    report['interruption']='Unable to confirm safe isolated state'
                    proc=owned.get('proc')
                    if proc and proc.poll() is None:proc.terminate()
                    return
        watcher=threading.Thread(target=watch,daemon=True);watcher.start()
        try:
            session=module.LlamaReferenceSession(ROOT,cfg,on_start)
            tool={'type':'function','function':{'name':'emit_receipt','description':'Record the requested marker.',
                'parameters':{'type':'object','properties':{'marker':{'type':'string'}},'required':['marker']}}}
            messages=[{'role':'system','content':'fixture_base_policy'}, {'role':'developer','content':'fixture_extra_policy'},
                {'role':'user','content':'fixture_goal'}, {'role':'assistant','reasoning_content':'fixture_tool_analysis',
                    'tool_calls':[{'id':'call_fixture','type':'function','function':{'name':'emit_receipt','arguments':'{"marker":"prior"}'}}]},
                {'role':'tool','tool_call_id':'call_fixture','content':'fixture_tool_result'},
                {'role':'assistant','reasoning_content':'fixture_unfinished_analysis','content':''},
                {'role':'developer','content':'fixture_checkpoint_review'}]
            payload={'messages':messages,'tools':[tool],'reasoning_effort':'medium','add_generation_prompt':True}
            response=session.client.post('/apply-template',json=payload);response.raise_for_status();prompt=response.json()['prompt']
            markers=['fixture_base_policy','fixture_extra_policy','fixture_goal','fixture_tool_analysis','fixture_tool_result','fixture_unfinished_analysis','fixture_checkpoint_review']
            report['markers_present']={marker:marker in prompt for marker in markers}
            report['checks']['every_message_survives_exact_native_formatter']=all(report['markers_present'].values())
            report['checks']['chronology_preserved']=all(marker in prompt for marker in markers) and [prompt.index(m) for m in markers]==sorted(prompt.index(m) for m in markers)
            report['checks']['late_update_has_developer_role']='<|start|>developer<|message|>fixture_checkpoint_review<|end|>' in prompt
            report['checks']['unfinished_analysis_not_fake_final']='<|channel|>analysis<|message|>fixture_unfinished_analysis<|end|>' in prompt
            save()
            if not all(report['checks'].values()):raise RuntimeError('Native formatter fidelity failed')
            for index,marker in enumerate(('after-review-208','after-checkpoint-317')):
                messages=[{'role':'system','content':'Follow developer instructions and use emit_receipt exactly once.'},
                    {'role':'user','content':'Emit marker before-update-101.'}]
                if index:messages.append({'role':'assistant','content':'','reasoning_content':'Synthetic unfinished history marker.'})
                messages.append({'role':'developer','content':'The requested marker has been updated. Call emit_receipt with marker '+marker+'.'})
                payload={'messages':messages,'tools':[tool],'tool_choice':'required','parallel_tool_calls':False,
                    'reasoning_effort':'medium','reasoning_format':'deepseek','stream':True,'stream_options':{'include_usage':True},
                    'temperature':1.0,'top_p':1.0,'top_k':0,'min_p':0.0,'repeat_penalty':1.0,'max_tokens':2048}
                stream=ChatStream();step=time.monotonic()
                with session.client.stream('POST','/v1/chat/completions',json=payload,timeout=None) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if line.startswith('data:'):
                            raw=line[5:].strip()
                            if raw=='[DONE]':break
                            stream.accept(json.loads(raw))
                replies,reason=stream.replies({'emit_receipt'})
                calls=[m for m in replies if m.recipient=='functions.emit_receipt']
                correct=reason=='EOS' and len(calls)==1 and json.loads(text_of_message(calls[0]))=={'marker':marker}
                receipt={'case':'checkpoint' if index else 'late_review','passed':correct,'seconds':round(time.monotonic()-step,2),
                    'completion_tokens':stream.usage.get('completion_tokens'),'private_characters':sum(map(len,stream.reasoning))}
                report['receipts'].append(receipt);report['checks'][receipt['case']+'_native_receipt']=correct;save();print(json.dumps(receipt),flush=True)
            report['passed']=all(report['checks'].values()) and not report.get('interruption');report['status']='complete'
        except Exception as exc:
            report['status']='failed';report['error_type']=type(exc).__name__;report['passed']=False
        finally:
            done.set();watcher.join(6)
            if session:session.close()
        report['seconds']=round(time.monotonic()-started,2);save()
        archive_report(ROOT,path.name,'native','Exact template and native steering receipts',report['scope']);refresh_results(ROOT)
        print(json.dumps({'passed':report['passed'],'checks':report['checks'],'seconds':report['seconds'],'report':str(path)}),flush=True)
        return report['passed']


if __name__=='__main__':raise SystemExit(0 if main() else 1)
