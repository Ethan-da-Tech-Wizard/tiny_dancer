# ==============================================================================
# Program: test_native_chat_timeout.py
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
"""Real local HTTP delay/cancellation checks without native model inference."""
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import socket
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import httpx
from openai_harmony import Message,Role
from app.engine import Cancelled
from app.native_chat import generate
from app.task_policy import contract_for


# ------------------------------------------------------------------------------
# NativeChatTimeoutTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class NativeChatTimeoutTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # make_engine: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(B) linear with respect to serialized payload byte length | Space: O(B) memory mapped buffer or byte stream heap allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def make_engine(self,hang=False):
        entered=threading.Event();release=threading.Event();connections=[]
        # ------------------------------------------------------------------------------
        # Handler: Class State Encapsulation & Contract Specification
        # Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
        # Invariant: Enforces structural invariants and thread-safe state mutations across member calls
        # Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
        # ------------------------------------------------------------------------------
        class Handler(BaseHTTPRequestHandler):
            # ------------------------------------------------------------------------------
            # log_message: Function Pipeline & Contract Specification
            # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
            # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
            # Failure Modes: Catches or propagates domain exceptions according to API contracts
            # ------------------------------------------------------------------------------
            def log_message(self,*args):pass
            # ------------------------------------------------------------------------------
            # do_POST: Function Pipeline & Contract Specification
            # Algorithmic Complexity: Time: O(B) linear with respect to serialized payload byte length | Space: O(B) memory mapped buffer or byte stream heap allocation
            # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
            # Failure Modes: Catches or propagates domain exceptions according to API contracts
            # ------------------------------------------------------------------------------
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                if self.path=='/apply-template': data={'prompt':'fixture prompt'}
                elif self.path=='/tokenize': data={'tokens':[1]*100}
                else:
                    connections.append(self.connection);entered.set()
                    if hang:
                        release.wait(3);return
                    time.sleep(.15)
                    data={'choices':[{'index':0,'delta':{'content':'Fixture complete'},'finish_reason':'stop'}]}
                    body=('data: '+json.dumps(data)+'\n\ndata: [DONE]\n\n').encode()
                    try:
                        self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers();self.wfile.write(body)
                    except (BrokenPipeError,ConnectionResetError):pass
                    return
                self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(data).encode())
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        # ------------------------------------------------------------------------------
        # cleanup: Function Pipeline & Contract Specification
        # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
        # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
        # Failure Modes: Catches or propagates domain exceptions according to API contracts
        # ------------------------------------------------------------------------------
        def cleanup():release.set();server.shutdown();server.server_close();thread.join()
        self.addCleanup(cleanup)
        client=httpx.Client(base_url='http://127.0.0.1:'+str(server.server_port),trust_env=False,
                           timeout=httpx.Timeout(1,read=.04))
        self.addCleanup(client.close)
        # ------------------------------------------------------------------------------
        # cancel_owned_server: Function Pipeline & Contract Specification
        # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
        # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
        # Failure Modes: Catches or propagates domain exceptions according to API contracts
        # ------------------------------------------------------------------------------
        def cancel_owned_server():
            # Models Stop killing the owned inference process/its pending socket.
            for connection in connections:
                try:connection.shutdown(socket.SHUT_RDWR)
                except OSError:pass
            release.set()
        engine=SimpleNamespace(lock=threading.Lock(),load=Mock(),cancel=Mock(side_effect=cancel_owned_server),
            config={'auto_work_reply_continuation':True,'native_sampling_profile':'recommended'},
            session=SimpleNamespace(client=client,ctx=8192,proc=SimpleNamespace(poll=lambda:None)))
        return engine,entered

    # ------------------------------------------------------------------------------
    # generate: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def generate(self,engine,flag):
        contract=contract_for('Make a Python program','work',cwd='/fixture')
        contract['_auto_reply_continuation']=True
        return generate(engine,[Message.from_role_and_content(Role.USER,'Make a program').to_dict()],'/fixture',
            lambda *_:None,flag,2048,contract,'medium')

    # ------------------------------------------------------------------------------
    # test_active_inference_outlives_transport_read_timer: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_active_inference_outlives_transport_read_timer(self):
        engine,_=self.make_engine();result,reason=self.generate(engine,threading.Event())
        self.assertEqual(reason,'EOS');self.assertEqual(len(result),1)
        engine.cancel.assert_not_called()
        # The override must not mutate the client's timeout for ordinary requests.
        self.assertEqual(engine.session.client.timeout.read,.04)
        self.assertEqual(engine.session.client.timeout.connect,1)

    # ------------------------------------------------------------------------------
    # test_stop_interrupts_inference_waiting_for_first_byte: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_stop_interrupts_inference_waiting_for_first_byte(self):
        engine,entered=self.make_engine(hang=True);flag=threading.Event()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(self.generate,engine,flag)
            self.assertTrue(entered.wait(2));flag.set();engine.cancel()
            with self.assertRaises(Cancelled):future.result(timeout=2)
        self.assertGreaterEqual(engine.cancel.call_count,1)
