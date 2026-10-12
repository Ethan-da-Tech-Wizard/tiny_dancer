import asyncio
import hmac
import json
import os
import secrets
import sqlite3
import threading
import time
import traceback
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import psutil
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai_harmony import Author, Message, Role, TextContent
from app.request_models import NewSession,NewTask,ResumeTask,apply_resume_options

from app.engine import Cancelled, LocalEngine
from app.tools import ComputerTools, ROOT, TOOLS
from app.agent import AgentRun
from app.history import task_history
from app.validation_results import collect_results,evidence_path

RUN = ROOT / 'run'
RUN.mkdir(exist_ok=True)
TOKEN = RUN / 'access-token'
if not TOKEN.exists():
    fd = os.open(TOKEN, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f: f.write(secrets.token_urlsafe(32))
token = TOKEN.read_text().strip()
os.chmod(TOKEN, 0o600)
DB = RUN / 'workspace.sqlite3'
db_lock = threading.Lock()

def query(sql, params=(), one=False):
    with db_lock, sqlite3.connect(DB, timeout=15) as con:
        con.row_factory = sqlite3.Row
        cursor = con.execute(sql, params)
        rows = [dict(r) for r in cursor.fetchall()] if cursor.description else []
        return (rows[0] if rows else None) if one else rows

with sqlite3.connect(DB) as con:
    con.executescript('''PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,title TEXT,cwd TEXT,created REAL);
    CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,session TEXT,role TEXT,text TEXT,harmony TEXT,created REAL);
    CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,session TEXT,status TEXT,created REAL,finished REAL);
    CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,job TEXT,kind TEXT,data TEXT,created REAL);
    CREATE TABLE IF NOT EXISTS job_context(job TEXT PRIMARY KEY,request TEXT,checkpoint TEXT);
    CREATE INDEX IF NOT EXISTS events_job ON events(job,id);
    CREATE INDEX IF NOT EXISTS messages_session ON messages(session,id);
    ''')
query("UPDATE jobs SET status='interrupted',finished=? WHERE status='running'", (time.time(),))
engine = LocalEngine()
tools = ComputerTools()
tasks = {}
cancel_flags = {}
active_job = None

def text_of(message):
    return ''.join(c.text for c in message.content if isinstance(c, TextContent))

def save_message(session, message, display_role=None):
    with db_lock, sqlite3.connect(DB, timeout=15) as con:
        cursor = con.execute('INSERT INTO messages(session,role,text,harmony,created) VALUES(?,?,?,?,?)',
            (session, display_role or str(message.author.role.value), text_of(message),
             json.dumps(message.to_dict()), time.time()))
        return cursor.lastrowid

def event(job, kind, data):
    query('INSERT INTO events(job,kind,data,created) VALUES(?,?,?,?)', (job, kind, json.dumps(data), time.time()))
    if kind in ('tool_start', 'tool_result', 'error', 'done', 'cancelled', 'checkpoint', 'continuation'):
        with (ROOT / 'logs/agent-audit.jsonl').open('a') as f:
            f.write(json.dumps({'at':time.time(), 'job':job, 'kind':kind, 'data':data}) + '\n')

@asynccontextmanager
async def lifespan(app):
    async def idle_maintenance():
        while True:
            await asyncio.sleep(10)
            seconds = engine.config.get('idle_unload_seconds', 300)
            if active_job or seconds <= 0: continue
            try:
                await asyncio.to_thread(engine.unload_if_idle, seconds)
                if not active_job: await tools.release_idle_browser(seconds)
            except Exception:
                # A browser teardown error must not disable future idle release.
                traceback.print_exc()
    maintenance = asyncio.create_task(idle_maintenance())
    yield
    maintenance.cancel()
    await asyncio.gather(maintenance, return_exceptions=True)
    for flag in cancel_flags.values(): flag.set()
    engine.close()
    for task in list(tasks.values()): task.cancel()
    await asyncio.gather(*list(tasks.values()), return_exceptions=True)
    await tools.close()

app = FastAPI(title='Tiny Dancer', lifespan=lifespan, docs_url=None, redoc_url=None)

@app.middleware('http')
async def local_auth(request, call_next):
    host = request.headers.get('host', '').split(':')[0]
    if host not in ('127.0.0.1', 'localhost', 'testserver'):
        return JSONResponse({'detail':'Invalid local host'}, status_code=403)
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        origin = request.headers.get('origin')
        if origin and origin not in ('http://127.0.0.1:3210', 'http://localhost:3210'):
            return JSONResponse({'detail':'Cross-origin requests are blocked'}, status_code=403)
    if request.url.path.startswith(('/api/', '/v1/', '/artifacts/')):
        bearer = request.headers.get('authorization', '').removeprefix('Bearer ')
        cookie = request.cookies.get('tiny_dancer', '')
        if not (hmac.compare_digest(cookie, token) or hmac.compare_digest(bearer, token)):
            return JSONResponse({'detail':'Open the local workspace first, or supply its local access token'}, status_code=401)
    response = await call_next(request)
    response.headers.update({'X-Content-Type-Options':'nosniff', 'X-Frame-Options':'DENY',
        'Referrer-Policy':'same-origin', 'Cache-Control':'no-store'})
    if request.url.path in ('/','/results'): response.set_cookie('tiny_dancer', token, httponly=True, samesite='strict')
    return response

@app.get('/')
def index(): return FileResponse(ROOT / 'app/static/index.html')

@app.get('/results')
def results_page(): return FileResponse(ROOT/'app/static/results.html')

@app.get('/api/test-results')
def test_results(): return collect_results(ROOT)

@app.get('/api/test-results/{identifier}')
def test_evidence(identifier: str):
    try: return FileResponse(evidence_path(ROOT,identifier,collect_results(ROOT)))
    except ValueError: raise HTTPException(404,'Unknown test evidence')

app.mount('/static', StaticFiles(directory=str(ROOT / 'app/static')), name='static')
app.mount('/artifacts', StaticFiles(directory=str(RUN / 'artifacts')), name='artifacts')

def persist_checkpoint(job, state):
    serialized = json.dumps(state)
    query('UPDATE job_context SET checkpoint=? WHERE job=?', (serialized, job))
    directory = RUN / 'tasks'
    directory.mkdir(exist_ok=True)
    temp = directory / (job + '.tmp')
    temp.write_text(serialized + '\n')
    temp.replace(directory / (job + '.json'))

@app.post('/api/sessions/{sid}/editor')
async def open_editor(sid: str):
    s = query('SELECT * FROM sessions WHERE id=?', (sid,), one=True)
    if not s: raise HTTPException(404, 'Session not found')
    try: return await tools.editor({'action':'open','path':s['cwd']}, s['cwd'])
    except Exception as exc: raise HTTPException(400, str(exc))

@app.get('/api/observe')
async def observe(source: str = 'browser'):
    try: return await tools.observe(source)
    except Exception as exc: raise HTTPException(400, str(exc))

@app.patch('/api/sessions/{sid}')
def change_directory(sid: str, data: NewSession):
    if active_job: raise HTTPException(409, 'Stop the current task before changing its folder')
    path = Path(data.cwd).expanduser().resolve()
    if not path.is_dir(): raise HTTPException(400, 'Working directory must exist')
    if not query('SELECT id FROM sessions WHERE id=?', (sid,), one=True): raise HTTPException(404, 'Session not found')
    query('UPDATE sessions SET cwd=? WHERE id=?', (str(path), sid))
    return {'cwd':str(path)}

@app.get('/api/status')
def status():
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage(ROOT)
    if engine.session and engine.session.proc.poll() is not None and engine.status in ('ready', 'generating', 'processing prompt'):
        engine.status = 'not loaded'
    child = engine.starting_proc or (engine.session.proc if engine.session else None)
    return {'model':'GPT-OSS-20B', 'runtime':'llama.cpp · native MXFP4' if engine.config.get('backend')=='llama.cpp' else 'Picchio · Colibrì-inspired expert streaming',
        'engine':engine.status, 'active_job':active_job, 'root':str(ROOT),
        'model_pid':child.pid if child and child.poll() is None else None,
        'model_installed':(ROOT / engine.config['model_path'] / 'INSTALL_COMPLETE').exists(),
        'ram':{'used':vm.used,'total':vm.total,'available':vm.available},
        'disk':{'free':disk.free,'total':disk.total}, 'cpu_percent':psutil.cpu_percent(),
        'config':engine.config, 'metrics':engine.last_timing,
        'tools':[t['name'] for t in TOOLS],
        'task':task_snapshot(active_job) if active_job else None}

def task_snapshot(job):
    """Small public progress record for polling if browser streaming disconnects."""
    row = query('SELECT * FROM jobs WHERE id=?', (job,), one=True)
    if not row: raise HTTPException(404, 'Job not found')
    context = query('SELECT checkpoint FROM job_context WHERE job=?', (job,), one=True)
    checkpoint = json.loads(context['checkpoint']) if context and context['checkpoint'] else {}
    # Only public counts/status; never return model analysis in a heartbeat.
    latest = query("SELECT kind,data,created FROM events WHERE job=? AND kind IN ('inference','progress','tool_start','paused','error','done','cancelled') ORDER BY id DESC LIMIT 1", (job,), one=True)
    if latest: latest['data'] = json.loads(latest['data'])
    row.update(checkpoint=checkpoint, progress=latest,
               elapsed_seconds=round(max(0,(row['finished'] or time.time())-checkpoint.get('run_started_at',row['created'])),1))
    return row

@app.get('/api/jobs/{job}/progress')
def job_progress(job):
    return task_snapshot(job)

@app.get('/api/sessions')
def sessions(): return query('SELECT * FROM sessions ORDER BY created DESC')

@app.post('/api/sessions')
def new_session(data: NewSession):
    cwd = Path(data.cwd).expanduser().resolve()
    if not cwd.is_dir(): raise HTTPException(400, 'Working directory must exist')
    sid = uuid.uuid4().hex
    query('INSERT INTO sessions VALUES(?,?,?,?)', (sid, data.title[:100], str(cwd), time.time()))
    return query('SELECT * FROM sessions WHERE id=?', (sid,), one=True)

@app.get('/api/sessions/{sid}')
def session(sid):
    s = query('SELECT * FROM sessions WHERE id=?', (sid,), one=True)
    if not s: raise HTTPException(404, 'Session not found')
    s['messages'] = query('SELECT id,role,text,harmony,created FROM messages WHERE session=? ORDER BY id', (sid,))
    s['jobs'] = query('SELECT * FROM jobs WHERE session=? ORDER BY created DESC LIMIT 10', (sid,))
    for job in s['jobs']:
        context = query('SELECT checkpoint FROM job_context WHERE job=?', (job['id'],), one=True)
        job['checkpoint'] = json.loads(context['checkpoint']) if context and context['checkpoint'] else None
    return s

@app.post('/api/sessions/{sid}/tasks')
async def start_task(sid: str, data: NewTask):
    global active_job
    s = query('SELECT * FROM sessions WHERE id=?', (sid,), one=True)
    if not s: raise HTTPException(404, 'Session not found')
    if active_job: raise HTTPException(409, 'Another task is running. Stop it or wait for it to finish.')
    if data.mode not in ('agent', 'chat'): raise HTTPException(400, 'Choose agent or chat mode')
    if not (ROOT / engine.config['model_path'] / 'INSTALL_COMPLETE').exists():
        raise HTTPException(503, 'Model installation is still in progress. See logs/model-convert.log.')
    if s['title'] == 'New session': query('UPDATE sessions SET title=? WHERE id=?', (data.prompt[:60], sid))
    goal_id = save_message(sid, Message.from_role_and_content(Role.USER, data.prompt))
    job = uuid.uuid4().hex
    query('INSERT INTO jobs VALUES(?,?,?,?,NULL)', (job, sid, 'running', time.time()))
    query('INSERT INTO job_context VALUES(?,?,NULL)', (job, data.model_dump_json()))
    checkpoint = {'job_id':job, 'goal_message_id': goal_id, 'context_start': goal_id if data.mode == 'agent' else 0,
                  'context_insert_goal': False}
    flag = threading.Event()
    active_job = job
    cancel_flags[job] = flag
    event(job, 'started', {'session':sid, 'mode':data.mode})
    tasks[job] = asyncio.create_task(run_agent(job, s, data, flag, checkpoint))
    return {'job':job}

async def run_agent(job, s, data, flag, checkpoint=None):
    global active_job
    sid = s['id']
    try:
        def history():
            return task_history(query('SELECT id,harmony FROM messages WHERE session=? ORDER BY id', (sid,)),
                                data.prompt, data.mode, run.state)
        run = AgentRun(engine, tools, s['cwd'], data,
            history,
            lambda message, role=None: save_message(sid, message, role),
            lambda kind, payload: event(job, kind, payload),
            lambda state: persist_checkpoint(job, state), flag, checkpoint)
        run.checkpoint()
        result = await run.run()
        query('UPDATE jobs SET status=?,finished=? WHERE id=?', (result, time.time(), job))
        if result == 'complete': event(job, 'done', {'steps':run.state['turns'], 'verified':run.state['verified'],
                                                  'evidence_checked':run.state['evidence_checked'],
                                                  'answer_origin':'checked_export' if run.state.get('data_check',{}).get('export') else 'checked_lookup' if run.state.get('data_check') else 'model'})
        else: event(job, 'paused', {'status':result, 'message':run.state.get('blocked_reason') or run.state.get('next_action') or 'Reply budget reached; history saved.'})
    except (Cancelled, asyncio.CancelledError):
        event(job, 'cancelled', {'message':'Task stopped. Completed tool actions remain in the history.'})
        query("UPDATE jobs SET status='cancelled',finished=? WHERE id=?", (time.time(), job))
    except Exception as exc:
        traceback.print_exc()
        event(job, 'error', {'message':str(exc) or type(exc).__name__})
        query("UPDATE jobs SET status='failed',finished=? WHERE id=?", (time.time(), job))
    finally:
        active_job = None
        tasks.pop(job, None)
        cancel_flags.pop(job, None)

@app.post('/api/jobs/{job}/resume')
async def resume(job: str, options: ResumeTask):
    global active_job
    if active_job: raise HTTPException(409, 'Another task is running')
    previous = query('SELECT * FROM jobs WHERE id=?', (job,), one=True)
    context = query('SELECT * FROM job_context WHERE job=?', (job,), one=True)
    if not previous or not context: raise HTTPException(404, 'No resumable task checkpoint')
    if previous['status'] not in ('paused','blocked','interrupted','cancelled','failed','limited'):
        raise HTTPException(400, 'This task does not need resuming')
    s = query('SELECT * FROM sessions WHERE id=?', (previous['session'],), one=True)
    latest = query('SELECT id FROM jobs WHERE session=? ORDER BY created DESC LIMIT 1', (s['id'],), one=True)
    if latest['id'] != job: raise HTTPException(400, 'Resume the latest task in this session, or start a new task with the saved notes')
    data = NewTask.model_validate_json(context['request'])
    apply_resume_options(data,options)
    query('UPDATE job_context SET request=? WHERE job=?', (data.model_dump_json(), job))
    checkpoint = json.loads(context['checkpoint']) if context['checkpoint'] else {
        'goal':data.prompt, 'steps':[], 'summary':'', 'next_action':'',
        'verified':False, 'checks':[], 'turns':0}
    if checkpoint:
        checkpoint['job_id'] = job
        checkpoint.pop('blocked_reason', None)
        checkpoint['verified'] = False
        if checkpoint.get('cwd'):
            if not Path(checkpoint['cwd']).is_dir(): raise HTTPException(400, 'The saved task folder no longer exists')
            s['cwd'] = checkpoint['cwd']
    notes = {key:checkpoint[key] for key in ('goal','steps','summary','next_action','cwd','turns','last_failure') if key in checkpoint}
    notes['last_checks'] = [{key:check[key] for key in ('command','exit_code','timed_out') if key in check}
                           | {'output':str(check.get('output',''))[:500]} for check in checkpoint.get('checks', [])[-8:]]
    resume_id = save_message(s['id'], Message.from_role_and_content(Role.DEVELOPER,
        'Resume the saved task without repeating completed actions. Check current files and screen before changing them. '
        f'Full previous history remains in run/workspace.sqlite3; durable task state is /mnt/GameDrive/tiny_dancer/run/tasks/{job}.json. '
        'This concise checkpoint is a starting point; re-read needed files and results before acting. '
        + json.dumps(notes)[:6000]))
    if options.compact_context and data.mode == 'agent':
        checkpoint['context_start'] = resume_id
        checkpoint['context_insert_goal'] = True
    elif not options.compact_context:
        checkpoint['context_start'] = checkpoint.get('goal_message_id', 0)
        checkpoint['context_insert_goal'] = False
    flag = threading.Event()
    active_job = job
    cancel_flags[job] = flag
    query("UPDATE jobs SET status='running',finished=NULL WHERE id=?", (job,))
    event(job, 'resumed', {'message':'Resuming the saved task and its verified progress.'})
    tasks[job] = asyncio.create_task(run_agent(job, s, data, flag, checkpoint))
    return {'job':job}

@app.post('/api/jobs/{job}/stop')
async def stop(job):
    if job not in cancel_flags: raise HTTPException(404, 'Task is not running')
    cancel_flags[job].set()
    engine.cancel()
    tasks[job].cancel()
    return {'stopped':True}

@app.get('/api/jobs/{job}')
def job_status(job):
    j = query('SELECT * FROM jobs WHERE id=?', (job,), one=True)
    if not j: raise HTTPException(404, 'Job not found')
    j['events'] = query('SELECT * FROM events WHERE job=? ORDER BY id', (job,))
    context = query('SELECT checkpoint FROM job_context WHERE job=?', (job,), one=True)
    j['checkpoint'] = json.loads(context['checkpoint']) if context and context['checkpoint'] else None
    return j

@app.get('/api/jobs/{job}/events')
async def events(job: str, request: Request, after: int = 0):
    if not query('SELECT id FROM jobs WHERE id=?', (job,), one=True): raise HTTPException(404, 'Job not found')
    try: after = max(after, int(request.headers.get('last-event-id', '0')))
    except ValueError: pass
    async def stream():
        cursor = after
        while True:
            rows = query('SELECT * FROM events WHERE job=? AND id>? ORDER BY id', (job, cursor))
            for row in rows:
                cursor = row['id']
                yield f"id: {cursor}\ndata: {json.dumps({'kind':row['kind'],'data':json.loads(row['data'])})}\n\n"
            if query('SELECT status FROM jobs WHERE id=?', (job,), one=True)['status'] != 'running':
                yield 'event: closed\ndata: {}\n\n'
                break
            if not rows: yield ': heartbeat\n\n'
            await asyncio.sleep(0.3)
    return StreamingResponse(stream(), media_type='text/event-stream')

@app.get('/api/sessions/{sid}/export')
def export(sid):
    s = session(sid)
    text = f"# {s['title']}\n\nWorking directory: `{s['cwd']}`\n\n"
    for m in s['messages']:
        h = json.loads(m['harmony'])
        if h.get('channel') == 'analysis' or m['role'] == 'developer': continue
        text += f"## {m['role']}\n\n{m['text']}\n\n"
    return StreamingResponse(iter([text]), media_type='text/markdown', headers={'Content-Disposition':f'attachment; filename="tiny-dancer-{sid[:8]}.md"'})

@app.get('/v1/models')
def models(): return {'object':'list','data':[{'id':'gpt-oss-20b','object':'model','owned_by':'local'}]}

@app.post('/v1/chat/completions')
async def completions(request: Request):
    if active_job: raise HTTPException(409, 'Computer agent is using the model')
    data = await request.json()
    if data.get('stream'): raise HTTPException(400, 'Use workspace events for streaming; this compatibility endpoint is non-streaming')
    instructions = '\n'.join(m.get('content','') for m in data.get('messages',[]) if m['role'] in ('system','developer'))
    history = [Message.from_role_and_content(Role.DEVELOPER,instructions).to_dict()] if instructions else []
    for m in data.get('messages',[]):
        if m['role'] in ('user','assistant'):
            history.append(Message.from_role_and_content(Role(m['role']),m.get('content','')).to_dict())
    if not history: raise HTTPException(400, 'messages are required')
    try:
        replies, reason = await asyncio.to_thread(engine.generate, history, str(ROOT/'workspace'), lambda *_:None,
            threading.Event(), False, min(2048, int(data.get('max_tokens',512))))
    except Exception as exc: raise HTTPException(500, str(exc))
    text = '\n'.join(text_of(m) for m in replies if m.channel == 'final')
    return {'id':'chatcmpl-'+uuid.uuid4().hex,'object':'chat.completion','model':'gpt-oss-20b',
        'choices':[{'index':0,'message':{'role':'assistant','content':text},'finish_reason':'length' if reason=='MAX_TOKENS' else 'stop'}],
        'usage':{'prompt_tokens':engine.last_timing.get('prompt_tokens',0),'completion_tokens':engine.last_timing.get('completion_tokens',0)}}
