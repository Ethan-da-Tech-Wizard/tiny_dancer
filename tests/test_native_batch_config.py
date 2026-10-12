# SPDX-License-Identifier: Apache-2.0
import unittest
from app.llama_session import batch_arguments

class NativeBatchArgumentsTests(unittest.TestCase):
    def test_legacy_default_and_separate_microbatch(self):
        self.assertEqual(batch_arguments({'context':32768}), ['-b','128','-ub','128'])
        self.assertEqual(batch_arguments({'context':32768,'llama_batch_size':512}), ['-b','512','-ub','512'])
        self.assertEqual(batch_arguments({'context':32768,'llama_batch_size':1024,'llama_microbatch_size':512}), ['-b','1024','-ub','512'])

    def test_invalid_sizes_fail_before_native_execution(self):
        for batch,micro in ((True,128),(512,False),(0,0),(-1,1),(128,512),(65536,512),('512',512),(512,None)):
            with self.subTest(batch=batch,microbatch=micro),self.assertRaises(ValueError):
                batch_arguments({'context':32768,'llama_batch_size':batch,'llama_microbatch_size':micro})

    def test_other_model_configuration_is_unchanged(self):
        config={'context':32768,'threads':8,'llama_batch_size':512,'llama_microbatch_size':512,'prefill_batch':1024}
        before=dict(config);batch_arguments(config);self.assertEqual(config,before)
