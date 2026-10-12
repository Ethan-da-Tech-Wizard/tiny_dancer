# Let the local model contribute improvements

GPT-OSS can inspect evidence about its own setup, propose corrections and write reproduction tests. This is practical diagnostic access: it does not establish consciousness or give the model infallible insight into why it generated an answer.

The first workflow uses the existing local agent, one run at a time. It costs no extra inference during ordinary tasks. A review starts only when requested and the app is idle. The review appears as **Agent diagnostic feedback** in the normal workspace.

## How it works

1. Select a completed evaluation and the relevant source files. Preparation copies only selected Python/Jinja source and allowlisted public outcomes into a new folder under `workspace/agent-feedback-*`.
2. GPT-OSS reads the observations and its local instructions. It writes `feedback.json`, an isolated candidate correction and `test_feedback.py` when the evidence justifies a change. It can also report insufficient evidence.
3. The same reproduction tests run against the unchanged original copy and the candidate. A setup/import failure does not count as detecting the defect.
4. Codex or the maintainer independently checks the diagnosis, tests a known conforming control, and runs relevant regressions. Only then can a correction enter the live application after an idle check.

No automatic deployment is provided. The ordinary agent still has the user's OS permissions; the separate working copy and instructions are an organizational boundary, not an OS sandbox. The observer checks original-evidence and runtime hashes. Use its saved report to detect changes outside the requested scope.

## Use

From `/mnt/GameDrive/tiny_dancer`, prepare an example review of the historical template failure:

```bash
.venv/bin/python scripts/prepare_agent_feedback.py \
  docs/native-template-steering-probe.json \
  --source app/templates/gpt-oss-upstream.jinja \
  --goal 'Preserve system and developer instructions, including later review updates, in chronological order while preserving supported user, assistant and tool formatting.'
```

The command prints the new workspace path. When the app is idle, start it with:

```bash
.venv/bin/python scripts/run_agent_feedback.py workspace/agent-feedback-TIMESTAMP
```

Alternatively, select that folder in the Tiny Dancer UI and send the contents of its `REQUEST.txt` in Agent mode. Stop and Resume use the same controls as other tasks. Runs have no aggregate deadline; ordinary inactivity, resource and tool safeguards remain.

`source/` is the unchanged snapshot; `candidate/` is the proposed revision. Neither is the live app. `manifest.json` records original hashes. The input excludes checkpoint transcripts, private reasoning, arbitrary error text and tool arguments. Public check names and manually supplied review requirements still need ordinary care when choosing what to share.

## Reading results

The observer saves `docs/native-agent-feedback-*.json` and adds it to [Test results](http://127.0.0.1:3210/results). Its pass means the agent completed, produced structured feedback and preserved evidence/runtime. **It does not approve the diagnosis or patch.** Separate independent validation must show a real failure before the correction, success after it, and compatibility with the known conforming behavior.

This first calibration uses a known historical bug. It can establish the ability to contribute a valid diagnosis/test, but cannot establish blind discovery of new defects or reliable self-improvement on arbitrary tasks. Earlier model-only reviews and generated tests missed defects or asserted wrong requirements; those failures remain in the test history.

The preparation/observer/test code is original Tiny Dancer Apache-2.0 and uses existing dependencies. Source snapshots retain their original licenses. No hosted inference or new framework is added.

## First native observation

The first diagnostic was cancelled by the maintainer after measured disk paging, before it produced a proposal or reproduction test. It is recorded as cancelled, not a capability pass or proof it could never finish. [Observation](feedback-paging-observation.json), [intervention](feedback-paging-intervention.json), [native report](native-agent-feedback-20261012T042654614528Z.json). A corrected prepared workspace puts the full brief, public evidence and exact source paths in README, which automatic initial project inspection actually delivers. An integration test verifies that delivery. Next trial follows the authorized SSD cache measurement; no live hints will be supplied.
