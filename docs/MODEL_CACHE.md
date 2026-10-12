# Optional faster local model storage

Tiny Dancer can read the same GPT-OSS-20B model from a second local drive. This can reduce disk waiting when the computer cannot keep all required weights in RAM. It does not shrink the model, reduce precision or change its context. Performance still needs native measurement on each machine.

The owner authorized this additional cache on 2026-10-12 UTC. Project files, the original model, conversations, test reports and backups stay on GameDrive. Nothing is deleted to make room. The model file is 12,109,566,624 bytes (11.28 GiB); the copy helper defaults to retaining another 10 GiB free.

## Install and select

Wait until Tiny Dancer and isolated model tests are idle, then run from the project root:

```bash
.venv/bin/python scripts/cache_native_model.py --directory '~/.cache/tiny-dancer/models'
```

The script copies into a private temporary directory, checks the source hash while copying, reads back and hashes the destination, retains the upstream LICENSE/USAGE_POLICY and publishes the complete directory atomically. An ordinary interruption removes only that copy's unfinished directory. A machine crash may leave a hidden `.partial` directory; it is never selected as a model. Existing unexpected or damaged bundles are not silently overwritten.

After successful installation, `config.json` can contain:

```json
"model_cache": {
  "enabled": true,
  "directory": "~/.cache/tiny-dancer/models"
}
```

Restart through `.venv/bin/python scripts/restart_when_idle.py`. The copy script does not change configuration or restart the service. Any explicit absolute path, `~` path, or project-relative directory is supported. If directory is omitted, the default is `$XDG_CACHE_HOME/tiny-dancer/models` or `~/.cache/tiny-dancer/models`. Choose a drive appropriate to the machine; the feature is not tied to a username or disk model.

At first use in each app process the cache is fully hashed. Later model reloads reuse that verification only while device, inode, size, modification time and change time all match. A missing, changed or invalid cache falls back to the original GameDrive model. This is local file-integrity checking, not an OS sandbox or defense against a privileged concurrent attacker. It does not replace the original model's fidelity checks.

`run/model-storage.json` records the actual selected file, reason, SHA-256 and first-use verification time. While idle, `scripts/cache_native_model.py --status` verifies whether the configured candidate can be used; it explicitly tests cache selection even if the enable flag is currently off. Disable `model_cache.enabled` and perform an idle restart to use the original again. Do not remove a cache while a model process is using it.

## Evidence

Installation reports are saved as `docs/model-cache-install-*.json`, with source preservation, free space, destination identity and elapsed time. They appear on [Test results](http://127.0.0.1:3210/results). Automated controls in `tests/test_model_cache.py` cover interrupted copies, source changes, corrupted/missing/replaced files, notices, provenance, free-space refusal, idempotency, portable paths, verification reuse and the actual native adapter's selected model/unchanged inference parameters.

The first native prompt-batch comparison remains separate: 128/512/128 processed the same 815 tokens in 64.982/42.974/68.983 seconds, with all three tool receipts correct and comparable starting temperatures. [Batch evidence](prompt-batch-probe-20261012T045157003763Z.json). This measures prompt processing, not overall coding quality.

The [storage-only native comparison](model-storage-probe-20261012T051254328467Z.json) passed with batch128 held fixed:

| Run | Same prompt processed | Complete probe, including loading | Instruction check |
| --- | --- | --- | --- |
| GameDrive original | 69.020 s | 169.583 s | Passed |
| Internal SSD cache | 29.858 s | 75.795 s | Passed |
| GameDrive repeat | 73.344 s | 147.612 s | Passed |

All runs processed exactly815prefilltokens at the same model SHA-256, precision, context, placement, threads and sampler. Starting GPU temperatures were71/72/72°C and CPU77/76/75°C. No software thermal slowdown was observed. No OS cache was forcibly dropped. The cache run included13.887s of first-use hashing. Generated output lengths differed, so total time is not a comparison of identical decode work. This small prompt was processed about2.3–2.5times faster on the SSD; it is not a universal whole-task speed promise or coding qualification.

Native batch sizes now have separate portable settings: `llama_batch_size` and `llama_microbatch_size`. The legacy default is128; the measured candidate uses512for both. Microbatch must be positive and at most batch, and batch must fit context. `prefill_batch` remains the Picchio setting. The current deployment and actual coding results are recorded in STATE.json; all other model capacity settings are retained.
