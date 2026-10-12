import asyncio
import json
import tempfile
import unittest
from pathlib import Path
import httpx
from app.tools import ComputerTools, ROOT

class ComputerIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'workspace', prefix='tool-validation-')
        self.cwd = self.temp.name
        self.tools = ComputerTools(browser_profile=Path(self.cwd) / 'browser-profile')

    async def asyncTearDown(self):
        await self.tools.close()
        self.temp.cleanup()

    async def test_shell_and_file_backup(self):
        path = Path(self.cwd) / 'note.txt'
        await self.tools.execute('write_file', {'path':str(path),'content':'first version'}, self.cwd)
        result = await self.tools.execute('write_file', {'path':str(path),'content':'second version'}, self.cwd)
        self.assertEqual(Path(result['backup']).read_text(), 'first version')
        self.assertIn('second version', (await self.tools.execute('read_file', {'path':str(path)}, self.cwd))['text'])
        result = await self.tools.execute('shell', {'command':"python3 -c 'print(6 * 7)'"}, self.cwd)
        self.assertEqual(result['exit_code'], 0)
        self.assertIn('42', result['output'])

    async def test_timeout_kills_shell(self):
        result = await self.tools.execute('shell', {'command':'sleep 30', 'timeout':1}, self.cwd)
        self.assertTrue(result['timed_out'])
        self.assertNotEqual(result['exit_code'], 0)

    async def test_cancel_kills_background_group(self):
        pidfile = Path(self.cwd) / 'pid'
        task = asyncio.create_task(self.tools.execute('shell', {'command':f'sleep 60 & echo $! > {pidfile}; wait'}, self.cwd))
        for _ in range(30):
            if pidfile.exists(): break
            await asyncio.sleep(0.05)
        child = int(pidfile.read_text())
        task.cancel()
        with self.assertRaises(asyncio.CancelledError): await task
        import psutil
        self.assertTrue(not psutil.pid_exists(child) or psutil.Process(child).status() == psutil.STATUS_ZOMBIE)

    async def test_browser_inspects_local_page(self):
        result = await self.tools.execute('browser', {'action':'open','url':'http://127.0.0.1:3210'}, self.cwd)
        self.assertEqual(result['http_status'], 200)
        self.assertIn('Tiny Dancer', result['title'])
        self.assertIn('GPT-OSS-20B', result['text'])

    async def test_browser_reports_missing_page_status(self):
        result = await self.tools.execute('browser', {'action':'open','url':'http://127.0.0.1:3210/missing-validation-page'}, self.cwd)
        self.assertEqual(result['http_status'], 404)
        self.assertIn('Not Found', result['text'])

    async def test_browser_prefers_main_content_and_its_unique_links(self):
        from urllib.parse import quote
        html = '<nav>Navigation menu <a href="https://example.com/nav">Menu</a></nav><main>Actual dated result<a href="https://example.com/result">Source</a><a href="https://example.com/result">Again</a></main>'
        result = await self.tools.execute('browser', {'action':'open','url':'data:text/html,'+quote(html)}, self.cwd)
        self.assertIn('Actual dated result', result['text'])
        self.assertNotIn('Navigation menu', result['text'])
        self.assertEqual(result['links'][0]['url'], 'https://example.com/result')
        self.assertEqual(sum(link['url']=='https://example.com/result' for link in result['links']), 1)

    async def test_desktop_lists_real_windows(self):
        result = await self.tools.execute('desktop', {'action':'windows'}, self.cwd)
        self.assertIsInstance(result, list)
        self.assertTrue(any(w.get('class') for w in result))

    async def test_api_auth_and_origin(self):
        async with httpx.AsyncClient(base_url='http://127.0.0.1:3210') as client:
            self.assertEqual((await client.get('/api/status')).status_code, 401)
            self.assertEqual((await client.get('/')).status_code, 200)
            self.assertEqual((await client.get('/api/status')).status_code, 200)
            response = await client.post('/api/sessions', json={}, headers={'Origin':'https://example.com'})
            self.assertEqual(response.status_code, 403)
            response = await client.get('/api/status', headers={'Host':'attacker.example'})
            self.assertEqual(response.status_code, 403)

    async def test_sse_reconnect_resumes_after_last_event(self):
        import sqlite3, time, uuid
        job='sse-check-'+uuid.uuid4().hex
        with sqlite3.connect(ROOT/'run/workspace.sqlite3') as con:
            con.execute('INSERT INTO jobs VALUES(?,?,?,?,?)',(job,'test','complete',time.time(),time.time()))
            first=con.execute('INSERT INTO events(job,kind,data,created) VALUES(?,?,?,?)',(job,'delta',json.dumps({'text':'already-seen'}),time.time())).lastrowid
            con.execute('INSERT INTO events(job,kind,data,created) VALUES(?,?,?,?)',(job,'delta',json.dumps({'text':'resume-here'}),time.time()))
        try:
            async with httpx.AsyncClient(base_url='http://127.0.0.1:3210') as client:
                await client.get('/')
                response=await client.get('/api/jobs/'+job+'/events',headers={'Last-Event-ID':str(first)})
                self.assertEqual(response.status_code,200)
                self.assertNotIn('already-seen',response.text)
                self.assertIn('resume-here',response.text)
                self.assertIn('event: closed',response.text)
        finally:
            with sqlite3.connect(ROOT/'run/workspace.sqlite3') as con:
                con.execute('DELETE FROM events WHERE job=?',(job,))
                con.execute('DELETE FROM jobs WHERE id=?',(job,))

if __name__ == '__main__': unittest.main()
