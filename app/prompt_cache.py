# Program: tiny_dancer - prompt_cache.py
# Programmer: Ethan-da-Tech-Wizard (written with Claude, an AI assistant)
# Last Modified: 2026-11-18
# Purpose: Reuse the model's exact emitted history when canonical messages still match.
# SPDX-License-Identifier: Apache-2.0
"""Reuse the model's exact emitted history when canonical messages still match."""


# ---- Definitions ----
class ExactHistoryCache:
    """Defines the exacthistorycache type."""
    def __init__(self):
        """Step: init."""
        self.clear()

    def clear(self):
        """Step: clear."""
        self.canonical = []
        self.raw = []

    def remember(self, canonical, raw):
        """Step: remember. Inputs: canonical, raw."""
        self.canonical, self.raw = list(canonical), list(raw)

    def restore(self, canonical, capacity, reserve):
        """Step: restore. Inputs: canonical, capacity, reserve."""
        boundary = len(self.canonical)
        if not boundary or canonical[:boundary] != self.canonical:
            return canonical, 0
        candidate = self.raw + canonical[boundary:]
        if len(candidate) + reserve >= capacity:
            return canonical, 0
        return candidate, len(self.raw)
