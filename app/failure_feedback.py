# SPDX-License-Identifier: Apache-2.0
"""Bounded excerpts of real runner failures; never a test verdict or diagnosis."""
import json
import re

ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
HEADERS = re.compile(r'^(?:FAIL|ERROR): (.+)$|^_{3,}\s+(.+?)\s+_{3,}$|^-{4,}\s+(.+?) stdout\s+-{4,}$', re.M)
HINT = 'Failure excerpts are observations, not a diagnosis. Read the saved artifact for omitted details.'


def clipped(value, limit):
    if len(value) <= limit: return value
    return value[:limit//2] + ' [... omitted ...] ' + value[-limit//2:]


def from_output(output, budget=2400):
    """Recognize unittest/pytest/Rust failure blocks, including subtest identities."""
    if not isinstance(output, str): return None
    # Bound parser work, retaining both ends of large command logs.
    output = ANSI.sub('', output)
    input_omitted = len(output) > 100000
    if input_omitted: output = output[:50000] + '\n' + output[-50000:]
    matches = list(HEADERS.finditer(output))
    if not matches: return None
    evidence = {'failures': [], 'omitted': 0, 'read_hint': HINT}
    if input_omitted: evidence['input_truncated'] = True
    for index, match in enumerate(matches):
        block = output[match.end():matches[index+1].start() if index+1<len(matches) else len(output)]
        identity = next(value for value in match.groups() if value is not None)
        lines = block.splitlines()
        # Keep exception/assertion lines, actual Rust sides, and pytest E lines.
        details = [line.strip() for line in lines if re.match(
            r'\s*(?:E\s+|[\w.]+(?:Error|Exception):|AssertionError:|thread .+ panicked|assertion .+ failed|left:|right:|Diff is )', line)]
        frames = [line.strip() for line in lines if re.match(
            r'\s*File ".+", line \d+|\S+\.(?:py|rs):\d+', line)]
        record = {'test': clipped(identity, 200)}
        if details: record['details'] = clipped('\n'.join(details), 460)
        if frames: record['locations'] = [clipped(line, 180) for line in frames[-2:]]
        candidate = {**evidence, 'failures': evidence['failures'] + [record], 'omitted': len(matches)-index-1}
        if len(json.dumps(candidate,ensure_ascii=False,separators=(',',':'))) <= budget:
            evidence = candidate
        else:
            evidence['omitted'] = len(matches)-index
            break
    if not evidence['failures']: return None
    return evidence


def with_failure_evidence(result):
    """Attach diagnostics before any preview; do not mutate full saved output."""
    if not isinstance(result, dict): return result
    value = dict(result)
    if isinstance(value.get('checks'), list):
        value['checks'] = [with_failure_evidence(check) for check in value['checks']]
    if (type(value.get('exit_code')) is int and value['exit_code'] != 0
            and not value.get('failure_evidence')):
        evidence = from_output(value.get('output'))
        if evidence: value['failure_evidence'] = evidence
    return value


def checkpoint_failures(result, budget=2200):
    """A separate bounded receipt survives even a very small raw-output preview."""
    result = with_failure_evidence(result)
    checks = result.get('checks', []) if isinstance(result, dict) else []
    if not checks: checks = [result]
    evidence = {'failures': [], 'omitted': 0, 'read_hint': HINT}
    seen = set()
    for check in checks:
        if not isinstance(check, dict): continue
        receipt = check.get('failure_evidence')
        if not isinstance(receipt, dict): continue
        evidence['omitted'] += receipt.get('omitted', 0)
        for record in receipt.get('failures', []):
            key=json.dumps(record,sort_keys=True)
            if key in seen: continue
            seen.add(key)
            candidate={**evidence,'failures':evidence['failures']+[record]}
            if len(json.dumps(candidate,ensure_ascii=False,separators=(',',':'))) <= budget:
                evidence=candidate
            else: evidence['omitted'] += 1
    return evidence if evidence['failures'] else None
