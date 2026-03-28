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

# cloud_dog_jobs — Queue backend interface
"""Backend contract used by queue and worker layers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from cloud_dog_jobs.domain.models import Job


class QueueBackend(ABC):
    """Abstract queue backend contract."""

    @abstractmethod
    def enqueue(self, job: Job) -> str:
        """Persist a job and return its identifier."""

    @abstractmethod
    def dequeue(self, limit: int, job_type: str | None = None) -> list[Job]:
        """Return queued jobs eligible for claiming."""

    @abstractmethod
    def claim(self, job_id: str, host_id: str, worker_id: str) -> bool:
        """Attempt to claim a queued job."""

    @abstractmethod
    def release(self, job_id: str) -> bool:
        """Release a claimed job back to queued state."""

    @abstractmethod
    def heartbeat(self, job_id: str) -> bool:
        """Update the heartbeat timestamp for a running job."""

    @abstractmethod
    def get(self, job_id: str) -> Job | None:
        """Return a single job by identifier."""

    @abstractmethod
    def update_status(self, job_id: str, status: str) -> bool:
        """Set job status."""

    @abstractmethod
    def get_queue_status(self) -> dict[str, int]:
        """Return counts grouped by status."""

    @abstractmethod
    def health_check(self) -> bool:
        """Check backend health."""

    @abstractmethod
    def all_jobs(self) -> list[Job]:
        """Return all known jobs for administrative maintenance operations."""
