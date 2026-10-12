# SPDX-License-Identifier: Apache-2.0
"""Bounded evidence for actual test runs, without inventing task assertions."""
import hashlib
import re
import shlex
from pathlib import Path


def test_command(command):
    """Recognize simple test invocations, avoiding log readers and shell pipelines."""
    try: args=shlex.split(command)
    except ValueError: return False
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
    text=re.sub(r'\x1b\[[0-9;]*m','',str(output))[-8000:]
    candidates=[]
    for m in re.finditer(r'(?m)^\s*Ran (\d+) tests?\b[^\n]*\n(?:[ \t]*\n)*([^\n]+)',text):
        count=int(m[1]);footer=m[2].strip()
        skipped=sum(int(n) for n in re.findall(r'(?:skipped|expected failures)=(\d+)',footer))
        count=max(0,count-skipped)
        candidates.append((m.start(),{'count':count,'passed':count>0 and footer.startswith('OK'),
                                     'empty':count==0,'failed':footer.startswith('FAILED')}))
    for m in re.finditer(r'(?m)^(?:=+\s*)?((?:\d+ (?:subtests? )?[a-z]+(?:, )?)+) in [\d.]+s(?:\s*=+)?\s*$',text):
        entries=[(int(number),subtest,kind) for number,subtest,kind in re.findall(r'(\d+) (?:(subtests?) )?([a-z]+)',m[1])]
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
    """Hash files; optional absent outputs are markers for replay, never proof."""
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
