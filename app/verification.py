# ==============================================================================
# app/verification.py - recognise real test runs and fingerprint the files they covered
#
# Role in the app: app/agent.py uses test_command() to decide whether a shell
# command counts as a test run, test_summary() to read pass/fail/empty out of
# its output, and source_hashes() to prove the files were unchanged while the
# tests ran. Together they back the rule "work is only verified by real tests
# on byte-identical files" (see AgentRun.execute and finish_task).
#
# Design decisions: everything is conservative. A command is a test command
# only if it is a plain unittest/pytest/cargo-test/test_*.py invocation with no
# pipes, redirects or substitutions (so "cat log | grep OK" cannot fake a pass).
# Output parsing recognises only the runners' own summary lines, and a run with
# zero collected tests is 'empty', never 'passed'.
#
# Tests: tests/test_verified_final.py, tests/test_completion.py and others.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0

"""Bounded evidence for actual test runs, without inventing task assertions."""
import hashlib
import re
import shlex
from pathlib import Path


def test_command(command):
    """Return True when `command` is a simple, direct test invocation.

    Accepted: python[3[.x]] -m unittest|pytest, python test_*.py, pytest, cargo test,
    optionally wrapped in up to three levels of `bash -c '...'`.
    Rejected: shell metacharacters (; & | < > $ `) in any argument, which would
    let a command print a fake "OK" or hide the real runner's exit status.
    """
    try: args=shlex.split(command)
    except ValueError: return False
    # Unwrap `bash -c "..."` a few times (agents often wrap commands), but not
    # unboundedly.
    for _ in range(3):
        if len(args)==3 and Path(args[0]).name in ('bash','sh') and args[1] in ('-c','-lc'):
            try: args=shlex.split(args[2])
            except ValueError: return False
        else: break
    if not args or any(re.search(r'[;&|<>$`]',arg) for arg in args): return False
    executable=Path(args[0]).name
    if re.fullmatch(r'python(?:\d+(?:\.\d+)?)?',executable):
        return args[1:3] in (['-m','unittest'],['-m','pytest']) or bool(
            len(args)>1 and Path(args[1]).name.startswith('test_') and args[1].endswith('.py'))
    return executable=='pytest' or (executable=='cargo' and args[1:2]==['test'])


def test_summary(output):
    """Parse a test run's output into {'count','passed','empty','failed'}.

    Understands unittest ("Ran N tests" + OK/FAILED footer, skips subtracted),
    pytest (the final "N passed, M failed in 1.2s" line, subtests counted as detail
    only) and cargo ("test result: ok. N passed; M failed"). Only the last 8000
    characters are examined, ANSI colours are stripped, and when several summaries
    appear the one latest in the output wins.
    Returns None when no recognised summary exists (so "no evidence", not "passed").
    """
    text=re.sub(r'\x1b\[[0-9;]*m','',str(output))[-8000:]
    candidates=[]
    # unittest: skipped tests and expected failures do not prove anything, so
    # they are removed from the count.
    for m in re.finditer(r'(?m)^\s*Ran (\d+) tests?\b[^\n]*\n(?:[ \t]*\n)*([^\n]+)',text):
        count=int(m[1]);footer=m[2].strip()
        skipped=sum(int(n) for n in re.findall(r'(?:skipped|expected failures)=(\d+)',footer))
        count=max(0,count-skipped)
        candidates.append((m.start(),{'count':count,'passed':count>0 and footer.startswith('OK'),
                                     'empty':count==0,'failed':footer.startswith('FAILED')}))
    for m in re.finditer(r'(?m)^(?:=+\s*)?((?:\d+ (?:subtests? )?[a-z]+(?:, )?)+) in [\d.]+s(?:\s*=+)?\s*$',text):
        entries=[(int(number),subtest,kind) for number,subtest,kind in re.findall(r'(\d+) (?:(subtests?) )?([a-z]+)',m[1])]
        # pytest-subtests report extra "subtests passed" counts; counting them would
        # inflate the number of real top-level tests.
        # Subcases are additional detail, not extra top-level test functions.
        # Their failures still invalidate the suite's passing evidence.
        count=sum(number for number,subtest,kind in entries if not subtest and kind=='passed')
        failed=any(number>0 and kind in ('failed','error','errors') for number,subtest,kind in entries)
        candidates.append((m.start(),{'count':count,'passed':count>0 and not failed,'empty':not count and not failed,'failed':failed}))
    rust=list(re.finditer(r'(?m)^test result: (ok|FAILED)\.\s*(\d+) passed; (\d+) failed;',text))
    if rust:
        count=sum(int(m[2]) for m in rust);failed=any(m[1]!='ok' or int(m[3])>0 for m in rust)
        candidates.append((rust[-1].start(),{'count':count,'passed':count>0 and not failed,'empty':count==0 and not failed,'failed':failed}))
    return max(candidates,key=lambda item:item[0])[1] if candidates else None


def source_hashes(paths, *, optional_missing=()):
    """Map each path to the SHA-256 of its content, or None if any cannot be trusted.

    Args:
        paths: files to fingerprint (at most 64).
        optional_missing: paths allowed to be absent right now; recorded as None
            so a later comparison still sees whether they appeared.
    Returns:
        dict {path: hexdigest|None}, or None when there are too many paths, a path
        is not a regular file, a file exceeds 2 MB, or an OS error occurred.
    Comparing two results is how the agent proves files did not change between
    the start and the end of a test run.
    """
    optional={str(Path(name)) for name in optional_missing}
    if not paths or len(paths)>64: return None
    hashes={}
    try:
        for name in paths:
            path=Path(name)
            if str(path) in optional and not path.exists() and not path.is_symlink():
                hashes[str(path)]=None
                continue
            if not path.is_file() or path.stat().st_size>2_000_000: return None
            with path.open('rb') as source:
                hashes[str(path)]=hashlib.file_digest(source,'sha256').hexdigest()
    except OSError: return None
    return hashes
