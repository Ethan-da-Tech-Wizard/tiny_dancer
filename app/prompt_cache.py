# SPDX-License-Identifier: Apache-2.0
"""Reuse the model's exact emitted history when canonical messages still match."""


class ExactHistoryCache:
    def __init__(self):
        self.clear()

    def clear(self):
        self.canonical = []
        self.raw = []

    def remember(self, canonical, raw):
        self.canonical, self.raw = list(canonical), list(raw)

    def restore(self, canonical, capacity, reserve):
        boundary = len(self.canonical)
        if not boundary or canonical[:boundary] != self.canonical:
            return canonical, 0
        candidate = self.raw + canonical[boundary:]
        if len(candidate) + reserve >= capacity:
            return canonical, 0
        return candidate, len(self.raw)
