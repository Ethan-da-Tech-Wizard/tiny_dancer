# SPDX-License-Identifier: Apache-2.0
"""Frozen native coding task; operator observes, then checks unseen inputs."""
import hashlib
import json
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import psutil

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'docs/native-coding-validation.json'
PROMPT = (
    'Build a Python command line tool summarize.py that takes a CSV filepath argument '
    'with category,amount columns. Print a JSON object mapping categories to exact monetary totals '
    'as fixed two decimal strings, with keys alphabetically sorted. Amounts are signed finite '
    'decimals with at most two decimal places. Support negative amounts and quoted category '
    'names containing commas. Reject invalid amounts with a nonzero exit status and a clear '
    'error. Use only the standard library. Add relevant tests and run them. Work in this folder.'
)


def independent_checks(folder):
    cases = [
        ('exact decimals and negatives', 'category,amount\nfood,0.10\nfood,0.20\nfood,-0.05\n', {'food':'0.25'}),
        ('quoted category and sorted keys', 'category,amount\nz,1\n"a,b",2.30\nz,-0.25\n', {'a,b':'2.30','z':'0.75'}),
        ('large exact monetary values', 'category,amount\nx,90071992547409.01\nx,0.01\n', {'x':'90071992547409.02'}),
        ('empty dataset', 'category,amount\n', {}),
    ]
    results=[]
    program=folder/'summarize.py'
    if not program.is_file(): return [{'check':'program created','passed':False}]
    with tempfile.TemporaryDirectory(dir=ROOT/'run') as temp:
        source=Path(temp)/'check.csv'
        for title,content,expected in cases:
            source.write_text(content)
            completed=subprocess.run(['/usr/bin/python3',str(program),str(source)],cwd=folder,capture_output=True,text=True,timeout=15)
            try: actual=json.loads(completed.stdout)
            except ValueError: actual=None
            results.append({'check':title,'passed':completed.returncode==0 and actual==expected and list(actual or {})==sorted(expected),
                            'exit_code':completed.returncode,'actual':actual,'stderr':completed.stderr[:1000]})
        for value in ('bad','NaN','Infinity','1.234',''):
            source.write_text('category,amount\nx,'+value+'\n')
            completed=subprocess.run(['/usr/bin/python3',str(program),str(source)],cwd=folder,capture_output=True,text=True,timeout=15)
            results.append({'check':'reject '+repr(value),'passed':completed.returncode!=0 and bool(completed.stderr.strip() or completed.stdout.strip()),
                            'exit_code':completed.returncode,'output':(completed.stderr or completed.stdout)[:1000]})
    return results


def main():
    report={'started_at':datetime.now(timezone.utc).isoformat(),'prompt':PROMPT,
            'prompt_sha256':hashlib.sha256(PROMPT.encode()).hexdigest(),'status':'starting',
            'method':'Fresh native GPT-OSS work task. Only input CSV provided; no implementation, answers, tests or recovery notes supplied by operator during execution. Independent checks run only after termination.',
            'operator_interventions':[],'resource_samples':[]}
    def save(): REPORT.write_text(json.dumps(report,indent=2)+'\n')
    with httpx.Client(base_url='http://127.0.0.1:3210',timeout=15) as client:
        client.get('/').raise_for_status()
        state=client.get('/api/status').json()
        if state['active_job']: raise SystemExit('Another task is active; evaluation not started')
        folder=ROOT/'workspace'/('native-coding-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
        folder.mkdir()
        (folder/'sample.csv').write_text('category,amount\nfood,0.10\nfood,0.20\n"travel, bus",2.50\nfood,-0.05\n')
        report.update(cwd=str(folder),config=state['config']);save()
        response=client.post('/api/sessions',json={'title':'Validation · unassisted Python coding','cwd':str(folder)})
        response.raise_for_status();sid=response.json()['id']
        response=client.post(f'/api/sessions/{sid}/tasks',json={'prompt':PROMPT,'mode':'agent','max_tokens':1024,'task_kind':'work','run_until_done':True})
        response.raise_for_status();job=response.json()['job']
        report.update(job=job,session=sid,status='running');save()
        print(json.dumps({'job':job,'session':sid,'cwd':str(folder),'status':'running'}),flush=True)
        start=time.monotonic()
        while True:
            data=client.get('/api/jobs/'+job+'/progress').json()
            state=client.get('/api/status').json()
            sample={'elapsed_seconds':round(time.monotonic()-start,1),'status':data['status'],'engine':state['engine'],
                    'available_ram_gib':round(state['ram']['available']/2**30,3),'pid':state['model_pid'],
                    'turns':data['checkpoint'].get('turns'),'public_progress':data['progress']}
            if sample['pid']:
                try:
                    process=psutil.Process(sample['pid'])
                    sample.update(nice=process.nice(),uss_gib=round(process.memory_full_info().uss/2**30,3),read_bytes=process.io_counters().read_bytes)
                except psutil.Error: pass
            report['resource_samples'].append(sample);save();print(json.dumps(sample),flush=True)
            if data['status']!='running': break
            if time.monotonic()-start>3600:
                # Only this evaluation, never the user's existing task.
                client.post('/api/jobs/'+job+'/stop').raise_for_status()
                report['operator_interventions'].append('Stopped this evaluation after its explicit one-hour observation limit; not scored as autonomous completion.')
            time.sleep(20)
        full=client.get('/api/jobs/'+job).json()
        events=[{'kind':e['kind'],'data':json.loads(e['data'])} for e in full['events']]
        report.update(status=full['status'],elapsed_seconds=round(time.monotonic()-start,1),checkpoint=full['checkpoint'],
                      metrics=[e['data'] for e in events if e['kind']=='metrics'],
                      tool_calls=[e['data'] for e in events if e['kind']=='tool_start'],
                      harness_continuations=[e['data'] for e in events if e['kind']=='continuation'],
                      errors=[e['data'] for e in events if e['kind']=='error'])
        # No expected results enter native history.
        report['independent_checks']=independent_checks(folder)
        report['passed']=full['status']=='complete' and bool(report['independent_checks']) and all(c['passed'] for c in report['independent_checks']) and not report['operator_interventions']
        report['generated_files']=[{'path':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in folder.glob('*.py')]
        save();print(json.dumps({k:report[k] for k in ('job','status','elapsed_seconds','passed','independent_checks')}),flush=True)
        if not report['passed']: raise SystemExit(1)


if __name__=='__main__': main()
