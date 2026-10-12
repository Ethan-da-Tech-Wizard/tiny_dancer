# SPDX-License-Identifier: Apache-2.0
"""Validate real read-only lookups, without starting or steering model tasks."""
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.language_tools import lookup


async def main():
    rows = []
    checks = [
        ('python',{'action':'package','package':'httpx','version':'0.28.1'}),
        ('rust',{'action':'package','package':'serde','version':'1.0.219'}),
        ('python',{'action':'docs','url':'https://docs.python.org/3.12/library/pathlib.html#pathlib.Path.read_text'}),
        ('rust',{'action':'docs','url':'https://doc.rust-lang.org/stable/std/result/enum.Result.html#method.unwrap'}),
        ('python',{'action':'dependencies','path':str(ROOT)}),
    ]
    for language,args in checks:
        started = time.monotonic()
        try:
            result = await lookup(language,args,ROOT,ROOT/'run/artifacts',ROOT/'cache/language-lookups')
            saved = json.loads(Path(result['local_path']).read_text())
            if args['action']=='package':
                assert saved['version']==args['version'] and saved['dependencies']
            elif args['action']=='docs':
                assert len(saved['text'])>100
                assert ('panic' in saved['text']) if language=='rust' else ('decoded contents' in saved['text'])
            else:
                assert any(m['path'].endswith('requirements.lock.txt') for m in saved['manifests'])
                assert saved['network_used'] is False
            row = {'language':language,'args':args,'ok':True,'seconds':round(time.monotonic()-started,3),
                   'source':result['source'],'artifact':result['artifact'],'cached':result.get('cached'),
                   'dependencies_count':len(saved.get('dependencies',[])),'text_chars':len(saved.get('text',''))}
        except Exception as exc:
            row = {'language':language,'args':args,'ok':False,'error':type(exc).__name__+': '+str(exc),'seconds':round(time.monotonic()-started,3)}
        rows.append(row)
        print(json.dumps(row),flush=True)
    report = {'at':time.time(),'checks':rows,'passed':all(row['ok'] for row in rows),
              'scope':'Actual lookup HTTP/file handlers, not a native GPT-OSS end-to-end coding run.'}
    (ROOT/'docs/language-lookup-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    if not report['passed']: raise SystemExit(1)


if __name__=='__main__': asyncio.run(main())
