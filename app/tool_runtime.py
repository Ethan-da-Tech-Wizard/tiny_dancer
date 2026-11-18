# Program: tiny_dancer - tool_runtime.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Project-owned command wrappers; preserve the ordinary Python and host PATH.
# SPDX-License-Identifier: Apache-2.0
"""Project-owned command wrappers; preserve the ordinary Python and host PATH."""
# ---- Imports ----
import os
from pathlib import Path

ROOT=Path('/mnt/GameDrive/tiny_dancer')


# ---- Definitions ----
def tool_environment():
    """Step: tool environment."""
    env=os.environ.copy()
    temporary=ROOT/'run/tool-tmp'
    cargo_cache=ROOT/'cache/cargo'
    for directory in (temporary,cargo_cache):directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    env['TMPDIR']=str(temporary)
    env['CARGO_HOME']=str(cargo_cache)
    folder=ROOT/'run/tool-bin'
    if (folder/'pytest').is_file():
        env['PATH']=str(folder)+os.pathsep+env.get('PATH','')
    return env
