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

import sqlite3

from cloud_dog_jobs.backends.sql_backend import SQLQueueBackend
from cloud_dog_jobs.domain.models import JobRequest
from cloud_dog_jobs.queue import JobQueue


def test_sql_backend_basic_sqlite() -> None:
    backend = SQLQueueBackend("sqlite+pysqlite:///:memory:")
    try:
        queue = JobQueue(backend)
        job_id = queue.submit(JobRequest(job_type="t"))
        assert queue.get(job_id) is not None
        assert backend.health_check()
    finally:
        backend.close()


def test_sql_backend_adds_claim_index_to_existing_database(tmp_path) -> None:
    database_path = tmp_path / "jobs.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE jobs (
                job_id VARCHAR(64) NOT NULL PRIMARY KEY,
                job_type VARCHAR(128) NOT NULL,
                queue_name VARCHAR(128) NOT NULL,
                payload JSON NOT NULL,
                meta JSON NOT NULL,
                status VARCHAR(32) NOT NULL,
                priority INTEGER NOT NULL,
                claimed_by VARCHAR(256),
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
            """
        )

    backend = SQLQueueBackend(f"sqlite+pysqlite:///{database_path}")
    try:
        with sqlite3.connect(database_path) as connection:
            indexes = {row[1] for row in connection.execute("PRAGMA index_list('jobs')")}
            plan = " ".join(
                str(value)
                for row in connection.execute(
                    """
                    EXPLAIN QUERY PLAN
                    SELECT * FROM jobs
                    WHERE status = 'queued' AND queue_name = 'git-mcp'
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                    """
                )
                for value in row
            )
        assert "ix_jobs_claim_queue" in indexes
        assert "USING INDEX ix_jobs_claim_queue" in plan
    finally:
        backend.close()
