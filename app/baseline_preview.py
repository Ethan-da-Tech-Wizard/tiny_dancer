# SPDX-License-Identifier: Apache-2.0
"""Bounded initial-context projection; does not mutate saved tool evidence."""
import copy
from pathlib import Path
from app.prompting import compact_result, excerpt


def baseline_preview(name, result):
    value=copy.deepcopy(result)
    if name=='inspect_project':
        for record in value.get('files',[]):
            path=Path(record.get('path',''))
            try: parts=path.relative_to(Path(value.get('path','/'))).parts
            except ValueError: parts=(path.name,)
            if 'text' in record and (path.name.startswith('test_') or {'tests','test'} & set(parts)):
                record.pop('text')
                record['preview_omitted']=True
                record['read_hint']='Read this test with read_file when needed; full bounded inspection is in the artifact.'
    # Remove intentionally hidden baseline test bodies before allocating the
    # shared source budget, so they cannot crowd out the implementation.
    value=compact_result(value)
    if name=='run_checks':
        for outcome in value.get('checks',[]):
            output=outcome.get('output')
            if isinstance(output,str) and len(output)>1200:
                outcome['output']=excerpt(output,1200)
                outcome['output_truncated']=True
    return value
