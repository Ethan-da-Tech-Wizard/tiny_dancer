# SPDX-License-Identifier: Apache-2.0
"""Terminal client with continuous Agent work and incremental public events."""
import argparse
import json
import sys
import time
from pathlib import Path
import httpx

ROOT=Path('/mnt/GameDrive/tiny_dancer')


def parse_options(argv=None):
    parser=argparse.ArgumentParser(description='Ask the local Tiny Dancer computer agent')
    parser.add_argument('prompt',nargs='*')
    parser.add_argument('--session',help='Start a new goal in an existing session')
    parser.add_argument('--cwd',default=str(ROOT/'workspace'))
    parser.add_argument('--chat',action='store_true')
    parser.add_argument('--max-tokens',type=int,default=None,help='Starting allowance; omitted uses Auto')
    parser.add_argument('--resume-job',help='Resume a saved task')
    policy=parser.add_mutually_exclusive_group()
    policy.add_argument('--until-done',dest='run_until_done',action='store_const',const=True,default=None)
    policy.add_argument('--bounded',dest='run_until_done',action='store_const',const=False,help='Use bounded work; new Agent tasks otherwise continue until checked completion or a blocker')
    args=parser.parse_args(argv)
    if not args.prompt and not args.resume_job:parser.error('Provide a prompt or --resume-job')
    return args


def task_options(args,resume=False):
    body={}
    if not resume or args.max_tokens is not None:body['max_tokens']=args.max_tokens
    if not resume:body.update(prompt=' '.join(args.prompt),mode='chat' if args.chat else 'agent',run_until_done=args.run_until_done if args.run_until_done is not None else not args.chat)
    elif args.run_until_done is not None:body['run_until_done']=args.run_until_done
    return body


def watch(client,job,stdout=sys.stdout,stderr=sys.stderr):
    cursor=0
    while True:
        try:
            with client.stream('GET','/api/jobs/'+job+'/events',params={'after':cursor},timeout=None) as response:
                response.raise_for_status();event_id=cursor
                for line in response.iter_lines():
                    if line.startswith('id:'):event_id=int(line[3:].strip())
                    elif line.startswith('data:'):
                        event=json.loads(line[5:].strip())
                        if not event.get('kind') or event_id<=cursor:continue
                        cursor=event_id;payload=event['data']
                        if event['kind']=='delta':print(payload['text'],end='',file=stdout,flush=True)
                        elif event['kind'] in ('tool_start','error','cancelled'):
                            print('\n['+event['kind']+'] '+json.dumps(payload),file=stderr,flush=True)
            response=client.get('/api/jobs/'+job+'/progress');response.raise_for_status();status=response.json()['status']
            if status!='running':return 0 if status=='complete' else 1
        except httpx.TransportError:
            time.sleep(.5)


def main():
    args=parse_options()
    with httpx.Client(base_url='http://127.0.0.1:3210',trust_env=False,timeout=20) as client:
        client.get('/').raise_for_status();sid=args.session
        if args.resume_job:
            response=client.post('/api/jobs/'+args.resume_job+'/resume',json=task_options(args,True));response.raise_for_status()
            state=client.get('/api/jobs/'+args.resume_job+'/progress');state.raise_for_status();sid=state.json()['session']
        else:
            if not sid:
                response=client.post('/api/sessions',json={'cwd':args.cwd});response.raise_for_status();sid=response.json()['id']
            response=client.post('/api/sessions/'+sid+'/tasks',json=task_options(args));response.raise_for_status()
        job=response.json()['job'];print('Session: '+sid+'\nTask: '+job,file=sys.stderr,flush=True)
        try:
            code=watch(client,job);print();return code
        except KeyboardInterrupt:
            try:
                response=client.post('/api/jobs/'+job+'/stop',json={});response.raise_for_status()
                print('\nStopped; history saved.',file=sys.stderr)
            except httpx.HTTPError:print('\nCould not confirm Stop. Saved task: '+job,file=sys.stderr)
            return 130


if __name__=='__main__':raise SystemExit(main())
