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

"""Integration tests for SQLite/MySQL/PostgreSQL queue behaviour."""

from __future__ import annotations

import pytest

from cloud_dog_jobs.backends.sql_backend import SQLQueueBackend
from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import JobRequest
from cloud_dog_jobs.queue import JobQueue

VAULT_HINT = "Source env-vault first: set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a"


def _exercise_sql_backend(database_url: str) -> None:
    backend = SQLQueueBackend(database_url=database_url)
    try:
        queue = JobQueue(backend)

        first = queue.submit(JobRequest(job_type="ingest", priority=1, payload={"n": 1}))
        second = queue.submit(JobRequest(job_type="ingest", priority=10, payload={"n": 2}))

        queued = queue.list(limit=10)
        assert [job.job_id for job in queued][:2] == [second, first]

        assert backend.claim(second, host_id="hostA", worker_id="worker1") is True
        assert backend.claim(second, host_id="hostB", worker_id="worker2") is False

        claimed = queue.get(second)
        assert claimed is not None
        assert claimed.status == JobStatus.RUNNING

        assert backend.update_status(second, JobStatus.SUCCEEDED.value) is True
        assert queue.get(second).status == JobStatus.SUCCEEDED
    finally:
        backend.close()


def test_sqlite_backend(sqlite_database_url: str) -> None:
    """Run SQL backend checks on SQLite."""
    _exercise_sql_backend(sqlite_database_url)


def test_mysql_backend(mysql_database_url: str | None, env_tier: str) -> None:
    """Run SQL backend checks on MySQL when IT env is selected."""
    if not mysql_database_url:
        pytest.fail(
            f"Vault credentials not in environment for MySQL integration test. {VAULT_HINT}",
            pytrace=False,
        )
    if env_tier not in {"IT", "AT"}:
        return
    _exercise_sql_backend(mysql_database_url)


def test_postgres_backend(postgres_database_url: str | None, env_tier: str) -> None:
    """Run SQL backend checks on PostgreSQL when IT env is selected."""
    if not postgres_database_url:
        pytest.fail(
            f"Vault credentials not in environment for PostgreSQL integration test. {VAULT_HINT}",
            pytrace=False,
        )
    if env_tier not in {"IT", "AT"}:
        return
    _exercise_sql_backend(postgres_database_url)
