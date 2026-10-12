# SPDX-License-Identifier: Apache-2.0
"""Verify requested saved JSON and editor actions using actual files/results."""
import json
from pathlib import Path

from app.verification import source_hashes
from app.dependency_policy import constrained_manifest,dependency_issue
from app.test_requirements import added_paths,issue as test_issue


def requested_output_path(contract, state):
    name=contract.get('deliverables',{}).get('path')
    if not name: return None
    path=Path(name).expanduser()
    if not path.is_absolute(): path=Path(state['cwd'])/path
    # Keep the requested name in the hash proof, including a symlink's name.
    # Changing its target after checks must invalidate the proof too.
    return path.absolute()


def verification_paths(contract, state):
    paths=state.get('edited_sources',[])+state.get('inspected_sources',[])+state.get('files_written',[])
    manifest=constrained_manifest(contract,state)
    if manifest is not None and (manifest.exists() or manifest.is_symlink()): paths=paths+[str(manifest)]
    additions=added_paths(contract,state)
    if additions: paths=paths+additions
    expected=requested_output_path(contract,state)
    if expected: paths=paths+[str(expected)]
    return list(dict.fromkeys(paths))


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
            def invalid_constant(value): raise ValueError('Nonfinite values are not valid JSON: '+value)
            data=json.loads(path.read_text(),parse_constant=invalid_constant)
            reference=state.get('score_reference')
            if contract.get('workflow')=='nfl_scores_export':
                if not reference: raise ValueError('Retrieve the actual requested scores before exporting')
                if not isinstance(data,dict) or data.get('date')!=reference['date'] or data.get('source')!=reference['source']:
                    raise ValueError('Saved JSON must retain the retrieved date and source')
                fields=('away','away_score','home','home_score')
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
