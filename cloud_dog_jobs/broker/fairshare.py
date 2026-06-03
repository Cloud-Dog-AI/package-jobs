# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# Licensed under the Apache License, Version 2.0

"""Tenant fair-share scheduler — prevents any single tenant from starving others."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TenantQuota:
    """Per-tenant resource quota and usage tracking."""

    tenant_id: str
    max_concurrent: int = 10
    max_per_minute: int = 60
    weight: float = 1.0  # relative share weight

    # Runtime counters (not config)
    active_count: int = field(default=0, repr=False)
    _minute_window_start: float = field(default_factory=time.monotonic, repr=False)
    _minute_count: int = field(default=0, repr=False)

    def can_submit(self) -> bool:
        """Check if tenant can submit another job."""
        if self.active_count >= self.max_concurrent:
            return False
        now = time.monotonic()
        if now - self._minute_window_start >= 60.0:
            self._minute_window_start = now
            self._minute_count = 0
        return self._minute_count < self.max_per_minute

    def record_submit(self) -> None:
        self.active_count += 1
        self._minute_count += 1

    def record_complete(self) -> None:
        self.active_count = max(0, self.active_count - 1)


class FairShareScheduler:
    """Tenant-aware fair-share scheduler.

    Ensures no single tenant monopolises the job queue by enforcing
    per-tenant concurrency limits and rate limits.
    """

    def __init__(self, default_max_concurrent: int = 10, default_max_per_minute: int = 60) -> None:
        self._tenants: dict[str, TenantQuota] = {}
        self._lock = threading.Lock()
        self._default_max_concurrent = default_max_concurrent
        self._default_max_per_minute = default_max_per_minute

    def register_tenant(self, quota: TenantQuota) -> None:
        """Register or update a tenant's quota."""
        with self._lock:
            self._tenants[quota.tenant_id] = quota

    def get_quota(self, tenant_id: str) -> TenantQuota:
        """Get or create default quota for a tenant."""
        with self._lock:
            if tenant_id not in self._tenants:
                self._tenants[tenant_id] = TenantQuota(
                    tenant_id=tenant_id,
                    max_concurrent=self._default_max_concurrent,
                    max_per_minute=self._default_max_per_minute,
                )
            return self._tenants[tenant_id]

    def can_submit(self, tenant_id: str) -> bool:
        """Check if a tenant can submit another job."""
        return self.get_quota(tenant_id).can_submit()

    def record_submit(self, tenant_id: str) -> None:
        """Record a job submission for a tenant."""
        self.get_quota(tenant_id).record_submit()

    def record_complete(self, tenant_id: str) -> None:
        """Record a job completion for a tenant."""
        self.get_quota(tenant_id).record_complete()

    def next_eligible_tenant(self, candidates: list[str]) -> str | None:
        """Pick the next tenant that should get a slot, weighted by fair share.

        Returns the candidate with the lowest (active_count / weight) ratio.
        """
        with self._lock:
            best: str | None = None
            best_ratio = float("inf")
            for tid in candidates:
                q = self._tenants.get(tid)
                if q is None:
                    return tid  # new tenant always gets priority
                if not q.can_submit():
                    continue
                ratio = q.active_count / max(q.weight, 0.01)
                if ratio < best_ratio:
                    best_ratio = ratio
                    best = tid
            return best

    def stats(self) -> dict[str, dict[str, Any]]:
        """Return per-tenant usage stats."""
        with self._lock:
            return {
                tid: {
                    "active": q.active_count,
                    "max_concurrent": q.max_concurrent,
                    "weight": q.weight,
                }
                for tid, q in self._tenants.items()
            }
