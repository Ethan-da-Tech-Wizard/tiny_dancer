# Researched projects and license scope

Recorded 2026-10-11. These references are research, separate from the [installed dependency inventory](README.md).

| Project | Primary license evidence | Use in Tiny Dancer |
| --- | --- | --- |
| Aider | [Apache-2.0 text](https://github.com/Aider-AI/aider/blob/main/LICENSE.txt) | Documentation reviewed for bounded repository maps and test feedback. Not installed; no implementation code copied. |
| mini-SWE-agent | [MIT text](https://github.com/SWE-agent/mini-swe-agent/blob/main/LICENSE.md) | Documentation reviewed for local inference, output previews and simple control flow. Not installed; no implementation code copied. |
| OpenHands root project | [MIT text](https://github.com/OpenHands/OpenHands/blob/main/LICENSE) | Public guidance reviewed for on-demand skills and repository context. No code, extension, enterprise component or dependency installed. Future component terms must be reviewed separately. |
| llama.cpp | `vendor/llama.cpp/LICENSE`, preserved upstream archive and `inventory.json` | Existing MIT-licensed local inference backend. Community paging/prefetch/cache proposals researched; those forks have not been adopted. |
| Self-Refine code repository | [Apache-2.0 text](https://github.com/madaan/self-refine/blob/main/LICENSE) | Research on bounded self-feedback and repair. No code copied or framework installed. The repository license does not determine the paper's license. |
| Agentless | [MIT text](https://github.com/OpenAutoCoder/Agentless/blob/main/LICENSE) | Research on localization, repair and independent patch validation. No code copied or framework installed; its documented cloud API setup was not adopted. |

The new expert-placement benchmark and stricter release checker are original Apache-2.0 project code using existing dependencies. Researching an idea does not install its project or change the license of its source. Any later copied code or installed dependency must have its full terms, revision and notices added to the installed inventory before use.

The experiment design, primary-source links and decisions are recorded in [OPEN_SOURCE_RESEARCH.md](../docs/OPEN_SOURCE_RESEARCH.md). No cloud model or paid inference service was added.

2026-10-12: mini-SWE-agent primary docs/current config reviewed again for a minimal local coding comparison. No framework installed or upstream implementation/prompt copied; original scripts remain Apache-2.0. Existing Harmony/HTTPX/psutil/tools licenses apply unchanged. Anthropic engineering article and Python docs inform the experiment; no runtime dependencies added.

### Pi coding agent — isolated comparison installed

Official package `@earendil-works/pi-coding-agent`1.1.0, upstream MIT, [tagged license](https://github.com/earendil-works/pi/blob/v1.1.0/LICENSE). Exact installation: `npm install --prefix /mnt/GameDrive/tiny_dancer/vendor/pi-runtime --cache /mnt/GameDrive/tiny_dancer/cache/npm-pi --ignore-scripts --no-audit --no-fund --save-exact @earendil-works/pi-coding-agent@1.1.0`. Verified registry tar SHA512 before install. Dependency lock and bundled notices: `licenses/pi/`. No production adoption or inference result yet.
