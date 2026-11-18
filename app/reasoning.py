# Program: tiny_dancer - reasoning.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Resolve an explicit effort choice before the configurable automatic default.
# SPDX-License-Identifier: Apache-2.0
"""Resolve an explicit effort choice before the configurable automatic default."""
# ---- Definitions ----
def effective_effort(requested,contract,config,agent=True):
    """Step: effective effort. Inputs: requested, contract, config, agent."""
    if requested!='auto':
        if requested not in ('low','medium','high'):raise ValueError('Invalid reasoning effort')
        return requested
    if not agent or contract.get('kind')!='work':return 'low'
    configured=config.get('work_reasoning_effort')
    if configured is not None:
        if configured not in ('low','medium','high'):raise ValueError('Invalid work_reasoning_effort')
        return configured
    return 'medium' if contract.get('lookup_languages') else 'low'
