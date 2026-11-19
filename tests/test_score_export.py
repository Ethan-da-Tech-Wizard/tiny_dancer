# ==============================================================================
# Program: test_score_export.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Automated test suite verifying functional correctness, regression
#          resistance, boundary conditions, and edge cases. Automated regression and
#          functional assertion test suite verifying system stability, edge-case
#          resilience, and contract invariants. Exercises mathematical boundary
#          conditions, state graph branch coverage, and mock failure modes within
#          isolated execution fixtures. Enforces deterministic test assertions and
#          hermetic runtime lifecycle management.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
import json
import tempfile
import threading
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch

from app.agent import AgentRun
from app.deliverables import inspect_deliverables
from app.task_policy import contract_for,tools_for
from app.tools import ComputerTools,ROOT,TOOLS
from tests.test_agent import ScriptedEngine,call

PROMPT='what wer ethe nfl scores 2 sundays ago put the answers in a json in  code oss'
SCORES={'ok':True,'date':'2026-09-27','source':'https://example.com/scoreboard','game_count':2,
        'games':[{'id':'1','away':'Away A','away_score':21,'home':'Home A','home_score':14},{'id':'2','away':'Away B','away_score':10,'home':'Home B','home_score':24}]}


# ------------------------------------------------------------------------------
# ExportRoutingTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class ExportRoutingTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # test_exact_user_request_is_work_with_both_outputs: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_exact_user_request_is_work_with_both_outputs(self):
        c=contract_for(PROMPT,today=date(2026,10,10))
        self.assertEqual(c['kind'],'work');self.assertEqual(c['workflow'],'nfl_scores_export')
        self.assertEqual(c['target_date'],'2026-09-27');self.assertEqual(c['deliverables'],{'format':'json','editor':True})
        self.assertIn('editor',{t['name'] for t in tools_for(c,TOOLS)})
    # ------------------------------------------------------------------------------
    # test_plain_question_keeps_fast_answer_without_file_obligation: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_plain_question_keeps_fast_answer_without_file_obligation(self):
        c=contract_for('What were the NFL scores 2 Sundays ago?',today=date(2026,10,10))
        self.assertEqual(c['workflow'],'nfl_scores');self.assertFalse(c['deliverables'])
    # ------------------------------------------------------------------------------
    # test_extra_work_is_never_short_circuited_by_score_export: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_extra_work_is_never_short_circuited_by_score_export(self):
        for suffix in (' and build a chart',' and email it',' and upload it',' and compare both weeks'):
            self.assertIsNone(contract_for(PROMPT+suffix,today=date(2026,10,10))['workflow'])


# ------------------------------------------------------------------------------
# ScoreExportTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class ScoreExportTests(unittest.IsolatedAsyncioTestCase):
    # ------------------------------------------------------------------------------
    # asyncSetUp: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'workspace');self.folder=Path(self.temp.name);self.tools=ComputerTools();self.messages=[];self.events=[]
        self.reference=patch('app.tools.nfl_scores',AsyncMock(return_value=SCORES.copy()));self.reference.start()
        # ------------------------------------------------------------------------------
        # editor: Asynchronous Coroutine & Contract Specification
        # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
        # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
        # Failure Modes: Catches or propagates domain exceptions according to API contracts
        # ------------------------------------------------------------------------------
        async def editor(args,cwd):
            path=(Path(cwd)/args['path']).resolve();self.assertTrue(path.is_file());return {'opened':str(path)}
        self.tools.editor=editor
    # ------------------------------------------------------------------------------
    # asyncTearDown: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def asyncTearDown(self): self.reference.stop();await self.tools.close();self.temp.cleanup()
    # ------------------------------------------------------------------------------
    # runner: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def runner(self,actions):
        request=SimpleNamespace(prompt=PROMPT,mode='agent',max_tokens=512,run_until_done=True)
        return AgentRun(ScriptedEngine(actions),self.tools,str(self.folder),request,lambda:self.messages,
                        lambda m,role=None:self.messages.append(m.to_dict()),lambda k,d:self.events.append((k,d)),lambda *a:None,threading.Event())
    # ------------------------------------------------------------------------------
    # test_export_saves_all_scores_opens_that_file_and_finishes: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_export_saves_all_scores_opens_that_file_and_finishes(self):
        run=self.runner([call('nfl_scores',{'save_path':'scores.json','open_editor':True})])
        self.assertEqual(await run.run(),'complete');self.assertTrue(run.state['verified'])
        saved=json.loads((self.folder/'scores.json').read_text());self.assertEqual(saved,{k:SCORES[k] for k in ('date','source','games')})
        self.assertEqual(run.state['editor_opened'],[str(self.folder/'scores.json')])
        self.assertEqual(run.state['completion_path'],'checked_json_export')
    # ------------------------------------------------------------------------------
    # test_lookup_only_cannot_finish_missing_json: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_lookup_only_cannot_finish_missing_json(self):
        run=self.runner([]);await run.execute('nfl_scores',{})
        self.assertFalse(run.state['verified']);self.assertIn('not been saved',inspect_deliverables(run.contract,run.state)[0])
        with self.assertRaisesRegex(ValueError,'not been saved'): await run.execute('finish_task',{'summary':'Done','checks':['true']})
    # ------------------------------------------------------------------------------
    # test_saved_but_unopened_json_cannot_complete: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_saved_but_unopened_json_cannot_complete(self):
        run=self.runner([]);await run.execute('nfl_scores',{'save_path':'scores.json'})
        self.assertIn('not been opened',inspect_deliverables(run.contract,run.state)[0])
        await run.execute('editor',{'action':'open','path':'scores.json'})
        self.assertIsNone(inspect_deliverables(run.contract,run.state)[0])
    # ------------------------------------------------------------------------------
    # test_wrong_missing_duplicate_and_nonfinite_scores_rejected: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_wrong_missing_duplicate_and_nonfinite_scores_rejected(self):
        run=self.runner([]);await run.execute('nfl_scores',{'save_path':'scores.json','open_editor':True})
        correct=json.loads((self.folder/'scores.json').read_text())
        for mutation in ('wrong','missing','duplicate','bool','date','nan'):
            data=json.loads(json.dumps(correct))
            if mutation=='wrong': data['games'][0]['home_score']+=1
            elif mutation=='missing': data['games'].pop()
            elif mutation=='duplicate': data['games'][1]=data['games'][0]
            elif mutation=='bool': data['games'][0]['home_score']=True
            elif mutation=='date': data['date']='2026-10-04'
            elif mutation=='nan': data['extra']=float('nan')
            (self.folder/'scores.json').write_text(json.dumps(data))
            with self.subTest(mutation=mutation): self.assertTrue(inspect_deliverables(run.contract,run.state)[0])
    # ------------------------------------------------------------------------------
    # test_failed_editor_preserves_file_and_requires_recovery: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_failed_editor_preserves_file_and_requires_recovery(self):
        self.tools.editor=AsyncMock(side_effect=RuntimeError('Editor unavailable'))
        run=self.runner([]);result=await run.execute('nfl_scores',{'save_path':'scores.json','open_editor':True})
        self.assertTrue((self.folder/'scores.json').exists());self.assertIn('Editor unavailable',result['editor_error']);self.assertFalse(result['requested_outputs']['verified'])
    # ------------------------------------------------------------------------------
    # test_verification_commands_cannot_remove_required_output_then_finish: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_verification_commands_cannot_remove_required_output_then_finish(self):
        run=self.runner([]);await run.execute('nfl_scores',{'save_path':'scores.json','open_editor':True})
        result=await run.execute('finish_task',{'summary':'Done','checks':['rm scores.json']})
        self.assertFalse(result['verified'])
    # ------------------------------------------------------------------------------
    # test_invalid_export_options_fail_before_fetch: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_invalid_export_options_fail_before_fetch(self):
        for args in ({'open_editor':True},{'save_path':'scores.txt'}):
            with self.assertRaises(ValueError): await self.tools.execute('nfl_scores',args,str(self.folder))
