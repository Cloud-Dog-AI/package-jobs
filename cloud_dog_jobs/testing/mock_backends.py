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

# cloud_dog_jobs — Mock backends for tests
"""In-memory mock backend implementations for focused unit tests."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from cloud_dog_jobs.backends.base import QueueBackend
from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import Job


class MockQueueBackend(QueueBackend):
    """Represent mock queue backend."""
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def enqueue(self, job: Job) -> str:
        """Handle enqueue."""
        self._jobs[job.job_id] = job
        return job.job_id

    def dequeue(self, limit: int, job_type: str | None = None) -> list[Job]:
        """Handle dequeue."""
        jobs = [j for j in self._jobs.values() if j.status == JobStatus.QUEUED]
        if job_type:
            jobs = [j for j in jobs if j.job_type == job_type]
        jobs.sort(key=lambda j: (-j.priority, j.created_at))
        return jobs[:limit]

    def claim(self, job_id: str, host_id: str, worker_id: str) -> bool:
        """Handle claim."""
        job = self._jobs.get(job_id)
        if job is None or job.status != JobStatus.QUEUED:
            return False
        job.status = JobStatus.RUNNING
        job.claimed_by = f"{host_id}:{worker_id}"
        job.updated_at = datetime.now(tz=timezone.utc)
        return True

    def release(self, job_id: str) -> bool:
        """Handle release."""
        return self.update_status(job_id, JobStatus.QUEUED.value)

    def heartbeat(self, job_id: str) -> bool:
        """Handle heartbeat."""
        job = self._jobs.get(job_id)
        if job is None:
            return False
        job.updated_at = datetime.now(tz=timezone.utc)
        return True

    def get(self, job_id: str) -> Job | None:
        """Handle get."""
        return self._jobs.get(job_id)

    def update_status(self, job_id: str, status: str) -> bool:
        """Update status."""
        job = self._jobs.get(job_id)
        if job is None:
            return False
        job.status = JobStatus(status)
        job.updated_at = datetime.now(tz=timezone.utc)
        if job.status != JobStatus.RUNNING:
            job.claimed_by = None
        return True

    def get_queue_status(self) -> dict[str, int]:
        """Return queue status."""
        return dict(Counter(j.status.value for j in self._jobs.values()))

    def health_check(self) -> bool:
        """Handle health check."""
        return True

    def all_jobs(self) -> list[Job]:
        """Handle all jobs."""
        return list(self._jobs.values())
