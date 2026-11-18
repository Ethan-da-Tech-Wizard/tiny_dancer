# ==============================================================================
# Program: sampling.py
# Programmer: Ethan-da-Tech-Wizard
# Last Modified: November 18, 2026
# Purpose: Defines temperature, top-p, min-p, repetition penalty, and nucleus sampling strategies for generation.
# ==============================================================================

# SPDX-License-Identifier: Apache-2.0
"""Explicit native profiles; preserve legacy greedy runs for comparisons."""


def native_temperature(config):
    profile = config.get('native_sampling_profile', 'greedy')
    if profile == 'greedy':
        return 0.0
    if profile == 'recommended':
        return 1.0
    raise ValueError('native_sampling_profile must be greedy or recommended')
