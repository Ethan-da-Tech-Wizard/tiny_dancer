# Program: tiny_dancer - tool_arguments.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Decode native arguments with one unambiguous structural correction.
# SPDX-License-Identifier: Apache-2.0
"""Decode native arguments with one unambiguous structural correction."""
# ---- Imports ----
import json


# ---- Definitions ----
def unique_object(pairs):
    """Step: unique object. Inputs: pairs."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate fields prevent argument repair')
        result[key] = value
    return result


def parse_tool_arguments(text):
    """Step: parse tool arguments. Inputs: text."""
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
