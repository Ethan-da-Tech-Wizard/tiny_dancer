# SPDX-License-Identifier: Apache-2.0
"""Verify an explicitly requested Rust standard-library constraint from Cargo."""
from pathlib import Path
import re
import tomllib


def constrained_manifest(contract,state):
    if contract.get('kind')!='work' or 'rust' not in contract.get('lookup_languages',[]): return None
    goal=state.get('goal','').lower()
    if not re.search(r'\bstandard[- ]library[- ]only\b|\buse only (?:the )?standard library\b',goal): return None
    if 'not standard-library-only' in goal or 'not standard library only' in goal: return None
    cwd=state.get('cwd')
    return Path(cwd).absolute()/'Cargo.toml' if cwd else None


def dependency_issue(contract,state):
    path=constrained_manifest(contract,state)
    if path is None or not path.exists() and not path.is_symlink(): return None
    try:
        if not path.resolve().is_relative_to(Path(state['cwd']).resolve()):
            return 'The constrained Cargo manifest points outside this project; verify the project manifest.'
        if not path.is_file() or path.stat().st_size>250_000:
            return 'The constrained Cargo manifest cannot be checked within the file limit.'
        manifest=tomllib.loads(path.read_text())
        sections=[manifest]+list(manifest.get('target',{}).values())
        names=set()
        for section in sections:
            for key in ('dependencies','dev-dependencies','build-dependencies'):
                declared=section.get(key,{})
                if not isinstance(declared,dict): return 'Cargo dependency declarations are malformed.'
                names.update(declared)
        if names:
            return 'The goal requires the Rust standard library only, but Cargo.toml declares dependencies: '+', '.join(sorted(names))[:500]+'.'
    except (OSError,ValueError,TypeError,AttributeError):
        return 'The constrained Cargo manifest could not be read or parsed; verify it before completion.'
    return None
