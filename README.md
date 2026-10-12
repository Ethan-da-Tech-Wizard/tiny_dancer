# Tiny Dancer

A local GPT-OSS-20B computer agent and workspace. Open **http://127.0.0.1:3210** or launch **Tiny Dancer** from the desktop application menu.

Project sources, original models, conversations and validation history live in `/mnt/GameDrive/tiny_dancer`. The original `/home/ethan/pg/tiny_dancer` is a symlink here. An optional [verified model cache](docs/MODEL_CACHE.md) can keep identical model bytes on a faster local drive; the GameDrive original remains intact. The desktop launcher and user-service registrations are also symlinks into this folder. No Ollama, cloud inference, remote hosting, or paid model API is used.

**Full native qualification has not passed.** The current 617 harness and comparison regression checks pass. The first normal task using the new native tool connection exposed an integration defect before the model acted; that defect is corrected. The fresh small Python task passes all independent checks; the larger inventory task still fails directory-error handling. Small, independently graded tasks must pass before moving to larger applications. [Current status and next steps](docs/RESUME_HERE.md) distinguish actual native results from test fixtures. Historical failures remain visible; `.venv/bin/python scripts/check_native_release.py` checks the same-runtime coding and precision gate.

[Local agent feedback](docs/AGENT_FEEDBACK.md) lets GPT-OSS propose corrections and reproduction tests from saved public evidence in a separate source copy. Independent validation is required before adoption.

[Simple capability status](docs/CAPABILITY_LADDER.md) shows the small-to-large test sequence.

[Native qualification](docs/NATIVE_QUALIFICATION.md) gives the three required outcomes, the reason for the previous failure, and links to current and historical evidence.

[Open-source research](docs/OPEN_SOURCE_RESEARCH.md) connects observed shortcomings to primary sources, bounded experiments and adoption decisions. Research-only tools and their licenses are listed separately from installed dependencies.

**Current setup status is in `docs/STATE.json`.** A new coding session must read `AGENTS.md`, `docs/STATE.json`, and `docs/SESSION_LOG.md` before continuing. These distinguish completed work from pending checks and record failures as well as successes.

Open **[Test results](http://127.0.0.1:3210/results)** from the workspace sidebar to compare current and historical runs, including failures and pauses. [docs/TEST_RESULTS.md](docs/TEST_RESULTS.md) provides the same saved index. Run `.venv/bin/python scripts/run_regressions.py` to archive every named test, outcome, duration and source fingerprint in `docs/validation/runs/`; `.venv/bin/python scripts/refresh_test_results.py` refreshes the index after other evaluations. Scripted model fixtures and actual local-model evaluations have separate scopes.

## Use

Choose **Agent** for tasks that use computer tools, or **Chat** for conversation. Enter a task and press Enter; Shift+Enter adds a line. Tool calls and their outputs are visible. **Stop** cancels inference and terminates the active shell process group. Completed actions stay saved. Sessions persist across app/browser restarts; a task interrupted by a service restart is marked interrupted and can be continued with a new prompt. The export button downloads a Markdown transcript.

### Code OSS and watching the work

Click **Open Code OSS** to open the session's working folder in a visible editor. Click the folder path above the composer to select a different existing project folder. The agent can also use `editor.open` to open a saved file at a line. It edits the actual files through its file/shell tools; Code OSS shows the saved changes. The agent is controlled from Tiny Dancer, with the editor alongside it. This is file editing and execution, rather than an inline autocomplete extension. Save your own unsaved editor buffers before asking it to edit those same files.

The dedicated Code OSS profile and extension directory are `run/editor-profile/` and `run/editor-extensions/`. Project-profile telemetry is disabled. The installed host editor keeps its own MIT license and bundled notices in `licenses/system/code/`.

Click **Watch** for browser or desktop snapshots, refreshed every three seconds while the dialog is open. Screenshots are stored locally. `desktop.inspect` supplies screenshot/OCR text plus active/all window metadata to the agent; browser tools supply page text, links, and fields. GPT-OSS-20B remains text-only: it reads DOM/OCR information, while you see the pictures. Desktop tools detect the active Hyprland socket instead of relying on a stale login-session `WAYLAND_DISPLAY` value.

### Work until the task is checked

Agent mode distinguishes **questions** from **work**. Questions finish with an answer; questions requiring current web evidence must cite a successfully retrieved source. Work uses a **plan → act → inspect → check → repair** loop: `task_progress` saves a checklist, and `finish_task` supplies relevant shell checks that Tiny Dancer executes. A native final can also complete after recognized passing tests on tracked, unchanged edited source files, with no pending plan steps. Failed checks and pending steps keep work open. Failed-test repair retains the native prompt prefix and adds a concise instruction to diagnose the actual latest failure; physical context exhaustion still rebuilds from the saved checkpoint. Source retrieval alone does not establish every factual claim, and successful commands only verify their actual assertions. Agent draft final text stays private until the runner accepts completion.

Each new agent task starts with its own user goal, without old task instructions or tool results. Use Resume to continue an existing goal. Chat retains ordinary conversation messages while excluding old tool/operator instructions. Every tool result and checkpoint persists in SQLite, the audit log, and `run/tasks/JOB_ID.json`. Long work retains the original goal and latest plan while compacting earlier transactions. Tool text is bounded in the model prompt; saved artifacts and narrower reads provide omitted data.

**Keep working until done** is on by default in the Agent UI. It continues the same task across context compactions, without an aggregate turn or time budget. It finishes after accepted answer/completion checks, or pauses when blocked, repeating unchanged actions, unable to generate a complete step after four attempts, or hitting eight consecutive tool failures. A watchdog stops inference after 900 seconds without observable token/CPU/I/O progress; a slow active prefill extends that watchdog. Individual tool actions still time out. This controls dead ends rather than promising every task will succeed. **Stop** remains available.

Native coding evaluations now default to observing until termination, with no aggregate deadline:

```bash
.venv/bin/python scripts/evaluate_hardening_suite.py labels --effort auto --until-terminal
```

Use this only when the app is idle; it starts a real model task. The report saves a progress sample every 20 seconds: actual edited-file hashes, completed plan steps, test receipts and separate action/token activity. The original-money observer accepts the same `--until-terminal` option. `--observation-seconds` retains bounded benchmark mode. A clock cutoff records an unfinished observation; it does not establish that eventual completion is impossible.

Uncheck that option for bounded runs: **6 inference turns / 10 minutes for questions** and **24 turns / 30 minutes for work**. Reaching either limit pauses and saves the task. `max_tool_steps` controls checkpoint cadence separately. New API Agent requests also default to continuous work; Chat stays bounded. Set `run_until_done: false` for a bounded Agent run, or `true` on Resume to change a saved bounded task. Omitted Resume options preserve the saved policy. `task_kind` (`auto`, `answer`, `work`), `max_turns` and `max_seconds` provide bounded-mode overrides. These automatic interpretations and checks cannot establish arbitrary task completeness.

For the narrow request “most recent NFL Sunday matchups and scores,” the host resolves the last completed Sunday in America/Phoenix. The model selects `nfl_scores`; that tool fetches decoded ESPN JSON with the correct compact date parameter, checks every returned game's NFL date, final status, team pairing, score format and unique ID, then the harness publishes those checked fields directly. It requires no second inference pass or invented shell check. This is a purpose-built score lookup, not evidence of general autonomous research. Player statistics, comparisons and predictions use the general question workflow. `fetch_json` supports other structured sources with a bounded decoded response, HTTP/application error checks, saved full JSON and optional RFC6901 pointer.

Counted completed Sundays (for example “2 Sundays ago” or “Sunday before last”) also resolve to an explicit date. On Saturday 2026-10-10, both mean 2026-09-27. Ambiguous/future phrases stay in the general workflow. The previous user's counted-Sunday retry exhausted its reply budget without making a tool call, then paused at 600 seconds; this date-routing correction does not constitute a successful native retest. See `docs/two-sundays-delay-diagnosis.json`.

Asking to save those scores in JSON or put them in Code OSS is **work**, with required file/editor outputs. `nfl_scores` can fetch, save every checked matchup to a `.json` file and open that actual file in Code OSS in one action. Completion requires the saved JSON's date, source and all matchups to match the retrieval, plus an actual open-file action when requested. A score table or internal retrieval artifact alone cannot complete that request. The interface identifies this path as **Checked data export**: GPT-OSS chooses tool arguments; host code retrieves, formats and writes the checked data. More involved requests stay in the general work loop.

**Resume task** sits beside the input whenever the latest task is paused, blocked, stopped, failed, or interrupted. The pause reason appears there too; neither depends on opening Task progress. Resume retains the selected run policy, original goal/folder, checklist and recent checks. Context exhaustion automatically rebuilds a prompt from those same saved facts and output references, while retaining the full history on disk. Incomplete tool calls never execute. If even the minimal goal/checkpoint cannot fit after two recoveries, the task pauses with that specific blocker. API clients can pass `compact_context: false` on Resume to replay earlier history. A service restart preserves progress and requires Resume; it does not automatically repeat computer actions.

The interface polls durable task state every four seconds as well as streaming events. Background tabs or interrupted event streams recover current progress and paused/completed controls. Progress shows elapsed time and generated-token counts; Task progress shows the goal/checklist rather than duplicating a full final answer. Refresh an already open tab once after application upgrades to load its new interface.

Example coding request: “Open this project in Code OSS. Implement a small Python greeting function, run checks of its behavior, fix any failures, and finish only when the checks pass.” A directly tested example is `workspace/live-coding-demo.py`; evidence is in `docs/editor-screen-validation.json`.

The working directory defaults to `workspace/`. The API allows creating a session with any existing working directory. Tools can access paths and run programs available to Ethan's ordinary user account. This provides normal user access, not root privileges or a claim that every desktop application has an automation interface.

For terminal use:

```bash
cd /mnt/GameDrive/tiny_dancer
.venv/bin/python scripts/ask.py "Inspect the workspace and summarize its files"
# Start another independent goal in the same session:
.venv/bin/python scripts/ask.py --session SESSION_ID "Inspect another folder"
```

New terminal Agent tasks continue until checked completion or a blocker. `--bounded` requests a timed run; `--until-done` changes a resumed bounded task to continuous work. Ctrl+C stops the task and preserves history. `--chat` disables computer tools; `--cwd` selects an existing working directory. The client streams public events and reconnects using its last event ID.

Resume a saved task from the terminal:

```bash
.venv/bin/python scripts/ask.py --resume-job JOB_ID --max-tokens 1024
```

Available tools:

- Shell: bash commands, Python, git, programs, process and system inspection; timeout and cancellation; complete output is saved as an artifact.
- Files: read, list, create, and replace files. Replacements save the original in `run/backups/`.
- Browser: local Chromium with a persistent separate profile; navigate, inspect text/links/fields, click, fill, press keys, execute page JavaScript, save screenshots, and download files. Websites load only when requested by a task; inference remains local.
- Desktop: inspect the screen with OCR/window metadata, list/focus Hyprland windows, capture screenshots, type via the clipboard, and send keyboard shortcuts. GPT-OSS is text-only, so OCR and DOM inspection supply screen information. Desktop mouse automation is not included. Typing uses the clipboard and changes its contents.
- Editor: open the working folder or a saved file in visible Code OSS; inspect editor window status.
- Task progress/completion: saved checklist, next action, executed completion checks, and resumable pauses.
- Python/Rust lookups: on-demand registry metadata, documentation and local manifest/lock inspection. See below.
- Project inspection: `inspect_project` gathers bounded files, listings and installed Python/Rust test commands together, without executing project imports or installing dependencies.
- Batched checks: `run_checks` executes up to eight commands sequentially, with actual exit codes, output artifacts, timeouts and cancellation. It stops on the first failure by default. Verification uses real test results and unchanged source hashes.

Local coding tasks initially expose the tools relevant to the goal. `discover_tools(toolset="web"|"desktop"|"editor")` makes another group available when needed; discovery choices persist across Resume. This reduces prompt processing without removing the underlying tools. Long tool previews retain both the beginning and final test/error summary; full saved outputs remain available. Auto reasoning is resolved once per run to preserve the native prompt prefix when another language is discovered.

Inspection uses its automatic bounded scan when `files` is omitted **or empty**. Available test commands are checked against the actual runtime; the model is guided to prefer them. Check timeouts use seconds, from 1 to 300, with 120 as the default. Small patches remain available for work in every language. Verification tracks all files written through the text tools, and external edits after tests invalidate that evidence. Loop detection compares parsed arguments so whitespace/key ordering cannot disguise an unchanged action. Explicitly named JSON output paths must match the saved file. Desktop/editor discovery also works for questions; greetings can finish as conversation without a work-verification loop.

The improvement sequence is recorded in [docs/hardening-plan.json](docs/hardening-plan.json). It includes frozen native repair, the exact user export, a fresh input-only CSV implementation, scripted failure/recovery variations and live interfaces. Results identify fixture tests, actual local-model execution and host-formatted exports. A passing test proves its assertions; it does not establish general coding accuracy or arbitrary task completeness.

### Local test runner and starting budget

**Starting budget → Auto** starts work with 2048-token chunks and chat/questions with 512. The model can stop earlier. Numeric choices keep their requested starting value. Until-done retries can grow the starting allowance up to 4096 after an incomplete step; Resume retains it unless the requested choice changes. The native chat-tool connection gives continuous Auto work the actual remaining context for a complete reply; the raw backend continues unfinished replies in chunks. The old 8192-token/four-chunk cap is removed. Context exhaustion still saves progress and rebuilds the prompt; explicit numeric reply budgets remain capped. Partial calls never execute. API `max_tokens: null` or omission selects Auto; compatibility `/v1` chat retains its own default.

The native context is now **32768 tokens**, shared by prompt and response. The previous 8192-token setting repeatedly filled during coding. The context increase preserves the original model weights, f16 KV and expert placement. The current sampler is the upstream recommended temperature 1.0 / top_p 1.0, with top_k/min_p cutoffs disabled and repetition penalty 1.0. On the previous greedy profile, an actual 9586-token prompt returned the correct native final in 95.22 seconds, with at least 6.45 GiB RAM and 2228 MiB VRAM available. That checks capacity and desktop memory, rather than coding completion. [Parameter evidence and remaining sampler uncertainty](docs/context-parameter-audit-validation.json) and all current/historical outcomes are on the [results page](http://127.0.0.1:3210/results).

A pinned local **pytest 9.1.1** runner is available to shell/check tools. It uses the project venv and collects function-style tests and fixtures; the ordinary bare `python` command remains the host interpreter. Use a project's explicit interpreter/runner when its runtime requirements differ. Pytest temporary files live on the GameDrive. The generated program can still depend only on the standard library. No inference service or background test process was added.

`inspect_project` includes common `tests/`, `test/` and `src/` files in its eight-file bound and prioritizes test evidence. A missing runner or zero-test invocation returns actual available runner facts with the recorded failure. Requested commands are never replaced or silently rerun. Named JSON created by shell, or an unnamed JSON read back through file tools, can satisfy output verification; the harness hashes required outputs and rejects later changes, including symlink retargeting.

### Python and Rust evidence when needed

`python_lookup` and `rust_lookup` each support `package`, `docs` and `dependencies`. Their schemas are exposed for a relevant language request or project task; unrelated tasks do not load them. `discover_tools(language)` enables a missed language during a task without fetching anything, and that choice persists across Resume. Availability does not force a lookup on every code edit.

Package lookup accepts an exact version or queries the registry's current version. Python results include Requires-Dist, extras, environment markers, Python constraints, project links and declared licenses. Rust results pin the dependency endpoint to the selected crate version and retain optional/default features, dev/build kinds, target conditions, compiler requirements and license metadata. These are declared dependencies, not a fresh solver result or audit of what is installed.

Documentation can use a topic (Python `asyncio`, Rust `std/collections`) or a precise version/URL/anchor. Supported reference hosts are docs.python.org, project subdomains of readthedocs.io, doc.rust-lang.org and docs.rs. Python defaults to the service interpreter's documentation version; pass a version for another project's interpreter. Crate docs accept a package and version. Other project documentation remains accessible through the existing browser tools.

Local inspection supports Python `pyproject.toml`, requirements/constraints files, `uv.lock`, `poetry.lock` and Pipfile files; Rust `Cargo.toml` and `Cargo.lock`, including workspace and target declarations. No package imports, setup.py execution, pip installation, Cargo resolution or build scripts occur during inspection. Includes/dynamic metadata/workspace inheritance may need additional targeted file reads.

Full evidence is saved in `run/artifacts/`; model output is bounded to about 6000 characters. HTTP/file inputs are limited to 2 MB. Disk-only caches under `cache/language-lookups/` expire after one hour for registry data and 24 hours for docs; cached results retain the original retrieval timestamp. No background indexing or browser process is needed. Public registry/doc requests use the internet while all model inference stays local. The lookup handlers use existing dependencies. [Lookup licensing](licenses/LANGUAGE_LOOKUPS.md) distinguishes publisher declarations from preserved actual license texts.

Examples: “Inspect this Python project's dependencies before editing it”; “Look up serde 1.0.219 dependencies and features”; “Check the Python 3.12 pathlib read_text documentation.” Actual handler validation: `.venv/bin/python scripts/validate_language_tools.py`, recorded in `docs/language-lookup-validation.json`. This validates lookup handlers, not general native coding competence.

## Harness and thinking controls

The composer provides **Auto**, **Quick**, **Balanced**, and **Thorough** thinking. Auto uses high reasoning for work and low for chat/questions. Quick selects low, Balanced medium, and Thorough high. The API accepts the same reasoning levels. This work default is under native evaluation. The choice is fixed for a run and preserved on Resume unless changed: switching it every step would invalidate the model's cached system prompt. Extra reasoning can take longer; it is not a guarantee of correctness or frontier-model capability.

Work in every language exposes `apply_patch` for small edits: `*** Begin Patch`, `*** Update File: relative/path`, `@@`, context lines prefixed with a space and `-old`/`+new` lines, `*** End Patch`. Add File sections use `+lines`. Every file is validated before writes; mismatched or ambiguous context, outside-folder paths, symlinks, deletion/rename and no-op edits are rejected. Existing files get recovery copies under `run/backups/patch-*`; write failures roll back earlier files. General writes remain available through existing tools. This original implementation adds no dependency.

`exact_history_cache` preserves the model's raw generated token prefix when the complete canonical prior conversation still matches. It avoids reprocessing code merely because native Harmony headers were reordered during serialization. Changed goals/results/instructions, context compaction, partial calls and final drafts fall back to normal rendering. Stop, unload and startup clear the resident cache. This preserves messages and model weights/precision; it does not remove cold-start prefill. Metrics report `exact_history_cache_tokens` and `canonical_prompt_tokens`. Native performance evidence is recorded separately from fixture tests.

For code edits, the runner can accept a native final after an actual recognized test command passes a nonempty suite, tracked edited sources still match their tested SHA256 hashes, and every plan step is complete. Reading a saved test log never counts as running tests. Mutations invalidate this evidence; read-only inspections retain it. Other work uses explicit `finish_task` checks. Work completion rejects zero-test suites even if the runner exits successfully. Nonzero shell exits and failed verification count toward the no-progress failure guard, with the latest failure kept in the checkpoint. Successful commands and tests prove their actual assertions; independent task evaluation remains necessary to detect incomplete or weak assertions.

Research informing these experiments: [GPT-OSS native Harmony/tool-interface paper](https://arxiv.org/abs/2604.00362), [dynamic tool discovery](https://www.anthropic.com/engineering/advanced-tool-use), and [long-running harness design](https://www.anthropic.com/engineering/harness-design-long-running-apps). Published results use different models/backends/hardware or context sizes and are not performance claims for this installation. No external harness or cloud model was installed.

Historical native repair validation: **584.59 seconds**, six turns, small patch applied, missing pytest recovered through standard-library unittest, three unseen arithmetic cases passed, and a native final accepted after verified tests. No operator code or recovery messages were added during execution. This deliberately seeded repair probe is distinct from the unassisted CSV baseline, which passed nine CLI checks but paused under the old finish-only gate and had unclear error messages. See [native repair report](docs/native-harness-validation.json), [completed UI evidence](docs/native-harness-ui-validation.json), and [frozen coding baseline](docs/native-coding-validation.json). That earlier release passed 87 regressions; current named results are in [TEST_RESULTS](docs/TEST_RESULTS.md). The cache metric is a per-turn counterfactual against the current raw prefix; a controlled full-run speed multiplier has not been measured.

The repeated frozen repair passed in **498.72 seconds / four turns**, versus the historical 584.59 / six. It used actual project inspection, a small patch, batched tests and native verified completion without runtime hints. Separate historical runs are not a controlled general speed multiplier. The exact missed score export now exists at [workspace/scores_2026-09-27.json](workspace/scores_2026-09-27.json) and was opened in Code OSS; every matchup matched a separate source fetch.

The fresh input-only CSV retest remains **failed**: it was stopped at its one-hour observation window, struggled with unavailable/zero-test runners, and passed 10 of 11 independent CLI checks plus all five friendly-error checks. Its large-money Decimal precision failure is preserved in [the frozen report](docs/hardening-coding-validation.json). [The seeded precision repair](docs/precision-repair-validation.json) also failed to finish within its one-hour evaluation window and left the large-number defect unchanged. It received acceptance tests before starting, with no implementation or runtime hints. Those failures exposed further source-preview and context-budget defects. The deployed fixes preserve modest source files in one read, identify missing ranges in larger reads, and reserve the full requested output allowance before inference. That historical release had **184 passing regressions**, plus **12 live results-page checks**. [The final native arithmetic replay](docs/final-native-repair-validation.json) passed in **8 minutes 37 seconds**, four inference turns, with all three unseen arithmetic cases passing and no runtime hints. It checks the deployed tool/patch/tests flow separately; it is seeded repair, not proof of independent coding ability. All current and past outcomes remain on the results page.

## Runtime and model

Colibrì is installed at `vendor/colibri`, with its compiled C engine at `vendor/colibri/c/colibri`. Its current model families do **not** include GPT-OSS. Loading the requested model directly into that engine would not work.

The current serving backend is **local llama.cpp**, using the same GPT-OSS-20B model in its native MXFP4 format. Tiny Dancer renders native OpenAI Harmony tool descriptions and preserves actual assistant tool calls/results. **Picchio**, the Colibrì-inspired GPT-OSS streaming engine at `vendor/picchio`, remains available as the previous backend with its persistent C service protocol.

Official `openai/gpt-oss-20b` weights remain in `models/gpt-oss-20b-original`. The serving copy is `models/gpt-oss-20b-native-mxfp4`; its pinned revision, checksum and sample fidelity checks are recorded in `docs/llama-reference-model-source.json` and `docs/native-gguf-fidelity-validation.json`. The prior Picchio copy, `models/gpt-oss-20b-picchio-int4`, uses INT4 gs64 experts and INT8 dense matrices/embedding/output head. That conversion changes precision and is retained separately. `docs/model-source.json` and `docs/upstreams.json` preserve original provenance and source commits.

Hardware: i7-12650H, about 16 GB RAM, RTX 3070 Laptop 8 GB VRAM, GameDrive USB SSD. The current native backend uses 32768 context tokens, eight CPU threads, batches of 128, f16 KV cache and one inference slot. The first 16 expert layers run on CPU; the remaining eight expert layers and dense layers use the GPU. Context shifting is disabled. The `prefill_batch`, `ram_cache_gb`, `gpu_cache_gb` and `gpu` settings in `config.json` describe the retained Picchio backend; they do not configure native llama.cpp. Reply budgets include internal reasoning and tool arguments. Saved evidence remains on disk when previews/history are compacted. Incomplete tool calls never execute.

Desktop stability: cold model loading requires 4.5 GiB available RAM, a user-requested 25% reduction from the earlier 6 GiB startup requirement. This is a configurable preflight check, not allocated or reserved memory. If available RAM remains below 1.5 GiB for 6 seconds during inference, only the model is stopped and the task checkpoint is saved for Resume. These checks use available memory, including reclaimable cache. The native child runs at nice 5; the UI and unrelated applications keep their priorities. Smaller expert caches can increase disk reads; weights, precision and active experts are unchanged. Code OSS uses this workspace's dedicated profile, equals-form directory flags and `--disable-gpu`, following the [official display troubleshooting guidance](https://code.visualstudio.com/docs/supporting/faq). This addresses an observed Electron crash but does not establish every crash's cause. No unrelated editor settings are changed.

After **300 idle seconds**, the model process and unused agent browser are released automatically. Historical Picchio measurements were about 4.3 GiB private RAM and 5.4 GiB CUDA allocation. Native memory use varies with the mapped model pages and workload; the controlled placement report records its measurements. Browser watching keeps that browser active. User editor/browser applications remain running. Set `idle_unload_seconds` to `0` to keep the model warm. Unloading frees working memory but loses the warm prompt cache; the next request pays startup and prefill again. Native per-turn timing and activity counters are visible in `/api/status` and saved metrics events.

The retained Picchio CUDA library is `vendor/picchio/libpicchio_cuda.so`; its local bridge patch is `docs/picchio-local.patch`. The current native build lives in `build/llama-reference/bin/`, built from the pinned source under `vendor/llama.cpp`. Backend changes require an idle guard, tests and a service restart.

## Service and continuity

```bash
systemctl --user status tiny-dancer.service
.venv/bin/python scripts/restart_when_idle.py
systemctl --user stop tiny-dancer.service
systemctl --user start tiny-dancer.service
```

The service is enabled for the user's login session. It requires the game drive to be mounted. Run `scripts/start.sh` directly for a foreground launch while the service is stopped. Desktop tools require an active Hyprland session. To refresh the graphical session environment if needed:

```bash
systemctl --user import-environment DISPLAY WAYLAND_DISPLAY XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS
.venv/bin/python scripts/restart_when_idle.py
```

The restart helper refuses while a task is active. Add `--wait-seconds 3600` to wait up to an hour for it to finish. Service restarts unload the model and close its live browser; saved history, screenshots, and task checkpoints remain available.

Project layout:

| Location | Contents |
| --- | --- |
| `app/` | Local web interface, native agent loop, computer tools |
| `vendor/` | Pinned upstream repositories and compiled engines |
| `models/` | Original weights and serving conversion |
| `.venv/`, `cache/`, `requirements.lock.txt` | Python environment, local caches, dependency versions |
| `workspace/` | Default task working directory and durable agent memory |
| `run/workspace.sqlite3` | Conversations, native Harmony messages, jobs, activity events |
| `run/artifacts/`, `run/backups/`, `run/browser-profile/` | Tool outputs, original file backups, persistent browser data |
| `run/tasks/`, `run/editor-profile/`, `run/editor-extensions/` | Durable task checkpoints and the dedicated Code OSS profile |
| `logs/agent-audit.jsonl` | Timestamped tool arguments/results and task outcomes |
| `logs/` | Build, download, conversion, service, and test logs |
| `docs/` | Resume instructions/state, session log, source manifests, validation, screenshots |
| `licenses/` | Upstream licenses, notices, and model usage policy |

Back up the folder while the service is stopped to include a consistent SQLite database. It contains your conversations, commands, file contents, and browser profile; the service creates runtime data with private user permissions.

## Reproduce installation

For the current llama.cpp backend, start with [native setup and installation limits](docs/INSTALL_NATIVE.md). The commands below preserve the older Picchio setup. [GitHub contents and update procedure](docs/GITHUB.md) explain the source snapshot and local-only data.


The dependencies and compilers already available on this Arch Linux machine were used; no system packages were installed. Model/dependency downloads need internet once. The inference tokenizer cache is in `cache/tiktoken`; serving does not use Hugging Face or OpenAI APIs.

```bash
cd /mnt/GameDrive/tiny_dancer
source scripts/env.sh
UV_CACHE_DIR="$TINY_DANCER_ROOT/cache/uv" uv venv .venv --python 3.12
uv pip sync --python .venv/bin/python requirements.lock.txt --extra-index-url https://download.pytorch.org/whl/cpu
make -C vendor/colibri/c -j4 colibri
make -C vendor/picchio -j4
(cd vendor/picchio && /opt/cuda/bin/nvcc -O3 -arch=sm_86 -shared -Xcompiler -fPIC -o libpicchio_cuda.so picchio_cuda.cu)
.venv/bin/python scripts/download_model.py > logs/model-download.log 2>&1
scripts/convert_model.sh > logs/model-convert.log 2>&1
```

Download resumes automatically and retains the selected revision. The upstream converter exceeded available memory on the third shard; `scripts/convert_low_memory.py` uses the same quantizers with chunked BF16 reads, atomic output parts, and a streaming merge into the sequential filenames required by the C loader. The merged payload is checked with SHA-256, and an exact check confirms every expected tensor is present once. The first two completed upstream shards are reused. Conversion resumes from completed outputs after interruption. Do not run conversion while serving the model. Upstream directories are already cloned; do not pull blindly over the local Picchio patch.

## Local API

The workspace uses `/api/` for sessions, tasks, cancellation, and durable streamed events. `/v1/models` and a **non-streaming, text-chat-only** `/v1/chat/completions` endpoint are available for other local clients. This compatibility endpoint does not implement OpenAI function-calling or the Responses API; computer tools run through workspace agent tasks.

Browser access uses a local HTTP-only session cookie. API clients can read the user-private token from `run/access-token` and send it as a Bearer token. Never copy the token into documentation or logs. The app binds only to `127.0.0.1` and blocks foreign-origin writes and unexpected Host headers.

## Verification

Read `docs/STATE.json` and the logs for the actual verification status. Synthetic CPU inference and CUDA numeric tests, direct tool tests, browser UI checks, and real model/agent tests are recorded separately. Re-run tool tests while the service is ready:

```bash
source scripts/env.sh
.venv/bin/python -m unittest discover -s tests -v
```

## License

Tiny Dancer's original code, scripts, tests, and project documentation are licensed under **Apache-2.0**. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

Colibrì and GPT-OSS are Apache-2.0; Picchio is MIT. Third-party components retain their own licenses. The organized [license inventory](licenses/README.md) includes the main components, model terms, every installed Python dependency, bundled notices, and direct host-tool licenses. Full texts and their source/checksum records are preserved in `licenses/`.

Refresh and verify the inventory after dependency changes:

```bash
.venv/bin/python scripts/collect_licenses.py
.venv/bin/python scripts/collect_licenses.py --check
```

## Measured performance

The completion rework tested the exact original Sunday-score question: **134.62 seconds, one model turn, 406 prompt tokens**, all 14 final games matched the independently fetched source. This is a specialized workflow improvement over the earlier failed run, not a controlled native-kernel speed comparison. Actual automatic idle unloading also released **3.918 GiB private RAM and 5506 MiB GPU allocation**. See [docs/PERFORMANCE_AND_TOOLS.md](docs/PERFORMANCE_AND_TOOLS.md) for the profile, tradeoffs, local-tool research and concrete next Picchio experiments.

Historical Picchio measurements: increasing prefill batches from 64 to 1024 reduced the first 700-token agent prompt from **326.89 s to 125.56 s**; decoding was about **1–1.5 tokens/s**. A larger browser task took 811.61 seconds for 3646 prompt tokens and 952.11 seconds for the next 2402 new tokens. These describe the previous backend, preserved in `docs/performance.json`.

The current native MXFP4 backend passed sample fidelity/protocol checks and all 377 regressions after source-window, release-checker and benchmark-control hardening. Earlier inventory and Rust tasks completed in 337 and 319 seconds; exact-money repair still fails. Small warm prompts previously decoded around 31–32 tokens/s; long cold prompts can wait on disk. The 1.5 GiB desktop RAM reserve remains enforced. The [CPU-thread comparison](docs/CPU_THREAD_BENCHMARK.md) found no speed gain from four/six threads; production stays at eight. [Expert placement](docs/expert-placement-validation.json) compares GPU placement without reducing model precision or context; its speed measurements do not establish task accuracy. See [native qualification](docs/NATIVE_QUALIFICATION.md) for the remaining failure.
