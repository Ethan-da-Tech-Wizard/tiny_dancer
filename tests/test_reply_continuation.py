# SPDX-License-Identifier: Apache-2.0
import json
from types import SimpleNamespace
import threading
import unittest

import httpx
from openai_harmony import Conversation,Message,Role,load_harmony_encoding,HarmonyEncodingName
from app.engine import LocalEngine,text_of_message
from app.llama_session import LlamaReferenceSession
from app.task_policy import contract_for
from app.reply_continuation import continue_reply
from tests.raw_engine_fixture import legacy_raw_engine


class NativeContinuationTests(unittest.TestCase):
    def engine(self,reply,auto=True,agent=True,profile='greedy',backend='llama.cpp'):
        encoding=load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
        prefix=list(encoding.render_conversation_for_completion(Conversation.from_messages([]),Role.ASSISTANT))
        output=list(encoding.render_conversation(Conversation.from_messages(reply)))[len(prefix):]
        if reply[-1].channel=='final' and not reply[-1].recipient: output[-1]=200002
        cut=len(output)//2+1;parts=[output[:cut],output[cut:]]
        self.requests=[]
        def handle(request):
            self.requests.append(json.loads(request.content))
            tokens=parts.pop(0)
            event={'tokens':tokens,'stop':True,'stop_type':'limit' if parts else 'eos',
                   'timings':{'prompt_ms':10,'predicted_ms':20,'prompt_n':1,'predicted_n':len(tokens)}}
            return httpx.Response(200,text='data: '+json.dumps(event)+'\n\n',headers={'content-type':'text/event-stream'})
        session=object.__new__(LlamaReferenceSession);session.ctx=8192;session.tokens=[];session.last_timing={}
        session.proc=SimpleNamespace(poll=lambda:None,kill=lambda:None)
        session.client=httpx.Client(base_url='http://127.0.0.1:1',transport=httpx.MockTransport(handle));self.addCleanup(session.client.close)
        engine=legacy_raw_engine();engine.encoding=encoding;engine.session=session
        engine.config={**engine.config,'auto_work_reply_continuation':True,'backend':backend,'native_sampling_profile':profile}
        contract=contract_for('Build a Python file.');contract['_auto_reply_continuation']=auto
        self.events=[]
        result=engine.generate([Message.from_role_and_content(Role.USER,'Build a Python file.').to_dict()],'/tmp',
            lambda kind,data:self.events.append((kind,data)),threading.Event(),agent=agent,max_tokens=cut,task_contract=contract,reasoning_effort='low')
        return engine,result,output,cut

    def test_unfinished_thought_continues_to_real_final_without_restart(self):
        reply=[Message.from_role_and_content(Role.ASSISTANT,'Private test scratch.').with_channel('analysis'),
               Message.from_role_and_content(Role.ASSISTANT,'Done.').with_channel('final')]
        engine,(messages,reason),output,cut=self.engine(reply)
        self.assertEqual(reason,'EOS');self.assertEqual([text_of_message(m) for m in messages if m.channel=='final'],['Done.'])
        self.assertEqual(self.requests[1]['prompt'],self.requests[0]['prompt']+output[:cut])
        self.assertEqual(engine.last_timing['native_reply_chunks'],2)
        self.assertAlmostEqual(engine.last_timing['decode_seconds'],.04)
        self.assertTrue(all('Private test scratch' not in str(data) for kind,data in self.events))

    def test_partial_tool_arguments_finish_before_dispatch(self):
        reply=[Message.from_role_and_content(Role.ASSISTANT,'Private test scratch.').with_channel('analysis'),
               Message.from_role_and_content(Role.ASSISTANT,'{"path":"x.txt","content":"ok"}').with_channel('commentary').with_recipient('functions.write_file')]
        _,(messages,reason),_,_=self.engine(reply)
        self.assertEqual(reason,'EOS');calls=[m for m in messages if m.recipient]
        self.assertEqual(json.loads(text_of_message(calls[0])),{'path':'x.txt','content':'ok'})

    def test_explicit_reply_allowance_stays_capped(self):
        reply=[Message.from_role_and_content(Role.ASSISTANT,'Private test scratch.').with_channel('analysis'),
               Message.from_role_and_content(Role.ASSISTANT,'Done.').with_channel('final')]
        _,(_,reason),_,_=self.engine(reply,auto=False)
        self.assertEqual(reason,'MAX_TOKENS');self.assertEqual(len(self.requests),1)

    def test_recommended_sampling_is_preserved_across_native_chunks(self):
        reply=[Message.from_role_and_content(Role.ASSISTANT,'Private test scratch.').with_channel('analysis'),
               Message.from_role_and_content(Role.ASSISTANT,'Done.').with_channel('final')]
        engine,(_,reason),_,_=self.engine(reply,profile='recommended')
        self.assertEqual(reason,'EOS');self.assertEqual(len(self.requests),2)
        for request in self.requests:
            self.assertEqual(request['temperature'],1.0)
            self.assertEqual(request['top_p'],1.0)
            self.assertEqual(request['top_k'],0)
            self.assertEqual(request['min_p'],0.0)
            self.assertEqual(request['repeat_penalty'],1.0)
        self.assertEqual(engine.last_timing['sampling_temperature'],1.0)

    def test_picchio_keeps_its_legacy_greedy_call_with_native_profile_present(self):
        reply=[Message.from_role_and_content(Role.ASSISTANT,'Done.').with_channel('final')]
        _,(_,reason),_,_=self.engine(reply,auto=False,profile='recommended',backend='picchio')
        self.assertEqual(reason,'MAX_TOKENS');self.assertEqual(len(self.requests),1)
        self.assertEqual(self.requests[0]['temperature'],0.0)

    def test_chat_does_not_expand_explicit_output(self):
        reply=[Message.from_role_and_content(Role.ASSISTANT,'Private test scratch.').with_channel('analysis'),
               Message.from_role_and_content(Role.ASSISTANT,'Done.').with_channel('final')]
        _,(_,reason),_,_=self.engine(reply,auto=True,agent=False)
        self.assertEqual(reason,'MAX_TOKENS');self.assertEqual(len(self.requests),1)


class ContinuationBoundsTests(unittest.TestCase):
    def session(self,ctx,respond):
        self.calls=[]
        def turn(ids,allowance,keep,callback,**kwargs):
            self.calls.append((ids,allowance,keep))
            return respond(allowance)
        return SimpleNamespace(ctx=ctx,last_timing={},turn=turn)

    def test_only_remaining_context_is_used(self):
        session=self.session(20,lambda allowance:([7]*allowance,'MAX_TOKENS',0))
        tokens,reason,_=continue_reply(session,15,[1,2,3],'MAX_TOKENS',10,lambda token:None)
        self.assertEqual(self.calls,[([],1,18)]);self.assertEqual(tokens,[1,2,3,7]);self.assertEqual(reason,'CONTEXT_FULL')

    def test_empty_receipt_stops_instead_of_looping(self):
        session=self.session(128,lambda allowance:([],'MAX_TOKENS',0))
        with self.assertRaisesRegex(RuntimeError,'bounded'):continue_reply(session,10,[1],'MAX_TOKENS',10,lambda token:None)
        self.assertEqual(len(self.calls),1)

    def test_continuation_stops_at_real_context_capacity(self):
        session=self.session(15,lambda allowance:([7]*allowance,'MAX_TOKENS',0))
        tokens,reason,timing=continue_reply(session,10,[1],'MAX_TOKENS',1,lambda token:None)
        self.assertEqual(len(self.calls),3);self.assertEqual(len(tokens),4);self.assertEqual(reason,'CONTEXT_FULL')
        self.assertEqual(timing['native_reply_chunks'],4)

    def test_useful_reply_can_finish_after_the_old_four_chunk_limit(self):
        parts=iter([([7]*2048,'MAX_TOKENS',0)]*4+[([8,9],'EOS',0)])
        session=self.session(32768,lambda allowance:next(parts))
        tokens,reason,timing=continue_reply(session,100,[1]*2048,'MAX_TOKENS',2048,lambda token:None)
        self.assertEqual(reason,'EOS');self.assertEqual(tokens[-2:],[8,9])
        self.assertGreater(len(tokens),8192);self.assertEqual(len(self.calls),5)
        self.assertEqual(timing['native_reply_chunks'],6)

    def test_invalid_chunk_cannot_create_a_nonprogressing_loop(self):
        session=self.session(128,lambda allowance:([7]*allowance,'MAX_TOKENS',0))
        for chunk in (0,-1,True,1.5):
            with self.subTest(chunk=chunk),self.assertRaises(ValueError):
                continue_reply(session,10,[1],'MAX_TOKENS',chunk,lambda token:None)
        self.assertEqual(self.calls,[])

    def test_oversized_receipt_is_rejected(self):
        session=self.session(128,lambda allowance:([7]*(allowance+1),'MAX_TOKENS',0))
        with self.assertRaisesRegex(RuntimeError,'bounded'):
            continue_reply(session,10,[1],'MAX_TOKENS',10,lambda token:None)

    def test_stop_interrupts_a_late_continuation(self):
        def cancelled(token):
            raise InterruptedError('User stopped the task')
        calls=[]
        def turn(ids,allowance,keep,callback,**kwargs):
            calls.append(keep);callback(7)
        session=SimpleNamespace(ctx=32768,last_timing={},turn=turn)
        with self.assertRaises(InterruptedError):
            continue_reply(session,100,[1]*10000,'MAX_TOKENS',2048,cancelled)
        self.assertEqual(calls,[10100])


if __name__=='__main__':unittest.main()
