# Program: tiny_dancer - tests/test_native_chat.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Tests for native chat (exercises app.engine, app.native_chat).
# SPDX-License-Identifier: Apache-2.0
"""Tests for native chat (exercises app.engine, app.native_chat)."""
import json
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import httpx
from openai_harmony import Message,Role,Author,TextContent
from app.engine import Cancelled,ContextBudgetError,ModelFormatError
from app.native_chat import generate,chat_history


# -------- native chat tests --------
class NativeChatTests(unittest.TestCase):
    """Test group for native chat."""
    def setup_engine(self,capacity=8192,prompt_tokens=100,finish='tool_calls',cancel_on_stream=False):
        """Test helper: setup engine."""
        self.requests=[];self.events=[];self.flag=threading.Event()
        def handle(request):
            """Test helper: handle."""
            body=json.loads(request.content);self.requests.append((request.url.path,body))
            if request.url.path=='/apply-template':return httpx.Response(200,json={'prompt':'exact formatted private prompt'})
            if request.url.path=='/tokenize':return httpx.Response(200,json={'tokens':[1]*prompt_tokens})
            if cancel_on_stream:self.flag.set()
            frame={'choices':[{'index':0,'delta':{'reasoning_content':'private reasoning','tool_calls':[{'index':0,'function':{'name':'shell','arguments':'{"command":"pwd"}'}}]},'finish_reason':finish}],
                'timings':{'predicted_n':32,'predicted_ms':100,'prompt_n':20,'prompt_ms':50},'usage':{'prompt_tokens':prompt_tokens,'completion_tokens':32},
                'prompt_progress':{'total':prompt_tokens,'cache':80,'processed':prompt_tokens}}
            return httpx.Response(200,text='data: '+json.dumps(frame)+'\n\ndata: [DONE]\n\n')
        client=httpx.Client(base_url='http://127.0.0.1:1',trust_env=False,transport=httpx.MockTransport(handle));self.addCleanup(client.close)
        config={'backend':'llama.cpp','native_sampling_profile':'recommended','auto_work_reply_continuation':True}
        return SimpleNamespace(lock=threading.Lock(),load=Mock(),cancel=Mock(),config=config,
            session=SimpleNamespace(client=client,ctx=capacity,proc=SimpleNamespace(poll=lambda:None)))

    def run_generation(self,engine,auto=True,budget=2048):
        """Test helper: run generation."""
        return generate(engine,[Message.from_role_and_content(Role.USER,'Create a Python app').to_dict()],'/task',
            lambda k,v:self.events.append((k,v)),self.flag,budget,
            {'kind':'work','workflow':None,'lookup_languages':['python'],'toolsets':[],'_auto_reply_continuation':auto},'medium')

    def test_auto_uses_remaining_physical_context_and_actual_progress(self):
        """Checks that auto uses remaining physical context and actual progress."""
        engine=self.setup_engine();replies,reason=self.run_generation(engine)
        request=self.requests[-1][1]
        self.assertEqual(request['max_tokens'],8192-100-1)
        self.assertTrue(request['timings_per_token']);self.assertTrue(request['return_progress'])
        self.assertEqual(request['tools'][0]['type'],'function');self.assertEqual(reason,'EOS')
        self.assertNotIn('private reasoning',json.dumps(self.events));self.assertNotIn('exact formatted private prompt',json.dumps(self.events))
        self.assertTrue(any(kind=='progress' and data['tokens']==32 for kind,data in self.events))
        self.assertEqual(engine.last_timing['cache_saved_prefill_tokens'],80)

    def test_explicit_budget_remains_explicit(self):
        """Checks that explicit budget remains explicit."""
        self.run_generation(self.setup_engine(),auto=False,budget=512)
        self.assertEqual(self.requests[-1][1]['max_tokens'],512)

    def test_context_exhaustion_recovers_before_inference(self):
        """Checks that context exhaustion recovers before inference."""
        engine=self.setup_engine(capacity=1000,prompt_tokens=800)
        with self.assertRaises(ContextBudgetError):self.run_generation(engine)
        self.assertEqual(len(self.requests),2)

    def test_incomplete_call_never_dispatches_and_reports_context_boundary(self):
        """Checks that incomplete call never dispatches and reports context boundary."""
        result=self.run_generation(self.setup_engine(finish='length'))
        self.assertEqual(result,([], 'CONTEXT_FULL'))

    def test_stop_during_stream_cancels_owned_worker(self):
        """Checks that stop during stream cancels owned worker."""
        engine=self.setup_engine(cancel_on_stream=True)
        with self.assertRaises(Cancelled):self.run_generation(engine)
        engine.cancel.assert_called_once()

    def test_checkpoint_developer_message_keeps_chronology(self):
        """Checks that checkpoint developer message keeps chronology."""
        history=[Message.from_role_and_content(Role.USER,'goal'),
          Message.from_role_and_content(Role.ASSISTANT,'private').with_channel('analysis'),
          Message.from_role_and_content(Role.DEVELOPER,'saved checkpoint')]
        rows=chat_history([m.to_dict() for m in history])
        self.assertEqual([r['role'] for r in rows],['user','assistant','developer'])
        self.assertEqual(rows[-1]['content'],'saved checkpoint')

    def test_malformed_legacy_history_uses_checkpoint_recovery(self):
        """Checks that malformed legacy history uses checkpoint recovery."""
        call=Message.from_role_and_content(Role.ASSISTANT,'{invalid').with_recipient('functions.shell')
        with self.assertRaises(ContextBudgetError):chat_history([call.to_dict()])

    def observation(self,origin,name='run_checks'):
        """Test helper: observation."""
        return Message(author=Author.new(Role.TOOL,'functions.'+name),content=[TextContent(
            text=json.dumps({'origin':origin,'exit_code':1,'output':'actual failed assertion'}))]).with_recipient('assistant')

    def test_automatic_checks_are_data_without_fabricated_model_calls(self):
        """Checks that automatic checks are data without fabricated model calls."""
        for origin in ('automatic_initial_project','automatic_post_edit'):
            rows=chat_history([Message.from_role_and_content(Role.USER,'original goal').to_dict(),
                               self.observation(origin).to_dict()])
            self.assertEqual([r['role'] for r in rows],['user','user'])
            self.assertIn('Automatic local tool observation',rows[-1]['content'])
            self.assertIn('actual failed assertion',rows[-1]['content'])
            self.assertNotIn('tool_calls',rows[-1]);self.assertNotIn('tool_call_id',rows[-1])

    def test_post_edit_observation_keeps_model_transaction_and_chronology(self):
        """Checks that post edit observation keeps model transaction and chronology."""
        call=Message.from_role_and_content(Role.ASSISTANT,'{"path":"a.py","content":"x=1"}').with_recipient('functions.write_file')
        result=Message(author=Author.new(Role.TOOL,'functions.write_file'),content=[TextContent(text='{"ok":true}')])
        history=[Message.from_role_and_content(Role.USER,'goal'),call,result,
                 self.observation('automatic_post_edit'),Message.from_role_and_content(Role.DEVELOPER,'continue')]
        rows=chat_history([m.to_dict() for m in history])
        self.assertEqual([r['role'] for r in rows],['user','assistant','tool','user','developer'])
        self.assertEqual(rows[1]['tool_calls'][0]['id'],rows[2]['tool_call_id'])

    def test_unrecognized_orphan_result_is_rejected(self):
        """Checks that unrecognized orphan result is rejected."""
        with self.assertRaises(ModelFormatError):chat_history([self.observation('unknown').to_dict()])

    def test_pending_private_text_is_not_reordered_or_promoted_into_observation(self):
        """Checks that pending private text is not reordered or promoted into observation."""
        history=[Message.from_role_and_content(Role.ASSISTANT,'private').with_channel('analysis'),
                 self.observation('automatic_post_edit')]
        rows=chat_history([m.to_dict() for m in history])
        self.assertEqual([r['role'] for r in rows],['assistant','user'])
        self.assertNotIn('private',rows[-1]['content'])
