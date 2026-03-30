# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# cloud_dog_jobs — Retry and scheduling policies
"""Retry, backoff, and fairness helpers."""

from __future__ import annotations

import random


def exponential_backoff_seconds(attempt: int, base: float = 2.0, maximum: float = 300.0, jitter: bool = True) -> float:
    """Calculate exponential backoff with optional jitter."""
    backoff = min(base * (2 ** max(attempt, 0)), maximum)
    if jitter:
        backoff += random.uniform(0.0, backoff * 0.1)
    return backoff


def fixed_backoff_seconds(value: float) -> float:
    """Return fixed backoff interval."""
    return max(0.0, value)
