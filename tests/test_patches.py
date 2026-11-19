# ==============================================================================
# Program: test_patches.py
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
import os
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from app.patches import apply_patch
from app.task_policy import contract_for,tools_for
from app.tools import TOOLS


# ------------------------------------------------------------------------------
# PatchTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class PatchTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # setUp: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.work=self.root/'work';self.work.mkdir();self.backups=self.root/'backups'

    # ------------------------------------------------------------------------------
    # tearDown: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def tearDown(self): self.temp.cleanup()

    # ------------------------------------------------------------------------------
    # apply: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def apply(self,text): return apply_patch(text,self.work,self.backups)

    # ------------------------------------------------------------------------------
    # test_small_edit_add_and_real_program_verification: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_small_edit_add_and_real_program_verification(self):
        source=self.work/'calc.py';source.write_text('def add(a, b):\n    return a - b\n')
        result=self.apply('*** Begin Patch\n*** Update File: calc.py\n@@\n def add(a, b):\n-    return a - b\n+    return a + b\n*** Add File: verify.py\n+from calc import add\n+assert add(7, 2) == 9\n+assert add(-3, 2) == -1\n*** End Patch')
        completed=subprocess.run(['/usr/bin/python3','verify.py'],cwd=self.work,capture_output=True)
        self.assertEqual(completed.returncode,0,completed.stderr)
        self.assertTrue(result['applied'])
        self.assertEqual(Path(result['files'][0]['backup']).read_text(),'def add(a, b):\n    return a - b\n')

    # ------------------------------------------------------------------------------
    # test_later_context_error_prevents_every_file_mutation: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_later_context_error_prevents_every_file_mutation(self):
        source=self.work/'a.txt';source.write_text('original\n')
        other=self.work/'b.txt';other.write_text('actual\n')
        with self.assertRaisesRegex(ValueError,'context'):
            self.apply('*** Begin Patch\n*** Update File: a.txt\n@@\n-original\n+new\n*** Update File: b.txt\n@@\n-guessed\n+bad\n*** End Patch')
        self.assertEqual(source.read_text(),'original\n');self.assertEqual(other.read_text(),'actual\n')
        self.assertFalse(self.backups.exists())

    # ------------------------------------------------------------------------------
    # test_ambiguous_context_rejected_and_anchor_disambiguates: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_ambiguous_context_rejected_and_anchor_disambiguates(self):
        source=self.work/'a.txt';source.write_text('first\nrepeat\nsecond\nrepeat\n')
        with self.assertRaisesRegex(ValueError,'exactly once'):
            self.apply('*** Begin Patch\n*** Update File: a.txt\n@@\n-repeat\n+new\n*** End Patch')
        self.apply('*** Begin Patch\n*** Update File: a.txt\n@@ second\n-repeat\n+new\n*** End Patch')
        self.assertEqual(source.read_text(),'first\nrepeat\nsecond\nnew\n')

    # ------------------------------------------------------------------------------
    # test_permissions_and_crlf_preserved: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_permissions_and_crlf_preserved(self):
        source=self.work/'run.py';source.write_bytes(b'print(1)\r\n');os.chmod(source,0o750)
        self.apply('*** Begin Patch\n*** Update File: run.py\n@@\n-print(1)\n+print(2)\n*** End Patch')
        self.assertEqual(source.read_bytes(),b'print(2)\r\n')
        self.assertEqual(source.stat().st_mode & 0o777,0o750)

    # ------------------------------------------------------------------------------
    # test_escape_symlink_deletion_and_overwrite_are_rejected: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_escape_symlink_deletion_and_overwrite_are_rejected(self):
        outside=self.root/'outside.txt';outside.write_text('private\n')
        (self.work/'link.txt').symlink_to(outside)
        (self.work/'keep.txt').write_text('keep\n')
        requests=[
            '*** Update File: ../outside.txt\n@@\n-private\n+bad',
            '*** Update File: '+str(outside)+'\n@@\n-private\n+bad',
            '*** Update File: link.txt\n@@\n-private\n+bad',
            '*** Delete File: keep.txt',
            '*** Add File: keep.txt\n+bad',
        ]
        for section in requests:
            with self.subTest(section=section),self.assertRaises(ValueError):
                self.apply('*** Begin Patch\n'+section+'\n*** End Patch')
        self.assertEqual(outside.read_text(),'private\n');self.assertEqual((self.work/'keep.txt').read_text(),'keep\n')

    # ------------------------------------------------------------------------------
    # test_failed_write_rolls_back_previously_changed_file: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_failed_write_rolls_back_previously_changed_file(self):
        (self.work/'a.txt').write_text('original\n');(self.work/'b.txt').write_text('original\n')
        original_replace=Path.replace
        # ------------------------------------------------------------------------------
        # fail_second: Function Pipeline & Contract Specification
        # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
        # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
        # Failure Modes: Catches or propagates domain exceptions according to API contracts
        # ------------------------------------------------------------------------------
        def fail_second(path,target):
            if Path(target).name=='b.txt': raise OSError('simulated disk error')
            return original_replace(path,target)
        with patch.object(Path,'replace',fail_second),self.assertRaises(OSError):
            self.apply('*** Begin Patch\n*** Update File: a.txt\n@@\n-original\n+new\n*** Update File: b.txt\n@@\n-original\n+new\n*** End Patch')
        self.assertEqual((self.work/'a.txt').read_text(),'original\n');self.assertEqual((self.work/'b.txt').read_text(),'original\n')
        self.assertFalse(list(self.work.glob('.*.tmp')))

    # ------------------------------------------------------------------------------
    # test_noop_and_empty_update_are_rejected: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_noop_and_empty_update_are_rejected(self):
        (self.work/'a.txt').write_text('original\n')
        for body in ('','@@\n original'):
            with self.assertRaises(ValueError):
                self.apply('*** Begin Patch\n*** Update File: a.txt\n'+body+'\n*** End Patch')

    # ------------------------------------------------------------------------------
    # test_patch_schema_available_for_all_work_but_not_questions: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_patch_schema_available_for_all_work_but_not_questions(self):
        names=lambda goal:{t['name'] for t in tools_for(contract_for(goal),TOOLS)}
        self.assertIn('apply_patch',names('Fix this Python program'))
        self.assertIn('apply_patch',names('Fix this Rust program'))
        self.assertIn('apply_patch',names('Create a grocery list'))
        self.assertNotIn('apply_patch',names('What are the Python dependencies?'))


    # ------------------------------------------------------------------------------
    # test_plain_new_manifest_is_preserved_and_parseable: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_plain_new_manifest_is_preserved_and_parseable(self):
        content='[package]\nname = "ranges"\nversion = "0.1.0"\nedition = "2021"\n\n[dependencies]\n'
        result=self.apply('*** Begin Patch\n*** Add File: Cargo.toml\n'+content+'*** End Patch')
        self.assertTrue(result['applied'])
        self.assertEqual((self.work/'Cargo.toml').read_text(),content)
        self.assertEqual(tomllib.loads(content)['package']['edition'],'2021')

    # ------------------------------------------------------------------------------
    # test_mixed_new_file_format_names_exact_missing_prefix_line: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_mixed_new_file_format_names_exact_missing_prefix_line(self):
        request='*** Begin Patch\n*** Add File: Cargo.toml\n+[package]\n+name="ranges"\n+version="0.1.0"\nedition="2021"\n+\n+[dependencies]\n*** End Patch'
        with self.assertRaisesRegex(ValueError,'line 6'):self.apply(request)
        self.assertFalse((self.work/'Cargo.toml').exists())

    # ------------------------------------------------------------------------------
    # test_literal_new_file_keeps_indentation_and_real_execution: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(P) bounded by external process execution timeout and IPC throughput | Space: O(B) stream buffer memory allocated for child stdout/stderr capture
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_literal_new_file_keeps_indentation_and_real_execution(self):
        content='def answer():\n    return 42\n\nassert answer() == 42\n'
        self.apply('*** Begin Patch\n*** Add File: answer.py\n'+content+'*** End Patch')
        self.assertEqual((self.work/'answer.py').read_text(),content)
        result=subprocess.run(['/usr/bin/python3','answer.py'],cwd=self.work,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)

    # ------------------------------------------------------------------------------
    # test_literal_add_cannot_bypass_multifile_validation: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_literal_add_cannot_bypass_multifile_validation(self):
        with self.assertRaises(ValueError):
            self.apply('*** Begin Patch\n*** Add File: good.txt\nvalid\n*** Delete File: keep.txt\n*** End Patch')
        self.assertFalse((self.work/'good.txt').exists())

    # ------------------------------------------------------------------------------
    # test_absolute_inside_task_supports_add_update_and_backups: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_absolute_inside_task_supports_add_update_and_backups(self):
        target=self.work/'nested'/'value.txt'
        self.apply('*** Begin Patch\n*** Add File: '+str(target)+'\n+old value\n*** End Patch')
        result=self.apply('*** Begin Patch\n*** Update File: '+str(target)+'\n@@\n-old value\n+new value\n*** End Patch')
        self.assertEqual(target.read_text(),'new value\n')
        self.assertEqual(Path(result['files'][0]['backup']).read_text(),'old value\n')

    # ------------------------------------------------------------------------------
    # test_absolute_sibling_or_symlink_escape_rejects_every_section: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_absolute_sibling_or_symlink_escape_rejects_every_section(self):
        sibling=self.root/'work-sibling';sibling.mkdir()
        (self.work/'escape').symlink_to(sibling,target_is_directory=True)
        for outside in (sibling/'victim.txt',self.work/'escape'/'victim.txt'):
            with self.subTest(outside=outside),self.assertRaises(ValueError):
                self.apply('*** Begin Patch\n*** Add File: inside.txt\n+keep unwritten\n*** Add File: '+str(outside)+'\n+bad\n*** End Patch')
            self.assertFalse((self.work/'inside.txt').exists())
            self.assertFalse((sibling/'victim.txt').exists())

    # ------------------------------------------------------------------------------
    # test_mixed_absolute_and_relative_alias_cannot_edit_same_file_twice: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_mixed_absolute_and_relative_alias_cannot_edit_same_file_twice(self):
        with self.assertRaisesRegex(ValueError,'one section'):
            self.apply('*** Begin Patch\n*** Add File: value.txt\n+first\n*** Add File: '+str(self.work/'value.txt')+'\n+second\n*** End Patch')
        self.assertFalse((self.work/'value.txt').exists())

    # ------------------------------------------------------------------------------
    # test_workspace_symlink_alias_keeps_same_containment: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_workspace_symlink_alias_keeps_same_containment(self):
        alias=self.root/'work-alias';alias.symlink_to(self.work,target_is_directory=True)
        self.apply('*** Begin Patch\n*** Add File: '+str(alias/'value.txt')+'\n+same project\n*** End Patch')
        self.assertEqual((self.work/'value.txt').read_text(),'same project\n')
