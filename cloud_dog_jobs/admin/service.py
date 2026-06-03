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

# cloud_dog_jobs — Admin service
"""Administrative CRUD and control operations."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Callable

from cloud_dog_jobs.admin.bulk import BulkAdminOperations
from cloud_dog_jobs.backends.base import QueueBackend
from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import Job, JobRequest
from cloud_dog_jobs.observability.audit import AuditEmitter


class AdminService:
    """Administrative operations over the queue backend."""

    def __init__(self, backend: QueueBackend, permission_checker: Callable[[str], bool] | None = None) -> None:
        self._backend = backend
        self._audit = AuditEmitter()
        self._permission_checker = permission_checker
        self._bulk = BulkAdminOperations(backend, permission_checker=permission_checker)

    def _require(self, permission: str) -> None:
        """Require permission when a permission checker is configured."""
        if self._permission_checker is None:
            return
        if not self._permission_checker(permission):
            raise PermissionError(f"Missing required permission: {permission}")

    def submit_job(self, request: JobRequest) -> str:
        """Submit job via admin interface."""
        self._require("jobs.submit")
        return self._backend.enqueue(Job.from_request(request))

    def get_job(self, job_id: str) -> Job | None:
        """Get job by ID."""
        return self._backend.get(job_id)

    def list_jobs(self, limit: int = 100) -> list[Job]:
        """List queued jobs."""
        return self._backend.dequeue(limit)

    def update_job(self, job_id: str, *, priority: int | None = None) -> bool:
        """Minimal update operation, currently supports priority update for queued jobs."""
        self._require("jobs.update")
        job = self._backend.get(job_id)
        if job is None:
            return False
        if priority is not None:
            job.priority = priority
            self._backend.release(job_id)
        return True

    def delete_job(self, job_id: str) -> bool:
        """Soft-delete by marking cancelled."""
        self._require("jobs.delete")
        return self._backend.update_status(job_id, JobStatus.CANCELLED.value)

    def cancel_job(self, job_id: str) -> bool:
        """Cancel job."""
        self._require("jobs.cancel")
        ok = self._backend.update_status(job_id, JobStatus.CANCELLED.value)
        self._audit.emit("job.cancel", "success" if ok else "failure")
        return ok

    def reschedule_job(self, job_id: str, _next_run_at: datetime) -> bool:
        """Reschedule by returning to queued state."""
        self._require("jobs.reschedule")
        return self._backend.update_status(job_id, JobStatus.QUEUED.value)

    def retry_now(self, job_id: str) -> bool:
        """Retry immediately by transitioning to queued state."""
        self._require("jobs.retry")
        ok = self._backend.update_status(job_id, JobStatus.QUEUED.value)
        self._audit.emit("job.resubmit", "success" if ok else "failure")
        return ok

    def resubmit_job(self, job_id: str) -> str | None:
        """Clone and resubmit a job."""
        self._require("jobs.resubmit")
        job = self._backend.get(job_id)
        if job is None:
            return None
        clone = Job.from_request(
            JobRequest(
                job_type=job.job_type,
                queue_name=job.queue_name,
                payload=job.payload,
                priority=job.priority,
                idempotency_key=None,
                correlation_id=job.correlation_id,
                app_id=job.app_id,
                tenant_id=job.tenant_id,
                user_id=job.user_id,
                session_id=job.session_id,
                channel_id=job.channel_id,
            )
        )
        return self._backend.enqueue(clone)

    def clear_old_jobs(self, _policy: dict | None = None) -> int:
        """Clear jobs older than configured age by marking them cancelled."""
        self._require("jobs.purge")
        policy = _policy or {"max_age_seconds": 86_400}
        max_age = int(policy.get("max_age_seconds", 86_400))
        now = datetime.now(timezone.utc)
        count = 0
        for job in self._backend.all_jobs():
            age_seconds = (now - job.updated_at).total_seconds()
            if age_seconds > max_age and job.status.value not in {"succeeded", "failed", "cancelled"}:
                if self._backend.update_status(job.job_id, JobStatus.CANCELLED.value):
                    count += 1
        if count:
            self._audit.emit("job.admin.purge", "success")
        return count

    def clear_stuck_jobs(self, _filter: dict | None = None, _action: str = "cancel") -> int:
        """Clear jobs stuck in running state beyond timeout threshold."""
        self._require("jobs.stuck_recovery")
        options = _filter or {"claim_timeout_seconds": 60}
        timeout = int(options.get("claim_timeout_seconds", 60))
        now = datetime.now(timezone.utc)
        count = 0
        for job in self._backend.all_jobs():
            if job.status.value != JobStatus.RUNNING.value:
                continue
            age_seconds = (now - job.updated_at).total_seconds()
            if age_seconds <= timeout:
                continue
            target = JobStatus.CANCELLED.value if _action == "cancel" else JobStatus.FAILED.value
            if self._backend.update_status(job.job_id, target):
                count += 1
        if count:
            self._audit.emit("job.admin.stuck_recovery", "success")
        return count

    def reassign_queue(self, job_id: str, queue_name: str) -> bool:
        """Reassign queue by re-submitting a cloned job into a target queue."""
        self._require("jobs.reassign")
        job = self._backend.get(job_id)
        if job is None:
            return False
        clone_id = self._backend.enqueue(
            Job.from_request(
                JobRequest(
                    job_type=job.job_type,
                    queue_name=queue_name,
                    payload=job.payload,
                    priority=job.priority,
                    correlation_id=job.correlation_id,
                    app_id=job.app_id,
                    tenant_id=job.tenant_id,
                    user_id=job.user_id,
                    session_id=job.session_id,
                    channel_id=job.channel_id,
                )
            )
        )
        return bool(clone_id)

    def bulk_update(self, job_ids: list[str], action: str) -> int:
        """Bulk update over job IDs."""
        self._require("jobs.bulk")
        return self._bulk.apply(action, job_ids=set(job_ids))

    def queue_status(self) -> dict[str, int]:
        """Return queue status counts."""
        return self._backend.get_queue_status()

    async def get_job_async(self, job_id: str) -> Job | None:
        """Async variant of get_job."""
        return await asyncio.to_thread(self.get_job, job_id)

    async def list_jobs_async(self, limit: int = 100) -> list[Job]:
        """Async variant of list_jobs."""
        return await asyncio.to_thread(self.list_jobs, limit)

    async def cancel_job_async(self, job_id: str) -> bool:
        """Async variant of cancel_job."""
        return await asyncio.to_thread(self.cancel_job, job_id)
