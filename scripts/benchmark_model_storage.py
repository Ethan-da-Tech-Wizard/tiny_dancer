# SPDX-License-Identifier: Apache-2.0
"""Compare original/cache/original storage with the existing fixed native receipt probe."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.benchmark_prompt_batches import main

if __name__ == '__main__':
    raise SystemExit(0 if main(storage=True) else 1)
