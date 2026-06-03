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

# cloud_dog_jobs — Idempotency manager
"""In-memory idempotency key deduplication."""

from __future__ import annotations

import time


class IdempotencyManager:
    """Track idempotency keys for a bounded TTL window."""

    def __init__(self, ttl_seconds: int = 86_400) -> None:
        self._ttl_seconds = ttl_seconds
        self._entries: dict[str, tuple[str, float]] = {}

    def register_or_get(self, key: str, job_id: str) -> str:
        """Return existing job_id if key exists and valid, otherwise store new entry."""
        now = time.time()
        existing = self._entries.get(key)
        if existing and existing[1] > now:
            return existing[0]
        self._entries[key] = (job_id, now + self._ttl_seconds)
        return job_id
