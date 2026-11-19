# ==============================================================================
# Program: inventory_goal_audit.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Benchmark, evaluation, verification, or audit script supporting the Tiny
#          Dancer testing framework. Operational automation, benchmark evaluation, and
#          system diagnostic harness. Executes high-throughput workload profiling
#          across CPU/GPU execution tiers with strict resource bounds. Enforces
#          reproducible benchmark metrics, mathematical latency bounds, and
#          deterministic subprocess exit contracts.
# ==============================================================================

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


# ------------------------------------------------------------------------------
# check_inventory_goal: Function Pipeline & Contract Specification
# Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
# Invariant: Preconditions validated before mutation; postconditions guarantee return contract
# Failure Modes: Catches or propagates domain exceptions according to API contracts
# ------------------------------------------------------------------------------
def check_inventory_goal(folder, root):
    folder, root = Path(folder), Path(root)
    program = folder / 'inventory.py'
    # ------------------------------------------------------------------------------
    # invoke: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def invoke(tree, output):
        try:
            return subprocess.run([sys.executable, str(program), str(tree), str(output)],
                                  cwd=folder, capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return subprocess.CompletedProcess([], 1, '', str(exc))
    # ------------------------------------------------------------------------------
    # expected: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def expected(files):
        return sorted([{'path':name, 'size':len(data), 'sha256':hashlib.sha256(data).hexdigest()}
                       for name, data in files.items()], key=lambda row:row['path'])
    # ------------------------------------------------------------------------------
    # matches: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
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
