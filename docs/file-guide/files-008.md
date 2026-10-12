# Files 8 of 8 — Tiny Dancer

[All pages](../FILE_GUIDE.md) · [Project guide](../PROJECT_GUIDE.md)

| File | Role and useful details |
| --- | --- |
| [scripts/collect_licenses.py](../../scripts/collect_licenses.py) | Archive installed license texts and metadata without network access. Defines `normalized`, `digest`, `archive`, `license_file`, `installed`, `check_lock` and 4 more top-level symbols. |
| [scripts/convert_low_memory.py](../../scripts/convert_low_memory.py) | Resume GPT-OSS conversion with bounded memory and atomic per-tensor output shards. Defines `header`, `mapped`, `floating`, `quant8_chunks`, `save`, `merge_parts` and 1 more top-level symbols. |
| [scripts/convert_model.sh](../../scripts/convert_model.sh) | Command-line automation for convert model; review prerequisites and side effects before executing. |
| [scripts/download_model.py](../../scripts/download_model.py) | Pinned, resumable official weights download. All assets live on GameDrive. Connects `json`, `pathlib`, `huggingface_hub`. |
| [scripts/env.sh](../../scripts/env.sh) | Command-line automation for env; review prerequisites and side effects before executing. |
| [scripts/evaluate_agent_default.py](../../scripts/evaluate_agent_default.py) | Real API default/answer smoke, using public facts and no aggregate cutoff. Defines `main`. |
| [scripts/evaluate_audit_test_probe.py](../../scripts/evaluate_audit_test_probe.py) | Idle-only same-model executable verification probe; no production mutation. Defines `evaluate`. |
| [scripts/evaluate_batching.py](../../scripts/evaluate_batching.py) | Frozen real-model repair comparison or exact user JSON/editor regression. Defines `main`. |
| [scripts/evaluate_context_capacity.py](../../scripts/evaluate_context_capacity.py) | Bounded real-model long-context receipt; no agent completion claim. Defines `make_prompt`, `checks_for`, `main`. |
| [scripts/evaluate_hardening_suite.py](../../scripts/evaluate_hardening_suite.py) | Run one predeclared native coding case; preserve every run independently. Defines `runtime_digest`, `parse_options`, `main`. |
| [scripts/evaluate_inventory_resume.py](../../scripts/evaluate_inventory_resume.py) | Observe a saved native inventory task's Resume; no fresh-coding claim. Defines `main`. |
| [scripts/evaluate_minimal_coding.py](../../scripts/evaluate_minimal_coding.py) | Same-model minimal baseline; original goals, no live hints, held-out grading. Defines `file_hash`, `evaluate`. |
| [scripts/evaluate_native_coding.py](../../scripts/evaluate_native_coding.py) | Frozen native coding task; operator observes, then checks unseen inputs. Defines `independent_checks`, `main`. |
| [scripts/evaluate_pi.py](../../scripts/evaluate_pi.py) | Frozen same-model comparison with upstream Pi; no live hints or product edits. Defines `file_hash`, `evaluate`. |
| [scripts/evaluate_precision_boundary.py](../../scripts/evaluate_precision_boundary.py) | Post-terminal independent boundary checks; never supply model hints or edits. Defines `probe`, `main`. |
| [scripts/evaluate_precision_repair.py](../../scripts/evaluate_precision_repair.py) | Native repair of observed CSV defects; immutable operator-seeded criteria. Defines `main`. |
| [scripts/evaluate_review_repair.py](../../scripts/evaluate_review_repair.py) | Fresh-context repair experiment; never counted as fresh implementation. Defines `main`. |
| [scripts/evaluate_sunday.py](../../scripts/evaluate_sunday.py) | Run the original user question, then independently refetch its score reference. Defines `main`. |
| [scripts/export_github.py](../../scripts/export_github.py) | Build a reviewable GitHub checkout without changing local runtime evidence. Defines `public_report`, `inspect_text`, `result_index`, `export`, `main`. |
| [scripts/fixtures/inventory_reference.py](../../scripts/fixtures/inventory_reference.py) | Operator-written positive TEST CONTROL only; never supplied as model output. Defines `fail_scan`, `inventory`, `main`. |
| [scripts/fixtures/scan_regression_tests.py](../../scripts/fixtures/scan_regression_tests.py) | Known filesystem error regressions supplied before a native repair task. Defines `ScanErrorRegressionTests`. |
| [scripts/inventory_extended_audit.py](../../scripts/inventory_extended_audit.py) | Predeclared extra regular-file requirement: pipes/sockets must not be read. Defines `check_special_files`. |
| [scripts/inventory_goal_audit.py](../../scripts/inventory_goal_audit.py) | Withheld inventory checks added after the original narrow trial passed. Defines `check_inventory_goal`. |
| [scripts/labels_goal_audit.py](../../scripts/labels_goal_audit.py) | Independent Unicode behavior audit; declared after the original labels trial. Defines `cases`, `check_labels_goal`. |
| [scripts/llama_chat_baseline.py](../../scripts/llama_chat_baseline.py) | Experimental adapter to the pinned llama.cpp native GPT-OSS tool grammar. Defines `chat_history`, `ChatStream`, `LlamaChatBaselineEngine`. |
| [scripts/minimal_coding.py](../../scripts/minimal_coding.py) | Experimental coding-loop baseline, not the production agent runner. Defines `message_text`, `run_loop`. |
| [scripts/native_observation.py](../../scripts/native_observation.py) | Observer policy and public progress evidence, separate from model reasoning. Defines `observation_limit`, `limit_reached`, `observation_delay`, `public_action_counts`, `ProgressTracker`. |
| [scripts/native_suite_cases.py](../../scripts/native_suite_cases.py) | Frozen native task criteria; no solution code is supplied to the agent. Defines `grade`. |
| [scripts/node_licenses.py](../../scripts/node_licenses.py) | Offline inventory of the isolated Pi installation and its shipped notices. Defines `digest`, `package_files`, `notice_file`, `collect_node`, `verify_node`. |
| [scripts/observe_existing_coding.py](../../scripts/observe_existing_coding.py) | Continue observing an existing native coding job without changing its task. Defines `main`. |
| [scripts/pi_baseline.py](../../scripts/pi_baseline.py) | Local-only Pi configuration and public event filtering for native comparisons. Defines `child_environment`, `models_config`, `settings_config`, `public_event`. |
| [scripts/prepare_agent_feedback.py](../../scripts/prepare_agent_feedback.py) | Prepare an evidence-only local-model review workspace; never launch or deploy. Defines `public_evidence`, `project_source`, `prepare`, `main`. |
| [scripts/probe_native_template.py](../../scripts/probe_native_template.py) | Exact staged backend/template check, plus two real native instruction receipts. Defines `main`. |
| [scripts/refresh_test_results.py](../../scripts/refresh_test_results.py) | Python implementation of refresh test results. Connects `pathlib`, `sys`, `app.validation_results`. |
| [scripts/restart_when_idle.py](../../scripts/restart_when_idle.py) | Restart only after both the service and its durable job table report idle. Defines `wait_for_ready`, `guarded_restart`, `main`. |
| [scripts/run_agent_feedback.py](../../scripts/run_agent_feedback.py) | Run a prepared diagnostic task through the ordinary local agent, one at a time. Defines `valid_feedback`, `main`. |
| [scripts/run_regressions.py](../../scripts/run_regressions.py) | Run real regressions and preserve named outcomes in a unique results report. Defines `main`. |
| [scripts/rust_toolchain_licenses.py](../../scripts/rust_toolchain_licenses.py) | Offline inventory of the already installed rustup-managed Rust toolchain. Defines `tool_version`, `collect_rust_entries`, `verify_rust_versions`. |
| [scripts/start.sh](../../scripts/start.sh) | Command-line automation for start; review prerequisites and side effects before executing. |
| [scripts/tiny-dancer.service](../../scripts/tiny-dancer.service) | Tracked tiny dancer resource in scripts; 444 bytes. |
| [scripts/tool-bin/pytest](../../scripts/tool-bin/pytest) | Tracked pytest resource in scripts/tool-bin; 228 bytes. |
| [scripts/validate_answer_ui.py](../../scripts/validate_answer_ui.py) | Check the actual completed answer UI without starting model work. Defines `main`. |
| [scripts/validate_batching_ui.py](../../scripts/validate_batching_ui.py) | Read-only live results/workspace validation; never starts model tasks. Defines `main`. |
| [scripts/validate_continuation_ui.py](../../scripts/validate_continuation_ui.py) | Check actual paused UI plus mocked network recovery/Resume without inference. Defines `main`. |
| [scripts/validate_generation_budget_ui.py](../../scripts/validate_generation_budget_ui.py) | Check budget validation and intercepted composer requests without inference. Defines `main`. |
| [scripts/validate_language_tools.py](../../scripts/validate_language_tools.py) | Validate real read-only lookups, without starting or steering model tasks. Defines `main`. |
| [scripts/validate_local_test_runner.py](../../scripts/validate_local_test_runner.py) | Actual project pytest, fixtures, failure and zero-suite checks; no inference. Defines `main`. |
| [scripts/validate_native_harness.py](../../scripts/validate_native_harness.py) | Native patch/cache/medium-effort capability probe with a seeded bug and tests. Defines `main`. |
| [scripts/validate_native_harness_ui.py](../../scripts/validate_native_harness_ui.py) | Inspect the actual completed native repair UI without starting model work. Defines `main`. |
| [scripts/verify_agent.py](../../scripts/verify_agent.py) | Actual local-model E2E: native function calls create and read back a file. Connects `json`, `shlex`, `time`, `pathlib`. |
| [tests/__init__.py](../../tests/__init__.py) | Tiny Dancer behavioral regressions. |
| [tests/raw_engine_fixture.py](../../tests/raw_engine_fixture.py) | Raw Harmony test doubles must select their protocol independently of live config. Defines `legacy_raw_engine`. |
| [tests/test_adaptive_work_allowance.py](../../tests/test_adaptive_work_allowance.py) | Scripted recovery boundaries; no native task or implementation injected. Defines `AdaptiveWorkAllowanceTests`. |
| [tests/test_agent.py](../../tests/test_agent.py) | Automated checks for agent. Defines `call`, `ScriptedEngine`, `AgentLoopTests`, `ContextTests`. |
| [tests/test_agent_feedback.py](../../tests/test_agent_feedback.py) | Automated checks for agent feedback. Defines `AgentFeedbackTests`. |
| [tests/test_artifact_reads.py](../../tests/test_artifact_reads.py) | Returned artifact references can be inspected without becoming product files. Defines `ArtifactReadTests`. |
| [tests/test_audit_test_probe.py](../../tests/test_audit_test_probe.py) | Automated checks for audit test probe. Defines `AuditTestProbeTests`. |
| [tests/test_baseline_preview.py](../../tests/test_baseline_preview.py) | Automated checks for baseline preview. Defines `ProjectionTests`. |
| [tests/test_basic_native_case.py](../../tests/test_basic_native_case.py) | Automated checks for basic native case. Defines `BasicNativeGraderTests`. |
| [tests/test_batching.py](../../tests/test_batching.py) | Automated checks for batching. Defines `BatchToolTests`, `BatchedVerificationTests`. |
| [tests/test_checkpoint_evidence.py](../../tests/test_checkpoint_evidence.py) | Reproduce expensive rolling and lost working evidence without native inference. Defines `CheckpointRolloverTests`, `CheckpointEvidenceTests`. |
| [tests/test_checkpoint_selection.py](../../tests/test_checkpoint_selection.py) | Preserve actual work after test reads; inspect no code outside the project. Defines `CheckpointSelectionTests`. |
| [tests/test_coding_acceptance.py](../../tests/test_coding_acceptance.py) | Automated checks for coding acceptance. Defines `IndependentCodingAcceptanceTests`. |
| [tests/test_coding_preflight.py](../../tests/test_coding_preflight.py) | Automated checks for coding preflight. Defines `PreflightSelectionTests`, `CapturingEngine`, `CodingPreflightTests`. |
| [tests/test_completion.py](../../tests/test_completion.py) | Automated checks for completion. Defines `scoreboard`, `PolicyTests`, `RetrievalTests`, `CompletionTests`, `IdleTests`. |
| [tests/test_completion_guidance.py](../../tests/test_completion_guidance.py) | Automated checks for completion guidance. Defines `CompletionGuidanceTests`. |
| [tests/test_completion_receipt.py](../../tests/test_completion_receipt.py) | Passing tests must report actual remaining work, without relaxing completion. Defines `CompletionReceiptTests`. |
| [tests/test_context_capacity.py](../../tests/test_context_capacity.py) | Long native prompts must retain their goal and complete action allowance. Defines `ContextCapacityTests`. |
| [tests/test_context_capacity_observer.py](../../tests/test_context_capacity_observer.py) | A capacity claim requires real final, token and memory witnesses. Defines `ContextObserverTests`. |
| [tests/test_continuation.py](../../tests/test_continuation.py) | Automated checks for continuation. Defines `ContinuingEngine`, `ContinuationTests`, `MemoryPreflightTests`, `DateTests`. |
| [tests/test_cpu_thread_benchmark.py](../../tests/test_cpu_thread_benchmark.py) | Automated checks for cpu thread benchmark. Defines `CPUThreadBenchmarkTests`. |
| [tests/test_explicit_budget.py](../../tests/test_explicit_budget.py) | Automated checks for explicit budget. Defines `ExplicitBudgetTests`. |
| [tests/test_failure_feedback.py](../../tests/test_failure_feedback.py) | Real failing runners and repair checkpoints, rather than model approval. Defines `FailureFeedbackTests`. |
| [tests/test_final_api_review.py](../../tests/test_final_api_review.py) | Final goal review refreshes advisory API facts without importing projects. Defines `FinalApiReviewTests`. |
| [tests/test_finish_context.py](../../tests/test_finish_context.py) | A factual final review can finish, remain open, or reject stale evidence. Defines `FinishContextTests`. |
| [tests/test_generation_budget.py](../../tests/test_generation_budget.py) | Exercise automatic starting allowances through actual runner/tool paths. Defines `GenerationBudgetTests`. |
| [tests/test_github_export.py](../../tests/test_github_export.py) | Automated checks for github export. Defines `GitHubExportTests`. |
| [tests/test_hardening.py](../../tests/test_hardening.py) | Regression scenarios derived from observed native waste and completion risks. Defines `CapabilityHardeningTests`, `NamedOutputRoutingTests`. |
| [tests/test_harmony.py](../../tests/test_harmony.py) | Automated checks for harmony. Defines `NativeHistoryTests`. |
| [tests/test_harmony_recovery.py](../../tests/test_harmony_recovery.py) | Automated checks for harmony recovery. Defines `format_error`, `call`, `NativeFormatTests`, `RunnerFormatTests`. |
| [tests/test_incomplete_generation_diagnostics.py](../../tests/test_incomplete_generation_diagnostics.py) | Diagnose real reply-limit recovery without leaking or executing text. Defines `IncompleteGenerationDiagnosticsTests`. |
| [tests/test_inspection_source_batch.py](../../tests/test_inspection_source_batch.py) | Batch readable sources without hiding the implementation or losing bounds. Defines `source`, `InspectionSourceBatchTests`. |
| [tests/test_inventory_goal_audit.py](../../tests/test_inventory_goal_audit.py) | Real child processes prove the broader grader detects both observed defects. Defines `InventoryGoalAuditTests`. |
| [tests/test_labels_goal_audit.py](../../tests/test_labels_goal_audit.py) | Automated checks for labels goal audit. Defines `LabelsGoalAuditTests`. |
| [tests/test_language_tools.py](../../tests/test_language_tools.py) | Automated checks for language tools. Defines `RoutingTests`, `LookupTests`, `AgentDiscoveryTests`. |
| [tests/test_llama_backend.py](../../tests/test_llama_backend.py) | Automated checks for llama backend. Defines `BackendSelectionTests`. |
| [tests/test_llama_chat_baseline.py](../../tests/test_llama_chat_baseline.py) | Automated checks for llama chat baseline. Defines `LlamaChatBaselineTests`. |
| [tests/test_llama_session.py](../../tests/test_llama_session.py) | Automated checks for llama session. Defines `frame`, `SessionTests`. |
| [tests/test_maintenance.py](../../tests/test_maintenance.py) | Automated checks for maintenance. Defines `MaintenanceTests`. |
| [tests/test_minimal_coding.py](../../tests/test_minimal_coding.py) | Automated checks for minimal coding. Defines `call`, `MinimalCodingTests`. |
| [tests/test_model_cache.py](../../tests/test_model_cache.py) | Automated checks for model cache. Defines `ModelCacheTests`. |
| [tests/test_native_batch_config.py](../../tests/test_native_batch_config.py) | Automated checks for native batch config. Defines `NativeBatchArgumentsTests`. |
| [tests/test_native_chat.py](../../tests/test_native_chat.py) | Automated checks for native chat. Defines `NativeChatTests`. |
| [tests/test_native_chat_timeout.py](../../tests/test_native_chat_timeout.py) | Real local HTTP delay/cancellation checks without native model inference. Defines `NativeChatTimeoutTests`. |
| [tests/test_native_observation.py](../../tests/test_native_observation.py) | Automated checks for native observation. Defines `ObservationTests`. |
| [tests/test_native_release_gate.py](../../tests/test_native_release_gate.py) | Automated checks for native release gate. Defines `NativeReleaseGateTests`. |
| [tests/test_native_suite_grading.py](../../tests/test_native_suite_grading.py) | Ensure withheld graders reject plausible incomplete or incorrect products. Defines `NativeSuiteGradingTests`. |
| [tests/test_native_template.py](../../tests/test_native_template.py) | Template fidelity uses synthetic text only, never model private reasoning. Defines `render`, `NativeTemplateTests`. |
| [tests/test_node_licenses.py](../../tests/test_node_licenses.py) | Automated checks for node licenses. Defines `NodeLicenseTests`. |
| [tests/test_output_reserve.py](../../tests/test_output_reserve.py) | A requested complete action needs real space after its input prompt. Defines `OutputReserveTests`. |
| [tests/test_patches.py](../../tests/test_patches.py) | Automated checks for patches. Defines `PatchTests`. |
| [tests/test_pending_output_receipts.py](../../tests/test_pending_output_receipts.py) | Automated checks for pending output receipts. Defines `PendingOutputReceiptsTests`, `ReceiptHashTests`. |
| [tests/test_pi_baseline.py](../../tests/test_pi_baseline.py) | Automated checks for pi baseline. Defines `PiBaselineTests`. |
| [tests/test_pi_cli_integration.py](../../tests/test_pi_cli_integration.py) | Actual upstream CLI against a scripted loopback endpoint; not native ability. Defines `PiCLIIntegrationTests`. |
| [tests/test_post_edit_checks.py](../../tests/test_post_edit_checks.py) | Actual execution verifies batching, failed checks, snapshots and cancellation. Defines `PostEditCheckTests`. |
| [tests/test_precision_boundary.py](../../tests/test_precision_boundary.py) | Independent grader controls are CLI fixtures, not native capability evidence. Defines `PrecisionBoundaryTests`. |
| [tests/test_preserved_files.py](../../tests/test_preserved_files.py) | Automated checks for preserved files. Defines `PreservedFileTests`. |
| [tests/test_prompt_batch_probe.py](../../tests/test_prompt_batch_probe.py) | Automated checks for prompt batch probe. Defines `PromptBatchProbeTests`. |
| [tests/test_prompt_cache.py](../../tests/test_prompt_cache.py) | Automated checks for prompt cache. Defines `PromptCacheTests`, `NativeSerializationCacheTests`. |
| [tests/test_prompting.py](../../tests/test_prompting.py) | Automated checks for prompting. Defines `prompt_size`, `PromptTrimTests`, `ToolDiscoveryTests`. |
| [tests/test_pytest_subtests.py](../../tests/test_pytest_subtests.py) | Current pytest subtest summaries must preserve real pass/failure evidence. Defines `PytestSubtestTests`. |
| [tests/test_reasoning_policy.py](../../tests/test_reasoning_policy.py) | Automated checks for reasoning policy. Defines `ReasoningPolicyTests`. |
| [tests/test_repair_context.py](../../tests/test_repair_context.py) | Failed repairs retain their prefix and real failure; capacity recovery remains. Defines `RepairContextTests`. |
| [tests/test_reply_continuation.py](../../tests/test_reply_continuation.py) | Automated checks for reply continuation. Defines `NativeContinuationTests`, `ContinuationBoundsTests`. |
| [tests/test_request_models.py](../../tests/test_request_models.py) | Validate API inputs without importing the server or touching job state. Defines `RequestModelTests`. |
| [tests/test_requested_test_additions.py](../../tests/test_requested_test_additions.py) | Automated checks for requested test additions. Defines `RequestedTests`. |
| [tests/test_rust_dependency_guard.py](../../tests/test_rust_dependency_guard.py) | Automated checks for rust dependency guard. Defines `DependencyCompletionTests`. |
| [tests/test_rust_toolchain_licenses.py](../../tests/test_rust_toolchain_licenses.py) | Automated checks for rust toolchain licenses. Defines `RustLicenseTests`. |
| [tests/test_sampling.py](../../tests/test_sampling.py) | Automated checks for sampling. Defines `SamplingProfileTests`. |
| [tests/test_scan_regression.py](../../tests/test_scan_regression.py) | Automated checks for scan regression. Defines `ScanRegressionControls`. |
| [tests/test_score_export.py](../../tests/test_score_export.py) | Automated checks for score export. Defines `ExportRoutingTests`, `ScoreExportTests`. |
| [tests/test_source_previews.py](../../tests/test_source_previews.py) | Source previews must preserve useful code and explain every omission. Defines `SourcePreviewTests`. |
| [tests/test_source_window_regression.py](../../tests/test_source_window_regression.py) | Automated checks for source window regression. Defines `source`, `SourceWindowRegressionTests`. |
| [tests/test_task_date_cache.py](../../tests/test_task_date_cache.py) | Long-running tasks keep their date anchor without re-prefilling at midnight. Defines `TaskDateCacheTests`. |
| [tests/test_terminal_client.py](../../tests/test_terminal_client.py) | Automated checks for terminal client. Defines `TerminalPolicyTests`, `TerminalEventTests`. |
| [tests/test_test_authority.py](../../tests/test_test_authority.py) | Automated checks for test authority. Defines `TestAuthorityTests`, `TestAuthorityIntegrationTests`. |
| [tests/test_test_collection.py](../../tests/test_test_collection.py) | Real collector mismatch must not produce a verified final. Defines `TestCollectionTests`. |
| [tests/test_test_environment_memory.py](../../tests/test_test_environment_memory.py) | Keep actual runner discovery through context changes without fake passes. Defines `TestEnvironmentMemoryTests`, `TestEnvironmentRunnerTests`. |
| [tests/test_tool_arguments.py](../../tests/test_tool_arguments.py) | Native malformed-call recovery with unchanged command values and audit. Defines `ToolArgumentDecodingTests`, `ToolArgumentRunnerTests`. |
| [tests/test_tool_runtime.py](../../tests/test_tool_runtime.py) | Automated checks for tool runtime. Defines `ToolRuntimeTests`. |
| [tests/test_tools.py](../../tests/test_tools.py) | Automated checks for tools. Defines `ComputerIntegrationTests`. |
| [tests/test_validation_results.py](../../tests/test_validation_results.py) | Automated checks for validation results. Defines `ResultsHistoryTests`. |
| [tests/test_verified_final.py](../../tests/test_verified_final.py) | Automated checks for verified final. Defines `TestEvidenceTests`, `VerifiedFinalTests`. |
| [tests/test_walk_api_evidence.py](../../tests/test_walk_api_evidence.py) | Generic standard-library facts appear only for actual relevant source calls. Defines `WalkApiEvidenceTests`. |
| [tests/test_working_memory.py](../../tests/test_working_memory.py) | Automated checks for working memory. Defines `WorkingMemoryTests`. |
