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

# cloud_dog_jobs — Testing fixtures
"""Shared test fixture builders for jobs and requests."""

from __future__ import annotations

from datetime import datetime, timezone

from cloud_dog_jobs.domain.models import Job, JobRequest


def sample_job_request(*, job_type: str = "test.echo", queue_name: str = "default", priority: int = 0) -> JobRequest:
    """Handle sample job request."""
    return JobRequest(job_type=job_type, queue_name=queue_name, payload={"value": "ok"}, priority=priority)


def sample_job(*, job_type: str = "test.echo", queue_name: str = "default", priority: int = 0) -> Job:
    """Handle sample job."""
    req = sample_job_request(job_type=job_type, queue_name=queue_name, priority=priority)
    return Job.from_request(req)


def utc_now() -> datetime:
    """Handle utc now."""
    return datetime.now(tz=timezone.utc)
