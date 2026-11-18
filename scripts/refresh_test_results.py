# Program: tiny_dancer - refresh_test_results.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Rebuilds the index of saved test and evaluation results by calling the app results refresher.
# SPDX-License-Identifier: Apache-2.0
# ---- Imports ----
"""Rebuilds the index of saved test and evaluation results by calling the app results refresher."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.validation_results import refresh_results

# ---- Script entry point ----
if __name__=='__main__':
    result=refresh_results(ROOT)
    print(f"Indexed {len(result['results'])} saved test/evaluation results.")
