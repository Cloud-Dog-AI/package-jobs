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

# cloud_dog_jobs — Queue facade
"""High-level queue API used by services and workers."""

from __future__ import annotations

import asyncio

from cloud_dog_jobs.backends.base import QueueBackend
from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import Job, JobRequest
from cloud_dog_jobs.idempotency.manager import IdempotencyManager
from cloud_dog_jobs.observability.audit import AuditEmitter
from cloud_dog_jobs.security.secrets import assert_no_secrets
from cloud_dog_jobs.security.validation import validate_payload_size


class JobQueue:
    """Facade over the configured backend."""

    def __init__(
        self,
        backend: QueueBackend,
        *,
        payload_max_bytes: int = 16_384,
        idempotency_manager: IdempotencyManager | None = None,
        audit_emitter: AuditEmitter | None = None,
    ) -> None:
        self._backend = backend
        self._payload_max_bytes = payload_max_bytes
        self._idempotency = idempotency_manager or IdempotencyManager()
        self._audit = audit_emitter or AuditEmitter()

    def submit(self, request: JobRequest) -> str:
        """Submit a new job and return job_id."""
        validate_payload_size(request.payload, max_bytes=self._payload_max_bytes)
        assert_no_secrets(request.payload)
        job = Job.from_request(request)
        if request.idempotency_key:
            prior = self._idempotency.register_or_get(request.idempotency_key, job.job_id)
            if prior != job.job_id:
                self._audit.emit("job.submit", "deduplicated")
                return prior
        job_id = self._backend.enqueue(job)
        self._audit.emit("job.submit", "success")
        return job_id

    async def submit_async(self, request: JobRequest) -> str:
        """Async variant of submit."""
        return await asyncio.to_thread(self.submit, request)

    def get(self, job_id: str) -> Job | None:
        """Get a job by identifier."""
        return self._backend.get(job_id)

    async def get_async(self, job_id: str) -> Job | None:
        """Async variant of get."""
        return await asyncio.to_thread(self.get, job_id)

    def list(self, limit: int = 50, job_type: str | None = None) -> list[Job]:
        """List queued jobs in dispatch order."""
        return self._backend.dequeue(limit=limit, job_type=job_type)

    async def list_async(self, limit: int = 50, job_type: str | None = None) -> list[Job]:
        """Async variant of list."""
        return await asyncio.to_thread(self.list, limit, job_type)

    def cancel(self, job_id: str) -> bool:
        """Cancel an existing job."""
        ok = self._backend.update_status(job_id, JobStatus.CANCELLED.value)
        self._audit.emit("job.cancel", "success" if ok else "failure")
        return ok

    async def cancel_async(self, job_id: str) -> bool:
        """Async variant of cancel."""
        return await asyncio.to_thread(self.cancel, job_id)

    def health(self) -> bool:
        """Check backend health."""
        return self._backend.health_check()

    async def health_async(self) -> bool:
        """Async variant of health."""
        return await asyncio.to_thread(self.health)
