# SPDX-License-Identifier: Apache-2.0
"""Install an identical, atomic model cache while local inference is idle."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

import httpx
import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.model_cache import install_cache, select_model
from app.validation_results import archive_report, refresh_results
from scripts.benchmark_cpu_threads import require_idle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', help='Optional cache location; otherwise uses model_cache.directory or XDG cache')
    parser.add_argument('--reserve-gib', type=int, default=10)
    parser.add_argument('--status', action='store_true', help='Verify selection only; do not copy or alter configuration')
    args = parser.parse_args()
    config = json.loads((ROOT / 'config.json').read_text())
    config['model_cache'] = dict(config.get('model_cache', {}), enabled=True)
    if args.directory:
        config['model_cache']['directory'] = args.directory
    # Status can read the whole cache on first verification; keep it away from live inference too.
    with httpx.Client(base_url='http://127.0.0.1:3210', trust_env=False, timeout=5) as control:
        control.get('/').raise_for_status(); require_idle(control)
        if any(p.info['name'] in ('llama-server', 'picchio') for p in psutil.process_iter(['name'])):
            raise SystemExit('Finish the existing inference process before cache work')
        if args.status:
            print(json.dumps(select_model(ROOT, config)[1], indent=2)); return
        now = datetime.now(timezone.utc)
        report_path = ROOT / 'docs' / ('model-cache-install-' + now.strftime('%Y%m%dT%H%M%S%fZ') + '.json')
        report = {'started_at': now.isoformat(), 'status': 'running', 'passed': False,
                  'scope': 'Actual identical model copy, destination SHA-256 readback, preserved source and upstream notices. No inference speed claim.'}
        def save():
            temporary = report_path.with_suffix('.tmp')
            temporary.write_text(json.dumps(report, indent=2) + '\n'); temporary.replace(report_path)
        last = [0.0]
        def progress(copied, total):
            now = time.monotonic()
            if now - last[0] < 5 and copied < total: return
            last[0] = now
            require_idle(control)
            report['copied_bytes'] = copied; report['total_bytes'] = total; save()
            print(json.dumps({'copied_gib': round(copied / 2**30, 2), 'total_gib': round(total / 2**30, 2)}), flush=True)
        save(); print(json.dumps({'report': str(report_path)}), flush=True)
        try:
            report['installation'] = install_cache(ROOT, config, reserve_bytes=args.reserve_gib * 2**30, progress=progress)
            report.update(status='complete', passed=report['installation']['original_unchanged'])
        except Exception as exc:
            report.update(status='failed', error_type=type(exc).__name__, error=str(exc))
            raise
        finally:
            report['finished_at'] = datetime.now(timezone.utc).isoformat(); save()
            archive_report(ROOT, report_path.name, 'automated', 'Verified local model cache', report['scope']); refresh_results(ROOT)
        print(json.dumps({'report': str(report_path), 'passed': report['passed']}), flush=True)


if __name__ == '__main__':
    main()
