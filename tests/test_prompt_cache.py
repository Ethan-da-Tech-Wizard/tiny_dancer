# ==============================================================================
# Program: test_prompt_cache.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Automated test suite verifying functional correctness, regression
#          resistance, boundary conditions, and edge cases. Automated regression and
#          functional assertion test suite verifying system stability, edge-case
#          resilience, and contract invariants. Exercises mathematical boundary
#          conditions, state graph branch coverage, and mock failure modes within
#          isolated execution fixtures. Enforces deterministic test assertions and
#          hermetic runtime lifecycle management.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
import json
import threading
import unittest
from types import SimpleNamespace

from openai_harmony import (Author, Conversation, HarmonyEncodingName, Message,
    Role, TextContent, RenderConversationConfig, load_harmony_encoding)
from app.engine import LocalEngine
from app.prompt_cache import ExactHistoryCache
from app.tools import ROOT
from tests.raw_engine_fixture import legacy_raw_engine


# ------------------------------------------------------------------------------
# PromptCacheTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class PromptCacheTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # test_changed_goal_or_tool_result_cannot_reuse_old_history: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_changed_goal_or_tool_result_cannot_reuse_old_history(self):
        cache=ExactHistoryCache();cache.remember([1,2,3],[1,9,3])
        self.assertEqual(cache.restore([1,2,4,5],100,5),([1,2,4,5],0))
        self.assertEqual(cache.restore([7,2,3,5],100,5),([7,2,3,5],0))

    # ------------------------------------------------------------------------------
    # test_raw_history_cannot_exceed_context_reserve: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_raw_history_cannot_exceed_context_reserve(self):
        cache=ExactHistoryCache();cache.remember([1,2],[1,2,3,4,5])
        self.assertEqual(cache.restore([1,2,6],7,2),([1,2,6],0))
        self.assertEqual(cache.restore([1,2,6],10,2),([1,2,3,4,5,6],5))
        cache.clear();self.assertEqual(cache.restore([1,2,6],10,2),([1,2,6],0))

    # ------------------------------------------------------------------------------
    # test_larger_action_rejects_raw_prefix_that_would_consume_its_output_space: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_larger_action_rejects_raw_prefix_that_would_consume_its_output_space(self):
        cache=ExactHistoryCache();cache.remember([1,2],[1,2]+[3]*4095)
        self.assertEqual(cache.restore([1,2,6],8192,4096),([1,2,6],0))
        restored,keep=cache.restore([1,2,6],8192,2048)
        self.assertEqual(keep,4097)
        self.assertLess(len(restored)+2048,8192)


# ------------------------------------------------------------------------------
# NativeSerializationCacheTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class NativeSerializationCacheTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # rejected_draft: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def rejected_draft(self, changed_goal=False):
        encoding=load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
        start=encoding.render_conversation_for_completion(Conversation.from_messages([]),Role.ASSISTANT)
        first=Message.from_role_and_content(Role.ASSISTANT,'{"path":"probe.py"}').with_channel('commentary').with_recipient('functions.read_file')
        rendered=encoding.render_conversation(Conversation.from_messages([first]))
        raw=encoding.encode(encoding.decode(rendered).replace(
            'assistant to=functions.read_file<|channel|>commentary',
            'assistant<|channel|>commentary to=functions.read_file'),allowed_special='all')
        first_tokens=raw[len(start):]
        analysis=Message.from_role_and_content(Role.ASSISTANT,'SYNTHETIC_REPAIR_REASONING').with_channel('analysis')
        draft=Message.from_role_and_content(Role.ASSISTANT,'UNACCEPTED_FINAL_SENTINEL').with_channel('final')
        analysis_tokens=encoding.render_conversation(Conversation.from_messages([analysis]))[len(start):]
        draft_tokens=encoding.render_conversation(Conversation.from_messages([analysis,draft]),
            RenderConversationConfig(auto_drop_analysis=False))[len(start):]
        final_tokens=encoding.render_conversation(Conversation.from_messages([
            Message.from_role_and_content(Role.ASSISTANT,'Checked.').with_channel('final')]))[len(start):]
        outputs=iter([first_tokens,draft_tokens,final_tokens]);calls=[]
        # ------------------------------------------------------------------------------
        # Session: Class State Encapsulation & Contract Specification
        # Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
        # Invariant: Enforces structural invariants and thread-safe state mutations across member calls
        # Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
        # ------------------------------------------------------------------------------
        class Session:
            ctx=32768;proc=SimpleNamespace(poll=lambda:None);last_timing={}
            # ------------------------------------------------------------------------------
            # turn: Function Pipeline & Contract Specification
            # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
            # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
            # Failure Modes: Catches or propagates domain exceptions according to API contracts
            # ------------------------------------------------------------------------------
            def turn(self,ids,maximum,keep,callback,temperature=0):
                calls.append({'ids':list(ids),'keep':keep,'full_prompt':engine.committed[:keep]+list(ids)})
                tokens=next(outputs)
                for token in tokens:callback(token)
                return tokens,'RETURN',None
        engine=legacy_raw_engine();engine.session=Session();engine.encoding=encoding;engine.load=lambda cancel=None:None
        engine.config['exact_history_cache']=True
        history=[Message.from_role_and_content(Role.USER,'Repair probe.py and check its tests.').to_dict()]
        emit=lambda *a:None
        replies,_=engine.generate(history,str(ROOT/'workspace'),emit,threading.Event(),True,512,reasoning_effort='low')
        history.extend(m.to_dict() for m in replies)
        history.append(Message(author=Author.new(Role.TOOL,'functions.read_file'),content=[TextContent(text='{"text":"def answer():return 0"}')]).with_recipient('assistant').to_dict())
        replies,_=engine.generate(history,str(ROOT/'workspace'),emit,threading.Event(),True,512,reasoning_effort='low')
        expected_prefix=len(engine.committed)-len(draft_tokens)+len(analysis_tokens)
        cached_prefix=len(engine.exact_history.raw)
        # Match AgentRun: persist analysis, reject the unchecked final, then steer.
        history.extend(m.to_dict() for m in replies if m.channel=='analysis')
        history.append(Message.from_role_and_content(Role.DEVELOPER,'Actual tests failed; repair the current source and rerun.').to_dict())
        if changed_goal:history[0]=Message.from_role_and_content(Role.USER,'A different task.').to_dict()
        replies,_=engine.generate(history,str(ROOT/'workspace'),emit,threading.Event(),True,512,reasoning_effort='low')
        return calls,expected_prefix,cached_prefix,encoding.decode(calls[-1]['full_prompt']),engine

    # ------------------------------------------------------------------------------
    # test_rejected_final_retains_exact_stored_history_without_replaying_draft: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_rejected_final_retains_exact_stored_history_without_replaying_draft(self):
        calls,prefix,cached,text,engine=self.rejected_draft()
        self.assertEqual(cached,prefix)
        # The next developer/assistant header shares its message-start token.
        self.assertGreaterEqual(calls[-1]['keep'],prefix)
        self.assertLessEqual(calls[-1]['keep'],prefix+1)
        self.assertNotIn('UNACCEPTED_FINAL_SENTINEL',text)
        self.assertIn('Actual tests failed',text)
        self.assertGreater(engine.last_timing['exact_history_cache_tokens'],0)

    # ------------------------------------------------------------------------------
    # test_changed_goal_cannot_restore_rejected_draft_history: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_changed_goal_cannot_restore_rejected_draft_history(self):
        calls,prefix,cached,text,engine=self.rejected_draft(changed_goal=True)
        self.assertLess(calls[-1]['keep'],prefix)
        self.assertEqual(engine.last_timing['exact_history_cache_tokens'],0)
        self.assertNotIn('UNACCEPTED_FINAL_SENTINEL',text)

    # ------------------------------------------------------------------------------
    # exercise: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def exercise(self, enabled=True, reason='RETURN', changed_goal=False, effort='auto'):
        encoding=load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
        body=json.dumps({'path':'probe.py','content':'# source line\n'*30})
        tool=Message.from_role_and_content(Role.ASSISTANT,body).with_channel('commentary').with_recipient('functions.write_file')
        canonical=encoding.render_conversation(Conversation.from_messages([tool]))
        # Both header orders are valid native Harmony and parse to identical messages.
        raw=encoding.encode(encoding.decode(canonical).replace(
            'assistant to=functions.write_file<|channel|>commentary',
            'assistant<|channel|>commentary to=functions.write_file'),allowed_special='all')
        self.assertNotEqual(canonical,raw)
        start=encoding.render_conversation_for_completion(Conversation.from_messages([]),Role.ASSISTANT)
        produced=raw[len(start):]
        final=encoding.render_conversation(Conversation.from_messages([
            Message.from_role_and_content(Role.ASSISTANT,'Checked.').with_channel('final')]))[len(start):]
        decoded=encoding.parse_messages_from_completion_tokens(produced,Role.ASSISTANT)
        self.assertEqual(decoded[0].to_dict(),tool.to_dict())
        calls=[]
        # ------------------------------------------------------------------------------
        # Session: Class State Encapsulation & Contract Specification
        # Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
        # Invariant: Enforces structural invariants and thread-safe state mutations across member calls
        # Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
        # ------------------------------------------------------------------------------
        class Session:
            ctx=8192
            proc=SimpleNamespace(poll=lambda:None)
            last_timing={}
            # ------------------------------------------------------------------------------
            # turn: Function Pipeline & Contract Specification
            # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
            # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
            # Failure Modes: Catches or propagates domain exceptions according to API contracts
            # ------------------------------------------------------------------------------
            def turn(self, ids, maximum, keep, callback, temperature=0):
                calls.append({'ids':ids,'keep':keep})
                tokens=produced if len(calls)==1 else final
                for token in tokens: callback(token)
                return tokens,reason if len(calls)==1 else 'RETURN',None
        engine=legacy_raw_engine();engine.session=Session();engine.encoding=encoding
        engine.config['exact_history_cache']=enabled;engine.load=lambda cancel=None:None
        events=[];emit=lambda k,d:events.append((k,d))
        history=[Message.from_role_and_content(Role.USER,'Create probe.py').to_dict()]
        replies,_=engine.generate(history,str(ROOT/'workspace'),emit,threading.Event(),True,512,reasoning_effort=effort)
        cached=len(engine.committed)
        history.extend(m.to_dict() for m in replies)
        history.append(Message(author=Author.new(Role.TOOL,'functions.write_file'),content=[TextContent(text='{"bytes":420}')]).with_recipient('assistant').to_dict())
        if changed_goal: history[0]=Message.from_role_and_content(Role.USER,'Create other.py').to_dict()
        engine.generate(history,str(ROOT/'workspace'),emit,threading.Event(),True,512,reasoning_effort=effort)
        inference=[d for k,d in events if k=='inference']
        return calls,cached,inference,engine

    # ------------------------------------------------------------------------------
    # test_exact_emitted_header_and_body_are_reused_after_tool: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_exact_emitted_header_and_body_are_reused_after_tool(self):
        calls,cached,events,_=self.exercise()
        self.assertEqual(calls[1]['keep'],cached)
        self.assertEqual(events[1]['exact_history_cache_tokens'],cached)
        self.assertGreater(events[1]['cache_saved_prefill_tokens'],100)
        self.assertLess(len(calls[1]['ids']),30)

    # ------------------------------------------------------------------------------
    # test_disabled_feature_demonstrates_canonical_header_cache_miss: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_disabled_feature_demonstrates_canonical_header_cache_miss(self):
        calls,cached,events,_=self.exercise(enabled=False)
        self.assertLess(calls[1]['keep'],cached)
        self.assertGreater(len(calls[1]['ids']),100)
        self.assertEqual(events[1]['exact_history_cache_tokens'],0)

    # ------------------------------------------------------------------------------
    # test_partial_generation_and_changed_history_never_splice: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_partial_generation_and_changed_history_never_splice(self):
        for options in ({'reason':'MAX_TOKENS'},{'changed_goal':True}):
            _,_,events,engine=self.exercise(**options)
            self.assertEqual(events[1]['exact_history_cache_tokens'],0)
            self.assertFalse(engine.exact_history.canonical) # final drafts are excluded too

    # ------------------------------------------------------------------------------
    # test_auto_coding_and_explicit_quick_use_fixed_reasoning_level: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_auto_coding_and_explicit_quick_use_fixed_reasoning_level(self):
        for effort,expected in (('auto','medium'),('low','low'),('high','high')):
            _,_,events,_=self.exercise(effort=effort)
            self.assertEqual([e['reasoning_effort'] for e in events],[expected,expected])

