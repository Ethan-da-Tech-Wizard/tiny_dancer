# SPDX-License-Identifier: Apache-2.0
"""Compare CPU threads in owned native sessions without changing production."""
import hashlib
import json
import math
from pathlib import Path
import statistics
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
from app.validation_results import archive_report, refresh_results
from scripts.check_native_release import runtime_fingerprint

ORDER = (8, 4, 6, 8)
WARMUP_TOKENS = 128
MEASURED_TOKENS = 384
REPEATS = 3
DESIGN = {
    'threads_order': list(ORDER), 'warmup_tokens': WARMUP_TOKENS,
    'measured_tokens_per_turn': MEASURED_TOKENS, 'measured_turns': REPEATS,
    'experiment_seconds': 720, 'per_variant_seconds': 150,
    'cooldown_seconds': 120, 'start_gpu_max_c': 72,
    'start_gpu_spread_max_c': 7, 'start_cpu_spread_max_c': 12,
    'ram_reserve_gib': 1.5, 'vram_reserve_mib': 1500,
    'gpu_stop_c': 93, 'cpu_stop_c': 100,
    'minimum_time_improvement_fraction': .05,
    'production_changes': False, 'cache_policy': 'No OS cache dropping; repeated baseline brackets candidates.',
}


def candidate_config(config, threads):
    if config.get('backend') != 'llama.cpp' or config.get('context') != 8192 or config.get('threads') != 8:
        raise ValueError('Comparison requires the recorded native baseline: context8192/threads8')
    if type(threads) is not int or threads not in ORDER:
        raise ValueError('Undeclared thread count')
    return dict(config, threads=threads)


def cpu_temperature():
    values = []
    for name, entries in psutil.sensors_temperatures().items():
        if name in ('coretemp', 'k10temp', 'cpu_thermal'):
            values.extend(entry.current for entry in entries if math.isfinite(entry.current))
    return max(values) if values else None


def gpu_state():
    query = 'temperature.gpu,clocks.current.sm,memory.used,memory.total,clocks_event_reasons.sw_thermal_slowdown'
    result = subprocess.run(['nvidia-smi', '--query-gpu='+query, '--format=csv,noheader,nounits'],
                            capture_output=True, text=True, timeout=3)
    result.check_returncode()
    fields = [value.strip() for value in result.stdout.strip().splitlines()[0].split(',')]
    if len(fields) != 5 or fields[4] not in ('Active', 'Not Active'):
        raise ValueError('GPU observation is incomplete')
    temp, clock, used, total = map(float, fields[:4])
    if not all(math.isfinite(n) for n in (temp, clock, used, total)) or not 0 <= used <= total:
        raise ValueError('Invalid GPU observation')
    return {'gpu_c': temp, 'sm_mhz': clock, 'gpu_used_mib': used,
            'gpu_total_mib': total, 'thermal_slowdown': fields[4] == 'Active'}


def resource_issue(sample, *, user_job=False, elapsed=0, experiment_elapsed=0):
    if user_job:
        return 'User task started; release benchmark resources'
    if experiment_elapsed >= DESIGN['experiment_seconds']:
        return 'Experiment observation deadline'
    if elapsed >= DESIGN['per_variant_seconds']:
        return 'Variant observation deadline'
    if sample['available_ram_gib'] < DESIGN['ram_reserve_gib']:
        return 'Desktop RAM reserve'
    if sample['gpu_total_mib']-sample['gpu_used_mib'] < DESIGN['vram_reserve_mib']:
        return 'Desktop GPU reserve'
    if sample['gpu_c'] >= DESIGN['gpu_stop_c']:
        return 'GPU temperature observation limit'
    if sample.get('cpu_c') is not None and sample['cpu_c'] >= DESIGN['cpu_stop_c']:
        return 'CPU temperature observation limit'
    return None


def observation():
    return dict(gpu_state(), available_ram_gib=psutil.virtual_memory().available/2**30,
                cpu_c=cpu_temperature())


def cooldown_ready(sample, elapsed):
    if sample['gpu_c'] <= DESIGN['start_gpu_max_c']:
        return True
    if elapsed >= DESIGN['cooldown_seconds']:
        raise RuntimeError('Comparable starting-temperature cooldown limit')
    return False


def require_idle(client):
    result = client.get('/api/status', timeout=3)
    result.raise_for_status()
    status = result.json()
    if status.get('active_job') or status.get('engine') != 'not loaded':
        raise RuntimeError('Benchmark requires idle app and unloaded production model')
    return status


def stop_owned(processes):
    for process in processes:
        if process.poll() is None:
            try:
                process.terminate()
            except ProcessLookupError:
                pass


def comparison(variants):
    result = {'comparison_complete': False, 'greedy_token_parity': False,
              'starting_temperatures_comparable': False, 'candidates': [], 'passed': False}
    if [v.get('threads') for v in variants] != list(ORDER):
        return result
    if not all(v.get('completed') and len(v.get('turns', [])) == REPEATS for v in variants):
        return result
    if not all(v.get('samples') and v.get('start_sample') for v in variants):
        return result
    all_turns = [t for v in variants for t in v['turns']]
    if not all(t.get('token_count', 0) > 0 and t.get('tokens_sha256') and
               math.isfinite(t['timings']['total_seconds']) and t['timings']['total_seconds'] > 0
               for t in all_turns):
        return result
    result['comparison_complete'] = True
    signatures = [{(t['tokens_sha256'], t['token_count'], t['reason']) for t in v['turns']} for v in variants]
    baseline_stable = len(signatures[0]) == 1 and signatures[0] == signatures[-1]
    result['baseline_token_stable'] = baseline_stable
    result['greedy_token_parity'] = baseline_stable and all(s == signatures[0] for s in signatures)
    gpu_starts = [v['start_sample']['gpu_c'] for v in variants]
    cpu_starts = [v['start_sample'].get('cpu_c') for v in variants]
    gpu_comparable = max(gpu_starts) <= DESIGN['start_gpu_max_c'] and max(gpu_starts)-min(gpu_starts) <= DESIGN['start_gpu_spread_max_c']
    cpu_comparable = all(c is not None for c in cpu_starts) and max(cpu_starts)-min(cpu_starts) <= DESIGN['start_cpu_spread_max_c']
    result['starting_temperatures_comparable'] = gpu_comparable and cpu_comparable
    result['start_gpu_spread_c'] = max(gpu_starts)-min(gpu_starts)
    baseline_times = [statistics.median(t['timings']['total_seconds'] for t in v['turns']) for v in (variants[0], variants[-1])]
    baseline = statistics.mean(baseline_times)
    result['baseline_median_seconds'] = baseline_times
    result['baseline_timing_drift_fraction'] = abs(baseline_times[1]-baseline_times[0])/baseline
    for variant, signature in zip(variants[1:-1], signatures[1:-1]):
        seconds = statistics.median(t['timings']['total_seconds'] for t in variant['turns'])
        improvement = 1-seconds/baseline
        parity = baseline_stable and signature == signatures[0]
        # Require an improvement against each baseline, not only their average.
        faster_than_both = all(seconds <= b*(1-DESIGN['minimum_time_improvement_fraction']) for b in baseline_times)
        result['candidates'].append({'threads': variant['threads'], 'median_seconds': seconds,
            'time_reduction_fraction_vs_bracket_mean': improvement, 'token_parity': parity,
            'faster_than_both_baselines': faster_than_both,
            'speed_probe_passed': parity and faster_than_both and result['starting_temperatures_comparable']})
    result['passed'] = any(c['speed_probe_passed'] for c in result['candidates'])
    return result


def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder = ROOT/'run/thread-benchmarks'/stamp
    folder.mkdir(parents=True)
    path = ROOT/'docs/cpu-thread-validation.json'
    report = {'title': 'Native CPU thread comparison', 'started_at': datetime.now(timezone.utc).isoformat(),
              'status': 'running', 'passed': None, 'design': DESIGN, 'variants': [], 'abort_reason': None,
              'runtime_sha256_before': runtime_fingerprint(ROOT),
              'scope': 'Isolated speed/parity experiment, three repeated final-channel turns per setting. Same native MXFP4 weights, context8192, CPU expert layers16, CUDA/batch/KV/greedy settings. No autonomous coding qualification or production change.'}
    if path.exists():
        previous = json.loads(path.read_text())
        if isinstance(previous.get('passed'), bool):
            archive_report(ROOT, path.name, 'evaluation', previous['title'], previous['scope'])
    def save():
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
        temporary.replace(path)
    save()
    started = time.monotonic()
    config = json.loads((ROOT/'config.json').read_text())
    owned = []
    try:
        candidate_config(config, 8)
        encoding = load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
        prompt = ('Use this sample project record as context:\n'+ '\n'.join(
            f'module_{i}.py: parse inputs, validate values, write output, and run its tests.' for i in range(90))+
            '\nWrite 24 numbered, concise recommendations for testing a Python command-line project. '
            'Explain the purpose of each test and cover valid inputs, errors, Unicode, files, and deterministic output.')
        ids = encoding.encode('<|start|>user<|message|>'+prompt+'<|end|>\n<|start|>assistant<|channel|>final<|message|>', allowed_special='all')
        report['prompt'] = {'sha256': hashlib.sha256(prompt.encode()).hexdigest(), 'tokens': len(ids),
                            'channel': 'final', 'private_reasoning_recorded': False}
        with httpx.Client(base_url='http://127.0.0.1:3210', trust_env=False, timeout=3) as client:
            client.get('/').raise_for_status()
            require_idle(client)
            if any(p.info['name'] in ('llama-server', 'picchio') for p in psutil.process_iter(['name'])):
                raise RuntimeError('Another inference process is present')
            for threads in ORDER:
                cooled_at = time.monotonic()
                while True:
                    require_idle(client)
                    sample = observation()
                    issue = resource_issue(sample, experiment_elapsed=time.monotonic()-started)
                    if issue:
                        raise RuntimeError(issue)
                    if cooldown_ready(sample, time.monotonic()-cooled_at):
                        break
                    time.sleep(2)
                variant = {'threads': threads, 'turns': [], 'samples': [], 'start_sample': sample,
                           'cooldown_seconds': round(time.monotonic()-cooled_at, 3), 'completed': False}
                report['variants'].append(variant)
                save()
                variant_start = time.monotonic()
                stopping = threading.Event()
                interrupted = []
                session = None
                owned = []
                original_popen = subprocess.Popen
                def launch(command, **kwargs):
                    if '-ncmoe' not in command:
                        return original_popen(command, **kwargs)
                    if interrupted:
                        raise RuntimeError(interrupted[0])
                    variant['launch_parameters'] = {flag: command[command.index(flag)+1]
                        for flag in ('-t', '-tb', '-c', '-ncmoe', '-b', '-ub')}
                    with (folder/f'variant-{len(report["variants"])}-server.log').open('a') as log:
                        kwargs.update(stdout=log, stderr=log)
                        process = original_popen(command, **kwargs)
                    owned.append(process)
                    if interrupted:
                        stop_owned(owned)
                    psutil.Process(process.pid).nice(config.get('model_nice', 5))
                    return process
                def monitor():
                    try:
                        with httpx.Client(base_url='http://127.0.0.1:3210', trust_env=False, timeout=3) as watch_client:
                            watch_client.get('/').raise_for_status()
                            while not stopping.wait(2):
                                current = observation()
                                current['elapsed_seconds'] = round(time.monotonic()-variant_start, 3)
                                response = watch_client.get('/api/status')
                                response.raise_for_status()
                                issue = resource_issue(current, user_job=bool(response.json().get('active_job')),
                                    elapsed=time.monotonic()-variant_start, experiment_elapsed=time.monotonic()-started)
                                variant['samples'].append(current)
                                if issue:
                                    interrupted.append(issue)
                                    stop_owned(owned)
                                    return
                    except Exception as exc:
                        interrupted.append(type(exc).__name__+' in resource monitor')
                        stop_owned(owned)
                watcher = threading.Thread(target=monitor, daemon=True)
                watcher.start()
                try:
                    with patch('app.llama_session.subprocess.Popen', side_effect=launch):
                        session = LlamaReferenceSession(ROOT, candidate_config(config, threads))
                    variant['load_seconds'] = round(time.monotonic()-variant_start, 3)
                    if interrupted:
                        raise RuntimeError(interrupted[0])
                    session.turn(ids, WARMUP_TOKENS, 0, lambda token: None, temperature=0)
                    variant['warmup_timing'] = dict(session.last_timing)
                    process = psutil.Process(session.proc.pid)
                    process.cpu_percent(None)
                    for index in range(REPEATS):
                        if interrupted:
                            raise RuntimeError(interrupted[0])
                        before = process.io_counters().read_bytes
                        tokens, reason, _ = session.turn(ids, MEASURED_TOKENS, 0, lambda token: None, temperature=0)
                        turn = {'reason': reason, 'token_count': len(tokens), 'timings': dict(session.last_timing),
                            'tokens_sha256': hashlib.sha256(json.dumps(tokens).encode()).hexdigest(),
                            'physical_read_bytes': process.io_counters().read_bytes-before,
                            'process_cpu_percent': process.cpu_percent(None),
                            'process_uss_gib': process.memory_full_info().uss/2**30}
                        variant['turns'].append(turn)
                        save()
                        print(json.dumps({'threads': threads, 'turn': index+1, 'tokens': len(tokens),
                            'seconds': round(turn['timings']['total_seconds'], 3)}), flush=True)
                    variant['completed'] = not interrupted
                except Exception as exc:
                    variant['error'] = interrupted[0] if interrupted else type(exc).__name__
                    report['abort_reason'] = variant['error']
                finally:
                    stopping.set()
                    watcher.join(timeout=10)
                    if watcher.is_alive():
                        report['abort_reason'] = 'Resource monitor did not stop; comparison cannot continue'
                    if session is not None:
                        session.close()
                    stop_owned(owned)
                    for process in owned:
                        try:
                            process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            process.kill(); process.wait(timeout=3)
                    variant['seconds'] = round(time.monotonic()-variant_start, 3)
                    save()
                if report['abort_reason']:
                    break
    except Exception as exc:
        report['abort_reason'] = str(exc) if isinstance(exc, (ValueError, RuntimeError)) else type(exc).__name__
    finally:
        stop_owned(owned)
        report.update(comparison(report['variants']))
        report['runtime_sha256_after'] = runtime_fingerprint(ROOT)
        report['runtime_frozen'] = report['runtime_sha256_after'] == report['runtime_sha256_before']
        report['passed'] = report['passed'] and report['runtime_frozen'] and not report['abort_reason']
        report.update(status='complete', elapsed_seconds=round(time.monotonic()-started, 3),
                      finished_at=datetime.now(timezone.utc).isoformat())
        save()
        archive_report(ROOT, path.name, 'evaluation', report['title'], report['scope'])
        refresh_results(ROOT)
    print(json.dumps({'passed': report['passed'], 'comparison_complete': report['comparison_complete'],
                      'candidates': report['candidates'], 'abort_reason': report['abort_reason']}), flush=True)
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
