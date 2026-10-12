# SPDX-License-Identifier: Apache-2.0
"""Build a reviewable GitHub checkout without changing local runtime evidence.

This command copies files only. Commit and push are explicit separate steps.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import stat

ROOT = Path(__file__).resolve().parents[1]
OMITTED = '[local detail omitted from GitHub snapshot]'
TOP_FILES = {'.gitignore', 'AGENTS.md', 'README.md', 'LICENSE', 'NOTICE',
             'config.json', 'requirements.lock.txt'}
FOLDERS = {'app', 'scripts', 'tests', 'docs', 'licenses', '.github'}
PRIVATE_KEYS = {
    'checkpoint', 'messages', 'message', 'history', 'harmony_history', 'transcript',
    'prompt', 'prompts', 'goal', 'summary', 'content', 'text', 'analysis', 'reasoning',
    'response', 'completion', 'raw', 'raw_output', 'partial_output', 'output',
    'stdout', 'stderr', 'detail', 'arguments', 'authorization', 'cookie',
    'cookies', 'api_key', 'apikey', 'password', 'secret', 'access_token',
}
PUBLIC_STRINGS = {
    'title', 'scope', 'status', 'case', 'test', 'check', 'name', 'kind', 'type',
    'phase', 'started_at', 'finished_at', 'updated_at', 'created_at', 'at',
    'timestamp', 'date', 'version', 'backend', 'engine', 'reasoning_effort',
    'effective_reasoning_effort', 'work_reasoning_effort', 'chat_auto_effort',
    'observation_policy', 'report', 'source_report', 'path', 'file', 'directory',
    'root', 'cwd', 'workspace', 'job', 'session', 'url', 'repo', 'revision', 'commit',
    'sha256', 'oid', 'source', 'license', 'identifier', 'model', 'serving_model_path',
    'model_path', 'template', 'chat_template', 'runtime_sha256', 'handoff',
}
SECRET_PATTERNS = [
    re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}'),
    re.compile(r'github_pat_[A-Za-z0-9_]{35,}'),
    re.compile(r'(?<![A-Za-z0-9_-])sk-(?:proj-)?[A-Za-z0-9_-]{30,}'),
    re.compile(r'AKIA[0-9A-Z]{16}'),
    re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
]
PRIVATE_MARKERS = ('<|channel|>analysis', '<think>')


def public_report(value, key=''):
    """Keep outcomes/measurements; omit conversation and arbitrary output fields."""
    normalized = key.lower().replace('-', '_')
    if normalized in PRIVATE_KEYS:
        # A numerical error/detail count is harmless, but a transcript container
        # must never be traversed even when its child keys look like metadata.
        return value if type(value) in (bool, int, float) else OMITTED
    if isinstance(value, dict):
        return {k: public_report(v, k) for k, v in value.items()}
    if isinstance(value, list):
        if normalized in {'tokens', 'token_ids', 'ids'}:
            return OMITTED
        return [public_report(v, key) for v in value]
    if not isinstance(value, str):
        return value
    if any(marker in value for marker in PRIVATE_MARKERS):
        return OMITTED
    if (key in PUBLIC_STRINGS or key.endswith(('_sha256', '_commit', '_report'))
            or re.fullmatch(r'[a-f0-9]{40}|[a-f0-9]{64}', value)):
        return value
    return OMITTED


def inspect_text(data, path, known_secrets=()):
    text = data.decode('utf-8')
    if any(pattern.search(text) for pattern in SECRET_PATTERNS):
        raise ValueError(f'Credential-shaped content requires review: {path}')
    if any(secret and secret in text for secret in known_secrets):
        raise ValueError(f'Local credential found; upload refused: {path}')
    return text


def result_index(reports):
    lines = ['# Test results in this GitHub snapshot', '',
             'These are saved outcomes, not newly executed tests. Raw conversations, '
             'checkpoints, command output and screenshots remain on the originating machine. '
             'See [SESSION_LOG.md](SESSION_LOG.md) for diagnoses and [RESUME_HERE.md](RESUME_HERE.md) '
             'for current limitations. Native qualification is separate from harness tests.', '',
             '| Report | Status | Passed | Tests | Seconds |',
             '| --- | --- | --- | --- | --- |']
    for name, report in sorted(reports.items(), reverse=True):
        if not isinstance(report, dict):
            continue
        status = report.get('status', '')
        passed = report.get('passed', '')
        tests = report.get('tests_run', '')
        seconds = report.get('job_elapsed_seconds', report.get('seconds', ''))
        # Do not insert arbitrary report text into generated Markdown.
        status = status if status in {'passed', 'failed', 'error', 'complete', 'cancelled',
                                     'running', 'starting', 'paused', 'blocked', 'stopped'} else ''
        passed = passed if type(passed) is bool else ''
        tests = tests if type(tests) is int else ''
        seconds = seconds if type(seconds) in (int, float) else ''
        if status or passed != '' or tests != '':
            relative = Path(name).relative_to('docs').as_posix()
            lines.append(f'| [{relative}]({relative}) | {status} | {passed} | {tests} | {seconds} |')
    return '\n'.join(lines) + '\n'


def export(root=ROOT, destination=None):
    root = Path(root).resolve()
    destination = Path(destination) if destination else root / 'run/github/tiny_dancer'
    if destination.is_symlink():
        raise ValueError('Destination must not be a symlink')
    destination = destination.resolve()
    if not destination.is_relative_to(root / 'run/github'):
        raise ValueError('Publication checkout must be inside this project run/github directory')
    credential = root / 'run/access-token'
    known = [credential.read_text().strip()] if credential.is_file() else []
    files = [root / name for name in TOP_FILES if (root / name).exists()]
    for folder in FOLDERS:
        base = root / folder
        if base.is_symlink():
            raise ValueError(f'Source directory symlink is not exported: {folder}')
        if base.exists():
            files.extend(base.rglob('*'))
    prepared = {}
    records = []
    reports = {}
    for source in sorted(files):
        relative = source.relative_to(root)
        if '__pycache__' in relative.parts or source.suffix in {'.pyc', '.tmp'}:
            continue
        if source.is_symlink():
            raise ValueError(f'Source symlink is not exported: {relative}')
        if not source.is_file():
            continue
        if source.name.startswith('.env') or source.suffix in {'.pem', '.key', '.p12'}:
            raise ValueError(f'Private file type is not exported: {relative}')
        if relative.parts[0] == 'docs' and source.suffix not in {'.json', '.md', '.patch', '.txt'}:
            continue  # Desktop/browser screenshots can contain unrelated private work.
        if relative.as_posix() in {'docs/TEST_RESULTS.md', 'docs/github-export-manifest.json'}:
            continue
        raw = source.read_bytes()
        if len(raw) >= 50 * 1024 * 1024:
            raise ValueError(f'Unexpected large source file: {relative}')
        text = inspect_text(raw, relative, known)
        data = raw
        mode = 'exact'
        if relative.parts[0] == 'docs' and source.suffix == '.json':
            report = public_report(json.loads(text))
            data = (json.dumps(report, indent=2, ensure_ascii=False) + '\n').encode()
            reports[relative.as_posix()] = report
            mode = 'public-evidence-view'
        elif relative.parts[0] == 'docs' and any(marker in text for marker in PRIVATE_MARKERS):
            raise ValueError(f'Model trace marker in prose requires review: {relative}')
        inspect_text(data, relative, known)
        executable = bool(source.stat().st_mode & stat.S_IXUSR)
        prepared[relative.as_posix()] = (data, executable)
        records.append({'path': relative.as_posix(), 'mode': mode,
                        'source_sha256': hashlib.sha256(raw).hexdigest(),
                        'export_sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
    prepared['docs/TEST_RESULTS.md'] = (result_index(reports).encode(), False)
    manifest = {'created_at': datetime.now(timezone.utc).isoformat(),
                'scope': 'Source, licenses, documentation and public evidence views. '
                         'Local original files remain unchanged. No runtime data or model weights.',
                'excluded': ['run', 'logs', 'workspace', 'models', 'cache', 'build',
                             'vendor', '.venv', 'screenshots', 'raw report text'],
                'files': records}
    manifest_name = 'docs/github-export-manifest.json'
    previous = destination / manifest_name
    # Refuse unowned files: never overwrite a collaborator's edits silently.
    if destination.exists():
        prior = json.loads(previous.read_text()) if previous.is_file() else None
        if prior:
            owned = {}
            for item in prior['files']:
                relative = Path(item['path'])
                if relative.is_absolute() or '..' in relative.parts or '.git' in relative.parts:
                    raise ValueError('Invalid path in previous publication manifest')
                owned[item['path']] = item['export_sha256']
            owned['docs/TEST_RESULTS.md'] = prior.get('results_index_sha256')
            for path in destination.rglob('*'):
                rel = path.relative_to(destination)
                if '.git' in rel.parts or rel.as_posix() == manifest_name:
                    continue
                if path.is_symlink():
                    raise ValueError(f'Publication checkout symlink requires review: {rel}')
                if path.is_dir():
                    continue
                expected = owned.get(rel.as_posix())
                if not expected or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                    raise ValueError(f'Publication checkout has unreviewed local edits: {rel}')
        elif any(p.name != '.git' for p in destination.iterdir()):
            raise ValueError('Publication destination is not empty and has no export manifest')
    else:
        prior = None
    manifest['results_index_sha256'] = hashlib.sha256(prepared['docs/TEST_RESULTS.md'][0]).hexdigest()
    prepared[manifest_name] = ((json.dumps(manifest, indent=2) + '\n').encode(), False)
    # All input validation finishes before touching the checkout.
    destination.mkdir(parents=True, exist_ok=True)
    if prior:
        for item in prior['files']:
            if item['path'] not in prepared:
                (destination / item['path']).unlink(missing_ok=True)
    for name, (data, executable) in prepared.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + '.export-tmp')
        temporary.write_bytes(data)
        temporary.chmod(0o755 if executable else 0o644)
        temporary.replace(target)
    return {'destination': str(destination), 'files': len(prepared),
            'bytes': sum(len(data) for data, _ in prepared.values()),
            'manifest': str(destination / manifest_name)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path)
    args = parser.parse_args()
    print(json.dumps(export(destination=args.destination), indent=2))


if __name__ == '__main__':
    main()
