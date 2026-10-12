# SPDX-License-Identifier: Apache-2.0
"""Raw Harmony test doubles must select their protocol independently of live config."""
from app.engine import LocalEngine


def legacy_raw_engine():
    engine=LocalEngine()
    engine.config['native_tool_protocol']='raw'
    engine.config.pop('work_reasoning_effort',None)
    return engine
