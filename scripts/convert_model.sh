#!/usr/bin/env bash
set -euo pipefail
source /mnt/GameDrive/tiny_dancer/scripts/env.sh
cd "$TINY_DANCER_ROOT"
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export MKL_NUM_THREADS=2
.venv/bin/python scripts/checkpoint.py model-conversion 'Converting MXFP4 experts to Picchio INT4 gs64, with INT8 dense attention/head/embedding, using bounded-memory chunks. Originals remain untouched. Complete output shards are reused on resume; atomic writes and exact tensor coverage guard against partial installation. See logs/model-convert.log.'
.venv/bin/python scripts/convert_low_memory.py
.venv/bin/python scripts/checkpoint.py model-installed 'Model conversion and binary vocabulary export completed. Next: test real generation, native tool calls and optional CUDA, then enable the tested configuration. Do not assume inference or agent behavior is verified yet.'
