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

# cloud_dog_jobs — Admin bulk operations
"""Bulk filter + action operations for administrative workflows."""

from __future__ import annotations

from collections.abc import Callable

from cloud_dog_jobs.backends.base import QueueBackend
from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import Job


class BulkAdminOperations:
    """Represent bulk admin operations."""
    def __init__(self, backend: QueueBackend, permission_checker: Callable[[str], bool] | None = None) -> None:
        self._backend = backend
        self._permission_checker = permission_checker

    def _require(self, permission: str) -> None:
        if self._permission_checker and not self._permission_checker(permission):
            raise PermissionError(f"Missing required permission: {permission}")

    def filter_jobs(
        self, *, status: str | None = None, queue_name: str | None = None, job_type: str | None = None
    ) -> list[Job]:
        """Handle filter jobs."""
        jobs = self._backend.all_jobs()
        out: list[Job] = []
        for job in jobs:
            if status and job.status.value != status:
                continue
            if queue_name and job.queue_name != queue_name:
                continue
            if job_type and job.job_type != job_type:
                continue
            out.append(job)
        return out

    def apply(
        self,
        action: str,
        *,
        status: str | None = None,
        queue_name: str | None = None,
        job_type: str | None = None,
        job_ids: set[str] | None = None,
    ) -> int:
        """Handle apply."""
        self._require("jobs.bulk")
        targets = self.filter_jobs(status=status, queue_name=queue_name, job_type=job_type)
        count = 0
        for job in targets:
            if job_ids is not None and job.job_id not in job_ids:
                continue
            if action == "cancel":
                if self._backend.update_status(job.job_id, JobStatus.CANCELLED.value):
                    count += 1
            elif action == "retry":
                if self._backend.update_status(job.job_id, JobStatus.QUEUED.value):
                    count += 1
            elif action == "fail":
                if self._backend.update_status(job.job_id, JobStatus.FAILED.value):
                    count += 1
            else:
                raise ValueError(f"Unsupported bulk action: {action}")
        return count
