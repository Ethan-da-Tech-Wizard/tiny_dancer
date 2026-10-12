# SPDX-License-Identifier: Apache-2.0
import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from openai_harmony import Message, Role
from app.agent import AgentRun
from app.language_tools import lookup
from app.task_policy import contract_for, tools_for
from app.tools import ComputerTools, ROOT, TOOLS
from tests.test_agent import ScriptedEngine, call


class RoutingTests(unittest.TestCase):
    def names(self, text, cwd=None):
        return {item['name'] for item in tools_for(contract_for(text,cwd=cwd),TOOLS)}

    def test_unrelated_tasks_do_not_load_language_schemas(self):
        for text in ('Who won the latest NFL game?', 'Write me a grocery list', 'Remove rust from the bicycle'):
            self.assertFalse(self.names(text) & {'python_lookup','rust_lookup'})
        self.assertIn('discover_tools',self.names('Who won the latest NFL game?'))

    def test_language_and_project_hints_select_only_relevant_tools(self):
        self.assertEqual(self.names('Look up Python pathlib docs') & {'python_lookup','rust_lookup'}, {'python_lookup'})
        self.assertEqual(self.names('What are the Cargo dependencies?') & {'python_lookup','rust_lookup'}, {'rust_lookup'})
        with tempfile.TemporaryDirectory() as folder:
            Path(folder,'Cargo.toml').write_text('[package]\nname="demo"\n')
            self.assertIn('rust_lookup',self.names('Inspect project dependencies',folder))
            self.assertNotIn('rust_lookup',self.names('Who won the NFL game?',folder))


class LookupTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT/'run/artifacts')
        self.path = Path(self.temp.name)
        self.artifacts, self.cache = self.path/'artifacts', self.path/'cache'

    async def asyncTearDown(self): self.temp.cleanup()

    async def run_lookup(self, language, args, handler=None):
        transport = httpx.MockTransport(handler) if handler else httpx.MockTransport(lambda r: self.fail('Unexpected network access'))
        return await lookup(language,args,str(self.path),self.artifacts,self.cache,transport)

    async def test_python_exact_version_dependency_markers_and_cache(self):
        calls = []
        def handle(request):
            calls.append(str(request.url))
            return httpx.Response(200,json={'info':{'name':'httpx','version':'0.28.1','requires_python':'>=3.8',
                'requires_dist':['anyio>=3; python_version >= "3.8"','rich; extra == "cli"'],
                'license_expression':'BSD-3-Clause','project_urls':{'Documentation':'https://www.python-httpx.org/'}}})
        args = {'action':'package','package':'httpx','version':'0.28.1'}
        first = await self.run_lookup('python',args,handle)
        second = await self.run_lookup('python',args,handle)
        self.assertEqual(calls,['https://pypi.org/pypi/httpx/0.28.1/json'])
        self.assertTrue(second['cached']); self.assertFalse(first['cached'])
        self.assertEqual(first['retrieved_at'],second['retrieved_at'])
        self.assertIn('extra',first['dependencies'][1]['marker'])
        self.assertEqual(first['license_expression'],'BSD-3-Clause')

    async def test_rust_pins_dependency_endpoint_and_preserves_features(self):
        calls = []
        def handle(request):
            calls.append(request.url.path)
            self.assertIn('TinyDancer',request.headers['user-agent'])
            if request.url.path.endswith('/dependencies'):
                return httpx.Response(200,json={'dependencies':[{'crate_id':'bytes','req':'^1','kind':'normal','optional':True,'default_features':False,'features':['std'],'target':'cfg(unix)'}]})
            return httpx.Response(200,json={'crate':{'max_stable_version':'1.2.3'},'versions':[
                {'crate':'tokio','num':'1.2.3','license':'MIT','rust_version':'1.70','features':{'full':['rt']},'yanked':False}]})
        result = await self.run_lookup('rust',{'action':'package','package':'tokio'},handle)
        self.assertEqual(calls,['/api/v1/crates/tokio','/api/v1/crates/tokio/1.2.3/dependencies'])
        self.assertEqual(result['version'],'1.2.3')
        self.assertTrue(result['dependencies'][0]['optional'])
        self.assertEqual(result['dependencies'][0]['target'],'cfg(unix)')
        self.assertEqual(len(result['sources']),2)

    async def test_docs_version_anchor_excludes_navigation_and_scripts(self):
        urls = []
        def handle(request):
            urls.append(str(request.url))
            return httpx.Response(200,text='<html><head><title>Pathlib</title></head><body><nav>NOISE</nav><main><h1>Pathlib</h1><section id="pathlib.Path"><p>Correct version.</p><pre>Path("a").read_text()</pre></section><section id="other">Wrong section</section><script>bad()</script></main></body></html>')
        result = await self.run_lookup('python',{'action':'docs','url':'https://docs.python.org/3.12/library/pathlib.html#pathlib.Path'},handle)
        self.assertEqual(urls,['https://docs.python.org/3.12/library/pathlib.html'])
        self.assertIn('Correct version',result['text'])
        self.assertNotIn('Wrong section',result['text'])
        self.assertNotIn('NOISE',result['text'])
        self.assertNotIn('bad()',result['text'])
        self.assertTrue(result['source'].endswith('#pathlib.Path'))

    async def test_documentation_redirects_cannot_leave_reference_hosts(self):
        calls = []
        def handle(request):
            calls.append(str(request.url))
            return httpx.Response(302,headers={'Location':'http://127.0.0.1/private'})
        with self.assertRaises(ValueError):
            await self.run_lookup('rust',{'action':'docs','topic':'std'},handle)
        self.assertEqual(len(calls),1)

    async def test_sphinx_and_rustdoc_anchors_include_the_method_description(self):
        for language,url,html in (
            ('python','https://docs.python.org/3.12/library/pathlib.html#method','<main><dl><dt id="method">Signature</dt><dd>Description and examples</dd></dl><dl><dt>Next method</dt><dd>OTHER</dd></dl></main>'),
            ('rust','https://doc.rust-lang.org/stable/std/result/enum.Result.html#method','<main><details class="method-toggle"><summary><section id="method">Signature</section></summary><div class="docblock">Description and examples</div></details><details class="method-toggle">OTHER</details></main>'),
        ):
            with self.subTest(language=language):
                result=await self.run_lookup(language,{'action':'docs','url':url},lambda r:httpx.Response(200,text=html))
                self.assertIn('Description and examples',result['text'])
                self.assertNotIn('OTHER',result['text'])

    async def test_default_python_docs_and_exact_rust_crate_docs(self):
        urls = []
        def handle(request):
            urls.append(str(request.url)); return httpx.Response(200,text='<main>API docs</main>')
        await self.run_lookup('python',{'action':'docs','topic':'asyncio','version':'3.12'},handle)
        await self.run_lookup('rust',{'action':'docs','package':'serde-json','version':'1.0.1'},handle)
        self.assertEqual(urls,['https://docs.python.org/3.12/library/asyncio.html','https://docs.rs/serde-json/1.0.1/serde_json/'])

    async def test_errors_and_invalid_identifiers_are_not_saved_as_evidence(self):
        for language,args,status in (
            ('python',{'action':'package','package':'missing'},404),
            ('rust',{'action':'package','package':'missing'},429),
        ):
            with self.subTest(language=language),self.assertRaises(httpx.HTTPStatusError):
                await self.run_lookup(language,args,lambda r:httpx.Response(status,json={'error':'failure'}))
        with self.assertRaises(ValueError):
            await self.run_lookup('python',{'action':'package','package':'../../secrets'})
        self.assertFalse(self.artifacts.exists())

    async def test_response_and_prompt_bounds_preserve_full_evidence(self):
        rows = ['dependency'+str(n)+'>=1' for n in range(300)]
        result = await self.run_lookup('python',{'action':'package','package':'demo'},lambda r:httpx.Response(200,json={'info':{'name':'demo','version':'1','requires_dist':rows}}))
        self.assertTrue(result['truncated'])
        self.assertLess(len(json.dumps(result)),6500)
        saved = json.loads(Path(result['local_path']).read_text())
        self.assertEqual(len(saved['dependencies']),300)
        with self.assertRaisesRegex(ValueError,'2 MB'):
            await self.run_lookup('rust',{'action':'docs','topic':'book'},lambda r:httpx.Response(200,text='x'*2_000_001))

    async def test_local_python_manifest_groups_and_literal_includes_no_execution(self):
        (self.path/'pyproject.toml').write_text('[project]\nname="demo"\nrequires-python=">=3.12"\ndependencies=["httpx>=0.28"]\n[project.optional-dependencies]\ntest=["pytest"]\n[dependency-groups]\ndev=[{include-group="test"}]\n')
        (self.path/'requirements.txt').write_text('requests==2.32.3\n-r other.txt\n--index-url https://example.com\n')
        (self.path/'setup.py').write_text('raise RuntimeError("Never execute this")')
        result = await self.run_lookup('python',{'action':'dependencies'})
        self.assertFalse(result['network_used'])
        self.assertEqual(len(result['sources']),2)
        pyproject = next(m for m in result['manifests'] if m['path'].endswith('pyproject.toml'))
        self.assertEqual(pyproject['content']['dependency-groups']['dev'],[{'include-group':'test'}])
        requirements = next(m for m in result['manifests'] if m['path'].endswith('requirements.txt'))
        self.assertEqual(requirements['content']['directives'],['-r other.txt','--index-url https://example.com'])

    async def test_rust_local_manifest_targets_workspace_and_lock_versions(self):
        (self.path/'Cargo.toml').write_text('[package]\nname="demo"\nversion="0.1.0"\n[dependencies]\nserde={workspace=true}\n[workspace.dependencies]\nserde="1"\n[target.\'cfg(unix)\'.dependencies]\nlibc="0.2"\n')
        (self.path/'Cargo.lock').write_text('version=4\n[[package]]\nname="serde"\nversion="1.0.219"\nsource="registry+https://github.com/rust-lang/crates.io-index"\n')
        result = await self.run_lookup('rust',{'action':'dependencies'})
        manifest = next(m for m in result['manifests'] if m['path'].endswith('Cargo.toml'))
        self.assertTrue(manifest['content']['dependencies']['serde']['workspace'])
        lock = next(m for m in result['manifests'] if m['path'].endswith('Cargo.lock'))
        self.assertEqual(lock['content']['package'][0]['version'],'1.0.219')
        self.assertFalse(result['network_used'])


class AgentDiscoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_late_discovery_changes_tools_and_survives_resume(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'workspace') as folder:
            Path(folder,'Cargo.toml').write_text('[dependencies]\nserde="1"\n')
            messages, events = [], []
            tools = ComputerTools()
            request = SimpleNamespace(prompt='What does this use?',mode='agent',max_tokens=512,max_turns=3)
            run = AgentRun(ScriptedEngine([call('discover_tools',{'language':'rust'}),call('rust_lookup',{'action':'dependencies'}),
                Message.from_role_and_content(Role.ASSISTANT,'Declared serde dependency. Source: '+str(Path(folder,'Cargo.toml'))).with_channel('final')]),
                tools,folder,request,lambda:messages,lambda m,role=None:messages.append(m.to_dict()),lambda k,d:events.append((k,d)),lambda s:None,threading.Event())
            self.assertNotIn('rust_lookup',run.allowed_tools)
            self.assertEqual(await run.run(),'complete')
            self.assertIn('rust_lookup',run.allowed_tools)
            self.assertIn(str(Path(folder,'Cargo.toml')),run.state['sources'])
            resumed = AgentRun(ScriptedEngine([]),tools,folder,request,lambda:[],lambda *a:None,lambda *a:None,lambda *a:None,threading.Event(),run.state)
            self.assertIn('rust_lookup',resumed.allowed_tools)
            await tools.close()

    async def test_discovery_does_no_network_and_unselected_lookup_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            tools = ComputerTools()
            run = AgentRun(ScriptedEngine([]),tools,folder,SimpleNamespace(prompt='What does this do?',mode='agent',max_tokens=512),
                           lambda:[],lambda *a:None,lambda *a:None,lambda *a:None,threading.Event())
            with self.assertRaisesRegex(ValueError,'unavailable'):
                await run.execute('python_lookup',{'action':'package','package':'httpx'})
            with patch('httpx.AsyncClient',side_effect=AssertionError('Unexpected network')):
                result = await run.execute('discover_tools',{'language':'python'})
            self.assertEqual(result['enabled'],'python_lookup')
            self.assertIn('python_lookup',run.allowed_tools)
            with self.assertRaises(ValueError): await run.execute('discover_tools',{'language':'ruby'})
            await tools.close()
