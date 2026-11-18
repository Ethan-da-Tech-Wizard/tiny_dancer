# Program: tiny_dancer - benchmark_model_storage.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Compare original/cache/original storage with the existing fixed native receipt probe.
# SPDX-License-Identifier: Apache-2.0
"""Compare original/cache/original storage with the existing fixed native receipt probe."""
# ---- Imports ----
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.benchmark_prompt_batches import main

# ---- Script entry point ----
if __name__ == '__main__':
    raise SystemExit(0 if main(storage=True) else 1)
