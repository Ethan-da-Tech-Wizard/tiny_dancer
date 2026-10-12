# SPDX-License-Identifier: Apache-2.0
"""Require a fixed failed task and two distinct native coding passes."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.native_suite_cases import CASES, RELEASE_CASES
from scripts.inventory_goal_audit import CRITERIA as INVENTORY_GOAL_CRITERIA
from scripts.inventory_extended_audit import CRITERIA as SPECIAL_FILE_CRITERIA

ALL_INVENTORY_CRITERIA=INVENTORY_GOAL_CRITERIA+SPECIAL_FILE_CRITERIA


def runtime_fingerprint(root):
    """Match native observers' source/config/UI digest without importing server."""
    root=Path(root)
    if not (root/'app').is_dir() or not (root/'config.json').is_file():
        return None
    digest=hashlib.sha256()
    paths=sorted((root/'app').rglob('*.py'))+[root/'config.json']
    paths+=sorted((root/'app/static').glob('*'))
    try:
        for path in paths:
            if path.is_file():
                digest.update(str(path.relative_to(root)).encode());digest.update(path.read_bytes())
    except OSError:
        return None
    return digest.hexdigest()


def release_checks(root):
    root=Path(root);docs=root/'docs';results=[]
    current=runtime_fingerprint(root)
    repair=docs/'precision-repair-retest-validation.json'
    def read(path):
        try:
            data=json.loads(path.read_text())
            return data if isinstance(data,dict) else None
        except (OSError,ValueError):return None
    def check(name,path,expected=None):
        report=read(path) if path else None
        reasons=[]
        if not report:reasons.append('No completed report')
        else:
            if report.get('status')!='complete' or report.get('passed') is not True:reasons.append('Latest native run did not pass')
            if report.get('operator_interventions'):reasons.append('Operator intervened during the run')
            checks=report.get('checks',{})
            if not checks or any(value is not True for value in checks.values()):reasons.append('Acceptance or independent checks failed')
            if checks.get('runtime_frozen') is not True:reasons.append('No frozen-runtime witness')
            recorded=report.get('runtime_sha256_before')
            if not isinstance(recorded,str) or len(recorded)!=64:reasons.append('No recorded runtime fingerprint')
            elif current is None or recorded!=current:reasons.append('Report does not match the current runtime')
            if 'runtime_sha256_after' in report and report['runtime_sha256_after']!=recorded:
                reasons.append('Runtime changed during evaluation')
            if report.get('checkpoint',{}).get('verified') is not True:reasons.append('No native verified completion')
            if not report.get('tool_calls'):reasons.append('No actual native tool execution recorded')
            if expected:
                if report.get('prompt')!=expected['prompt']:reasons.append('Frozen goal changed')
                if report.get('acceptance_sha256')!=expected['acceptance_sha256']:reasons.append('Frozen acceptance changed')
                if not report.get('independent_checks') or not all(c.get('passed') is True for c in report['independent_checks']):reasons.append('Independent CLI evidence missing or failed')
            if name=='inventory':
                if report.get('additional_independent_criteria')!=list(ALL_INVENTORY_CRITERIA):
                    reasons.append('Broader inventory goal checks were not declared')
                audit=report.get('additional_goal_checks')
                if not isinstance(audit,list) or len(audit)!=len(ALL_INVENTORY_CRITERIA) or \
                        {c.get('check') for c in audit if isinstance(c,dict)}!=set(ALL_INVENTORY_CRITERIA) or \
                        not all(isinstance(c,dict) and c.get('passed') is True for c in audit):
                    reasons.append('Output replacement, directory failure or special-file checks missing or failed')
        results.append({'task':name,'passed':not reasons,'reasons':reasons,'report':str(path.relative_to(root)) if path else None})
    criteria=read(docs/'native-generalization-criteria.json') or {}
    check('Failed exact-money repair replay',repair,criteria.get('repair'))
    if not criteria.get('repair'):
        results[-1]['passed']=False;results[-1]['reasons'].append('Original failed-task criteria missing')
    for name in RELEASE_CASES:
        reports=[(p,read(p)) for p in docs.glob('native-'+name+'-*.json')]
        reports=[(p,d) for p,d in reports if isinstance(d,dict) and d.get('case')==name]
        latest=max(reports,key=lambda pair:pair[1].get('started_at',''))[0] if reports else None
        expected=criteria.get('cases',{}).get(name)
        check(name,latest,expected)
        if not expected:
            results[-1]['passed']=False;results[-1]['reasons'].append('Predeclared criteria missing')
    declaration=docs/'native-money-extended-criteria.json'
    if declaration.exists():
        boundary=read(docs/'money-precision-boundary-validation.json')
        native=read(repair);reasons=[]
        if not isinstance(boundary,dict) or boundary.get('passed') is not True or boundary.get('status')!='complete':
            reasons.append('Additional declared boundary has not passed')
        else:
            if boundary.get('runtime_sha256')!=current:reasons.append('Boundary report does not match current runtime')
            if not isinstance(native,dict) or not native.get('job') or boundary.get('native_job')!=native['job']:reasons.append('Boundary report does not match latest native repair')
            if boundary.get('criteria_sha256')!=hashlib.sha256(declaration.read_bytes()).hexdigest():reasons.append('Boundary declaration changed')
            checks=boundary.get('checks',{})
            if any(checks.get(key) is not True for key in ('declared_before_native','native_complete','runtime_frozen','source_frozen','signed','total')):reasons.append('Boundary evidence missing or failed')
            if set(boundary.get('cases',{}))!={'signed','total'} or not all(c.get('passed') is True for c in boundary.get('cases',{}).values()):reasons.append('Both actual boundary CLI cases required')
        results.append({'task':'Additional declared exact-money boundary','passed':not reasons,'reasons':reasons,'report':'docs/money-precision-boundary-validation.json'})
    return {'passed':current is not None and all(r['passed'] for r in results),'checks':results,
            'current_runtime_sha256':current,
            'scope':'Three actual native outcomes: failed repair replay, fresh Python inventory, fresh Rust ranges. Historical arithmetic smoke and scripted regression passes cannot replace these.'}


if __name__=='__main__':
    result=release_checks(ROOT);print(json.dumps(result,indent=2))
    if not result['passed']:raise SystemExit(1)
