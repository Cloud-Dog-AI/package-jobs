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

from __future__ import annotations

from cloud_dog_jobs.backends.memory_backend import MemoryQueueBackend
from cloud_dog_jobs.mcp.job_tools import create_job_tools
from cloud_dog_jobs.mcp.secrets import assert_no_secrets, payload_contains_secret
from cloud_dog_jobs.mcp.validation import validate_callback_url, validate_payload_size
from cloud_dog_jobs.queue import JobQueue


def test_create_job_tools_returns_expected_definitions_and_handlers() -> None:
    queue = JobQueue(MemoryQueueBackend())
    tools = create_job_tools(queue)
    names = [tool["name"] for tool in tools]
    assert names == ["jobs.create", "jobs.status", "jobs.cancel", "jobs.list"]

    create = tools[0]["handler"]
    status = tools[1]["handler"]
    cancel = tools[2]["handler"]

    created = create({"job_type": "demo", "payload": {"x": 1}})
    job_id = created["job_id"]
    assert status({"job_id": job_id})["status"] == "queued"
    assert cancel({"job_id": job_id})["cancelled"] is True


def test_error_mapping_uses_mcp_shape() -> None:
    queue = JobQueue(MemoryQueueBackend())
    tools = create_job_tools(queue)
    status = tools[1]["handler"]
    missing = status({"job_id": "missing"})
    assert missing["error"]["code"] == "not_found"


def test_mcp_validation_and_secret_helpers_delegate_to_security_layer() -> None:
    validate_payload_size({"ok": 1}, max_bytes=1024)
    validate_callback_url("https://example.com/callback")
    assert payload_contains_secret({"api_key": "abc"}) is True
    assert payload_contains_secret({"safe": "value"}) is False
    assert_no_secrets({"safe": {"value": 1}})
