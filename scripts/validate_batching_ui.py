# SPDX-License-Identifier: Apache-2.0
"""Read-only live results/workspace validation; never starts model tasks."""
import argparse
import asyncio
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import httpx
from playwright.async_api import async_playwright
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.validation_results import archive_report,refresh_results
BASE = 'http://127.0.0.1:3210'


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export', action='store_true', help='Also inspect completed exact-user export session')
    args = parser.parse_args()
    report = {'at': datetime.now(timezone.utc).isoformat(), 'errors': [], 'checks': {}}
    output = ROOT / ('docs/score-export-ui-validation.json' if args.export else 'docs/results-ui-validation.json')
    try:
        with httpx.Client(base_url=BASE, timeout=10) as client:
            report['checks']['unauthenticated_results_denied'] = client.get('/api/test-results').status_code == 401
            client.get('/results').raise_for_status()
            response = client.get('/api/test-results'); response.raise_for_status(); index = response.json()
            report['checks']['unknown_evidence_denied'] = client.get('/api/test-results/not-an-allowed-report').status_code == 404
            for row in index['results']:
                client.get('/api/test-results/' + row['id']).raise_for_status()
            report['checks']['all_evidence_links_work'] = bool(index['results'])
            report['checks']['past_failure_kept'] = any(row['status'] == 'failed' for row in index['results'])
            report['checks']['missing_export_kept'] = any(row['id'] == 'native-score-export-before' and row['status'] == 'incomplete' for row in index['results'])
            report['checks']['latest_suite_status_valid'] = next(row for row in index['results'] if row['id'].startswith('run-'))['status'] in ('passed','failed','running')
            report['results_count'] = len(index['results'])
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(executable_path=shutil.which('chromium'), headless=True)
            try:
                page = await browser.new_page(viewport={'width':1280,'height':900})
                page.on('pageerror', lambda error: report['errors'].append(str(error)))
                await page.goto(BASE + '/results')
                await page.wait_for_selector('#native tr')
                report['checks']['results_render_all_rows'] = await page.locator('tbody tr').count() == len(index['results'])
                for size, name in (({'width':1280,'height':900},'desktop'),({'width':390,'height':844},'mobile')):
                    await page.set_viewport_size(size)
                    report['checks']['results_' + name + '_no_overflow'] = await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    await page.screenshot(path=str(ROOT / ('docs/test-results-' + name + '.png')))
                # Saved result titles/scopes are displayed as text, including hostile markup.
                malicious = {'updated_at': report['at'], 'results': [{'id':'fixture','kind':'native','title':'<img src=x onerror="window.resultXss=true">', 'scope':'<script>window.resultXss=true</script>', 'status':'failed','at':''}]}
                await page.route('**/api/test-results', lambda route: route.fulfill(json=malicious))
                await page.locator('#refresh').click()
                await page.wait_for_selector('tr[data-result-id="fixture"]')
                report['checks']['saved_text_cannot_execute_markup'] = await page.evaluate('!window.resultXss && document.querySelectorAll("tbody img,tbody script").length === 0')
                await page.unroute('**/api/test-results')
                if args.export:
                    native = json.loads((ROOT / 'docs/score-export-validation.json').read_text())
                    assert native['passed'] and native['status'] == 'complete'
                    await page.evaluate('localStorage.setItem("tiny-dancer-session",' + json.dumps(native['session']) + ')')
                    await page.goto(BASE)
                    await page.wait_for_function('document.querySelector("#task-status").textContent.includes("Complete")')
                    report['checks']['sidebar_results_link'] = await page.locator('a[href="/results"]').count() == 1
                    answer = await page.locator('.message.assistant').last.inner_text()
                    report['checks']['export_label'] = 'CHECKED DATA EXPORT' in answer.upper()
                    report['checks']['saved_path_shown'] = native['saved_file'] in answer
                    report['checks']['verified_complete_controls'] = ('checks passed' in (await page.locator('#task-status').inner_text()).lower()
                                                                      and not await page.locator('#stop').is_visible()
                                                                      and not await page.locator('#resume-task').is_visible())
                    titles = await page.locator('.tool-event summary').all_inner_texts()
                    report['checks']['old_tool_calls_not_running'] = not any(' · running' in title for title in titles)
                    for size, name in (({'width':1280,'height':900},'desktop'),({'width':390,'height':844},'mobile'),({'width':960,'height':360},'short-window')):
                        await page.set_viewport_size(size)
                        report['checks']['export_' + name + '_no_overflow'] = await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                        report['checks']['export_' + name + '_messages_visible'] = await page.locator('#messages').evaluate('(element)=>element.clientHeight>=80')
                        await page.screenshot(path=str(ROOT / ('docs/score-export-' + name + '.png')))
                    report['session'] = native['session']; report['saved_file'] = native['saved_file']
                else:
                    await page.goto(BASE)
                    report['checks']['sidebar_results_link'] = await page.locator('a[href="/results"]').count() == 1
            finally:
                await browser.close()
        report['checks']['no_javascript_errors'] = not report['errors']
        report['passed'] = all(report['checks'].values())
    except Exception as error:
        report['passed'] = False
        report['errors'].append(str(error))
    output.write_text(json.dumps(report, indent=2) + '\n')
    archive_report(ROOT,output.name,'automated','Completed score export interface' if args.export else 'Results page and authentication','Live browser assertions; no model task actions.')
    refresh_results(ROOT)
    print(json.dumps(report, indent=2))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    asyncio.run(main())
