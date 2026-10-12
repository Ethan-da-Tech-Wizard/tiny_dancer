# SPDX-License-Identifier: Apache-2.0
"""Bounded factual working evidence for a new model context; never execute code."""
import hashlib
import json
from pathlib import Path
from app.failure_feedback import checkpoint_failures
from app.source_diagnostics import python_runtime_notes


def runtime_source_evidence(cwd,sources):
    """Refresh existing import-derived library notes from bounded observed files."""
    base=Path(cwd).resolve();files=[];seen=set()
    for value in sources:
        if len(files)>=8:break
        try:
            path=Path(value);path=(path if path.is_absolute() else base/path).resolve(strict=True)
            if path in seen or not path.is_relative_to(base) or not path.is_file() or path.suffix!='.py':continue
            seen.add(path)
            if path.stat().st_size>12000:continue
            files.append({'path':str(path),'text':path.read_text()})
        except (OSError,ValueError,UnicodeError):continue
    notes=[]
    for note in python_runtime_notes(files):
        if len(json.dumps(notes+[note],ensure_ascii=False,separators=(',',':'))) > 1400:break
        notes.append(note)
    return notes


def preview(text,limit,marker='\n[... omitted; retrieve the full saved tool result ...]\n'):
    if limit<=0:return ''
    if len(text)<=limit:return text
    if limit<=len(marker):return marker[:limit]
    room=limit-len(marker);head=room//2;tail=room-head
    return text[:head]+marker+text[-tail:]


def checkpoint_evidence(observations,cwd,sources,source_budget=6000,failure_budget=1600):
    paths=[];modified=[];last_failure=None
    def add(path,changed=False):
        if isinstance(path,str) and path not in paths:paths.append(path)
        if changed and isinstance(path,str) and path not in modified:modified.append(path)
    for name,result in reversed(observations):
        if not isinstance(result,dict):continue
        if last_failure is None and (result.get('error') or result.get('timed_out') or result.get('verified') is False or type(result.get('exit_code')) is int and result['exit_code']!=0):
            output=result.get('output',result.get('text',result.get('error','')))
            if not output and isinstance(result.get('checks'),list):output='\n'.join(str(check.get('output',check.get('error',''))) for check in result['checks'] if isinstance(check,dict) and (check.get('exit_code') or check.get('error') or check.get('timed_out')))
            last_failure={'tool':name,'result':{k:result[k] for k in ('artifact','path','exit_code','error','timed_out','test_count') if k in result},'preview':preview(str(output),failure_budget)}
            failures=checkpoint_failures(result)
            if failures:last_failure['failure_evidence']=failures
        if name.split('.')[-1] in ('read_file','write_file','apply_patch'):
            changed=name.split('.')[-1] in ('write_file','apply_patch')
            add(result.get('path'),changed)
            files=result.get('files',[])
            if isinstance(files,list):
                for file in files:add(file.get('path') if isinstance(file,dict) else file,changed)
    for path in sources:add(path)
    snapshots=[];base=Path(cwd).resolve();remaining=source_budget
    candidates=[];seen=set()
    code_suffixes={'.py','.rs','.c','.cc','.cpp','.cxx','.h','.hpp','.js','.jsx','.ts','.tsx','.go','.java','.cs','.rb','.php','.sh','.sql','.lua','.zig','.swift','.kt','.scala','.jl','.html','.css','.scss','.svelte','.vue'}
    for value in paths:
        try:
            path=Path(value);path=path if path.is_absolute() else base/path
            resolved=path.resolve(strict=True)
            if resolved in seen or not resolved.is_relative_to(base) or not resolved.is_file():continue
            seen.add(resolved)
            relative=resolved.relative_to(base);name=relative.name.lower();stem=relative.stem.lower()
            test=any(part.lower() in ('tests','test','__tests__','spec','specs') for part in relative.parts[:-1]) or name.startswith(('test_','test.')) or stem in ('test','tests') or stem.endswith(('_test','_tests','_spec','.test','.spec'))
            candidates.append((path,resolved,test,relative.suffix.lower() in code_suffixes))
        except (OSError,ValueError):continue
    by_path={item[1]:item for item in candidates}
    changed=[]
    for value in modified:
        try:
            path=Path(value);resolved=(path if path.is_absolute() else base/path).resolve(strict=True)
            if resolved in by_path:changed.append(by_path[resolved])
        except (OSError,ValueError):continue
    # Test reads must not replace every implementation snapshot. Prefer the
    # changed implementation and the test named by actual failure evidence.
    primary=next((item for item in changed if not item[2]),None) or next((item for item in candidates if item[3] and not item[2]),None)
    tests=[item for item in candidates if item[2]]
    failure_text=json.dumps(last_failure or {},ensure_ascii=False)
    failing=next((item for item in tests if item[1].name in failure_text),None) or next(iter(tests),None)
    preferred=[item for item in (primary,failing) if item is not None]
    ordered=preferred+[item for item in candidates if item not in preferred]
    for path,resolved,_,_ in ordered:
        if len(snapshots)>=2:break
        try:
            # Refresh only previously observed project files. A retargeted
            # symlink must not cause a new read outside the working project.
            if not resolved.is_relative_to(base) or not resolved.is_file():continue
            before=resolved.stat();snapshot={'path':str(path),'bytes':before.st_size}
            if before.st_size>12000:
                snapshot['read_hint']='Large file; use targeted read_file ranges.'
            else:
                data=resolved.read_bytes();after=resolved.stat()
                if before.st_mtime_ns!=after.st_mtime_ns or before.st_size!=after.st_size:continue
                if b'\x00' in data:continue
                text=data.decode('utf-8',errors='replace');snapshot['sha256']=hashlib.sha256(data).hexdigest()
                allowance=min(6000,remaining)
                if len(text)<=allowance:snapshot['text']=text
                elif allowance>0:
                    snapshot.update(text=preview(text,allowance,'\n[... source characters omitted; read this file ...]\n'),text_truncated=True,partial_lines=True,read_hint='Source preview contains partial lines; use read_file on this path before changing omitted code.')
                else:snapshot['read_hint']='Use targeted read_file ranges; no source-preview budget remains.'
                remaining-=min(len(text),allowance)
            snapshots.append(snapshot)
        except (OSError,ValueError):continue
    return {'source_snapshots':snapshots,'last_failed_result':last_failure}


def inspection_test_evidence(result):
    """Keep bounded actual runner discovery, never a cached test verdict."""
    if not isinstance(result, dict):
        return None
    evidence = {'note': 'Earlier inspection; runner availability is not a successful test run.'}
    truncated = False
    omitted = 0

    def fits(value):
        return len(json.dumps(value, ensure_ascii=False, separators=(',', ':'))) <= 1800

    artifact = result.get('artifact')
    if isinstance(artifact, str):
        if len(artifact) <= 400:
            evidence['artifact'] = artifact
        else:
            truncated = True
    runtime = {}
    raw_runtime = result.get('runtime')
    if isinstance(raw_runtime, dict):
        for key in ('python', 'version', 'pytest_module', 'pytest_command', 'cargo'):
            if key not in raw_runtime:
                continue
            value = raw_runtime[key]
            valid = type(value) is bool if key == 'pytest_module' else value is None or isinstance(value, str)
            if not valid:
                continue
            if isinstance(value, str) and len(value) > (80 if key == 'version' else 300):
                truncated = True
                continue
            candidate = {**runtime, key: value}
            if fits({**evidence, 'runtime': candidate}):
                runtime = candidate
            else:
                truncated = True
    if runtime:
        evidence['runtime'] = runtime
    commands = []
    raw_commands = result.get('test_candidates')
    if isinstance(raw_commands, list):
        omitted = max(0, len(raw_commands) - 32)
        for entry in raw_commands[:32]:
            if not isinstance(entry, dict) or not isinstance(entry.get('command'), str) or not entry['command'].strip():
                continue
            if len(entry['command']) > 600 or len(commands) >= 8:
                omitted += 1
                continue
            candidate = {'command': entry['command']}
            if type(entry.get('available')) is bool:
                candidate['available'] = entry['available']
            if isinstance(entry.get('evidence'), str):
                candidate['evidence'] = entry['evidence'][:160]
                if len(entry['evidence']) > 160:
                    truncated = True
            proposed = {**evidence, 'test_candidates': commands + [candidate]}
            if fits(proposed):
                commands.append(candidate)
            else:
                omitted += 1
    if not runtime and not commands:
        return None
    if commands:
        evidence['test_candidates'] = commands
    if truncated or omitted:
        evidence.update(truncated=True, commands_omitted=omitted,
                        read_hint='Re-inspect the project for omitted runner details; omitted commands were not shortened or executed.')
    return evidence
