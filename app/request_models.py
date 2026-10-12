# SPDX-License-Identifier: Apache-2.0
"""Pure API validation; importing it never starts services or modifies jobs."""
from pathlib import Path
from typing import Literal

from pydantic import BaseModel,Field,model_validator


class NewSession(BaseModel):
    title: str = 'New session'
    cwd: str = str(Path('/mnt/GameDrive/tiny_dancer/workspace'))


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
    def default_chat_to_bounded(cls,values):
        if isinstance(values,dict) and values.get('mode')=='chat' and 'run_until_done' not in values:
            return dict(values,run_until_done=False)
        return values


class ResumeTask(BaseModel):
    max_tokens: int | None = Field(default=None,ge=64,le=4096)
    compact_context: bool = True
    run_until_done: bool | None = None
    reasoning_effort: Literal['auto','low','medium','high'] | None = None


def apply_resume_options(data,options):
    if 'max_tokens' in options.model_fields_set: data.max_tokens=options.max_tokens
    if options.run_until_done is not None: data.run_until_done=options.run_until_done
    if options.reasoning_effort is not None: data.reasoning_effort=options.reasoning_effort
    return data
