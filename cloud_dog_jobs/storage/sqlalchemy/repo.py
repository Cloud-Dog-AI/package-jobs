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

# cloud_dog_jobs — SQLAlchemy job repository
"""Repository helpers for atomic SQL claim/update operations."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import MetaData, create_engine, select, text, update
from sqlalchemy.engine import Engine, RowMapping

from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import Job
from cloud_dog_jobs.storage.sqlalchemy.models import (
    build_job_call_logs_table,
    build_job_callbacks_table,
    build_job_deliveries_table,
    build_jobs_table,
    row_to_job,
)


class SQLAlchemyJobRepository:
    """Represent s q l alchemy job repository."""
    def __init__(self, database_url: str) -> None:
        self.engine: Engine = create_engine(database_url, future=True)
        self.metadata = MetaData()
        self.jobs = build_jobs_table(self.metadata)
        self.job_call_logs = build_job_call_logs_table(self.metadata)
        self.job_deliveries = build_job_deliveries_table(self.metadata)
        self.job_callbacks = build_job_callbacks_table(self.metadata)
        self.metadata.create_all(self.engine)

    def enqueue(self, job: Job) -> str:
        """Handle enqueue."""
        with self.engine.begin() as conn:
            conn.execute(
                self.jobs.insert().values(
                    job_id=job.job_id,
                    job_type=job.job_type,
                    queue_name=job.queue_name,
                    payload=job.payload,
                    meta=job.to_meta_dict(),
                    status=job.status.value,
                    priority=job.priority,
                    claimed_by=job.claimed_by,
                    created_at=job.created_at,
                    updated_at=job.updated_at,
                )
            )
        return job.job_id

    def queued(self, *, limit: int, job_type: str | None = None) -> list[Job]:
        """Handle queued."""
        stmt = (
            select(self.jobs)
            .where(self.jobs.c.status == JobStatus.QUEUED.value)
            .order_by(self.jobs.c.priority.desc(), self.jobs.c.created_at.asc())
            .limit(limit)
        )
        if job_type:
            stmt = stmt.where(self.jobs.c.job_type == job_type)
        with self.engine.begin() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [row_to_job(dict(r)) for r in rows]

    def get(self, job_id: str) -> Job | None:
        """Handle get."""
        with self.engine.begin() as conn:
            row = conn.execute(select(self.jobs).where(self.jobs.c.job_id == job_id)).mappings().one_or_none()
        if row is None:
            return None
        return row_to_job(dict(row))

    def set_claimed(self, job_id: str, *, host_id: str, worker_id: str) -> bool:
        """Handle set claimed."""
        with self.engine.begin() as conn:
            row = conn.execute(select(self.jobs.c.meta).where(self.jobs.c.job_id == job_id)).mappings().one_or_none()
            if row is None:
                return False
            meta = dict(row["meta"] or {})
            meta["host_id"] = host_id
            meta["worker_id"] = worker_id
            result = conn.execute(
                update(self.jobs)
                .where(self.jobs.c.job_id == job_id)
                .where(self.jobs.c.status == JobStatus.QUEUED.value)
                .values(
                    status=JobStatus.RUNNING.value,
                    claimed_by=f"{host_id}:{worker_id}",
                    meta=meta,
                    updated_at=datetime.now(tz=timezone.utc),
                )
            )
        return result.rowcount == 1

    def set_status(self, job_id: str, status: str, *, clear_claim: bool = True) -> bool:
        """Handle set status."""
        values = {"status": status, "updated_at": datetime.now(tz=timezone.utc)}
        if clear_claim:
            values["claimed_by"] = None
        with self.engine.begin() as conn:
            result = conn.execute(update(self.jobs).where(self.jobs.c.job_id == job_id).values(**values))
        return result.rowcount == 1

    def heartbeat(self, job_id: str) -> bool:
        """Handle heartbeat."""
        with self.engine.begin() as conn:
            result = conn.execute(
                update(self.jobs).where(self.jobs.c.job_id == job_id).values(updated_at=datetime.now(tz=timezone.utc))
            )
        return result.rowcount == 1

    def all_jobs(self) -> list[Job]:
        """Handle all jobs."""
        with self.engine.begin() as conn:
            rows: list[RowMapping] = conn.execute(select(self.jobs)).mappings().all()
        return [row_to_job(dict(r)) for r in rows]

    def queue_status(self) -> dict[str, int]:
        """Handle queue status."""
        with self.engine.begin() as conn:
            rows = conn.execute(select(self.jobs.c.status)).all()
        return dict(Counter(status for (status,) in rows))

    def health_check(self) -> bool:
        """Handle health check."""
        try:
            with self.engine.begin() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def close(self) -> None:
        """Handle close."""
        self.engine.dispose()
