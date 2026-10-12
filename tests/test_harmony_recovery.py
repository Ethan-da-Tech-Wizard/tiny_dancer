# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest

from openai_harmony import HarmonyEncodingName,Message,Role,load_harmony_encoding
import app.engine as engine_module
from app.engine import LocalEngine
from app.agent import AgentRun
from app.tools import ComputerTools
from tests.raw_engine_fixture import legacy_raw_engine


def format_error():
    return getattr(engine_module,'ModelFormatError',RuntimeError)('Malformed model message; no tools executed.')


def call(name,args):
    return Message.from_role_and_content(Role.ASSISTANT,json.dumps(args)).with_channel('commentary').with_recipient('functions.'+name)


class NativeFormatTests(unittest.TestCase):
    def test_malformed_header_is_drained_without_killing_or_publishing(self):
        enc=load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
        tokens=enc.encode('<|start|>assistant to=functions.write_file<|constrain|>commentary<|message|>{"path":"must-not-exist.txt","content":"synthetic-private-sentinel"}<|call|>',allowed_special='all')
        class Session:
            ctx=8192
            last_timing={}
            def __init__(self):
                self.kills=0;self.received=0
                self.proc=SimpleNamespace(poll=lambda:None,kill=self.kill)
            def kill(self):self.kills+=1
            def turn(self,ids,maximum,keep,callback,**kwargs):
                for token in tokens:self.received+=1;callback(token)
                return tokens,'EOS',len(ids)+len(tokens)
        session=Session();engine=legacy_raw_engine();engine.encoding=enc;engine.session=session
        engine.load=lambda cancel=None:None;events=[]
        expected=getattr(engine_module,'ModelFormatError',type('ExpectedModelFormatError',(Exception,),{}))
        with self.assertRaises(expected):
            engine.generate([Message.from_role_and_content(Role.USER,'Create a file').to_dict()],'/tmp',lambda k,d:events.append((k,d)),threading.Event(),True,512)
        self.assertEqual(session.received,len(tokens));self.assertEqual(session.kills,0)
        self.assertEqual(engine.status,'ready');self.assertIs(engine.session,session)
        self.assertFalse(any(k=='delta' for k,d in events))
        self.assertNotIn('synthetic-private-sentinel',str(events))


class RunnerFormatTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'workspace')
        self.root=Path(self.tmp.name);self.tools=ComputerTools();self.events=[];self.messages=[]

    async def asyncTearDown(self):
        await self.tools.close();self.tmp.cleanup()

    def runner(self,actions,mode='agent'):
        iterator=iter(actions)
        class Engine:
            config={'max_tool_steps':24,'max_repeated_actions':4,'coding_preflight':False}
            calls=0
            def generate(self,*args,**kwargs):
                self.calls+=1;item=next(iterator)
                if isinstance(item,Exception):raise item
                return [item],'EOS'
        self.engine=Engine();prompt='Create and check result.txt'
        self.messages=[Message.from_role_and_content(Role.USER,prompt).to_dict()]
        request=SimpleNamespace(mode=mode,prompt=prompt,max_tokens=None,run_until_done=True)
        return AgentRun(self.engine,self.tools,str(self.root),request,lambda:self.messages,lambda m,role=None:self.messages.append(m.to_dict()),lambda k,d:self.events.append((k,d)),lambda s:None,threading.Event())

    async def test_valid_tools_finish_after_format_failure_with_files_preserved(self):
        (self.root/'prior.txt').write_text('prior work')
        run=self.runner([format_error(),call('write_file',{'path':'result.txt','content':'ok'}),call('finish_task',{'summary':'Created and checked result.txt','checks':["python -c \"from pathlib import Path; assert Path('result.txt').read_text() == 'ok'\""]})])
        self.assertEqual(await run.run(),'complete');self.assertTrue(run.state['verified'])
        self.assertEqual((self.root/'prior.txt').read_text(),'prior work')
        self.assertEqual(self.engine.calls,3)
        self.assertTrue(any(k=='model_format_error' for k,d in self.events))

    async def test_persistent_bad_headers_pause_after_three_without_tools(self):
        (self.root/'prior.txt').write_text('prior work')
        run=self.runner([format_error() for _ in range(4)])
        self.assertEqual(await run.run(),'paused');self.assertEqual(self.engine.calls,3)
        self.assertFalse(run.state['verified']);self.assertEqual(list(self.root.iterdir()),[self.root/'prior.txt'])
        self.assertEqual((self.root/'prior.txt').read_text(),'prior work')

    async def test_chat_does_not_autonomously_retry_or_execute_tools(self):
        run=self.runner([format_error()],mode='chat')
        with self.assertRaises(type(format_error())):await run.run()
        self.assertEqual(self.engine.calls,1);self.assertEqual(list(self.root.iterdir()),[])
