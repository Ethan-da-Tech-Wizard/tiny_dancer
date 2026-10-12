# SPDX-License-Identifier: Apache-2.0
"""Post-terminal independent boundary checks; never supply model hints or edits."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.validation_results import archive_report,refresh_results
from app.verification import source_hashes
from scripts.evaluate_hardening_suite import runtime_digest


def probe(folder,width):
    folder=Path(folder).resolve();whole=('1234567890'*((width+9)//10))[:width]
    outcomes={}
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        for name,amounts,expected in (
            ('signed',[whole+'.99','-'+whole+'.00','0.02'],{'huge':'1.01'}),
            ('total',[whole+'.01','0.02'],{'huge':whole+'.03'})):
            path=Path(temporary)/(name+'.csv')
            path.write_text('category,amount\n'+'\n'.join('huge,'+v for v in amounts)+'\n')
            try:
                result=subprocess.run(['/usr/bin/python3',str(folder/'summarize.py'),str(path)],cwd=folder,capture_output=True,text=True,timeout=15)
                try:actual=json.loads(result.stdout)
                except ValueError:actual=None
                outcomes[name]={'passed':result.returncode==0 and actual==expected,'exit_code':result.returncode,
                    'stdout_chars':len(result.stdout),'actual_preview':str(actual)[:180],'stderr':result.stderr[-800:]}
            except subprocess.TimeoutExpired:
                outcomes[name]={'passed':False,'timed_out':True}
    return outcomes


def main():
    criteria_path=ROOT/'docs/native-money-extended-criteria.json'
    criteria=json.loads(criteria_path.read_text());native=json.loads((ROOT/'docs/precision-repair-retest-validation.json').read_text())
    if native.get('status') in ('running','starting'):raise SystemExit('Refusing boundary grading while native task is active')
    if criteria.get('width')!=12000:raise SystemExit('Declared boundary changed')
    native_sha=native.get('runtime_sha256_before')
    paths=list(native.get('checkpoint',{}).get('auto_verification',{}).get('files_sha256',{}))
    before=source_hashes(paths)
    cases=probe(native['cwd'],criteria['width'])
    checks={'declared_before_native':datetime.fromisoformat(criteria['declared_at'])<datetime.fromisoformat(native['started_at']),
        'native_complete':native.get('status')=='complete' and native.get('passed') is True,
        'runtime_frozen':runtime_digest()==native_sha==native.get('runtime_sha256_after'),
        'source_frozen':bool(before) and before==source_hashes(paths)==native['checkpoint']['auto_verification']['files_sha256'],
        'signed':cases['signed']['passed'],'total':cases['total']['passed']}
    report={'title':'Declared additional exact-money boundary checks','status':'complete','passed':all(checks.values()),
        'started_at':datetime.now(timezone.utc).isoformat(),'scope':'Independent post-terminal CLI checks. No model call, live hint or product edit. Original frozen checks remain unchanged.',
        'native_job':native.get('job'),'runtime_sha256':native_sha,'criteria_sha256':hashlib.sha256(criteria_path.read_bytes()).hexdigest(),
        'width':criteria['width'],'checks':checks,'cases':cases}
    path=ROOT/'docs/money-precision-boundary-validation.json'
    if path.exists():archive_report(ROOT,path.name,'native','Previous additional precision boundary',report['scope'])
    path.write_text(json.dumps(report,indent=2)+'\n')
    archive_report(ROOT,path.name,'native',report['title'],report['scope']);refresh_results(ROOT)
    print(json.dumps({'passed':report['passed'],'checks':checks}),flush=True)
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
