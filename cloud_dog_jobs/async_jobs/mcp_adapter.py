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

# cloud_dog_jobs — MCP async adapter
"""Adapter for wait=false job submission pattern."""

from __future__ import annotations

from cloud_dog_jobs.domain.models import JobRequest
from cloud_dog_jobs.queue import JobQueue


class MCPAsyncJobAdapter:
    """Submit job requests and poll results using job IDs."""

    def __init__(self, queue: JobQueue) -> None:
        self._queue = queue

    def submit_async(self, tool_name: str, arguments: dict) -> str:
        """Submit async job and return job ID."""
        return self._queue.submit(JobRequest(job_type=tool_name, payload=arguments))

    def get_result(self, job_id: str) -> dict:
        """Return current status payload for a job."""
        job = self._queue.get(job_id)
        if job is None:
            return {"status": "not_found"}
        return {"status": job.status.value, "job_id": job.job_id, "payload": job.payload}
