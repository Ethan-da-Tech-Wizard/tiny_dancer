# SPDX-License-Identifier: Apache-2.0
"""Withheld inventory checks added after the original narrow trial passed."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

CRITERIA = ('Repeated successful output outside ROOT is replaced with current data',
            'Unreadable directory fails scanning and preserves prior output')


def check_inventory_goal(folder, root):
    folder, root = Path(folder), Path(root)
    program = folder / 'inventory.py'
    def invoke(tree, output):
        try:
            return subprocess.run([sys.executable, str(program), str(tree), str(output)],
                                  cwd=folder, capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return subprocess.CompletedProcess([], 1, '', str(exc))
    def expected(files):
        return sorted([{'path':name, 'size':len(data), 'sha256':hashlib.sha256(data).hexdigest()}
                       for name, data in files.items()], key=lambda row:row['path'])
    def matches(output, files):
        try: return json.loads(output.read_text()) == expected(files)
        except (OSError, ValueError): return False
    with tempfile.TemporaryDirectory(dir=root / 'run') as temporary:
        base = Path(temporary); tree = base / 'tree'; tree.mkdir()
        files = {'alpha.txt':b'first contents'}
        (tree / 'alpha.txt').write_bytes(files['alpha.txt'])
        outside = base / 'outside.json'
        first = invoke(tree, outside)
        first_valid = first.returncode == 0 and matches(outside, files)
        files['.new.txt'] = b'added after the first successful inventory'
        (tree / '.new.txt').write_bytes(files['.new.txt'])
        second = invoke(tree, outside)
        replacement = {'check':CRITERIA[0], 'passed':first_valid and second.returncode == 0 and matches(outside, files),
                       'first_exit_code':first.returncode, 'second_exit_code':second.returncode,
                       'stderr':second.stderr[-1000:]}
        denied = tree / 'restricted'; denied.mkdir()
        (denied / 'nested.txt').write_bytes(b'readable control then unavailable')
        files['restricted/nested.txt'] = b'readable control then unavailable'
        inside = tree / 'inside.json'
        readable = invoke(tree, inside)
        readable_valid = readable.returncode == 0 and matches(inside, files)
        prior = b'previous output must survive a scan error'
        inside.write_bytes(prior); denied.chmod(0)
        try:
            failed = invoke(tree, inside)
            preserved = inside.read_bytes() == prior
        finally:
            denied.chmod(0o700)
        traversal = {'check':CRITERIA[1], 'passed':readable_valid and failed.returncode != 0
                     and bool(failed.stderr.strip()) and 'Traceback' not in failed.stderr and preserved,
                     'readable_control_passed':readable_valid, 'exit_code':failed.returncode,
                     'prior_output_preserved':preserved, 'stderr':failed.stderr[-1000:]}
        return [replacement, traversal]
