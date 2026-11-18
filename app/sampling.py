# Program: tiny_dancer - sampling.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Explicit native profiles; preserve legacy greedy runs for comparisons.
# SPDX-License-Identifier: Apache-2.0
"""Explicit native profiles; preserve legacy greedy runs for comparisons."""


# ---- Definitions ----
def native_temperature(config):
    """Step: native temperature. Inputs: config."""
    profile = config.get('native_sampling_profile', 'greedy')
    if profile == 'greedy':
        return 0.0
    if profile == 'recommended':
        return 1.0
    raise ValueError('native_sampling_profile must be greedy or recommended')
