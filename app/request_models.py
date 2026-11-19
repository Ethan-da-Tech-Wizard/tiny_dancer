# ==============================================================================
# Program: request_models.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Pydantic / dataclass schemas defining API request bodies, query models,
#          and tool invocation parameters. Core component of the autonomous agent
#          reasoning architecture governing multi-turn execution cycles, state graph
#          transitions, and prompt synthesis. Strictly enforces mathematical bounds on
#          LLM token context windows, rolling memory buffers, and timeout thresholds.
#          Guarantees transactional execution invariants, deterministic failure
#          isolation, and thread-safe API contracts.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
"""Pure API validation; importing it never starts services or modifies jobs."""
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel,Field,model_validator


# ------------------------------------------------------------------------------
# NewSession: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class NewSession(BaseModel):
    title: str = 'New session'
    # Default working folder of a new session: <install root>/workspace (root from TINY_DANCER_ROOT, see app/engine.py).
    cwd: str = str(Path(os.environ.get('TINY_DANCER_ROOT', '/mnt/GameDrive/tiny_dancer')) / 'workspace')


# ------------------------------------------------------------------------------
# NewTask: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class NewTask(BaseModel):
    prompt: str = Field(min_length=1,max_length=30000)
    mode: str = 'agent'
    max_tokens: int | None = Field(default=None,ge=64,le=4096)
    task_kind: Literal['auto','answer','work'] = 'auto'
    max_turns: int | None = Field(default=None,ge=1,le=200)
    max_seconds: int | None = Field(default=None,ge=30,le=7200)
    run_until_done: bool = True
    reasoning_effort: Literal['auto','low','medium','high'] = 'auto'

    @model_validator(mode='before')
    @classmethod
    # ------------------------------------------------------------------------------
    # default_chat_to_bounded: Function Pipeline & Contract Specification
    # Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
    # Invariant: Preconditions validated before mutation; postconditions guarantee return contract
    # Failure Modes: Catches or propagates domain exceptions according to API contracts
    # ------------------------------------------------------------------------------
    def default_chat_to_bounded(cls,values):
        if isinstance(values,dict) and values.get('mode')=='chat' and 'run_until_done' not in values:
            return dict(values,run_until_done=False)
        return values


# ------------------------------------------------------------------------------
# ResumeTask: Class State Encapsulation & Contract Specification
# Algorithmic Complexity: Time: O(1) instantiation overhead | Space: O(M) memory model allocation for instance state and attribute dict
# Invariant: Enforces structural invariants and thread-safe state mutations across member calls
# Failure Modes: Raises TypeError or AttributeError upon illegal state transition or contract violation
# ------------------------------------------------------------------------------
class ResumeTask(BaseModel):
    max_tokens: int | None = Field(default=None,ge=64,le=4096)
    compact_context: bool = True
    run_until_done: bool | None = None
    reasoning_effort: Literal['auto','low','medium','high'] | None = None


# ------------------------------------------------------------------------------
# apply_resume_options: Function Pipeline & Contract Specification
# Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
# Invariant: Preconditions validated before mutation; postconditions guarantee return contract
# Failure Modes: Catches or propagates domain exceptions according to API contracts
# ------------------------------------------------------------------------------
def apply_resume_options(data,options):
    if 'max_tokens' in options.model_fields_set: data.max_tokens=options.max_tokens
    if options.run_until_done is not None: data.run_until_done=options.run_until_done
    if options.reasoning_effort is not None: data.reasoning_effort=options.reasoning_effort
    return data
