# SPDX-License-Identifier: Apache-2.0
"""Frozen native task criteria; no solution code is supplied to the agent."""
from pathlib import Path
import hashlib
import json
import subprocess
import tempfile

INVENTORY_PROMPT = '''Build inventory.py, a standard-library Python command line tool invoked as python inventory.py ROOT OUTPUT. Recursively inventory regular files under ROOT, including hidden files. Skip symbolic links to files and directories. Write OUTPUT as a JSON array of objects with path (relative POSIX path), size (bytes), and sha256 (hex digest), sorted by path. Exclude OUTPUT itself when it lies inside ROOT. Never replace an existing output if scanning or argument validation fails; errors must have nonzero status and clear stderr without a traceback. Use an atomic replacement for successful output. Keep the supplied test_acceptance.py unchanged, add your own relevant tests, and run the project tests. Run your tool on sample_tree and save the actual result as report.json in this folder. Work here until all requested outputs and tests are checked.'''

INVENTORY_ACCEPTANCE = '''import hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class AcceptanceTests(unittest.TestCase):
 def invoke(self,source,output):
  return subprocess.run([sys.executable,str(ROOT/"inventory.py"),str(source),str(output)],cwd=ROOT,capture_output=True,text=True,timeout=15)
 def entries(self,files):
  return sorted([{"path":p,"size":len(data),"sha256":hashlib.sha256(data).hexdigest()} for p,data in files.items()],key=lambda x:x["path"])
 def test_binary_hidden_nested_sorted(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as d:
   base=Path(d);source=base/"tree";source.mkdir();files={"z.bin":b"\\x00\\xff", ".hidden":b"", "a/b.txt":b"hello\\n"}
   for name,data in files.items():
    p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
   out=base/"report.json";r=self.invoke(source,out);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(out.read_text()),self.entries(files))
 def test_symlinks_skipped_without_following_cycles(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as d:
   base=Path(d);source=base/"tree";source.mkdir();(source/"real").write_bytes(b"ok");(base/"outside").write_bytes(b"secret")
   (source/"linked-file").symlink_to(base/"outside");(source/"cycle").symlink_to(source,target_is_directory=True)
   out=base/"report.json";r=self.invoke(source,out);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(out.read_text()),self.entries({"real":b"ok"}))
 def test_existing_output_inside_root_excluded(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as d:
   source=Path(d);(source/"data").write_bytes(b"abc");out=source/"report.json";out.write_text("previous")
   r=self.invoke(source,out);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(out.read_text()),self.entries({"data":b"abc"}))
 def test_empty_tree(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as d:
   source=Path(d)/"empty";source.mkdir();out=Path(d)/"report.json";r=self.invoke(source,out)
   self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(out.read_text()),[])
 def test_missing_root_preserves_output(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as d:
   out=Path(d)/"report.json";out.write_text("keep me");r=self.invoke(Path(d)/"missing",out)
   self.assertNotEqual(r.returncode,0);self.assertTrue(r.stderr.strip());self.assertNotIn("Traceback",r.stderr);self.assertEqual(out.read_text(),"keep me")
 def test_file_root_rejected_and_preserves_output(self):
  with tempfile.TemporaryDirectory(dir=ROOT) as d:
   source=Path(d)/"file";source.write_text("data");out=Path(d)/"report.json";out.write_text("old");r=self.invoke(source,out)
   self.assertNotEqual(r.returncode,0);self.assertTrue(r.stderr.strip());self.assertNotIn("Traceback",r.stderr);self.assertEqual(out.read_text(),"old")
if __name__=="__main__":unittest.main()
'''

RANGES_PROMPT = '''Create a standard-library-only Rust Cargo application named ranges in this folder. Its CLI takes one input filepath. Each nonblank line contains one signed 64-bit integer; trim surrounding whitespace and ignore blank lines. Sort and deduplicate the numbers, then print a JSON array of maximal consecutive ranges, each as an object with start and end integer fields, sorted by start. Empty input prints []. Handle both i64 boundaries without arithmetic overflow. Reject malformed integers, out-of-range integers, missing files and incorrect arguments with nonzero status and clear stderr; failed requests must not print a partial JSON result. Add relevant Rust unit tests and run cargo test --offline and the supplied Python CLI tests. Keep test_acceptance.py unchanged. Run the tool on sample.txt and save its JSON output to ranges.json in this folder. Work here until the outputs and tests are checked. Do not add external dependencies.'''

RANGES_ACCEPTANCE = '''import json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class AcceptanceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  r=subprocess.run(["cargo","build","--offline","--quiet"],cwd=ROOT,capture_output=True,text=True,timeout=120)
  if r.returncode:raise RuntimeError(r.stderr)
  cls.binary=ROOT/"target/debug/ranges"
 def invoke(self,text):
  with tempfile.TemporaryDirectory(dir=ROOT) as d:
   p=Path(d)/"numbers.txt";p.write_text(text)
   return subprocess.run([str(self.binary),str(p)],cwd=ROOT,capture_output=True,text=True,timeout=10)
 def output(self,text):
  r=self.invoke(text);self.assertEqual(r.returncode,0,r.stderr);return json.loads(r.stdout)
 def test_sort_deduplicate_and_compress(self):
  self.assertEqual(self.output("5\\n2\\n1\\n2\\n4\\n9\\n"),[{"start":1,"end":2},{"start":4,"end":5},{"start":9,"end":9}])
 def test_signed_and_whitespace(self):
  self.assertEqual(self.output(" -2 \\n\\n0\\n-1\\n  4\\n"),[{"start":-2,"end":0},{"start":4,"end":4}])
 def test_both_integer_boundaries(self):
  low=-(2**63);high=2**63-1
  self.assertEqual(self.output(f"{high}\\n{high-1}\\n{low}\\n{low+1}\\n"),[{"start":low,"end":low+1},{"start":high-1,"end":high}])
 def test_empty(self):self.assertEqual(self.output("\\n \\n"),[])
 def test_invalid_and_out_of_range(self):
  for text in ("1\\nbad\\n", "2\\n1.5\\n", "9223372036854775808\\n", "-9223372036854775809\\n"):
   with self.subTest(text=text):
    r=self.invoke(text);self.assertNotEqual(r.returncode,0);self.assertTrue(r.stderr.strip());self.assertEqual(r.stdout.strip(),"")
 def test_missing_file_and_incorrect_arguments(self):
  for args in ([],[str(ROOT/"missing-input")],["a","b"]):
   with self.subTest(args=args):
    r=subprocess.run([str(self.binary)]+args,cwd=ROOT,capture_output=True,text=True,timeout=10)
    self.assertNotEqual(r.returncode,0);self.assertTrue(r.stderr.strip());self.assertEqual(r.stdout.strip(),"")
if __name__=="__main__":unittest.main()
'''

# Keep the established release requirements distinct from diagnostic ladder cases.
RELEASE_CASES = ('inventory', 'ranges')

CASES = {
    'labels': {'title': 'Small native Python label function and new tests', 'kind': 'module',
               'prompt': 'Create labels.py with normalize_label(text). For a string, remove leading and trailing whitespace, collapse internal whitespace to one space, and lowercase its letters. Empty or whitespace-only strings must return an empty string. Use only the Python standard library. Add your own relevant tests and run the project tests. Existing acceptance tests must remain unchanged. Finish when the requested function and tests work.',
               'acceptance': '''import unittest
from labels import normalize_label
class AcceptanceTests(unittest.TestCase):
 def test_outer_spaces(self):self.assertEqual(normalize_label("  Hello  "),"hello")
 def test_inner_spaces(self):self.assertEqual(normalize_label("a   b"),"a b")
 def test_case(self):self.assertEqual(normalize_label("HeLLo"),"hello")
 def test_tabs_and_newlines(self):self.assertEqual(normalize_label("a\\tb\\nc"),"a b c")
 def test_empty(self):self.assertEqual(normalize_label(""),"")
 def test_only_whitespace(self):self.assertEqual(normalize_label(" \\t\\n"),"")
if __name__=="__main__":unittest.main()
''', 'inputs': {},
               'independent': ['Unicode lowercase', 'nonbreaking-space and em-space whitespace', 'zero-width text remains text', 'mixed numbers and punctuation preserved']},
    'inventory': {'title': 'Fresh Python file inventory and atomic JSON output',
                  'prompt': INVENTORY_PROMPT, 'acceptance': INVENTORY_ACCEPTANCE,
                  'inputs': {'sample_tree/.hidden': b'', 'sample_tree/nested/hello.txt': b'hello\n', 'sample_tree/data.bin': b'\x00\xff'},
                  'independent': ['large binary digest and unicode filename', 'symlink outside root and nested symlink cycle', 'repeat output inside root remains deterministic', 'scan failure preserves prior output', 'actual report.json matches sample_tree']},
    'ranges': {'title': 'Fresh Rust CLI ranges, validation and integer boundaries',
               'prompt': RANGES_PROMPT, 'acceptance': RANGES_ACCEPTANCE,
               'inputs': {'sample.txt': b'5\n1\n2\n2\n4\n-1\n0\n9\n'},
               'independent': ['independently derived randomized signed ranges', 'duplicates of both integer boundaries', 'invalid suffix and huge integer reject without partial output', 'actual ranges.json matches sample.txt']},
}


def grade(folder, case, root):
    """Black-box cases withheld until native termination, independent of seeded tests."""
    folder,root=Path(folder),Path(root); checks=[]
    def record(name,passed,**detail):checks.append({'check':name,'passed':bool(passed),**detail})
    if case=='labels':
        cases=[('unicode lowercase','  ÄÖ TEST  ','äö test'),
               ('unicode whitespace','x\u00a0\u2003Y','x y'),
               ('zero-width text','A\u200bB','a\u200bb'),
               ('numbers and punctuation',' A-1\tB_2! ','a-1 b_2!')]
        source='import json,sys; from labels import normalize_label; print(json.dumps([normalize_label(x) for x in json.loads(sys.argv[1])],ensure_ascii=False))'
        try:
            result=subprocess.run(['/usr/bin/python3','-c',source,json.dumps([row[1] for row in cases])],
                                  cwd=folder,capture_output=True,text=True,timeout=10)
            try:actual=json.loads(result.stdout)
            except ValueError:actual=None
            for index,(name,_,wanted) in enumerate(cases):
                record(name,result.returncode==0 and isinstance(actual,list) and len(actual)==len(cases) and actual[index]==wanted,
                       exit_code=result.returncode,stderr=result.stderr[-600:])
        except subprocess.TimeoutExpired:
            record('function terminates',False,timed_out=True)
    elif case=='inventory':
        def call(source,out):return subprocess.run(['/usr/bin/python3',str(folder/'inventory.py'),str(source),str(out)],cwd=folder,capture_output=True,text=True,timeout=20)
        def expected(files):return sorted([{'path':p,'size':len(b),'sha256':hashlib.sha256(b).hexdigest()} for p,b in files.items()],key=lambda r:r['path'])
        with tempfile.TemporaryDirectory(dir=root/'run') as d:
            base=Path(d);source=base/'tree';source.mkdir();files={'資料/δ.bin':bytes(range(256))*4097,'a.txt':b'a\n','.empty':b''}
            for name,data in files.items():
                p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            (base/'outside').write_bytes(b'private');(source/'資料/link').symlink_to(base/'outside');(source/'資料/cycle').symlink_to(source,target_is_directory=True)
            out=source/'result.json';out.write_text('prior')
            for n in range(2):
                r=call(source,out)
                try:actual=json.loads(out.read_text())
                except (OSError,ValueError):actual=None
                record('unseen binary/unicode/symlinks/output exclusion '+str(n+1),r.returncode==0 and actual==expected(files),exit_code=r.returncode,stderr=r.stderr[-1000:])
            before=out.read_bytes();r=call(base/'absent',out)
            record('invalid root preserves actual prior bytes',r.returncode!=0 and out.read_bytes()==before and bool(r.stderr.strip()) and 'Traceback' not in r.stderr,exit_code=r.returncode)
            # /proc/1/mem is inaccessible to this ordinary user. Scanning a
            # temporary tree with a real unreadable file must fail, not omit it.
            denied=source/'denied';denied.write_bytes(b'cannot read');denied.chmod(0)
            try:
                r=call(source,out);record('scan read failure preserves actual prior bytes',r.returncode!=0 and out.read_bytes()==before and bool(r.stderr.strip()) and 'Traceback' not in r.stderr,exit_code=r.returncode,stderr=r.stderr[-1000:])
            finally:denied.chmod(0o600)
        wanted=expected(CASES['inventory']['inputs'] | {})
        wanted=[dict(item,path=item['path'].removeprefix('sample_tree/')) for item in wanted]
        try:actual=json.loads((folder/'report.json').read_text())
        except (OSError,ValueError):actual=None
        record('requested real report.json complete and exact',actual==wanted)
    elif case=='ranges':
        binary=folder/'target/debug/ranges'
        def invoke(text):
            with tempfile.TemporaryDirectory(dir=root/'run') as d:
                p=Path(d)/'unseen.txt';p.write_text(text)
                return subprocess.run([str(binary),str(p)],cwd=folder,capture_output=True,text=True,timeout=10)
        if not binary.is_file():return [{'check':'actual compiled CLI exists','passed':False}]
        values=[(n*7919)%1301-650 for n in range(2300)]+[-2**63,-2**63,2**63-1,2**63-1]
        # Derive consecutive groups by value-index, rather than replaying the
        # product's expected adjacent-comparison implementation.
        import itertools
        wanted=[{'start':group[0][1],'end':group[-1][1]} for _,items in itertools.groupby(enumerate(sorted(set(values))),lambda x:x[1]-x[0]) if (group:=list(items))]
        r=invoke('\n'.join(map(str,reversed(values))))
        try:actual=json.loads(r.stdout)
        except ValueError:actual=None
        record('unseen randomized groups with duplicate i64 boundaries',r.returncode==0 and actual==wanted,exit_code=r.returncode,stderr=r.stderr[-1000:])
        for text in ('1\n2x\n','1\n'+'9'*100+'\n'):
            r=invoke(text);record('unseen malformed or oversized input',r.returncode!=0 and bool(r.stderr.strip()) and not r.stdout.strip(),exit_code=r.returncode)
        try:actual=json.loads((folder/'ranges.json').read_text())
        except (OSError,ValueError):actual=None
        record('requested real ranges.json complete and exact',actual==[{'start':-1,'end':2},{'start':4,'end':5},{'start':9,'end':9}])
    else:raise ValueError('Unknown case')
    return checks
