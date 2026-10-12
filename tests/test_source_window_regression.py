# SPDX-License-Identifier: Apache-2.0
import tempfile
from pathlib import Path
import unittest

from app.prompting import compact_result
from app.baseline_preview import baseline_preview
from app.working_memory import checkpoint_evidence


def source():
    lines=[f'value_{i} = "'+('x'*35)+'"\n' for i in range(100)]
    lines[65]='updated_value = previous_value + input_value\n'
    return ''.join(lines)


class SourceWindowRegressionTests(unittest.TestCase):
    def test_numbered_five_kilobyte_source_keeps_middle_complete(self):
        text=''.join(f'{i}: {line}' for i,line in enumerate(source().splitlines(True),1))
        self.assertGreater(len(text),4000);self.assertLess(len(text),6000)
        data={'path':'/project/main.py','text':text}
        self.assertEqual(compact_result(data)['text'],text)
        self.assertEqual(data['text'],text)

    def test_inspection_preserves_five_kilobyte_implementation(self):
        text=source();data={'files':[{'path':'/project/main.py','text':text}]}
        preview=compact_result(data)
        self.assertEqual(preview['files'][0]['text'],text)

    def test_omitted_baseline_tests_do_not_consume_source_budget(self):
        text=source();data={'path':'/project','files':[
            {'path':'/project/test_main.py','text':'t'*8000},
            {'path':'/project/main.py','text':text}]}
        preview=baseline_preview('inspect_project',data)
        self.assertNotIn('text',preview['files'][0])
        self.assertEqual(preview['files'][1]['text'],text)
        self.assertEqual(data['files'][0]['text'],'t'*8000)

    def test_checkpoint_keeps_updated_moderate_source_in_existing_budget(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root/'run') as folder:
            p=Path(folder)/'main.py';p.write_text(source())
            evidence=checkpoint_evidence([('apply_patch',{'path':str(p)})],folder,[],source_budget=6000)
            self.assertEqual(evidence['source_snapshots'][0]['text'],source())
            self.assertLessEqual(sum(len(r.get('text','')) for r in evidence['source_snapshots']),6000)

    def test_real_inspection_does_not_let_tests_crowd_out_implementation(self):
        import asyncio
        from app.batching import inspect_project
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root/'run') as folder:
            p=Path(folder);(p/'main.py').write_text(source())
            (p/'test_main.py').write_text('import unittest\n'+('# padding '*1000)+'\n')
            result=asyncio.run(inspect_project({},folder,p/'artifacts'))
            shown={Path(r['path']).name:r for r in baseline_preview('inspect_project',result)['files']}
            self.assertEqual(shown['main.py']['text'],source())
            self.assertNotIn('text',shown['test_main.py'])
            full=__import__('json').loads((p/'artifacts'/Path(result['artifact']).name).read_text())
            self.assertIn('text',next(r for r in full['files'] if Path(r['path']).name=='test_main.py'))

    def test_optional_path_and_error_records_keep_order_and_bounded_text(self):
        files=[{'path':None,'text':'short'},None,{'error':'missing'}]
        self.assertEqual(compact_result({'path':3,'files':files})['files'],files)

    def test_complete_moderate_source_preserves_full_harmony_output_reserve(self):
        import threading
        from openai_harmony import Message,Role
        from tests.test_output_reserve import OutputReserveTests
        fixture=OutputReserveTests();engine,_,calls=fixture.setup_engine()
        text=''.join(f'{i}: {line}' for i,line in enumerate(source().splitlines(True),1))
        history=[Message.from_role_and_content(Role.USER,'Repair main.py and run relevant checks.').to_dict(),
                 Message.from_role_and_content(Role.ASSISTANT,'{"path":"main.py"}').with_channel('commentary').with_recipient('functions.read_file').to_dict(),
                 fixture.tool('read_file',{'path':'/project/main.py','text':text})]
        engine.generate(history,'/project',lambda *a:None,threading.Event(),True,4096,reasoning_effort='medium')
        self.assertEqual(calls[-1]['maximum'],4096)
        self.assertLessEqual(calls[-1]['prompt_tokens']+4096,8192)
        self.assertIn('updated_value = previous_value + input_value',calls[-1]['text'])


if __name__=='__main__':unittest.main()
