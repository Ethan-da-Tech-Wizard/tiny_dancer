# SPDX-License-Identifier: Apache-2.0
"""Grade model-written verification against flawed and conforming controls."""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


INSTRUCTIONS = '''You generate executable verification for existing software. The original requirements define correctness; the implementation and its existing passing tests can be wrong. Examine the supplied current source and documented API behavior. Write a concise Python unittest module named audit_tests.py that independently exercises required behavior, including relevant failure and boundary cases. Use temporary data and the real program via subprocess; expected results must follow the requirements, not the current implementation. Use only the standard library. Do not edit the implementation. Do not assert source-code spelling or implementation choices. Tests may correctly fail on a defective implementation. Return the complete test module through write_verification. Do not return a pass/fail opinion as a substitute for an executable test.'''

TOOL = {'name':'write_verification','description':'Submit the complete standard-library unittest module audit_tests.py for actual execution.',
        'parameters':{'type':'object','properties':{'content':{'type':'string'}},'required':['content']}}


def submitted_code(messages):
    calls=[m for m in messages if m.recipient]
    if len(calls)!=1 or calls[0].recipient!='functions.write_verification':
        raise ValueError('Exactly one completed verification submission is required')
    from app.engine import text_of_message
    args=json.loads(text_of_message(calls[0]));code=args.get('content')
    if not isinstance(code,str) or not code.strip() or len(code.encode())>100000:
        raise ValueError('Missing or oversized test module')
    ast.parse(code)
    return code


RUNNER = '''import contextlib,io,json,unittest
out=io.StringIO()
with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
 suite=unittest.defaultTestLoader.loadTestsFromName('audit_tests')
 result=unittest.TextTestRunner(stream=out,verbosity=2).run(suite)
print(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'passed':result.wasSuccessful(),'output':out.getvalue()[-12000:]}))
'''


def run_verification(program,code,root):
    with tempfile.TemporaryDirectory(dir=Path(root)/'run') as temporary:
        folder=Path(temporary);target=folder/'inventory.py';target.write_text(program)
        (folder/'audit_tests.py').write_text(code)
        try:
            probe_env={**os.environ,'TMPDIR':str(folder)}
            done=subprocess.run([sys.executable,'-c',RUNNER],cwd=folder,env=probe_env,
                                capture_output=True,text=True,timeout=90)
            result=json.loads(done.stdout) if done.returncode==0 else {'error':'Verification runner exited','stderr':done.stderr[-1000:]}
        except (subprocess.TimeoutExpired,ValueError) as exc:
            result={'error':type(exc).__name__}
        result['implementation_unchanged']=target.is_file() and target.read_text()==program
        return result


def grade_verification(program,conforming,code,root):
    bad=run_verification(program,code,root);good=run_verification(conforming,code,root)
    checks={'actual_nonempty_tests':bad.get('tests',0)>0 and bad.get('tests')==good.get('tests'),
            'finds_behavioral_failure':bad.get('failures',0)>0 and bad.get('errors')==0,
            'accepts_conforming_control':good.get('passed') is True and good.get('errors')==0,
            'no_skipped_cases':bad.get('skipped')==0 and good.get('skipped')==0,
            'does_not_change_implementations':bad['implementation_unchanged'] and good['implementation_unchanged']}
    return {'passed':all(checks.values()),'checks':checks,'flawed':bad,'conforming':good}
