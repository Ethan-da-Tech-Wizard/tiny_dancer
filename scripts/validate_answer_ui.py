# SPDX-License-Identifier: Apache-2.0
"""Check the actual completed answer UI without starting model work."""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path('/mnt/GameDrive/tiny_dancer')
URL = 'http://127.0.0.1:3210'


async def main():
    validation = json.loads((ROOT/'docs/answer-completion-validation.json').read_text())
    report = {'errors':[]}
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
        try:
            page = await browser.new_page(viewport={'width':1440,'height':1000})
            page.on('pageerror',lambda exc:report['errors'].append(str(exc)))
            await page.add_init_script("localStorage.setItem('tiny-dancer-session'," + json.dumps(validation['session']) + ')')
            await page.goto(URL)
            await page.wait_for_function("document.querySelector('#task-status').textContent.includes('Complete')")
            await page.wait_for_function("() => {const box=document.querySelector('#messages');return box.scrollHeight-box.clientHeight-box.scrollTop<4;}")
            report['scroll_at_latest_answer'] = True
            report['task_status'] = await page.locator('#task-status').inner_text()
            report['progress_label'] = await page.locator('#progress-label').inner_text()
            final = await page.locator('.message.assistant .message-text').last.inner_text()
            report['correct_date_visible'] = validation['comparison']['date'] in final
            report['all_rows_visible'] = sum(line.startswith('- ') for line in final.splitlines()) == validation['comparison']['games']
            report['stop_hidden'] = not await page.locator('#stop').is_visible()
            report['resume_hidden'] = not await page.locator('#resume-task').is_visible()
            report['historical_tools_marked_running'] = any(' · running' in title for title in await page.locator('.tool-event summary').all_inner_texts())
            report['desktop_overflow'] = await page.evaluate('document.documentElement.scrollWidth>innerWidth')
            link = page.locator('a[href^="/artifacts/data-"]').last
            report['artifact_http_status'] = (await page.request.head(URL + await link.get_attribute('href'))).status
            await page.screenshot(path=str(ROOT/'docs/answer-completed-workspace.png'),full_page=True)
            await page.set_viewport_size({'width':390,'height':844})
            report['mobile_overflow'] = await page.evaluate('document.documentElement.scrollWidth>innerWidth')
        finally:
            await browser.close()
    (ROOT/'docs/answer-ui-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    assert report['correct_date_visible'] and report['all_rows_visible']
    assert report['stop_hidden'] and report['resume_hidden'] and report['artifact_http_status']==200
    assert not report['historical_tools_marked_running']
    assert not report['errors'] and not report['desktop_overflow'] and not report['mobile_overflow']
    print(json.dumps(report))


if __name__=='__main__': asyncio.run(main())
