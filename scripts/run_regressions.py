# SPDX-License-Identifier: Apache-2.0
"""Run real regressions and preserve named outcomes in a unique results report."""
import hashlib
import json
import sys
import time
import traceback
import unittest
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.validation_results import refresh_results


def main():
    started=time.monotonic();now=datetime.now(timezone.utc)
    directory=ROOT/'docs/validation/runs';directory.mkdir(parents=True,exist_ok=True)
    path=directory/(now.strftime('%Y%m%dT%H%M%S%fZ')+'.json')
    report={'title':'Batching, completion and full regressions','started_at':now.isoformat(),'status':'running',
            'scope':'Scripted-model regression fixtures plus actual file, shell, browser and desktop tool checks. No native generation in this suite.',
            'results':[],'tests_run':0,'failures':0,'errors':0,'skipped':0}
    digest=hashlib.sha256()
    sources=[]
    for folder in ('app','tests','scripts'): sources.extend((ROOT/folder).rglob('*.py'))
    sources.extend((ROOT/'app/static').glob('*'));sources.append(ROOT/'config.json')
    for source in sorted(p for p in sources if p.is_file()): digest.update(str(source.relative_to(ROOT)).encode());digest.update(source.read_bytes())
    report['source_sha256']=digest.hexdigest()
    def save():
        temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(path)
    class Results(unittest.TextTestResult):
        def startTest(self,test): self.test_started=time.monotonic();super().startTest(test)
        def record(self,test,status,detail=''):
            report['results'].append({'test':test.id(),'status':status,'seconds':round(time.monotonic()-self.test_started,4),'detail':detail})
        def addSuccess(self,test): super().addSuccess(test);self.record(test,'passed')
        def addFailure(self,test,err): super().addFailure(test,err);self.record(test,'failed',self._exc_info_to_string(err,test))
        def addError(self,test,err): super().addError(test,err);self.record(test,'error',self._exc_info_to_string(err,test))
        def addSkip(self,test,reason): super().addSkip(test,reason);self.record(test,'skipped',reason)
        def addSubTest(self,test,subtest,err):
            super().addSubTest(test,subtest,err)
            if err: self.record(subtest,'failed',self._exc_info_to_string(err,test))
        def stopTest(self,test):
            super().stopTest(test)
            report.update(tests_run=self.testsRun,failures=len(self.failures),errors=len(self.errors),skipped=len(self.skipped),seconds=round(time.monotonic()-started,3))
            save()
    save();refresh_results(ROOT)
    try: suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),top_level_dir=str(ROOT))
    except Exception:
        report.update(status='failed',errors=1,seconds=round(time.monotonic()-started,3),finished_at=datetime.now(timezone.utc).isoformat())
        report['results'].append({'test':'runner.discovery','status':'error','detail':traceback.format_exc()})
        save();refresh_results(ROOT);raise
    result=unittest.TextTestRunner(verbosity=2,resultclass=Results).run(suite)
    report.update(status='passed' if result.wasSuccessful() else 'failed',tests_run=result.testsRun,
                  failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),seconds=round(time.monotonic()-started,3),
                  finished_at=datetime.now(timezone.utc).isoformat())
    save();refresh_results(ROOT)
    print('Saved per-test report:',path,flush=True)
    if not result.wasSuccessful(): raise SystemExit(1)


if __name__=='__main__':main()
