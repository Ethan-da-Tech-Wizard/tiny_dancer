# SPDX-License-Identifier: Apache-2.0
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock

from app import model_cache as cache

ROOT = Path(__file__).resolve().parents[1]


class ModelCacheTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / 'run')
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        cache._verified.clear()
        self.addCleanup(cache._verified.clear)
        self.data = b'original model fixture\x00\xff' * 128
        self.original = self.root / cache.MODEL_DIRECTORY / cache.MODEL_NAME
        self.original.parent.mkdir(parents=True)
        self.original.write_bytes(self.data)
        for name in cache.NOTICES:
            (self.original.parent / name).write_text('preserve exact ' + name + '\n')
        digest = hashlib.sha256(self.data).hexdigest()
        (self.root / 'docs').mkdir()
        (self.root / 'docs/llama-reference-model-source.json').write_text(json.dumps({
            'downloaded': True, 'download_sha256': digest, 'repo': 'fixture', 'revision': 'pinned',
            'candidate': [{'path': cache.MODEL_NAME, 'size': len(self.data), 'lfs': {'oid': digest}}]}))
        (self.root / 'docs/native-gguf-fidelity-validation.json').write_text('{"passed":true}')
        self.config = {'model_cache': {'enabled': True, 'directory': str(self.root / 'ssd')}}

    def install(self):
        return cache.install_cache(self.root, self.config, reserve_bytes=0)

    def test_verified_copy_keeps_original_notices_and_provenance(self):
        before = cache.fingerprint(self.original)
        report = self.install()
        target = Path(report['path'])
        self.assertNotEqual(target, self.original)
        self.assertEqual(target.read_bytes(), self.data)
        self.assertEqual(cache.fingerprint(self.original), before)
        self.assertTrue(report['original_unchanged'])
        for name in cache.NOTICES:
            self.assertEqual((target.parent / name).read_bytes(), (self.original.parent / name).read_bytes())
        manifest = json.loads((target.parent / 'manifest.json').read_text())
        self.assertEqual(manifest['model']['revision'], 'pinned')
        self.assertEqual(manifest['model']['sha256'], hashlib.sha256(self.data).hexdigest())
        path, selection = cache.select_model(self.root, self.config)
        self.assertEqual(path, target)
        self.assertEqual(selection['kind'], 'cache')

    def test_disabled_or_missing_cache_falls_back_without_creating_files(self):
        for cfg in ({}, self.config):
            path, selected = cache.select_model(self.root, cfg)
            self.assertEqual(path, self.original)
            self.assertEqual(selected['kind'], 'original')
        self.assertFalse((self.root / 'ssd').exists())

    def test_corruption_same_size_invalidates_verified_receipt_and_falls_back(self):
        target = Path(self.install()['path'])
        cache.select_model(self.root, self.config)
        target.chmod(0o644)
        target.write_bytes(b'X' * len(self.data))
        path, selected = cache.select_model(self.root, self.config)
        self.assertEqual(path, self.original)
        self.assertEqual(selected['kind'], 'original')
        self.assertIn('invalid', selected['reason'])
        # Reinstall must not silently overwrite an unexpected existing bundle.
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            self.install()
        self.assertEqual(target.read_bytes(), b'X' * len(self.data))

    def test_replaced_inode_and_missing_cache_file_fall_back(self):
        target = Path(self.install()['path'])
        cache.select_model(self.root, self.config)
        replacement = target.with_suffix('.other')
        replacement.write_bytes(b'Z' * len(self.data))
        replacement.replace(target)
        self.assertEqual(cache.select_model(self.root, self.config)[0], self.original)
        target.unlink()
        self.assertEqual(cache.select_model(self.root, self.config)[0], self.original)

    def test_unchanged_file_is_hashed_once_per_process(self):
        target = Path(self.install()['path'])
        expected = cache.identity(self.root)[1]
        cache.verify_file(target, expected)
        with patch.object(cache.hashlib, 'sha256', side_effect=AssertionError('Unnecessary full model scan')):
            cache.verify_file(target, expected)
        cache._verified.clear()
        with patch.object(cache.hashlib, 'sha256', side_effect=RuntimeError('First use must hash')):
            with self.assertRaisesRegex(RuntimeError, 'First use'):
                cache.verify_file(target, expected)

    def test_insufficient_space_never_starts_or_deletes_other_files(self):
        base = self.root / 'ssd'; base.mkdir()
        unrelated = base / 'user-file'; unrelated.write_text('keep')
        with patch.object(cache.shutil, 'disk_usage', return_value=SimpleNamespace(free=10)):
            with self.assertRaisesRegex(ValueError, 'Insufficient space'):
                self.install()
        self.assertEqual(list(base.iterdir()), [unrelated])
        self.assertEqual(unrelated.read_text(), 'keep')
        self.assertEqual(self.original.read_bytes(), self.data)

    def test_interruption_never_publishes_partial_cache(self):
        def interrupt(copied, total):
            raise RuntimeError('Simulated interruption')
        with patch.object(cache, 'CHUNK_BYTES', 64):
            with self.assertRaisesRegex(RuntimeError, 'interruption'):
                cache.install_cache(self.root, self.config, reserve_bytes=0, progress=interrupt)
        self.assertEqual(list((self.root / 'ssd').iterdir()), [])
        self.assertEqual(self.original.read_bytes(), self.data)
        self.assertEqual(cache.select_model(self.root, self.config)[0], self.original)

    def test_invalid_source_hash_never_publishes_model(self):
        self.original.write_bytes(b'Y' * len(self.data))
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            self.install()
        self.assertEqual(list((self.root / 'ssd').iterdir()), [])

    def test_source_mutation_during_copy_is_rejected(self):
        def mutate(copied, total):
            if copied == 64:
                self.original.write_bytes(b'Y' * len(self.data))
        with patch.object(cache, 'CHUNK_BYTES', 64):
            with self.assertRaisesRegex(ValueError, 'Source changed'):
                cache.install_cache(self.root, self.config, reserve_bytes=0, progress=mutate)
        self.assertEqual(list((self.root / 'ssd').iterdir()), [])

    def test_notice_or_manifest_damage_falls_back(self):
        target = Path(self.install()['path'])
        notice = target.parent / 'LICENSE'; notice.chmod(0o644); notice.write_text('wrong license')
        self.assertEqual(cache.select_model(self.root, self.config)[0], self.original)
        notice.write_bytes((self.original.parent / 'LICENSE').read_bytes())
        manifest = target.parent / 'manifest.json'; manifest.chmod(0o644); manifest.write_text('{broken')
        self.assertEqual(cache.select_model(self.root, self.config)[0], self.original)

    def test_symbolic_link_to_unverified_bytes_is_rejected(self):
        target = Path(self.install()['path'])
        target.unlink(); target.symlink_to(self.original)
        self.assertEqual(cache.select_model(self.root, self.config)[0], self.original)

    def test_malformed_metadata_and_cache_settings_use_original(self):
        target = Path(self.install()['path'])
        manifest = target.parent / 'manifest.json'; manifest.chmod(0o644)
        for data in ('null', '[]', '{}'):
            manifest.write_text(data)
            self.assertEqual(cache.select_model(self.root, self.config)[0], self.original)
        for invalid in (True, None, [], 'wrong'):
            self.assertEqual(cache.select_model(self.root, {'model_cache': invalid})[0], self.original)

    def test_install_is_idempotent_and_directory_is_portable(self):
        self.config['model_cache']['directory'] = 'relative-cache'
        first = self.install()
        second = self.install()
        self.assertTrue(second['reused'])
        self.assertEqual(first['path'], second['path'])
        self.assertTrue(Path(first['path']).is_relative_to(self.root / 'relative-cache'))
        with patch.dict('os.environ', {'XDG_CACHE_HOME': str(self.root / 'xdg')}):
            self.assertEqual(cache.cache_directory(self.root, {}), self.root / 'xdg/tiny-dancer/models')

    def test_native_adapter_uses_cache_without_changing_model_parameters(self):
        from app.llama_session import LlamaReferenceSession
        cached = Path(self.install()['path'])
        binary = self.root / 'build/llama-reference/bin/llama-server'
        binary.parent.mkdir(parents=True); binary.touch()
        (self.root / 'logs').mkdir(); (self.root / 'run').mkdir()
        config = dict(self.config, context=32768, threads=8)
        process = Mock(); process.poll.return_value = None
        client = Mock(); client.get.return_value.status_code = 200
        with patch('app.llama_session.subprocess.Popen', return_value=process) as launch, \
                patch('app.llama_session.httpx.Client', return_value=client), \
                patch('app.llama_session.psutil.virtual_memory', return_value=SimpleNamespace(available=8 * 2**30)):
            for batch in (128, 512):
                current = dict(config, **({'llama_batch_size': batch, 'llama_microbatch_size': batch} if batch != 128 else {}))
                session = LlamaReferenceSession(self.root, current)
                command = launch.call_args.args[0]
                self.assertEqual(command[command.index('-m') + 1], str(cached))
                for flag, value in (('-c','32768'),('-ncmoe','16'),('-t','8'),('-b',str(batch)),('-ub',str(batch)),('--cache-type-k','f16'),('--cache-type-v','f16')):
                    self.assertEqual(command[command.index(flag) + 1], value)
                self.assertEqual(session.model_storage['kind'], 'cache')
                self.assertEqual(json.loads((self.root / 'run/model-storage.json').read_text())['kind'], 'cache')
                session.close()


if __name__ == '__main__':
    unittest.main()
