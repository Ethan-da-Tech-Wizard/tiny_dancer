# SPDX-License-Identifier: Apache-2.0
"""Trusted task constraints derived from the current user request and host date."""
import re
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def lookup_languages(prompt, cwd=None):
    """Expose language tools for relevant goals; discovery handles missed cues."""
    text = prompt.lower()
    languages = set()
    if re.search(r'\b(python|pypi|pip|pyproject|requirements\.txt|pytest|venv)\b|\b[\w/-]+\.py\b', text):
        languages.add('python')
    if re.search(r'\b(cargo|rustc|rustup|crates\.io|docs\.rs)\b|\b[\w/-]+\.rs\b', text) or (
        re.search(r'\brust\b', text) and not re.search(r'\b(rust removal|rust stain|rust on|rust off|rust from)\b', text)
    ):
        languages.add('rust')
    if cwd and not languages and re.search(r'\b(code|coding|project|dependenc\w*|packages?|build|compile|tests?|debug|implement|refactor)\b', text):
        folder = Path(cwd)
        if any((folder / name).is_file() for name in ('pyproject.toml','requirements.txt','requirements.lock.txt','uv.lock','poetry.lock','Pipfile')):
            languages.add('python')
        if (folder / 'Cargo.toml').is_file():
            languages.add('rust')
    return sorted(languages)


def completed_weekday(prompt, today, weekday):
    """Resolve a named completed weekday, including counted occurrences ago."""
    names = ('monday','tuesday','wednesday','thursday','friday','saturday','sunday')
    name = names[weekday]
    text = prompt.lower()
    prior = today - timedelta(days=(today.weekday()-weekday)%7 or 7)
    counts = {'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10}
    match = re.search(r'\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+' + name + r's?\s+ago\b',text)
    if match:
        count = counts.get(match[1]) or int(match[1])
        return prior-timedelta(weeks=count-1) if 1<=count<=52 else None
    if re.search(r'\b'+name+r'\s+before\s+last\b',text): return prior-timedelta(weeks=1)
    dates = re.findall(r'\b20\d{2}-\d{2}-\d{2}\b',text)
    if dates:
        from datetime import date
        try: explicit = date.fromisoformat(dates[0])
        except ValueError: return None
        return explicit if len(dates)==1 and explicit.weekday()==weekday and explicit<today else None
    if re.search(r'\b(ago|next|this|since|between)\b',text): return None
    return prior if re.search(r'\b(recent|latest|last)\b',text) else None


def contract_for(prompt, kind='auto', today=None, cwd=None):
    today = today or datetime.now(ZoneInfo('America/Phoenix')).date()
    text = prompt.lower()
    action = re.search(r'\b(create|edit|install|implement|fix|build|write|run|execute|delete|rename|move|open|modify|update|change|add|remove|launch|stop|debug|optimize|configure|save|export|store)\b', text)
    file_cue=bool(re.search(r'\b(file|document|code\s+oss|vs\s*code|vscode|editor)\b|[\w/-]+\.(?:json|csv)\b',text))
    file_request = bool(re.search(r'\b(save|export|store)\b',text) and re.search(r'\b(json|csv|file|code\s+oss|vs\s*code)\b',text)
                        or re.search(r'\b(put|write|create|make)\b',text) and file_cue)
    editor_request = file_request and bool(re.search(r'\b(code\s+oss|vs\s*code|vscode)\b',text))
    deliverables = {'format':'json','editor':editor_request} if file_request and re.search(r'\bjson\b',text) else {}
    if deliverables:
        paths=re.findall(r'\b(?:save|export|store|write|create|put|make)\b[^;\n]{0,140}?\b(?:to|as|in|named|called)\s+[`\"\']?([/\w.-]+\.json)\b',prompt,re.I)
        paths+=re.findall(r'\b(?:write|create|save|export|store)\s+[`\"\']?([/\w.-]+\.json)\b',prompt,re.I)
        if len(set(paths))==1: deliverables['path']=paths[0]
    question = bool(re.search(r'\b(what|who|when|why|how|tell me|list|find|look up|search)\b', text))
    conversational=bool(re.fullmatch(r'\s*(?:hi|hello|hey|thanks|thank you|good (?:morning|afternoon|evening|night))[\s!.,]*',text))
    task_kind = kind if kind in ('answer', 'work') else ('work' if action or file_request or not (question or conversational) else 'answer')
    recent = bool(re.search(r'\b(recent|latest|last|current|today)\b', text))
    nfl = 'nfl' in text and 'sunday' in text and bool(re.search(r'\b(scores?|stats?|played|matchups?|games?)\b', text))
    if re.search(r'\b(why|how|compare|analy[sz]e|average|ranking|passing|rushing|receiving|players?|quarters?|prediction|bet|fantasy|forecast)\b', text):
        nfl = False
    target = None
    if nfl:
        target = completed_weekday(text,today,6)
        nfl = target is not None
    languages = lookup_languages(prompt,cwd)
    groups=[]
    if re.search(r'https?://|\b(internet|web|website|browser|html|frontend|search|look up|nfl)\b',text): groups.append('web')
    if re.search(r'\b(desktop|screen|screenshot|window|click|keyboard|mouse|hyprland)\b',text): groups.append('desktop')
    if re.search(r'\b(code\s+oss|vs\s*code|vscode|editor)\b',text): groups.append('editor')
    export = nfl and task_kind=='work' and deliverables and not re.search(r'\b(install|implement|build|debug|refactor|plot|chart|website|application|email|send|post|upload|delete|remove|rename|move|analyze|analyse|compare)\b',text)
    return {'kind': task_kind, 'today': today.isoformat(), 'timezone': 'America/Phoenix',
            'recent': recent, 'workflow': 'nfl_scores' if nfl and task_kind == 'answer' else 'nfl_scores_export' if export else None,
            'target_date': target.isoformat() if target else None,
            'needs_source': recent or bool(re.search(r'\b(internet|web|search|look up|nfl|source)\b', text)) or bool(
                task_kind=='answer' and languages and re.search(r'\b(dependenc\w*|packages?|crates?|docs?|documentation|versions?|licen[sc]es?|requires)\b',text)),
            'lookup_languages': languages,'toolsets':groups,'deliverables':deliverables}


def answer_issue(text, contract, sources):
    if not text.strip():
        return 'The answer is empty.'
    if contract['needs_source'] and not any(source in text for source in sources):
        return 'Cite the URL or file path from a successful tool retrieval in the answer.'
    if contract['recent']:
        for value in re.findall(r'\b20\d{2}-\d{2}-\d{2}\b', text):
            if value > contract['today']:
                return f"A recent result cannot be dated in the future. Today is {contract['today']}."
    if contract['workflow'] == 'nfl_scores':
        return 'Use nfl_scores for the requested completed Sunday. It validates every matchup and score before publishing.'
    return None


def tools_for(contract, definitions):
    languages = set(contract.get('lookup_languages', []))
    definitions = [tool for tool in definitions if tool['name'] not in ('python_lookup','rust_lookup')
                   or tool['name'].removesuffix('_lookup') in languages]
    if contract['workflow'] == 'nfl_scores':
        names = {'nfl_scores', 'finish_task'}
    elif contract['workflow'] == 'nfl_scores_export':
        names = {'nfl_scores','finish_task','write_file','read_file','editor'}
    elif contract['kind'] == 'answer':
        names = {'read_file', 'list_directory', 'browser', 'fetch_json', 'nfl_scores', 'finish_task', 'discover_tools'}
        names.update(language + '_lookup' for language in languages)
    else:
        names={'shell','read_file','write_file','list_directory','apply_patch','inspect_project','run_checks','task_progress','finish_task','discover_tools'}
        names.update(language+'_lookup' for language in languages)
        groups=set(contract.get('toolsets',[]))
        if 'web' in groups: names.update(('browser','fetch_json','nfl_scores'))
        if 'desktop' in groups: names.add('desktop')
        if 'editor' in groups: names.add('editor')
    if contract['kind']=='answer' and contract['workflow']!='nfl_scores':
        groups=set(contract.get('toolsets',[]))
        if 'desktop' in groups:names.add('desktop')
        if 'editor' in groups:names.add('editor')
    return [tool for tool in definitions if tool['name'] in names]
