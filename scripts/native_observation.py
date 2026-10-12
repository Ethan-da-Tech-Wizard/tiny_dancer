# SPDX-License-Identifier: Apache-2.0
"""Observer policy and public progress evidence, separate from model reasoning."""
import hashlib
from pathlib import Path
import sqlite3


def observation_limit(seconds, until_terminal):
    return None if until_terminal else seconds


def limit_reached(elapsed, limit):
    return limit is not None and elapsed >= limit


def observation_delay(elapsed, limit, stopped=False):
    return 20 if stopped or limit is None else min(20, max(0, limit-elapsed))


def public_action_counts(root, job):
    with sqlite3.connect(f'file:{Path(root)/"run/workspace.sqlite3"}?mode=ro',uri=True) as db:
        return dict(db.execute("SELECT kind,COUNT(*) FROM events WHERE job=? AND kind IN ('tool_start','tool_result','generation_incomplete','context_compacted') GROUP BY kind",(job,)))


class ProgressTracker:
    """Token/command activity is not a claim of better files or passing tests."""
    def __init__(self, folder):
        self.folder=Path(folder).resolve()
        self.previous=None
        self.last_useful=0.0

    def observe(self, checkpoint, elapsed, action_counts=None):
        files={}
        for name in checkpoint.get('edited_sources',[])[:256]:
            path=Path(name)
            path=path if path.is_absolute() else self.folder/path
            try:
                path=path.resolve()
                if not path.is_relative_to(self.folder) or not path.is_file() or path.stat().st_size>2**20:
                    continue
                files[str(path.relative_to(self.folder))]=hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                continue
        steps=checkpoint.get('steps',[])
        completed=sorted(str(step.get('title','')) for step in steps if step.get('done'))
        receipt=checkpoint.get('latest_project_checks') or {}
        checks={key:receipt.get(key) for key in ('test_count','passed','remaining_requirement')}
        checks['files_sha256']=receipt.get('files_sha256',{})
        evidence=(files,completed,checks,bool(checkpoint.get('verified')))
        changed=self.previous is not None and evidence!=self.previous
        if changed:self.last_useful=elapsed
        self.previous=evidence
        return {'changed_evidence':changed,'seconds_since_changed_evidence':round(elapsed-self.last_useful,1),
                'edited_files':len(files),'completed_plan_steps':len(completed),'total_plan_steps':len(steps),
                'latest_test_count':receipt.get('test_count'),'latest_tests_passed':receipt.get('passed'),
                'native_verified':bool(checkpoint.get('verified')),'action_counts':action_counts or {},
                'interpretation':'Elapsed time and token/action counts alone do not establish useful progress or a stall.'}
