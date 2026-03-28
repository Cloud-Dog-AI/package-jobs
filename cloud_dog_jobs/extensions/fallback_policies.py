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

# cloud_dog_jobs — Explicit fallback policies
"""Per-job-type fallback actions used by worker finalisation logic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

import httpx

from cloud_dog_jobs.backends.base import QueueBackend
from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import Job


class FallbackAction(str, Enum):
    """Represent fallback action."""
    RETRY = "retry"
    DEAD_LETTER = "dead_letter"
    NOTIFY = "notify"
    IGNORE = "ignore"


@dataclass(frozen=True, slots=True)
class FallbackPolicy:
    """Represent fallback policy."""
    action: FallbackAction = FallbackAction.RETRY
    dead_letter_queue: str = "dead_letter"
    notify_url: str | None = None


@dataclass(frozen=True, slots=True)
class FallbackDecision:
    """Represent fallback decision."""
    action: FallbackAction
    status: str
    should_raise: bool
    dead_letter_job_id: str | None = None


class FallbackPolicyManager:
    """Resolve and execute configured fallback policy by job type."""

    def __init__(
        self,
        *,
        policies: dict[str, FallbackPolicy] | None = None,
        notifier: Callable[..., Any] | None = None,
    ) -> None:
        self._policies = dict(policies or {})
        self._notifier = notifier or httpx.request

    def set_policy(self, job_type: str, policy: FallbackPolicy) -> None:
        """Handle set policy."""
        self._policies[job_type] = policy

    def policy_for(self, job_type: str) -> FallbackPolicy:
        """Handle policy for."""
        return self._policies.get(job_type, FallbackPolicy())

    def apply(self, backend: QueueBackend, job: Job, error: Exception) -> FallbackDecision:
        """Handle apply."""
        policy = self.policy_for(job.job_type)

        if policy.action is FallbackAction.RETRY:
            backend.update_status(job.job_id, JobStatus.RETRY_WAIT.value)
            return FallbackDecision(action=policy.action, status=JobStatus.RETRY_WAIT.value, should_raise=True)

        if policy.action is FallbackAction.DEAD_LETTER:
            backend.update_status(job.job_id, JobStatus.FAILED.value)
            now = datetime.now(tz=timezone.utc)
            dead_letter_job = Job(
                job_id=str(uuid4()),
                job_type=job.job_type,
                queue_name=policy.dead_letter_queue,
                payload={"error": str(error), "original_payload": job.payload, "source_job_id": job.job_id},
                status=JobStatus.QUEUED,
                priority=job.priority,
                created_at=now,
                updated_at=now,
                app_id=job.app_id,
                tenant_id=job.tenant_id,
                host_id=job.host_id,
                worker_id=job.worker_id,
                idempotency_key=job.idempotency_key,
                correlation_id=job.correlation_id,
                user_id=job.user_id,
                session_id=job.session_id,
                channel_id=job.channel_id,
            )
            dead_letter_job_id = backend.enqueue(dead_letter_job)
            return FallbackDecision(
                action=policy.action,
                status=JobStatus.FAILED.value,
                should_raise=False,
                dead_letter_job_id=dead_letter_job_id,
            )

        if policy.action is FallbackAction.NOTIFY:
            backend.update_status(job.job_id, JobStatus.FAILED.value)
            if policy.notify_url:
                payload = {
                    "job_id": job.job_id,
                    "job_type": job.job_type,
                    "status": JobStatus.FAILED.value,
                    "error": str(error),
                    "queue_name": job.queue_name,
                }
                self._notifier("POST", policy.notify_url, json=payload, timeout=5.0)
            return FallbackDecision(action=policy.action, status=JobStatus.FAILED.value, should_raise=False)

        backend.update_status(job.job_id, JobStatus.FAILED.value)
        return FallbackDecision(action=policy.action, status=JobStatus.FAILED.value, should_raise=False)
