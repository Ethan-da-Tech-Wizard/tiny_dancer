# Program: tiny_dancer - tests/raw_engine_fixture.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Provides a test helper that builds an engine forced to the raw tool protocol.
# SPDX-License-Identifier: Apache-2.0
"""Raw Harmony test doubles must select their protocol independently of live config."""
from app.engine import LocalEngine


def legacy_raw_engine():
    """Test helper: legacy raw engine."""
    engine=LocalEngine()
    engine.config['native_tool_protocol']='raw'
    engine.config.pop('work_reasoning_effort',None)
    return engine
