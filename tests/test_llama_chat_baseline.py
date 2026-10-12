# SPDX-License-Identifier: Apache-2.0
import json
import unittest
import threading
from types import SimpleNamespace
from unittest.mock import Mock
import httpx
from openai_harmony import Message, Role, Author, TextContent
from app.engine import ModelFormatError
from scripts.llama_chat_baseline import ChatStream,chat_history,LlamaChatBaselineEngine


class LlamaChatBaselineTests(unittest.TestCase):
    def chunk(self,delta,finish=None):return {'choices':[{'index':0,'delta':delta,'finish_reason':finish}]}

    def test_fragmented_arguments_preserve_quotes_and_newlines(self):
        s=ChatStream();args=json.dumps({'command':'printf \'"\\n\'\npython -c "print(1)"'})
        s.accept(self.chunk({'reasoning_content':'private'}))
        for i,piece in enumerate((args[:15],args[15:])):
            s.accept(self.chunk({'tool_calls':[{'index':0,'function':{'name':'shell' if i==0 else '', 'arguments':piece}}]}))
        s.accept(self.chunk({},'tool_calls'));replies,reason=s.replies({'shell'})
        self.assertEqual(reason,'EOS');self.assertEqual(replies[-1].recipient,'functions.shell')
        self.assertEqual(json.loads(replies[-1].content[0].text)['command'],json.loads(args)['command'])

    def test_length_never_dispatches_partial_action(self):
        s=ChatStream();s.accept(self.chunk({'tool_calls':[{'function':{'name':'shell','arguments':'{"command":'}}]},'length'))
        self.assertEqual(s.replies({'shell'}),([], 'MAX_TOKENS'))

    def test_invalid_json_or_unknown_tool_rejected(self):
        for name,args in (('shell','{bad'),('unknown','{}'),('shell','[]')):
            s=ChatStream();s.accept(self.chunk({'tool_calls':[{'function':{'name':name,'arguments':args}}]},'tool_calls'))
            with self.assertRaises(ModelFormatError):s.replies({'shell'})

    def test_missing_terminal_receipt_rejected(self):
        s=ChatStream();s.accept(self.chunk({'content':'draft'}))
        with self.assertRaises(ModelFormatError):s.replies({'shell'})

    def test_final_channel_is_separate_from_reasoning(self):
        s=ChatStream();s.accept(self.chunk({'reasoning_content':'private','content':'answer'},'stop'))
        replies,_=s.replies({'shell'})
        self.assertEqual([m.channel for m in replies],['analysis','final'])
        self.assertEqual(replies[-1].content[0].text,'answer')

    def test_history_keeps_matching_tool_identity(self):
        messages=[Message.from_role_and_content(Role.USER,'task'),
          Message.from_role_and_content(Role.ASSISTANT,'private').with_channel('analysis'),
          Message.from_role_and_content(Role.ASSISTANT,'{"command":"pwd"}').with_channel('analysis').with_recipient('functions.shell'),
          Message(author=Author(role=Role.TOOL,name='shell'),content=[TextContent(text='{"exit_code":0}')]).with_recipient('assistant')]
        rows=chat_history([m.to_dict() for m in messages])
        self.assertEqual(rows[1]['tool_calls'][0]['id'],rows[2]['tool_call_id'])
        self.assertEqual(rows[1]['reasoning_content'],'private');self.assertNotIn('private',rows[2]['content'])

    def test_orphaned_tool_result_rejected(self):
        m=Message(author=Author(role=Role.TOOL,name='shell'),content=[TextContent(text='{}')])
        with self.assertRaises(ModelFormatError):chat_history([m.to_dict()])

    def test_adapter_requests_native_tool_grammar_and_preserves_sampling(self):
        captured=[]
        def handle(request):
            captured.append((request.url.path,json.loads(request.content)))
            frame=self.chunk({'tool_calls':[{'index':0,'function':{'name':'shell','arguments':'{"command":"pwd"}'}}]},'tool_calls')
            frame.update(usage={'prompt_tokens':30,'completion_tokens':20})
            return httpx.Response(200,text='data: '+json.dumps(frame)+'\n\ndata: [DONE]\n\n')
        client=httpx.Client(base_url='http://127.0.0.1:1',trust_env=False,transport=httpx.MockTransport(handle))
        self.addCleanup(client.close)
        engine=object.__new__(LlamaChatBaselineEngine);engine.lock=threading.Lock();engine.load=Mock()
        engine.session=SimpleNamespace(client=client);engine.config={'native_sampling_profile':'recommended'}
        engine.instructions='test';engine.definitions=[{'name':'shell','description':'Run','parameters':{'type':'object','properties':{'command':{'type':'string'}},'required':['command']}}]
        events=[]
        replies,reason=engine.generate([Message.from_role_and_content(Role.USER,'task').to_dict()],'/tmp',lambda k,v:events.append((k,v)),threading.Event())
        path,body=captured[0]
        self.assertEqual(path,'/v1/chat/completions');self.assertEqual(body['tools'][0]['function']['name'],'shell')
        self.assertEqual(body['reasoning_effort'],'medium');self.assertEqual(body['tool_choice'],'auto')
        self.assertEqual(body['temperature'],1.0);self.assertEqual(body['top_k'],0);self.assertEqual(body['min_p'],0)
        self.assertEqual(reason,'EOS');self.assertEqual(replies[-1].recipient,'functions.shell')
        self.assertEqual(events[-1][1]['completion_tokens'],20)
