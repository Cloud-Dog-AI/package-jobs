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

from cloud_dog_jobs.admin.service import AdminService
from cloud_dog_jobs.backends.memory_backend import MemoryQueueBackend
from cloud_dog_jobs.domain.models import JobRequest
from cloud_dog_jobs.queue import JobQueue
from datetime import timedelta


def test_admin_bulk_cancel_loop() -> None:
    backend = MemoryQueueBackend()
    queue = JobQueue(backend)
    ids = [queue.submit(JobRequest(job_type="x")) for _ in range(3)]
    admin = AdminService(backend)
    for job_id in ids:
        assert admin.cancel_job(job_id)
    assert admin.queue_status().get("cancelled", 0) == 3


def test_admin_clear_and_reassign_operations() -> None:
    backend = MemoryQueueBackend()
    queue = JobQueue(backend)
    job_id = queue.submit(JobRequest(job_type="x", queue_name="q1"))
    job = backend.get(job_id)
    job.updated_at = job.updated_at - timedelta(days=2)

    admin = AdminService(backend)
    purged = admin.clear_old_jobs({"max_age_seconds": 3600})
    assert purged >= 1

    assert admin.reassign_queue(job_id, "q2") is True
