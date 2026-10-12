# SPDX-License-Identifier: Apache-2.0
"""Offline inventory of the already installed rustup-managed Rust toolchain."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def tool_version(name):
    return subprocess.check_output([name,'--version'],text=True,stderr=subprocess.DEVNULL,timeout=10).split()[1]


def collect_rust_entries(root,save):
    root=Path(root)
    if not any(shutil.which(name) for name in ('rustc','cargo','rustup')):return []
    if not all(shutil.which(name) for name in ('rustc','cargo','rustup')):raise RuntimeError('Incomplete Rust toolchain; cannot inventory accurately')
    sysroot=Path(subprocess.check_output(['rustc','--print','sysroot'],text=True,timeout=10).strip())
    docs=sysroot/'share/doc'
    rust=[save(docs/'rust'/name,'licenses/system/rust-toolchain/'+name) for name in ('COPYRIGHT.html','COPYRIGHT-library.html')]
    cargo=[save(docs/'cargo'/name,'licenses/system/cargo/'+name) for name in ('LICENSE-MIT','LICENSE-APACHE','LICENSE-THIRD-PARTY')]
    provenance=json.loads((root/'licenses/system/rustup/upstream-source.json').read_text())
    if tool_version('rustup')!=provenance['version']:raise RuntimeError('rustup changed; review and preserve licenses for the installed version')
    rustup=[]
    for entry in provenance['files']:
        path=root/entry['path']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:raise RuntimeError('Pinned rustup license differs from reviewed upstream source')
        rustup.append(save(path,entry['path']))
    common={'license':'Apache-2.0 OR MIT; bundled components retain their own terms','license_evidence':'installed complete copyright notices and Cargo licenses; tagged upstream rustup texts'}
    return [dict(common,name='rustc/toolchain',version=tool_version('rustc'),role='Existing host Rust compiler and standard library; native Rust task checks',source=str(sysroot),files=rust),
            dict(common,name='cargo',version=tool_version('cargo'),role='Existing host Cargo build/test tool; offline standard-library-only tasks',source=str(sysroot/'bin/cargo'),files=cargo),
            dict(common,name='rustup',version=provenance['version'],role='Existing Rust toolchain manager and compiler/build shims',source=str(Path(shutil.which('rustup')).resolve()),files=rustup,upstream=provenance)]


def verify_rust_versions(entries):
    for entry in entries:
        command={'rustc/toolchain':'rustc','cargo':'cargo','rustup':'rustup'}.get(entry['name'])
        if command and tool_version(command)!=entry['version']:raise RuntimeError('Rust tool version changed; refresh the license inventory: '+command)
