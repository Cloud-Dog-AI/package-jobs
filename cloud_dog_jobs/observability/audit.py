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

# cloud_dog_jobs — Audit event helpers
"""Audit event builder and schema checks."""

from datetime import datetime, timezone


REQUIRED_FIELDS = {
    "timestamp",
    "service",
    "event_type",
    "action",
    "outcome",
    "severity",
    "trace_id",
    "request_id",
    "actor",
    "target",
}


def build_audit_event(action: str, outcome: str, *, service: str = "cloud_dog_jobs") -> dict:
    """Build a minimal PS-40 style audit event."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": service,
        "event_type": "system_function",
        "action": action,
        "outcome": outcome,
        "severity": "INFO",
        "trace_id": "trace-test",
        "request_id": "request-test",
        "actor": {"type": "system", "id": "worker"},
        "target": {"type": "job", "id": "job-test"},
    }


def validate_audit_event_schema(event: dict) -> bool:
    """Return true when all required fields are present."""
    return REQUIRED_FIELDS.issubset(set(event.keys()))


class AuditEmitter:
    """In-memory audit sink used by default in the package baseline."""

    def __init__(self) -> None:
        self.events: list[dict] = []

    def emit(self, action: str, outcome: str, *, service: str = "cloud_dog_jobs") -> dict:
        """Build and store an audit event."""
        event = build_audit_event(action=action, outcome=outcome, service=service)
        self.events.append(event)
        return event
