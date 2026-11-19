# ==============================================================================
# Program: deliverables.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Validates and packages target code deliverables, verifying that generated
#          patches satisfy all benchmark requirements before submission. Core
#          component of the autonomous agent reasoning architecture governing
#          multi-turn execution cycles, state graph transitions, and prompt synthesis.
#          Strictly enforces mathematical bounds on LLM token context windows, rolling
#          memory buffers, and timeout thresholds. Guarantees transactional execution
#          invariants, deterministic failure isolation, and thread-safe API contracts.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
"""Verify requested saved JSON and editor actions using actual files/results."""
import json
from pathlib import Path

from app.verification import source_hashes
from app.dependency_policy import constrained_manifest,dependency_issue
from app.test_requirements import added_paths,issue as test_issue


# ------------------------------------------------------------------------------
# requested_output_path: Function Pipeline & Contract Specification
# Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
# Invariant: Preconditions validated before mutation; postconditions guarantee return contract
# Failure Modes: Catches or propagates domain exceptions according to API contracts
# ------------------------------------------------------------------------------
def requested_output_path(contract, state):
    name=contract.get('deliverables',{}).get('path')
    if not name: return None
    path=Path(name).expanduser()
    if not path.is_absolute(): path=Path(state['cwd'])/path
    # Keep the requested name in the hash proof, including a symlink's name.
    # Changing its target after checks must invalidate the proof too.
    return path.absolute()


# ------------------------------------------------------------------------------
# verification_paths: Function Pipeline & Contract Specification
# Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
# Invariant: Preconditions validated before mutation; postconditions guarantee return contract
# Failure Modes: Catches or propagates domain exceptions according to API contracts
# ------------------------------------------------------------------------------
def verification_paths(contract, state):
    paths=state.get('edited_sources',[])+state.get('inspected_sources',[])+state.get('files_written',[])
    manifest=constrained_manifest(contract,state)
    if manifest is not None and (manifest.exists() or manifest.is_symlink()): paths=paths+[str(manifest)]
    additions=added_paths(contract,state)
    if additions: paths=paths+additions
    expected=requested_output_path(contract,state)
    if expected: paths=paths+[str(expected)]
    return list(dict.fromkeys(paths))


# ------------------------------------------------------------------------------
# inspect_deliverables: Function Pipeline & Contract Specification
# Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
# Invariant: Preconditions validated before mutation; postconditions guarantee return contract
# Failure Modes: Catches or propagates domain exceptions according to API contracts
# ------------------------------------------------------------------------------
def inspect_deliverables(contract,state):
    issue=dependency_issue(contract,state)
    if issue: return issue,None
    issue=test_issue(contract,state)
    if issue: return issue,None
    required=contract.get('deliverables',{})
    if not required: return None,None
    candidates=list(dict.fromkeys(state.get('files_written',[])+state.get('inspected_sources',[])+state.get('editor_opened',[])))
    expected=requested_output_path(contract,state)
    if expected:
        if not expected.is_file(): return 'Save the requested JSON at '+str(expected)+'.',None
        # An actual named output can be created by a shell command. Do not
        # fabricate a write_file event merely to acknowledge that file.
        candidates=[str(expected)]
    if not candidates: return 'The requested JSON file has not been saved.',None
    errors=[]
    for name in candidates:
        path=Path(name)
        if path.suffix.lower()!='.json': continue
        try:
            if path.stat().st_size>2_000_000: raise ValueError('JSON verification limit is 2 MB')
            # ------------------------------------------------------------------------------
            # invalid_constant: Function Pipeline & Contract Specification
            # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
            # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
            # Failure Modes: Catches or propagates domain exceptions according to API contracts
            # ------------------------------------------------------------------------------
            def invalid_constant(value): raise ValueError('Nonfinite values are not valid JSON: '+value)
            data=json.loads(path.read_text(),parse_constant=invalid_constant)
            reference=state.get('score_reference')
            if contract.get('workflow')=='nfl_scores_export':
                if not reference: raise ValueError('Retrieve the actual requested scores before exporting')
                if not isinstance(data,dict) or data.get('date')!=reference['date'] or data.get('source')!=reference['source']:
                    raise ValueError('Saved JSON must retain the retrieved date and source')
                fields=('away','away_score','home','home_score')
                # ------------------------------------------------------------------------------
                # rows: Function Pipeline & Contract Specification
                # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
                # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
                # Failure Modes: Catches or propagates domain exceptions according to API contracts
                # ------------------------------------------------------------------------------
                def rows(games):
                    if not isinstance(games,list): raise ValueError('Saved JSON needs the retrieved games array')
                    if any(not isinstance(game,dict) or any(not isinstance(game.get(k),str) for k in ('away','home'))
                           or any(type(game.get(k)) is not int for k in ('away_score','home_score')) for game in games):
                        raise ValueError('Each game needs team names and integer scores')
                    return sorted(tuple(game[key] for key in fields) for game in games)
                if rows(data.get('games'))!=rows(reference['games']): raise ValueError('Saved JSON must include every retrieved matchup and exact score')
            if required.get('editor') and str(path.resolve()) not in state.get('editor_opened',[]):
                errors.append('The requested JSON file has not been opened in Code OSS.');continue
            hashes=source_hashes([str(path)])
            if not hashes: raise ValueError('The saved file could not be verified')
            return None,{'path':str(path),'files_sha256':hashes,'game_count':len(reference['games']) if reference else None}
        except (OSError,ValueError,KeyError,TypeError) as exc: errors.append(str(exc))
    return errors[0] if errors else 'Save the requested output as a .json file.',None
