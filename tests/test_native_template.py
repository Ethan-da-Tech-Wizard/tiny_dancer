# SPDX-License-Identifier: Apache-2.0
"""Template fidelity uses synthetic text only, never model private reasoning."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from jinja2 import Environment
from app.llama_session import template_arguments

ROOT=Path(__file__).resolve().parents[1]


def render(name,messages):
    env=Environment()
    env.globals['strftime_now']=lambda _: '2026-10-12'
    def raise_exception(message):raise ValueError(message)
    env.globals['raise_exception']=raise_exception
    return env.from_string((ROOT/'app/templates'/name).read_text()).render(
        messages=messages,tools=[],builtin_tools=[],reasoning_effort='medium',add_generation_prompt=True)


class NativeTemplateTests(unittest.TestCase):
    def history(self):
        return [{'role':'system','content':'BASE_POLICY'}, {'role':'user','content':'USER_GOAL'},
            {'role':'assistant','thinking':'TOOL_REASONING','tool_calls':[{'function':{'name':'shell','arguments':{'command':'true'}}}]},
            {'role':'tool','content':'TOOL_RESULT'}]

    def test_upstream_silently_drops_late_review_but_candidate_preserves_role_and_order(self):
        messages=self.history()+[{'role':'developer','content':'REVIEW_UPDATE'}]
        old=render('gpt-oss-upstream.jinja',messages);new=render('gpt-oss-agent.jinja',messages)
        self.assertNotIn('REVIEW_UPDATE',old)
        self.assertIn('<|start|>developer<|message|>REVIEW_UPDATE<|end|>',new)
        self.assertLess(new.index('TOOL_RESULT'),new.index('REVIEW_UPDATE'))
        self.assertIn('TOOL_REASONING',new)

    def test_initial_extra_developer_and_compacted_checkpoint_are_retained(self):
        messages=[{'role':'system','content':'BASE_POLICY'}, {'role':'developer','content':'EXTRA_POLICY'},
                  {'role':'user','content':'USER_GOAL'}, {'role':'developer','content':'SAVED_CHECKPOINT'}]
        text=render('gpt-oss-agent.jinja',messages)
        positions=[text.index(marker) for marker in ('BASE_POLICY','EXTRA_POLICY','USER_GOAL','SAVED_CHECKPOINT')]
        self.assertEqual(positions,sorted(positions))

    def test_unfinished_private_analysis_is_not_an_empty_final(self):
        messages=self.history()+[{'role':'assistant','thinking':'UNFINISHED_REASONING','content':''},
                                 {'role':'developer','content':'RECOVERY_UPDATE'}]
        old=render('gpt-oss-upstream.jinja',messages);new=render('gpt-oss-agent.jinja',messages)
        self.assertNotIn('TOOL_REASONING',old);self.assertNotIn('UNFINISHED_REASONING',old)
        self.assertIn('TOOL_REASONING',new)
        self.assertIn('<|start|>assistant<|channel|>analysis<|message|>UNFINISHED_REASONING<|end|>',new)
        self.assertNotIn('<|channel|>final',new)

    def test_supported_history_is_byte_for_byte_identical(self):
        for messages in (self.history(),self.history()+[{'role':'user','content':'AUTOMATIC_OBSERVATION'}]):
            self.assertEqual(render('gpt-oss-upstream.jinja',messages),render('gpt-oss-agent.jinja',messages))

    def test_actual_completed_final_retains_upstream_reasoning_drop(self):
        messages=self.history()+[{'role':'assistant','content':'ACTUAL_FINAL'}, {'role':'user','content':'NEXT_GOAL'}]
        self.assertEqual(render('gpt-oss-upstream.jinja',messages),render('gpt-oss-agent.jinja',messages))
        self.assertNotIn('TOOL_REASONING',render('gpt-oss-agent.jinja',messages))

    def test_override_is_pinned_and_confined_to_project(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);template=root/'template.jinja';template.write_text('fixture')
            cfg={'llama_chat_template_file':'template.jinja','llama_chat_template_sha256':hashlib.sha256(template.read_bytes()).hexdigest()}
            self.assertEqual(template_arguments(root,cfg),['--jinja','--chat-template-file',str(template)])
            template.write_text('changed')
            with self.assertRaisesRegex(RuntimeError,'fingerprint'):template_arguments(root,cfg)
            cfg['llama_chat_template_file']='../outside.jinja'
            with self.assertRaisesRegex(RuntimeError,'outside'):template_arguments(root,cfg)
            self.assertEqual(template_arguments(root,{}),[])
