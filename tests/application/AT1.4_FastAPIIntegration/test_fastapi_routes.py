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

from fastapi import APIRouter

from cloud_dog_jobs.admin.service import AdminService
from cloud_dog_jobs.api.fastapi.router import build_router
from cloud_dog_jobs.backends.memory_backend import MemoryQueueBackend
from cloud_dog_jobs.domain.models import JobRequest
from cloud_dog_jobs.queue import JobQueue


def test_fastapi_router_contract_and_endpoints() -> None:
    backend = MemoryQueueBackend()
    queue = JobQueue(backend)
    job_id = queue.submit(JobRequest(job_type="api-test", priority=2))

    admin = AdminService(backend)
    router = build_router(admin)
    assert isinstance(router, APIRouter)

    paths = {route.path for route in router.routes}
    assert "/jobs/queue/status" in paths
    assert "/jobs" in paths
    assert "/jobs/{job_id}" in paths
    assert "/jobs/{job_id}/resubmit" in paths
    assert "/jobs/{job_id}/stop" in paths

    route_map = {(route.path, next(iter(route.methods))): route.endpoint for route in router.routes if route.methods}
    status_payload = route_map[("/jobs/queue/status", "GET")]()
    assert isinstance(status_payload, dict)
    assert status_payload.get("queued", 0) >= 1

    list_payload = route_map[("/jobs", "GET")]()
    assert isinstance(list_payload, list)
    assert any(item["job_id"] == job_id for item in list_payload)

    job_payload = route_map[("/jobs/{job_id}", "GET")](job_id)
    assert job_payload["job_id"] == job_id
    assert job_payload["status"] == "queued"

    resubmit_payload = route_map[("/jobs/{job_id}/resubmit", "POST")](job_id)
    assert isinstance(resubmit_payload["job_id"], str)

    stop_payload = route_map[("/jobs/{job_id}/stop", "POST")](job_id)
    assert stop_payload["cancelled"] is True
