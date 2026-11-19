# ==============================================================================
# app/facts.py - bounded JSON retrieval and the checked NFL scoreboard workflow
#
# Role in the app: app/tools.py exposes fetch_json() and nfl_scores() as tools,
# and app/agent.py uses format_scores() to build the final answer for the
# 'nfl_scores' workflows directly from validated data, so the language model
# never retypes (and possibly invents) scores. Every retrieval is saved as an
# artifact under run/artifacts for later inspection.
#
# Design decisions: responses are streamed and capped at 2 MB; HTTP errors and
# JSON bodies that signal an application error are rejected rather than passed
# on; nfl_scores() validates every event (unique id, requested NFL date in the
# America/New_York time zone, final status, two teams, integer scores) and fails
# the whole request on any inconsistency instead of returning partial data.
#
# Known limits: retrieve_json follows redirects and accepts any http(s) URL, so
# the fetch_json tool can reach loopback/LAN addresses; the model is trusted
# only as far as the task policy lets it call that tool. The scoreboard source
# is ESPN's unauthenticated public endpoint, which can change shape.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0

"""Bounded, decoded HTTP data and a checked NFL scoreboard workflow."""
import json
import time
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx


async def retrieve_json(url, artifacts, transport=None):
    """Download JSON, enforce limits, save it, and return (data, metadata).

    Args:
        url: http(s) URL.
        artifacts: folder where the decoded JSON is saved.
        transport: optional httpx transport so tests avoid the network.
    Returns:
        (parsed_data, {'source': final url, 'http_status', 'artifact',
        'local_path', 'retrieved_at'}).
    Raises:
        ValueError: bad scheme, body over 2 MB, or a JSON body whose 'code' field
        reports an error (some APIs return HTTP 200 with an error payload).
        httpx.HTTPStatusError: non-2xx status.
    """
    if not url.startswith(('https://', 'http://')):
        raise ValueError('Use an HTTP or HTTPS URL')
    async with httpx.AsyncClient(timeout=20, follow_redirects=True, transport=transport) as client:
        async with client.stream('GET', url, headers={'Accept': 'application/json'}) as response:
            response.raise_for_status()
            chunks, size = [], 0
            # Count bytes while streaming so an oversized body is abandoned early.
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > 2_000_000:
                    raise ValueError('Decoded JSON exceeds the 2 MB retrieval limit')
                chunks.append(chunk)
            data = json.loads(b''.join(chunks))
    if isinstance(data, dict) and isinstance(data.get('code'), int) and data['code'] >= 400:
        raise ValueError('Source application error: ' + str(data.get('message', data['code'])))
    artifacts = Path(artifacts)
    artifacts.mkdir(parents=True, exist_ok=True)
    path = artifacts / ('data-' + uuid.uuid4().hex + '.json')
    path.write_text(json.dumps(data, ensure_ascii=False))
    return data, {'source': str(response.url), 'http_status': response.status_code,
                  'artifact': '/artifacts/' + path.name, 'local_path': str(path), 'retrieved_at': time.time()}


def pointer(data, path):
    """Resolve an RFC 6901 JSON Pointer ('' = whole document, '/a/0/b').

    Applies the standard ~1 -> '/' and ~0 -> '~' unescaping, in that order.
    Raises KeyError/IndexError/ValueError when the path does not exist.
    """
    if path == '': return data
    if not path.startswith('/'): raise ValueError('JSON pointer must begin with /')
    for key in path[1:].split('/'):
        key = key.replace('~1', '/').replace('~0', '~')
        data = data[int(key)] if isinstance(data, list) else data[key]
    return data


async def fetch_json(args, artifacts, transport=None):
    """Implementation of the fetch_json tool.

    Returns the data inline when its JSON is <= 6000 characters, otherwise a
    3000-character preview flagged truncated; the complete data is always in the
    saved artifact.
    """
    data, meta = await retrieve_json(args['url'], artifacts, transport)
    data = pointer(data, args.get('pointer', ''))
    encoded = json.dumps(data, ensure_ascii=False)
    if len(encoded) > 6000:
        return {'ok': True, **meta, 'preview': encoded[:3000], 'truncated': True,
                'next_action': 'Use a narrower JSON pointer or read the saved artifact.'}
    return {'ok': True, **meta, 'data': data}


def validate_scores(data, requested_date):
    """Check an ESPN scoreboard payload and reduce it to plain game records.

    Args:
        data: decoded scoreboard JSON. requested_date: 'YYYY-MM-DD'.
    Returns:
        List of {'id', 'away', 'away_score', 'home', 'home_score'}.
    Raises:
        ValueError: no games, duplicate ids, naive timestamps, a game on another
        date, a game that is not final, a missing home/away side or negative score.
    """
    events = data.get('events')
    if not isinstance(events, list) or not events:
        raise ValueError('The source returned no games for the requested date')
    games, ids = [], set()
    for event in events:
        event_id = event['id']
        if event_id in ids: raise ValueError('Duplicate game in source')
        ids.add(event_id)
        played = datetime.fromisoformat(event['date'].replace('Z', '+00:00'))
        if played.tzinfo is None: raise ValueError('Source game date is missing its timezone')
        # NFL "game day" is an Eastern-time notion: a late Sunday game is already
        # Monday in UTC, so compare the Eastern calendar date.
        if played.astimezone(ZoneInfo('America/New_York')).date().isoformat() != requested_date:
            raise ValueError('Source includes a game outside the requested NFL date')
        competition = event['competitions'][0]
        if not competition['status']['type']['completed']:
            raise ValueError('A game is not final; a complete final-score answer is unavailable')
        sides = {row['homeAway']: row for row in competition['competitors']}
        if set(sides) != {'home', 'away'} or len(competition['competitors']) != 2:
            raise ValueError('Source is missing a home or away team')
        home, away = sides['home'], sides['away']
        home_score, away_score = int(home['score']), int(away['score'])
        if min(home_score, away_score) < 0: raise ValueError('Invalid negative score')
        games.append({'id': event_id, 'away': away['team']['displayName'], 'away_score': away_score,
                      'home': home['team']['displayName'], 'home_score': home_score})
    return games


async def nfl_scores(args, artifacts, transport=None, today=None):
    """Fetch and validate final NFL scores for one completed date.

    Args:
        args: optional 'date' (YYYY-MM-DD); default is the most recent completed Sunday.
        artifacts: artifact folder. transport: test transport. today: test clock.
    Raises:
        ValueError: date not before today, or any validation failure.
    """
    today = today or datetime.now(ZoneInfo('America/Phoenix')).date()
    # Default: last Sunday strictly before today ('or 7' avoids using today when
    # today is Sunday, whose games may not be final).
    requested = date.fromisoformat(args['date']) if args.get('date') else today - timedelta(days=(today.weekday()-6) % 7 or 7)
    if requested >= today: raise ValueError('Choose a completed date before today')
    url = 'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=' + requested.strftime('%Y%m%d')
    data, meta = await retrieve_json(url, artifacts, transport)
    games = validate_scores(data, requested.isoformat())
    return {'ok': True, **meta, 'date': requested.isoformat(), 'games': games, 'game_count': len(games),
            'verification': 'Every source event has a unique ID, the requested NFL date, two teams, integer scores and final status.'}


def format_scores(result):
    """Render validated scores as the Markdown answer shown to the user."""
    rows = [f"- {game['away']} {game['away_score']} — {game['home']} {game['home_score']}" for game in result['games']]
    return f"NFL scores for Sunday, {result['date']} ({result['game_count']} final games):\n\n" + '\n'.join(rows) + f"\n\nSource: [ESPN scoreboard]({result['source']})"
