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

import pytest

from cloud_dog_jobs.backends.sql_backend import SQLQueueBackend
from cloud_dog_jobs.domain.models import JobRequest
from cloud_dog_jobs.queue import JobQueue
from cloud_dog_jobs.worker.worker import Worker


def test_multi_worker_claim(sqlite_database_url: str) -> None:
    backend = SQLQueueBackend(sqlite_database_url)
    try:
        queue = JobQueue(backend)
        job_id = queue.submit(JobRequest(job_type="x"))
        claims = [backend.claim(job_id, f"h{i}", f"w{i}") for i in range(3)]
        assert claims.count(True) == 1
    finally:
        backend.close()


def test_worker_identity_authorisation(sqlite_database_url: str) -> None:
    backend = SQLQueueBackend(sqlite_database_url)
    try:
        queue = JobQueue(backend)
        queue.submit(JobRequest(job_type="auth"))
        worker = Worker(
            backend,
            host_id="h1",
            worker_id="w1",
            identity_authoriser=lambda host, worker_id: False,
        )
        worker.register_handler("auth", lambda ctx: {"ok": True})
        with pytest.raises(PermissionError):
            worker.run_once()
    finally:
        backend.close()
