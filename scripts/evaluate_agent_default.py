# SPDX-License-Identifier: Apache-2.0
"""Real API default/answer smoke, using public facts and no aggregate cutoff."""
from datetime import datetime,timezone
import json
from pathlib import Path
import sqlite3
import sys
import time

import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.validation_results import archive_report,refresh_results
from scripts.check_native_release import runtime_fingerprint

EXPECTED='TINY_DANCER_READY'


def main():
    path=ROOT/'docs/agent-default-native-validation.json'
    if path.exists():
        archive_report(ROOT,path.name,'native','Previous API-default smoke','Previous tiny answer/API-policy probe, not coding qualification.')
    report={'started_at':datetime.now(timezone.utc).isoformat(),'status':'starting',
            'scope':'Actual local-model tiny answer with run_until_done omitted from the API request. Tests deployed Agent defaults and sampling; not coding, long-context or general autonomous capability.',
            'runtime_sha256_before':runtime_fingerprint(ROOT),'observation_limit_seconds':None,
            'operator_interventions':[],'samples':[],'request':{'prompt':'Reply with exactly '+EXPECTED+'.','mode':'agent','task_kind':'answer','reasoning_effort':'low'}}
    def save():
        temp=path.with_suffix('.tmp');temp.write_text(json.dumps(report,indent=2)+'\n');temp.replace(path)
    with httpx.Client(base_url='http://127.0.0.1:3210',trust_env=False,timeout=10) as client:
        client.get('/').raise_for_status();response=client.get('/api/status');response.raise_for_status()
        if response.json()['active_job']:raise SystemExit('Refusing concurrent native evaluation')
        response=client.post('/api/sessions',json={'title':'Validation · continuous Agent API default','cwd':str(ROOT/'workspace')});response.raise_for_status();sid=response.json()['id']
        response=client.post('/api/sessions/'+sid+'/tasks',json=report['request']);response.raise_for_status();job=response.json()['job']
        report.update(status='running',job=job,session=sid);save();print(json.dumps({'job':job,'report':str(path)}),flush=True)
        started=time.monotonic()
        while True:
            response=client.get('/api/jobs/'+job+'/progress');response.raise_for_status();progress=response.json()
            response=client.get('/api/status');response.raise_for_status();status=response.json()
            checkpoint=progress['checkpoint']
            sample={'elapsed_seconds':round(time.monotonic()-started,2),'status':progress['status'],
                    'run_until_done':checkpoint.get('run_until_done'),'max_seconds':checkpoint.get('max_seconds'),
                    'max_turns':checkpoint.get('max_turns'),'available_ram_gib':status['ram']['available']/2**30}
            report['samples'].append(sample);save()
            if progress['status']!='running':break
            time.sleep(10)
    with sqlite3.connect(f'file:{ROOT/"run/workspace.sqlite3"}?mode=ro',uri=True) as db:
        finals=[r[0].strip() for r in db.execute("SELECT text FROM messages WHERE session=? AND role='assistant' AND json_extract(harmony,'$.channel')='final' ORDER BY id",(sid,))]
        metrics=[json.loads(r[0]) for r in db.execute("SELECT data FROM events WHERE job=? AND kind='metrics' ORDER BY id",(job,))]
    expected_sampling={'sampling_temperature':1.0,'sampling_top_p':1.0,'sampling_top_k':0,'sampling_min_p':0.0,'sampling_repeat_penalty':1.0}
    report['runtime_sha256_after']=runtime_fingerprint(ROOT)
    checks={'native_final_complete':progress['status']=='complete' and finals==[EXPECTED],
            'implicit_agent_policy_continuous':bool(report['samples']) and all(s['run_until_done'] is True and s['max_seconds'] is None and s['max_turns'] is None for s in report['samples']),
            'actual_native_recommended_sampling':bool(metrics) and all(m.get('backend')=='llama.cpp-native-mxfp4' and all(m.get(k)==v for k,v in expected_sampling.items()) for m in metrics),
            'runtime_frozen':report['runtime_sha256_before']==report['runtime_sha256_after'],
            'desktop_ram_reserve':all(s['available_ram_gib']>=1.5 for s in report['samples']),
            'no_operator_intervention':not report['operator_interventions']}
    report.update(status=progress['status'],passed=all(checks.values()),checks=checks,finals=finals,metrics=metrics,
                  elapsed_seconds=round(time.monotonic()-started,2),finished_at=datetime.now(timezone.utc).isoformat())
    save();archive_report(ROOT,path.name,'native','Continuous Agent API default and native sampler',report['scope']);refresh_results(ROOT)
    print(json.dumps({k:report[k] for k in ('status','passed','checks','elapsed_seconds')}),flush=True)
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
