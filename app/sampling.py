# SPDX-License-Identifier: Apache-2.0
"""Explicit native profiles; preserve legacy greedy runs for comparisons."""


def native_temperature(config):
    profile = config.get('native_sampling_profile', 'greedy')
    if profile == 'greedy':
        return 0.0
    if profile == 'recommended':
        return 1.0
    raise ValueError('native_sampling_profile must be greedy or recommended')
