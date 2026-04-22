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
from cloud_dog_jobs.domain.models import Job
from cloud_dog_jobs.scheduler.concurrency import ConcurrencyManager


class Dispatcher:
    """Select eligible jobs from the backend."""

    def __init__(self, backend: QueueBackend, concurrency: ConcurrencyManager | None = None) -> None:
        self._backend = backend
        self._concurrency = concurrency

    def select_eligible(self, limit: int) -> list[Job]:
        """Return jobs ordered by backend policy and filtered by concurrency."""
        jobs = self._backend.dequeue(limit=limit)
        if self._concurrency is None:
            return jobs
        selected: list[Job] = []
        for job in jobs:
            if self._concurrency.acquire(job.job_type):
                selected.append(job)
        return selected
