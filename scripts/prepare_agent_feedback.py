# SPDX-License-Identifier: Apache-2.0
"""Prepare an evidence-only local-model review workspace; never launch or deploy."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def public_evidence(report):
    """Allowlist observations; do not copy transcripts, arguments or reasoning."""
    if not isinstance(report, dict):
        raise ValueError('Expected an evaluation report object')
    if report.get('status') in ('starting', 'queued', 'running'):
        raise ValueError('Finish the observed task before preparing feedback')
    if not isinstance(report.get('passed'), bool):
        raise ValueError('A completed evaluation with a boolean outcome is required')
    result = {'passed': report['passed'], 'status': report.get('status', 'complete')}
    for key in ('checks', 'markers_present'):
        values = report.get(key, {})
        if isinstance(values, dict):
            result[key] = {str(k): v for k, v in values.items() if isinstance(v, bool)}
    checks = report.get('independent_checks', [])
    result['independent_checks'] = [
        {'check': c['check'], 'passed': c['passed']}
        for c in checks if isinstance(c, dict) and isinstance(c.get('check'), str)
        and isinstance(c.get('passed'), bool)]
    for key in ('seconds', 'job_elapsed_seconds', 'formatted_characters'):
        if type(report.get(key)) in (int, float):
            result[key] = report[key]
    result['tool_counts'] = dict(Counter(
        call['name'] for call in report.get('tool_calls', [])
        if isinstance(call, dict) and isinstance(call.get('name'), str)))
    return result


def project_source(root, name):
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise ValueError('Source must be a relative project path')
    if relative.parts[0] not in ('app', 'tests', 'scripts') or relative.suffix not in ('.py', '.jinja'):
        raise ValueError('Only explicitly selected app/tests/scripts Python or Jinja source is copied')
    source = root / relative
    # Reject links anywhere in the selected path, including links inside root.
    if any((root / Path(*relative.parts[:i])).is_symlink() for i in range(1, len(relative.parts) + 1)):
        raise ValueError('Source symlinks are not copied')
    if not source.is_file() or not source.resolve().is_relative_to(root.resolve()):
        raise ValueError('Source is missing or outside the project')
    if source.stat().st_size > 500_000:
        raise ValueError('Select a smaller source file for review')
    return source


def prepare(root, report_path, sources, goal):
    root = Path(root).resolve()
    report_path = Path(report_path).resolve()
    if not report_path.is_relative_to(root / 'docs') or report_path.suffix != '.json':
        raise ValueError('Choose a saved evaluation JSON under project docs')
    raw = report_path.read_bytes()
    evidence = public_evidence(json.loads(raw))
    if not goal.strip() or len(goal) > 12_000:
        raise ValueError('Provide a concise review requirement')
    selected = [(name, project_source(root, name)) for name in dict.fromkeys(sources)]
    if not selected:
        raise ValueError('Select at least one relevant source file')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = root / 'workspace' / ('agent-feedback-' + stamp)
    folder.mkdir(parents=True)
    records = []
    for name, source in selected:
        data = source.read_bytes()
        for directory in ('source', 'candidate'):
            dest = folder / directory / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        records.append({'path': name, 'sha256': hashlib.sha256(data).hexdigest()})
    evidence['requirement'] = goal.strip()
    (folder / 'evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    manifest = {'created_at': datetime.now(timezone.utc).isoformat(),
                'report': str(report_path.relative_to(root)),
                'report_sha256': hashlib.sha256(raw).hexdigest(), 'sources': records,
                'scope': 'Copied source and public outcomes only. No deployment authority or model launch.'}
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (folder / 'AGENTS.md').write_text('''# Diagnostic review workspace

Use evidence.json and the copied source as observations. Inspect the implementation;
report uncertainty honestly. Work only inside this review folder. Preserve source/,
evidence.json and manifest.json. Modify only candidate/ and new review/test files.
Never import app.server or start a service. Do not change the running application,
its configuration, model, dependencies, or any project outside this folder.

Write feedback.json with keys: verdict (proposal, no_change, or insufficient_evidence),
summary, evidence (list of file/line references or check names), proposed_change,
test_command, risks (list), and limitations (list). All values except lists are strings.
Explain observable behavior; do not request or expose private reasoning/transcripts.

If a concrete defect is reproducible, add test_feedback.py and fix only candidate/.
Tests must read the code/template root from TD_REVIEW_SOURCE_ROOT (default candidate/).
Run the exact same tests against source/ and candidate/, saving test-results.json
with commands and exit codes. A useful reproduction fails because of the observed
behavior on source/ and passes on candidate/. Import/setup errors are not evidence.
Preserve the original goal; do not invent requirements to justify a patch.

If the evidence does not justify a change, record no_change or insufficient_evidence;
do not manufacture a test or problem. Proposals require separate independent review
and regression checks before any deployment. You cannot approve your own proposal.
''')
    (folder / 'REQUEST.txt').write_text(
        'Review this isolated agent diagnostic workspace. Read AGENTS.md and evidence.json. '
        'Use the copied source to investigate the observed behavior, propose the smallest '
        'justified correction, and produce the requested feedback and reproduction tests. '
        'Run the tests on both the original copy and your candidate. Keep original evidence '
        'and source unchanged. Do not modify or start the live application.\n')
    # The normal automatic inspection already reads README.md. Put the known
    # requirement and paths there so the model does not spend separate turns
    # rediscovering them. Original observations remain unchanged in evidence.json.
    locations = '\n'.join('- `source/' + name + '` and `candidate/' + name + '`'
                          for name, _ in selected)
    (folder / 'README.md').write_text(
        (folder / 'AGENTS.md').read_text() + '\n## Observed requirement and results\n\n' +
        json.dumps(evidence, indent=2) + '\n\n## Exact source paths\n\n' + locations + '\n')
    return folder


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', help='Saved evaluation JSON under docs/')
    parser.add_argument('--source', action='append', required=True, help='Relevant relative source path; repeat as needed')
    parser.add_argument('--goal', required=True, help='Behavior the selected implementation must satisfy')
    args = parser.parse_args()
    folder = prepare(ROOT, ROOT / args.report, args.source, args.goal)
    print(json.dumps({'workspace': str(folder), 'request': str(folder / 'REQUEST.txt'),
                      'next': 'When the app is idle, select this workspace and send the request in Agent mode.'}, indent=2))


if __name__ == '__main__':
    main()
