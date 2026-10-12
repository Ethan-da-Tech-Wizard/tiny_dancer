# SPDX-License-Identifier: Apache-2.0
"""Small, read-only runtime notes derived from inspected Python imports."""
import ast
from pathlib import Path


def walk_default_error_sites(tree):
    modules=set();functions=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            modules.update(alias.asname or alias.name for alias in node.names if alias.name=='os')
        elif isinstance(node,ast.ImportFrom) and node.level==0 and node.module=='os':
            functions.update(alias.asname or alias.name for alias in node.names if alias.name=='walk')
    sites=[]
    for node in ast.walk(tree):
        if not isinstance(node,ast.Call):continue
        target=node.func
        actual=(isinstance(target,ast.Attribute) and target.attr=='walk' and isinstance(target.value,ast.Name) and target.value.id in modules
                or isinstance(target,ast.Name) and target.id in functions)
        if not actual or any(isinstance(arg,ast.Starred) for arg in node.args) or any(key.arg is None for key in node.keywords):continue
        callback=next((key.value for key in node.keywords if key.arg=='onerror'),node.args[2] if len(node.args)>2 else None)
        if callback is None or isinstance(callback,ast.Constant) and callback.value is None:sites.append(node.lineno)
    return sites[:8]


def python_runtime_notes(files):
    notes = []
    for record in files:
        if (not isinstance(record, dict) or record.get('error') or record.get('truncated')
                or Path(record.get('path', '')).suffix != '.py'):
            continue
        try:
            tree = ast.parse(record.get('text', ''))
        except (SyntaxError, ValueError, RecursionError):
            continue
        walk_sites=walk_default_error_sites(tree)
        if walk_sites:
            notes.append({'path':record['path'],'library':'os.walk','call_lines':walk_sites,
                          'note':'os.walk directory scan errors are ignored by default. Its onerror callback receives an OSError and can report it or raise to abort traversal. An outer try/except does not catch errors that the walker ignored.',
                          'reference':'https://docs.python.org/3.14/library/os.html#os.walk',
                          'scope':'Call-derived standard-library behavior, not a proven defect. Project code was parsed, never imported or executed.'})
            if len(notes)==8:break
        imports = [node for node in ast.walk(tree) if (
            isinstance(node, ast.Import) and any(alias.name == 'decimal' for alias in node.names)
            or isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == 'decimal')]
        if not imports:
            continue
        sites = []
        for node in ast.walk(tree):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
            if any(isinstance(target, ast.Attribute) and target.attr == 'prec' for target in targets):
                value = node.value
                constant = value.value if isinstance(value, ast.Constant) and type(value.value) is int else None
                sites.append({'line': node.lineno, 'constant': constant,
                              'classification': 'possible_precision_assignment'})
        notes.append({'path': record['path'], 'library': 'decimal',
                      'import_lines': [node.lineno for node in imports][:8],
                      'precision_assignments': sites[:8],
                      'note': 'Decimal construction from strings is exact; arithmetic can round at the active context precision. Check precision policy against the full required input range. A passing sample does not establish that range.',
                      'reference': 'https://docs.python.org/3/library/decimal.html#mitigating-round-off-error-with-increased-precision',
                      'scope': 'Import-derived library behavior, not a proven defect. Project code was parsed, never imported or executed.'})
        if len(notes) == 8:
            break
    return notes
