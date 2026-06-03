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

# cloud_dog_jobs — Maintenance reaper
"""Stuck detection and retention helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cloud_dog_jobs.backends.base import QueueBackend
from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.ttl.expiry import is_ttl_expired
from cloud_dog_jobs.ttl.retention import should_purge


class MaintenanceReaper:
    """Run maintenance sweeps over queue data."""

    def __init__(self, backend: QueueBackend, claim_timeout_seconds: int = 60) -> None:
        self._backend = backend
        self._claim_timeout_seconds = claim_timeout_seconds

    def find_stuck_job_ids(self) -> list[str]:
        """Return running jobs older than claim timeout."""
        now = datetime.now(tz=timezone.utc)
        stuck: list[str] = []
        # Scan backend-visible jobs and flag stale running jobs.
        for job in self._backend.dequeue(limit=10_000):
            if job.status.value == "running" and (now - job.updated_at) > timedelta(
                seconds=self._claim_timeout_seconds
            ):
                stuck.append(job.job_id)
        return stuck

    def run_sweep(
        self,
        *,
        ttl_seconds: int = 86_400,
        retention_seconds: int = 86_400 * 30,
    ) -> dict[str, int]:
        """Run stuck/TTL/retention maintenance sweep and return summary counts."""
        now = datetime.now(tz=timezone.utc)
        summary = {"stuck_recovered": 0, "ttl_expired": 0, "retention_purged": 0}
        for job in self._backend.all_jobs():
            if (
                job.status.value == JobStatus.RUNNING.value
                and (now - job.updated_at).total_seconds() > self._claim_timeout_seconds
            ):
                if self._backend.update_status(job.job_id, JobStatus.FAILED.value):
                    summary["stuck_recovered"] += 1
                continue

            if job.status.value in {JobStatus.QUEUED.value, JobStatus.RUNNING.value} and is_ttl_expired(
                job.created_at, ttl_seconds=ttl_seconds, now=now
            ):
                if self._backend.update_status(job.job_id, JobStatus.TTL_EXPIRED.value):
                    summary["ttl_expired"] += 1
                continue

            if should_purge(job.updated_at, max_age_seconds=retention_seconds, now=now):
                # Baseline backend does not hard-delete; mark as cancelled for safe retention purge semantics.
                if self._backend.update_status(job.job_id, JobStatus.CANCELLED.value):
                    summary["retention_purged"] += 1
        return summary
