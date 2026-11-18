# ==============================================================================
# Program: benchmark_model_storage.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 18, 2026
# Purpose: Benchmark, evaluation, verification, or audit script supporting the Tiny Dancer testing framework.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
"""Compare original/cache/original storage with the existing fixed native receipt probe."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.benchmark_prompt_batches import main

if __name__ == '__main__':
    raise SystemExit(0 if main(storage=True) else 1)
