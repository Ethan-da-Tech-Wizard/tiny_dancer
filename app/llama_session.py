# ==============================================================================
# app/llama_session.py - start and talk to a private llama.cpp server
#
# Role in the app: app/engine.py creates a LlamaReferenceSession (backend
# 'llama.cpp') and calls turn() once per model generation. The class exposes the
# same small interface as the vendored Picchio session (ctx, proc, turn(),
# last_timing, close()) so the engine does not care which runtime is behind it.
#
# How it works: a llama-server child is launched on a random free loopback port
# with a random bearer key, so no other local program can use it. turn() sends
# the full prompt token list to /completion with cache_prompt on; llama.cpp
# reuses its KV cache for the shared prefix, and tokens stream back as they are
# generated and are handed to on_token() one by one.
#
# Safety: start-up refuses to run unless the model passed the identity and
# fidelity checks recorded in docs/, and the start-up wait aborts if free RAM
# drops below 1.5 GiB (desktop reserve). All sampling is deterministic
# (temperature from app/sampling, top_p 1, top_k 0).
#
# Tests: tests/test_llama_session.py and tests/test_llama_backend.py use fake
# servers; no model is loaded.
# ==============================================================================

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
    """Build llama-server -b/-ub flags from config.

    Prompt processing is done in batches of `llama_batch_size` (default 128) tokens,
    split further into micro-batches. Larger batches prefill faster but use more
    VRAM/RAM; the validated rule microbatch <= batch <= context matches what
    llama.cpp itself requires.

    Raises:
        ValueError: non-integer or inconsistent sizes.
    """
    batch = config.get('llama_batch_size', 128)
    microbatch = config.get('llama_microbatch_size', batch)
    if (type(batch) is not int or type(microbatch) is not int or
            not 1 <= microbatch <= batch <= int(config['context'])):
        raise ValueError('Native batch sizes must be positive integers: microbatch <= batch <= context')
    return ['-b', str(batch), '-ub', str(microbatch)]


def template_arguments(root,config):
    """Return the flags that load a pinned local chat template, or [].

    The template file must live inside the project and match the SHA-256 in
    config, so a swapped template (which changes tool-call parsing) is caught.

    Raises:
        RuntimeError: template missing, outside the project, or hash changed.
    """
    template_name=config.get('llama_chat_template_file')
    if not template_name:return []
    template=(root/template_name).resolve()
    if not template.is_relative_to(root.resolve()) or not template.is_file():
        raise RuntimeError('Pinned local chat template is missing or outside the project')
    if hashlib.sha256(template.read_bytes()).hexdigest()!=config.get('llama_chat_template_sha256'):
        raise RuntimeError('Pinned local chat template changed; validate and update its fingerprint')
    return ['--jinja','--chat-template-file',str(template)]


class LlamaReferenceSession:
    """One owned llama-server process plus the HTTP client used to drive it.

    Attributes:
        ctx: context window in tokens (config 'context').
        tokens: the token list the server's KV cache currently reflects.
        last_timing: dict of prefill/decode seconds and tokens per second from the
            previous turn.
        proc: the subprocess.Popen of the server (engine polls/kills it).
        model_storage: which model file was chosen and why (see model_cache).
    """
    def __init__(self, root, config, on_process_started=None):
        """Validate the model, start llama-server, and wait until it is healthy.

        Args:
            root: project root path.
            config: loaded config.json (context, threads, batch sizes, template).
            on_process_started: callback(proc) fired right after spawn so the engine
                can lower its priority or kill it if the user cancels during load.
        Raises:
            RuntimeError: identity checks failed, binary missing, server died, RAM
            reserve hit, or 240 s start-up deadline passed (server is closed first).
        """
        batch_args = batch_arguments(config)
        binary = root/'build/llama-reference/bin/llama-server'
        model = root/'models/gpt-oss-20b-native-mxfp4/gpt-oss-20b-MXFP4.gguf'
        fidelity = json.loads((root/'docs/native-gguf-fidelity-validation.json').read_text())
        source = json.loads((root/'docs/llama-reference-model-source.json').read_text())
        # Refuse to serve a model that has not passed its recorded identity and
        # fidelity validation; a wrong file would silently change behaviour.
        if not fidelity['passed'] or not source.get('downloaded') or model.stat().st_size != source['candidate'][0]['size']:
            raise RuntimeError('Reference model has not passed its identity checks')
        if not binary.is_file(): raise RuntimeError('Reference server build is unavailable')
        model, self.model_storage = select_model(root, config)
        # Record which file was chosen for diagnostics. Temp-then-rename keeps the
        # JSON valid even if two processes start at once.
        selection_path = root/'run/model-storage.json'
        temporary = selection_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.model_storage, indent=2)+'\n')
        temporary.replace(selection_path)
        self.ctx = int(config['context'])
        self.default_temperature = native_temperature(config)
        self.tokens = []
        self.last_timing = {}
        template_args=template_arguments(root,config)
        # Ask the OS for a free port (bind to 0). A tiny race exists between closing
        # this socket and llama-server binding, acceptable on loopback.
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0))
            port = sock.getsockname()[1]
        # Per-run API key: the server only answers requests carrying it.
        key = secrets.token_hex(32)
        # trust_env=False ignores proxy variables so loopback traffic is never proxied.
        self.client = httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False,
                                   headers={'Authorization':'Bearer '+key},timeout=120)
        # Flag meaning: -ngl 99 offload all layers to GPU; -ncmoe 16 keep the MoE
        # expert weights of the first 16 layers on CPU (fits the target VRAM); -t/-tb
        # CPU threads for generation and batch work; -np 1 a single sequence slot;
        # --flash-attn on with f16 KV cache; --no-context-shift so the context never
        # silently slides (the harness manages overflow itself).
        command = [str(binary),'-m',str(model),'-c',str(self.ctx),'-ngl','99','-ncmoe','16',
                   '-t',str(config['threads']),'-tb',str(config['threads']),*batch_args,'-np','1',
                   '--flash-attn','on','--cache-type-k','f16','--cache-type-v','f16',
                   '--no-context-shift','--host','127.0.0.1','--port',str(port),'--api-key',key,'--log-verbosity','3']
        command += template_args
        # The server log is appended, not truncated, so crashes stay inspectable.
        with (root/'logs/llama-reference-server.log').open('a') as log:
            self.proc = subprocess.Popen(command,stdout=log,stderr=log,start_new_session=True)
        try:
            if on_process_started: on_process_started(self.proc)
            deadline = time.monotonic()+240
            # Poll /health until ready; abort on process death, low RAM or the deadline.
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
        """Stop the server (SIGTERM, then SIGKILL after 3 s) and close the HTTP client."""
        if self.proc.poll() is None:
            self.proc.terminate()
            try: self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill();self.proc.wait(timeout=3)
        self.client.close()

    def turn(self, ids, max_new, keep, on_token, temperature=None, **unused):
        """Run one generation and return (produced_tokens, reason, total_tokens).

        Args:
            ids: new prompt tokens to append after the retained prefix.
            max_new: maximum tokens to generate (> 0).
            keep: how many tokens of self.tokens are still valid (0..len(tokens)).
            on_token: callback(token_id) for each streamed token; may raise to abort.
            temperature: overrides the configured default when not None.
        Returns:
            (produced, reason, n) where reason is 'EOS' or 'MAX_TOKENS' and n is the
            prompt+output length now held by the server.
        Raises:
            ValueError: invalid arguments or prompt+allowance over the context.
            RuntimeError: server error, truncation, invalid token ids, or a stream
            that ended without a terminal receipt.
        """
        if type(keep) is not int or not 0 <= keep <= len(self.tokens):
            raise ValueError('Invalid retained prefix')
        if type(max_new) is not int or max_new <= 0:
            raise ValueError('A bounded output allowance is required')
        if any(type(token) is not int or not 0 <= token < 201088 for token in ids):
            raise ValueError('Invalid Harmony token ID')
        # The server receives the whole prompt every time; its cache_prompt feature
        # finds the shared prefix itself. keep only trims what we claim to retain.
        prompt = self.tokens[:keep]+list(ids)
        if not prompt or len(prompt)+max_new > self.ctx:
            raise ValueError('Full prompt and output allowance exceed the context')
        produced = []
        timing = {'prefill_seconds':0.0,'decode_seconds':0.0,'prefill_tokens':0,'decode_tokens':0}
        started = time.monotonic()
        # Loop because a Harmony analysis message may end the stream early; the same
        # turn continues (below) until a real boundary or the allowance runs out.
        while len(produced) < max_new:
            remaining = max_new-len(produced)
            # Greedy-style sampling by default: top_k 0 / top_p 1 / min_p 0 / no repeat
            # penalty disable every filter so output depends only on temperature.
            payload = {'prompt':prompt+produced,'n_predict':remaining,'temperature':getattr(self,'default_temperature',0.0) if temperature is None else temperature,
                       'top_p':1.0,'top_k':0,'min_p':0.0,
                       'repeat_penalty':1.0,'cache_prompt':True,'return_tokens':True,'stream':True}
            terminal = None
            received = 0
            # One retry is allowed only for a connection the server closed while idle,
            # before any token arrived.
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
                            # The server cut our prompt to fit: continuing would answer a different
                            # prompt than the one we built, so fail loudly.
                            if event.get('truncated'): raise RuntimeError('Reference server truncated the supplied context')
                            tokens = event.get('tokens',[])
                            if not isinstance(tokens,list) or any(type(token) is not int or not 0 <= token < 201088 for token in tokens):
                                raise RuntimeError('Reference server returned invalid token IDs')
                            # The server must obey n_predict; exceeding it means a protocol problem.
                            if len(produced)+len(tokens) > max_new:
                                raise RuntimeError('Reference server exceeded the output allowance')
                            for token in tokens:
                                produced.append(token);received += 1;on_token(token)
                            if event.get('stop'):
                                terminal = event
                    break
                # A closed idle HTTP connection can fail before its first token.
                except httpx.RemoteProtocolError:
                    # A closed idle HTTP connection can fail before its first
                    # token. Replay only that request, once, while the owned
                    # server is alive. Never replay a partially delivered turn.
                    if attempt or received or self.proc.poll() is not None:
                        raise
            if terminal is None or not received:
                raise RuntimeError('Reference completion stream ended without a complete token receipt')
            # llama.cpp reports milliseconds; convert to seconds and accumulate across
            # the continuation loop.
            stats = terminal.get('timings',{})
            timing['prefill_seconds'] += float(stats.get('prompt_ms',0))/1000
            timing['decode_seconds'] += float(stats.get('predicted_ms',0))/1000
            timing['prefill_tokens'] += int(stats.get('prompt_n',0))
            timing['decode_tokens'] += int(stats.get('predicted_n',received))
            # A Harmony analysis message can end before the assistant's tool
            # call or final. Continue this same generation within its allowance.
            # 200007 is Harmony <|end|>: an analysis message ended but the assistant's
            # call/final has not started, so keep generating inside the same allowance.
            if terminal.get('stop_type') == 'eos' and produced[-1] == 200007 and len(produced) < max_new:
                continue
            # 200002 (<|return|>) and 200012 (<|call|>) are the legitimate message ends;
            # anything else that hits the limit is a truncation.
            completed_boundary=terminal.get('stop_type')=='eos' and produced[-1] in (200002,200012)
            reason = 'MAX_TOKENS' if terminal.get('stop_type')=='limit' or len(produced)>=max_new and not completed_boundary else 'EOS'
            break
        else: reason = 'MAX_TOKENS'
        # Remember what the server now caches for the next turn's prefix reuse.
        self.tokens = prompt+produced
        timing.update(total_seconds=time.monotonic()-started,backend='llama.cpp-native-mxfp4',
                      sampling_temperature=payload['temperature'],sampling_top_p=1.0,sampling_top_k=0,sampling_min_p=0.0,
                      sampling_repeat_penalty=1.0)
        # Tokens per second per phase; None when the phase took no measurable time.
        for phase in ('prefill','decode'):
            seconds=timing[phase+'_seconds']
            timing[phase+'_tokens_per_s']=timing[phase+'_tokens']/seconds if seconds else None
        self.last_timing=timing
        return produced,reason,len(self.tokens)
