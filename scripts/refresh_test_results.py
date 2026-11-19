# ==============================================================================
# Program: refresh_test_results.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Benchmark, evaluation, verification, or audit script supporting the Tiny
#          Dancer testing framework. Operational automation, benchmark evaluation, and
#          system diagnostic harness. Executes high-throughput workload profiling
#          across CPU/GPU execution tiers with strict resource bounds. Enforces
#          reproducible benchmark metrics, mathematical latency bounds, and
#          deterministic subprocess exit contracts.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.validation_results import refresh_results

if __name__=='__main__':
    result=refresh_results(ROOT)
    print(f"Indexed {len(result['results'])} saved test/evaluation results.")
