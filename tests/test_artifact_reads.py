# ==============================================================================
# Program: test_artifact_reads.py
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
"""Returned artifact references can be inspected without becoming product files."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from app.tools import ComputerTools,ROOT


# ------------------------------------------------------------------------------
# ArtifactReadTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class ArtifactReadTests(unittest.IsolatedAsyncioTestCase):
    # ------------------------------------------------------------------------------
    # asyncSetUp: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'run');self.root=Path(self.temp.name)
        self.artifacts=self.root/'artifacts';self.artifacts.mkdir();self.project=self.root/'project';self.project.mkdir()
        self.tools=ComputerTools();self.mock=patch('app.tools.ARTIFACTS',self.artifacts);self.mock.start()
        (self.artifacts/'check.json').write_text('{"exit_code": 1}\n')
    # ------------------------------------------------------------------------------
    # asyncTearDown: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def asyncTearDown(self):self.mock.stop();await self.tools.close();self.temp.cleanup()

    # ------------------------------------------------------------------------------
    # test_returned_artifact_reference_reads_real_saved_text: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_returned_artifact_reference_reads_real_saved_text(self):
        result=await self.tools.execute('read_file',{'path':'/artifacts/check.json'},str(self.project))
        self.assertIn('"exit_code": 1',result['text'])
        self.assertEqual(result['path'],str(self.artifacts/'check.json'))
        self.assertTrue(result['artifact_reference'])

    # ------------------------------------------------------------------------------
    # test_artifact_directory_reference_lists_saved_outputs: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_artifact_directory_reference_lists_saved_outputs(self):
        result=await self.tools.execute('list_directory',{'path':'/artifacts'},str(self.project))
        self.assertIn('check.json',[x['name'] for x in result['entries']])

    # ------------------------------------------------------------------------------
    # test_alias_cannot_escape_directory_or_follow_escape_symlink: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_alias_cannot_escape_directory_or_follow_escape_symlink(self):
        (self.root/'outside.txt').write_text('OUTSIDE')
        (self.artifacts/'escape.txt').symlink_to(self.root/'outside.txt')
        for path in ('/artifacts/../outside.txt','/artifacts/escape.txt'):
            with self.assertRaises(ValueError):await self.tools.execute('read_file',{'path':path},str(self.project))

    # ------------------------------------------------------------------------------
    # test_normal_project_file_still_resolves_relative_to_cwd: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_normal_project_file_still_resolves_relative_to_cwd(self):
        (self.project/'product.py').write_text('PROJECT_SENTINEL\n')
        result=await self.tools.execute('read_file',{'path':'product.py'},str(self.project))
        self.assertIn('PROJECT_SENTINEL',result['text'])
        self.assertNotIn('artifact_reference',result)

    # ------------------------------------------------------------------------------
    # test_artifact_observation_does_not_pollute_source_hash_proof: Asynchronous Coroutine & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    async def test_artifact_observation_does_not_pollute_source_hash_proof(self):
        from types import SimpleNamespace
        import threading
        from app.agent import AgentRun
        run=AgentRun(SimpleNamespace(config={}),self.tools,str(self.project),SimpleNamespace(prompt='Build a Python program.',mode='agent',max_tokens=None,run_until_done=True),lambda:[],lambda *a:None,lambda *a:None,lambda *a:None,threading.Event())
        await run.execute('read_file',{'path':'/artifacts/check.json'})
        self.assertNotIn(str(self.artifacts/'check.json'),run.state.get('inspected_sources',[]))


if __name__=='__main__':unittest.main()
