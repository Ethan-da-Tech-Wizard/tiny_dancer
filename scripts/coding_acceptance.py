# SPDX-License-Identifier: Apache-2.0
"""Independent CLI acceptance cases, never inserted into a running model task."""
import json
import subprocess
import tempfile
from pathlib import Path

from scripts.evaluate_native_coding import independent_checks


def coding_checks(folder,root):
    folder=Path(folder);checks=independent_checks(folder);program=folder/'summarize.py'
    if not program.is_file():return checks,[]
    large=str(10**40)
    cases=[('exact totals beyond default Decimal precision','category,amount\nx,'+large+'.01\nx,0.02\n',{'x':large+'.03'}),
           ('many repeated signed amounts','category,amount\n'+'x,0.01\n'*500+'x,-0.02\n'*100,{'x':'3.00'})]
    friendly=[]
    with tempfile.TemporaryDirectory(dir=Path(root)/'run') as temporary:
        source=Path(temporary)/'acceptance.csv'
        for name,content,expected in cases:
            source.write_text(content)
            result=subprocess.run(['/usr/bin/python3',str(program),str(source)],cwd=folder,capture_output=True,text=True,timeout=15)
            try:actual=json.loads(result.stdout)
            except ValueError:actual=None
            checks.append({'check':name,'passed':result.returncode==0 and actual==expected,'actual':actual,'exit_code':result.returncode,'stderr':result.stderr[:1000]})
        for value in ('bad','NaN','Infinity','1.234',''):
            source.write_text('category,amount\nx,'+value+'\n')
            result=subprocess.run(['/usr/bin/python3',str(program),str(source)],cwd=folder,capture_output=True,text=True,timeout=15)
            text=result.stderr or result.stdout
            friendly.append({'value':value,'passed':result.returncode!=0 and bool(text.strip()) and 'Traceback' not in text and any(word in text.lower() for word in ('invalid','amount','finite','decimal')),'output':text[:1000]})
    return checks,friendly
