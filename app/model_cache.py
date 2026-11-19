# ==============================================================================
# app/model_cache.py - optional verified copy of the model on faster storage
#
# Role in the app: app/llama_session.py calls select_model() every time it
# starts the native server to decide which GGUF file to load. The copy in the
# project (models/gpt-oss-20b-native-mxfp4) is always the authority; an
# optional cache directory (config.json "model_cache") may hold an identical
# copy on a faster disk. scripts/cache_native_model.py calls install_cache() to
# create it. See docs/MODEL_CACHE.md.
#
# Design decisions: the cache is only used when it is byte-identical (size plus
# SHA-256 equal to the pinned identity in docs/llama-reference-model-source.json)
# and its manifest/notices match; any doubt silently falls back to the original
# with a recorded reason. The original is never modified or deleted. A new bundle
# is staged in a hidden temp folder, fsynced, made read-only and published with a
# single rename so a crash cannot leave a half-valid cache.
#
# Tests: tests/test_model_cache.py.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0

"""Optional identical local model cache; the project copy remains authoritative."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import time

# Location of the authoritative copy, relative to the project root.
MODEL_DIRECTORY = 'models/gpt-oss-20b-native-mxfp4'
MODEL_NAME = 'gpt-oss-20b-MXFP4.gguf'
# License/usage files that must travel with (and match) any model copy.
NOTICES = ('LICENSE', 'USAGE_POLICY')
# 8 MiB read size: large enough for disk throughput, small enough for a low
# memory footprint while hashing a multi-GB file.
CHUNK_BYTES = 8 * 1024 * 1024
# Per-process memo of (file fingerprint, sha) already hashed, so the multi-
# second SHA-256 is not repeated on every model start.
_verified = {}


def identity(root):
    """Read the pinned identity (size, SHA-256, repo, revision) of the original model.

    Returns:
        (path_to_original, expected_dict).
    Raises:
        ValueError: the source record is incomplete (not downloaded, wrong file
        name, bad digest, or LFS oid disagreeing with the digest).
    """
    data = json.loads((root / 'docs/llama-reference-model-source.json').read_text())
    candidate = data['candidate'][0]
    digest = data['download_sha256']
    if (data.get('downloaded') is not True or candidate['path'] != MODEL_NAME or
            type(candidate['size']) is not int or candidate['size'] <= 0 or
            not isinstance(digest, str) or len(digest) != 64 or
            any(c not in '0123456789abcdef' for c in digest) or
            candidate.get('lfs', {}).get('oid') != digest):
        raise ValueError('Original model identity is incomplete')
    return root / MODEL_DIRECTORY / MODEL_NAME, {
        'sha256': digest, 'size': candidate['size'],
        'repo': data['repo'], 'revision': data['revision'], 'name': MODEL_NAME}


def cache_directory(root, config):
    """Resolve the cache folder from config or the XDG default.

    Order: config model_cache.directory (relative paths are under the project
    root), else $XDG_CACHE_HOME/tiny-dancer/models, else ~/.cache/tiny-dancer/models.

    Raises:
        ValueError: malformed settings.
    """
    options = config.get('model_cache', {})
    if not isinstance(options, dict):
        raise ValueError('Model cache settings must be an object')
    configured = options.get('directory')
    if configured:
        if not isinstance(configured, str):
            raise ValueError('Model cache directory must be a path string')
        directory = Path(configured).expanduser()
        if not directory.is_absolute():
            directory = root / directory
    else:
        base = os.environ.get('XDG_CACHE_HOME')
        directory = (Path(base) if base and Path(base).is_absolute() else Path.home() / '.cache') / 'tiny-dancer/models'
    return directory.resolve()


def fingerprint(path):
    """Cheap identity of a file on disk: device, inode, size, mtime and ctime (ns).

    Uses lstat and rejects symlinks/non-regular files so the verified file is
    the file that will be loaded. A changed fingerprint means re-hash.
    """
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('Model must be a regular file, without a symlink')
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def verify_file(path, expected, *, memoize=True):
    """Hash on first use in each process, and again after any file identity change.

    Args:
        path: file to verify.
        expected: dict with 'size' and 'sha256'.
        memoize: set False to force a fresh hash (used after copying).
    Raises:
        ValueError: wrong size, file modified while hashing, or digest mismatch.
    """
    before = fingerprint(path)
    if before[2] != expected['size']:
        raise ValueError('Cached model size does not match the original')
    key = str(path)
    receipt = (before, expected['sha256'])
    if memoize and _verified.get(key) == receipt:
        return
    digest = hashlib.sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda: file.read(CHUNK_BYTES), b''):
            digest.update(chunk)
    # Guards against the file changing mid-hash, which would make the digest
    # describe neither version.
    if fingerprint(path) != before:
        raise ValueError('Model changed during verification')
    if digest.hexdigest() != expected['sha256']:
        raise ValueError('Cached model SHA-256 does not match the original')
    if memoize:
        _verified[key] = receipt


def verified_bundle(root, config, expected):
    """Return the path of a cache bundle proven identical to the original.

    Checks, in order: directory is not a symlink, manifest names this project as
    owner and matches the expected model, license notices equal the originals,
    and the model file's size and SHA-256 match.
    """
    directory = cache_directory(root, config) / expected['sha256']
    if directory.is_symlink():
        raise ValueError('Cache bundle cannot be a symlink')
    manifest = json.loads((directory / 'manifest.json').read_text())
    if not isinstance(manifest, dict) or manifest.get('owner') != 'tiny-dancer-model-cache' or manifest.get('model') != expected:
        raise ValueError('Cache provenance does not match the original model')
    for name in NOTICES:
        if (directory / name).read_bytes() != (root / MODEL_DIRECTORY / name).read_bytes():
            raise ValueError('Cached model notices do not match the original')
    path = directory / MODEL_NAME
    verify_file(path, expected)
    return path


def select_model(root, config):
    """Choose which model file to load and explain why.

    Returns:
        (path, selection) where selection records kind ('original'|'cache'),
        sha256, a human reason and verification_seconds; llama_session stores it
        in run/model-storage.json for diagnostics.
    Any cache failure is downgraded to using the original, never an error.
    """
    original, expected = identity(root)
    selection = {'kind': 'original', 'path': str(original), 'sha256': expected['sha256'],
                 'reason': 'cache disabled', 'verification_seconds': 0.0}
    options = config.get('model_cache', {})
    if not isinstance(options, dict):
        selection['reason'] = 'invalid cache settings; using original'
        return original, selection
    if options.get('enabled') is not True:
        return original, selection
    began = time.monotonic()
    try:
        path = verified_bundle(root, config, expected)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        selection['reason'] = 'cache unavailable or invalid: ' + type(exc).__name__
    else:
        selection.update(kind='cache', path=str(path), reason='identical SHA-256 verified')
    selection['verification_seconds'] = round(time.monotonic() - began, 3)
    return Path(selection['path']), selection


def install_cache(root, config, *, reserve_bytes=10 * 2**30, progress=None):
    """Publish a complete verified bundle atomically; never remove the original.

    Args:
        root: project root.
        config: loaded config.json.
        reserve_bytes: free space that must remain after copying (default 10 GiB).
        progress: optional callable(copied_bytes, total_bytes).
    Returns:
        dict describing the cache path, whether an existing bundle was reused and
        timings/free-space figures.
    Raises:
        ValueError: bad reserve, original changed, not enough space, or copy
        identity mismatch.
    """
    if type(reserve_bytes) is not int or reserve_bytes < 0:
        raise ValueError('Free-space reserve must be a nonnegative byte count')
    original, expected = identity(root)
    before = fingerprint(original)
    if before[2] != expected['size']:
        raise ValueError('Original model size changed')
    # Fail early on a missing license file instead of after a long copy.
    # Require notices before allocating a large copy.
    notices = {name: (root / MODEL_DIRECTORY / name).read_bytes() for name in NOTICES}
    base = cache_directory(root, config)
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = base / expected['sha256']
    started = time.monotonic()
    if target.exists() or target.is_symlink():
        path = verified_bundle(root, config, expected)
        return {'path': str(path), 'model': expected, 'reused': True,
                'original_unchanged': fingerprint(original) == before,
                'seconds': round(time.monotonic() - started, 3)}
    # Need the model plus the user's reserve plus 1 MiB slack for the manifest.
    free = shutil.disk_usage(base).free
    if free < expected['size'] + reserve_bytes + 1024 * 1024:
        raise ValueError('Insufficient space for model copy and requested free-space reserve')
    # Work in a hidden '.partial' sibling on the same filesystem so the final
    # rename is atomic.
    stage = Path(tempfile.mkdtemp(prefix='.' + expected['sha256'] + '-', suffix='.partial', dir=base))
    try:
        copied = 0
        digest = hashlib.sha256()
        # 'xb' refuses to overwrite; hashing while copying avoids a second full read.
        with original.open('rb') as source, (stage / MODEL_NAME).open('xb') as destination:
            for chunk in iter(lambda: source.read(CHUNK_BYTES), b''):
                destination.write(chunk)
                digest.update(chunk)
                copied += len(chunk)
                if progress:
                    progress(copied, expected['size'])
            destination.flush()
            os.fsync(destination.fileno())
        if fingerprint(original) != before or copied != expected['size'] or digest.hexdigest() != expected['sha256']:
            raise ValueError('Source changed or copied model identity mismatch')
        # Catches silent disk or copy errors that bytes-written counters cannot see.
        # Read back the destination instead of trusting only bytes passed to write().
        verify_file(stage / MODEL_NAME, expected, memoize=False)
        for name, contents in notices.items():
            (stage / name).write_bytes(contents)
        manifest = {'owner': 'tiny-dancer-model-cache', 'schema': 1, 'model': expected,
                    'source': str(original), 'notices': {
                        name: hashlib.sha256(contents).hexdigest() for name, contents in notices.items()}}
        (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        # Durability then immutability: fsync each file and make it read-only (0444).
        for file in stage.iterdir():
            with file.open('rb') as saved:
                os.fsync(saved.fileno())
            file.chmod(0o444)
        descriptor = os.open(stage, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        # Directory rename fails if the target exists and is non-empty, so a racing
        # installer cannot be overwritten.
        # rename fails on a concurrently published nonempty bundle; no existing data replaced.
        stage.rename(target)
        # fsync the parent directory so the rename itself survives power loss.
        descriptor = os.open(base, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        # Remove leftovers whenever the rename did not happen.
        if stage.exists():
            shutil.rmtree(stage)
    return {'path': str(target / MODEL_NAME), 'model': expected, 'reused': False,
            'original_unchanged': fingerprint(original) == before,
            'free_before_bytes': free, 'free_after_bytes': shutil.disk_usage(base).free,
            'reserve_bytes': reserve_bytes, 'seconds': round(time.monotonic() - started, 3)}
