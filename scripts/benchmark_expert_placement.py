# SPDX-License-Identifier: Apache-2.0
"""Bounded isolated native placement comparison; never alter the serving config."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from unittest.mock import patch

import httpx
import psutil
from openai_harmony import HarmonyEncodingName, load_harmony_encoding

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.llama_session import LlamaReferenceSession
from app.validation_results import archive_report


def gpu_memory():
    result = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,memory.total,temperature.gpu',
                             '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=3)
    result.check_returncode()
    used, total, temperature = map(float, result.stdout.strip().splitlines()[0].split(','))
    return {'used_mib': used, 'total_mib': total, 'temperature_c': temperature}


def assert_idle(client):
    status = client.get('/api/status', timeout=3).json()
    if status.get('active_job') or status.get('engine') != 'not loaded':
        raise RuntimeError('Placement benchmark requires idle app and unloaded production model')
    return status


def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder = ROOT/'run/placement-benchmarks'/stamp
    folder.mkdir(parents=True)
    report = {'title': 'Native expert placement comparison', 'started_at': datetime.now(timezone.utc).isoformat(),
              'passed': None, 'scope': 'Same native MXFP4 model, greedy forced-final prompts, context8192/threads8/batch128. Speed experiment only; does not qualify autonomous coding.',
              'design': {'order_cpu_expert_layers': [16, 14, 16], 'max_new_tokens': 128,
                         'per_variant_seconds': 180, 'ram_reserve_gib': 1.5, 'vram_reserve_mib': 1500,
                         'production_changes': False, 'cache_policy': 'No OS cache dropping; repeated baseline brackets candidate.'},
              'variants': [], 'abort_reason': None}
    path = ROOT/'docs/expert-placement-validation.json'
    def save():
        path.write_text(json.dumps(report, indent=2)+'\n')
    save()
    encoding = load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
    # Supply a final-channel prefix, so this benchmark contains no private reasoning.
    prompts = [
        'Write a short paragraph about what a Python command-line program does.',
        'Use this sample project record as context:\n'+ '\n'.join(
            f'module_{i}.py: parse inputs, validate values, write output, and run its tests.' for i in range(90)) +
        '\nWrite a paragraph explaining why command-line tests should check both success and errors.']
    prompt_ids = [encoding.encode('<|start|>user<|message|>'+p+'<|end|>\n<|start|>assistant<|channel|>final<|message|>', allowed_special='all') for p in prompts]
    report['prompts'] = [{'sha256': hashlib.sha256(p.encode()).hexdigest(), 'tokens': len(ids)} for p, ids in zip(prompts, prompt_ids)]
    config = json.loads((ROOT/'config.json').read_text())
    started = time.monotonic()
    with httpx.Client(base_url='http://127.0.0.1:3210', trust_env=False) as client:
        client.get('/')
        assert_idle(client)
        if any(p.info['name'] in ('llama-server', 'picchio') for p in psutil.process_iter(['name'])):
            raise RuntimeError('A native model is already running; do not start a second one')
        for cpu_layers in (16, 14, 16):
            assert_idle(client)
            variant = {'cpu_expert_layers': cpu_layers, 'turns': [], 'peak_gpu_mib': 0, 'min_ram_gib': float('inf')}
            report['variants'].append(variant)
            stop = threading.Event()
            owned = []
            interrupted = []
            variant_started = time.monotonic()
            original_popen = subprocess.Popen
            def launch(command, **kwargs):
                command = list(command)
                if '-ncmoe' not in command:
                    return original_popen(command, **kwargs)
                command[command.index('-ncmoe')+1] = str(cpu_layers)
                # Preserve logs independently, without exposing the private listener key.
                with (folder/f'variant-{len(report["variants"])}-server.log').open('a') as log:
                    kwargs.update(stdout=log, stderr=log)
                    proc = original_popen(command, **kwargs)
                psutil.Process(proc.pid).nice(config.get('model_nice', 5))
                owned.append(proc)
                return proc
            def monitor():
                while not stop.wait(1):
                    try:
                        gpu = gpu_memory()
                        available = psutil.virtual_memory().available/2**30
                        variant['peak_gpu_mib'] = max(variant['peak_gpu_mib'], gpu['used_mib'])
                        variant['min_ram_gib'] = min(variant['min_ram_gib'], available)
                        variant['last_gpu_temperature_c'] = gpu['temperature_c']
                        issue = None
                        if time.monotonic()-variant_started > 180: issue = 'Variant observation deadline'
                        elif available < 1.5: issue = 'Desktop RAM reserve'
                        elif gpu['total_mib']-gpu['used_mib'] < 1500: issue = 'Desktop GPU reserve'
                        elif client.get('/api/status', timeout=3).json().get('active_job'): issue = 'User task started; benchmark yields resources'
                        if issue:
                            interrupted.append(issue)
                            for proc in owned:
                                if proc.poll() is None: proc.terminate()
                            return
                    except Exception as exc:
                        interrupted.append(type(exc).__name__+' in resource monitor')
                        for proc in owned:
                            if proc.poll() is None: proc.terminate()
                        return
            watcher = threading.Thread(target=monitor, daemon=True)
            watcher.start()
            session = None
            try:
                with patch('app.llama_session.subprocess.Popen', side_effect=launch):
                    session = LlamaReferenceSession(ROOT, config)
                variant['load_seconds'] = round(time.monotonic()-variant_started, 3)
                for ids in prompt_ids:
                    if interrupted: raise RuntimeError(interrupted[0])
                    proc = psutil.Process(session.proc.pid)
                    before_reads = proc.io_counters().read_bytes
                    tokens, reason, _ = session.turn(ids, 128, 0, lambda token: None, temperature=0)
                    variant['turns'].append({'reason': reason, 'token_count': len(tokens),
                        'tokens_sha256': hashlib.sha256(json.dumps(tokens).encode()).hexdigest(),
                        'physical_read_bytes': proc.io_counters().read_bytes-before_reads,
                        'timings': session.last_timing})
                    save()
                variant['completed'] = not interrupted
            except Exception as exc:
                variant.update(completed=False, error=interrupted[0] if interrupted else type(exc).__name__+': '+str(exc))
                report['abort_reason'] = variant['error']
            finally:
                stop.set()
                watcher.join(timeout=4)
                if session is not None: session.close()
                for proc in owned:
                    if proc.poll() is None: proc.terminate()
                    try: proc.wait(timeout=3)
                    except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=3)
                variant['seconds'] = round(time.monotonic()-variant_started, 3)
                save()
            print(json.dumps(variant), flush=True)
            if report['abort_reason']: break
    report['seconds'] = round(time.monotonic()-started, 3)
    report['finished_at'] = datetime.now(timezone.utc).isoformat()
    variants = report['variants']
    complete = len(variants)==3 and all(v.get('completed') and len(v['turns'])==2 for v in variants)
    report['comparison_complete'] = complete
    if complete:
        hashes = [[t['tokens_sha256'] for t in v['turns']] for v in variants]
        report['greedy_token_parity'] = hashes[0]==hashes[1]==hashes[2]
        report['passed'] = report['greedy_token_parity']
        report['speed_ratios_vs_bracketed_baseline'] = [
            ((variants[0]['turns'][i]['timings']['total_seconds']+variants[2]['turns'][i]['timings']['total_seconds'])/2)/variants[1]['turns'][i]['timings']['total_seconds'] for i in range(2)]
    else: report['passed'] = False
    save()
    archive_report(ROOT, path.name, kind='evaluation', title=report['title'], scope=report['scope'])
    print('Saved:', path, flush=True)


if __name__ == '__main__': main()
