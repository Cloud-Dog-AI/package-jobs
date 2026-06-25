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

from cloud_dog_jobs.admin.service import AdminService
from cloud_dog_jobs.backends.memory_backend import MemoryQueueBackend
from cloud_dog_jobs.domain.models import JobRequest
from cloud_dog_jobs.security.rbac import check_permission, require_permission


def test_rbac_enforcement_for_required_permission() -> None:
    granted = {"jobs.read", "jobs.cancel"}
    assert check_permission(granted, "jobs.read") is True
    assert check_permission(granted, "jobs.delete") is False

    require_permission(granted, "jobs.cancel")
    with pytest.raises(PermissionError):
        require_permission(granted, "jobs.admin")


def test_admin_service_enforces_permission_checker() -> None:
    backend = MemoryQueueBackend()
    admin = AdminService(backend, permission_checker=lambda perm: perm in {"jobs.submit"})
    job_id = admin.submit_job(JobRequest(job_type="x"))
    assert isinstance(job_id, str)
    with pytest.raises(PermissionError):
        admin.cancel_job(job_id)
