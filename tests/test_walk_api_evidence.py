# SPDX-License-Identifier: Apache-2.0
"""Generic standard-library facts appear only for actual relevant source calls."""
import os
from pathlib import Path
import tempfile
import unittest
from app.source_diagnostics import python_runtime_notes
from app.working_memory import runtime_source_evidence
from app.tools import ROOT


class WalkApiEvidenceTests(unittest.TestCase):
    def notes(self, source):
        return python_runtime_notes([{'path':'program.py','text':source}])

    def test_missing_callback_and_import_aliases_include_the_api_fact(self):
        for source in ('import os\nos.walk(root)\n',
                       'import os as paths\npaths.walk(root,onerror=None)\n',
                       'from os import walk as traverse\ntraverse(root)\n'):
            with self.subTest(source=source):
                notes=self.notes(source)
                self.assertEqual(notes[0]['library'],'os.walk')
                self.assertIn('ignored',notes[0]['note'])
                self.assertEqual(notes[0]['call_lines'],[2])

    def test_supplied_callback_or_unknown_options_do_not_claim_default_behavior(self):
        for call in ('os.walk(root,onerror=handler)','os.walk(root,True,handler)',
                     'os.walk(root,**options)','os.walk(*args)'):
            with self.subTest(call=call):self.assertEqual(self.notes('import os\n'+call+'\n'),[])

    def test_imports_comments_strings_and_relative_modules_do_not_trigger(self):
        for source in ('import os\nvalue="os.walk(root)"\n',
                       'import os\n# os.walk(root)\n',
                       'from .os import walk\nwalk(root)\n',
                       'walk(root)\n'):
            with self.subTest(source=source):self.assertEqual(self.notes(source),[])

    def test_observed_source_notes_do_not_execute_project_and_remain_bounded(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'run') as temporary:
            folder=Path(temporary);marker=folder/'MUST_NOT_EXECUTE';source=folder/'program.py'
            source.write_text('import os\nfrom pathlib import Path\nPath('+repr(str(marker))+').write_text("BAD")\nos.walk(".")\n')
            notes=runtime_source_evidence(folder,[str(source)])
            self.assertEqual(notes[0]['library'],'os.walk');self.assertFalse(marker.exists())
        many=[{'path':str(i)+'.py','text':'import os\nos.walk(root)\n'} for i in range(20)]
        self.assertEqual(len(python_runtime_notes(many)),8)

    def test_real_walk_default_and_callback_match_documented_behavior(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'run') as temporary:
            folder=Path(temporary);blocked=folder/'blocked';blocked.mkdir();blocked.chmod(0)
            def fail(error):raise error
            try:
                self.assertEqual(list(os.walk(blocked)),[])
                with self.assertRaises(PermissionError):list(os.walk(blocked,onerror=fail))
            finally:blocked.chmod(0o700)
