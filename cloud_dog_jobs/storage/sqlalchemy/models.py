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

# cloud_dog_jobs — SQLAlchemy storage models
"""Table definitions and row mapping helpers for SQL-backed jobs."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import JSON, Column, DateTime, Integer, MetaData, String, Table

from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import Job


def build_jobs_table(metadata: MetaData) -> Table:
    """Build jobs table."""
    return Table(
        "jobs",
        metadata,
        Column("job_id", String(64), primary_key=True),
        Column("job_type", String(128), nullable=False),
        Column("queue_name", String(128), nullable=False),
        Column("payload", JSON, nullable=False),
        Column("meta", JSON, nullable=False, default=dict),
        Column("status", String(32), nullable=False),
        Column("priority", Integer, nullable=False),
        Column("claimed_by", String(256), nullable=True),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )


def build_job_call_logs_table(metadata: MetaData) -> Table:
    """Build job call logs table."""
    return Table(
        "job_call_logs",
        metadata,
        Column("job_id", String(64), nullable=False),
        Column("provider", String(64), nullable=False),
        Column("request_id", String(128), nullable=False),
        Column("payload", JSON, nullable=False, default=dict),
        Column("created_at", DateTime(timezone=True), nullable=False),
    )


def build_job_deliveries_table(metadata: MetaData) -> Table:
    """Build job deliveries table."""
    return Table(
        "job_deliveries",
        metadata,
        Column("job_id", String(64), nullable=False),
        Column("target", String(512), nullable=False),
        Column("status", String(32), nullable=False),
        Column("response", JSON, nullable=False, default=dict),
        Column("created_at", DateTime(timezone=True), nullable=False),
    )


def build_job_callbacks_table(metadata: MetaData) -> Table:
    """Build job callbacks table."""
    return Table(
        "job_callbacks",
        metadata,
        Column("job_id", String(64), primary_key=True),
        Column("callback_url", String(512), nullable=False),
        Column("method", String(16), nullable=False, default="POST"),
        Column("headers", JSON, nullable=False, default=dict),
        Column("retry_policy", JSON, nullable=False, default=dict),
        Column("attempt_count", Integer, nullable=False, default=0),
        Column("last_error", String(512), nullable=True),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )


def row_to_job(row: dict[str, Any]) -> Job:
    """Handle row to job."""
    payload = row["payload"]
    if isinstance(payload, str):
        payload = json.loads(payload)

    meta = row.get("meta") or {}
    if isinstance(meta, str):
        meta = json.loads(meta)

    return Job(
        job_id=row["job_id"],
        job_type=row["job_type"],
        queue_name=row["queue_name"],
        payload=payload,
        status=JobStatus(row["status"]),
        priority=row["priority"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        claimed_by=row.get("claimed_by"),
        app_id=meta.get("app_id"),
        tenant_id=meta.get("tenant_id"),
        host_id=meta.get("host_id"),
        worker_id=meta.get("worker_id"),
        idempotency_key=meta.get("idempotency_key"),
        correlation_id=meta.get("correlation_id"),
        user_id=meta.get("user_id"),
        session_id=meta.get("session_id"),
        channel_id=meta.get("channel_id"),
        callback_url=meta.get("callback_url"),
        callback_method=meta.get("callback_method", "POST"),
        callback_headers=meta.get("callback_headers") or {},
        request_source=meta.get("request_source"),
        request_ip=meta.get("request_ip"),
        request_auth_method=meta.get("request_auth_method"),
        request_auth_identity=meta.get("request_auth_identity"),
        request_user_agent=meta.get("request_user_agent"),
    )
