# SPDX-License-Identifier: Apache-2.0
import asyncio
import gzip
import json
import tempfile
import threading
import time
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import httpx
from openai_harmony import Message, Role
from app.agent import AgentRun
from app.engine import LocalEngine, Cancelled
from app.facts import fetch_json, nfl_scores, validate_scores
from app.history import task_history
from app.task_policy import contract_for, tools_for
from app.tools import ComputerTools, ROOT, TOOLS
from tests.test_agent import ScriptedEngine, call

PROMPT = 'tell me all the stats of the most recent nfl sunday football list by stats i mean scores and what teams played eachother'


def scoreboard():
    return {'events': [{'id':str(n), 'date':'2026-10-04T20:25:00Z',
                       'competitions':[{'status':{'type':{'completed':True}}, 'competitors':[
                           {'homeAway':'away', 'team':{'displayName':f'Away {n}'}, 'score':str(n)},
                           {'homeAway':'home', 'team':{'displayName':f'Home {n}'}, 'score':'24'}]}]}
                      for n in (1, 2)]}


class PolicyTests(unittest.TestCase):
    def test_exact_user_question_resolves_last_completed_sunday(self):
        contract = contract_for(PROMPT, today=date(2026, 10, 10))
        self.assertEqual(contract['target_date'], '2026-10-04')
        self.assertEqual(contract['kind'], 'answer')
        self.assertEqual({t['name'] for t in tools_for(contract, TOOLS)}, {'nfl_scores','finish_task'})
        self.assertEqual(contract_for(PROMPT, today=date(2026, 10, 11))['target_date'], '2026-10-04')

    def test_player_stats_or_analysis_are_not_replaced_with_score_lookup(self):
        self.assertIsNone(contract_for('Compare player stats from the most recent NFL Sunday')['workflow'])
        self.assertEqual(contract_for('Update the app with an NFL scores panel')['kind'],'work')

    def test_new_task_does_not_inherit_old_operator_instructions(self):
        messages = [Message.from_role_and_content(Role.USER, 'Thursday'),
                    Message.from_role_and_content(Role.DEVELOPER, 'Only answer Thursday'),
                    Message.from_role_and_content(Role.USER, PROMPT)]
        rows = [{'id':n, 'harmony':json.dumps(m.to_dict())} for n,m in enumerate(messages,1)]
        selected = task_history(rows, PROMPT, 'agent', {'context_start':3})
        self.assertEqual(len(selected),1)
        self.assertIn(PROMPT, json.dumps(selected))
        self.assertNotIn('Thursday', json.dumps(selected))
        resumed = task_history(rows, PROMPT, 'agent', {'context_start':3,'context_insert_goal':True})
        self.assertEqual(Message.from_dict(resumed[0]).author.role, Role.USER)

    def test_chat_history_excludes_operator_notes_and_tools(self):
        messages = [Message.from_role_and_content(Role.USER, 'hi'),
                    Message.from_role_and_content(Role.DEVELOPER, 'operator note'),
                    call('shell',{'command':'pwd'}),
                    Message.from_role_and_content(Role.ASSISTANT,'hello').with_channel('final')]
        rows = [{'id':n, 'harmony':json.dumps(m.to_dict())} for n,m in enumerate(messages,1)]
        self.assertEqual(len(task_history(rows,'hi','chat',{})),2)

    def test_incomplete_wrong_date_and_duplicate_games_are_rejected(self):
        for mutation in ('unfinished','wrong_date','duplicate','missing_team'):
            data = scoreboard()
            if mutation == 'unfinished': data['events'][0]['competitions'][0]['status']['type']['completed'] = False
            if mutation == 'wrong_date': data['events'][0]['date'] = '2026-10-11T20:25:00Z'
            if mutation == 'duplicate': data['events'][1]['id'] = '1'
            if mutation == 'missing_team': data['events'][0]['competitions'][0]['competitors'].pop()
            with self.subTest(mutation=mutation), self.assertRaises((ValueError,KeyError)):
                validate_scores(data,'2026-10-04')


class RetrievalTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT/'run/artifacts')
    async def asyncTearDown(self): self.temp.cleanup()

    async def test_gzip_decoded_and_date_compact_and_all_games_returned(self):
        urls = []
        def handle(request):
            urls.append(str(request.url))
            return httpx.Response(200, headers={'Content-Encoding':'gzip'}, content=gzip.compress(json.dumps(scoreboard()).encode()))
        result = await nfl_scores({},self.temp.name,httpx.MockTransport(handle),today=date(2026,10,10))
        self.assertTrue(urls[0].endswith('dates=20261004'))
        self.assertEqual(result['game_count'],2)
        self.assertEqual(result['games'][1]['away_score'],2)
        self.assertTrue(Path(result['local_path']).is_file())

    async def test_http_and_application_errors_do_not_become_evidence(self):
        for status, data in ((404, {}), (200, {'code':400,'message':'Invalid date'})):
            transport = httpx.MockTransport(lambda request:httpx.Response(status,json=data))
            with self.subTest(status=status), self.assertRaises((httpx.HTTPStatusError,ValueError)):
                await fetch_json({'url':'https://example.com/data'},self.temp.name,transport)

    async def test_targeted_json_pointer_and_future_date_rejected(self):
        transport=httpx.MockTransport(lambda request:httpx.Response(200,json={'rows':[{'score':42}]}))
        result=await fetch_json({'url':'https://example.com/data','pointer':'/rows/0/score'},self.temp.name,transport)
        self.assertEqual(result['data'],42)
        with self.assertRaisesRegex(ValueError,'completed date'):
            await nfl_scores({'date':'2026-10-11'},self.temp.name,transport,today=date(2026,10,10))


class CompletionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'workspace')
        self.tools=ComputerTools(); self.events=[]; self.messages=[]
    async def asyncTearDown(self):
        await self.tools.close();self.temp.cleanup()

    def runner(self, actions, prompt='What is 6 times 7?', **options):
        engine=ScriptedEngine(actions)
        request=SimpleNamespace(mode='agent',prompt=prompt,max_tokens=512,**options)
        return AgentRun(engine,self.tools,self.temp.name,request,lambda:self.messages,
                        lambda message,role=None:self.messages.append(message.to_dict()),
                        lambda kind,data:self.events.append((kind,data)),lambda state:None,threading.Event())

    async def test_factual_answer_finishes_without_shell_loop(self):
        final=Message.from_role_and_content(Role.ASSISTANT,'42').with_channel('final')
        run=self.runner([final])
        self.assertEqual(await run.run(),'complete')
        self.assertEqual(run.state['turns'],1)
        self.assertFalse(run.state['verified'])
        self.assertEqual([data['text'] for kind,data in self.events if kind=='delta'],['42'])

    async def test_unchecked_draft_is_hidden_and_pauses_after_one_repair(self):
        final=Message.from_role_and_content(Role.ASSISTANT,'Tomorrow won today').with_channel('final')
        run=self.runner([final,final],prompt='Who won the most recent football game?')
        self.assertEqual(await run.run(),'paused')
        self.assertFalse(any(kind=='delta' for kind,data in self.events))
        self.assertEqual(run.state['turns'],2)

    async def test_draft_alongside_tool_call_is_not_saved_as_final(self):
        draft=Message.from_role_and_content(Role.ASSISTANT,'Unsupported claim').with_channel('final')
        run=self.runner([([draft,call('read_file',{'path':'missing.txt'})],'RETURN')],max_turns=1)
        self.assertEqual(await run.run(),'paused')
        self.assertNotIn('Unsupported claim',json.dumps(self.messages))

    async def test_checked_score_data_published_once_without_second_inference(self):
        async def execute(name,args,cwd):
            data=scoreboard()
            for event in data['events']: event['date']=run.contract['target_date']+'T20:25:00Z'
            games=validate_scores(data,run.contract['target_date'])
            return {'ok':True,'date':run.contract['target_date'],'games':games,'game_count':len(games),
                    'source':'https://example.com/scoreboard','artifact':'saved.json'}
        run=self.runner([call('nfl_scores',{})],prompt=PROMPT)
        run.tools.execute=execute
        self.assertEqual(await run.run(),'complete')
        self.assertTrue(run.state['verified'])
        self.assertIn('Away 2 2',run.state['summary'])
        self.assertEqual(run.state['turns'],1)

    async def test_turn_budget_saves_progress_without_restarting_loop(self):
        run=self.runner([call('read_file',{'path':'missing.txt'})]*3,max_turns=2)
        self.assertEqual(await run.run(),'paused')
        self.assertIn('budget',run.state['next_action'])
        self.assertEqual(run.state['turns'],2)

    async def test_inference_deadline_cancels_engine_and_pauses(self):
        released=threading.Event()
        run=self.runner([],max_seconds=0.02)
        def generate(*args,**kwargs):
            released.wait(1)
            raise Cancelled()
        run.engine.generate=generate
        run.engine.cancel=released.set
        self.assertEqual(await run.run(),'paused')
        self.assertTrue(released.is_set())
        self.assertIn('Time budget',run.state['next_action'])


class IdleTests(unittest.TestCase):
    def test_idle_unload_releases_session_but_cannot_interrupt_locked_inference(self):
        engine=LocalEngine()
        killed=[]
        engine.session=SimpleNamespace(proc=SimpleNamespace(poll=lambda:None,kill=lambda:killed.append(True),wait=lambda timeout:None))
        engine.last_activity=time.monotonic()-301
        engine.lock.acquire()
        self.assertFalse(engine.unload_if_idle(300))
        engine.lock.release()
        self.assertTrue(engine.unload_if_idle(300))
        self.assertIsNone(engine.session)
        self.assertEqual(killed,[True])
