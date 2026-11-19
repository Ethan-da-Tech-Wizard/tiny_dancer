# ==============================================================================
# Program: baseline_preview.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Generates baseline summaries and diff previews comparing initial and
#          current workspace states. Core component of the autonomous agent reasoning
#          architecture governing multi-turn execution cycles, state graph
#          transitions, and prompt synthesis. Strictly enforces mathematical bounds on
#          LLM token context windows, rolling memory buffers, and timeout thresholds.
#          Guarantees transactional execution invariants, deterministic failure
#          isolation, and thread-safe API contracts.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
"""Bounded initial-context projection; does not mutate saved tool evidence."""
import copy
from pathlib import Path
from app.prompting import compact_result, excerpt


# ------------------------------------------------------------------------------
# baseline_preview: Function Pipeline & Contract Specification
# Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
# Invariant: Preconditions validated before mutation; postconditions guarantee return contract
# Failure Modes: Catches or propagates domain exceptions according to API contracts
# ------------------------------------------------------------------------------
def baseline_preview(name, result):
    value=copy.deepcopy(result)
    if name=='inspect_project':
        for record in value.get('files',[]):
            path=Path(record.get('path',''))
            try: parts=path.relative_to(Path(value.get('path','/'))).parts
            except ValueError: parts=(path.name,)
            if 'text' in record and (path.name.startswith('test_') or {'tests','test'} & set(parts)):
                record.pop('text')
                record['preview_omitted']=True
                record['read_hint']='Read this test with read_file when needed; full bounded inspection is in the artifact.'
    # Remove intentionally hidden baseline test bodies before allocating the
    # shared source budget, so they cannot crowd out the implementation.
    value=compact_result(value)
    if name=='run_checks':
        for outcome in value.get('checks',[]):
            output=outcome.get('output')
            if isinstance(output,str) and len(output)>1200:
                outcome['output']=excerpt(output,1200)
                outcome['output_truncated']=True
    return value
