# SPDX-License-Identifier: Apache-2.0
"""Continue observing an existing native coding job without changing its task."""
import json
import sys
import time
from datetime import datetime,timezone
from pathlib import Path

import httpx
import psutil

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.validation_results import archive_report,refresh_results
from scripts.coding_acceptance import coding_checks


def main():
    path=ROOT/'docs/hardening-coding-validation.json';report=json.loads(path.read_text())
    report.setdefault('observation_notes',[]).append('Read-only watcher reattached with a one-hour observation window, matching the original CSV baseline. Native goal, history, source, tools and generation remain unchanged; no pause/resume, code or hints were supplied.')
    def save():
        temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(path);refresh_results(ROOT)
    with httpx.Client(base_url='http://127.0.0.1:3210',timeout=20) as client:
        client.get('/').raise_for_status();job=report['job'];full=client.get('/api/jobs/'+job).json()
        assert full['checkpoint']['goal']==report['prompt']
        state=client.get('/api/status').json()
        if full['status']=='running' and state['active_job']!=job:raise SystemExit('Job ownership mismatch')
        started=time.monotonic()-(time.time()-full['created']);save()
        while True:
            progress=client.get('/api/jobs/'+job+'/progress').json();state=client.get('/api/status').json()
            sample={'elapsed_seconds':round(time.monotonic()-started,1),'status':progress['status'],'engine':state['engine'],'available_ram_gib':round(state['ram']['available']/2**30,3),'progress':progress['progress'],'turns':progress['checkpoint'].get('turns')}
            if state.get('model_pid'):
                try:
                    process=psutil.Process(state['model_pid']);cpu=process.cpu_times()
                    sample.update(pid=process.pid,nice=process.nice(),uss_gib=round(process.memory_full_info().uss/2**30,3),cpu_seconds=round(cpu.user+cpu.system,3),read_bytes=process.io_counters().read_bytes)
                except psutil.Error:pass
            report['samples'].append(sample);save();print(json.dumps(sample),flush=True)
            if progress['status']!='running':break
            if time.monotonic()-started>3600:
                client.post('/api/jobs/'+job+'/stop').raise_for_status();report['operator_interventions'].append('Stopped only this evaluation after its one-hour observation window; not scored as autonomous completion.');save()
            time.sleep(20)
        full=client.get('/api/jobs/'+job).json();events=[{'kind':e['kind'],'data':json.loads(e['data'])} for e in full['events']]
        independent,friendly=coding_checks(Path(report['cwd']),ROOT)
        checks={'independent_cli_checks':bool(independent) and all(check['passed'] for check in independent),'clear_invalid_amount_errors':bool(friendly) and all(check['passed'] for check in friendly),'native_verified':full['checkpoint'].get('verified',False),'own_tests_created':bool(list(Path(report['cwd']).rglob('test_*.py')))}
        report.update(status=full['status'],checkpoint=full['checkpoint'],job_elapsed_seconds=round(full['finished']-full['created'],2),metrics=[e['data'] for e in events if e['kind']=='metrics'],tool_calls=[e['data'] for e in events if e['kind']=='tool_start'],
                      independent_checks=independent,clear_error_checks=friendly,checks=checks,errors=[e['data'] for e in events if e['kind']=='error'],harness_continuations=[e['data'] for e in events if e['kind']=='continuation'],
                      generated_files=[{'path':str(p),'bytes':p.stat().st_size} for p in Path(report['cwd']).rglob('*.py')])
        observed=[sample for sample in report['samples'] if 'uss_gib' in sample]
        report['resources']={'minimum_available_ram_gib':min(sample['available_ram_gib'] for sample in report['samples']),'maximum_observed_model_uss_gib':max((sample['uss_gib'] for sample in observed),default=None),'worker_nice_values':sorted({sample['nice'] for sample in observed}),'scope':'20-second observations, not continuous peaks.'}
        report['passed']=full['status']=='complete' and all(checks.values()) and not report['operator_interventions'];save()
        archive_report(ROOT,path.name,'native','Fresh CSV implementation after hardening',report['scope']);refresh_results(ROOT)
        print(json.dumps({k:report[k] for k in ('status','passed','checks','job_elapsed_seconds')}),flush=True)
        if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
