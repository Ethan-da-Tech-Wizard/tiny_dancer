# SPDX-License-Identifier: Apache-2.0
"""Inspect the actual completed native repair UI without starting model work."""
import asyncio
import json
import shutil
from pathlib import Path

from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:3210'


async def main():
    native=json.loads((ROOT/'docs/native-harness-validation.json').read_text())
    assert native['status']=='complete' and native['passed'],native['status']
    report={'session':native['session'],'job':native['job'],'errors':[],'checks':[]}
    async with async_playwright() as playwright:
        browser=await playwright.chromium.launch(executable_path=shutil.which('chromium'),headless=True)
        try:
            page=await browser.new_page(viewport={'width':1280,'height':900})
            page.on('pageerror',lambda error:report['errors'].append(str(error)))
            await page.add_init_script("localStorage.setItem('tiny-dancer-session',"+json.dumps(native['session'])+");localStorage.setItem('tiny-dancer-thinking','medium');")
            await page.goto(BASE)
            await page.wait_for_function("document.querySelector('#task-status').textContent.includes('Complete')")
            await page.wait_for_function("() => {const box=document.querySelector('#messages');return box.scrollHeight-box.clientHeight-box.scrollTop<4;}")
            report['task_status']=await page.locator('#task-status').inner_text()
            report['native_answer']=await page.locator('.message.assistant .message-text').last.inner_text()
            assert report['native_answer'].strip()
            assert 'checks passed' in report['task_status'].lower()
            assert not await page.locator('#stop').is_visible()
            assert not await page.locator('#resume-task').is_visible()
            assert not await page.locator('#thinking').is_disabled()
            assert await page.locator('#thinking').input_value()=='medium'
            titles=await page.locator('.tool-event summary').all_inner_texts()
            assert any('apply_patch' in title for title in titles),titles
            assert not any(' · running' in title for title in titles)
            for size,name in (({'width':1280,'height':900},'desktop'),({'width':390,'height':844},'mobile')):
                await page.set_viewport_size(size)
                assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                await page.screenshot(path=str(ROOT/f'docs/native-harness-completed-{name}.png'))
                report['checks'].append({'viewport':name,'completed_controls':True,'overflow':False})
        finally:
            await browser.close()
    assert not report['errors'],report['errors']
    report['passed']=True
    (ROOT/'docs/native-harness-ui-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':asyncio.run(main())
