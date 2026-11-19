# ==============================================================================
# app/task_policy.py - turn a user prompt into a trusted "task contract"
#
# Role in the app: app/agent.py (AgentRun.__init__) and app/engine.py call
# contract_for() once per request. The returned dict decides whether the task
# is an 'answer' (look something up, cite it) or 'work' (change files, run
# tests), which tools the model may see (tools_for), which extra language/toolset
# helpers are pre-enabled, whether a source citation is required, and whether a
# deterministic NFL-scores workflow applies.
#
# Why code instead of asking the model: the contract is derived from the user's
# own words and the host clock with plain regular expressions, so a model (or a
# web page it reads) cannot talk its way into more tools or into skipping the
# evidence rules. The regexes are intentionally conservative; progressive
# discovery (the discover_tools tool) covers anything they miss.
#
# Time zone: 'today' is computed in America/Phoenix because the owner's machine
# and the NFL schedule logic are anchored there.
#
# Tests: tests/test_agent.py, tests/test_task_date_cache.py and others cover
# the date and workflow rules.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0

"""Trusted task constraints derived from the current user request and host date."""
import re
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def lookup_languages(prompt, cwd=None):
    """Decide which language lookup tools (python_lookup / rust_lookup) to pre-enable.

    Keywords and file extensions in the prompt are the main signal. For generic
    coding words with no language named, the project folder's manifests decide.

    Args:
        prompt: user request text.
        cwd: optional project folder to look for pyproject.toml, Cargo.toml, etc.
    Returns:
        Sorted list containing 'python' and/or 'rust'.
    """
    text = prompt.lower()
    languages = set()
    if re.search(r'\b(python|pypi|pip|pyproject|requirements\.txt|pytest|venv)\b|\b[\w/-]+\.py\b', text):
        languages.add('python')
    # 'rust' alone is ambiguous (corrosion), so a few non-programming phrases are
    # excluded.
    if re.search(r'\b(cargo|rustc|rustup|crates\.io|docs\.rs)\b|\b[\w/-]+\.rs\b', text) or (
        re.search(r'\brust\b', text) and not re.search(r'\b(rust removal|rust stain|rust on|rust off|rust from)\b', text)
    ):
        languages.add('rust')
    # Only when the prompt itself named no language: infer from manifests, but
    # only for prompts that sound like software work.
    if cwd and not languages and re.search(r'\b(code|coding|project|dependenc\w*|packages?|build|compile|tests?|debug|implement|refactor)\b', text):
        folder = Path(cwd)
        if any((folder / name).is_file() for name in ('pyproject.toml','requirements.txt','requirements.lock.txt','uv.lock','poetry.lock','Pipfile')):
            languages.add('python')
        if (folder / 'Cargo.toml').is_file():
            languages.add('rust')
    return sorted(languages)


def completed_weekday(prompt, today, weekday):
    """Resolve which past occurrence of a weekday the user means.

    Args:
        prompt: lower-cased request. today: current date. weekday: 0=Mon..6=Sun.
    Returns:
        A date strictly before today, or None when the wording is ambiguous or
        asks about the future ('next', 'this', 'since', 'between').
    Handles: 'N <day>s ago' (1..52), '<day> before last', an explicit ISO date that
    really is that weekday and in the past, and bare 'last/latest/recent'.
    """
    names = ('monday','tuesday','wednesday','thursday','friday','saturday','sunday')
    name = names[weekday]
    text = prompt.lower()
    # The most recent such weekday strictly before today ('or 7' so that on a
    # Sunday, "last Sunday" is a week ago, not today).
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
    """Build the trusted task contract for a request.

    Args:
        prompt: user request.
        kind: 'answer', 'work' or 'auto' (classify from wording).
        today: override date (tests); defaults to now in America/Phoenix.
        cwd: project folder, used for language detection.
    Returns:
        dict with kind, today, timezone, recent, workflow ('nfl_scores',
        'nfl_scores_export' or None), target_date, needs_source,
        lookup_languages, toolsets (web/desktop/editor) and deliverables
        (requested JSON file path/format and whether to open it in an editor).
    """
    today = today or datetime.now(ZoneInfo('America/Phoenix')).date()
    text = prompt.lower()
    # Verbs that ask the machine to DO something (as opposed to a question).
    action = re.search(r'\b(create|edit|install|implement|fix|build|write|run|execute|delete|rename|move|open|modify|update|change|add|remove|launch|stop|debug|optimize|configure|save|export|store)\b', text)
    # Mentions of a file or editor, used with save/export/make verbs below.
    file_cue=bool(re.search(r'\b(file|document|code\s+oss|vs\s*code|vscode|editor)\b|[\w/-]+\.(?:json|csv)\b',text))
    file_request = bool(re.search(r'\b(save|export|store)\b',text) and re.search(r'\b(json|csv|file|code\s+oss|vs\s*code)\b',text)
                        or re.search(r'\b(put|write|create|make)\b',text) and file_cue)
    editor_request = file_request and bool(re.search(r'\b(code\s+oss|vs\s*code|vscode)\b',text))
    # A requested JSON file is a checkable deliverable (existence and validity are
    # verified at completion by app/deliverables.py).
    deliverables = {'format':'json','editor':editor_request} if file_request and re.search(r'\bjson\b',text) else {}
    if deliverables:
        paths=re.findall(r'\b(?:save|export|store|write|create|put|make)\b[^;\n]{0,140}?\b(?:to|as|in|named|called)\s+[`\"\']?([/\w.-]+\.json)\b',prompt,re.I)
        paths+=re.findall(r'\b(?:write|create|save|export|store)\s+[`\"\']?([/\w.-]+\.json)\b',prompt,re.I)
        # Only an unambiguous single path is trusted; with several candidates the
        # model must choose and completion checks stay generic.
        if len(set(paths))==1: deliverables['path']=paths[0]
    question = bool(re.search(r'\b(what|who|when|why|how|tell me|list|find|look up|search)\b', text))
    conversational=bool(re.fullmatch(r'\s*(?:hi|hello|hey|thanks|thank you|good (?:morning|afternoon|evening|night))[\s!.,]*',text))
    # Default for unclear requests is 'work' (the stricter, evidence-requiring
    # mode) unless it reads as a question or greeting.
    task_kind = kind if kind in ('answer', 'work') else ('work' if action or file_request or not (question or conversational) else 'answer')
    recent = bool(re.search(r'\b(recent|latest|last|current|today)\b', text))
    # Narrow trigger for the deterministic scores workflow: only plain "what were
    # the Sunday scores" requests, not analysis, predictions or player stats, which
    # the next check excludes.
    nfl = 'nfl' in text and 'sunday' in text and bool(re.search(r'\b(scores?|stats?|played|matchups?|games?)\b', text))
    if re.search(r'\b(why|how|compare|analy[sz]e|average|ranking|passing|rushing|receiving|players?|quarters?|prediction|bet|fantasy|forecast)\b', text):
        nfl = False
    target = None
    if nfl:
        target = completed_weekday(text,today,6)
        nfl = target is not None
    languages = lookup_languages(prompt,cwd)
    # Optional toolsets are enabled from keywords so their schemas only cost
    # prompt tokens when relevant.
    groups=[]
    if re.search(r'https?://|\b(internet|web|website|browser|html|frontend|search|look up|nfl)\b',text): groups.append('web')
    if re.search(r'\b(desktop|screen|screenshot|window|click|keyboard|mouse|hyprland)\b',text): groups.append('desktop')
    if re.search(r'\b(code\s+oss|vs\s*code|vscode|editor)\b',text): groups.append('editor')
    # Scores plus a JSON file and nothing else that needs real engineering.
    export = nfl and task_kind=='work' and deliverables and not re.search(r'\b(install|implement|build|debug|refactor|plot|chart|website|application|email|send|post|upload|delete|remove|rename|move|analyze|analyse|compare)\b',text)
    return {'kind': task_kind, 'today': today.isoformat(), 'timezone': 'America/Phoenix',
            'recent': recent, 'workflow': 'nfl_scores' if nfl and task_kind == 'answer' else 'nfl_scores_export' if export else None,
            'target_date': target.isoformat() if target else None,
            # Recent/online topics, and answer-mode package/doc questions, must cite a
            # retrieved source.
            'needs_source': recent or bool(re.search(r'\b(internet|web|search|look up|nfl|source)\b', text)) or bool(
                task_kind=='answer' and languages and re.search(r'\b(dependenc\w*|packages?|crates?|docs?|documentation|versions?|licen[sc]es?|requires)\b',text)),
            'lookup_languages': languages,'toolsets':groups,'deliverables':deliverables}


def answer_issue(text, contract, sources):
    """Check an answer-mode reply against the contract's evidence rules.

    Returns:
        A correction message for the model, or None when the answer is acceptable:
        non-empty, cites a URL/path actually retrieved when needed, no future
        dates in a 'recent' result, and not a hand-written NFL answer when the
        nfl_scores tool must be used.
    """
    if not text.strip():
        return 'The answer is empty.'
    if contract['needs_source'] and not any(source in text for source in sources):
        return 'Cite the URL or file path from a successful tool retrieval in the answer.'
    if contract['recent']:
        for value in re.findall(r'\b20\d{2}-\d{2}-\d{2}\b', text):
            # ISO dates compare correctly as strings.
            if value > contract['today']:
                return f"A recent result cannot be dated in the future. Today is {contract['today']}."
    if contract['workflow'] == 'nfl_scores':
        return 'Use nfl_scores for the requested completed Sunday. It validates every matchup and score before publishing.'
    return None


def tools_for(contract, definitions):
    """Filter the tool catalogue to what this contract allows.

    Args:
        contract: result of contract_for (may have gained languages/toolsets via
            discover_tools).
        definitions: the full TOOLS list.
    Returns:
        The subset of definitions to advertise and accept. NFL workflows get a
        minimal set; answer tasks get read-only tools; work tasks get shell/edit
        tools. Lookup, web, desktop and editor tools appear only when enabled.
    """
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
    # Desktop/editor inspection is allowed for answers too (e.g. "what is on my screen").
    if contract['kind']=='answer' and contract['workflow']!='nfl_scores':
        groups=set(contract.get('toolsets',[]))
        if 'desktop' in groups:names.add('desktop')
        if 'editor' in groups:names.add('editor')
    return [tool for tool in definitions if tool['name'] in names]
