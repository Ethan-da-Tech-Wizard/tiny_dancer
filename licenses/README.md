# Tiny Dancer licenses

Tiny Dancer's original application code, scripts, tests, and project documentation are **Apache-2.0**, as requested by the project owner on 2026-10-10. The full text is [../LICENSE](../LICENSE), with project attribution in [../NOTICE](../NOTICE). The copyright notice uses “Tiny Dancer contributors.”

Third-party code, libraries, model weights, and their local modifications retain their original terms. Private conversations, browser profiles, task files, downloaded content, caches, and machine logs are not automatically licensed by the project's software license.

The completion/resource rework adds original Apache-2.0 modules and uses the already inventoried HTTPX library; it adds no new third-party package. The owner requires open source tool integrations and local inference. Gemini CLI (Apache-2.0 upstream) and Claude Code were considered, but neither is installed or included in this inventory. Future MCP servers must have their own source revision, license and bundled notices archived here before use. The project's Apache-2.0 license does not replace their terms.

## Main components

| Component | License | Preserved license and notices | Installed role |
| --- | --- | --- | --- |
| Tiny Dancer | Apache-2.0 | [LICENSE](../LICENSE), [NOTICE](../NOTICE) | Local workspace, native agent loop, and computer tools |
| Colibri | Apache-2.0; included components have additional notices | [LICENSE](colibri-LICENSE), [NOTICE](colibri-NOTICE), [third-party notices](colibri-THIRD_PARTY_NOTICES.md) | Preserved installed C engine; current GPT-OSS serving uses llama.cpp |
| OpenAI GPT-OSS source | Apache-2.0 | [LICENSE](gpt-oss-LICENSE), [repository usage policy](gpt-oss-USAGE_POLICY) | Pinned reference source in `vendor/gpt-oss/` |
| GPT-OSS-20B weights and tokenizer | Apache-2.0 | [model LICENSE](models/gpt-oss-20b-original/LICENSE), [model USAGE_POLICY](models/gpt-oss-20b-original/USAGE_POLICY) | Original official model; the converted serving copy retains the same files |
| Picchio | MIT | [LICENSE](picchio-LICENSE) | Preserved GPT-OSS C/CUDA engine and session bridge; fallback backend |
| llama.cpp | MIT; bundled component terms preserved | [license and bundled notices](llama.cpp/) | Current pinned local native MXFP4 C/CUDA backend; bundled notices retained |

Source commits are recorded in [../docs/upstreams.json](../docs/upstreams.json), and the model revision in [../docs/model-source.json](../docs/model-source.json). `inventory.json` ties these revisions to the copied license files. The original repository usage policy and model usage policy differ slightly; both are preserved verbatim. Serving-model copies are in [models/gpt-oss-20b-picchio-int4/](models/gpt-oss-20b-picchio-int4/).

Colibri's upstream notice includes MIT-licensed ds4/ggml adaptations and Apache-2.0 Swiftlet adaptations. Its optional DeepGEMM/CUTLASS build is described upstream as fetched rather than vendored; this installation does not use that build.

## Other installed dependencies

- [PYTHON_DEPENDENCIES.md](PYTHON_DEPENDENCIES.md): every distribution in the current project virtual environment, checked against `requirements.lock.txt`; full license files, notices, and bundled component licenses are copied under `python/`.
- [SYSTEM_DEPENDENCIES.md](SYSTEM_DEPENDENCIES.md): the Python interpreter and direct host tools used for inference, shell/browser/desktop actions, service management, installation, builds, and validation. Available host notices, common license texts, and NVIDIA terms are copied under `system/` and `common/`.
- [inventory.json](inventory.json): machine-readable versions, upstream revisions, source paths, SHA-256 hashes, and metadata evidence for every copied file.

Examples beyond the main components include MIT (FastAPI), BSD licenses (HTTPX/Starlette), Apache-2.0 (Harmony/Playwright), MPL-2.0 (Certifi and portions of other packages), PSF terms (Python), GPL/LGPL host tools, and NVIDIA's separate CUDA/driver agreements. Bundled subcomponents can have additional terms; their preserved texts are the authority.

The Code OSS editor integration uses the installed MIT-licensed `code` package; its full license and bundled `ThirdPartyNotices.txt` are preserved in [system/code/](system/code/).

The [Python/Rust lookup integration](LANGUAGE_LOOKUPS.md) is original Apache-2.0 code using already inventoried Python, HTTPX and packaging. No new third-party package or compiler was installed. Registry license fields are publisher metadata, rather than an archive of a referenced package's actual license terms.

The system inventory covers the direct tools used by this project, rather than every transitive library or package in the operating system. Chromium's full bundled-component notices are available through its `chrome://credits` page. These external tools remain installed on the host; the license archive does not redistribute their binaries.

## Updating the records

[Researched projects](RESEARCH.md) records Aider and mini-SWE-agent separately from installed components. Their documentation was reviewed; neither framework was installed and no implementation code was copied.

The CPU-thread benchmark and its 13 control tests are original Apache-2.0 project code using the existing Harmony, HTTPX, psutil and host NVIDIA tools. No package was added. Primary llama.cpp/NVIDIA monitoring documentation motivated the measured experiment; no upstream implementation code was copied. [Results and scope](../docs/CPU_THREAD_BENCHMARK.md).

From `/mnt/GameDrive/tiny_dancer`:

```bash
.venv/bin/python scripts/collect_licenses.py
.venv/bin/python scripts/collect_licenses.py --check
```

Collection works offline from the installed files and package metadata. It copies texts without rewriting them, includes bundled notices shipped in the Python wheels, records license identifiers with their evidence, and fails if a locked dependency is missing or at the wrong version. Existing archives from older dependency versions are retained; `inventory.json` and the generated tables describe the current snapshot.

After changing dependencies, refresh `requirements.lock.txt` and this inventory together, then record the change in `docs/SESSION_LOG.md`. Keep third-party notices with the corresponding component when packaging the application. Local Picchio modifications remain MIT and are documented in [../docs/picchio-local.patch](../docs/picchio-local.patch).

The project license text follows the [Apache Software Foundation's canonical Apache 2.0 license](https://www.apache.org/licenses/LICENSE-2.0.txt).

The exact native-history cache, small context-checked patch handler, thinking controls and tested-native-final/zero-test verification guards are original Tiny Dancer Apache-2.0 code. No new dependency or external harness was installed; functional interface ideas from research are cited in README. Public registry/documentation retrieval and private generated task files retain their existing scope and are not relicensed by this project.

The batching, compact-prompt, required JSON/editor-output verification and test-results modules, scripts and tests are original Apache-2.0 code. They use already inventoried dependencies and host tools; no additional package, MCP server or native CUDA kernel was added. The current archive contains 257 license texts, 45 Python distributions and 29 direct host dependencies. Private score exports and evaluation logs remain runtime data under the scope above.

The later local test-runner addition pins pytest 9.1.1 (MIT), iniconfig 2.3.1 (MIT), pluggy 1.6.0 (MIT), and Pygments 2.21.0 (BSD-2-Clause). Full installed license/bundled texts are preserved in the generated Python table and matching `python/` directories. All original package pins were retained. The thin command wrapper, nullable Auto-budget validation, output/evidence fixes and maintenance readiness code remain original Apache-2.0. Pytest is a testing tool; private generated programs and task data retain the scope above.

The native variation suite also uses the existing host Rust 1.96.0 toolchain, Cargo 1.96.0 and rustup 1.29.0. No compiler or third-party crate was installed. Complete installed Rust compiler/standard-library copyright notices and Cargo MIT/Apache/third-party texts are in `system/rust-toolchain/` and `system/cargo/`; pinned upstream rustup texts and provenance are in `system/rustup/`. Their main terms are Apache-2.0 OR MIT, with bundled component terms preserved separately. `collect_licenses.py` now inventories these tools offline and checks their versions and reviewed rustup hashes. Evaluation projects use only the Rust standard library and `cargo --offline`.

The llama.cpp source candidate is pinned in `docs/upstreams.json`. Its main MIT text and all shipped files whose names identify license/copyright/notices are archived with relative paths; that initial checkout used Picchio, while current production uses llama.cpp. No new model, hosted service or Python package is introduced by this source checkout.

The existing host CMake3.30.0 is used only for the isolated llama.cpp candidate build. Its reviewed upstream BSD copyright text and available installed LGPL notice are preserved under `system/cmake-3.30.0/`, with version/source/hashes in provenance. This inventories the direct host tool and available installed notices, not every transitive OS dependency.

The nativeMXFP4 GPT-OSS-20B reference format is now the local serving format under qualification, under Apache2. OriginalLICENSE/USAGE_POLICY preserved in `models/gpt-oss-20b-native-mxfp4/`; source/format revision andSHA arein `docs/llama-reference-model-source.json`. llama.cpp remainsMIT withbundlednotices, while the originaladapter/integrationcode remainsApache2. Picchio/Colibri/convertedweights arepreserved. No cloudAI ornewPythonpackage isinstalled. Earlier source-only notes above describe the initial checkout phase.

## Isolated Pi comparison

Pi1.1.0 (`@earendil-works/pi-coding-agent`, MIT) is installed under `vendor/pi-runtime`, with npm lifecycle scripts disabled. It is a comparison candidate, not the production agent. [All 121 installed npm packages](pi/DEPENDENCIES.md), exact lock, full shipped notices, bundled legal comments and upstream supplements are archived in `pi/`. Transitive terms include their own MIT, Apache, BSD, ISC and other declarations; Tiny Dancer Apache-2.0 does not replace them. The proxy-agent-negotiate package omits a package-specific notice; the inventory records its declared MIT terms and a supplemental notice from the same upstream project/author, with that limitation explicit.

The expanded inventory contains 523 archived evidence files (including package metadata/lock, not all license texts),45 Python distributions,29 direct host dependencies and121 installed npm packages. `scripts/collect_licenses.py --check` also checks the Pi lock, installed metadata and preserved notice hashes. No hosted provider is configured.

## GPT-OSS chat template adaptation

The original model template and the modified agent template under `app/templates/` are Apache-2.0. [Provenance and exact hashes](../docs/native-template-provenance.json), the [original model license](models/gpt-oss-20b-original/LICENSE), and the [modification notice](../NOTICE) are preserved. The adaptation retains later developer instructions and unfinished analysis; it introduces no new dependency.

The optional local diagnostic feedback preparation, observer and controls are original Tiny Dancer Apache-2.0, using existing Python/HTTPX and the normal local agent. No additional package/model/framework was installed. Copies of upstream source retain their existing terms; generated review artifacts and task data are not automatically covered by the project software license. Research links are recorded in docs/OPEN_SOURCE_RESEARCH.md.

The optional SSD model cache, copy/verification helpers and storage controls are original Apache-2.0 code using existing dependencies. Each cache bundle preserves the exact GPT-OSS model LICENSE and USAGE_POLICY alongside the byte-identical weights and source/hash manifest. The canonical license archive and original model remain on GameDrive. No model conversion, new dependency or license change is involved.

## GitHub publication checks

The GitHub-only source/publication workflow uses the MIT-licensed `actions/checkout` and `actions/setup-python` actions. Exact upstream license texts and source/commit/hash records are archived in [github-actions/](github-actions/provenance.json). Workflow references are pinned to those full commits. These build-service dependencies are separate from the local application inventory and introduce no hosted inference or local runtime package. The export script and its tests are original Apache-2.0 project code.
