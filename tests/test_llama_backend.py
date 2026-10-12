# SPDX-License-Identifier: Apache-2.0
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

from app.engine import LocalEngine


class BackendSelectionTests(unittest.TestCase):
    def engine(self,backend=None):
        engine=LocalEngine();engine.memory_issue=lambda **kwargs:None
        if backend is None:engine.config.pop('backend',None)
        else:engine.config['backend']=backend
        return engine

    @patch('app.engine.resolve_aux',return_value='vocab')
    @patch('app.engine.load_harmony_encoding',return_value=object())
    def test_picchio_remains_default(self,*ignored):
        engine=self.engine()
        with patch('app.engine.PicchioSession') as old,patch('app.llama_session.LlamaReferenceSession') as new:
            engine.load();old.assert_called_once();new.assert_not_called()

    @patch('app.engine.load_harmony_encoding',return_value=object())
    def test_native_backend_uses_same_context_and_thread_config(self,*ignored):
        for context,threads in ((8192,8),(32768,6)):
            with self.subTest(context=context,threads=threads):
                engine=self.engine('llama.cpp')
                engine.config.update(context=context,threads=threads)
                with patch('app.engine.PicchioSession') as old,patch('app.llama_session.LlamaReferenceSession') as new:
                    engine.load();new.assert_called_once();old.assert_not_called()
                    config=new.call_args.args[1]
                    self.assertEqual(config['context'],context);self.assertEqual(config['threads'],threads)
                    self.assertIn('on_process_started',new.call_args.kwargs)

    @patch('app.engine.load_harmony_encoding',return_value=object())
    def test_unknown_backend_cannot_silently_substitute_a_model(self,*ignored):
        engine=self.engine('unknown')
        with patch('app.engine.PicchioSession') as old,patch('app.llama_session.LlamaReferenceSession') as new:
            with self.assertRaisesRegex(ValueError,'Unknown'):engine.load()
            old.assert_not_called();new.assert_not_called()

    def test_idle_release_closes_owned_local_http_client(self):
        engine=self.engine('llama.cpp');proc=Mock();proc.poll.return_value=None
        client=Mock();engine.session=SimpleNamespace(proc=proc,client=client)
        engine.close();proc.kill.assert_called_once();client.close.assert_called_once()
        self.assertIsNone(engine.session)


if __name__=='__main__':unittest.main()
