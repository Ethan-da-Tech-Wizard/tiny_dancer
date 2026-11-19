# ==============================================================================
# tests/test_root_override.py - TINY_DANCER_ROOT environment override
#
# Pins down: the install root is no longer hard-coded. With TINY_DANCER_ROOT set,
# app.tool_runtime.ROOT follows it (imported in a fresh interpreter, because ROOT is
# computed at import time); without it the original /mnt/GameDrive/tiny_dancer default
# still applies. A source scan also asserts that engine.py, tools.py, tool_runtime.py and
# request_models.py read the variable and keep the old path only as the default, so a
# module whose imports are unavailable on this machine (fastapi, pydantic) is still covered.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OLD = '/mnt/GameDrive/tiny_dancer'


def root_in_fresh_interpreter(env_value):
    """Import app.tool_runtime in a child process and print its ROOT."""
    env = {k: v for k, v in os.environ.items() if k != 'TINY_DANCER_ROOT'}
    if env_value is not None:
        env['TINY_DANCER_ROOT'] = env_value
    out = subprocess.run([sys.executable, '-c', 'from app.tool_runtime import ROOT; print(ROOT)'],
                         cwd=REPO, env=env, capture_output=True, text=True, check=True)
    return out.stdout.strip()


class RootOverrideTests(unittest.TestCase):
    # Scenario: env var set -> ROOT follows it.
    def test_env_var_overrides_root(self):
        self.assertEqual(root_in_fresh_interpreter('/tmp/td-root-test'), '/tmp/td-root-test')

    # Scenario: nothing set -> historical default (existing deployments must not change behaviour).
    def test_default_is_old_path(self):
        self.assertEqual(root_in_fresh_interpreter(None), OLD)

    # Scenario: every module that defines the root reads the variable and uses the old path only as its default.
    def test_sources_read_env_var(self):
        for name in ('engine.py', 'tools.py', 'tool_runtime.py', 'request_models.py'):
            text = (REPO / 'app' / name).read_text()
            self.assertIn("TINY_DANCER_ROOT", text, name)
            for line in text.splitlines():
                if OLD in line and not line.lstrip().startswith('#'):
                    self.assertIn('TINY_DANCER_ROOT', line, name + ': hard-coded path outside the env default: ' + line)


if __name__ == '__main__':
    unittest.main()
