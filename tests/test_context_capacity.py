# SPDX-License-Identifier: Apache-2.0
"""Long native prompts must retain their goal and complete action allowance."""
import threading
from types import SimpleNamespace
import unittest

from openai_harmony import Conversation, HarmonyEncodingName, Message, Role, load_harmony_encoding
from app.engine import ContextBudgetError, LocalEngine
from app.prompt_cache import ExactHistoryCache
from app.reply_continuation import continue_reply
from tests.raw_engine_fixture import legacy_raw_engine


class ContextCapacityTests(unittest.TestCase):
    def exercise(self, capacity, agent=True, maximum=2048):
        encoding = load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
        prompt = 'Create and test a Python module. Original goal marker ALPHA.\n' + ''.join(
            f'Reference record {i}: value {i * 17}, unchanged.\n' for i in range(1500)) + 'Latest requirement marker OMEGA.'
        prefix = encoding.render_conversation_for_completion(Conversation.from_messages([]), Role.ASSISTANT)
        reply = Message.from_role_and_content(Role.ASSISTANT, 'Checked.').with_channel('final')
        output = list(encoding.render_conversation(Conversation.from_messages([reply])))[len(prefix):]
        output[-1] = 200002
        calls = []

        def turn(ids, allowance, keep, on_token, **kwargs):
            calls.append({'ids': list(ids), 'allowance': allowance, 'keep': keep})
            for token in output:
                on_token(token)
            return output, 'EOS', len(ids) + len(output)

        engine = legacy_raw_engine()
        engine.encoding = encoding
        engine.config = dict(engine.config, context=capacity, backend='llama.cpp')
        engine.session = SimpleNamespace(ctx=capacity, proc=SimpleNamespace(poll=lambda: None), last_timing={}, turn=turn)
        engine.load = lambda cancel=None: None
        events = []
        history = [Message.from_role_and_content(Role.USER, prompt).to_dict()]
        return engine, history, calls, events, maximum, agent

    def generate(self, fixture):
        engine, history, calls, events, maximum, agent = fixture
        return engine.generate(history, '/mnt/GameDrive/tiny_dancer/workspace',
                               lambda kind, data: events.append((kind, data)), threading.Event(), agent, maximum)

    def test_long_agent_goal_and_latest_requirement_both_reach_native_session(self):
        fixture = self.exercise(32768)
        replies, reason = self.generate(fixture)
        engine, _, calls, events, _, _ = fixture
        text = engine.encoding.decode(calls[0]['ids'])
        self.assertIn('Original goal marker ALPHA', text)
        self.assertIn('Latest requirement marker OMEGA', text)
        self.assertGreater(len(calls[0]['ids']), 8192)
        self.assertEqual(calls[0]['allowance'], 2048)
        self.assertLess(len(calls[0]['ids']) + 2048, 32768)
        self.assertEqual(reason, 'EOS')
        self.assertEqual(replies[-1].channel, 'final')
        self.assertEqual([data['prompt_tokens'] for kind, data in events if kind == 'inference'], [len(calls[0]['ids'])])

    def test_small_context_cannot_silently_drop_a_single_large_agent_goal(self):
        fixture = self.exercise(8192)
        with self.assertRaises(ContextBudgetError):
            self.generate(fixture)
        self.assertEqual(fixture[2], [])

    def test_long_chat_preserves_the_same_user_message(self):
        fixture = self.exercise(32768, agent=False, maximum=512)
        self.generate(fixture)
        engine, _, calls, _, _, _ = fixture
        self.assertGreater(len(calls[0]['ids']), 8192)
        self.assertIn('Original goal marker ALPHA', engine.encoding.decode(calls[0]['ids']))
        self.assertIn('Latest requirement marker OMEGA', engine.encoding.decode(calls[0]['ids']))
        self.assertEqual(calls[0]['allowance'], 512)

    def test_larger_context_still_reserves_the_entire_requested_action(self):
        fixture = self.exercise(32768, maximum=24000)
        with self.assertRaises(ContextBudgetError):
            self.generate(fixture)
        self.assertEqual(fixture[2], [])

    def test_larger_context_can_retain_exact_native_prefix_without_consuming_output_reserve(self):
        cache = ExactHistoryCache()
        canonical = [11, 12]
        raw = canonical + [23] * 15000
        cache.remember(canonical, raw)
        self.assertEqual(cache.restore(canonical + [31], 8192, 4096), (canonical + [31], 0))
        restored, keep = cache.restore(canonical + [31], 32768, 4096)
        self.assertEqual(restored, raw + [31])
        self.assertEqual(keep, len(raw))
        self.assertLess(len(restored) + 4096, 32768)

    def test_long_native_reply_is_bounded_by_actual_remaining_context(self):
        calls = []
        def turn(ids, allowance, keep, callback, **kwargs):
            calls.append((allowance, keep))
            return [7] * allowance, 'MAX_TOKENS', 0
        session = SimpleNamespace(ctx=32768, last_timing={}, turn=turn)
        tokens, reason, timing = continue_reply(session, 4903, [7] * 2048, 'MAX_TOKENS', 2048, lambda token: None)
        self.assertEqual(len(tokens), 27864)
        self.assertEqual(reason, 'CONTEXT_FULL')
        self.assertEqual(timing['native_reply_chunks'], 14)
        self.assertEqual(calls[-1], (1240, 31527))
        self.assertTrue(all(allowance+keep < 32768 for allowance,keep in calls))


if __name__ == '__main__':
    unittest.main()
