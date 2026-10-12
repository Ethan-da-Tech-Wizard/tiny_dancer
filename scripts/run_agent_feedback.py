# SPDX-License-Identifier: Apache-2.0
"""Run a prepared diagnostic task through the ordinary local agent, one at a time."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.validation_results import archive_report, refresh_results
from scripts.evaluate_hardening_suite import runtime_digest


def valid_feedback(data):
    if not isinstance(data, dict) or data.get('verdict') not in ('proposal', 'no_change', 'insufficient_evidence'):
        return False
    if not all(isinstance(data.get(k), str) for k in ('summary', 'proposed_change', 'test_command')):
        return False
    if not data['summary'].strip():
        return False
    if data['verdict'] == 'proposal' and not (
            data['proposed_change'].strip() and data['test_command'].strip() and data.get('evidence')):
        return False
    return all(isinstance(data.get(k), list) and all(isinstance(v, str) for v in data[k])
               for k in ('evidence', 'risks', 'limitations'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace')
    args = parser.parse_args()
    folder = Path(args.workspace).resolve()
    if not folder.is_relative_to(ROOT / 'workspace') or not folder.name.startswith('agent-feedback-'):
        raise SystemExit('Choose a prepared agent-feedback workspace')
    manifest = json.loads((folder / 'manifest.json').read_text())
    immutable = [folder / name for name in ('manifest.json', 'evidence.json', 'AGENTS.md', 'REQUEST.txt', 'README.md')]
    immutable += [folder / 'source' / record['path'] for record in manifest['sources']]
    before = {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest() for p in immutable}
    runtime = runtime_digest()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    path = ROOT / 'docs' / ('native-agent-feedback-' + stamp + '.json')
    report = {'started_at': datetime.now(timezone.utc).isoformat(), 'status': 'starting',
              'cwd': str(folder), 'runtime_sha256_before': runtime, 'samples': [],
              'scope': 'Actual local model diagnostic proposal on an isolated source copy. Workflow checks do not approve the diagnosis or patch. Independent reproduction/control checks are required.',
              'operator_interventions': [], 'observation_limit_seconds': None}
    def save():
        temp = path.with_suffix('.tmp'); temp.write_text(json.dumps(report, indent=2) + '\n'); temp.replace(path)
    with httpx.Client(base_url='http://127.0.0.1:3210', trust_env=False, timeout=30) as client:
        client.get('/').raise_for_status()
        status = client.get('/api/status'); status.raise_for_status()
        if status.json()['active_job']:
            raise SystemExit('Finish or stop the existing task before starting feedback')
        session = client.post('/api/sessions', json={'title': 'Agent diagnostic feedback', 'cwd': str(folder)})
        session.raise_for_status(); sid = session.json()['id']
        response = client.post('/api/sessions/' + sid + '/tasks', json={
            'prompt': (folder / 'REQUEST.txt').read_text(), 'mode': 'agent', 'task_kind': 'work',
            'run_until_done': True, 'max_tokens': None, 'reasoning_effort': 'medium'})
        response.raise_for_status(); job = response.json()['job']
        report.update(status='running', job=job, session=sid); save()
        print(json.dumps({'job': job, 'report': str(path), 'workspace': str(folder)}), flush=True)
        started = time.monotonic()
        while True:
            response = client.get('/api/jobs/' + job + '/progress'); response.raise_for_status()
            progress = response.json(); state = progress.get('checkpoint', {})
            sample = {'elapsed_seconds': round(time.monotonic() - started, 1), 'status': progress['status'],
                      'turns': state.get('turns'), 'verified': state.get('verified', False)}
            report['samples'].append(sample); save(); print(json.dumps(sample), flush=True)
            if progress['status'] != 'running': break
            time.sleep(20)
    try: feedback = json.loads((folder / 'feedback.json').read_text())
    except (OSError, ValueError): feedback = None
    unchanged = all(p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == before[str(p.relative_to(folder))]
                    for p in immutable)
    checks = {'agent_completed': progress['status'] == 'complete', 'feedback_schema': valid_feedback(feedback),
              'original_evidence_unchanged': unchanged, 'runtime_frozen': runtime_digest() == runtime}
    report.update(status=progress['status'], passed=all(checks.values()), checks=checks,
                  seconds=round(time.monotonic() - started, 2),
                  verdict=feedback.get('verdict') if isinstance(feedback, dict) else None,
                  independent_proposal_validation='pending; not approved by workflow checks')
    save(); archive_report(ROOT, path.name, 'native', 'Local agent diagnostic contribution', report['scope']); refresh_results(ROOT)
    print(json.dumps({'report': str(path), 'checks': checks, 'proposal_approved': False}), flush=True)
    if not report['passed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
