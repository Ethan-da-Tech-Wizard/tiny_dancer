"""Actual local-model E2E: native function calls create and read back a file."""
import json
import shlex
import time
from pathlib import Path
import httpx

ROOT=Path('/mnt/GameDrive/tiny_dancer')
expected='Tiny Dancer local agent verified.\n'
path=ROOT/'workspace/agent-verification.txt'
with httpx.Client(base_url='http://127.0.0.1:3210',timeout=20) as client:
    client.get('/').raise_for_status()
    session=client.post('/api/sessions',json={'title':'Validation · local computer agent'}).json()
    check='python3 -c ' + shlex.quote(f'from pathlib import Path; assert Path({str(path)!r}).read_text() == {expected!r}')
    prompt=f'Use write_file to create {path} containing exactly "Tiny Dancer local agent verified." followed by a newline. Then use read_file to verify the contents. Finish using finish_task with this verification command: {check}'
    response=client.post(f"/api/sessions/{session['id']}/tasks",json={'prompt':prompt,'mode':'agent','max_tokens':1024})
    response.raise_for_status();job=response.json()['job']
    print('Validation job:',job,flush=True)
    last_id=0
    for _ in range(3600):
        data=client.get('/api/jobs/'+job).json()
        for e in data['events']:
            if e['id']>last_id:
                last_id=e['id']
                if e['kind']!='delta':print(e['kind'],e['data'],flush=True)
        if data['status']!='running':break
        time.sleep(2)
    if data['status']=='running':
        client.post('/api/jobs/'+job+'/stop',json={})
        raise RuntimeError('Validation timeout; model task stopped')
    result={'job':job,'session':session['id'],'status':data['status'],'file_exists':path.exists(),
        'file_correct':path.exists() and path.read_text()==expected,
        'verified':bool(data.get('checkpoint',{}).get('verified')),
        'tools':[json.loads(e['data'])['name'] for e in data['events'] if e['kind']=='tool_start'],
        'metrics':[json.loads(e['data']) for e in data['events'] if e['kind']=='metrics']}
    (ROOT/'docs/agent-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)
    assert result['status']=='complete',result
    assert result['file_correct'],result
    assert result['verified'],result
    assert 'write_file' in result['tools'] and 'read_file' in result['tools'],result
