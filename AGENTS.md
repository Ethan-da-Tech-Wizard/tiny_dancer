# Tiny Dancer continuity

Read README.md, docs/STATE.json, and docs/SESSION_LOG.md before continuing.
Canonical root: /mnt/GameDrive/tiny_dancer. Keep project sources, models, caches, logs, and history on the GameDrive. /home/ethan/pg/tiny_dancer is a compatibility symlink.
Owner-approved exception (2026-10-12 UTC, "FULL SEND"): an additional identical, SHA-256-verified native model cache may live on the internal SSD. Retain the complete original model/project on GameDrive; make cache location configurable and fall back to the original when the cache is unavailable. Do not infer authorization to delete unrelated files.
User requested GPT-OSS-20B plus Colibri, no Ollama, local hosting, a functional computer agent, and durable documentation at every step. Never substitute another model silently.
Record commands, findings, failures, tests, and next actions in docs/SESSION_LOG.md and keep docs/STATE.json accurate after meaningful transitions. Never record secrets or raw environment dumps. Read upstream licenses and build docs before execution.
Never restart the service while a task is running. Use .venv/bin/python scripts/restart_when_idle.py (refuses when busy), or add --wait-seconds 3600 to wait for idle. Do not chain a failed guard and a restart as separate shell commands.
Do not touch unrelated services or data. The agent runs with Ethan's normal OS permissions. Authentication, loopback binding, cancellation, and an audit trail belong in the app.
Original Tiny Dancer code is Apache-2.0; dependencies retain their own terms. Read licenses/README.md, preserve upstream notices, and refresh the inventory with scripts/collect_licenses.py followed by its --check after dependency changes. Do not apply the project license to private runtime data or upstream files.

Owner preference (2026-10-12 UTC): keep all existing apps and browser windows open. Qualify changes under that ordinary workload; do not close unrelated processes to make benchmarks faster.
