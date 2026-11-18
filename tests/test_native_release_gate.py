# Program: tiny_dancer - tests/test_native_release_gate.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Tests for native release gate (exercises scripts.check_native_release, scripts.evaluate_hardening_suite, scripts.inventory_extended_audit).
# SPDX-License-Identifier: Apache-2.0
"""Tests for native release gate (exercises scripts.check_native_release, scripts.evaluate_hardening_suite, scripts.inventory_extended_audit)."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.check_native_release import release_checks
from scripts.evaluate_hardening_suite import runtime_digest
from scripts.inventory_goal_audit import CRITERIA as INVENTORY_GOAL_CRITERIA
from scripts.inventory_extended_audit import CRITERIA as SPECIAL_FILE_CRITERIA
ALL_INVENTORY_CRITERIA=INVENTORY_GOAL_CRITERIA+SPECIAL_FILE_CRITERIA
from unittest.mock import patch


# -------- native release gate tests --------
class NativeReleaseGateTests(unittest.TestCase):
    """Test group for native release gate."""
    def setUp(self):
        """Prepare the fixtures for each test."""
        root=Path(__file__).resolve().parents[1]
        self.temp=tempfile.TemporaryDirectory(dir=root/'run');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.docs=self.root/'docs';self.docs.mkdir()
        (self.root/'app/static').mkdir(parents=True)
        (self.root/'app/main.py').write_text('value = 1\n')
        (self.root/'config.json').write_text('{}\n')
        with patch('scripts.evaluate_hardening_suite.ROOT',self.root):
            self.runtime_sha256=runtime_digest()
        self.criteria={'cases':{name:{'prompt':'frozen '+name,'acceptance_sha256':'seed-'+name} for name in ('inventory','ranges')}}
        self.criteria['repair']={'prompt':'frozen repair','acceptance_sha256':'seed-repair'}
        self.write('native-generalization-criteria.json',self.criteria)

    def write(self,name,data):
        """Test helper: write."""
        (self.docs/name).write_text(json.dumps(data))

    def passed(self,case='repair',at='2026-10-11T00:00:00+00:00'):
        """Test helper: passed."""
        data={'started_at':at,'status':'complete','passed':True,'operator_interventions':[],'checks':{'native_verified':True,'independent':True,'runtime_frozen':True},'checkpoint':{'verified':True},'tool_calls':[{'name':'run_checks'}],'runtime_sha256_before':self.runtime_sha256}
        if case:data.update(case=case,prompt='frozen '+case,acceptance_sha256='seed-'+case,independent_checks=[{'passed':True}])
        if case=='inventory':
            data['additional_independent_criteria']=list(ALL_INVENTORY_CRITERIA)
            data['additional_goal_checks']=[{'check':name,'passed':True} for name in ALL_INVENTORY_CRITERIA]
        return data

    def seed_passes(self):
        """Test helper: seed passes."""
        self.write('precision-repair-retest-validation.json',self.passed())
        for case in ('inventory','ranges'):self.write('native-'+case+'-old.json',self.passed(case))

    def test_missing_reports_reject_release(self):
        """Checks that missing reports reject release."""
        result=release_checks(self.root);self.assertFalse(result['passed']);self.assertEqual(len(result['checks']),3)

    def test_original_narrow_inventory_pass_cannot_hide_missing_broader_checks(self):
        """Checks that original narrow inventory pass cannot hide missing broader checks."""
        self.seed_passes();data=self.passed('inventory')
        data.pop('additional_independent_criteria');data.pop('additional_goal_checks')
        self.write('native-inventory-old.json',data)
        self.assertFalse(release_checks(self.root)['passed'])

    def test_inventory_top_level_pass_cannot_hide_a_failed_goal_audit(self):
        """Checks that inventory top level pass cannot hide a failed goal audit."""
        self.seed_passes();data=self.passed('inventory');data['additional_goal_checks'][0]['passed']=False
        self.write('native-inventory-old.json',data)
        self.assertFalse(release_checks(self.root)['passed'])

    def test_inventory_missing_special_file_evidence_cannot_release(self):
        """Checks that inventory missing special file evidence cannot release."""
        self.seed_passes();data=self.passed('inventory')
        data['additional_independent_criteria']=list(INVENTORY_GOAL_CRITERIA)
        data['additional_goal_checks']=data['additional_goal_checks'][:-1]
        self.write('native-inventory-old.json',data)
        self.assertFalse(release_checks(self.root)['passed'])

    def test_inventory_special_file_failure_cannot_hide_behind_top_level_pass(self):
        """Checks that inventory special file failure cannot hide behind top level pass."""
        self.seed_passes();data=self.passed('inventory')
        data['additional_goal_checks'][-1]['passed']=False
        self.write('native-inventory-old.json',data)
        self.assertFalse(release_checks(self.root)['passed'])

    def test_all_distinct_verified_native_reports_required(self):
        """Checks that all distinct verified native reports required."""
        self.seed_passes();self.assertTrue(release_checks(self.root)['passed'])
        (self.docs/'native-ranges-old.json').unlink();self.assertFalse(release_checks(self.root)['passed'])

    def test_newer_failure_cannot_be_hidden_by_older_pass(self):
        """Checks that newer failure cannot be hidden by older pass."""
        self.seed_passes();data=self.passed('inventory','2026-10-11T01:00:00+00:00');data.update(status='paused',passed=False)
        self.write('native-inventory-new.json',data);result=release_checks(self.root)
        self.assertFalse(result['passed']);self.assertEqual(result['checks'][1]['report'],'docs/native-inventory-new.json')

    def test_changed_goal_or_tests_reject_release(self):
        """Checks that changed goal or tests reject release."""
        self.seed_passes();data=self.passed('ranges');data['prompt']='different';data['acceptance_sha256']='modified'
        self.write('native-ranges-old.json',data);reasons=release_checks(self.root)['checks'][2]['reasons']
        self.assertIn('Frozen goal changed',reasons);self.assertIn('Frozen acceptance changed',reasons)

    def test_top_level_pass_cannot_hide_failed_checks_or_runtime_hints(self):
        """Checks that top level pass cannot hide failed checks or runtime hints."""
        self.seed_passes();data=self.passed();data['checks']['independent']=False;data['operator_interventions']=['live hint']
        self.write('precision-repair-retest-validation.json',data);self.assertFalse(release_checks(self.root)['passed'])

    def test_regressions_and_arithmetic_smoke_cannot_replace_actual_runs(self):
        """Checks that regressions and arithmetic smoke cannot replace actual runs."""
        self.write('final-native-repair-validation.json',self.passed())
        self.write('regressions.json',{'passed':True,'tests':200})
        self.assertFalse(release_checks(self.root)['passed'])

    def test_reports_from_different_runtime_cannot_be_combined(self):
        """Checks that reports from different runtime cannot be combined."""
        self.seed_passes();data=self.passed('ranges');data['runtime_sha256_before']='a'*64
        self.write('native-ranges-old.json',data)
        result=release_checks(self.root)
        self.assertFalse(result['passed'])
        self.assertIn('Report does not match the current runtime',result['checks'][2]['reasons'])

    def test_source_or_config_change_invalidates_old_passes(self):
        """Checks that source or config change invalidates old passes."""
        self.seed_passes()
        for path in ('app/main.py','app/static/index.html','config.json'):
            with self.subTest(path=path):
                p=self.root/path;before=p.read_bytes() if p.exists() else None
                p.write_text('changed\n')
                self.assertFalse(release_checks(self.root)['passed'])
                if before is None:p.unlink()
                else:p.write_bytes(before)
        self.assertTrue(release_checks(self.root)['passed'])

    def test_missing_fingerprint_or_frozen_witness_rejects_release(self):
        """Checks that missing fingerprint or frozen witness rejects release."""
        for key in ('runtime_sha256_before','runtime_frozen'):
            with self.subTest(key=key):
                self.seed_passes();data=self.passed()
                if key=='runtime_frozen':data['checks'].pop(key)
                else:data.pop(key)
                self.write('precision-repair-retest-validation.json',data)
                self.assertFalse(release_checks(self.root)['passed'])

    def test_changed_after_fingerprint_rejects_release(self):
        """Checks that changed after fingerprint rejects release."""
        self.seed_passes();data=self.passed();data['runtime_sha256_after']='b'*64
        self.write('precision-repair-retest-validation.json',data)
        self.assertFalse(release_checks(self.root)['passed'])

    def test_malformed_latest_report_rejects_without_crashing(self):
        """Checks that malformed latest report rejects without crashing."""
        self.seed_passes();self.write('precision-repair-retest-validation.json',[])
        self.assertFalse(release_checks(self.root)['passed'])

    def test_unavailable_current_runtime_rejects_release(self):
        """Checks that unavailable current runtime rejects release."""
        self.seed_passes();(self.root/'config.json').unlink()
        self.assertFalse(release_checks(self.root)['passed'])

    def boundary(self):
        """Test helper: boundary."""
        import hashlib
        self.seed_passes();native=self.passed();native['job']='fixture-job';self.write('precision-repair-retest-validation.json',native)
        self.write('native-money-extended-criteria.json',{'width':12000,'declared_at':'2026-10-10T23:00:00+00:00'})
        return {'status':'complete','passed':True,'runtime_sha256':self.runtime_sha256,'native_job':'fixture-job',
            'criteria_sha256':hashlib.sha256((self.docs/'native-money-extended-criteria.json').read_bytes()).hexdigest(),
            'checks':{k:True for k in ('declared_before_native','native_complete','runtime_frozen','source_frozen','signed','total')},
            'cases':{'signed':{'passed':True},'total':{'passed':True}}}

    def test_declared_boundary_is_required_and_matching_evidence_can_pass(self):
        """Checks that declared boundary is required and matching evidence can pass."""
        report=self.boundary();self.assertFalse(release_checks(self.root)['passed'])
        self.write('money-precision-boundary-validation.json',report)
        self.assertTrue(release_checks(self.root)['passed'])

    def test_boundary_cannot_borrow_another_job_runtime_or_declaration(self):
        """Checks that boundary cannot borrow another job runtime or declaration."""
        for key,value in (('runtime_sha256','wrong'),('native_job','different'),('criteria_sha256','changed')):
            with self.subTest(key=key):
                report=self.boundary();report[key]=value;self.write('money-precision-boundary-validation.json',report)
                self.assertFalse(release_checks(self.root)['passed'])

    def test_boundary_top_level_pass_cannot_hide_missing_or_failed_actual_cases(self):
        """Checks that boundary top level pass cannot hide missing or failed actual cases."""
        for missing in (True,False):
            report=self.boundary()
            if missing:report['cases'].pop('signed')
            else:report['cases']['signed']['passed']=False
            self.write('money-precision-boundary-validation.json',report)
            self.assertFalse(release_checks(self.root)['passed'])

    def test_boundary_source_changes_or_late_declaration_cannot_pass(self):
        """Checks that boundary source changes or late declaration cannot pass."""
        for key in ('source_frozen','declared_before_native'):
            report=self.boundary();report['checks'][key]=False;self.write('money-precision-boundary-validation.json',report)
            self.assertFalse(release_checks(self.root)['passed'])


if __name__=='__main__':unittest.main()
