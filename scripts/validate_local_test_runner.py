# SPDX-License-Identifier: Apache-2.0
"""Actual project pytest, fixtures, failure and zero-suite checks; no inference."""
import asyncio
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.tools import ComputerTools
from app.verification import test_summary
from app.validation_results import archive_report,refresh_results


async def main():
    with tempfile.TemporaryDirectory(dir=ROOT/'workspace',prefix='runner-validation-') as temporary:
        folder=Path(temporary)
        (folder/'test_good.py').write_text('''from pathlib import Path
def test_fixture(tmp_path):
 assert str(tmp_path).startswith('/mnt/GameDrive/tiny_dancer/')
 (tmp_path/'answer.txt').write_text('42')
 assert (tmp_path/'answer.txt').read_text()=='42'
def test_sum():assert 6*7==42
''')
        (folder/'test_bad.py').write_text('def test_failure():assert 6*7==41\n')
        tools=ComputerTools()
        try:
            snapshot=await tools.execute('inspect_project',{},str(folder))
            good=await tools.execute('run_checks',{'commands':['pytest -q test_good.py']},str(folder))
            bad=await tools.execute('run_checks',{'commands':['pytest -q test_bad.py','touch must_not_run']},str(folder))
            empty=await tools.execute('run_checks',{'commands':['pytest -q test_good.py -k absent_test']},str(folder))
        finally:await tools.close()
        checks={'local_runner_discovered':snapshot['runtime']['pytest_command']==str(ROOT/'run/tool-bin/pytest'),
                'real_two_test_suite_passed':good['exit_code']==0 and test_summary(good['checks'][0]['output'])['count']==2,
                'real_failure_retained_and_later_command_skipped':bad['exit_code']!=0 and not (folder/'must_not_run').exists(),
                'zero_selected_tests_retained':empty['exit_code']!=0 and test_summary(empty['checks'][0]['output'])['empty']}
        report={'at':datetime.now(timezone.utc).isoformat(),'passed':all(checks.values()),'checks':checks,
                'scope':'Actual project-owned pytest through the same inspection/shell/batched-check handlers; success, tmp_path under GameDrive, failure and zero selected tests. No native model or user task invoked.',
                'runtime':snapshot['runtime'],'outcomes':{'good':good,'bad':bad,'empty':empty}}
    name='local-test-runner-validation.json';(ROOT/'docs'/name).write_text(json.dumps(report,indent=2)+'\n');archive_report(ROOT,name,'automated','Actual local pytest runner',report['scope']);refresh_results(ROOT)
    print(json.dumps({'passed':report['passed'],'checks':checks}))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':asyncio.run(main())
