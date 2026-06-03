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

from cloud_dog_jobs.observability.audit import AuditEmitter, build_audit_event
from cloud_dog_jobs.observability.otel import span


def test_audit_event_emitter_builds_payload() -> None:
    event = build_audit_event("job.submit", "success")
    assert event["action"] == "job.submit"


def test_audit_emitter_records_event() -> None:
    emitter = AuditEmitter()
    event = emitter.emit("job.claim", "success")
    assert event in emitter.events


def test_otel_span_helper_noop_safe() -> None:
    with span("jobs.test"):
        assert True
