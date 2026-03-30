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

from datetime import datetime, timezone

from cloud_dog_jobs.backends.hybrid_backend import HybridQueueBackend
from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import Job


class _Stub:
    def __init__(self):
        self.jobs = {}

    def enqueue(self, job):
        self.jobs[job.job_id] = job
        return job.job_id

    def dequeue(self, limit, job_type=None):
        return list(self.jobs.values())[:limit]

    def claim(self, *a, **k):
        return True

    def release(self, *a, **k):
        return True

    def heartbeat(self, *a, **k):
        return True

    def get(self, job_id):
        return self.jobs.get(job_id)

    def update_status(self, job_id, status):
        return True

    def get_queue_status(self):
        return {"queued": len(self.jobs)}

    def health_check(self):
        return True


def test_hybrid_backend_enqueue() -> None:
    redis_stub = _Stub()
    sql_stub = _Stub()
    hybrid = HybridQueueBackend(redis_stub, sql_stub)
    job = Job("id1", "x", "q", {}, JobStatus.QUEUED, 1, datetime.now(timezone.utc), datetime.now(timezone.utc))
    assert hybrid.enqueue(job) == "id1"
    assert sql_stub.get("id1") is not None
