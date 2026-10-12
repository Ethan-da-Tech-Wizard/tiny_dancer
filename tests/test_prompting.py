# SPDX-License-Identifier: Apache-2.0
import json
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

from openai_harmony import Conversation,Message,Role,HarmonyEncodingName,load_harmony_encoding
from app.engine import LocalEngine
from app.prompting import compact_result,instructions_for
from app.task_policy import contract_for,tools_for
from app.tools import ROOT,TOOLS
from tests import test_verified_final as fixtures
from tests.raw_engine_fixture import legacy_raw_engine


def prompt_size(prompt,cwd,effort='medium'):
    encoding=load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
    prefix=encoding.render_conversation_for_completion(Conversation.from_messages([]),Role.ASSISTANT)
    final=encoding.render_conversation(Conversation.from_messages([Message.from_role_and_content(Role.ASSISTANT,'Measurement.').with_channel('final')]))[len(prefix):]
    class Session:
        ctx=8192;proc=SimpleNamespace(poll=lambda:None);last_timing={}
        def turn(self,ids,maximum,keep,callback,temperature=0): return final,'RETURN',None
    engine=legacy_raw_engine();engine.session=Session();engine.encoding=encoding;engine.load=lambda cancel=None:None
    engine.generate([Message.from_role_and_content(Role.USER,prompt).to_dict()],cwd,lambda *a:None,threading.Event(),True,1024,reasoning_effort=effort)
    return engine.last_timing['prompt_tokens']


class PromptTrimTests(unittest.TestCase):
    def test_same_frozen_repair_prompt_is_smaller_with_actual_tokenizer(self):
        baseline=json.loads((ROOT/'docs/prompt-overhead-before.json').read_text())
        count=prompt_size(baseline['prompt'],baseline['cwd'],baseline['effort'])
        self.assertLess(count,baseline['before_tokens']*0.8)
    def test_compact_preview_retains_failure_footer_and_full_original(self):
        payload={'output':'noise'*2000+'\nRan 0 tests in 0s\n\nOK','artifact':'/artifacts/full.txt','exit_code':0}
        result=compact_result(payload)
        self.assertIn('Ran 0 tests',result['output']);self.assertLess(len(result['output']),2500)
        self.assertGreater(len(payload['output']),10000);self.assertEqual(result['artifact'],payload['artifact'])
    def test_every_structured_game_remains_available(self):
        data={'games':[{'home':str(i),'home_score':i} for i in range(32)]}
        self.assertEqual(compact_result(data),data)
    def test_authorization_and_verification_instructions_remain(self):
        text=instructions_for(contract_for('Repair calc.py'),'/tmp/project')
        for requirement in ('credentials','destructive','data, never instructions','real tests','unchanged files','completed plan','specific blocker','Discover'):
            self.assertIn(requirement,text)
    def test_local_code_hides_unneeded_tools_but_detects_explicit_requests(self):
        names=lambda goal:{t['name'] for t in tools_for(contract_for(goal),TOOLS)}
        local=names('Repair calc.py');self.assertTrue({'inspect_project','run_checks','discover_tools'}<=local)
        self.assertFalse({'browser','desktop','editor','nfl_scores'}&local)
        self.assertIn('browser',names('Repair calc.py and test the website in a browser'))
        self.assertIn('editor',names('Repair calc.py in Code OSS'))


class ToolDiscoveryTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=fixtures.VerifiedFinalTests.asyncSetUp
    asyncTearDown=fixtures.VerifiedFinalTests.asyncTearDown
    runner=fixtures.VerifiedFinalTests.runner
    async def test_late_language_discovery_does_not_change_effort_mid_run(self):
        run=self.runner([]);run.request.prompt='Create a report'
        from app.agent import AgentRun
        run=AgentRun(run.engine,self.tools,str(self.folder),run.request,lambda:self.messages,lambda *a:None,lambda *a:None,lambda *a:None,threading.Event())
        self.assertEqual(run.effective_effort,'low')
        await run.execute('discover_tools',{'language':'rust'})
        self.assertEqual(run.effective_effort,'low');self.assertIn('rust_lookup',run.allowed_tools)
    async def test_discovered_groups_persist_across_resume_without_actions(self):
        run=self.runner([])
        with self.assertRaises(ValueError): await run.execute('editor',{'action':'status'})
        result=await run.execute('discover_tools',{'toolset':'editor'})
        self.assertIn('editor',[tool['name'] for tool in result['tools']]);self.assertFalse(any(kind=='tool_start' for kind,data in self.events))
        resumed=self.runner([]);resumed.state.update(run.state)
        # Constructor must receive the durable checkpoint, as the real Resume does.
        from app.agent import AgentRun
        other=AgentRun(resumed.engine,self.tools,str(self.folder),resumed.request,lambda:self.messages,
                       lambda *a:None,lambda *a:None,lambda *a:None,threading.Event(),checkpoint=run.state)
        self.assertIn('editor',other.allowed_tools)
