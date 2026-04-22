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

# cloud_dog_jobs — Concurrency controls
"""Simple in-process concurrency manager."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ConcurrencyLimits:
    """Concurrency limit definitions."""

    global_max: int = 10
    per_type_max: int = 5
    per_tenant_max: int = 3
    per_user_max: int = 2


class ConcurrencyManager:
    """Track active slots and enforce per-dimension limits."""

    def __init__(self, limits: ConcurrencyLimits) -> None:
        self._limits = limits
        self._global = 0
        self._by_type: dict[str, int] = {}
        self._by_tenant: dict[str, int] = {}
        self._by_user: dict[str, int] = {}

    def can_acquire(self, job_type: str, tenant_id: str = "default", user_id: str = "default") -> bool:
        """Return whether a slot can be acquired."""
        return (
            self._global < self._limits.global_max
            and self._by_type.get(job_type, 0) < self._limits.per_type_max
            and self._by_tenant.get(tenant_id, 0) < self._limits.per_tenant_max
            and self._by_user.get(user_id, 0) < self._limits.per_user_max
        )

    def acquire(self, job_type: str, tenant_id: str = "default", user_id: str = "default") -> bool:
        """Acquire a slot if limits allow."""
        if not self.can_acquire(job_type, tenant_id, user_id):
            return False
        self._global += 1
        self._by_type[job_type] = self._by_type.get(job_type, 0) + 1
        self._by_tenant[tenant_id] = self._by_tenant.get(tenant_id, 0) + 1
        self._by_user[user_id] = self._by_user.get(user_id, 0) + 1
        return True

    def release(self, job_type: str, tenant_id: str = "default", user_id: str = "default") -> None:
        """Release a previously acquired slot."""
        self._global = max(0, self._global - 1)
        self._by_type[job_type] = max(0, self._by_type.get(job_type, 0) - 1)
        self._by_tenant[tenant_id] = max(0, self._by_tenant.get(tenant_id, 0) - 1)
        self._by_user[user_id] = max(0, self._by_user.get(user_id, 0) - 1)
