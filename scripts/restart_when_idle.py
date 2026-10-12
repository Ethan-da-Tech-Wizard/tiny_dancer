# SPDX-License-Identifier: Apache-2.0
"""Restart only after both the service and its durable job table report idle."""
import argparse
import json
import sqlite3
import subprocess
import time
from pathlib import Path

import httpx

ROOT = Path('/mnt/GameDrive/tiny_dancer')

def wait_for_ready(max_seconds=20):
    deadline=time.monotonic()+max_seconds
    last_error='No response'
    with httpx.Client(base_url='http://127.0.0.1:3210',timeout=1) as client:
        while True:
            try:
                client.get('/').raise_for_status()
                response=client.get('/api/status');response.raise_for_status()
                return response.json()
            except (httpx.HTTPError,ValueError) as exc:last_error=str(exc)
            if time.monotonic()>=deadline:
                raise RuntimeError('Service restarted but did not become ready: '+last_error)
            time.sleep(0.2)


def guarded_restart(wait_seconds=0):
    deadline = time.monotonic() + max(0, wait_seconds)
    announced = False
    with httpx.Client(base_url='http://127.0.0.1:3210', timeout=15) as client:
        client.get('/').raise_for_status()
        while True:
            response = client.get('/api/status')
            response.raise_for_status()
            active = response.json()['active_job']
            with sqlite3.connect(f'file:{ROOT / "run/workspace.sqlite3"}?mode=ro', uri=True) as db:
                running = [r[0] for r in db.execute("SELECT id FROM jobs WHERE status='running'")]
            if not active and not running:
                break
            if time.monotonic() >= deadline:
                raise SystemExit('Refusing restart: a task is running. Stop it explicitly or wait for completion.')
            if not announced:
                print('Waiting for active tasks; inference continues uninterrupted.', flush=True)
                announced = True
            time.sleep(2)
    # Keep the guard and restart in the same process: failures cannot fall
    # through to a later shell command, as happened during the initial upgrade.
    subprocess.run(['systemctl', '--user', 'restart', 'tiny-dancer.service'], check=True)
    wait_for_ready()
    record = {'at':time.time(), 'kind':'idle_service_restart',
              'data':{'active_job':active, 'running_jobs':running,'ready':True}}
    with (ROOT / 'logs/agent-audit.jsonl').open('a') as file:
        file.write(json.dumps(record)+'\n')
    print('Service restarted after the idle checks passed; authenticated API is ready.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wait-seconds', type=int, default=0,
                        help='Wait for active tasks; default refuses immediately.')
    args = parser.parse_args()
    guarded_restart(args.wait_seconds)

if __name__ == '__main__':
    main()
