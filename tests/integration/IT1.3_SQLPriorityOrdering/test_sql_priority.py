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

from cloud_dog_jobs.backends.sql_backend import SQLQueueBackend
from cloud_dog_jobs.domain.models import JobRequest
from cloud_dog_jobs.queue import JobQueue


def test_sql_priority_ordering(sqlite_database_url: str) -> None:
    backend = SQLQueueBackend(sqlite_database_url)
    try:
        queue = JobQueue(backend)
        low = queue.submit(JobRequest(job_type="x", priority=1))
        high = queue.submit(JobRequest(job_type="x", priority=9))
        jobs = queue.list(limit=2)
        assert [j.job_id for j in jobs] == [high, low]
    finally:
        backend.close()
