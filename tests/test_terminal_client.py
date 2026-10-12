# SPDX-License-Identifier: Apache-2.0
import io
import json
from unittest.mock import patch
import unittest
import httpx
from scripts.ask import parse_options,task_options,watch


class TerminalPolicyTests(unittest.TestCase):
    def test_new_agent_work_has_no_aggregate_budget_by_default(self):
        body=task_options(parse_options(['Build','a','larger','application']))
        self.assertTrue(body['run_until_done']);self.assertIsNone(body['max_tokens'])

    def test_bounded_choice_and_explicit_reply_budget_are_preserved(self):
        body=task_options(parse_options(['--bounded','--max-tokens','1024','Build','a','program']))
        self.assertFalse(body['run_until_done']);self.assertEqual(body['max_tokens'],1024)

    def test_resume_preserves_saved_policy_unless_explicitly_changed(self):
        self.assertEqual(task_options(parse_options(['--resume-job','saved']),True),{})
        self.assertEqual(task_options(parse_options(['--resume-job','saved','--until-done']),True),{'run_until_done':True})

    def test_chat_keeps_its_existing_bounded_policy(self):
        self.assertFalse(task_options(parse_options(['--chat','Hello']))['run_until_done'])


class TerminalEventTests(unittest.TestCase):
    def event(self,number,kind,payload):return 'id: '+str(number)+'\ndata: '+json.dumps({'kind':kind,'data':payload})+'\n\n'

    def client(self,responses,status='complete'):
        self.requests=[];streams=iter(responses)
        def handler(request):
            self.requests.append(str(request.url))
            if request.url.path.endswith('/events'):
                item=next(streams)
                if isinstance(item,Exception):raise item
                return httpx.Response(200,text=item)
            if request.url.path.endswith('/progress'):return httpx.Response(200,json={'status':status})
            raise AssertionError('Unexpected full-history request: '+str(request.url))
        client=httpx.Client(base_url='http://localhost',transport=httpx.MockTransport(handler));self.addCleanup(client.close)
        return client

    def test_streams_public_answer_and_tools_without_full_history_polling(self):
        stdout=io.StringIO();stderr=io.StringIO()
        data=': heartbeat\n\n'+self.event(1,'tool_start',{'name':'read_file'})+self.event(2,'delta',{'text':'Done.'})+'event: closed\ndata: {}\n\n'
        self.assertEqual(watch(self.client([data]),'task',stdout,stderr),0)
        self.assertEqual(stdout.getvalue(),'Done.');self.assertIn('read_file',stderr.getvalue())
        self.assertEqual(len(self.requests),2)

    def test_reconnection_reuses_cursor_and_suppresses_replayed_events(self):
        stdout=io.StringIO();first=self.event(1,'delta',{'text':'first'})
        counts=iter(['running','complete']);self.requests=[];bodies=iter([first,first+self.event(2,'delta',{'text':' second'})])
        def handler(request):
            self.requests.append(str(request.url))
            return httpx.Response(200,text=next(bodies)) if request.url.path.endswith('/events') else httpx.Response(200,json={'status':next(counts)})
        with httpx.Client(base_url='http://localhost',transport=httpx.MockTransport(handler)) as client:
            self.assertEqual(watch(client,'task',stdout,io.StringIO()),0)
        self.assertEqual(stdout.getvalue(),'first second');self.assertIn('after=1',self.requests[2])

    def test_temporary_transport_failure_does_not_stop_the_task(self):
        client=self.client([httpx.ConnectError('fixture offline'),self.event(1,'delta',{'text':'Recovered'})])
        with patch('scripts.ask.time.sleep') as delay:self.assertEqual(watch(client,'task',io.StringIO(),io.StringIO()),0)
        delay.assert_called_once_with(.5)

    def test_paused_and_cancelled_are_not_reported_as_completed(self):
        for status in ('paused','cancelled'):
            with self.subTest(status=status):self.assertEqual(watch(self.client([''],status),'task',io.StringIO(),io.StringIO()),1)


if __name__=='__main__':unittest.main()
