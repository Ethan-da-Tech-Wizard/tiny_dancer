#!/usr/bin/env bash
# ==============================================================================
# Program: env.sh
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 18, 2026
# Purpose: Shell script automating environment setup, model conversion, test runs, or daemon service execution.
# ==============================================================================

export TINY_DANCER_ROOT=/mnt/GameDrive/tiny_dancer
export HF_HOME="$TINY_DANCER_ROOT/cache/huggingface"
export HF_HUB_CACHE="$HF_HOME/hub"
export HF_HUB_DISABLE_TELEMETRY=1
export TIKTOKEN_CACHE_DIR="$TINY_DANCER_ROOT/cache/tiktoken"
export UV_CACHE_DIR="$TINY_DANCER_ROOT/cache/uv"
export PLAYWRIGHT_BROWSERS_PATH="$TINY_DANCER_ROOT/cache/playwright"
export PYTHONUNBUFFERED=1
export TOKENIZERS_PARALLELISM=false
