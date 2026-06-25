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

from cloud_dog_jobs.backends.hybrid_backend import HybridQueueBackend
from cloud_dog_jobs.backends.redis_backend import RedisQueueBackend
from cloud_dog_jobs.backends.sql_backend import SQLQueueBackend
from cloud_dog_jobs.domain.models import JobRequest
from cloud_dog_jobs.queue import JobQueue

VAULT_HINT = "Source env-vault first: set -a; source /opt/iac/Development/cloud-dog-ai/env-vault; set +a"


def test_hybrid_enqueue_and_get(redis_url: str | None, sqlite_database_url: str, env_tier: str) -> None:
    if not redis_url:
        pytest.fail(
            f"Vault credentials not in environment for Redis integration test. {VAULT_HINT}",
            pytrace=False,
        )
    if env_tier not in {"IT", "AT"}:
        return
    redis_backend = RedisQueueBackend(redis_url, key_prefix="cloud_dog_ai_jobs_it_tmp")
    sql_backend = SQLQueueBackend(sqlite_database_url)
    hybrid = HybridQueueBackend(redis_backend, sql_backend)
    redis_backend.clear_prefix()
    try:
        queue = JobQueue(hybrid)
        job_id = queue.submit(JobRequest(job_type="x", priority=4))
        assert queue.get(job_id) is not None
    finally:
        redis_backend.clear_prefix()
        sql_backend.close()
