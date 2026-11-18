# Program: tiny_dancer - tests/test_coding_acceptance.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Tests for coding acceptance (exercises app.tools, scripts.coding_acceptance).
# SPDX-License-Identifier: Apache-2.0
"""Tests for coding acceptance (exercises app.tools, scripts.coding_acceptance)."""
import tempfile
import unittest
from pathlib import Path

from app.tools import ROOT
from scripts.coding_acceptance import coding_checks


# -------- independent coding acceptance tests --------
class IndependentCodingAcceptanceTests(unittest.TestCase):
    """Test group for independent coding acceptance."""
    def setUp(self):
        """Prepare the fixtures for each test."""
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'workspace');self.folder=Path(self.temp.name)
    # Clean up the fixtures after each test.
    def tearDown(self):self.temp.cleanup()
    def test_default_decimal_precision_bug_is_caught_by_unseen_large_amount(self):
        """Checks that default decimal precision bug is caught by unseen large amount."""
        source='''import csv,json,sys
from decimal import Decimal
totals={}
try:
 for row in csv.DictReader(open(sys.argv[1])):
  amount=Decimal(row['amount'])
  if not amount.is_finite() or amount.as_tuple().exponent < -2:raise ValueError('invalid amount')
  category=row['category'];totals[category]=totals.get(category,Decimal(0))+amount
 print(json.dumps({key:format(value,'.2f') for key,value in sorted(totals.items())}))
except Exception:
 print('invalid amount',file=sys.stderr);sys.exit(1)
'''
        (self.folder/'summarize.py').write_text(source)
        checks,friendly=coding_checks(self.folder,ROOT)
        self.assertTrue(all(check['passed'] for check in checks if 'default Decimal' not in check['check']))
        self.assertFalse(next(check['passed'] for check in checks if 'default Decimal' in check['check']))
        self.assertTrue(all(check['passed'] for check in friendly))
    def test_exact_integer_cents_cli_passes_all_acceptance_cases(self):
        """Checks that exact integer cents cli passes all acceptance cases."""
        source='''import csv,json,re,sys
totals={}
try:
 for row in csv.DictReader(open(sys.argv[1])):
  match=re.fullmatch(r'([+-]?)([0-9]+)(?:\\.([0-9]{1,2}))?',row['amount'])
  if not match:raise ValueError('invalid amount')
  sign,whole,fraction=match.groups();cents=int(whole)*100+int((fraction or '').ljust(2,'0'))
  if sign=='-':cents=-cents
  category=row['category'];totals[category]=totals.get(category,0)+cents
 print(json.dumps({key:('-' if value<0 else '')+str(abs(value)//100)+'.'+str(abs(value)%100).zfill(2) for key,value in sorted(totals.items())}))
except Exception:
 print('invalid amount',file=sys.stderr);sys.exit(1)
'''
        (self.folder/'summarize.py').write_text(source)
        checks,friendly=coding_checks(self.folder,ROOT)
        self.assertEqual(len(checks),11);self.assertEqual(len(friendly),5)
        self.assertTrue(all(check['passed'] for check in checks+friendly),checks+friendly)
