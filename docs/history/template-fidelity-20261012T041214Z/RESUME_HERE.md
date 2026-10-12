# Resume here

Current runtime `960e43ef3ae74455757650649e6bc973251b1247a69698eb21b442fcb838cd87`. **573 harness/comparison controls pass**, plus the actual results-page browser check. All saved categories are visible, terminal failed submissions show FAILED, and durations are displayed. Inference/model policy is unchanged from49db07; the later change affects result reporting.

**Native evidence:** normal-app Auto/high labels passed11projecttests and all8independentgroups/152Unicodeinputs in182.55s. Fresh Auto/high inventory failed1077.26s (6/7independentchecks): unreadable directories were silently skipped. Both generated-test probes and generic fresh-context review failed and were rejected. Pi1.1.0 medium comparison also failed its small task137.49s:11tests passed, but wrong self-authored Unicode assertions caused implementation regressions (5/8independentgroups). Pi is isolated and not adopted; no larger Pi task attempted.

**A real recovery passed:** [known-failure inventory repair](native-regression-repair-inventory-20261012T033014199471Z.json),141.72s,10projecttests and8independentchecks. At task start the model received the earlier failed project plus two calibrated public regression tests. It repaired the code itself, preserved supplied tests and also passed a withheld pipe/socket check. No live hints or operator edits. This is seeded repair, not fresh implementation qualification.

**Active direction:** fresh normal-app medium labels PASSED131.48s,12projecttests and all152Unicodeexamples on the current runtime. Fresh medium inventory is now running with original goal/6acceptance/inputs only and all8predeclaredchecks; check STATE.json. No aggregate deadline. Original API/acceptance/runtime fingerprints remain frozen throughout each run. Full native qualification remains false.

## Start and inspect

Open http://127.0.0.1:3210 or the Tiny Dancer desktop launcher. Results: http://127.0.0.1:3210/results. Use Agent / Auto / Auto budget with Keep working until done checked. Auto work now uses high reasoning; Chat/questions use low. Quick=low, Balanced=medium, Thorough=high. Stop and Resume remain available; the task folder opens in Code OSS.

Read AGENTS.md and current STATE.json. Canonical root: `/mnt/GameDrive/tiny_dancer`. Keep all sources, caches, history, reports and backups there. Never restart during a task; use `.venv/bin/python scripts/restart_when_idle.py` after an idle check. Never import app.server in diagnostics. Do not print credentials, process arguments, native private reasoning or unaccepted drafts.

## Current setup

Original GPT-OSS-20B MXFP4, local pinned llama.cpp, native chat tool grammar for Agent. Picchio and Colibri remain installed. No Ollama or hosted model. 32768 context, f16 KV,8 CPU threads,16 CPU expert layers,8 GPU expert layers plus GPU attention/dense,128 batch and microbatch. Recommended sampler1/1/0/0/1. Startup free RAM4.5 GiB; runtime1.5 GiB sustained for 6 seconds. These are thresholds, not preallocated RAM. Continuous Agent and native observers have no aggregate deadline. Tool timeouts, Stop, real inactivity/repetition safeguards and physical context recovery remain.

Recent changes: native tool grammar; Auto high for work; test-file provenance to distinguish supplied versus newly added/changed assertions; accurate “Checks passed” UI wording; automatic baseline/post-edit observations supported in chat history. New Tiny Dancer modules are original Apache-2.0. Pi1.1.0 and121npm dependencies are isolated comparison software; exact licenses/notices/lock are in licenses/pi/. No hosted model/provider is configured.

Backups: `run/backups/completion-quality-20261012T015328Z` and `run/backups/native-chat-observations-20261012T020606Z`.

## Next tests, in order

1. Completed current small prerequisite; reproduce later if runtime changes with `.venv/bin/python scripts/evaluate_hardening_suite.py labels --effort auto --until-terminal`. Actual model must create the function, add tests, pass supplied tests and all 8 independent groups including 152 Unicode examples. Runtime and acceptance must remain unchanged; no live hints/product edits.
2. Fresh inventory failed; diagnose and test the new candidate before another `inventory` trial. Require all 7 independent checks, including actual unreadable-directory failure and preservation of existing output. Prior minimal grammar inventory failed this semantic case; grammar alone is not a quality fix.
3. If a case fails: inspect public source/tools/results, retain the report, research the cause, stage a specific change and test it before another run. Do not repeat the same failure unchanged or weaken acceptance.
4. Then fresh Rust `ranges`, original seeded exact-money repair and declared12,000-digit boundary on the same runtime. Larger web/desktop/research/multi-part tasks remain unqualified.

## Evidence to retain

- [Former small-task narrow pass](native-labels-20261012T010612854536Z.json) failed a later [Unicode goal audit](labels-additional-goal-audit-validation.json): the model replaced correct lowercasing to satisfy its own wrong test. Original report preserved with its original scope.
- Minimal raw loop: [labels pass](minimal-labels-20261012T012305377817Z.json), [inventory fail](minimal-inventory-20261012T012524949205Z.json),10 malformed calls; no added tests or report. Not adopted.
- Minimal grammar loop: [labels pass](minimal-labels-20261012T013804229285Z.json), [inventory fail](minimal-inventory-20261012T014030513755Z.json),0 malformed calls,7 project tests and saved report,6/7 independent cases. No claim of a controlled speedup.
- [Normal-app integration failure](native-labels-20261012T015812683517Z.json): adapter rejected initial observations before native work. Saved history now converts; real initial/post-edit paths covered by tests.
- 548 production controls passed before this integration fix; current 553 controls pass in 42.589 seconds. Failed setup suites and the fixture-isolation error remain archived.

[Current capabilities](CAPABILITY_LADDER.md), [qualification requirements](NATIVE_QUALIFICATION.md), [research](OPEN_SOURCE_RESEARCH.md), [all results](TEST_RESULTS.md), [work log](SESSION_LOG.md). Earlier contradictory current-status prose is preserved under `docs/history/completion-quality-20261012T020546Z`; use current STATE.json and this handoff.
