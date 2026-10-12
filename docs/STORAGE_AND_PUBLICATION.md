# Storage and public source

The owner requested public access to Tiny Dancer on 2026-10-12, with credentials
and personal information excluded. The application, source changes, documentation,
dependency notices, model provenance and public test-result summaries are published
at https://github.com/Ethan-da-Tech-Wizard/tiny_dancer.

## The two drives

| Location | Contents | GitHub treatment |
| --- | --- | --- |
| `/mnt/GameDrive/tiny_dancer` | Canonical application, models, evidence and local state | Source and documentation pass through the checked publication export. |
| `/home/ethan/pg/tiny_dancer` | Compatibility symlink to the canonical project | The same source; there is no second independent application here. |
| `~/.cache/tiny-dancer/models` | Additional internal-SSD native model cache | Downloaded weights stay local; provenance and checksums are documented below. |
| `run/github/tiny_dancer` in the canonical project | Publishing Git checkout | Local `main` is synchronized with GitHub `origin/main`. |

The internal cache contains the native model, its upstream license, usage-policy
notice and cache manifest. Those notices are already represented in the published
dependency inventory. It contains no additional application source code.

## Native model provenance

Tiny Dancer uses upstream GPT-OSS-20B weights; this publication does not claim that
the model was trained by this project. The native cached file is:

- Source: `ggml-org/gpt-oss-20b-GGUF`
- Revision: `ef9b12f2ff56c69cf32153a02784e7a3c88bf524`
- File: `gpt-oss-20b-MXFP4.gguf`
- Size: `12109566624` bytes
- SHA-256: `27cd6c432c7672cb812a92f611cf3ba7bbc35928262bb1e1253ff4ee6ae35901`

The prior cache-installation evidence records identical source and destination
hashes. Publication inventories the files and preserves that evidence; it does not
claim to have rerun the multi-gigabyte hash or any model qualification tests.
See [MODEL_CACHE.md](MODEL_CACHE.md), [INSTALL_NATIVE.md](INSTALL_NATIVE.md), and
the archived model-source records for setup and provenance.

## Files that remain local

Credentials, browser/editor profiles, chat databases, conversations, model
checkpoints, raw model traces, personal workspaces and screenshots remain local.
Published JSON evidence is a reviewed summary; complete local evidence remains
necessary to qualify the runtime. Downloaded model weights, installed dependencies,
build products and caches are not mirrored into GitHub. The original model and
alternative downloaded model formats remain on GameDrive; the SSD cache is retained.

No service restart, runtime change, file deletion or model substitution is needed
to publish the source. [GITHUB.md](GITHUB.md) describes the export and push workflow.
