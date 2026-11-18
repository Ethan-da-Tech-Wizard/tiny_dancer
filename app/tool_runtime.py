# ==============================================================================
# Program: tool_runtime.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 18, 2026
# Purpose: Validates, deserializes, and safely dispatches tool invocations and structured JSON arguments from agent response messages to target tool handlers.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
"""Project-owned command wrappers; preserve the ordinary Python and host PATH."""
import os
from pathlib import Path

ROOT=Path('/mnt/GameDrive/tiny_dancer')


def tool_environment():
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
