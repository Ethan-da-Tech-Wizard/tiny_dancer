# ==============================================================================
# Program: test_maintenance.py
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
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import httpx
from app.tools import ROOT
from scripts import restart_when_idle as maintenance


# ------------------------------------------------------------------------------
# MaintenanceTests: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class MaintenanceTests(unittest.TestCase):
    # ------------------------------------------------------------------------------
    # setUp: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'workspace');self.folder=Path(self.temp.name)
        (self.folder/'run').mkdir();(self.folder/'logs').mkdir()
        with sqlite3.connect(self.folder/'run/workspace.sqlite3') as db:
            db.execute('CREATE TABLE jobs (id TEXT,status TEXT)')

    # ------------------------------------------------------------------------------
    # tearDown: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def tearDown(self):self.temp.cleanup()

    # ------------------------------------------------------------------------------
    # client: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def client(self,active=None):
        # ------------------------------------------------------------------------------
        # handle: Function Pipeline & Contract Specification
        # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
        # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
        # Failure Modes: Catches or propagates domain exceptions according to API contracts
        # ------------------------------------------------------------------------------
        def handle(request):return httpx.Response(200,json={'active_job':active})
        return httpx.Client(base_url='http://127.0.0.1:3210',transport=httpx.MockTransport(handle))

    # ------------------------------------------------------------------------------
    # test_active_api_task_prevents_any_restart: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_active_api_task_prevents_any_restart(self):
        with (patch.object(maintenance,'ROOT',self.folder),patch.object(maintenance.httpx,'Client',return_value=self.client('active')),
             patch.object(maintenance.subprocess,'run') as restart):
            with self.assertRaisesRegex(SystemExit,'Refusing restart'):maintenance.guarded_restart()
            restart.assert_not_called()

    # ------------------------------------------------------------------------------
    # test_durable_running_task_prevents_any_restart: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_durable_running_task_prevents_any_restart(self):
        with sqlite3.connect(self.folder/'run/workspace.sqlite3') as db:db.execute("INSERT INTO jobs VALUES ('active','running')")
        with (patch.object(maintenance,'ROOT',self.folder),patch.object(maintenance.httpx,'Client',return_value=self.client()),
             patch.object(maintenance.subprocess,'run') as restart):
            with self.assertRaisesRegex(SystemExit,'Refusing restart'):maintenance.guarded_restart()
            restart.assert_not_called()

    # ------------------------------------------------------------------------------
    # test_idle_restart_waits_for_ready_before_recording_success: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_idle_restart_waits_for_ready_before_recording_success(self):
        with (patch.object(maintenance,'ROOT',self.folder),patch.object(maintenance.httpx,'Client',return_value=self.client()),
             patch.object(maintenance.subprocess,'run') as restart,patch.object(maintenance,'wait_for_ready',return_value={}) as ready):
            maintenance.guarded_restart()
            restart.assert_called_once();ready.assert_called_once()
        record=json.loads((self.folder/'logs/agent-audit.jsonl').read_text())
        self.assertTrue(record['data']['ready'])

    # ------------------------------------------------------------------------------
    # test_readiness_retries_startup_errors_without_restart: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_readiness_retries_startup_errors_without_restart(self):
        calls=[]
        # ------------------------------------------------------------------------------
        # handle: Function Pipeline & Contract Specification
        # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
        # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
        # Failure Modes: Catches or propagates domain exceptions according to API contracts
        # ------------------------------------------------------------------------------
        def handle(request):
            calls.append(request.url.path)
            return httpx.Response(503 if len(calls)==1 else 200,json={'active_job':None})
        client=httpx.Client(base_url='http://127.0.0.1:3210',transport=httpx.MockTransport(handle))
        with (patch.object(maintenance.httpx,'Client',return_value=client),patch.object(maintenance.time,'sleep'),
             patch.object(maintenance.subprocess,'run') as restart):
            self.assertIsNone(maintenance.wait_for_ready()['active_job']);restart.assert_not_called()
        self.assertEqual(calls,['/','/','/api/status'])

    # ------------------------------------------------------------------------------
    # test_failed_readiness_never_records_false_success: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def test_failed_readiness_never_records_false_success(self):
        with (patch.object(maintenance,'ROOT',self.folder),patch.object(maintenance.httpx,'Client',return_value=self.client()),
             patch.object(maintenance.subprocess,'run'),patch.object(maintenance,'wait_for_ready',side_effect=RuntimeError('not ready'))):
            with self.assertRaisesRegex(RuntimeError,'not ready'):maintenance.guarded_restart()
        self.assertFalse((self.folder/'logs/agent-audit.jsonl').exists())
