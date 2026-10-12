# SPDX-License-Identifier: Apache-2.0
"""Require actual compatible checks for newly added plain Python test functions."""
import ast
import hashlib
from pathlib import Path
import shlex
from app.test_requirements import added_paths
from app.verification import source_hashes,test_command,test_summary
from app.deliverables import verification_paths


def plain_tests(contract,state):
    found={}
    for name in added_paths(contract,state) or []:
        path=Path(name)
        if path.suffix!='.py':continue
        try:
            data=path.read_bytes();tree=ast.parse(data)
        except (OSError,SyntaxError):continue
        functions=[n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test_')]
        # A custom unittest adapter may deliberately collect plain functions.
        adapter=any(isinstance(n,ast.FunctionDef) and n.name=='load_tests' or
                    isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute)) and
                    (n.func.id if isinstance(n.func,ast.Name) else n.func.attr)=='FunctionTestCase' for n in ast.walk(tree))
        if functions and not adapter:found[str(path.resolve())]=hashlib.sha256(data).hexdigest()
    return found


def pytest_covers(command,cwd,path):
    if not test_command(command):return False
    args=shlex.split(command)
    for _ in range(3):
        if len(args)==3 and Path(args[0]).name in ('bash','sh') and args[1] in ('-c','-lc'):args=shlex.split(args[2])
        else:break
    if args[1:3]==['-m','pytest']:rest=args[3:]
    elif Path(args[0]).name=='pytest':rest=args[1:]
    else:return False
    selectors=[]
    for arg in rest:
        if arg in ('-q','-qq','-v','-vv','-s','--disable-warnings','--no-header','--no-summary','--strict-markers'):continue
        if arg.startswith(('--tb=','--color=','--maxfail=')):continue
        # Filters/unknown options and node selectors cannot witness a whole file.
        if arg.startswith('-') or '::' in arg:return False
        selectors.append(arg)
    if not selectors:return Path(path).is_relative_to(Path(cwd).resolve())
    for selector in selectors:
        selected=(Path(cwd)/selector).resolve()
        if selected==Path(path) or selected.is_dir() and Path(path).is_relative_to(selected):return True
    return False


def record_checks(contract,state,outcomes,checked_sources):
    receipts=state.setdefault('plain_test_collection_receipts',{})
    for outcome in outcomes:
        summary=test_summary(outcome.get('output',''))
        if outcome.get('exit_code')!=0 or outcome.get('timed_out') or not summary or not summary['passed']:continue
        for path,digest in plain_tests(contract,state).items():
            if pytest_covers(outcome['command'],state['cwd'],path):
                receipts[path]={'sha256':digest,'command':outcome['command'],'artifact':outcome.get('artifact'),'checked_sources':checked_sources}


def issue(contract,state):
    receipts=state.get('plain_test_collection_receipts',{})
    plain=plain_tests(contract,state)
    if not plain:return None
    current=source_hashes(verification_paths(contract,state))
    missing=[Path(path).relative_to(Path(state['cwd']).resolve()).as_posix() for path,digest in plain.items()
             if not current or receipts.get(path,{}).get('sha256')!=digest or receipts.get(path,{}).get('checked_sources')!=current]
    if missing:
        return 'New plain Python test functions have not been checked by a compatible runner: '+', '.join(missing[:8])+'. unittest discovery does not collect these functions. Run the available pytest runner on these files without selection filters, or use properly collected unittest tests, then finish.'
    return None
