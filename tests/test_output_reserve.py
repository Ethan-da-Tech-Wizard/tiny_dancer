# SPDX-License-Identifier: Apache-2.0
"""A requested complete action needs real space after its input prompt."""
import json
import threading
import unittest
from types import SimpleNamespace

from openai_harmony import Author,Conversation,HarmonyEncodingName,Message,Role,TextContent,load_harmony_encoding
from app.engine import LocalEngine,ContextBudgetError
from tests.raw_engine_fixture import legacy_raw_engine


class OutputReserveTests(unittest.TestCase):
    def setup_engine(self,first=None):
        enc=load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
        prefix=enc.render_conversation_for_completion(Conversation.from_messages([]),Role.ASSISTANT)
        final=enc.render_conversation(Conversation.from_messages([Message.from_role_and_content(Role.ASSISTANT,'Checked.').with_channel('final')]))[len(prefix):]
        calls=[]
        class Session:
            ctx=8192;proc=SimpleNamespace(poll=lambda:None);last_timing={}
            def turn(self,ids,maximum,keep,callback,temperature=0):
                calls.append({'prompt_tokens':len(ids)+keep,'maximum':maximum,'text':enc.decode(ids)})
                tokens=first if first is not None and len(calls)==1 else final
                return tokens,'RETURN',None
        engine=legacy_raw_engine();engine.session=Session();engine.encoding=enc;engine.load=lambda cancel=None:None
        return engine,enc,calls

    def tool(self,name,payload):
        return Message(author=Author.new(Role.TOOL,'functions.'+name),content=[TextContent(text=json.dumps(payload))]).with_recipient('assistant').to_dict()

    def test_rolling_history_reserves_full_action_preserving_goal_and_latest_failure(self):
        engine,enc,calls=self.setup_engine()
        goal='Repair summarize.py and run real tests. ORIGINAL_GOAL_SENTINEL'
        history=[Message.from_role_and_content(Role.USER,goal).to_dict()]
        for i in range(12):
            history.append(Message.from_role_and_content(Role.ASSISTANT,json.dumps({'path':f'source{i}.py'})).with_channel('commentary').with_recipient('functions.read_file').to_dict())
            text=''.join(f'{n}: value_{n} = '+('1234567890'*2)+'\n' for n in range(1,91))
            history.append(self.tool('read_file',{'path':f'/project/source{i}.py','text':text}))
        history.append(Message.from_role_and_content(Role.ASSISTANT,'{"commands":["pytest"]}').with_channel('commentary').with_recipient('functions.run_checks').to_dict())
        history.append(self.tool('run_checks',{'exit_code':1,'output':'FAILED LATEST_FAILURE_SENTINEL'}))
        unchanged=json.dumps(history)
        with self.assertRaises(ContextBudgetError):
            engine.generate(history,'/project',lambda *a:None,threading.Event(),True,2048,reasoning_effort='medium')
        self.assertEqual(calls,[])
        from app.agent import AgentRun
        saved=list(history)
        request=SimpleNamespace(prompt=goal,mode='agent',max_tokens=2048,run_until_done=True)
        run=AgentRun(engine,SimpleNamespace(),'/project',request,lambda:saved,
                     lambda message,role=None:saved.append(message.to_dict()),lambda *a:None,lambda *a:None,threading.Event())
        run.compact_context('Context was full.')
        engine.generate(run.prompt_history(),'/project',lambda *a:None,threading.Event(),True,2048,reasoning_effort='medium')
        self.assertEqual(calls[-1]['maximum'],2048)
        self.assertLess(calls[-1]['prompt_tokens']+2048,8192)
        self.assertIn('ORIGINAL_GOAL_SENTINEL',calls[-1]['text'])
        self.assertIn('LATEST_FAILURE_SENTINEL',calls[-1]['text'])
        self.assertEqual(json.dumps(history),unchanged)

    def test_oversized_latest_transaction_requests_recovery_before_generation(self):
        enc=load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
        prefix=enc.render_conversation_for_completion(Conversation.from_messages([]),Role.ASSISTANT)
        emitted=[Message.from_role_and_content(Role.ASSISTANT,'Consider. '*600).with_channel('analysis'),Message.from_role_and_content(Role.ASSISTANT,'{"command":"pytest"}').with_channel('commentary').with_recipient('functions.shell')]
        produced=enc.render_conversation(Conversation.from_messages(emitted))[len(prefix):]
        self.assertLess(len(produced),2048)
        engine,enc,calls=self.setup_engine(first=produced)
        history=[Message.from_role_and_content(Role.USER,'Repair summarize.py and run tests.').to_dict()]
        replies,_=engine.generate(history,'/project',lambda *a:None,threading.Event(),True,2048,reasoning_effort='medium')
        history.extend(message.to_dict() for message in replies)
        history.append(self.tool('shell',{'exit_code':1,'numbers':list(range(1800))}))
        unchanged=json.dumps(history)
        with self.assertRaises(ContextBudgetError):
            engine.generate(history,'/project',lambda *a:None,threading.Event(),True,2048,reasoning_effort='medium')
        self.assertEqual(len(calls),1)
        self.assertEqual(json.dumps(history),unchanged)

    def test_larger_learned_action_fits_after_checkpoint_with_current_source(self):
        import tempfile
        from pathlib import Path
        from app.agent import AgentRun
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'run') as folder:
            source=Path(folder)/'main.py';source.write_text('CURRENT_SOURCE_SENTINEL\n'+('value = 1234567890\n'*120))
            test=Path(folder)/'test_case.py';test.write_text('ACCEPTANCE_SOURCE_SENTINEL\n'+('assert 1 == 1\n'*70))
            goal='Repair main.py and run its tests. ORIGINAL_BIG_OUTPUT_SENTINEL'
            history=[Message.from_role_and_content(Role.USER,goal).to_dict()]
            for i in range(12):
                history.append(Message.from_role_and_content(Role.ASSISTANT,'{"path":"main.py"}').with_channel('commentary').with_recipient('functions.read_file').to_dict())
                text=''.join(f'{n}: value_{n} = '+('1234567890'*2)+'\n' for n in range(1,91))
                history.append(self.tool('read_file',{'path':str(source),'text':text}))
            history.append(Message.from_role_and_content(Role.ASSISTANT,'{"commands":["pytest"]}').with_channel('commentary').with_recipient('functions.run_checks').to_dict())
            history.append(self.tool('run_checks',{'exit_code':1,'output':'test_case.py FAILED BIG_OUTPUT_FAILURE_SENTINEL'}))
            unchanged=json.dumps(history);engine,_,calls=self.setup_engine()
            with self.assertRaises(ContextBudgetError):engine.generate(history,folder,lambda *a:None,threading.Event(),True,4096,reasoning_effort='medium')
            self.assertEqual(calls,[])
            request=SimpleNamespace(prompt=goal,mode='agent',max_tokens=None,run_until_done=True)
            saved=list(history);checkpoint={'sources':[str(source),str(test)],'generation_budget':{'requested':None,'initial':2048,'current':4096}}
            run=AgentRun(engine,SimpleNamespace(),folder,request,lambda:saved,
                         lambda m,role=None:saved.append(m.to_dict()),lambda *a:None,lambda *a:None,threading.Event(),checkpoint)
            self.assertEqual(run.current_max_tokens,4096)
            run.compact_context('Recover after a clipped larger action.')
            engine.generate(run.prompt_history(),folder,lambda *a:None,threading.Event(),True,run.current_max_tokens,reasoning_effort='medium')
            self.assertEqual(calls[-1]['maximum'],4096)
            self.assertLess(calls[-1]['prompt_tokens']+4096,8192)
            for sentinel in ('ORIGINAL_BIG_OUTPUT_SENTINEL','CURRENT_SOURCE_SENTINEL','ACCEPTANCE_SOURCE_SENTINEL','BIG_OUTPUT_FAILURE_SENTINEL'):
                self.assertIn(sentinel,calls[-1]['text'])
            self.assertEqual(json.dumps(history),unchanged)


if __name__=='__main__':unittest.main()
