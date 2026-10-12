# SPDX-License-Identifier: Apache-2.0
"""Final goal review refreshes advisory API facts without importing projects."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from app.working_memory import runtime_source_evidence
from tests.test_post_edit_checks import PostEditCheckTests


class FinalApiReviewTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=PostEditCheckTests.asyncSetUp
    asyncTearDown=PostEditCheckTests.asyncTearDown
    runner=PostEditCheckTests.runner
    prepare=PostEditCheckTests.prepare

    async def checked(self,source):
        (self.folder/'program.py').write_text('def add(a,b):return a-b\n')
        run=self.runner();await self.prepare(run)
        await run.execute('write_file',{'path':'program.py','content':source+'\ndef add(a,b):return a+b\n'})
        await run.check_after_edit();self.assertTrue(run.state['verified']);return run

    async def test_known_api_caveat_is_explicit_in_verified_final_goal_review(self):
        run=await self.checked('import os\ndef scan(root):return os.walk(root)\n')
        before=list(run.prompt_history());await run.review_completion()
        review=json.dumps(run.prompt_history()[len(before):])
        self.assertIn('os.walk',review);self.assertIn('ignored',review)
        self.assertIn('original goal',review);self.assertIn('API facts',review)
        self.assertIn('not a defect verdict',review)
        self.assertEqual(run.prompt_history()[:len(before)],before)
        self.assertIsNone(run.compacted_history);self.assertTrue(run.state['verified'])

    async def test_decimal_notes_use_same_generic_review_path(self):
        run=await self.checked('from decimal import getcontext\ngetcontext().prec=20\n')
        before=len(run.prompt_history());await run.review_completion()
        review=json.dumps(run.prompt_history()[before:]);self.assertIn('decimal',review)
        self.assertIn('arithmetic can round',review);self.assertIn('constant',review)

    async def test_unrelated_sources_and_explicit_callback_have_no_advisory_payload(self):
        for source in ('value=1\n','import os\ndef handler(error):raise error\ndef scan(root):return os.walk(root,onerror=handler)\n'):
            with self.subTest(source=source):
                run=await self.checked(source);before=len(run.prompt_history());await run.review_completion()
                review=json.dumps(run.prompt_history()[before:]);self.assertNotIn('Current source API facts',review)
                self.assertEqual(run.state['completion_reviews'],1)

    async def test_refreshed_facts_never_execute_observed_helper(self):
        run=self.runner();await self.prepare(run)
        marker=self.folder/'must-not-import-helper'
        helper='import os\nfrom pathlib import Path\nPath('+repr(str(marker))+').write_text("BAD")\nos.walk(".")\n'
        await run.execute('write_file',{'path':'helper.py','content':helper})
        await run.execute('write_file',{'path':'program.py','content':'def add(a,b):return a+b\n'})
        await run.check_after_edit();self.assertTrue(run.state['verified']);before=len(run.prompt_history())
        await run.review_completion();self.assertFalse(marker.exists())
        self.assertIn('os.walk',json.dumps(run.prompt_history()[before:]))

    async def test_repaired_source_review_does_not_replay_old_caveat(self):
        run=await self.checked('import os\ndef scan(root):return os.walk(root)\n')
        await run.review_completion();first=json.dumps(run.prompt_history()[-1]);self.assertIn('ignored',first)
        await run.execute('task_progress',{'steps':[{'title':'Check remaining goal requirement','done':False}]})
        await run.execute('write_file',{'path':'program.py','content':'import os\ndef handler(error):raise error\ndef scan(root):return os.walk(root,onerror=handler)\ndef add(a,b):return a+b\n'})
        run.state['steps'][0]['done']=True;await run.check_after_edit();self.assertTrue(run.state['verified'])
        before=len(run.prompt_history());await run.review_completion()
        self.assertEqual(run.state['completion_reviews'],2)
        self.assertNotIn('Current source API facts',json.dumps(run.prompt_history()[before:]))

    async def test_source_change_during_fact_refresh_invalidates_test_proof(self):
        run=await self.checked('import os\ndef scan(root):return os.walk(root)\n')
        def changed(cwd,sources):
            (self.folder/'program.py').write_text('import os\ndef scan(root):return os.walk(root)\ndef add(a,b):return a-b\n')
            return runtime_source_evidence(cwd,sources)
        with patch('app.agent.runtime_source_evidence',side_effect=changed):
            await run.review_completion()
        self.assertFalse(run.state['verified'])
        self.assertNotIn('auto_verification',run.state)
        self.assertNotIn('completion_reviews',run.state)


del PostEditCheckTests
