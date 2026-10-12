# SPDX-License-Identifier: Apache-2.0
"""Bounded real-model long-context receipt; no agent completion claim."""
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.validation_results import archive_report, refresh_results
from scripts.check_native_release import runtime_fingerprint

EXPECTED = 'ALPHA=17; OMEGA=29'
LIMIT_SECONDS = 180


def make_prompt():
    return ('Read the reference records and return only the ALPHA and OMEGA values, '
            'in the form ALPHA=<value>; OMEGA=<value>.\nALPHA=17\n' + ''.join(
                f'r{i}={i * 17};\n' for i in range(1500)) + '\nOMEGA=29\n')


def checks_for(status, finals, metrics, before, after, samples, interventions):
    return {
        'native_final_complete': status == 'complete' and finals == [EXPECTED],
        'actual_prompt_over_8192': any(type(m.get('prompt_tokens')) is int and m['prompt_tokens'] > 8192 for m in metrics),
        'native_backend': bool(metrics) and all(m.get('backend') == 'llama.cpp-native-mxfp4' for m in metrics),
        'runtime_frozen': bool(before) and before == after,
        'desktop_ram_reserve': bool(samples) and all(s['available_ram_gib'] >= 1.5 for s in samples),
        'desktop_vram_reserve': bool(samples) and all(s['free_vram_mib'] >= 1500 for s in samples),
        'no_operator_intervention': not interventions,
    }


def main():
    report = {'started_at': datetime.now(timezone.utc).isoformat(), 'status': 'starting', 'passed': False,
              'scope': 'Actual local GPT-OSS final and native token/memory receipts for a prompt longer than8192. '
                       'This is a long-context retrieval smoke, not a coding qualification, speed claim or general quality proof.',
              'observation_seconds': LIMIT_SECONDS, 'expected': EXPECTED, 'samples': [], 'operator_interventions': []}
    path = ROOT / 'docs/context-capacity-native-validation.json'
    if path.exists():
        archive_report(ROOT, path.name, 'native', 'Previous long-context receipt', report['scope'])

    def save():
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(report, indent=2) + '\n')
        temporary.replace(path)
        refresh_results(ROOT)

    with httpx.Client(base_url='http://127.0.0.1:3210', trust_env=False, timeout=10) as client:
        client.get('/').raise_for_status()
        response = client.get('/api/status'); response.raise_for_status(); status = response.json()
        if status.get('active_job'):
            raise SystemExit('Refusing long-context probe while a task is active')
        if status['config'].get('context') != 32768 or status['config'].get('backend') != 'llama.cpp':
            raise SystemExit('This declared context32768/native probe does not match the loaded application configuration')
        report['runtime_sha256_before'] = runtime_fingerprint(ROOT)
        report['context'] = status['config']['context']
        response = client.post('/api/sessions', json={'title': 'Validation · long-context receipt', 'cwd': str(ROOT / 'workspace')})
        response.raise_for_status(); sid = response.json()['id']
        response = client.post('/api/sessions/' + sid + '/tasks', json={
            'prompt': make_prompt(), 'mode': 'chat', 'max_tokens': 256, 'reasoning_effort': 'low',
            'run_until_done': False, 'max_seconds': LIMIT_SECONDS})
        response.raise_for_status(); job = response.json()['job']
        report.update(status='running', job=job, session=sid); save()
        start = time.monotonic(); stopped = False
        while True:
            response = client.get('/api/jobs/' + job + '/progress'); response.raise_for_status(); progress = response.json()
            response = client.get('/api/status'); response.raise_for_status(); status = response.json()
            memory = subprocess.run(['nvidia-smi', '--query-gpu=memory.free', '--format=csv,noheader,nounits'],
                                    capture_output=True, text=True, timeout=3, check=True)
            report['samples'].append({'elapsed_seconds': round(time.monotonic() - start, 2),
                                      'available_ram_gib': status['ram']['available'] / 2**30,
                                      'free_vram_mib': float(memory.stdout.strip().splitlines()[0])})
            save()
            if progress['status'] != 'running':
                break
            resource_failure = report['samples'][-1]['available_ram_gib'] < 1.5 or report['samples'][-1]['free_vram_mib'] < 1500
            if not stopped and (time.monotonic() - start >= LIMIT_SECONDS or resource_failure):
                stopped = True
                client.post('/api/jobs/' + job + '/stop').raise_for_status()
                report['operator_interventions'].append('Stopped only this probe at its declared time or desktop memory reserve')
            time.sleep(2)
    with sqlite3.connect(f'file:{ROOT / "run/workspace.sqlite3"}?mode=ro', uri=True) as db:
        finals = [r[0].strip() for r in db.execute(
            "SELECT text FROM messages WHERE session=? AND role='assistant' AND json_extract(harmony,'$.channel')='final' ORDER BY id", (sid,))]
        metrics = [json.loads(r[0]) for r in db.execute("SELECT data FROM events WHERE job=? AND kind='metrics' ORDER BY id", (job,))]
    report['finals'] = finals
    report['metrics'] = metrics
    report['runtime_sha256_after'] = runtime_fingerprint(ROOT)
    report['checks'] = checks_for(progress['status'], finals, metrics, report['runtime_sha256_before'],
                                  report['runtime_sha256_after'], report['samples'], report['operator_interventions'])
    report.update(status=progress['status'], passed=all(report['checks'].values()),
                  seconds=round(time.monotonic() - start, 2), finished_at=datetime.now(timezone.utc).isoformat())
    save(); archive_report(ROOT, path.name, 'native', 'Native long-context receipt', report['scope']); refresh_results(ROOT)
    print(json.dumps({'status': report['status'], 'passed': report['passed'], 'checks': report['checks'],
                      'seconds': report['seconds'], 'report': str(path)}, indent=2), flush=True)
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
