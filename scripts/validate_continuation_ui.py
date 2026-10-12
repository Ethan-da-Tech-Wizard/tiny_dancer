# SPDX-License-Identifier: Apache-2.0
"""Check actual paused UI plus mocked network recovery/Resume without inference."""
import asyncio
import json
import shutil
import time
from pathlib import Path

import httpx
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:3210'


async def main():
    with httpx.Client(base_url=BASE,timeout=10) as client:
        client.get('/')
        status=client.get('/api/status').json()
        assert {'python_lookup','rust_lookup','discover_tools'}<=set(status['tools'])
        sessions=client.get('/api/sessions').json()
        original=next(s for s in sessions if s['id']=='e49878f2e88542cdaefe0fe660e32307')
        record=client.get('/api/sessions/'+original['id']).json()
        latest=record['jobs'][0]
        assert latest['status']=='paused',latest['status']
        heartbeat=client.get('/api/jobs/'+latest['id']+'/progress').json()
        assert heartbeat['status']=='paused' and heartbeat['progress']['kind']=='paused'
    errors,results=[],[]
    async with async_playwright() as playwright:
        browser=await playwright.chromium.launch(executable_path=shutil.which('chromium'),headless=True)
        context=await browser.new_context(viewport={'width':1280,'height':900})
        page=await context.new_page()
        page.on('pageerror',lambda error:errors.append(str(error)))
        await page.goto(BASE)
        await page.evaluate('(id)=>localStorage.setItem("tiny-dancer-session",id)',original['id'])
        await page.reload()
        await page.locator('#resume-task').wait_for(state='visible')
        assert not await page.locator('#stop').is_visible()
        assert await page.locator('#thinking').input_value()=='auto'
        assert await page.locator('#run-until-done').is_checked()
        assert not await page.locator('#progress-card').evaluate('(el)=>el.open')
        assert 'Time budget' in await page.locator('#pause-reason').inner_text()
        assert await page.locator('.source-link').count()>0
        assert 'CHECKED DATA LOOKUP' in await page.locator('#messages').inner_text()
        for size,name in (({'width':1280,'height':900},'desktop'),({'width':390,'height':844},'mobile')):
            await page.set_viewport_size(size)
            box=await page.locator('#resume-task').bounding_box()
            assert box and box['y']>=0 and box['y']+box['height']<=size['height']
            assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            await page.screenshot(path=str(ROOT/f'docs/resume-workspace-{name}.png'))
            results.append({'check':'actual paused '+name,'passed':True,'resume_in_viewport':True,'overflow':False})

        # Fixtures only: no real task is started, resumed, stopped or rewritten.
        phase='running';posted=[]
        fixture={'id':'ui-fixture','session':'ui-session','status':'running','created':time.time()-12,'finished':None,
                 'checkpoint':{'goal':'Continue the existing task','mode':'agent','steps':[{'title':'Already done','done':True}],
                               'summary':'','next_action':'','max_seconds':None,'run_until_done':True},
                 'progress':{'kind':'progress','data':{'tokens':64,'seconds':12},'created':time.time()},'elapsed_seconds':12}
        async def route(request):
            nonlocal phase
            path=request.request.url.removeprefix(BASE)
            if path.startswith('/api/jobs/ui-fixture/events'):
                await request.fulfill(status=200,content_type='text/event-stream',body=': disconnected fixture\n\n');return
            if path=='/api/jobs/ui-fixture/resume':
                posted.append(request.request.post_data_json);phase='running'
                fixture['status']='running';fixture['checkpoint']['next_action']=''
                await request.fulfill(json={'job':'ui-fixture'});return
            if path=='/api/status':
                data=status|{'active_job':'ui-fixture' if phase=='running' else None,'task':fixture if phase=='running' else None,'engine':'generating' if phase=='running' else 'not loaded'}
            elif path=='/api/sessions': data=[{'id':'ui-session','title':'UI fixture','cwd':str(ROOT/'workspace')}]
            elif path=='/api/sessions/ui-session':
                data={'id':'ui-session','title':'UI fixture','cwd':str(ROOT/'workspace'),'messages':[],
                      'jobs':[fixture|{'status':phase}]}
            elif path=='/api/jobs/ui-fixture/progress': data=fixture|{'status':phase}
            else: await request.continue_();return
            await request.fulfill(json=data)
        await page.route(BASE+'/api/**',route)
        await page.set_viewport_size({'width':1280,'height':900})
        await page.evaluate('localStorage.setItem("tiny-dancer-session","ui-session")')
        await page.reload()
        await page.wait_for_function('document.querySelector("#task-status").textContent.includes("64 tokens")',timeout=12000)
        assert await page.locator('#stop').is_visible()
        phase='paused';fixture['status']='paused';fixture['checkpoint']['next_action']='Fixture blocker; progress remains saved.'
        await page.locator('#resume-task').wait_for(state='visible',timeout=12000)
        assert not await page.locator('#stop').is_visible()
        assert 'Fixture blocker' in await page.locator('#pause-reason').inner_text()
        results.append({'check':'polling recovers progress and pause after stream disconnect','passed':True,'scope':'network fixture'})
        await page.locator('#thinking').select_option('medium')
        await page.locator('#resume-task').click()
        await page.locator('#stop').wait_for(state='visible')
        assert posted and posted[0]['run_until_done'] is True
        assert posted[0]['max_tokens']==1024
        assert posted[0]['reasoning_effort']=='medium'
        assert await page.locator('#thinking').is_disabled()
        results.append({'check':'Resume sends saved-job request and until-done policy','passed':True,'scope':'intercepted request; no native task resumed'})
        await browser.close()
    assert not errors,errors
    report={'at':time.time(),'passed':True,'checks':results,'javascript_errors':errors,
            'scope':'Real paused user UI, screenshots and public heartbeat; fixture stream/Resume only. No model task started or modified.'}
    (ROOT/'docs/continuation-ui-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':asyncio.run(main())
