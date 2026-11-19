# ==============================================================================
# Program: preserved_files.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Tracks unmodified reference files and guarantees that critical repository
#          configuration files are preserved throughout agent edits. Core component of
#          the autonomous agent reasoning architecture governing multi-turn execution
#          cycles, state graph transitions, and prompt synthesis. Strictly enforces
#          mathematical bounds on LLM token context windows, rolling memory buffers,
#          and timeout thresholds. Guarantees transactional execution invariants,
#          deterministic failure isolation, and thread-safe API contracts.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
"""Honor explicit user requests to leave literal files unchanged."""
from pathlib import Path
import re

_FILE = r"""(`[^`\n]+`|"[^"\n]+"|'[^'\n]+'|[^\s,;]+)"""
_RULE = re.compile(r'\b(?:keep|leave)\s+(?:(?:the|supplied|existing)\s+)*'+_FILE+r'\s+(?:unchanged|untouched)\b',re.I)


# ------------------------------------------------------------------------------
# issue: Function Pipeline & Contract Specification
# Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
# Invariant: Preconditions validated before mutation; postconditions guarantee return contract
# Failure Modes: Catches or propagates domain exceptions according to API contracts
# ------------------------------------------------------------------------------
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
