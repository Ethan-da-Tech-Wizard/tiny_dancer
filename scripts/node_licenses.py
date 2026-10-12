# SPDX-License-Identifier: Apache-2.0
"""Offline inventory of the isolated Pi installation and its shipped notices."""
import hashlib
import json
from pathlib import Path
import re
import shutil


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_files(folder):
    return sorted(p for p in folder.rglob('*') if p.is_file()
                  and 'node_modules' not in p.relative_to(folder).parts)


def notice_file(path):
    name = path.name.lower()
    return name.startswith(('license', 'licence', 'copying', 'notice', 'copyright', 'thirdpartynotice')) or name.endswith(('.license', '.licence'))


def collect_node(root):
    prefix = root / 'vendor/pi-runtime'
    lock = prefix / 'package-lock.json'
    if not lock.exists():
        return None
    archive = root / 'licenses/pi'
    archive.mkdir(parents=True, exist_ok=True)
    result = {'scope': 'Isolated Pi comparison; installed npm packages, supplied notices and bundled legal comments. Not production adoption.',
              'lock_sha256': digest(lock), 'packages': [], 'files': []}

    def save(source, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != target.resolve():
            shutil.copyfile(source, target)
        record = {'source': str(source.resolve()), 'path': str(target.relative_to(root)),
                  'sha256': digest(target), 'bytes': target.stat().st_size}
        result['files'].append(record)
        return record

    save(lock, archive / 'package-lock.json')
    entries = json.loads(lock.read_text())['packages']
    for relative, entry in sorted(entries.items()):
        if not relative:
            continue
        folder = prefix / relative
        meta_path = folder / 'package.json'
        if not meta_path.is_file():
            if entry.get('optional'):
                continue
            raise RuntimeError('Missing installed package: ' + relative)
        meta = json.loads(meta_path.read_text())
        if meta['version'] != entry['version']:
            raise RuntimeError('Package version differs from lock: ' + relative)
        name = meta['name']
        target = archive / 'packages' / relative.removeprefix('node_modules/')
        files = package_files(folder)
        notices = [p for p in files if notice_file(p)]
        # Some packages place their complete license in the README.
        notices += [p for p in files if p.name.lower().startswith('readme')
                    and 'Permission is hereby granted' in p.read_text(errors='replace')]
        evidence = 'Installed package notices and metadata'
        if name.startswith('@earendil-works/'):
            notices.append(archive / 'LICENSE-pi')
            evidence += '; main MIT notice from pinned upstream v1.1.0'
        if not notices:
            if name.startswith('@aws-sdk/'):
                notices = [prefix / 'node_modules/@aws-sdk/credential-provider-ini/LICENSE']
                evidence += '; Apache text from same installed SDK; package omits its own notice'
            elif name == '@esbuild/linux-x64':
                notices = [prefix / 'node_modules/esbuild/LICENSE.md']
                evidence += '; notice from matching esbuild package'
            else:
                candidate = archive / 'upstream' / name / 'LICENSE'
                if candidate.is_file():
                    notices = [candidate]
                    evidence += '; see upstream provenance, including supplemental notice limitation'
        if not notices:
            raise RuntimeError('Unresolved license notice: ' + name)
        records = [save(meta_path, target / 'package.json')]
        for p in notices:
            rel = p.relative_to(folder) if p.is_relative_to(folder) else Path('upstream') / p.name
            records.append(save(p, target / rel))
        bundled = []
        for p in files:
            if p.suffix != '.js':
                continue
            for comment in re.findall(r'/\*.*?\*/', p.read_text(errors='replace'), re.S):
                if re.search(r'@license|copyright|permission is hereby granted|licensed under', comment, re.I):
                    bundled.append(str(p.relative_to(folder)) + '\n' + comment)
        if bundled:
            legal = target / 'BUNDLED-NOTICES.txt'
            legal.write_text('\n\n'.join(dict.fromkeys(bundled)) + '\n')
            records.append(save(legal, legal))
        result['packages'].append({'name': name, 'version': meta['version'], 'license': meta.get('license'),
            'installed_path': relative, 'metadata_sha256': digest(meta_path), 'evidence': evidence, 'files': records})
    (archive / 'inventory.json').write_text(json.dumps(result, indent=2) + '\n')
    rows = ['# Pi comparison dependencies', '', result['scope'], '',
            'Full shipped notices, bundled legal comments, package metadata and the exact lock are archived. Pi is MIT; dependencies retain their individual terms. Missing package notices use documented upstream/same-project supplements; no copyright ownership is inferred.', '',
            '| Package | Version | Declared license | Archived files |', '| --- | --- | --- | --- |']
    for item in result['packages']:
        link = Path(item['files'][0]['path']).parent.relative_to('licenses/pi')
        rows.append(f"| {item['name']} | {item['version']} | {item['license']} | [notices]({link}/) |")
    (archive / 'DEPENDENCIES.md').write_text('\n'.join(rows) + '\n')
    return result


def verify_node(root):
    prefix = root / 'vendor/pi-runtime'
    if not (prefix / 'package-lock.json').exists():
        return None
    result = json.loads((root / 'licenses/pi/inventory.json').read_text())
    if digest(prefix / 'package-lock.json') != result['lock_sha256']:
        raise RuntimeError('Pi dependency lock changed')
    for item in result['packages']:
        if digest(prefix / item['installed_path'] / 'package.json') != item['metadata_sha256']:
            raise RuntimeError('Pi installed package metadata changed: ' + item['name'])
    for record in result['files']:
        for path in (Path(record['source']), root / record['path']):
            if not path.is_file() or digest(path) != record['sha256']:
                raise RuntimeError('Pi notice missing or changed: ' + str(path))
    return result
