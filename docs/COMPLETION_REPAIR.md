# Completion repair experiment

The purpose is to help GPT-OSS complete checked work. The dated entries below preserve earlier experiments; current changes and qualification are recorded at the end and in STATE.json.

Two changes are being evaluated:

- Failed unittest, pytest and Rust checks retain bounded excerpts containing failing test identities, subtest parameters, exception/assertion details and source locations. These are extracted from actual output before the baseline preview is shortened. They also survive context recovery. Full outputs remain in their saved artifacts; omitted details are explicitly marked.
- After changed source fails an executed project suite, the next repair starts from the original goal, current source and actual failure evidence. The preceding attempt stays in durable history but is left out of that next model context. This applies to automatic checks and an explicit check in the same edit batch. Unchanged reads do not repeat the tests or reset the context. Passing checks retain the usual completion path.

These excerpts do not diagnose the bug or approve the model's work. The harness supplies no arithmetic implementation. The model still has to diagnose, edit and run real tests. Existing completion guards and independently withheld checks remain unchanged.

## Evidence

Before implementation, the new reproductions failed: one assertion failure and six missing-feature errors. See [the initial log](../logs/completion-feedback-before.log). The initial run also included inherited existing tests; those duplicates were removed from the final suite.

The final [focused run](../logs/completion-feedback-focused-final.log) passed 29 tests. It includes actual failing unittest and pytest runs, Rust failure excerpts, long assertion diffs, repeated previewing, constrained checkpoint output, original-history retention, two different failed repairs followed by a real successful repair, explicit checks in an edit batch, and a native Harmony prompt with the complete 4096-token action reserve.

The [full production log](../logs/completion-feedback-production-final.log) and its named JSON report record every current regression. [Test results](http://127.0.0.1:3210/results) includes past failures and successes.

## Native acceptance

The original money task must pass on the current runtime with its original goal and unchanged six acceptance tests, plus the same independently withheld ordinary, error and large-input checks. The observation limit is 900 seconds. No live code, solution, algorithm hint or replacement model will be supplied. The [native report](precision-repair-retest-validation.json) records the actual outcome and frozen source fingerprint.

If that task passes, fresh Python inventory and Rust ranges tasks must pass their frozen checks on the same runtime before the three-task release gate can pass. A scripted fixture is not evidence that native task completion improved.

The latest earlier native money attempt removed three seeded errors but still failed signed cancellation. Its remaining output was only 954 characters, so preview loss alone is not an established explanation. Fresh repair contexts are an experiment, not a proven remedy.

The original Apache-2.0 implementation adds no dependency. Aider's [automatic test and repair workflow](https://aider.chat/docs/usage/lint-test.html) supports using actual executed failures as feedback; it does not establish the effectiveness of this local context strategy.

## First native outcome and follow-up

The first completion-focused replay did not qualify: 900.23 seconds, 13 turns, no native completion. All 11 ordinary CLI checks, five clear-error checks and the 1,600-digit check passed; both 3,200-digit checks failed. The public implementation used a fixed precision of 2,000 based on the supplied examples. It added no new test definitions. No live hint or code replacement was supplied.

Public tool evidence reproduced three further harness defects. Passing project checks silently withheld verification when a requested deliverable was missing. Checkpoints omitted those newer passing results while retaining older failures. `/artifacts/name` references returned by tools could not be read through file tools.

The follow-up candidate gives passing checks an explicit incomplete-task receipt with the actual unmet requirement. Checkpoints preserve the latest executed commands, counts, passing status, remaining requirement and whether tracked sources still match that execution. A later edit remains unverified. Existing import-derived library notes are refreshed from bounded current files by parsing, without importing or running project code. They report observed settings and documentation, not a diagnosis or implementation.

Read-only file tools now resolve returned `/artifacts/name` references to saved output. References cannot escape the artifact directory; observations do not become product files in the source-hash proof. Ordinary task paths keep their existing behavior.

The [follow-up initial log](../logs/completion-contract-before.log) reproduces missing features. The first [full staging run](../logs/completion-contract-staging-full.log) failed one legacy assertion expecting silent feedback. That assertion now requires an explicit **false** verification and the missing filename; completion remains blocked until the file exists and checks pass. The native goal and acceptance tests were not changed.

The final staging suite passed 399 tests. [Production results](../logs/completion-contract-production.log) record the deployed suite. The actual task's source/receipt/native Harmony budget probe fit a 3,701-token prompt plus the full 4,096-token action allowance. This is a serialization check, not native generation. [Follow-up evidence](completion-contract-validation.json) separates fixture results from the pending native outcome.

## Finishing and unrestricted input claims

The second replay passed every original frozen independent check, added and ran seven new tests, and still did not produce a native final before its 900-second observation limit. It subsequently rechecked passing work. The public implementation selected a literal precision of 10,000. Separate post-terminal 12,000-digit checks failed: see [the boundary diagnosis](money-precision-boundary-diagnosis.json). These additional results do not rewrite the original frozen report.

The final-context candidate refreshes the model context once per unchanged, actually tested source version with no pending plan step. It asks the native model to review the original goal and any implementation limits it introduced. The model can return its own final, or name an unmet requirement and continue working. It does not publish a host-written answer, change the reasoning effort or token allowance, or use model approval as test evidence. Changed source, failed tests and missing requested outputs still block completion. Full history stays on disk.

The checkpoint's recovery/review instruction now reaches the model; it previously appeared only in the UI event. The existing checkpoint opening remains compatible. A full staging run caught that opening-text compatibility regression, and it was fixed before deployment. [The failing full log](../logs/completion-finish-staging.log) and [final production log](../logs/completion-finish-production.log) preserve both outcomes.

The additional [12,000-digit criteria](native-money-extended-criteria.json) were declared before the next candidate trial. Original goal, six seeded tests and all original independent checks remain unchanged. These new inputs are withheld from the model and run after the observer finishes through `scripts/evaluate_precision_boundary.py`. The release gate requires both actual cases, matching declaration, unchanged source and the same completed native job/runtime. Neither an older native pass nor a top-level report flag can replace that evidence.

The next original replay has a declared 1,800-second observation limit: the previous 900-second limit cut off work after it had repaired and tested the source. That gives the changed harness a bounded chance to finish. It is not a controlled comparison of runtime or causal proof that context review improves the model. Two fresh Python/Rust native tasks on the same runtime are still required before release qualification.

## Parameter audit and context-only candidate

The user requested a check that harness settings do not degrade the model. [The parameter audit](context-parameter-audit-validation.json) identifies the actual native settings rather than dormant Picchio cache controls. The active runtime uses context8192, temperature0, repetition penalty1, medium coding reasoning, batch/ubatch128, 16 CPU expert layers and f16 KV. [OpenAI recommends temperature1/top_p1](https://github.com/openai/gpt-oss#recommended-sampling-parameters); the earlier stochastic trial failed on an older harness, which does not establish sampler causality. [The model supports131072 positions](https://huggingface.co/openai/gpt-oss-20b/raw/main/config.json).

Auto2048 is a starting chunk. Up to three more chunks can continue the same native reply, bounded by8192 generated tokens and remaining context. The current native run filled the remaining4431 tokens after a3760-token prompt without a complete action. Context-full recovery rebuilds the checkpoint but keeps the starting chunk. Increasing context can remove that particular cap; it does not prove the model will complete an arbitrary task.

A context-only32768 candidate is isolated in run/staging/context-capacity. Weights, KV precision, sampler, effort, threads and expert placement stay the same to make this comparison interpretable. Estimated additional f16 KV is576MiB from the published architecture; actual memory receipts are required. Six new long-prompt/cache/continuation tests and five observer receipt tests verify goal retention, full output reserve, unchanged chunk bounds and refusal to accept missing/incorrect native evidence. Focused28 tests passed. The first full stage failed51 times because its temporary directories were missing; after fixing that setup, all424 tests passed in38.730 seconds. Both reports are retained in the results history.

After the current frozen observer and its independent grading finish, use the idle restart guard before applying the candidate. The real native capacity smoke has a declared180-second limit and requires a correct model final, an actual prompt over8192 tokens, matching frozen runtime and desktop reserves of1.5GiB RAM/1500MiB VRAM. It is a retrieval/capacity check, not coding qualification. Then replay the original coding goal and frozen independent cases. The active run also observed51.28GiB physical model reads and a disk-waiting worker; this is separate from the context capacity diagnosis.

## Continuous observation —2026-10-11

The user removed aggregate deadlines for longer tasks. Agent until-done already has no overall time/turn limit; the evaluation observers were imposing900/1800-second cutoffs. Those outcomes are censored completion observations, with independently failing or passing checks on the saved files at the cutoff. They do not prove eventual model incapacity.

The current Auto native reply continues in chunks to EOS or the actual remaining32768-token context, retaining its exact prefix, cancellation, complete-action requirement and context recovery. Removed the arbitrary8192-output/four-chunk ceiling. Explicit numeric reply budgets and Chat retain their requested caps. Recommended native sampling is temperature1/top_p1, top_k0/min_p0/repetition1; actual scalar receipts record each model request. Weights, KV precision, threads and expert placement are unchanged.

Both native observers accept `--until-terminal`. They sample every20seconds, distinguishing actual edited-source hashes, completed plan steps and test receipts from token/CPU/I/O/command activity. Repeated identical checks do not count as better test evidence. Long generation without a new file is visible rather than automatically killed by elapsed time. Existing no-activity watchdog, unchanged-action cycles, malformed/incomplete-step, tool-failure, memory and Stop controls remain. Source observation covers up to256 reported edited files of1MiB each; it is a diagnostic, not a complete proof of arbitrary project progress.

New continuation controls first reproduced5failures/3errors in19tests. Focused48 passed; revised staged449 passed30.258s and production449 passed30.135s. [Production report](validation/runs/20261011T204558105495Z.json). Backup `run/backups/continuous-native-20261011T204554Z`, runtime90c14ea967a2f3c827b1598e2023bda1f48337ad9e08ff3829195592d93c327d. No dependencies added. Native quality remains unqualified pending actual tests. Start with protocol/context/memory receipts, then labels function plus model-written tests, inventory Python CLI, Rust CLI, local browser app, standalone desktop app, sourced saved research, and multi-part stop/resume. Do not skip an earlier failing native level.
