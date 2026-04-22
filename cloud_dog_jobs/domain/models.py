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

# cloud_dog_jobs — Domain data models
"""Dataclass-based job models exposed by the package."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from cloud_dog_jobs.domain.enums import JobStatus


@dataclass(slots=True)
class JobRequest:
    """Input payload for creating a new queued job."""

    job_type: str
    queue_name: str = "default"
    payload: dict[str, Any] = field(default_factory=dict)
    priority: int = 0

    app_id: str | None = None
    tenant_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    channel_id: str | None = None

    idempotency_key: str | None = None
    correlation_id: str | None = None

    callback_url: str | None = None
    callback_method: str = "POST"
    callback_headers: dict[str, str] = field(default_factory=dict)

    request_source: str | None = None
    request_ip: str | None = None
    request_auth_method: str | None = None
    request_auth_identity: str | None = None
    request_user_agent: str | None = None


@dataclass(slots=True)
class Job:
    """Persistent representation of a queued job."""

    job_id: str
    job_type: str
    queue_name: str
    payload: dict[str, Any]
    status: JobStatus
    priority: int
    created_at: datetime
    updated_at: datetime

    app_id: str | None = None
    tenant_id: str | None = None
    host_id: str | None = None
    worker_id: str | None = None

    idempotency_key: str | None = None
    correlation_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    channel_id: str | None = None

    callback_url: str | None = None
    callback_method: str = "POST"
    callback_headers: dict[str, str] = field(default_factory=dict)

    request_source: str | None = None
    request_ip: str | None = None
    request_auth_method: str | None = None
    request_auth_identity: str | None = None
    request_user_agent: str | None = None

    claimed_by: str | None = None

    # --- Lifecycle tracking (PS-75 JQ4.3) ---
    attempt: int = 0
    max_attempts: int = 3
    next_run_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    last_heartbeat_at: datetime | None = None
    last_error: dict[str, Any] | None = None
    result_ref: str | None = None
    progress: dict[str, Any] | None = None

    # --- Timeout controls (PS-75 JQ7.1) ---
    run_timeout_ms: int | None = None
    claim_timeout_ms: int | None = None

    # --- Tracing (PS-75 JQ15.1) ---
    trace_id: str | None = None

    # --- Optimistic locking (PS-75 JQ18.1) ---
    version: int = 0

    def to_meta_dict(self) -> dict[str, Any]:
        """Return metadata fields for compact backend storage."""
        return {
            "app_id": self.app_id,
            "tenant_id": self.tenant_id,
            "host_id": self.host_id,
            "worker_id": self.worker_id,
            "idempotency_key": self.idempotency_key,
            "correlation_id": self.correlation_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "channel_id": self.channel_id,
            "callback_url": self.callback_url,
            "callback_method": self.callback_method,
            "callback_headers": self.callback_headers,
            "request_source": self.request_source,
            "request_ip": self.request_ip,
            "request_auth_method": self.request_auth_method,
            "request_auth_identity": self.request_auth_identity,
            "request_user_agent": self.request_user_agent,
        }

    @classmethod
    def from_request(cls, request: JobRequest) -> "Job":
        """Create a queued job from a request."""
        now = datetime.now(tz=timezone.utc)
        return cls(
            job_id=str(uuid4()),
            job_type=request.job_type,
            queue_name=request.queue_name,
            payload=request.payload,
            status=JobStatus.QUEUED,
            priority=request.priority,
            created_at=now,
            updated_at=now,
            app_id=request.app_id,
            tenant_id=request.tenant_id,
            idempotency_key=request.idempotency_key,
            correlation_id=request.correlation_id,
            user_id=request.user_id,
            session_id=request.session_id,
            channel_id=request.channel_id,
            callback_url=request.callback_url,
            callback_method=request.callback_method,
            callback_headers=request.callback_headers,
            request_source=request.request_source,
            request_ip=request.request_ip,
            request_auth_method=request.request_auth_method,
            request_auth_identity=request.request_auth_identity,
            request_user_agent=request.request_user_agent,
        )
