# Direct host dependency licenses

Generated from the actual Python interpreter, installed Arch package metadata and the existing rustup-managed Rust toolchain. Complete installed Rust/Cargo notices and tagged rustup license texts are preserved. Host tools and their transitive OS dependencies retain their own terms. Common SPDX texts supplement package-specific notices. This table covers the direct tools used by Tiny Dancer, not every package on the computer.

CUDA ships both a newer `toolkit-LICENSE` and an older `toolkit-EULA.txt`; the package README refers to EULA.txt. Both installed files are preserved without resolving that upstream discrepancy. Chromium component notices are also available at `chrome://credits`.

| Component | Installed version | Recorded license | Role | Preserved texts |
| --- | --- | --- | --- | --- |
| Python interpreter | 3.12.13 | PSF-2.0 with historical and incorporated-component notices | Project virtual environment interpreter | [LICENSE.txt](system/python-runtime/LICENSE.txt) |
| CMake | 3.30.0 | BSD-3-Clause (main); available bundled notices retained | Existing host CMake; local llama.cpp candidate build, not inference runtime | [Copyright.txt](system/cmake-3.30.0/Copyright.txt), [LGPLv3.txt](system/cmake-3.30.0/installed/LGPLv3.txt) |
| bash | 5.3.20-1 | GPL-3.0-or-later | Shell tool and launch scripts | [GPL-3.0-or-later.txt](common/GPL-3.0-or-later.txt) |
| chromium | 153.0.8010.52-1 | BSD-3-Clause | Browser automation; bundled notices also at chrome://credits | [LICENSE](system/chromium/LICENSE), [LICENSE.launcher](system/chromium/LICENSE.launcher) |
| grim | 1.5.0-2 | MIT | Desktop screenshots | [LICENSE](system/grim/LICENSE) |
| tesseract | 5.5.3-1 | APACHE | Desktop OCR | [Apache-2.0.txt](common/Apache-2.0.txt) |
| tesseract-data-eng | 2:4.1.0-5 | Apache | English OCR data | [Apache-2.0.txt](common/Apache-2.0.txt) |
| wl-clipboard | 1:2.3.0-1 | GPL-3.0-or-later | Desktop clipboard typing | [GPL-3.0-or-later.txt](common/GPL-3.0-or-later.txt) |
| hyprland | 0.56.2-4 | BSD-3-Clause | Desktop window control and keyboard shortcuts | [LICENSE](system/hyprland/LICENSE) |
| systemd | 262-1 | LGPL-2.1-or-later  CC0-1.0  GPL-2.0-or-later  MIT-0 | User service management | [MIT-0.txt](system/systemd/MIT-0.txt), [LGPL-2.1-or-later.txt](common/LGPL-2.1-or-later.txt), [CC0-1.0.txt](common/CC0-1.0.txt), [GPL-2.0-or-later.txt](common/GPL-2.0-or-later.txt), [MIT-0.txt](common/MIT-0.txt) |
| gcc | 16.2.1+r23+gd564253eb6c8-1 | GPL-3.0-or-later WITH GCC-exception-3.1  GFDL-1.3-or-later | Native C/CUDA builds | [RUNTIME.LIBRARY.EXCEPTION](system/gcc/RUNTIME.LIBRARY.EXCEPTION), [GPL-3.0-or-later.txt](common/GPL-3.0-or-later.txt), [GCC-exception-3.1.txt](common/GCC-exception-3.1.txt), [GFDL-1.3-or-later.txt](common/GFDL-1.3-or-later.txt) |
| gcc-libs | 16.2.1+r23+gd564253eb6c8-1 | GPL-3.0-or-later WITH GCC-exception-3.1  GFDL-1.3-or-later | Compiler runtime package | [RUNTIME.LIBRARY.EXCEPTION](system/gcc-libs/RUNTIME.LIBRARY.EXCEPTION), [GPL-3.0-or-later.txt](common/GPL-3.0-or-later.txt), [GCC-exception-3.1.txt](common/GCC-exception-3.1.txt), [GFDL-1.3-or-later.txt](common/GFDL-1.3-or-later.txt) |
| libstdc++ | 16.2.1+r23+gd564253eb6c8-1 | GPL-3.0-or-later WITH GCC-exception-3.1  GFDL-1.3-or-later | C++ runtime | [RUNTIME.LIBRARY.EXCEPTION](system/libstdc++/RUNTIME.LIBRARY.EXCEPTION), [GPL-3.0-or-later.txt](common/GPL-3.0-or-later.txt), [GCC-exception-3.1.txt](common/GCC-exception-3.1.txt) |
| libgomp | 16.2.1+r23+gd564253eb6c8-1 | GPL-3.0-or-later WITH GCC-exception-3.1  GFDL-1.3-or-later | OpenMP runtime | [RUNTIME.LIBRARY.EXCEPTION](system/libgomp/RUNTIME.LIBRARY.EXCEPTION), [GPL-3.0-or-later.txt](common/GPL-3.0-or-later.txt), [GCC-exception-3.1.txt](common/GCC-exception-3.1.txt) |
| make | 4.4.1-3 | GPL3 | Native engine builds | [GPL-3.0-or-later.txt](common/GPL-3.0-or-later.txt) |
| cuda | 13.4.2-1 | LicenseRef-NVIDIA-CUDA | Optional GPU build and runtime; NVIDIA terms | [EULA.txt](system/cuda/EULA.txt), [README](system/cuda/README), [toolkit-LICENSE](system/cuda/toolkit-LICENSE), [toolkit-EULA.txt](system/cuda/toolkit-EULA.txt) |
| nvidia-utils | 615.71.09-1 | LicenseRef-NVIDIA-Driver-License-Agreement | GPU driver userspace; NVIDIA terms | [LICENSE](system/nvidia-utils/LICENSE) |
| sqlite | 3.53.4-1 | LicenseRef-Sqlite | Host database library; Python also supplies sqlite3 | [license.txt](system/sqlite/license.txt) |
| glibc | 2.44+r50+g1848099f063e-1 | GPL-2.0-or-later  LGPL-2.1-or-later | Native runtime | [GPL-2.0-or-later.txt](common/GPL-2.0-or-later.txt), [LGPL-2.1-or-later.txt](common/LGPL-2.1-or-later.txt) |
| git | 2.56.0-1 | GPL-2.0-only | Upstream source checkout and version records | [GPL-2.0-only.txt](common/GPL-2.0-only.txt) |
| uv | 0.12.23-1 | MIT  Apache-2.0 | Python environment and dependency installation | [LICENSE-APACHE](system/uv/LICENSE-APACHE), [LICENSE-MIT](system/uv/LICENSE-MIT) |
| nodejs | 26.10.0-2 | MIT | JavaScript syntax validation; Playwright also bundles a driver | [LICENSE](system/nodejs/LICENSE) |
| xdg-utils | 1.2.1-2 | MIT | Desktop launcher opens the local workspace | [LICENSE](system/xdg-utils/LICENSE) |
| code | 1.138.0-1 | MIT | Code OSS editor; live display of saved agent file changes | [LICENSE](system/code/LICENSE), [ThirdPartyNotices.txt](system/code/ThirdPartyNotices.txt) |
| electron42 | 42.11.11-1 | MIT  BSD-3-Clause | Installed Code OSS graphical runtime | [LICENSE](system/electron42/LICENSE), [LICENSES.chromium.html](system/electron42/LICENSES.chromium.html) |
| python | 3.14.7-1 | PSF-2.0 | Host shell Python for coding checks; the service uses its separate virtual-environment interpreter | [PSF-2.0.txt](common/PSF-2.0.txt) |
| rustc/toolchain | 1.96.0 | Apache-2.0 OR MIT; bundled components retain their own terms | Existing host Rust compiler and standard library; native Rust task checks | [COPYRIGHT.html](system/rust-toolchain/COPYRIGHT.html), [COPYRIGHT-library.html](system/rust-toolchain/COPYRIGHT-library.html) |
| cargo | 1.96.0 | Apache-2.0 OR MIT; bundled components retain their own terms | Existing host Cargo build/test tool; offline standard-library-only tasks | [LICENSE-MIT](system/cargo/LICENSE-MIT), [LICENSE-APACHE](system/cargo/LICENSE-APACHE), [LICENSE-THIRD-PARTY](system/cargo/LICENSE-THIRD-PARTY) |
| rustup | 1.29.0 | Apache-2.0 OR MIT; bundled components retain their own terms | Existing Rust toolchain manager and compiler/build shims | [LICENSE-MIT](system/rustup/LICENSE-MIT), [LICENSE-APACHE](system/rustup/LICENSE-APACHE) |
