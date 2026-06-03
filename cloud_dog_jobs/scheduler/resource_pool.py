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

# cloud_dog_jobs — Resource pool tracker (PS-95 §6.1, W28D-304)
"""In-process resource pool for enforcing per-resource concurrency limits."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ResourcePoolConfig:
    """Configuration for resource pool limits.

    ``limits`` maps pool name → max concurrent slots.
    Example: ``{"llm-pool": 2}`` means at most 2 concurrent jobs
    holding an ``llm-pool`` resource.
    """

    limits: dict[str, int] = field(default_factory=dict)


class ResourcePool:
    """Track and enforce resource slot allocation across running jobs.

    Thread-safe via a reentrant lock. Each job may request multiple
    named resources with a slot count (e.g. ``{"llm-pool": 1}``).
    The pool blocks acquisition when the configured limit for any
    requested resource would be exceeded.
    """

    def __init__(self, config: ResourcePoolConfig | None = None) -> None:
        self._config = config or ResourcePoolConfig()
        self._lock = threading.RLock()
        self._used: dict[str, int] = {}
        self._holders: dict[str, dict[str, int]] = {}  # job_id → {pool: slots}

    @property
    def limits(self) -> dict[str, int]:
        return dict(self._config.limits)

    def utilisation(self) -> dict[str, dict[str, int]]:
        """Return per-pool {used, max, available} snapshot."""
        with self._lock:
            result: dict[str, dict[str, int]] = {}
            for pool, limit in self._config.limits.items():
                used = self._used.get(pool, 0)
                result[pool] = {"used": used, "max": limit, "available": limit - used}
            return result

    def blocked_count(self) -> int:
        """Return count of pools at capacity (no slots available)."""
        with self._lock:
            count = 0
            for pool, limit in self._config.limits.items():
                if self._used.get(pool, 0) >= limit:
                    count += 1
            return count

    def can_acquire(self, resources: dict[str, int]) -> bool:
        """Return whether all requested resource slots are available."""
        if not resources:
            return True
        with self._lock:
            for pool, requested in resources.items():
                limit = self._config.limits.get(pool)
                if limit is None:
                    continue  # no limit configured for this pool
                used = self._used.get(pool, 0)
                if used + requested > limit:
                    return False
            return True

    def acquire(self, job_id: str, resources: dict[str, int]) -> bool:
        """Acquire resource slots for a job. Returns False if limits exceeded."""
        if not resources:
            return True
        with self._lock:
            if not self.can_acquire(resources):
                return False
            for pool, requested in resources.items():
                self._used[pool] = self._used.get(pool, 0) + requested
            self._holders[job_id] = dict(resources)
            return True

    def release(self, job_id: str) -> None:
        """Release all resource slots held by a job."""
        with self._lock:
            held = self._holders.pop(job_id, {})
            for pool, slots in held.items():
                self._used[pool] = max(0, self._used.get(pool, 0) - slots)

    def held_by(self, job_id: str) -> dict[str, int]:
        """Return the resources currently held by a specific job."""
        with self._lock:
            return dict(self._holders.get(job_id, {}))
