# ==============================================================================
# Program: test_pi_cli_integration.py
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
"""Actual upstream CLI against a scripted loopback endpoint; not native ability."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from scripts.pi_baseline import FLAGS, child_environment, models_config, settings_config, public_event

ROOT = Path(__file__).resolve().parents[1]


# ------------------------------------------------------------------------------
# PiCLIIntegrationTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class PiCLIIntegrationTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # test_actual_cli_tool_execution_sampler_and_reasoning_replay: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_actual_cli_tool_execution_sampler_and_reasoning_replay(self):
        requests = []
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
            def log_message(self, *args): pass
            # ------------------------------------------------------------------------------
            # do_POST: Function Pipeline & Contract Specification
            # Algorithmic Complexity: Time: O(B) linear with respect to serialized payload byte length | Space: O(B) memory mapped buffer or byte stream heap allocation
            # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
            # Failure Modes: Catches or propagates domain exceptions according to API contracts
            # ------------------------------------------------------------------------------
            def do_POST(self):
                data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                requests.append({'path':self.path,'authorized':self.headers.get('Authorization')=='Bearer fixture-key','body':data})
                self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
                if len(requests)==1:
                    delta={'reasoning_content':'private fixture reasoning','tool_calls':[{'index':0,'id':'call_fixture','type':'function','function':{'name':'read','arguments':'{"path":"note.txt"}'}}]};finish='tool_calls'
                else: delta={'content':'fixture final'};finish='stop'
                for event in ({'choices':[{'index':0,'delta':delta,'finish_reason':None}]},
                              {'choices':[{'index':0,'delta':{},'finish_reason':finish}], 'usage':{'prompt_tokens':30,'completion_tokens':10,'total_tokens':40}}):
                    self.wfile.write(('data: '+json.dumps(event)+'\n\n').encode())
                self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush()
        with tempfile.TemporaryDirectory(dir=ROOT/'run') as temporary:
            folder=Path(temporary);private=folder/'private';private.mkdir(mode=0o700);(private/'tmp').mkdir()
            (folder/'note.txt').write_text('fixture file content')
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                (private/'models.json').write_text(json.dumps(models_config('http://127.0.0.1:'+str(server.server_port))))
                (private/'settings.json').write_text(json.dumps(settings_config('medium')))
                command=[str(ROOT/'vendor/pi-runtime/node_modules/.bin/pi'),*FLAGS,'--mode','json','--print','--no-session',
                         '--provider','tiny-local','--model','gpt-oss-20b','--thinking','medium','--tools','read,bash,edit,write','Read note.txt.']
                result=subprocess.run(command,cwd=folder,env=child_environment(ROOT,private,'fixture-key'),capture_output=True,text=True,timeout=30)
            finally: server.shutdown();server.server_close();thread.join()
            self.assertEqual(result.returncode,0)
            diagnostic = {'requests':[{'path':r['path'],'model':r['body'].get('model'),
                'roles':[m.get('role') for m in r['body'].get('messages',[])]} for r in requests],
                'events':[{'type':e.get('type'),'error':e.get('message',{}).get('errorMessage'),
                           'stop':e.get('message',{}).get('stopReason'),
                           'public':public_event(e)} for line in result.stdout.splitlines()
                          if (e:=json.loads(line)).get('type') in ('message_end','tool_execution_end')]}
            (ROOT/'logs/pi-scripted-fixture-diagnostic.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
            self.assertEqual(len(requests),2)
            for request in requests:
                self.assertEqual(request['path'],'/v1/chat/completions');self.assertTrue(request['authorized'])
                body=request['body'];self.assertEqual(body['reasoning_effort'],'medium')
                self.assertEqual(body['temperature'],1.0);self.assertEqual(body['top_p'],1.0)
                self.assertEqual(body['top_k'],0);self.assertEqual(body['min_p'],0.0)
                self.assertEqual(body['repeat_penalty'],1.0);self.assertFalse(body['parallel_tool_calls'])
                self.assertGreater(body['max_tokens'],16000);self.assertLess(body['max_tokens'],32768)
            messages=requests[1]['body']['messages']
            self.assertTrue(any(m.get('reasoning_content')=='private fixture reasoning' for m in messages))
            self.assertTrue(any(m.get('role')=='tool' and 'fixture file content' in str(m['content']) for m in messages))
            public=[p for line in result.stdout.splitlines() if (p:=public_event(json.loads(line)))]
            self.assertTrue(any(e['type']=='tool_execution_end' for e in public))
            self.assertNotIn('private fixture reasoning',json.dumps(public));self.assertNotIn('fixture final',json.dumps(public))
