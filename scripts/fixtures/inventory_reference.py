# SPDX-License-Identifier: Apache-2.0
"""Operator-written positive TEST CONTROL only; never supplied as model output."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile


def fail_scan(error):
    raise error


def inventory(root,output):
    root=Path(root).absolute();output=Path(output).absolute()
    if not root.is_dir():raise ValueError('ROOT must be a directory')
    rows=[]
    for parent,dirs,files in os.walk(root,followlinks=False,onerror=fail_scan):
        dirs[:]=[name for name in dirs if not (Path(parent)/name).is_symlink()]
        for name in files:
            path=Path(parent)/name
            if path==output:continue
            mode=path.lstat().st_mode
            if not stat.S_ISREG(mode):continue
            digest=hashlib.sha256();size=0
            with path.open('rb') as handle:
                while block:=handle.read(1048576):digest.update(block);size+=len(block)
            rows.append({'path':path.relative_to(root).as_posix(),'size':size,'sha256':digest.hexdigest()})
    rows.sort(key=lambda row:row['path'])
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',dir=output.parent,delete=False,encoding='utf-8') as handle:
            temporary=Path(handle.name);json.dump(rows,handle,ensure_ascii=False)
        os.replace(temporary,output)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)


def main():
    try:
        if len(sys.argv)!=3:raise ValueError('Usage: inventory.py ROOT OUTPUT')
        inventory(sys.argv[1],sys.argv[2])
    except (OSError,ValueError) as error:
        print('error:',error,file=sys.stderr);return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
