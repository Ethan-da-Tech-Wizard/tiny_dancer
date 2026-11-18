# Program: tiny_dancer - checkpoint.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Records a setup phase and message into the project state file and appends them to the session log.
"""Use after meaningful setup transitions: checkpoint.py PHASE MESSAGE."""
# ---- Imports ----
import json, sys
from pathlib import Path
from datetime import datetime, timezone
root = Path('/mnt/GameDrive/tiny_dancer')
now = datetime.now(timezone.utc).isoformat()
state_path = root / 'docs/STATE.json'
state = json.loads(state_path.read_text())
state.update(updated_at=now, phase=sys.argv[1], last_update=sys.argv[2])
state_path.write_text(json.dumps(state, indent=2) + '\n')
with (root / 'docs/SESSION_LOG.md').open('a') as f:
    f.write(f'\n## {now} — {sys.argv[1]}\n{sys.argv[2]}\n')
