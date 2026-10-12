# SPDX-License-Identifier: Apache-2.0
"""Check explicitly requested test-source additions, preserving the initial snapshot."""
import ast
import hashlib
import os
from pathlib import Path
import re


def required_language(contract,state):
    if contract.get('kind')!='work' or not contract.get('lookup_languages'):return None
    goal=state.get('goal','').lower()
    for match in re.finditer(r'\b(?:add|write|create)\s+(?:[\w-]+\s+){0,5}tests\b',goal):
        if re.search(r"\b(?:do not|don't|dont|never|avoid|no need to|without)\s*$",goal[max(0,match.start()-25):match.start()]):continue
        if re.match(r'\s+(?:(?:only )?if needed|(?:only )?if necessary|where needed|unless)\b',goal[match.end():]):continue
        return 'rust' if 'rust' in match.group() else 'any'
    return None


def snapshot(cwd):
    root=Path(cwd).resolve();sources={};complete=True;seen=0
    ignored={'.git','.venv','venv','__pycache__','node_modules','target','cache','build','models','vendor'}
    def onerror(error):
        nonlocal complete
        complete=False
    for directory,dirs,files in os.walk(root,onerror=onerror,followlinks=False):
        dirs[:]=[name for name in dirs if name not in ignored and not (Path(directory)/name).is_symlink()]
        for name in files:
            seen+=1
            if seen>2000:return {'complete':False,'sources':sources}
            path=Path(directory)/name
            if path.suffix not in ('.py','.rs') or path.is_symlink():continue
            try:
                if path.stat().st_size>250000:complete=False;continue
                text=path.read_text();relative=path.relative_to(root).as_posix()
                if path.suffix=='.py':
                    if not (path.stem.lower().startswith('test') or path.stem.lower().endswith(('_test','_tests')) or any(part in ('test','tests') for part in path.relative_to(root).parts[:-1])):continue
                    nodes=[node for node in ast.walk(ast.parse(text)) if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name.startswith('test')]
                    bodies=[ast.dump(node,include_attributes=False) for node in nodes];language='python'
                else:
                    text=re.sub(r'//[^\n]*|/\*.*?\*/','',text,flags=re.S);bodies=[];language='rust'
                    for match in re.finditer(r'#\[\s*test\s*\]\s*(?:#\[[^\]]+\]\s*)*(?:pub\s+)?(?:async\s+)?fn\s+\w+[^\{]*\{',text):
                        depth=1;quote=None;escape=False;end=match.end()
                        while end<len(text) and depth:
                            char=text[end];end+=1
                            if quote:
                                if escape:escape=False
                                elif char=='\\':escape=True
                                elif char==quote:quote=None
                            elif char in ('"',"'"):quote=char
                            elif char=='{':depth+=1
                            elif char=='}':depth-=1
                        if not depth:bodies.append(text[match.start():end])
                if bodies:sources[relative]={'language':language,'sha256':hashlib.sha256('\n'.join(sorted(bodies)).encode()).hexdigest()}
            except (OSError,UnicodeError,SyntaxError):complete=False
    return {'complete':complete,'sources':sources}


def added_paths(contract,state):
    language=required_language(contract,state);baseline=state.get('baseline_test_sources')
    if not language or not baseline or not baseline.get('complete'):return None
    current=snapshot(state['cwd'])
    if not current['complete']:return None
    return [str(Path(state['cwd'])/name) for name,value in current['sources'].items()
            if (language=='any' or value['language']==language) and baseline['sources'].get(name)!=value]


def issue(contract,state):
    paths=added_paths(contract,state)
    if paths==[]:
        language=required_language(contract,state)
        return 'The goal explicitly asks for added '+('Rust unit ' if language=='rust' else '')+'tests. Add relevant test definitions beyond the initial supplied tests, then run them before completion.'
    return None
