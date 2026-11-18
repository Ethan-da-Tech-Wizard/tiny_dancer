# Program: tiny_dancer - tests/test_maintenance.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Tests for maintenance (exercises app.tools).
# SPDX-License-Identifier: Apache-2.0
"""Tests for maintenance (exercises app.tools)."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import httpx
from app.tools import ROOT
from scripts import restart_when_idle as maintenance


# -------- maintenance tests --------
class MaintenanceTests(unittest.TestCase):
    """Test group for maintenance."""
    def setUp(self):
        """Prepare the fixtures for each test."""
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'workspace');self.folder=Path(self.temp.name)
        (self.folder/'run').mkdir();(self.folder/'logs').mkdir()
        with sqlite3.connect(self.folder/'run/workspace.sqlite3') as db:
            db.execute('CREATE TABLE jobs (id TEXT,status TEXT)')

    # Clean up the fixtures after each test.
    def tearDown(self):self.temp.cleanup()

    def client(self,active=None):
        # Test helper: handle.
        """Test helper: client."""
        def handle(request):return httpx.Response(200,json={'active_job':active})
        return httpx.Client(base_url='http://127.0.0.1:3210',transport=httpx.MockTransport(handle))

    def test_active_api_task_prevents_any_restart(self):
        """Checks that active api task prevents any restart."""
        with (patch.object(maintenance,'ROOT',self.folder),patch.object(maintenance.httpx,'Client',return_value=self.client('active')),
             patch.object(maintenance.subprocess,'run') as restart):
            with self.assertRaisesRegex(SystemExit,'Refusing restart'):maintenance.guarded_restart()
            restart.assert_not_called()

    def test_durable_running_task_prevents_any_restart(self):
        """Checks that durable running task prevents any restart."""
        with sqlite3.connect(self.folder/'run/workspace.sqlite3') as db:db.execute("INSERT INTO jobs VALUES ('active','running')")
        with (patch.object(maintenance,'ROOT',self.folder),patch.object(maintenance.httpx,'Client',return_value=self.client()),
             patch.object(maintenance.subprocess,'run') as restart):
            with self.assertRaisesRegex(SystemExit,'Refusing restart'):maintenance.guarded_restart()
            restart.assert_not_called()

    def test_idle_restart_waits_for_ready_before_recording_success(self):
        """Checks that idle restart waits for ready before recording success."""
        with (patch.object(maintenance,'ROOT',self.folder),patch.object(maintenance.httpx,'Client',return_value=self.client()),
             patch.object(maintenance.subprocess,'run') as restart,patch.object(maintenance,'wait_for_ready',return_value={}) as ready):
            maintenance.guarded_restart()
            restart.assert_called_once();ready.assert_called_once()
        record=json.loads((self.folder/'logs/agent-audit.jsonl').read_text())
        self.assertTrue(record['data']['ready'])

    def test_readiness_retries_startup_errors_without_restart(self):
        """Checks that readiness retries startup errors without restart."""
        calls=[]
        def handle(request):
            """Test helper: handle."""
            calls.append(request.url.path)
            return httpx.Response(503 if len(calls)==1 else 200,json={'active_job':None})
        client=httpx.Client(base_url='http://127.0.0.1:3210',transport=httpx.MockTransport(handle))
        with (patch.object(maintenance.httpx,'Client',return_value=client),patch.object(maintenance.time,'sleep'),
             patch.object(maintenance.subprocess,'run') as restart):
            self.assertIsNone(maintenance.wait_for_ready()['active_job']);restart.assert_not_called()
        self.assertEqual(calls,['/','/','/api/status'])

    def test_failed_readiness_never_records_false_success(self):
        """Checks that failed readiness never records false success."""
        with (patch.object(maintenance,'ROOT',self.folder),patch.object(maintenance.httpx,'Client',return_value=self.client()),
             patch.object(maintenance.subprocess,'run'),patch.object(maintenance,'wait_for_ready',side_effect=RuntimeError('not ready'))):
            with self.assertRaisesRegex(RuntimeError,'not ready'):maintenance.guarded_restart()
        self.assertFalse((self.folder/'logs/agent-audit.jsonl').exists())
