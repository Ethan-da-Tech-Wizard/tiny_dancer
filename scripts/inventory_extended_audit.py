# SPDX-License-Identifier: Apache-2.0
"""Predeclared extra regular-file requirement: pipes/sockets must not be read."""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile

CRITERIA = ('Special files are excluded without blocking; regular files remain correct',)


def check_special_files(folder, root):
    folder,root=Path(folder),Path(root)
    with tempfile.TemporaryDirectory(dir=root/'run') as temporary:
        base=Path(temporary);tree=base/'tree';tree.mkdir()
        payload=b'regular file\x00\xff';(tree/'data.bin').write_bytes(payload)
        os.mkfifo(tree/'pipe')
        with socket.socket(socket.AF_UNIX) as sock:
            sock.bind(str(tree/'socket'))
            output=base/'result.json'
            try:
                result=subprocess.run([sys.executable,str(folder/'inventory.py'),str(tree),str(output)],
                                      cwd=folder,capture_output=True,text=True,timeout=3)
                try: rows=json.loads(output.read_text())
                except (OSError,ValueError): rows=None
                wanted=[{'path':'data.bin','size':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}]
                return [{'check':CRITERIA[0],'passed':result.returncode==0 and rows==wanted,
                         'exit_code':result.returncode,'timed_out':False,'stderr':result.stderr[-1000:]}]
            except subprocess.TimeoutExpired:
                return [{'check':CRITERIA[0],'passed':False,'timed_out':True}]
