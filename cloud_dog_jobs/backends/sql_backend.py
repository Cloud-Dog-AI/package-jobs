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

# cloud_dog_jobs — SQL backend implementation
"""SQLAlchemy backend supporting SQLite, MySQL, and PostgreSQL."""

from __future__ import annotations

from cloud_dog_jobs.backends.base import QueueBackend
from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import Job
from cloud_dog_jobs.storage.sqlalchemy.repo import SQLAlchemyJobRepository


class SQLQueueBackend(QueueBackend):
    """SQL queue backend with atomic claim semantics."""

    def __init__(self, database_url: str) -> None:
        self._repo = SQLAlchemyJobRepository(database_url)

    def enqueue(self, job: Job) -> str:
        """Handle enqueue."""
        return self._repo.enqueue(job)

    def dequeue(self, limit: int, job_type: str | None = None) -> list[Job]:
        """Handle dequeue."""
        return self._repo.queued(limit=limit, job_type=job_type)

    def claim(self, job_id: str, host_id: str, worker_id: str) -> bool:
        """Handle claim."""
        return self._repo.set_claimed(job_id, host_id=host_id, worker_id=worker_id)

    def release(self, job_id: str) -> bool:
        """Handle release."""
        return self.update_status(job_id, JobStatus.QUEUED.value)

    def heartbeat(self, job_id: str) -> bool:
        """Handle heartbeat."""
        return self._repo.heartbeat(job_id)

    def get(self, job_id: str) -> Job | None:
        """Handle get."""
        return self._repo.get(job_id)

    def update_status(self, job_id: str, status: str) -> bool:
        """Update status."""
        return self._repo.set_status(job_id, status)

    def get_queue_status(self) -> dict[str, int]:
        """Return queue status."""
        return self._repo.queue_status()

    def health_check(self) -> bool:
        """Handle health check."""
        return self._repo.health_check()

    def all_jobs(self) -> list[Job]:
        """Return all jobs for admin and maintenance use cases."""
        return self._repo.all_jobs()

    def close(self) -> None:
        """Dispose engine connections, used by integration tests and shutdown hooks."""
        self._repo.close()
