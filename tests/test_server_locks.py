# ==============================================================================
# tests/test_server_locks.py - single-task lock and stop() behaviour in app/server.py
#
# app/server.py cannot be imported in a unit test (it opens sqlite under ROOT, starts the
# engine objects and needs fastapi/psutil/openai_harmony). Instead the functions under test
# are extracted from the source with `ast` and executed in a namespace of small fakes, which
# keeps the REAL function bodies under test without those side effects.
#
# Pins down:
#   * /v1/chat/completions holds active_job while generating (so a task start answers 409) and
#     releases it on success AND on every failure path (try/finally);
#   * stop() on a job whose task object is already gone returns normally instead of KeyError.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
import ast
import asyncio
import threading
import types
import unittest
import uuid
from pathlib import Path

SOURCE = (Path(__file__).resolve().parent.parent / 'app' / 'server.py').read_text()


class HTTPException(Exception):
    """Minimal stand-in for fastapi.HTTPException."""

    def __init__(self, status, detail=''):
        super().__init__(status, detail)
        self.status = status


def load(names, **extra):
    """Compile the named top-level functions of server.py (decorators stripped) into one namespace."""
    tree = ast.parse(SOURCE)
    picked = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            node.decorator_list = []
            picked.append(node)
    assert {n.name for n in picked} == set(names), 'missing function in server.py'
    ns = {'HTTPException': HTTPException, 'asyncio': asyncio, 'threading': threading, 'uuid': uuid,
          'Request': object, 'active_job': None, 'tasks': {}, 'cancel_flags': {}, **extra}
    exec(compile(ast.Module(body=picked, type_ignores=[]), 'server_extract', 'exec'), ns)
    return ns


class FakeMessage:
    """Stand-in for openai_harmony.Message with the two constructors completions() uses."""

    def __init__(self, role, text):
        self.role, self.text, self.channel = role, text, 'final'

    @classmethod
    def from_role_and_content(cls, role, text):
        return cls(role, text)

    def to_dict(self):
        return {'role': self.role, 'text': self.text}


class FakeEngine:
    """Records whether the lock was held while generate() ran."""

    last_timing = {}

    def __init__(self, ns, fail=False):
        self.ns, self.fail, self.seen = ns, fail, None
        self.cancelled = 0

    def generate(self, *args):
        self.seen = self.ns['active_job']
        if self.fail:
            raise RuntimeError('boom')
        return [FakeMessage('assistant', 'hi')], 'STOP'

    def cancel(self):
        self.cancelled += 1


class FakeRequest:
    def __init__(self, body):
        self.body = body

    async def json(self):
        return self.body


def make(fail=False):
    ns = load(['completions', '_completions_locked'], Message=FakeMessage,
              Role=types.SimpleNamespace(DEVELOPER='developer', USER='user', ASSISTANT='assistant'),
              text_of=lambda m: m.text, ROOT=Path('/tmp'))
    ns['Role'] = lambda v: v  # Role(m['role']) in the source is a call
    ns['Role'].DEVELOPER, ns['Role'].USER = 'developer', 'user'
    ns['engine'] = FakeEngine(ns, fail)
    return ns


class CompletionsLockTests(unittest.TestCase):
    """The compatibility endpoint must hold the single-task lock."""

    # Scenario: normal request. During generate() active_job is set; afterwards it is cleared.
    def test_lock_held_during_generation_and_released(self):
        ns = make()
        out = asyncio.run(ns['completions'](FakeRequest({'messages': [{'role': 'user', 'content': 'x'}]})))
        self.assertTrue(str(ns['engine'].seen).startswith('chat-'))
        self.assertIsNone(ns['active_job'])
        self.assertEqual(out['choices'][0]['message']['content'], 'hi')

    # Scenario: generation raises, request is invalid, or stream requested: the lock must still be freed.
    def test_lock_released_on_every_failure_path(self):
        for body, fail in [({'messages': [{'role': 'user', 'content': 'x'}]}, True), ({'messages': []}, False),
                           ({'stream': True, 'messages': [{'role': 'user', 'content': 'x'}]}, False)]:
            ns = make(fail)
            with self.assertRaises(HTTPException):
                asyncio.run(ns['completions'](FakeRequest(body)))
            self.assertIsNone(ns['active_job'], body)

    # Scenario: a task (or another completion) already holds the lock: 409 and the lock is untouched.
    def test_busy_returns_409_and_keeps_existing_lock(self):
        ns = make()
        ns['active_job'] = 'realjob'
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(ns['completions'](FakeRequest({'messages': []})))
        self.assertEqual(ctx.exception.status, 409)
        self.assertEqual(ns['active_job'], 'realjob')

    # Scenario: two completions started together; the second sees the lock claimed before the first awaits.
    def test_concurrent_requests_second_gets_409(self):
        ns = make()

        async def both():
            first = asyncio.ensure_future(ns['completions'](FakeRequest({'messages': [{'role': 'user', 'content': 'x'}]})))
            await asyncio.sleep(0)  # let the first run up to its first await
            with self.assertRaises(HTTPException) as ctx:
                await ns['completions'](FakeRequest({'messages': []}))
            self.assertEqual(ctx.exception.status, 409)
            await first
        asyncio.run(both())


class StopTests(unittest.TestCase):
    """stop() robustness when bookkeeping dicts are mid-cleanup."""

    def make(self, flags, tasks):
        eng = FakeEngine({'active_job': None})
        return load(['stop'], engine=eng, cancel_flags=flags, tasks=tasks), eng

    # Scenario: flag present but the task object already popped (task just finished): no KeyError.
    def test_missing_task_object_is_tolerated(self):
        flag = threading.Event()
        ns, eng = self.make({'j': flag}, {})
        self.assertEqual(asyncio.run(ns['stop']('j')), {'stopped': True})
        self.assertTrue(flag.is_set())
        self.assertEqual(eng.cancelled, 1)

    # Scenario: normal stop cancels the asyncio task.
    def test_running_task_is_cancelled(self):
        async def go():
            flag = threading.Event()
            task = asyncio.ensure_future(asyncio.sleep(60))
            ns, _ = self.make({'j': flag}, {'j': task})
            await ns['stop']('j')
            await asyncio.sleep(0)
            return task.cancelled()
        self.assertTrue(asyncio.run(go()))

    # Scenario: unknown job still answers 404.
    def test_unknown_job_404(self):
        ns, _ = self.make({}, {})
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(ns['stop']('nope'))
        self.assertEqual(ctx.exception.status, 404)


if __name__ == '__main__':
    unittest.main()
