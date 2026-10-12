# SPDX-License-Identifier: Apache-2.0
"""Isolated same-model session adapter; compatible with the native Harmony runner."""
import json
import hashlib
import secrets
import socket
import subprocess
import time

import httpx
import psutil
from app.sampling import native_temperature
from app.model_cache import select_model


def batch_arguments(config):
    batch = config.get('llama_batch_size', 128)
    microbatch = config.get('llama_microbatch_size', batch)
    if (type(batch) is not int or type(microbatch) is not int or
            not 1 <= microbatch <= batch <= int(config['context'])):
        raise ValueError('Native batch sizes must be positive integers: microbatch <= batch <= context')
    return ['-b', str(batch), '-ub', str(microbatch)]


def template_arguments(root,config):
    template_name=config.get('llama_chat_template_file')
    if not template_name:return []
    template=(root/template_name).resolve()
    if not template.is_relative_to(root.resolve()) or not template.is_file():
        raise RuntimeError('Pinned local chat template is missing or outside the project')
    if hashlib.sha256(template.read_bytes()).hexdigest()!=config.get('llama_chat_template_sha256'):
        raise RuntimeError('Pinned local chat template changed; validate and update its fingerprint')
    return ['--jinja','--chat-template-file',str(template)]


class LlamaReferenceSession:
    def __init__(self, root, config, on_process_started=None):
        batch_args = batch_arguments(config)
        binary = root/'build/llama-reference/bin/llama-server'
        model = root/'models/gpt-oss-20b-native-mxfp4/gpt-oss-20b-MXFP4.gguf'
        fidelity = json.loads((root/'docs/native-gguf-fidelity-validation.json').read_text())
        source = json.loads((root/'docs/llama-reference-model-source.json').read_text())
        if not fidelity['passed'] or not source.get('downloaded') or model.stat().st_size != source['candidate'][0]['size']:
            raise RuntimeError('Reference model has not passed its identity checks')
        if not binary.is_file(): raise RuntimeError('Reference server build is unavailable')
        model, self.model_storage = select_model(root, config)
        selection_path = root/'run/model-storage.json'
        temporary = selection_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.model_storage, indent=2)+'\n')
        temporary.replace(selection_path)
        self.ctx = int(config['context'])
        self.default_temperature = native_temperature(config)
        self.tokens = []
        self.last_timing = {}
        template_args=template_arguments(root,config)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0))
            port = sock.getsockname()[1]
        key = secrets.token_hex(32)
        self.client = httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False,
                                   headers={'Authorization':'Bearer '+key},timeout=120)
        command = [str(binary),'-m',str(model),'-c',str(self.ctx),'-ngl','99','-ncmoe','16',
                   '-t',str(config['threads']),'-tb',str(config['threads']),*batch_args,'-np','1',
                   '--flash-attn','on','--cache-type-k','f16','--cache-type-v','f16',
                   '--no-context-shift','--host','127.0.0.1','--port',str(port),'--api-key',key,'--log-verbosity','3']
        command += template_args
        with (root/'logs/llama-reference-server.log').open('a') as log:
            self.proc = subprocess.Popen(command,stdout=log,stderr=log,start_new_session=True)
        try:
            if on_process_started: on_process_started(self.proc)
            deadline = time.monotonic()+240
            while True:
                if self.proc.poll() is not None: raise RuntimeError('Reference server exited during startup; inspect its saved log')
                if psutil.virtual_memory().available < 1.5*2**30:
                    raise RuntimeError('Reference startup stopped at the desktop RAM reserve')
                try:
                    response = self.client.get('/health',timeout=2)
                    if response.status_code == 200: break
                except httpx.TransportError: pass
                if time.monotonic() >= deadline: raise RuntimeError('Reference startup deadline reached')
                time.sleep(.2)
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try: self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill();self.proc.wait(timeout=3)
        self.client.close()

    def turn(self, ids, max_new, keep, on_token, temperature=None, **unused):
        if type(keep) is not int or not 0 <= keep <= len(self.tokens):
            raise ValueError('Invalid retained prefix')
        if type(max_new) is not int or max_new <= 0:
            raise ValueError('A bounded output allowance is required')
        if any(type(token) is not int or not 0 <= token < 201088 for token in ids):
            raise ValueError('Invalid Harmony token ID')
        prompt = self.tokens[:keep]+list(ids)
        if not prompt or len(prompt)+max_new > self.ctx:
            raise ValueError('Full prompt and output allowance exceed the context')
        produced = []
        timing = {'prefill_seconds':0.0,'decode_seconds':0.0,'prefill_tokens':0,'decode_tokens':0}
        started = time.monotonic()
        while len(produced) < max_new:
            remaining = max_new-len(produced)
            payload = {'prompt':prompt+produced,'n_predict':remaining,'temperature':getattr(self,'default_temperature',0.0) if temperature is None else temperature,
                       'top_p':1.0,'top_k':0,'min_p':0.0,
                       'repeat_penalty':1.0,'cache_prompt':True,'return_tokens':True,'stream':True}
            terminal = None
            received = 0
            for attempt in range(2):
                try:
                    with self.client.stream('POST','/completion',json=payload) as response:
                        response.raise_for_status()
                        for line in response.iter_lines():
                            if not line.startswith('data:'): continue
                            data = line[5:].strip()
                            if data == '[DONE]': break
                            event = json.loads(data)
                            if event.get('error'): raise RuntimeError('Reference completion returned an error')
                            if event.get('truncated'): raise RuntimeError('Reference server truncated the supplied context')
                            tokens = event.get('tokens',[])
                            if not isinstance(tokens,list) or any(type(token) is not int or not 0 <= token < 201088 for token in tokens):
                                raise RuntimeError('Reference server returned invalid token IDs')
                            if len(produced)+len(tokens) > max_new:
                                raise RuntimeError('Reference server exceeded the output allowance')
                            for token in tokens:
                                produced.append(token);received += 1;on_token(token)
                            if event.get('stop'):
                                terminal = event
                    break
                except httpx.RemoteProtocolError:
                    # A closed idle HTTP connection can fail before its first
                    # token. Replay only that request, once, while the owned
                    # server is alive. Never replay a partially delivered turn.
                    if attempt or received or self.proc.poll() is not None:
                        raise
            if terminal is None or not received:
                raise RuntimeError('Reference completion stream ended without a complete token receipt')
            stats = terminal.get('timings',{})
            timing['prefill_seconds'] += float(stats.get('prompt_ms',0))/1000
            timing['decode_seconds'] += float(stats.get('predicted_ms',0))/1000
            timing['prefill_tokens'] += int(stats.get('prompt_n',0))
            timing['decode_tokens'] += int(stats.get('predicted_n',received))
            # A Harmony analysis message can end before the assistant's tool
            # call or final. Continue this same generation within its allowance.
            if terminal.get('stop_type') == 'eos' and produced[-1] == 200007 and len(produced) < max_new:
                continue
            completed_boundary=terminal.get('stop_type')=='eos' and produced[-1] in (200002,200012)
            reason = 'MAX_TOKENS' if terminal.get('stop_type')=='limit' or len(produced)>=max_new and not completed_boundary else 'EOS'
            break
        else: reason = 'MAX_TOKENS'
        self.tokens = prompt+produced
        timing.update(total_seconds=time.monotonic()-started,backend='llama.cpp-native-mxfp4',
                      sampling_temperature=payload['temperature'],sampling_top_p=1.0,sampling_top_k=0,sampling_min_p=0.0,
                      sampling_repeat_penalty=1.0)
        for phase in ('prefill','decode'):
            seconds=timing[phase+'_seconds']
            timing[phase+'_tokens_per_s']=timing[phase+'_tokens']/seconds if seconds else None
        self.last_timing=timing
        return produced,reason,len(self.tokens)
