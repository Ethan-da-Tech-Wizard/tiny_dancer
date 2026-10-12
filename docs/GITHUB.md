# GitHub copy and local originals

Repository: https://github.com/Ethan-da-Tech-Wizard/tiny_dancer

The owner requested this repository on 2026-10-12 UTC. It starts private unless the
owner selects public visibility. The software license remains Apache-2.0 either
way; all upstream notices retain their own terms.

The working installation is `/mnt/GameDrive/tiny_dancer`. Its publishing Git
checkout is `run/github/tiny_dancer`, on the same drive. Edit the working
installation, validate the changes, then export them into that checkout. The
export refuses to overwrite independent edits in the publishing checkout.

## What is included

- Original application, tools, tests, scripts, configuration and dependency lock.
- Documentation, research, session handoff and all archived dependency notices.
- Pinned upstream URLs/commits and model source revision, size and SHA-256.
- The local Picchio source patch; the other upstream checkouts have no tracked edits.
- Public views of validation reports: outcomes, named checks, measurements and
  source fingerprints. Failed and cancelled runs remain failed and cancelled.
- A regenerated test-results index and a manifest of original/exported hashes.

The local JSON originals are never rewritten for publication. Report exports
omit checkpoints, model reasoning, prompts, arbitrary command output and unknown
text fields. They are summaries for review, not a complete forensic backup.
Full diagnoses remain in the human-written session log. Screenshots, personal
workspace files, chat databases, credentials, browser/editor profiles, build
products, environments, caches and multi-gigabyte weights stay local. Upstreams
and weights can be obtained from their recorded sources; GitHub is not their
binary mirror.

The release checker requires complete local evidence. Published summaries cannot
re-qualify a runtime: omitted checkpoint details remain absent rather than being
reconstructed or treated as passing evidence.

## Publish an update

Run from the working installation, after recording the actual test outcomes:

```bash
.venv/bin/python -m unittest tests.test_github_export -v
.venv/bin/python scripts/export_github.py
git -C run/github/tiny_dancer status --short
git -C run/github/tiny_dancer diff --stat
git -C run/github/tiny_dancer add --all
git -C run/github/tiny_dancer commit -m "Describe the tested change"
git -C run/github/tiny_dancer push origin main
```

Export itself does not commit, contact GitHub or start/restart the agent. It scans
the selected text for recognizable credentials and the local access token,
rejects source symlinks, and checks previous exported hashes before replacement.
This is a targeted check, not a claim to recognize every possible secret format.
Review the staged content before pushing. Credentials come from the existing
GitHub CLI keyring integration; never put tokens in remotes or project files.

GitHub Actions runs Python syntax and publication-boundary tests. The complete
local harness suite and GPU/model evaluations still require the installed tools
and hardware. A green GitHub workflow does not establish native agent competence.

## Installation scope

This is a development snapshot of the existing Linux installation. Several
launchers and paths still target `/mnt/GameDrive/tiny_dancer`; arbitrary-location
installation and other operating systems are not qualified yet. See
[INSTALL_NATIVE.md](INSTALL_NATIVE.md) for the current native backend and
[RESUME_HERE.md](RESUME_HERE.md) for known capability failures.
