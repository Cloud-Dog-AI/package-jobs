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

# cloud_dog_jobs — Hybrid backend
"""Hybrid backend using Redis queue operations with SQL source-of-truth state."""

from __future__ import annotations

from cloud_dog_jobs.backends.base import QueueBackend
from cloud_dog_jobs.backends.redis_backend import RedisQueueBackend
from cloud_dog_jobs.backends.sql_backend import SQLQueueBackend
from cloud_dog_jobs.domain.models import Job


class HybridQueueBackend(QueueBackend):
    """Redis for dispatch operations, SQL for durable state."""

    def __init__(self, redis_backend: RedisQueueBackend, sql_backend: SQLQueueBackend) -> None:
        self._redis = redis_backend
        self._sql = sql_backend

    def enqueue(self, job: Job) -> str:
        """Handle enqueue."""
        self._sql.enqueue(job)
        return self._redis.enqueue(job)

    def dequeue(self, limit: int, job_type: str | None = None) -> list[Job]:
        """Handle dequeue."""
        return self._redis.dequeue(limit, job_type)

    def claim(self, job_id: str, host_id: str, worker_id: str) -> bool:
        """Handle claim."""
        if not self._redis.claim(job_id, host_id, worker_id):
            return False
        self._sql.claim(job_id, host_id, worker_id)
        return True

    def release(self, job_id: str) -> bool:
        """Handle release."""
        self._sql.release(job_id)
        return self._redis.release(job_id)

    def heartbeat(self, job_id: str) -> bool:
        """Handle heartbeat."""
        self._sql.heartbeat(job_id)
        return self._redis.heartbeat(job_id)

    def get(self, job_id: str) -> Job | None:
        """Handle get."""
        return self._sql.get(job_id)

    def update_status(self, job_id: str, status: str) -> bool:
        """Update status."""
        self._redis.update_status(job_id, status)
        return self._sql.update_status(job_id, status)

    def get_queue_status(self) -> dict[str, int]:
        """Return queue status."""
        return self._sql.get_queue_status()

    def health_check(self) -> bool:
        """Handle health check."""
        return self._sql.health_check() and self._redis.health_check()

    def all_jobs(self) -> list[Job]:
        """Return all jobs from durable SQL source-of-truth."""
        return self._sql.all_jobs()
