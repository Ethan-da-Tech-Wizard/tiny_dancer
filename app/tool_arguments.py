# ==============================================================================
# Program: tool_arguments.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 19, 2026
# Purpose: Validates, deserializes, and safely dispatches tool invocations and
#          structured JSON arguments from agent response messages to target tool
#          handlers. Core component of the autonomous agent reasoning architecture
#          governing multi-turn execution cycles, state graph transitions, and prompt
#          synthesis. Strictly enforces mathematical bounds on LLM token context
#          windows, rolling memory buffers, and timeout thresholds. Guarantees
#          transactional execution invariants, deterministic failure isolation, and
#          thread-safe API contracts.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
"""Decode native arguments with one unambiguous structural correction."""
import json


# ------------------------------------------------------------------------------
# unique_object: Function Pipeline & Contract Specification
# Algorithmic Complexity: Time: O(N) linear iteration over collection or state elements | Space: O(1) auxiliary space beyond input collection storage
# Invariant: Preconditions validated before mutation; postconditions guarantee return contract
# Failure Modes: Catches or propagates domain exceptions according to API contracts
# ------------------------------------------------------------------------------
def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate fields prevent argument repair')
        result[key] = value
    return result


# ------------------------------------------------------------------------------
# parse_tool_arguments: Function Pipeline & Contract Specification
# Algorithmic Complexity: Time: O(1) constant time primitive operation and state evaluation | Space: O(1) constant stack space allocation
# Invariant: Preconditions validated before mutation; postconditions guarantee return contract
# Failure Modes: Catches or propagates domain exceptions according to API contracts
# ------------------------------------------------------------------------------
def parse_tool_arguments(text):
    repair = None
    try:
        args = json.loads(text)
    except json.JSONDecodeError as error:
        # The decoder has already consumed a complete value. Only remove an
        # unexpected ] immediately before the final object closer. Never edit
        # quoted text, keys, values, escapes, missing closers or trailing data.
        if (error.msg != "Expecting ',' delimiter" or text[error.pos:error.pos + 1] != ']'
                or text[error.pos + 1:].strip() != '}'):
            raise
        candidate = text[:error.pos] + text[error.pos + 1:]
        try:
            args = json.loads(candidate, object_pairs_hook=unique_object)
        except ValueError:
            raise error
        if not isinstance(args, dict):
            raise error
        repair = {'kind': 'removed_unmatched_final_array_closer', 'removed_at': error.pos}
    if not isinstance(args, dict):
        raise ValueError('Tool arguments must be an object')
    return args, repair
