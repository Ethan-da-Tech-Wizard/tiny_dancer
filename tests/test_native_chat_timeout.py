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


class NativeChatTimeoutTests(unittest.TestCase):
    def make_engine(self,hang=False):
        entered=threading.Event();release=threading.Event();connections=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
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
        def cleanup():release.set();server.shutdown();server.server_close();thread.join()
        self.addCleanup(cleanup)
        client=httpx.Client(base_url='http://127.0.0.1:'+str(server.server_port),trust_env=False,
                           timeout=httpx.Timeout(1,read=.04))
        self.addCleanup(client.close)
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

    def generate(self,engine,flag):
        contract=contract_for('Make a Python program','work',cwd='/fixture')
        contract['_auto_reply_continuation']=True
        return generate(engine,[Message.from_role_and_content(Role.USER,'Make a program').to_dict()],'/fixture',
            lambda *_:None,flag,2048,contract,'medium')

    def test_active_inference_outlives_transport_read_timer(self):
        engine,_=self.make_engine();result,reason=self.generate(engine,threading.Event())
        self.assertEqual(reason,'EOS');self.assertEqual(len(result),1)
        engine.cancel.assert_not_called()
        # The override must not mutate the client's timeout for ordinary requests.
        self.assertEqual(engine.session.client.timeout.read,.04)
        self.assertEqual(engine.session.client.timeout.connect,1)

    def test_stop_interrupts_inference_waiting_for_first_byte(self):
        engine,entered=self.make_engine(hang=True);flag=threading.Event()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(self.generate,engine,flag)
            self.assertTrue(entered.wait(2));flag.set();engine.cancel()
            with self.assertRaises(Cancelled):future.result(timeout=2)
        self.assertGreaterEqual(engine.cancel.call_count,1)
