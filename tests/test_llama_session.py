# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

import httpx

from app.llama_session import LlamaReferenceSession


def frame(tokens,stop=False,stop_type='eos',**extra):
    return {'tokens':tokens,'stop':stop,'stop_type':stop_type,**extra}


class SessionTests(unittest.TestCase):
    def session(self,replies):
        self.requests=[];iterator=iter(replies)
        def handle(request):
            self.requests.append(json.loads(request.content))
            events=next(iterator)
            body=''.join('data: '+json.dumps(event)+'\n\n' for event in events)
            return httpx.Response(200,text=body,headers={'content-type':'text/event-stream'})
        session=object.__new__(LlamaReferenceSession)
        session.ctx=32;session.tokens=[];session.last_timing={}
        session.client=httpx.Client(base_url='http://127.0.0.1:1',transport=httpx.MockTransport(handle),trust_env=False)
        self.addCleanup(session.client.close)
        return session

    def test_tool_call_keeps_boundary_and_actual_token_ids(self):
        session=self.session([[frame([7,200012]),frame([],True,timings={'prompt_n':2,'prompt_ms':50,'predicted_n':2,'predicted_ms':100})]])
        delivered=[];tokens,reason,_=session.turn([200006,8],8,0,delivered.append)
        self.assertEqual(tokens,delivered);self.assertEqual(tokens,[7,200012]);self.assertEqual(reason,'EOS')
        self.assertEqual(session.last_timing['prefill_seconds'],.05)
        self.assertEqual(session.last_timing['decode_tokens_per_s'],20)

    def test_analysis_boundary_continues_same_bounded_turn(self):
        session=self.session([[frame([7,200007],True)],[frame([200006,8,200002],True)]])
        delivered=[];tokens,reason,_=session.turn([1,2],7,0,delivered.append)
        self.assertEqual(tokens,[7,200007,200006,8,200002]);self.assertEqual(reason,'EOS')
        self.assertEqual(self.requests[1]['prompt'],[1,2,7,200007])
        self.assertEqual(self.requests[1]['n_predict'],5)

    def test_complete_limit_is_not_reported_as_completion(self):
        session=self.session([[frame([7,8],True,'limit')]])
        self.assertEqual(session.turn([1],2,0,lambda token:None)[1],'MAX_TOKENS')

    def test_recommended_sampling_survives_native_analysis_boundary(self):
        session=self.session([[frame([7,200007],True)],[frame([8,200002],True)]])
        session.default_temperature=1.0
        tokens,reason,_=session.turn([1,2],8,0,lambda token:None)
        self.assertEqual(tokens,[7,200007,8,200002]);self.assertEqual(reason,'EOS')
        for request in self.requests:
            self.assertEqual(request['temperature'],1.0)
            self.assertEqual(request['top_p'],1.0)
            self.assertEqual(request['top_k'],0)
            self.assertEqual(request['min_p'],0.0)
        self.assertEqual(session.last_timing['sampling_temperature'],1.0)
        self.assertEqual(session.last_timing['sampling_repeat_penalty'],1.0)

    def test_explicit_greedy_override_and_recorded_receipt_match(self):
        session=self.session([[frame([7,200002],True)]])
        session.default_temperature=1.0
        session.turn([1,2],8,0,lambda token:None,temperature=0.0)
        self.assertEqual(self.requests[0]['temperature'],0.0)
        self.assertEqual(session.last_timing['sampling_temperature'],0.0)
        self.assertEqual(self.requests[0]['repeat_penalty'],1.0)

    def test_final_at_exact_budget_keeps_actual_eos_receipt(self):
        session=self.session([[frame([7,200002],True,'eos')]])
        self.assertEqual(session.turn([1],2,0,lambda token:None)[1],'EOS')

    def test_tool_call_at_exact_budget_keeps_actual_eos_receipt(self):
        session=self.session([[frame([7,200012],True,'eos')]])
        self.assertEqual(session.turn([1],2,0,lambda token:None)[1],'EOS')

    def test_analysis_boundary_at_budget_remains_incomplete(self):
        session=self.session([[frame([7,200007],True,'eos')]])
        self.assertEqual(session.turn([1],2,0,lambda token:None)[1],'MAX_TOKENS')

    def test_retained_prefix_sends_exact_full_prompt(self):
        session=self.session([[frame([200002],True)]])
        session.tokens=[1,2,3,4]
        session.turn([9],2,2,lambda token:None)
        self.assertEqual(self.requests[0]['prompt'],[1,2,9])
        self.assertTrue(self.requests[0]['cache_prompt'])

    def test_stream_disconnection_cannot_become_success(self):
        session=self.session([[frame([7])]])
        with self.assertRaisesRegex(RuntimeError,'complete token receipt'):session.turn([1],3,0,lambda token:None)

    def test_silent_context_truncation_is_rejected(self):
        session=self.session([[frame([7],True,truncated=True)]])
        with self.assertRaisesRegex(RuntimeError,'truncated'):session.turn([1],3,0,lambda token:None)

    def test_server_cannot_expand_reply_budget(self):
        session=self.session([[frame([7,8,9],True)]])
        with self.assertRaisesRegex(RuntimeError,'allowance'):session.turn([1],2,0,lambda token:None)

    def test_cancellation_callback_propagates(self):
        session=self.session([[frame([7,8],True)]])
        def stop(token):raise InterruptedError('Stop')
        with self.assertRaises(InterruptedError):session.turn([1],3,0,stop)

    def test_invalid_ids_and_prefix_do_not_call_server(self):
        session=self.session([])
        for ids,keep in [([True],0),([-1],0),([201088],0),([1],1)]:
            with self.subTest(ids=ids,keep=keep),self.assertRaises(ValueError):session.turn(ids,2,keep,lambda token:None)
        self.assertFalse(self.requests)

    def test_full_output_reserve_is_checked_before_request(self):
        session=self.session([])
        with self.assertRaisesRegex(ValueError,'context'):session.turn([1]*30,3,0,lambda token:None)
        self.assertFalse(self.requests)


    def test_idle_connection_disconnect_retries_same_prompt_once(self):
        requests=[]
        def handle(request):
            requests.append(json.loads(request.content))
            if len(requests)==1:raise httpx.RemoteProtocolError('Server disconnected without sending a response.')
            return httpx.Response(200,text='data: '+json.dumps(frame([7,200002],True))+'\n\n')
        session=self.session([]);session.client.close()
        session.client=httpx.Client(base_url='http://127.0.0.1:1',transport=httpx.MockTransport(handle),trust_env=False)
        session.proc=Mock();session.proc.poll.return_value=None
        delivered=[]
        self.assertEqual(session.turn([1,2],8,0,delivered.append)[1],'EOS')
        self.assertEqual(delivered,[7,200002]);self.assertEqual(len(requests),2)
        self.assertEqual(requests[0],requests[1])

    def test_disconnect_after_tokens_never_replays_generation(self):
        requests=[]
        class BrokenStream(httpx.SyncByteStream):
            def __iter__(self):
                yield ('data: '+json.dumps(frame([7]))+'\n\n').encode()
                raise httpx.RemoteProtocolError('disconnected after partial generation')
        def handle(request):
            requests.append(request)
            return httpx.Response(200,stream=BrokenStream())
        session=self.session([]);session.client.close()
        session.client=httpx.Client(base_url='http://127.0.0.1:1',transport=httpx.MockTransport(handle),trust_env=False)
        session.proc=Mock();session.proc.poll.return_value=None;delivered=[]
        with self.assertRaises(httpx.RemoteProtocolError):session.turn([1],8,0,delivered.append)
        self.assertEqual(delivered,[7]);self.assertEqual(len(requests),1)

    def test_dead_server_disconnect_is_not_retried(self):
        requests=[]
        def handle(request):
            requests.append(request);raise httpx.RemoteProtocolError('server exited')
        session=self.session([]);session.client.close()
        session.client=httpx.Client(base_url='http://127.0.0.1:1',transport=httpx.MockTransport(handle),trust_env=False)
        session.proc=Mock();session.proc.poll.return_value=-9
        with self.assertRaises(httpx.RemoteProtocolError):session.turn([1],8,0,lambda token:None)
        self.assertEqual(len(requests),1)


if __name__=='__main__':unittest.main(verbosity=2)
