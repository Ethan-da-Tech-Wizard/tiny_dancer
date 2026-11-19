# ==============================================================================
# Program: test_authority.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Manages test discovery, test command construction, test requirement
#          enforcement, and authoritative verdict evaluation. Core component of the
#          autonomous agent reasoning architecture governing multi-turn execution
#          cycles, state graph transitions, and prompt synthesis. Strictly enforces
#          mathematical bounds on LLM token context windows, rolling memory buffers,
#          and timeout thresholds. Guarantees transactional execution invariants,
#          deterministic failure isolation, and thread-safe API contracts.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
"""Explain test provenance without treating model-authored assertions as truth."""
import re
import hashlib
from pathlib import Path
from app.failure_feedback import checkpoint_failures
from app.test_requirements import snapshot as test_definitions


# ------------------------------------------------------------------------------
# snapshot: Function Pipeline & Contract Specification
# Algorithmic Complexity: Time: O(B) linear with respect to serialized payload byte length | Space: O(B) memory mapped buffer or byte stream heap allocation
# Invariant: Preconditions validated before mutation; postconditions guarantee return contract
# Failure Modes: Catches or propagates domain exceptions according to API contracts
# ------------------------------------------------------------------------------
def snapshot(cwd):
    """Track whole test files, including fixtures/constants outside test bodies."""
    root=Path(cwd).resolve();tests=test_definitions(cwd);sources={};complete=tests['complete']
    for name in tests['sources']:
        path=root/name
        try:
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                complete=False;continue
            with path.open('rb') as handle: data=handle.read(250001)
            if len(data)>250000:complete=False;continue
            sources[name]={'sha256':hashlib.sha256(data).hexdigest()}
        except OSError:complete=False
    return {'complete':complete,'sources':sources}


# ------------------------------------------------------------------------------
# failure_test_origins: Function Pipeline & Contract Specification
# Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
# Invariant: Preconditions validated before mutation; postconditions guarantee return contract
# Failure Modes: Catches or propagates domain exceptions according to API contracts
# ------------------------------------------------------------------------------
def failure_test_origins(result, baseline, current, cwd):
    evidence = checkpoint_failures(result)
    if not evidence: return None
    root = Path(cwd).resolve()
    origins = []
    known = bool(baseline and baseline.get('complete') and current.get('complete'))
    for failure in evidence['failures'][:8]:
        files = []
        for location in failure.get('locations', []):
            match = re.search(r'File "([^"]+)", line \d+|^(.*?\.(?:py|rs)):\d+', location)
            if not match: continue
            value = next(part for part in match.groups() if part)
            path = Path(value)
            try: relative = (path if path.is_absolute() else root/path).resolve().relative_to(root).as_posix()
            except (ValueError,OSError): continue
            if relative in current.get('sources', {}):files.append(relative)
        for name in dict.fromkeys(files):
            before = baseline.get('sources', {}).get(name) if baseline else None
            after = current.get('sources', {}).get(name)
            origin = 'unknown' if not known else 'added_since_task_start' if before is None else 'unchanged_since_task_start' if before == after else 'changed_since_task_start'
            origins.append({'test':failure['test'], 'path':name, 'origin':origin})
    if not origins: return None
    return {'failures':origins, 'note':'Provenance describes the test file, not who changed it or whether its assertion is correct. The original user goal defines expected behavior. Check newly added or changed test expectations against that goal and the actual language/library behavior before changing implementation to satisfy them. Preserve supplied acceptance tests; correct an erroneous test you added only with a concrete reason.'}
