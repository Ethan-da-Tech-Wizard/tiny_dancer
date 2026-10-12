# SPDX-License-Identifier: Apache-2.0
"""Read-only test summaries and a bounded allowlist of their saved evidence."""
import json
import hashlib
import re
import uuid
from datetime import datetime,timezone
from pathlib import Path

NATIVE_REPORTS=[('final-native-repair-validation.json','Final deployed arithmetic repair','Frozen seeded arithmetic task on the final source/output-reserve harness; Auto initial allowance2048, no runtime hints. Not a fresh coding implementation.'),
                ('native-coding-validation.json','Independent CSV implementation','Fresh goal and input only; no implementation, tests or operator recovery notes.'),
                ('native-harness-validation.json','Seeded repair before batching','Existing bug and tests; actual local GPT-OSS execution without interventions.'),
                ('batching-native-validation.json','Seeded repair after batching','Same initial repair prompt and test inputs; historical single-run comparison, not a controlled general speed benchmark.'),
                ('hardening-coding-validation.json','Fresh CSV implementation after hardening','Original goal and input only; independent CLI and friendly-error checks after native termination, no runtime hints.'),
                ('precision-repair-validation.json','Exact-money repair after runner hardening','Native repair with operator-seeded acceptance tests; not an unassisted implementation. No runtime hints or implementation injected.'),
                ('answer-completion-validation.json','Checked Sunday-score answer','Native tool selection and source-checked host formatting, rather than model-generated scores.'),
                ('score-export-before.json','Scores before file-output fix','Original user run; completion was reported despite the missing requested workspace JSON/editor action.'),
                ('score-export-validation.json','Scores → JSON → Code OSS','Exact user request; verify saved data against a separate source retrieval and actual editor action.')]
LEGACY_LOGS=['curated-harness-final-tests.log','curated-harness-tests.log','stability-tests.log','language-tools-tests.log','batching-first-regressions.log','batching-targeted-tests.log',
             'auth-tests.log','final-tests.log','sustained-agent-tests.log','tool-tests.log','harmony-tests.log','sse-tests.log','continuation-stability-tests.log',
             'native-final-guard-tests.log','curated-focused-tests.log','prompt-cache-tests.log','patch-tests.log','hardening-capability-diagnosis.log','hardening-json-intent-diagnosis.log','hardening-project-scan-diagnosis.log','hardening-evidence-diagnosis.log','hardening-finish-check-diagnosis.log','coding-acceptance-tests.log']
INTEGRATION_REPORTS=[('results-ui-validation.json','Results page and authentication','Live desktop/mobile browser, evidence links, authentication and hostile saved-text rendering.'),
                     ('score-export-ui-validation.json','Completed score export interface','Actual completed user session, saved-file label, controls and desktop/mobile layout.'),
                     ('gpu-prefill-investigation.json','Existing CUDA numeric self-test','Existing INT8 output-head and INT4 expert checks; no new GPU prefill kernel or full-task speed claim.')]


def archive_report(root,name,kind,title,scope):
    """Preserve a completed evaluation before its current-report path is reused."""
    root=Path(root);source=root/'docs'/name;data=load_json(source)
    if not data or not isinstance(data.get('passed'),bool) or data.get('status') in ('starting','queued','running'):
        raise ValueError('Only completed evaluations can be archived')
    directory=root/'docs/validation/evaluations';directory.mkdir(parents=True,exist_ok=True)
    path=directory/(Path(name).stem+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
    data['archive_metadata']={'source':name,'kind':kind,'title':title,'scope':scope,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
    with path.open('x') as output: output.write(json.dumps(data,indent=2)+'\n')
    return path


def evaluation_row(identifier,data,title,scope,kind):
    report_kind=kind
    # Historical writers used several categories; the UI has two evidence
    # lanes. These aliases keep those saved rows visible without rewriting them.
    kind={'regression':'automated','tools':'automated','integration':'automated',
          'fixtures':'automated','evaluation':'native'}.get(kind,kind)
    metrics=data.get('metrics',[])
    lifecycle=data.get('status','unknown')
    # A submission/completion boundary is not a passing independent verdict.
    if data.get('passed') is True: status='passed'
    elif lifecycle in ('starting','queued','running','paused','blocked','stopped','cancelled','canceled','interrupted','limited'): status=lifecycle
    elif data.get('passed') is False: status='failed'
    else: status=lifecycle
    samples=data.get('samples',[])
    live=samples[-1] if samples and status=='running' else {}
    first=next((sample['progress']['data'].get('prompt_tokens') for sample in samples if (sample.get('progress') or {}).get('kind')=='inference'),None)
    event_turns=sum(event.get('type')=='inference' for event in data.get('events',[]) if isinstance(event,dict))
    row={'id':identifier,'kind':kind,'report_kind':report_kind,'title':title,'at':data.get('started_at',data.get('at',data.get('checked_at',''))),'status':status,'scope':scope,
         'seconds':data.get('job_elapsed_seconds',data.get('elapsed_seconds',data.get('seconds',live.get('elapsed_seconds')))),
         'prompt_tokens':metrics[0].get('prompt_tokens') if metrics else first,
         'turns':data.get('checkpoint',{}).get('turns',live.get('turns',len(metrics) if metrics else event_turns or None)),
         'interventions':len(data.get('operator_interventions',[])),'note':data.get('assessment_note','')}
    if kind=='automated': row['tests']=len(data['checks']) if isinstance(data.get('checks'),(dict,list)) else None
    if isinstance(data.get('tests'),int): row['tests']=data['tests']
    return row


def load_json(path):
    if not path.is_file() or path.stat().st_size>2_000_000: return None
    try: return json.loads(path.read_text())
    except (OSError,ValueError): return None


def collect_results(root):
    root=Path(root);items=[];files={}
    for path in sorted((root/'docs/validation/runs').glob('*.json')):
        data=load_json(path)
        if not data: continue
        identifier='run-'+path.stem;files[identifier]=str(path.relative_to(root))
        items.append({'id':identifier,'kind':'automated','title':data.get('title','Regression suite'),'at':data['started_at'],
                      'status':data['status'],'tests':data.get('tests_run',0),'failures':data.get('failures',0),'errors':data.get('errors',0),
                      'skipped':data.get('skipped',0),'seconds':data.get('seconds'),'scope':data['scope']})
    for name in LEGACY_LOGS:
        path=root/'logs'/name
        if not path.is_file(): continue
        text=path.read_text(errors='replace')[-12000:]
        summaries=list(re.finditer(r'Ran (\d+) tests? in ([\d.]+)s\s*\n\s*\n(OK|FAILED[^\n]*)',text))
        if not summaries: continue
        summary=summaries[-1];identifier='log-'+path.stem;files[identifier]=str(path.relative_to(root))
        items.append({'id':identifier,'kind':'automated','title':path.stem.replace('-',' '),'at':datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),
                      'status':'passed' if summary[3]=='OK' else 'failed','tests':int(summary[1]),'seconds':float(summary[2]),
                      'scope':'Archived runner log; includes scripted model fixtures and real local tool tests. Does not establish autonomous model accuracy.'})
    for name,title,scope in NATIVE_REPORTS:
        path=root/'docs'/name;data=load_json(path)
        if not data: continue
        identifier='native-'+path.stem;files[identifier]=str(path.relative_to(root))
        items.append(evaluation_row(identifier,data,title,scope,'native'))
    for name,title,scope in INTEGRATION_REPORTS:
        path=root/'docs'/name;data=load_json(path)
        if not data: continue
        identifier='integration-'+path.stem;files[identifier]=str(path.relative_to(root))
        items.append(evaluation_row(identifier,data,title,scope,'automated'))
    for path in sorted((root/'docs/validation/evaluations').glob('*.json')):
        data=load_json(path)
        if not data or not isinstance(data.get('archive_metadata'),dict): continue
        metadata=data['archive_metadata'];current=root/'docs'/metadata['source']
        # Suppress duplicates only when the current report is actually listed.
        # New report types otherwise lost their only visible evidence row.
        if str(current.relative_to(root)) in files.values() and current.is_file() and hashlib.sha256(current.read_bytes()).hexdigest()==metadata['source_sha256']: continue
        identifier='archive-'+path.stem;files[identifier]=str(path.relative_to(root))
        items.append(evaluation_row(identifier,data,metadata['title'],metadata['scope'],metadata['kind']))
    items.sort(key=lambda item:item['at'],reverse=True)
    return {'updated_at':datetime.now(timezone.utc).isoformat(),'results':items,'evidence':files}


def evidence_path(root,identifier,index):
    name=index.get('evidence',{}).get(identifier)
    if not name: raise ValueError('Unknown test evidence')
    root=Path(root).resolve();path=(root/name).resolve()
    if not path.is_relative_to(root) or path.suffix not in ('.json','.log') or not path.is_file(): raise ValueError('Invalid test evidence path')
    return path


def refresh_results(root):
    root=Path(root);index=collect_results(root);folder=root/'docs/validation';folder.mkdir(parents=True,exist_ok=True)
    temp=folder/('index-'+uuid.uuid4().hex+'.tmp');temp.write_text(json.dumps(index,indent=2)+'\n');temp.replace(folder/'index.json')
    rows=['# Test results','', 'Open the readable local results page at http://127.0.0.1:3210/results. This file and saved evidence are on the GameDrive.',
          '', 'Automated regressions include scripted model fixtures and actual tool execution. Native evaluations run the real local GPT-OSS model. Passing tests verify their assertions, rather than arbitrary task completeness.',
          '', 'The repair comparison uses the same initial prompt and seeded files at different times. CPU load, disk warmth and model decisions can differ; it is not a universal speed multiplier.',
          '', '| Result | Status | Tests / native turns | Seconds | Scope | Evidence |','| --- | --- | ---: | ---: | --- | --- |']
    for item in index['results']:
        count=item.get('tests',item.get('turns','—'));count='—' if count is None else count;seconds=item.get('seconds');duration=f'{seconds:.2f}' if isinstance(seconds,(int,float)) else '—'
        evidence=Path('..')/index['evidence'][item['id']]
        scope=item['scope'].replace('|','/').replace('\n',' ')
        rows.append(f"| {item['title']} | **{item['status']}** | {count} | {duration} | {scope} | [report]({evidence.as_posix()}) |")
    rows+=['','Run all regressions and archive every individual outcome:','','```bash','.venv/bin/python scripts/run_regressions.py','```','',
           'Refresh the index after other evaluations: `.venv/bin/python scripts/refresh_test_results.py`. New regression runs get unique timestamps; failed and historical results remain available.']
    temp=folder/('readable-'+uuid.uuid4().hex+'.tmp');temp.write_text('\n'.join(rows)+'\n');temp.replace(root/'docs/TEST_RESULTS.md')
    return index
