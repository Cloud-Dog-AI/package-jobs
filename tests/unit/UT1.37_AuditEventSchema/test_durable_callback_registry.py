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

from pathlib import Path

from cloud_dog_jobs.callbacks.manager import CallbackManager


class _Resp:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


def test_register_callback_persists_and_completion_payload_retries(tmp_path: Path) -> None:
    calls: list[dict] = []

    def requester(method, url, json=None, headers=None, timeout=None):
        _ = method
        _ = headers
        _ = timeout
        calls.append({"url": url, "payload": json})
        if len(calls) == 1:
            return _Resp(500)
        return _Resp(200)

    db_url = f"sqlite:///{tmp_path / 'callbacks.db'}"
    mgr = CallbackManager(database_url=db_url, requester=requester, sleeper=lambda _: None)
    mgr.register_callback("job-1", "https://example.com/callback", retry_policy={"max_attempts": 2})

    reloaded = CallbackManager(database_url=db_url, requester=requester, sleeper=lambda _: None)
    ok = reloaded.trigger_job_completion(
        "job-1",
        status="succeeded",
        result_summary={"rows": 10},
        duration_ms=123,
    )

    assert ok is True
    assert len(calls) == 2
    assert calls[-1]["payload"] == {
        "job_id": "job-1",
        "status": "succeeded",
        "result_summary": {"rows": 10},
        "duration_ms": 123,
    }


def test_register_legacy_api_still_works() -> None:
    calls: list[int] = []

    def requester(method, url, json=None, headers=None, timeout=None):
        _ = method
        _ = url
        _ = json
        _ = headers
        _ = timeout
        calls.append(1)
        return _Resp(200)

    mgr = CallbackManager(requester=requester, sleeper=lambda _: None)
    mgr.register("job-legacy", "https://example.com/callback")
    assert mgr.trigger("job-legacy", {"ok": True}, retries=0) is True
    assert len(calls) == 1
