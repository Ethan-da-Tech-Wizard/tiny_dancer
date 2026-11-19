# ==============================================================================
# app/batching.py - inspect_project and run_checks tool implementations
#
# Role in the app: app/tools.py ComputerTools.execute() lazily imports
# inspect_project() and run_checks(). They exist so a small local model can look
# at a whole project (a directory listing, up to eight source/test files and the
# available test runners) in ONE call, and run several related checks in ONE
# call, instead of spending many slow turns on single reads and commands.
#
# Design decisions: inspection is strictly bounded (100 directory entries,
# 8 files, 16 KB per file, symlinks skipped) and never imports or executes the
# project's code (the Python probe runs with -I isolation from a neutral cwd
# environment). Every result is also saved as a JSON artifact so a trimmed
# preview in the prompt never loses data. run_checks runs commands sequentially
# (stopping at the first failure by default), saves the artifact after every
# command so a crash or timeout still leaves evidence, and when a test runner
# is missing or collected zero tests it attaches real runner-discovery facts
# without silently substituting another command.
#
# Tests: tests/test_batching.py, tests/test_inspection_source_batch.py.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0

"""Bounded project inspection and sequential, auditable groups of checks."""
import asyncio
import ast
import heapq
import json
import re
import shlex
import shutil
import uuid
from pathlib import Path
from app.verification import test_command,test_summary
from app.tool_runtime import tool_environment
from app.prompting import inspection_files_preview
from app.source_diagnostics import python_runtime_notes


def save_result(artifacts, name, result):
    """Write a result dict as pretty JSON in the artifact folder and return its URL.

    Uses temp-then-rename so the UI or model never reads half-written JSON, which
    matters because run_checks rewrites the same file after every command.

    Returns:
        '/artifacts/<name>.json'.
    """
    path=Path(artifacts)/(name+'.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    temporary.replace(path)
    return '/artifacts/'+path.name


def project_snapshot(args,cwd):
    """Read a directory listing and a bounded set of files, synchronously.

    Args:
        args: optional 'path' (folder, default cwd) and 'files' (list of at most 8
            paths). When files is omitted/empty, a default set is chosen.
        cwd: base for relative paths.
    Returns:
        dict with entries (first 100, directories first), files (text up to 16 KB
        each with a truncated flag or an error), unittest_dirs and pytest_found
        (used by inspect_project to propose test commands).
    Raises:
        ValueError: not a directory, or invalid 'files'.
    """
    directory=Path(args.get('path') or cwd).expanduser()
    if not directory.is_absolute(): directory=Path(cwd)/directory
    directory=directory.resolve()
    if not directory.is_dir(): raise ValueError('Inspection path must be a directory')
    entries=[]
    # nsmallest bounds the work on huge folders (no full sort) and gives a stable
    # order: directories first, then case-insensitive names.
    for path in heapq.nsmallest(100,directory.iterdir(),key=lambda p:(not p.is_dir(),p.name.lower())):
        entries.append({'name':path.name,'directory':path.is_dir()})
    files=args.get('files')
    # Auto-selection order: manifests, then tests, then root sources, then src/,
    # so the model sees how the project is built and tested before the code.
    if files is None or files==[]:
        preferred=['pyproject.toml','Cargo.toml','requirements.txt','package.json','CMakeLists.txt','README.md']
        source_types={'.py','.rs','.c','.h','.cc','.cpp','.hpp','.js','.mjs','.ts','.tsx','.jsx','.sh'}
        # Up to 8 plain, non-hidden, non-symlink source files in a folder.
        def source_names(folder):
            return heapq.nsmallest(8,(p for p in folder.iterdir() if not p.name.startswith('.') and not p.is_symlink() and p.is_file() and p.suffix in source_types),key=lambda p:(not p.name.startswith('test_'),p.name))
        root_sources=source_names(directory)
        preferred += [p.name for p in root_sources if p.name.startswith('test_')]
        for name in ('tests','test'):
            folder=directory/name
            if folder.is_dir() and not folder.is_symlink():
                preferred += [str(p.relative_to(directory)) for p in source_names(folder)]
        preferred += [p.name for p in root_sources if not p.name.startswith('test_')]
        folder=directory/'src'
        if folder.is_dir() and not folder.is_symlink():
            preferred += [str(p.relative_to(directory)) for p in source_names(folder)]
        # dict.fromkeys de-duplicates while keeping order; symlinks are refused so a
        # link cannot expose files outside the project.
        files=[name for name in dict.fromkeys(preferred) if (directory/name).is_file() and not (directory/name).is_symlink()][:8]
    if not isinstance(files,list) or len(files)>8 or any(not isinstance(p,str) or not p.strip() for p in files):
        raise ValueError('files must contain at most eight nonempty paths')
    outputs=[];unittest_dirs=set();pytest_found=False
    for name in files:
        path=Path(name).expanduser()
        if not path.is_absolute(): path=directory/path
        record={'path':str(path.resolve())}
        try:
            # Read one byte past the 16 KB limit to learn whether the file was truncated
            # without reading the rest of it.
            with path.open('rb') as source: data=source.read(16385)
            # NUL bytes identify binary files, which are useless (and noisy) as text.
            if b'\0' in data: raise ValueError('Binary file; use a suitable tool')
            text=data[:16384].decode('utf-8')
            record.update(text=text,truncated=len(data)>16384)
            if path.suffix=='.py' and not record['truncated']:
                try:
                    # Cheap, safe test-style detection by parsing (never importing) the file:
                    # 'import unittest' implies the unittest runner; top-level test_ functions or
                    # a test_*.py name without unittest implies pytest.
                    tree=ast.parse(text)
                    has_unittest=any(isinstance(n,ast.Import) and any(a.name=='unittest' for a in n.names)
                                          or isinstance(n,ast.ImportFrom) and n.module=='unittest' for n in ast.walk(tree))
                    if has_unittest: unittest_dirs.add(str(path.resolve().parent))
                    pytest_found |= any(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test_') for n in tree.body)
                    pytest_found |= path.name.startswith('test_') and not has_unittest
                except SyntaxError: pass
        except (OSError,ValueError,UnicodeError) as exc: record['error']=str(exc)
        outputs.append(record)
    return {'path':str(directory),'entries':entries,'files':outputs,'unittest_dirs':sorted(unittest_dirs),'pytest_found':pytest_found}


async def inspect_project(args,cwd,artifacts):
    """Inspect a project and report which test runners are actually available.

    Args:
        args: see project_snapshot. cwd: project folder.
        artifacts: artifact folder for the full saved result.
    Returns:
        The snapshot plus runtime (python path/version, pytest and cargo
        availability), test_candidates (concrete commands with 'available' and the
        evidence they came from), runtime_notes, artifact, and a prompt-sized
        preview of files.
    Candidates are suggestions from evidence, never verdicts: a command being
    available does not mean its tests pass.
    """
    result=await asyncio.to_thread(project_snapshot,args,cwd)
    env=tool_environment()
    python=shutil.which('python',path=env.get('PATH')) or shutil.which('python3',path=env.get('PATH'))
    runtime={'python':python,'pytest_command':shutil.which('pytest',path=env.get('PATH')),'cargo':shutil.which('cargo',path=env.get('PATH'))}
    # Probe the interpreter in isolated mode (-I): it ignores PYTHON* variables,
    # the user site and the current directory, so modules in the inspected
    # folder cannot be imported and the probe cannot execute project code.
    if python:
        # Isolated Python cannot execute/import source from the inspected project.
        command='import importlib.util,json,sys;print(json.dumps({"version":sys.version.split()[0],"pytest_module":importlib.util.find_spec("pytest") is not None}))'
        proc=await asyncio.create_subprocess_exec(python,'-I','-c',command,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        try:
            stdout,_=await asyncio.wait_for(proc.communicate(),5)
            if proc.returncode==0: runtime.update(json.loads(stdout))
        # Never leave an orphaned probe process behind on cancel or timeout.
        except asyncio.CancelledError:
            if proc.returncode is None: proc.kill()
            await proc.wait();raise
        except (asyncio.TimeoutError,ValueError):
            if proc.returncode is None: proc.kill()
            await proc.wait();runtime['probe_error']='Python runtime inspection failed'
    result['runtime']=runtime;result['test_candidates']=[]
    notes=python_runtime_notes(result['files'])
    if notes: result['runtime_notes']=notes
    python_command=shlex.quote(python) if python else 'python3'
    # One 'unittest discover' command per directory that contains unittest tests,
    # expressed relative to the project when possible and always shell-quoted.
    for parent in result.pop('unittest_dirs'):
        try: target=str(Path(parent).relative_to(result['path']))
        except ValueError: target=parent
        result['test_candidates'].append({'command':python_command+" -m unittest discover -s "+shlex.quote(target)+" -p 'test_*.py'",'available':bool(python),'evidence':'unittest imports in '+target})
    # Prefer a real pytest executable, else 'python -m pytest'.
    if result.pop('pytest_found'):
        command=shlex.quote(runtime['pytest_command']) if runtime.get('pytest_command') else python_command+' -m pytest'
        result['test_candidates'].append({'command':command,'available':bool(runtime.get('pytest_command') or runtime.get('pytest_module')),'evidence':'function-style or test_ files; actual interpreter/runner availability'})
    if (Path(result['path'])/'Cargo.toml').is_file():
        result['test_candidates'].append({'command':'cargo test','available':bool(runtime['cargo']),'evidence':'Cargo.toml exists'})
    # The full bounded reads go to disk first...
    result['artifact']=save_result(artifacts,'inspection-'+uuid.uuid4().hex,result)
    # Keep modest sources complete, with the same shared bound at both layers.
    # The artifact retains every bounded read, including omitted source.
    # ...then the in-prompt copy is shrunk to the shared source-character budget.
    result['files']=inspection_files_preview(result['files'],result['path'])
    return result


async def run_checks(args,cwd,artifacts,execute_shell):
    """Run 1-8 shell commands in order and record each real outcome.

    Args:
        args: 'commands' (1-8 non-empty strings, <= 6000 chars each), optional
            'timeout' (int 1..300 seconds per command, default 120) and
            'stop_on_failure' (bool, default True).
        cwd: working folder. artifacts: artifact folder.
        execute_shell: coroutine(command, cwd, timeout) -> dict, normally
            app.tools.shell; injected so tests can fake it.
    Returns:
        dict with checks (per-command outcome), requested, complete, the first
        non-zero exit_code, timed_out, artifact and optional recovery evidence.
    Raises:
        ValueError: invalid arguments.
    """
    commands=args.get('commands')
    if not isinstance(commands,list) or not 1<=len(commands)<=8 or any(not isinstance(c,str) or not c.strip() or len(c)>6000 for c in commands):
        raise ValueError('commands must contain 1–8 nonempty commands, each at most 6000 characters')
    timeout=args.get('timeout',120)
    if isinstance(timeout,bool) or not isinstance(timeout,int) or not 1<=timeout<=300: raise ValueError('timeout must be an integer from 1 to 300')
    if not isinstance(args.get('stop_on_failure',True),bool): raise ValueError('stop_on_failure must be boolean')
    name='checks-'+uuid.uuid4().hex
    result={'checks':[],'requested':len(commands),'complete':False,'exit_code':0,'timed_out':False}
    # Write the (still empty) artifact up front so the URL is valid immediately.
    result['artifact']=save_result(artifacts,name,result)
    for command in commands:
        outcome=await execute_shell(command,cwd,timeout)
        result['checks'].append({'command':command,**outcome})
        failed=outcome['exit_code']!=0 or outcome.get('timed_out')
        if failed:
            # Keep the FIRST failing exit code as the overall result.
            if not result['exit_code']: result['exit_code']=outcome['exit_code'] or 1
            result['timed_out'] |= outcome.get('timed_out',False)
        # Persist after every command: a later hang or kill still leaves evidence.
        save_result(artifacts,name,result)
        # 127 plus 'not found', or Python's "No module named pytest": the runner is
        # absent, which is different from tests failing.
        missing_runner=outcome['exit_code']==127 and 'not found' in outcome.get('output','') or bool(re.search(r"No module named ['\"]?pytest",outcome.get('output','')))
        suite=test_summary(outcome.get('output','')) if test_command(command) else None
        # Runner missing or zero tests collected: attach what is really installed so
        # the model can pick a valid command. The requested command is NOT replaced or
        # rerun, so results stay honest.
        if failed and missing_runner or suite and suite['empty']:
            try:
                inspection=await inspect_project({},cwd,artifacts)
                result['recovery']={key:inspection[key] for key in ('runtime','test_candidates','artifact')}
                result['recovery']['note']='Actual installed runner evidence; requested commands were not replaced or rerun. Inspect the failure and choose relevant available checks.'
            except (OSError,ValueError) as exc: result['recovery']={'inspection_error':str(exc)}
            save_result(artifacts,name,result)
        # Default is fail-fast, since later commands often depend on earlier ones.
        if failed and args.get('stop_on_failure',True): break
    result['complete']=len(result['checks'])==len(commands)
    save_result(artifacts,name,result)
    return result
