# Python and Rust lookup integration

The original `app/language_tools.py` implementation, language discovery/routing, tests, UI and continuation changes are **Apache-2.0**, covered by the project's [LICENSE](../LICENSE) and [NOTICE](../NOTICE).

No new package, compiler, language server, MCP server or hosted inference client was installed for these tools. They reuse the inventoried Python interpreter/standard library, HTTPX (BSD-3-Clause) and packaging (Apache-2.0 OR BSD-2-Clause). Their actual full license texts and bundled notices are retained in [PYTHON_DEPENDENCIES.md](PYTHON_DEPENDENCIES.md), [SYSTEM_DEPENDENCIES.md](SYSTEM_DEPENDENCIES.md) and [inventory.json](inventory.json). Rust manifests are parsed as data with Python's `tomllib`; these lookups do not invoke Rust/Cargo binaries or build scripts.

Read-only public reference sources:

| Source | Purpose | Primary documentation |
| --- | --- | --- |
| PyPI | Exact/latest Python package metadata, Requires-Dist, extras, Python version constraints, declared licenses | [JSON API](https://docs.pypi.org/api/json/) |
| docs.python.org | Versioned Python standard library/language docs | [Python documentation](https://docs.python.org/3/) |
| Project subdomains of readthedocs.io | Python package documentation when its URL is provided | Publisher's documentation page |
| crates.io | Crate version metadata, dependencies, optional features, target conditions, declared license | [Cargo registry API](https://doc.rust-lang.org/cargo/reference/registry-web-api.html) |
| doc.rust-lang.org | Rust standard library, book and Cargo reference | [Rust documentation](https://doc.rust-lang.org/) |
| docs.rs | Versioned published crate documentation | [About docs.rs](https://docs.rs/about) |

Lookup metadata reports the publisher's license declaration. It does not download/install a package, verify its full license terms, resolve a dependency graph, or automatically add referenced packages to the application's installed-dependency inventory. Before installing a dependency for Tiny Dancer, preserve its actual license/notices, pin it in the relevant lock and refresh/check the inventory. Project dependencies inspected for a user task retain that project's licenses.

Retrieved documentation, registry responses and user project manifests retain their original terms. The project's Apache-2.0 license does not relicense them. Saved lookup evidence is under `run/artifacts/`; timestamped TTL caches are under `cache/language-lookups/`. These private runtime records are excluded from the software license, as explained in [README.md](README.md).
