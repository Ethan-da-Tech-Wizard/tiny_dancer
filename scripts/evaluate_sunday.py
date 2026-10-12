# SPDX-License-Identifier: Apache-2.0
"""Run the original user question, then independently refetch its score reference."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import psutil

ROOT = Path('/mnt/GameDrive/tiny_dancer')
REPORT = ROOT / 'docs/answer-completion-validation.json'
PROMPT = 'tell me all the stats of the most recent nfl sunday football list by stats i mean scores and what teams played eachother'


def main():
    report = {'started_at':datetime.now(timezone.utc).isoformat(), 'prompt':PROMPT,
              'method':'Native GPT-OSS selects a typed tool; harness publishes validated data. No scores or reference answers supplied to model.',
              'status':'starting', 'resource_samples':[]}
    def save(): REPORT.write_text(json.dumps(report,indent=2)+'\n')
    with httpx.Client(base_url='http://127.0.0.1:3210',timeout=30) as client:
        client.get('/').raise_for_status()
        initial=client.get('/api/status').json()
        if initial['active_job']: raise SystemExit('Another task is active; no evaluation started')
        report['initial_engine']=initial['engine']
        sessions=client.get('/api/sessions').json()
        previous=next((s for s in sessions if s['id']=='e49878f2e88542cdaefe0fe660e32307'),None)
        if not previous:
            previous=client.post('/api/sessions',json={'title':'Validation · original Sunday question'}).json()
        sid=previous['id']
        response=client.post(f'/api/sessions/{sid}/tasks',json={'prompt':PROMPT,'mode':'agent','max_tokens':512})
        response.raise_for_status()
        job=response.json()['job']
        report.update(job=job,session=sid,status='running');save()
        print(json.dumps({'job':job,'status':'running'}),flush=True)
        started=time.monotonic(); last_report=-30
        while time.monotonic()-started < 660:
            data=client.get('/api/jobs/'+job).json()
            if time.monotonic()-started-last_report >= 30:
                state=client.get('/api/status').json()
                sample={'elapsed_seconds':round(time.monotonic()-started,2),'engine':state['engine'],'model_pid':state['model_pid']}
                if state['model_pid']:
                    try:
                        process=psutil.Process(state['model_pid'])
                        sample.update(rss_gib=round(process.memory_info().rss/2**30,3),
                                      uss_gib=round(process.memory_full_info().uss/2**30,3),
                                      cpu_seconds=sum(process.cpu_times()[:2]),read_bytes=process.io_counters().read_bytes)
                    except psutil.NoSuchProcess: pass
                report['resource_samples'].append(sample);save();print(json.dumps(sample),flush=True)
                last_report=time.monotonic()-started
            if data['status']!='running': break
            time.sleep(1)
        report.update(status=data['status'],elapsed_seconds=round(time.monotonic()-started,2),checkpoint=data['checkpoint'])
        decoded=[{'kind':e['kind'],'data':json.loads(e['data'])} for e in data['events']]
        report['metrics']=[e['data'] for e in decoded if e['kind']=='metrics']
        report['tool_calls']=[e['data'] for e in decoded if e['kind']=='tool_start']
        report['errors']=[e['data'] for e in decoded if e['kind']=='error']
        results=[json.loads(e['data']['result']) for e in decoded if e['kind']=='tool_result' and e['data']['name']=='nfl_scores']
        report['comparison']={'passed':False}
        save()
        if data['status']=='complete' and results and results[-1].get('ok'):
            result=results[-1]
            # Reference fetched only AFTER the run. No operator recovery input.
            raw=httpx.get(result['source'],timeout=30)
            raw.raise_for_status(); reference=raw.json()
            expected={}
            for event in reference['events']:
                rows=event['competitions'][0]['competitors']
                expected[event['id']]={r['homeAway']:(r['team']['displayName'],int(r['score'])) for r in rows}
                assert event['competitions'][0]['status']['type']['completed']
            actual={g['id']:{'home':(g['home'],g['home_score']),'away':(g['away'],g['away_score'])} for g in result['games']}
            report['comparison']={'passed':actual==expected,'games':len(expected),'date':result['date'],
                                  'source':result['source'],'note':'Independent HTTP retrieval of the same primary scoreboard, not a second publisher.'}
        save(); print(json.dumps({k:report[k] for k in ('job','status','elapsed_seconds','comparison')}),flush=True)
        if report['status']!='complete' or not report['comparison']['passed']: raise SystemExit(1)


if __name__=='__main__':main()
