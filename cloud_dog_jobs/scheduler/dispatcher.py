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

# cloud_dog_jobs — Job dispatcher
"""Dispatcher to select jobs by priority and limits."""

from __future__ import annotations

from cloud_dog_jobs.backends.base import QueueBackend
from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import Job
from cloud_dog_jobs.scheduler.concurrency import ConcurrencyManager
from cloud_dog_jobs.scheduler.dependency import DependencyTracker
from cloud_dog_jobs.scheduler.resource_pool import ResourcePool


class Dispatcher:
    """Select eligible jobs from the backend, respecting dependencies, concurrency and resource limits.

    Selection order (PS-95 §6.3): dependencies satisfied → resources available → priority + age.
    """

    def __init__(
        self,
        backend: QueueBackend,
        concurrency: ConcurrencyManager | None = None,
        resource_pool: ResourcePool | None = None,
        dependency_tracker: DependencyTracker | None = None,
    ) -> None:
        self._backend = backend
        self._concurrency = concurrency
        self._resource_pool = resource_pool
        self._dependency_tracker = dependency_tracker

    def _get_job_status(self, job_id: str) -> JobStatus | None:
        """Look up a job's status via the backend."""
        job = self._backend.get(job_id)
        return job.status if job is not None else None

    def select_eligible(self, limit: int, queue_name: str | None = None) -> list[Job]:
        """Return jobs ordered by backend policy and filtered by deps + concurrency + resources."""
        jobs = self._backend.dequeue(limit=limit, queue_name=queue_name)
        selected: list[Job] = []
        for job in jobs:
            # --- Dependency check (PS-95 §6.3, W28D-305) ---
            if self._dependency_tracker is not None and job.depends_on:
                if not self._dependency_tracker.is_runnable(job.job_id, self._get_job_status):
                    continue
            if self._concurrency is not None and not self._concurrency.acquire(job.job_type):
                continue
            if self._resource_pool is not None and job.resources:
                if not self._resource_pool.acquire(job.job_id, job.resources):
                    if self._concurrency is not None:
                        self._concurrency.release(job.job_type)
                    continue
            selected.append(job)
        return selected

    def release_job(self, job: Job) -> None:
        """Release concurrency and resource slots when a job finishes."""
        if self._concurrency is not None:
            self._concurrency.release(job.job_type)
        if self._resource_pool is not None:
            self._resource_pool.release(job.job_id)
