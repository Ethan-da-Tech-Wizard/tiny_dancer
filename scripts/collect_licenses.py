#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Archive installed license texts and metadata without network access."""
import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.rust_toolchain_licenses import collect_rust_entries, verify_rust_versions
from scripts.node_licenses import collect_node, verify_node

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'licenses'
HOST_ROLES = {
    'bash': 'Shell tool and launch scripts',
    'chromium': 'Browser automation; bundled notices also at chrome://credits',
    'grim': 'Desktop screenshots',
    'tesseract': 'Desktop OCR',
    'tesseract-data-eng': 'English OCR data',
    'wl-clipboard': 'Desktop clipboard typing',
    'hyprland': 'Desktop window control and keyboard shortcuts',
    'systemd': 'User service management',
    'gcc': 'Native C/CUDA builds',
    'gcc-libs': 'Compiler runtime package',
    'libstdc++': 'C++ runtime',
    'libgomp': 'OpenMP runtime',
    'make': 'Native engine builds',
    'cuda': 'Optional GPU build and runtime; NVIDIA terms',
    'nvidia-utils': 'GPU driver userspace; NVIDIA terms',
    'sqlite': 'Host database library; Python also supplies sqlite3',
    'glibc': 'Native runtime',
    'git': 'Upstream source checkout and version records',
    'uv': 'Python environment and dependency installation',
    'nodejs': 'JavaScript syntax validation; Playwright also bundles a driver',
    'xdg-utils': 'Desktop launcher opens the local workspace',
    'code': 'Code OSS editor; live display of saved agent file changes',
    'electron42': 'Installed Code OSS graphical runtime',
    'python': 'Host shell Python for coding checks; the service uses its separate virtual-environment interpreter',
}
# Explicit readings of the installed license files where metadata is absent
# or only says "BSD". Bundled subcomponent terms remain in the full copies.
FILE_EVIDENCE = {
    'jinja2': 'BSD-3-Clause',
    'mpmath': 'BSD-3-Clause',
    'sympy': 'BSD-3-Clause (main); bundled MIT notices also retained',
    'openai-harmony': 'Apache-2.0',
    'safetensors': 'Apache-2.0',
    'setuptools': 'MIT (main); bundled licenses and MPL-2.0 notices also retained',
}
HOST_COMMON_IDS = {
    'bash': ['GPL-3.0-or-later'],
    'tesseract': ['Apache-2.0'],
    'tesseract-data-eng': ['Apache-2.0'],
    'wl-clipboard': ['GPL-3.0-or-later'],
    'systemd': ['LGPL-2.1-or-later', 'CC0-1.0', 'GPL-2.0-or-later', 'MIT-0'],
    'gcc': ['GPL-3.0-or-later', 'GCC-exception-3.1', 'GFDL-1.3-or-later'],
    'gcc-libs': ['GPL-3.0-or-later', 'GCC-exception-3.1', 'GFDL-1.3-or-later'],
    'libstdc++': ['GPL-3.0-or-later', 'GCC-exception-3.1'],
    'libgomp': ['GPL-3.0-or-later', 'GCC-exception-3.1'],
    'make': ['GPL-3.0-or-later'],
    'glibc': ['GPL-2.0-or-later', 'LGPL-2.1-or-later'],
    'git': ['GPL-2.0-only'],
    'python': ['PSF-2.0'],
}
COMMON_FALLBACKS = {
    'MIT-0': Path('/usr/share/licenses/systemd/MIT-0.txt'),
    'GCC-exception-3.1': Path('/usr/share/licenses/gcc/RUNTIME.LIBRARY.EXCEPTION'),
}


def normalized(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def archive(source, destination):
    source = Path(source)
    destination = ROOT / destination
    if not source.is_file():
        raise RuntimeError(f'Missing license source: {source}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != destination.resolve():
        shutil.copyfile(source, destination)
    return {
        'source': str(source.resolve()),
        'path': str(destination.relative_to(ROOT)),
        'sha256': digest(destination),
        'bytes': destination.stat().st_size,
    }


def license_file(path):
    name = Path(str(path)).name.lower()
    return (name.startswith(('license', 'licence', 'copying', 'notice',
                             'thirdpartynotice', 'copyright', 'authors'))
            or name.endswith(('.license', '.licence'))) and not name.endswith(('.py', '.pyc', '.so'))


def installed():
    return {normalized(d.metadata['Name']): d for d in metadata.distributions()}


def check_lock(distributions):
    locked = {}
    for line in (ROOT / 'requirements.lock.txt').read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        name, version = line.strip().split('==', 1)
        locked[normalized(name)] = version
    for name, version in locked.items():
        if name not in distributions or distributions[name].version != version:
            raise RuntimeError(f'Locked dependency missing or changed: {name}=={version}')
    return locked


def cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def links(records):
    return ', '.join(f'[{Path(r["path"]).name}]({Path(r["path"]).relative_to("licenses").as_posix()})'
                     for r in records)


def collect():
    distributions = installed()
    locked = check_lock(distributions)
    result = {
        'schema_version': 1,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'root': str(ROOT),
        'scope': 'Original project, pinned upstreams/model, all project Python distributions, and direct host dependencies; not the entire OS dependency tree.',
        'files': [], 'components': [], 'python': [], 'system': [],
        'requirements_lock_sha256': digest(ROOT / 'requirements.lock.txt'),
    }

    def save(source, destination):
        record = archive(source, destination)
        result['files'].append(record)
        return record

    save(ROOT / 'LICENSE', 'LICENSE')
    save(ROOT / 'NOTICE', 'NOTICE')
    upstreams = json.loads((ROOT / 'docs/upstreams.json').read_text())
    for name, license_id in (('colibri', 'Apache-2.0'), ('gpt-oss', 'Apache-2.0'), ('picchio', 'MIT')):
        records = []
        for filename in ('LICENSE', 'NOTICE', 'THIRD_PARTY_NOTICES.md', 'USAGE_POLICY'):
            source = ROOT / 'vendor' / name / filename
            if source.is_file():
                records.append(save(source, f'licenses/{name}-{filename}'))
        result['components'].append({'name': name, 'license': license_id, **upstreams[name], 'files': records})
    candidate = ROOT / 'vendor/llama.cpp'
    if candidate.is_dir():
        records = [save(source, f'licenses/llama.cpp/{source.relative_to(candidate)}')
                   for source in sorted(candidate.rglob('*'))
                   if source.is_file() and '.git' not in source.parts and license_file(source)]
        if not records:
            raise RuntimeError('No llama.cpp source license texts')
        result['components'].append({'name': 'llama.cpp', 'license': 'MIT (main); bundled components retain their terms',
                                     **upstreams['llama.cpp'], 'files': records})

    model_source = json.loads((ROOT / 'docs/model-source.json').read_text())
    for folder in ('gpt-oss-20b-original', 'gpt-oss-20b-picchio-int4'):
        records = [save(ROOT / 'models' / folder / filename, f'licenses/models/{folder}/{filename}')
                   for filename in ('LICENSE', 'USAGE_POLICY')]
        result['components'].append({'name': folder, 'license': 'Apache-2.0', 'repo': model_source['repo'],
                                     'revision': model_source['revision'], 'files': records})

    native_folder = ROOT / 'models/gpt-oss-20b-native-mxfp4'
    native_source = ROOT / 'docs/llama-reference-model-source.json'
    if (native_folder / 'LICENSE').is_file() and native_source.is_file():
        source = json.loads(native_source.read_text())
        records = [save(native_folder / filename, f'licenses/models/gpt-oss-20b-native-mxfp4/{filename}')
                   for filename in ('LICENSE', 'USAGE_POLICY')]
        result['components'].append({'name': 'GPT-OSS-20B native-MXFP4 reference weights', 'license': 'Apache-2.0',
                                     'repo': source['repo'], 'revision': source['revision'],
                                     'role': 'Same original model, candidate format; not the default backend', 'files': records})

    for name, dist in sorted(distributions.items()):
        m = dist.metadata
        license_id = FILE_EVIDENCE.get(name) or m.get('License-Expression') or m.get('License')
        if not license_id:
            raise RuntimeError(f'No license evidence for {name}')
        folder = f'licenses/python/{name}-{dist.version}'
        records = [save(dist.locate_file(p), f'{folder}/{p}')
                   for p in dist.files or [] if license_file(p)]
        if not records:
            raise RuntimeError(f'No installed license texts for {name}')
        result['python'].append({
            'name': m['Name'], 'version': dist.version, 'license': license_id,
            'license_evidence': 'installed license text' if name in FILE_EVIDENCE else 'installed package metadata',
            'license_expression': m.get('License-Expression'), 'license_field': m.get('License'),
            'license_classifiers': [c for c in m.get_all('Classifier', []) if c.startswith('License')],
            'license_file_headers': m.get_all('License-File', []),
            'project_urls': m.get_all('Project-URL', []),
            'locked': name in locked, 'files': records,
        })
    rows = ['# Installed Python dependency licenses', '',
            'Generated by `scripts/collect_licenses.py` from the current virtual environment. Full copies include bundled component notices. License expressions retain their upstream `AND`/`OR` terms.', '',
            '| Distribution | Version | Recorded license | Full texts and notices |', '| --- | --- | --- | --- |']
    for entry in result['python']:
        folder = Path(entry['files'][0]['path']).parts[:3]
        target = Path(*folder).relative_to('licenses').as_posix()
        rows.append(f'| {cell(entry["name"])} | {entry["version"]} | {cell(entry["license"])} | [{len(entry["files"])} files]({target}/) |')
    (ARCHIVE / 'PYTHON_DEPENDENCIES.md').write_text('\n'.join(rows) + '\n')

    base = Path(sys.base_prefix)
    python_record = save(base / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'LICENSE.txt',
                         'licenses/system/python-runtime/LICENSE.txt')
    result['system'].append({'name': 'Python interpreter', 'version': sys.version.split()[0],
                             'license': 'PSF-2.0 with historical and incorporated-component notices',
                             'role': 'Project virtual environment interpreter', 'source': str(base), 'files': [python_record]})
    cmake_provenance = ROOT / 'licenses/system/cmake-3.30.0/provenance.json'
    if cmake_provenance.is_file():
        provenance = json.loads(cmake_provenance.read_text())
        version = subprocess.run([provenance['binary'], '--version'], capture_output=True, text=True, check=True).stdout.splitlines()[0]
        if version != 'cmake version ' + provenance['version']:
            raise RuntimeError('Reviewed CMake version changed')
        source = ROOT / 'licenses/system/cmake-3.30.0/Copyright.txt'
        if digest(source) != provenance['license_text_sha256']:
            raise RuntimeError('Reviewed CMake copyright text changed')
        records = [save(source, 'licenses/system/cmake-3.30.0/Copyright.txt')]
        notices = Path('/home/ethan/.local/share/cmake-3.30/Licenses')
        records += [save(item, f'licenses/system/cmake-3.30.0/installed/{item.relative_to(notices)}')
                    for item in sorted(notices.rglob('*')) if item.is_file()]
        result['system'].append({'name': 'CMake', 'version': provenance['version'],
                                 'license': 'BSD-3-Clause (main); available bundled notices retained',
                                 'role': provenance['role'], 'source': provenance['copyright_source'], 'files': records})

    for package, role in HOST_ROLES.items():
        query = subprocess.run(['pacman', '-Qi', package], capture_output=True, text=True, check=True)
        fields = {}
        for line in query.stdout.splitlines():
            if ':' in line and not line.startswith(' '):
                key, value = line.split(':', 1)
                fields[key.strip()] = value.strip()
        directory = Path('/usr/share/licenses') / package
        records = [save(p, f'licenses/system/{package}/{p.relative_to(directory)}')
                   for p in sorted(directory.rglob('*')) if p.is_file()]
        common = []
        for identifier in HOST_COMMON_IDS.get(package, []):
            source = Path('/usr/share/licenses/spdx') / f'{identifier}.txt'
            if not source.is_file():
                source = COMMON_FALLBACKS.get(identifier, source)
            destination = f'licenses/common/{identifier}.txt'
            existing = next((r for r in result['files'] if r['path'] == destination), None)
            common.append(existing or save(source, destination))
        if package == 'cuda':
            records.extend(save(Path('/opt/cuda') / filename, f'licenses/system/cuda/toolkit-{filename}')
                           for filename in ('LICENSE', 'EULA.txt'))
        result['system'].append({'name': package, 'version': fields['Version'],
                                 'license': fields['Licenses'], 'license_evidence': 'installed pacman package metadata',
                                 'url': fields['URL'], 'role': role, 'files': records, 'common_texts': common})
    result['system'].extend(collect_rust_entries(ROOT, save))
    rows = ['# Direct host dependency licenses', '',
            'Generated from the actual Python interpreter, installed Arch package metadata and the existing rustup-managed Rust toolchain. Complete installed Rust/Cargo notices and tagged rustup license texts are preserved. Host tools and their transitive OS dependencies retain their own terms. Common SPDX texts supplement package-specific notices. This table covers the direct tools used by Tiny Dancer, not every package on the computer.', '',
            'CUDA ships both a newer `toolkit-LICENSE` and an older `toolkit-EULA.txt`; the package README refers to EULA.txt. Both installed files are preserved without resolving that upstream discrepancy. Chromium component notices are also available at `chrome://credits`.', '',
            '| Component | Installed version | Recorded license | Role | Preserved texts |', '| --- | --- | --- | --- | --- |']
    for entry in result['system']:
        records = entry['files'] + entry.get('common_texts', [])
        rows.append(f'| {cell(entry["name"])} | {cell(entry["version"])} | {cell(entry["license"])} | {cell(entry["role"])} | {links(records)} |')
    (ARCHIVE / 'SYSTEM_DEPENDENCIES.md').write_text('\n'.join(rows) + '\n')
    result['node'] = collect_node(ROOT)
    if result['node']:
        result['files'].extend(result['node']['files'])
        result['scope'] += ' Also includes isolated Pi npm dependencies and bundled notices.'
    (ARCHIVE / 'inventory.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def verify():
    result = json.loads((ARCHIVE / 'inventory.json').read_text())
    distributions = installed()
    check_lock(distributions)
    actual = {name: d.version for name, d in distributions.items()}
    recorded = {normalized(e['name']): e['version'] for e in result['python']}
    if recorded != actual:
        raise RuntimeError('Python environment changed; refresh the license inventory')
    if result['requirements_lock_sha256'] != digest(ROOT / 'requirements.lock.txt'):
        raise RuntimeError('Dependency lock changed; refresh the license inventory')
    verify_rust_versions(result['system'])
    verify_node(ROOT)
    for record in result['files']:
        for path in (ROOT / record['path'], Path(record['source'])):
            if not path.is_file() or digest(path) != record['sha256']:
                raise RuntimeError(f'License missing or changed: {path}')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify recorded files and the current environment without writing')
    args = parser.parse_args()
    snapshot = verify() if args.check else collect()
    print(f'{"Verified" if args.check else "Archived"} {len(snapshot["files"])} texts; '
          f'{len(snapshot["python"])} Python distributions; {len(snapshot["system"])} direct host dependencies.')
