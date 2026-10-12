# SPDX-License-Identifier: Apache-2.0
"""Check budget validation and intercepted composer requests without inference."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

import httpx
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.validation_results import archive_report, refresh_results

BASE = 'http://127.0.0.1:3210'
SID = 'e49878f2e88542cdaefe0fe660e32307'


async def main():
    report = {'at': datetime.now(timezone.utc).isoformat(), 'checks': {}, 'errors': [],
              'scope': 'Actual nullable/bounded API validation against a nonexistent session, plus intercepted browser POSTs. No native task started, resumed or stopped.'}
    with httpx.Client(base_url=BASE, timeout=10) as client:
        client.get('/').raise_for_status()
        original_active = client.get('/api/status').json()['active_job']
        for name, budget, expected in [('auto', None, 404), ('minimum', 64, 404), ('maximum', 2048, 404),
                                       ('below_minimum', 63, 422), ('above_maximum', 2049, 422)]:
            response = client.post('/api/sessions/nonexistent-budget-validation-session/tasks',
                                   json={'prompt': 'Budget schema validation', 'max_tokens': budget})
            report['checks']['api_' + name] = response.status_code == expected
        report['checks']['api_omitted_auto'] = client.post('/api/sessions/nonexistent-budget-validation-session/tasks',
                                                        json={'prompt': 'Budget schema validation'}).status_code == 404
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(executable_path=shutil.which('chromium'), headless=True)
            try:
                context = await browser.new_context(viewport={'width': 1280, 'height': 900})
                await context.add_init_script("localStorage.setItem('tiny-dancer-session'," + json.dumps(SID) + ")")
                page = await context.new_page()
                page.on('pageerror', lambda error: report['errors'].append(str(error)))
                posted = []
                received = asyncio.Event()

                async def task_route(route):
                    posted.append(route.request.post_data_json)
                    await route.fulfill(json={'job': 'budget-fixture'})
                    received.set()

                async def fixture_route(route):
                    if route.request.url.endswith('/events'):
                        await route.fulfill(content_type='text/event-stream', body='event: closed\ndata: {}\n\n')
                    else:
                        await route.fulfill(json={'id': 'budget-fixture', 'session': SID, 'status': 'complete',
                                                 'checkpoint': {'verified': True}, 'elapsed_seconds': 0})

                await page.route('**/api/sessions/*/tasks', task_route)
                await page.route('**/api/jobs/budget-fixture*', fixture_route)
                await page.goto(BASE)
                await page.locator('#send').wait_for(state='visible')
                report['checks']['ui_auto_default'] = await page.locator('#budget').input_value() == 'auto'
                if not report['checks']['ui_auto_default']:
                    raise AssertionError('Automatic starting allowance is not the default')
                for mode, selection, expected in [('agent', 'auto', None), ('agent', '512', 512),
                                                  ('chat', 'auto', None), ('chat', '1024', 1024)]:
                    received.clear()
                    await page.locator('#mode').select_option(mode)
                    await page.locator('#budget').select_option(selection)
                    await page.locator('#prompt').fill('Intercepted budget check; no native task')
                    await page.locator('#send').click()
                    await asyncio.wait_for(received.wait(), 5)
                    report['checks']['ui_' + mode + '_' + selection] = posted[-1]['max_tokens'] == expected and posted[-1]['mode'] == mode
                    await page.reload()
                    await page.locator('#send').wait_for(state='visible')
                report['checks']['numeric_choice_persists'] = await page.locator('#budget').input_value() == '1024'
                report['checks']['no_javascript_errors'] = not report['errors']
            finally:
                await browser.close()
    except Exception as exc:
        report['errors'].append(type(exc).__name__ + ': ' + str(exc))
    with httpx.Client(base_url=BASE, timeout=10) as client:
        client.get('/').raise_for_status()
        report['checks']['native_job_untouched'] = client.get('/api/status').json()['active_job'] == original_active
    report['passed'] = bool(report['checks']) and all(report['checks'].values()) and not report['errors']
    report['status'] = 'passed' if report['passed'] else 'failed'
    name = 'generation-budget-ui-validation.json'
    (ROOT / 'docs' / name).write_text(json.dumps(report, indent=2) + '\n')
    archive_report(ROOT, name, 'automated', 'Automatic starting allowance API and composer', report['scope'])
    refresh_results(ROOT)
    print(json.dumps(report))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    asyncio.run(main())
