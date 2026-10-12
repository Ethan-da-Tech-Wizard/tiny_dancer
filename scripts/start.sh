#!/usr/bin/env bash
set -euo pipefail
source /mnt/GameDrive/tiny_dancer/scripts/env.sh
cd "$TINY_DANCER_ROOT"
export LD_LIBRARY_PATH="$TINY_DANCER_ROOT/vendor/picchio${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec .venv/bin/python -m uvicorn app.server:app --host 127.0.0.1 --port 3210 --no-access-log
