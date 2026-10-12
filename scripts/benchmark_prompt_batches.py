# SPDX-License-Identifier: Apache-2.0
"""Bracket one prompt-batch candidate; never change production configuration."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
from unittest.mock import patch

import httpx
import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.llama_session import LlamaReferenceSession
from app.native_chat import ChatStream
from app.engine import text_of_message
from app.validation_results import archive_report, refresh_results
from scripts.benchmark_cpu_threads import observation, require_idle
from scripts.evaluate_hardening_suite import runtime_digest

ORDER = (128, 512, 128)


def batch_command(command, batch):
    if type(batch) is not int or batch not in ORDER:
        raise ValueError('Undeclared batch size')
    result = list(command)
    for flag in ('-b', '-ub'):
        result[result.index(flag) + 1] = str(batch)
    return result


def verdict(variants, storage=False):
    order = ('original', 'cache', 'original') if storage else ORDER
    key = 'storage' if storage else 'batch'
    complete = [v.get(key) for v in variants] == list(order) and all(
        v.get('receipt_passed') and (v.get('prefill_tokens') or 0) > 0 and (v.get('prefill_seconds') or 0) > 0
        and not v.get('interruption') for v in variants)
    if storage:
        complete = complete and all(v.get('model_storage', {}).get('kind') == v['storage'] for v in variants)
        complete = complete and len({v.get('model_storage', {}).get('sha256') for v in variants}) == 1
        complete = complete and all(v.get('batch') == 128 for v in variants)
    result = {'complete': complete, 'faster_than_both_baselines': False, 'passed': False}
    if complete:
        same_input = len({v['prefill_tokens'] for v in variants}) == 1
        faster = all(variants[1]['prefill_seconds'] < v['prefill_seconds'] * .9 for v in (variants[0], variants[2]))
        starts = [v.get('start_sample', {}) for v in variants]
        comparable = all(type(s.get('gpu_c')) in (float, int) and type(s.get('cpu_c')) in (float, int) for s in starts)
        if comparable:
            comparable = max(s['gpu_c'] for s in starts) - min(s['gpu_c'] for s in starts) <= 7 and \
                max(s['cpu_c'] for s in starts) - min(s['cpu_c'] for s in starts) <= 12 and \
                not any(s.get('thermal_slowdown') for v in variants for s in v.get('samples', []))
        result.update(same_prefill_tokens=same_input, faster_than_both_baselines=faster,
                      temperature_comparable=comparable, passed=same_input and faster and comparable)
    return result


def main(storage=False):
    config = json.loads((ROOT / 'config.json').read_text())
    order = ('original', 'cache', 'original') if storage else ORDER
    title = 'Model storage prefill experiment' if storage else 'Prompt batch prefill experiment'
    prefix = 'model-storage-probe-' if storage else 'prompt-batch-probe-'
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    path = ROOT / 'docs' / (prefix + stamp + '.json')
    report = {'started_at': datetime.now(timezone.utc).isoformat(), 'status': 'running', 'passed': False,
              'scope': ('Isolated original/cache/original model storage comparison at fixed batch128. ' if storage else 'Isolated 128/512/128 prompt-batch experiment. ') + 'Identical public synthetic input and native tool receipt. Same model, precision, context, placement, threads and sampler. No coding qualification or production change.',
              'design': {'order': list(order), 'max_variant_seconds': 600, 'min_ram_gib': 1.5,
                         'min_vram_free_mib': 1500, 'min_prefill_improvement': .1,
                         'start_gpu_max_c': 72, 'start_cpu_max_c': 85, 'cooldown_seconds': 120,
                         'cache_policy': 'No OS cache dropping; repeated baseline brackets candidate.'},
              'runtime_sha256_before': runtime_digest(), 'variants': []}
    def save():
        temp = path.with_suffix('.tmp'); temp.write_text(json.dumps(report, indent=2) + '\n'); temp.replace(path)
    # Fixed initial input; report the exact token work rather than trusting character counts.
    records = '\n'.join(f'record_{i:03d}: verify text, files, values and error handling.' for i in range(48))
    messages = [{'role': 'system', 'content': 'Use emit_receipt exactly once with the marker requested by the user.'},
                {'role': 'user', 'content': 'Reference records:\n' + records + '\nEmit marker batch-fixture-419.'}]
    tool = {'type': 'function', 'function': {'name': 'emit_receipt', 'parameters': {
        'type': 'object', 'properties': {'marker': {'type': 'string'}}, 'required': ['marker']}}}
    payload = {'messages': messages, 'tools': [tool], 'tool_choice': 'required', 'parallel_tool_calls': False,
               'reasoning_effort': 'medium', 'reasoning_format': 'deepseek', 'stream': True,
               'stream_options': {'include_usage': True}, 'temperature': 1.0, 'top_p': 1.0,
               'top_k': 0, 'min_p': 0.0, 'repeat_penalty': 1.0, 'max_tokens': 256}
    report['input_sha256'] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    save(); print(json.dumps({'report': str(path), 'order': order}), flush=True)
    with httpx.Client(base_url='http://127.0.0.1:3210', trust_env=False, timeout=5) as control:
        control.get('/').raise_for_status(); require_idle(control)
        if any(p.info['name'] in ('llama-server', 'picchio') for p in psutil.process_iter(['name'])):
            raise RuntimeError('Another inference process is present')
        for setting in order:
            batch = 128 if storage else setting
            selected_config = dict(config)
            if storage:
                selected_config['model_cache'] = dict(config.get('model_cache', {}), enabled=setting == 'cache')
            require_idle(control)
            cooling = time.monotonic()
            while True:
                require_idle(control); cooled = observation()
                if cooled['gpu_c'] <= 72 and (cooled.get('cpu_c') or 101) <= 85: break
                if time.monotonic() - cooling >= 120:
                    report.update(status='complete', abort_reason='Comparable starting-temperature cooldown limit')
                    save(); archive_report(ROOT, path.name, 'native', title, report['scope']); refresh_results(ROOT)
                    return False
                time.sleep(3)
            variant = {'batch': batch, 'samples': [], 'receipt_passed': False, 'start_sample': cooled,
                       'cooldown_seconds': round(time.monotonic() - cooling, 2)}
            if storage: variant['storage'] = setting
            report['variants'].append(variant); save()
            started = time.monotonic(); done = threading.Event(); owned = []; session = None
            real_popen = subprocess.Popen
            def launch(command, **kwargs):
                if '-ncmoe' not in command: return real_popen(command, **kwargs)
                command = batch_command(command, batch)
                variant['parameters'] = {flag: command[command.index(flag) + 1] for flag in ('-b', '-ub', '-c', '-t', '-ncmoe')}
                proc = real_popen(command, **kwargs); owned.append(proc); psutil.Process(proc.pid).nice(5)
                return proc
            def watch():
                while not done.wait(3):
                    try:
                        current = observation(); current['seconds'] = round(time.monotonic() - started, 1)
                        live = control.get('/api/status').json()
                        reason = 'User inference started' if live['active_job'] or live['model_pid'] else (
                            'RAM reserve' if current['available_ram_gib'] < 1.5 else
                            'GPU reserve' if current['gpu_total_mib'] - current['gpu_used_mib'] < 1500 else
                            'Temperature reserve' if current['gpu_c'] >= 93 or (current.get('cpu_c') or 0) >= 100 else
                            'Bounded speed-probe limit' if current['seconds'] >= 600 else None)
                        variant['samples'].append(current)
                        if len(variant['samples']) % 7 == 1:
                            print(json.dumps({'batch': batch, 'seconds': current['seconds'],
                                              'available_ram_gib': round(current['available_ram_gib'], 2)}), flush=True)
                        if reason:
                            variant['interruption'] = reason
                            for proc in owned:
                                if proc.poll() is None: proc.terminate()
                            return
                    except Exception:
                        variant['interruption'] = 'Resource observation unavailable'
                        for proc in owned:
                            if proc.poll() is None: proc.terminate()
                        return
            watcher = threading.Thread(target=watch, daemon=True); watcher.start()
            try:
                with patch('app.llama_session.subprocess.Popen', side_effect=launch):
                    session = LlamaReferenceSession(ROOT, selected_config)
                variant['model_storage'] = session.model_storage
                if storage and session.model_storage['kind'] != setting:
                    raise RuntimeError('Requested storage was not selected')
                if variant.get('interruption'): raise RuntimeError('Interrupted during load')
                process = psutil.Process(session.proc.pid); reads = process.io_counters().read_bytes
                stream = ChatStream(); began = time.monotonic()
                with session.client.stream('POST', '/v1/chat/completions', json=payload, timeout=None) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if line.startswith('data:'):
                            raw = line[5:].strip()
                            if raw == '[DONE]': break
                            stream.accept(json.loads(raw))
                replies, reason = stream.replies({'emit_receipt'})
                calls = [m for m in replies if m.recipient == 'functions.emit_receipt']
                variant.update(receipt_passed=reason == 'EOS' and len(calls) == 1 and
                               json.loads(text_of_message(calls[0])) == {'marker': 'batch-fixture-419'},
                               generation_seconds=round(time.monotonic() - began, 3),
                               prefill_tokens=stream.timings.get('prompt_n'),
                               prefill_seconds=stream.timings.get('prompt_ms', 0) / 1000,
                               completion_tokens=stream.usage.get('completion_tokens'),
                               physical_read_mib=round((process.io_counters().read_bytes - reads) / 2**20, 3))
            except Exception as exc:
                variant['error_type'] = type(exc).__name__
            finally:
                done.set(); watcher.join(6)
                if session: session.close()
                for proc in owned:
                    if proc.poll() is None: proc.terminate()
                    try: proc.wait(timeout=3)
                    except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=3)
                variant['seconds'] = round(time.monotonic() - started, 3); save()
                print(json.dumps({k:v for k,v in variant.items() if k != 'samples'}), flush=True)
            if not variant.get('receipt_passed') or variant.get('interruption'): break
    report.update(verdict(report['variants'], storage)); report['runtime_frozen'] = runtime_digest() == report['runtime_sha256_before']
    report['passed'] = report['passed'] and report['runtime_frozen']; report['status'] = 'complete'; save()
    archive_report(ROOT, path.name, 'native', title, report['scope']); refresh_results(ROOT)
    print(json.dumps({'report': str(path), 'passed': report['passed']}), flush=True)
    return report['passed']


if __name__ == '__main__':
    raise SystemExit(0 if main() else 1)
