const $ = (s) => document.querySelector(s);
let sessionId = null, currentJob = null, source = null, live = null, activityCount = 0;
let latestJob = null, currentFolder = '', viewTimer = null;
let reconciling = false;
const gb = (n) => (n / 1024 ** 3).toFixed(1) + ' GB';
async function api(path, method='GET', data) {
  const response = await fetch(path, {method, headers:{'Content-Type':'application/json'}, body:data === undefined ? undefined : JSON.stringify(data)});
  if (!response.ok) {let message; try {message=(await response.json()).detail;} catch {message=response.statusText;} throw new Error(typeof message==='string' ? message : JSON.stringify(message));}
  return response.json();
}
function toast(message) {$('#toast').textContent=message; $('#toast').classList.remove('hidden'); setTimeout(()=>$('#toast').classList.add('hidden'),6500);}
function scroll() {const box=$('#messages'); box.scrollTop=box.scrollHeight;}
function renderAnswer(body,text) {
  body.replaceChildren();let cursor=0;
  for(const match of text.matchAll(/\[([^\]\n]{1,200})\]\((https?:\/\/[^\s)]+)\)/g)) {
    body.append(document.createTextNode(text.slice(cursor,match.index)));
    const link=document.createElement('a');link.href=match[2];link.target='_blank';link.rel='noopener noreferrer';link.textContent=match[1];link.className='source-link';body.append(link);cursor=match.index+match[0].length;
  }
  body.append(document.createTextNode(text.slice(cursor)));
}
function message(role,text='',checkedLookup=false) {
  $('#welcome')?.remove();
  const div=document.createElement('article'); div.className='message '+role;
  const label=document.createElement('div'); label.className='message-label';label.textContent=role==='user'?'YOU':checkedLookup==='export'?'✳ TINY DANCER · CHECKED DATA EXPORT':checkedLookup?'✳ TINY DANCER · CHECKED DATA LOOKUP':'✳ TINY DANCER';
  if(checkedLookup)label.title='Fields formatted directly from checked tool data. GPT-OSS selected the lookup.';
  const body=document.createElement('div');body.className='message-text';if(role==='assistant')renderAnswer(body,text);else body.textContent=text;
  div.append(label,body);$('#messages').append(div);scroll();return body;
}
function toolEvent(name,args,result,historical=false) {
  $('#welcome')?.remove();const details=document.createElement('details');details.className='tool-event';
  const summary=document.createElement('summary'); summary.textContent='⌘ '+name+' · '+(result?'result saved':historical?'call saved':'running');
  const pre=document.createElement('pre');pre.textContent=(args || '')+(result?'\n\n'+result:'');details.append(summary,pre);
  if(result) {try {const r=JSON.parse(result);if(r.artifact){const a=document.createElement('a');a.href=r.artifact;a.target='_blank';a.rel='noopener';a.textContent='Open saved output ↗';details.append(a);}}catch{}}
  $('#messages').append(details);scroll();return details;
}
function activity(title,description='') {
  if(activityCount===0) $('#activity').replaceChildren();activityCount++;$('#activity-count').textContent=activityCount;
  const d=document.createElement('div');d.className='activity-entry';const t=document.createElement('strong');t.textContent=title;
  const s=document.createElement('small');s.textContent=description;d.append(t,s);$('#activity').prepend(d);
}
function busy(value) {$('#send').classList.toggle('hidden',value);$('#stop').classList.toggle('hidden',!value);$('#prompt').disabled=value;$('#new-session').disabled=value;$('#run-until-done').disabled=value;$('#mode').disabled=value;$('#thinking').disabled=value;$('#budget').disabled=value;}
function showProgress(state,status='running') {
  $('#progress-card').classList.toggle('hidden',!state || state.mode==='chat');
  const resumable=['paused','blocked','interrupted','cancelled','failed','limited'].includes(status);
  $('#resume-task').classList.toggle('hidden',!resumable);
  $('#pause-reason').classList.toggle('hidden',!resumable);
  $('#pause-reason').textContent=resumable?(state?.blocked_reason||state?.next_action||'Your task and completed actions are saved. Resume continues from that point.') : '';
  if(!state) return;
  $('#progress-label').textContent=status==='complete'&&state.verified?'Checks passed':status==='complete'&&state.evidence_checked?'Answered · source retrieved':status==='running'?'Working':status;
  $('#progress-summary').textContent=[state.goal?.slice(0,300),status==='running'?state.next_action:''].filter(Boolean).join('\n');
  $('#progress-steps').replaceChildren();
  for(const step of state.steps||[]){const item=document.createElement('li');item.textContent=(step.done?'✓ ':'○ ')+step.title;item.className=step.done?'step-done':'';$('#progress-steps').append(item);}
}
async function refreshSessions() {
  const list=await api('/api/sessions');$('#session-count').textContent=list.length;$('#sessions').replaceChildren();
  list.forEach(s=>{const b=document.createElement('button');b.className='session-item'+(s.id===sessionId?' active':'');
    const icon=document.createElement('span');icon.textContent='◌';const t=document.createElement('span');t.textContent=s.title;
    b.append(icon,t);b.addEventListener('click',()=>loadSession(s.id).catch(e=>toast(e.message)));$('#sessions').append(b);});return list;
}
async function createSession() {
  if(currentJob) return toast('Stop the running task before switching sessions.');
  const s=await api('/api/sessions','POST',{});await loadSession(s.id);$('#prompt').focus();
}
async function loadSession(id) {
  if(currentJob && sessionId!==id) return toast('Stop the running task before switching sessions.');
  source?.close();const s=await api('/api/sessions/'+id);sessionId=id;localStorage.setItem('tiny-dancer-session',id);
  $('#session-title').textContent=s.title;$('#messages').replaceChildren();live=null;
  currentFolder=s.cwd;$('#working-folder').textContent=s.cwd;$('#working-folder').title=s.cwd;
  latestJob=s.jobs[0]||null;showProgress(latestJob?.checkpoint,latestJob?.status);
  const running=s.jobs.find(j=>j.status==='running');
  for(const m of s.messages){const h=JSON.parse(m.harmony);if(h.channel==='analysis'||m.role==='developer'||(running&&m.created>=running.created&&m.role!=='user'))continue;
    if(h.recipient?.startsWith('functions.')) toolEvent(h.recipient.slice(10),m.text,undefined,true);
    else if(m.role==='tool') toolEvent((h.name || 'tool').replace(/^functions\./,''),'',m.text,true);
    else {const checked=s.jobs.find(j=>j.checkpoint?.data_check&&j.checkpoint.summary===m.text);message(m.role,m.text,checked?.checkpoint.data_check.export?'export':Boolean(checked));}
  }
  if(!s.messages.length){$('#messages').innerHTML=welcomeHTML;bindSuggestions();}
  currentJob=running?.id||null;busy(!!running);
  if(running) attach(running.id);
  else if(s.jobs[0] && ['interrupted','limited','failed','cancelled','paused','blocked'].includes(s.jobs[0].status)) $('#task-status').textContent='Task '+s.jobs[0].status+' · progress saved';
  else if(s.jobs[0]?.status==='complete') $('#task-status').textContent=s.jobs[0].checkpoint?.verified?'Complete · checks passed':s.jobs[0].checkpoint?.evidence_checked?'Answered · source retrieved':'Complete · conversation saved';
  else $('#task-status').textContent='Ready when you are';
  await refreshSessions();scroll();
}
function attach(job) {
  source?.close();const connection=new EventSource('/api/jobs/'+job+'/events');source=connection;
  let lastTool=null;
  source.onmessage=(e)=>{const {kind,data}=JSON.parse(e.data);
    if(kind==='inference'){$('#task-status').textContent=`Processing ${data.prompt_tokens} tokens · ${data.reused_tokens} reused`;live=null;}
    if(kind==='delta'){if(!live){live=message('assistant');live.classList.add('streaming');}live.textContent+=data.text;scroll();}
    if(kind==='progress') $('#task-status').textContent=`Generating · ${data.tokens} tokens · ${data.seconds}s`;
    if(kind==='tool_start'){live?.classList.remove('streaming');live=null;lastTool=toolEvent(data.name,data.arguments);activity(data.name,'Running on your computer');$('#task-status').textContent='Running '+data.name+'…';}
    if(kind==='tool_result'){if(lastTool){lastTool.querySelector('summary').textContent='⌘ '+data.name+' · finished';lastTool.querySelector('pre').textContent+='\n\n'+data.result;
      try{const r=JSON.parse(data.result);if(r.artifact){const a=document.createElement('a');a.href=r.artifact;a.target='_blank';a.rel='noopener';a.textContent='Open saved output ↗';lastTool.append(a);}}catch{}
      lastTool=null;}else toolEvent(data.name,'',data.result);activity(data.name,'Result saved');}
    if(kind==='metrics'){$('#task-status').textContent=`${data.completion_tokens} tokens · ${data.total_seconds}s · ${(data.decode_tokens_per_s||0).toFixed(1)} tok/s`;}
    if(kind==='context') activity('Context updated',data.message);
    if(kind==='checkpoint') showProgress(data,'running');
    if(kind==='continuation'||kind==='resumed'){activity('Continuing',data.message);$('#task-status').textContent='Continuing · progress saved';}
    if(kind==='resumed') document.querySelectorAll('#messages .error-message').forEach(el=>{el.textContent+=' (previous attempt; task resumed)';el.classList.add('historical-error');});
    if(kind==='paused'){$('#task-status').textContent=data.message;activity('Task '+data.status,data.message);$('#progress-label').textContent=data.status;}
    if(kind==='error'){const d=document.createElement('div');d.className='error-message';d.textContent=data.message;$('#messages').append(d);$('#task-status').textContent='Task needs attention · history saved';activity('Task paused',data.message);scroll();}
    if(kind==='done'){if(live){renderAnswer(live,live.textContent);if(data.answer_origin==='checked_lookup')live.previousElementSibling.textContent='✳ TINY DANCER · CHECKED DATA LOOKUP';if(data.answer_origin==='checked_export')live.previousElementSibling.textContent='✳ TINY DANCER · CHECKED DATA EXPORT';}$('#task-status').textContent=data.verified?'Complete · checks passed':data.evidence_checked?'Answered · source retrieved':'Complete · conversation saved';activity('Complete',data.steps+' inference steps');}
    if(kind==='cancelled'){$('#task-status').textContent=data.message;activity('Stopped','Completed actions remain saved');}
  };
  source.addEventListener('closed',()=>{connection.close();if(source!==connection)return;live?.classList.remove('streaming');currentJob=null;busy(false);loadSession(sessionId).catch(e=>toast(e.message));refreshStatus();});
  source.onerror=()=>{$('#task-status').textContent='Reconnecting to the local workspace…';};
}
$('#composer').addEventListener('submit',async(e)=>{e.preventDefault();const prompt=$('#prompt').value.trim();if(!prompt||currentJob)return;
  try {if(!sessionId)await createSession();const {job}=await api('/api/sessions/'+sessionId+'/tasks','POST',{prompt,mode:$('#mode').value,max_tokens:$('#budget').value==='auto'?null:Number($('#budget').value),reasoning_effort:$('#thinking').value,run_until_done:$('#mode').value==='agent'&&$('#run-until-done').checked});
    message('user',prompt);$('#prompt').value='';currentJob=job;busy(true);$('#task-status').textContent='Loading the local model…';attach(job);await refreshSessions();
  }catch(err){toast(err.message);}});
$('#prompt').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();$('#composer').requestSubmit();}});
$('#new-session').addEventListener('click',()=>createSession().catch(e=>toast(e.message)));
$('#stop').addEventListener('click',async()=>{if(currentJob){try{await api('/api/jobs/'+currentJob+'/stop','POST',{});}catch(e){toast(e.message);}}});
$('#resume-task').addEventListener('click',async()=>{if(!latestJob||currentJob)return;const button=$('#resume-task');button.disabled=true;try{await api('/api/jobs/'+latestJob.id+'/resume','POST',{max_tokens:$('#budget').value==='auto'?null:Number($('#budget').value),reasoning_effort:$('#thinking').value,run_until_done:$('#run-until-done').checked});await loadSession(sessionId);}catch(e){toast(e.message);}finally{button.disabled=false;}});
const savedBudget=localStorage.getItem('tiny-dancer-budget');
$('#budget').value=['auto','512','1024','2048'].includes(savedBudget)?savedBudget:'auto';
$('#budget').addEventListener('change',()=>localStorage.setItem('tiny-dancer-budget',$('#budget').value));
const savedThinking=localStorage.getItem('tiny-dancer-thinking');
$('#thinking').value=['auto','low','medium','high'].includes(savedThinking)?savedThinking:'auto';
$('#thinking').addEventListener('change',()=>localStorage.setItem('tiny-dancer-thinking',$('#thinking').value));
$('#run-until-done').checked=localStorage.getItem('tiny-dancer-until-done')!=='false';
$('#run-until-done').addEventListener('change',()=>localStorage.setItem('tiny-dancer-until-done',String($('#run-until-done').checked)));
$('#mode').addEventListener('change',()=>$('.run-policy').classList.toggle('hidden',$('#mode').value==='chat'));
$('#open-editor').addEventListener('click',async()=>{try{if(!sessionId)await createSession();await api('/api/sessions/'+sessionId+'/editor','POST',{});toast('Working folder opened in Code OSS.');}catch(e){toast(e.message);}});
$('#change-folder').addEventListener('click',async()=>{if(currentJob)return toast('Stop the task before changing its working folder.');const path=window.prompt('Working folder (an existing absolute path):',currentFolder);if(!path)return;try{if(!sessionId)await createSession();await api('/api/sessions/'+sessionId,'PATCH',{cwd:path});await loadSession(sessionId);}catch(e){toast(e.message);}});
async function updateView(){
  if(!$('#viewer').open)return;
  try{const data=await api('/api/observe?source='+$('#view-source').value);if(!$('#viewer').open)return;
    $('#view-caption').textContent=data.available?(data.url||'Desktop snapshot')+' · refreshes every 3 seconds':data.message;
    $('#view-image').classList.toggle('hidden',!data.available);if(data.available)$('#view-image').src=data.artifact+'?t='+data.at;
  }catch(e){$('#view-caption').textContent=e.message;}
  if($('#viewer').open)viewTimer=setTimeout(updateView,3000);
}
$('#watch').addEventListener('click',()=>{$('#viewer').showModal();clearTimeout(viewTimer);updateView();});
$('#close-viewer').addEventListener('click',()=>$('#viewer').close());
$('#viewer').addEventListener('close',()=>clearTimeout(viewTimer));
$('#view-source').addEventListener('change',()=>{clearTimeout(viewTimer);updateView();});
$('#export').addEventListener('click',()=>{if(sessionId)window.location.href='/api/sessions/'+sessionId+'/export';else toast('Start a conversation first.');});
function bindSuggestions(){document.querySelectorAll('[data-prompt]').forEach(b=>b.addEventListener('click',()=>{$('#prompt').value=b.dataset.prompt;$('#prompt').focus();}));}
const welcomeHTML=$('#messages').innerHTML;bindSuggestions();
const duration = (seconds) => `${Math.floor(seconds/60)}:${String(Math.floor(seconds%60)).padStart(2,'0')}`;
function polledProgress(task) {
  const {kind,data}=task.progress||{};
  let label=kind==='progress'?`Model working · ${data.tokens} tokens`:kind==='inference'?`Processing ${data.prompt_tokens} tokens · ${data.reused_tokens} reused`:kind==='tool_start'?`Running ${data.name}`:'Loading the local model';
  label+=` · ${duration(task.elapsed_seconds)} elapsed`;
  if(task.checkpoint?.max_seconds)label+=` · ${duration(Math.max(0,task.checkpoint.max_seconds-task.elapsed_seconds))} left`;
  if(task.checkpoint?.run_until_done)label+=' · until done';
  $('#task-status').textContent=label;
}
async function reconcileTask(s) {
  if(reconciling||!sessionId)return;
  if(!currentJob) {
    if(s.task?.session===sessionId&&s.task.status==='running') {
      reconciling=true;try{await loadSession(sessionId);}finally{reconciling=false;}
    }
    return;
  }
  const job=currentJob;
  const task=s.task?.id===job?s.task:await api('/api/jobs/'+job+'/progress');
  if(currentJob!==job)return;
  if(task.status==='running'){polledProgress(task);return;}
  // SSE may be suspended in an old/background tab. Durable server state wins.
  reconciling=true;
  try{source?.close();source=null;currentJob=null;busy(false);await loadSession(sessionId);}
  finally{reconciling=false;}
}
async function refreshStatus(){try{const s=await api('/api/status');$('#engine-state').textContent=s.model_installed?s.engine.toUpperCase():'INSTALLING MODEL';
  $('#ram').textContent=gb(s.ram.used)+' / '+gb(s.ram.total);$('#ram-meter').style.width=(s.ram.used/s.ram.total*100)+'%';$('#disk').textContent=gb(s.disk.free);$('#cpu').textContent=s.cpu_percent+'%';$('#engine-label').textContent=s.config.backend==='llama.cpp'?'Native MXFP4':'Expert streaming';$('#runtime-description').textContent=s.runtime;$('#compute-mode').textContent=s.config.backend==='llama.cpp'?'CPU + NVIDIA CUDA · native model weights':s.config.gpu?'CPU + NVIDIA CUDA · disk expert cache':'CPU · disk expert cache';
  if(!s.model_installed&&!currentJob)$('#task-status').textContent='Model installation in progress · setup logs are saved on GameDrive';
  await reconcileTask(s);
}catch{$('#engine-state').textContent='OFFLINE';}}
await refreshStatus();setInterval(refreshStatus,4000);
const list=await refreshSessions();const saved=localStorage.getItem('tiny-dancer-session');
if(list.some(s=>s.id===saved))await loadSession(saved);else if(list.length)await loadSession(list[0].id);
