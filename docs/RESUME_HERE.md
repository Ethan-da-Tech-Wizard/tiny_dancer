# Resume here

**Session handoff: the owner is going to bed and requested documentation plus a GitHub push.** The latest small coding test passed; the larger inventory task still has a known failure. At the 2026-10-12 07:53 UTC handoff check, the service responded, no API or durable job was running, no inference process existed, and the model was unloaded. No new native experiment was started for the handoff. Check live state again next session.

The owner explicitly requested `Ethan-da-Tech-Wizard/tiny_dancer` and approved the additional identical SSD model cache. Keep all existing apps and browser windows open. Do not close unrelated apps, delete unrelated files, silently substitute a model or reduce precision, or ask again for authorizations already recorded.

Read [STATE.json](STATE.json) and the end of [SESSION_LOG.md](SESSION_LOG.md) first. Check API, durable jobs and owned inference processes before launching anything. Never run two models or restart during an active task. Use the guarded restart script. Never print credentials, native private reasoning, unaccepted drafts or full process arguments.

## Current deployment

All **617 full harness regressions passed** in 51.576 seconds: [per-test report](validation/runs/20261012T054640463797Z.json). These tests do not run the actual model. Confined absolute-path patch support is deployed after an idle check. Runtime SHA-256 is `391b59aeebf13b0bd5b8f1b42d664d65f2745b601f42affefe53a64f760b2545`.

The model remains original GPT-OSS-20B MXFP4, context 32768, f16 KV, 8 threads, 16 CPU expert layers, recommended sampler, native batch/microbatch 512. The verified SSD cache preserves the original on GameDrive. All user apps stay open; no compressed-swap change has been made.

## Current tasks

- Fresh labels **PASS: 563.32 seconds, 4 turns, 10 project tests, all 8 independent groups / 152 Unicode inputs**. [Report](native-labels-20261012T055302670443Z.json), log `logs/github-patch-path-labels.log`. Job `5f0a8b9fa2fa4a958aa5cacacb343022` is complete; observer session 26863 exited successfully. Original acceptance and runtime stayed frozen. No live hints or implementation edits; all existing user apps stayed open.
- Private repository https://github.com/Ethan-da-Tech-Wizard/tiny_dancer is published. Before this handoff update, commit `ab8fedaa77fca36e4474211189b4b49697fa8932` and its GitHub Actions checks were verified. The final handoff commit/push receipt is saved locally in `run/github-publish-last.json`; inspect the publishing checkout's HEAD for the latest commit. Source/evidence publishing checkout: `run/github/tiny_dancer`. [Repeatable export and push instructions](GITHUB.md). The complete raw local reports remain unchanged; GitHub receives public evidence views. Never blindly add runtime folders. All 13 publication controls pass separately from the 617 last full harness checks; a combined 630-test full run has not been claimed. Publication and GitHub CI are separate from native qualification.

## Actual outcomes and remaining failures

- Template fidelity repair passes the exact native formatter probe and two real model instruction receipts. Later developer instructions now reach inference.
- Earlier fresh labels on the repaired template: **PASS, 143.36 seconds**, 10 project tests and all 8 independent groups / 152 Unicode inputs. [Report](native-labels-20261012T041238448162Z.json).
- Fresh inventory: **FAIL, 476.19 seconds**, 9 project tests but only 7/8 independent checks. Unreadable directories were omitted and an old output overwritten. [Report](native-inventory-20261012T041546625894Z.json). Address the requirement gap before advancing.
- Later labels trial was **cancelled after 1263.46 seconds** at a real harness interoperability failure: an absolute patch path inside its task folder was rejected. The general path fix passes 49 focused controls, exact public payload replay, and the 617 full regressions. No model-authored implementation was repaired by the operator. [Cancelled trial](native-labels-20261012T052428411538Z.json).
- Original/cache/original storage test: the same 815 prompt tokens took **69.02 / 29.86 / 73.34 seconds**; all tool receipts correct. [Report](model-storage-probe-20261012T051254328467Z.json). This establishes that prompt comparison, not general whole-task speed. Heavy weight paging was observed with lower available RAM during the later coding trial; there was no controlled whole-task comparison proving its entire cause. [Observation](ssd-coding-memory-observation.json).
- First local-model diagnostic was cancelled for paging without a proposal. A new isolated workspace is ready at `workspace/agent-feedback-20261012T045341331895Z`, not launched. Its brief delivery is tested. After coding terminates, independently calibrate any proposed tests against the observed failure, candidate and a known conforming control. [Workflow](AGENT_FEEDBACK.md).

Full native qualification remains false. Rust, exact-money, larger applications and long research are not qualified on this runtime. Keep historical failures visible. The local release checker is separate from regression counts and from GitHub CI.

## First actions next session

1. Read this file, [STATE.json](STATE.json), and the latest [SESSION_LOG.md](SESSION_LOG.md) entries. Verify the API, durable running jobs and owned inference processes before launching a model. Isolated benchmark servers do not appear in the app's `active_job`. The working installation is `/mnt/GameDrive/tiny_dancer`; `/home/ethan/pg/tiny_dancer` is its compatibility symlink. The Git checkout under `run/github/` is a publication copy, not the running application.
2. Use the already prepared diagnostic workspace. Its original template and evidence report hashes were checked at handoff; no `feedback.json` exists. The historical template bug is already fixed in production: this trial measures whether the local model can independently contribute a valid diagnosis and reproduction test. Do not give it the fixed template or the maintainer's solution during execution. When idle, launch:

   ```bash
   cd /mnt/GameDrive/tiny_dancer
   .venv/bin/python scripts/run_agent_feedback.py \
     workspace/agent-feedback-20261012T045341331895Z
   ```

   Save the job/report printed by the observer in STATE.json. Observe public progress, file/test receipts and numeric CPU/I/O/token activity. There is no aggregate task deadline. Do not edit production or immutable review inputs while it runs. Its observer checks only workflow completion and unchanged evidence; that alone cannot approve a correction.
3. After termination, inspect its proposed source and tests before executing them. Apply [feedback-calibration-criteria.json](feedback-calibration-criteria.json): the identical tests must fail the original for the observed behavior, pass the candidate, and pass the separately known conforming control. Require nonempty tests, no skips, chronological instruction preservation and unchanged supported formatting. A setup error or a test that asserts a false requirement is a failure. Record missing evidence as incomplete; do not manufacture a pass or deploy automatically.
4. Return to the real capability gap: fresh inventory silently skips an unreadable directory and overwrites an existing output. Review the failed generated project in `workspace/native-inventory-20261012T041546625894Z` and its public tool/test evidence. `os.walk` error handling is the known issue. Existing seeded repair succeeds, but fresh requirement coverage does not. Establish a reproduction, research the relevant official API behavior, make a general harness correction supported by evidence, and run focused regressions before another fresh trial. Do not repair the generated implementation for the model, weaken acceptance, or just repeat the unchanged failed run. After a validated change and idle deployment, use:

   ```bash
   .venv/bin/python scripts/evaluate_hardening_suite.py inventory --effort medium --until-terminal
   ```

5. Keep all eight inventory checks, including special files, output replacement and directory-error preservation. Only after the smaller cases pass should current-runtime Rust and exact-money qualification advance. Larger web/desktop apps, long research and multi-part tasks remain later stages in [CAPABILITY_LADDER.md](CAPABILITY_LADDER.md). Run `scripts/check_native_release.py` on complete local evidence; nonzero is currently expected.

## Performance work and boundaries

The SSD cache and native prompt batch 512 have measured, limited wins. The latest successful small task still took 9 minutes 23 seconds under the owner's ordinary app load. Do not call that a general speedup or close apps to make the benchmark look better. Log available RAM, model residency, physical reads, CPU/GPU activity, prompt/decode time and actual useful progress while preserving model/context/precision. Different generated output lengths invalidate simple total-time speed ratios.

Compressed memory (zram/zswap) is research only; nothing has been installed or configured. [OPEN_SOURCE_RESEARCH.md](OPEN_SOURCE_RESEARCH.md) preserves primary references. Deleting GameDrive files does not free RAM, and the drive already had ample space. Keep model, precision and context fixed for meaningful speed comparisons. Diagnose memory pressure before changing the guards; document the measured effect of any later configuration change. Stop/Resume and context recovery remain important after earlier desktop freezes.

Useful code entry points: `app/agent.py` (loop and completion), `app/native_chat.py` and `app/templates/` (native instruction/tool protocol), `app/patches.py` (confined patch paths), `app/llama_session.py` and `app/model_cache.py` (inference and cache), `scripts/inventory_goal_audit.py` and `scripts/inventory_extended_audit.py` (independent criteria). Preserve original licenses and the local Picchio patch. No new package was added for publication; the two GitHub-only actions have pinned commits and MIT notices in `licenses/github-actions/`.

## Finish each work session

Record the concrete change, command, outcome, scope, failure diagnosis and next action in SESSION_LOG.md; update STATE.json and this handoff. Keep old failed/cancelled reports intact. Use `scripts/run_regressions.py` for required harness checks and `scripts/refresh_test_results.py` for the readable historical index. Avoid repeating expensive tests without a new change or unresolved concern.

Follow [GITHUB.md](GITHUB.md) to export, review, commit and push. Check the remote head and CI, then save the final receipt to `run/github-publish-last.json`. Never push raw chat/checkpoint data, model weights, browser profiles or credentials. Exported report summaries are deliberately incomplete for native release qualification; the complete original evidence stays on GameDrive.

Open http://127.0.0.1:3210 or the [results page](http://127.0.0.1:3210/results). Continuous Agent work has no aggregate deadline; Stop, Resume, context recovery and memory/activity/repetition guards remain.
