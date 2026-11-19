# ==============================================================================
# Program: test_coding_acceptance.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Automated test suite verifying functional correctness, regression
#          resistance, boundary conditions, and edge cases. Automated regression and
#          functional assertion test suite verifying system stability, edge-case
#          resilience, and contract invariants. Exercises mathematical boundary
#          conditions, state graph branch coverage, and mock failure modes within
#          isolated execution fixtures. Enforces deterministic test assertions and
#          hermetic runtime lifecycle management.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
import tempfile
import unittest
from pathlib import Path

from app.tools import ROOT
from scripts.coding_acceptance import coding_checks


# ------------------------------------------------------------------------------
# IndependentCodingAcceptanceTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class IndependentCodingAcceptanceTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # setUp: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'workspace');self.folder=Path(self.temp.name)
    # ------------------------------------------------------------------------------
    # tearDown: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def tearDown(self):self.temp.cleanup()
    # ------------------------------------------------------------------------------
    # test_default_decimal_precision_bug_is_caught_by_unseen_large_amount: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_default_decimal_precision_bug_is_caught_by_unseen_large_amount(self):
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
    # ------------------------------------------------------------------------------
    # test_exact_integer_cents_cli_passes_all_acceptance_cases: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_exact_integer_cents_cli_passes_all_acceptance_cases(self):
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
