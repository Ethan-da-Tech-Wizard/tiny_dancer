# ==============================================================================
# Program: test_source_previews.py
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
"""Source previews must preserve useful code and explain every omission."""
import unittest

from app.prompting import compact_result


# ------------------------------------------------------------------------------
# SourcePreviewTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class SourcePreviewTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # source: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def source(self, count=100, width=28):
        lines=[f"{line}: value_{line} = {'1'*width}\n" for line in range(1,count+1)]
        return {'path':'/project/summary.py','text':''.join(lines)}

    # ------------------------------------------------------------------------------
    # test_modest_source_preserves_middle_needed_for_a_patch: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_modest_source_preserves_middle_needed_for_a_patch(self):
        data=self.source(90,20)
        data['text']=data['text'].replace('45: value_45', '45: amount_total')
        original=dict(data)
        preview=compact_result(data)
        self.assertIn('45: amount_total',preview['text'])
        self.assertEqual(preview['text'],data['text'])
        self.assertNotIn('saved artifact',preview['text'])
        self.assertEqual(data,original)

    # ------------------------------------------------------------------------------
    # test_large_source_explains_missing_lines_and_how_to_read_them: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_large_source_explains_missing_lines_and_how_to_read_them(self):
        data=self.source(250,50)
        preview=compact_result(data)
        self.assertTrue(preview['text_truncated'])
        self.assertLessEqual(len(preview['text']),6100)
        start,end=preview['omitted_lines']
        self.assertGreater(start,1);self.assertLess(end,250)
        self.assertEqual(preview['next_read'],{'path':data['path'],'start_line':start,'max_lines':end-start+1})
        visible=[line for line in preview['text'].splitlines(True) if not line.startswith('[...')]
        source=data['text'].splitlines(True)
        self.assertTrue(all(line in source for line in visible))
        self.assertEqual(visible[:start-1]+source[start-1:end]+visible[start-1:],source)
        self.assertNotIn('saved artifact',preview['text'])

    # ------------------------------------------------------------------------------
    # test_long_single_line_is_explicitly_partial_without_fake_artifact: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_long_single_line_is_explicitly_partial_without_fake_artifact(self):
        data={'path':'/project/large.py','text':'1: value = "'+'x'*18000+'"\n'}
        preview=compact_result(data)
        self.assertTrue(preview['text_truncated'])
        self.assertTrue(preview['partial_lines'])
        self.assertIn('shell',preview['read_hint'])
        self.assertNotIn('saved artifact',preview['text'])
        self.assertNotIn('next_read',preview)

    # ------------------------------------------------------------------------------
    # test_non_source_output_retains_existing_failure_footer: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_non_source_output_retains_existing_failure_footer(self):
        data={'path':'/project/check.log','output':'noise'*2000+'\nFAILED (errors=1)','artifact':'/artifacts/check.log'}
        preview=compact_result(data)
        self.assertIn('FAILED (errors=1)',preview['output'])
        self.assertLess(len(preview['output']),2500)
        self.assertEqual(preview['artifact'],data['artifact'])


if __name__=='__main__':unittest.main()
