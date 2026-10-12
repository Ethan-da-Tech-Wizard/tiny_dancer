# SPDX-License-Identifier: Apache-2.0
"""Independent Unicode behavior audit; declared after the original labels trial."""
import itertools
import json
from pathlib import Path
import subprocess
import sys

CRITERIA = (
    'Already lowercase text retains combining marks',
    'Unicode lowercase expansions follow Python str.lower',
    'Lowercase does not introduce casefolding or accent removal',
    'Whitespace and letter transformations compose across mixed inputs',
)


def cases():
    groups = [
        ['i\u0307', ' x i\u0307 y '],
        ['\u0130', '\u00c7\u00dc\u0130  123'],
        ['Stra\u00dfe', '\ufb00 \u00c9 e\u0301', '\u039f\u03a3', 'A\u200bB'],
        [' \t' + a + sep + b + '\n ' for a, sep, b in itertools.product(
            ['A', '\u0130', 'i\u0307', '\u00df', '\u039f\u03a3', 'e\u0301'],
            [' ', '\t\n', '\u00a0\u2003', '\u200b'],
            ['B', '\u0130', 'i\u0307', '\u00df', '\u039f\u03a3', 'e\u0301'])],
    ]
    return list(zip(CRITERIA, groups))


def check_labels_goal(folder):
    """Run the model product in a child; never import it into the observer."""
    groups = cases()
    inputs = [value for _, values in groups for value in values]
    code = ('import json,sys\nfrom labels import normalize_label\n'
            'print(json.dumps([normalize_label(s) for s in json.load(sys.stdin)]))')
    try:
        result = subprocess.run([sys.executable, '-c', code], cwd=Path(folder),
                                input=json.dumps(inputs), text=True, capture_output=True, timeout=20)
        actual = json.loads(result.stdout) if result.returncode == 0 else None
        valid = isinstance(actual, list) and len(actual) == len(inputs)
        error = result.stderr[-1000:] if not valid else None
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        actual, valid, error = None, False, type(exc).__name__
    checks, offset = [], 0
    for name, values in groups:
        failures = []
        for i, value in enumerate(values):
            expected = ' '.join(value.split()).lower()
            observed = actual[offset+i] if valid else None
            if observed != expected:
                failures.append({'input':value, 'expected':expected, 'actual':observed})
        checks.append({'check':name, 'passed':valid and not failures,
                       'examples':len(values), 'failed_examples':len(failures),
                       'counterexamples':failures[:3], 'error':error})
        offset += len(values)
    return checks
