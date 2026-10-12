# SPDX-License-Identifier: Apache-2.0
"""Honor explicit user requests to leave literal files unchanged."""
from pathlib import Path
import re

_FILE = r"""(`[^`\n]+`|"[^"\n]+"|'[^'\n]+'|[^\s,;]+)"""
_RULE = re.compile(r'\b(?:keep|leave)\s+(?:(?:the|supplied|existing)\s+)*'+_FILE+r'\s+(?:unchanged|untouched)\b',re.I)


def issue(goal,cwd,name,args):
    if name not in ('write_file','apply_patch'):return None
    targets=[args.get('path')] if name=='write_file' else re.findall(r'^\*\*\* (?:Update|Add|Delete) File: (.+)$',str(args.get('patch','')),re.M)
    folder=Path(cwd).resolve()
    for match in _RULE.finditer(goal):
        raw=match.group(1).strip('`\"\'')
        protected=Path(raw).expanduser()
        protected=(protected if protected.is_absolute() else folder/protected).resolve()
        # Only literal file/directory names; broad prose is not a path policy.
        if not protected.exists() and not protected.suffix and not raw.endswith('/'):continue
        for target in targets:
            if not isinstance(target,str):continue
            path=Path(target.strip()).expanduser()
            path=(path if path.is_absolute() else folder/path).resolve()
            if path==protected or protected.is_dir() and path.is_relative_to(protected):
                return 'The user asked to keep '+raw+' unchanged. Put new work in a different file; do not edit this preserved path.'
    return None
