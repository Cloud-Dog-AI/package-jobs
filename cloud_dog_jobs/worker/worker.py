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

# cloud_dog_jobs — Worker engine
"""Worker run loop and handler dispatch."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
import time
from typing import Callable

from cloud_dog_jobs.backends.base import QueueBackend
from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.extensions.fallback_policies import FallbackPolicyManager
from cloud_dog_jobs.observability.audit import AuditEmitter
from cloud_dog_jobs.observability.metrics import Metrics
from cloud_dog_jobs.worker.context import JobContext
from cloud_dog_jobs.worker.handlers import HandlerRegistry, JobHandler


class Worker:
    """Execute claimed jobs using registered handlers."""

    def __init__(
        self,
        backend: QueueBackend,
        host_id: str = "localhost",
        worker_id: str = "worker-1",
        *,
        run_timeout_seconds: float | None = None,
        identity_authoriser: Callable[[str, str], bool] | None = None,
        fallback_policies: FallbackPolicyManager | None = None,
    ) -> None:
        self._backend = backend
        self._host_id = host_id
        self._worker_id = worker_id
        self._registry = HandlerRegistry()
        self._stopped = False
        self._audit = AuditEmitter()
        self._metrics = Metrics()
        self._run_timeout_seconds = run_timeout_seconds
        self._identity_authoriser = identity_authoriser
        self._fallback_policies = fallback_policies

    def register_handler(self, job_type: str, handler: JobHandler) -> None:
        """Register job handler."""
        self._registry.register(job_type, handler)

    def run_once(self) -> bool:
        """Run one eligible job and return whether a job was processed."""
        if self._identity_authoriser is not None and not self._identity_authoriser(self._host_id, self._worker_id):
            raise PermissionError(f"Worker identity not authorised: {self._host_id}:{self._worker_id}")

        jobs = self._backend.dequeue(limit=1)
        if not jobs:
            return False
        job = jobs[0]
        if not self._backend.claim(job.job_id, self._host_id, self._worker_id):
            return False
        self._audit.emit("job.claim", "success")

        handler = self._registry.get(job.job_type)
        ctx = JobContext(job=job)
        try:
            self._backend.heartbeat(job.job_id)
            if self._run_timeout_seconds is not None:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(handler, ctx)
                    try:
                        future.result(timeout=self._run_timeout_seconds)
                    except FuturesTimeout as exc:
                        self._backend.update_status(job.job_id, JobStatus.TIMEOUT.value)
                        self._audit.emit("job.transition", "failure")
                        self._metrics.inc("jobs.timed_out")
                        raise TimeoutError(f"Job timed out after {self._run_timeout_seconds}s") from exc
            else:
                handler(ctx)
            self._backend.update_status(job.job_id, JobStatus.SUCCEEDED.value)
            self._audit.emit("job.transition", "success")
            self._metrics.inc("jobs.succeeded")
        except Exception as exc:
            if self._fallback_policies is not None:
                decision = self._fallback_policies.apply(self._backend, job, exc)
                self._audit.emit("job.transition", "failure")
                if decision.status == JobStatus.RETRY_WAIT.value:
                    self._metrics.inc("jobs.retry_wait")
                elif decision.status == JobStatus.FAILED.value:
                    self._metrics.inc("jobs.failed")
                if decision.should_raise:
                    raise
                return True

            self._backend.update_status(job.job_id, JobStatus.FAILED.value)
            self._audit.emit("job.transition", "failure")
            self._metrics.inc("jobs.failed")
            raise
        return True

    async def run_once_async(self) -> bool:
        """Async variant of run_once."""
        return await asyncio.to_thread(self.run_once)

    def run_forever(self, poll_interval: float = 1.0, max_loops: int | None = None) -> int:
        """Poll and execute jobs until stopped or max_loops reached."""
        loops = 0
        self._stopped = False
        while not self._stopped:
            self.run_once()
            loops += 1
            if max_loops is not None and loops >= max_loops:
                break
            time.sleep(max(0.0, poll_interval))
        return loops

    async def run_forever_async(self, poll_interval: float = 1.0, max_loops: int | None = None) -> int:
        """Async variant of run_forever."""
        loops = 0
        self._stopped = False
        while not self._stopped:
            await self.run_once_async()
            loops += 1
            if max_loops is not None and loops >= max_loops:
                break
            await asyncio.sleep(max(0.0, poll_interval))
        return loops

    def stop(self) -> None:
        """Signal loop stop for run_forever methods."""
        self._stopped = True
