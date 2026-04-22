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

# cloud_dog_jobs — Fan-out manager
"""Parent/child fan-out orchestration and status aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import JobRequest
from cloud_dog_jobs.queue import JobQueue


@dataclass(frozen=True, slots=True)
class ChildJobSpec:
    """Specification for a fan-out child job."""

    job_type: str
    payload: dict[str, Any]
    queue_name: str = "default"
    priority: int = 0


def aggregate_child_statuses(statuses: list[str], *, partial_success_threshold: float | None = None) -> str:
    """Aggregate child statuses into a parent lifecycle status."""
    if not statuses:
        return JobStatus.QUEUED.value

    terminal_success = JobStatus.SUCCEEDED.value
    terminal_failure = JobStatus.FAILED.value
    active_states = {
        JobStatus.QUEUED.value,
        JobStatus.SCHEDULED.value,
        JobStatus.RUNNING.value,
        JobStatus.RETRY_WAIT.value,
        JobStatus.PAUSED.value,
    }

    success_count = sum(1 for state in statuses if state == terminal_success)
    failure_count = sum(1 for state in statuses if state == terminal_failure)
    active_count = sum(1 for state in statuses if state in active_states)

    if partial_success_threshold is None:
        if failure_count > 0:
            return terminal_failure
        if success_count == len(statuses):
            return terminal_success
        if active_count > 0:
            return JobStatus.RUNNING.value
        return JobStatus.QUEUED.value

    threshold = min(max(partial_success_threshold, 0.0), 1.0)
    ratio = success_count / len(statuses)
    if active_count > 0:
        return JobStatus.RUNNING.value
    return terminal_success if ratio >= threshold else terminal_failure


class FanOutManager:
    """Manage parent/child job fan-out patterns."""

    def __init__(self, queue: JobQueue) -> None:
        self._queue = queue
        self._children_by_parent: dict[str, list[str]] = {}

    def create_fan_out(
        self,
        parent_job_id: str,
        child_specs: list[ChildJobSpec | dict[str, Any]],
    ) -> list[str]:
        """Create child jobs linked to a parent job and return child IDs."""
        child_ids: list[str] = []
        for spec in child_specs:
            if isinstance(spec, dict):
                child_spec = ChildJobSpec(
                    job_type=str(spec["job_type"]),
                    payload=dict(spec.get("payload") or {}),
                    queue_name=str(spec.get("queue_name") or "default"),
                    priority=int(spec.get("priority") or 0),
                )
            else:
                child_spec = spec

            payload = dict(child_spec.payload)
            payload["__fanout_parent_job_id"] = parent_job_id
            child_id = self._queue.submit(
                JobRequest(
                    job_type=child_spec.job_type,
                    queue_name=child_spec.queue_name,
                    payload=payload,
                    priority=child_spec.priority,
                )
            )
            child_ids.append(child_id)

        self._children_by_parent[parent_job_id] = child_ids
        return child_ids

    def get_children(self, parent_job_id: str) -> list[str]:
        """Return child job IDs for a parent job."""
        return list(self._children_by_parent.get(parent_job_id, []))

    def aggregate_parent_status(self, parent_job_id: str, *, partial_success_threshold: float | None = None) -> str:
        """Return parent aggregate status based on current child states."""
        child_ids = self._children_by_parent.get(parent_job_id, [])
        statuses: list[str] = []
        for child_id in child_ids:
            child = self._queue.get(child_id)
            if child is None:
                statuses.append(JobStatus.FAILED.value)
            else:
                statuses.append(child.status.value)
        return aggregate_child_statuses(statuses, partial_success_threshold=partial_success_threshold)

    def cancel_parent_and_children(self, parent_job_id: str) -> int:
        """Cancel parent job and all known child jobs."""
        cancelled = 0
        if self._queue.cancel(parent_job_id):
            cancelled += 1
        for child_id in self._children_by_parent.get(parent_job_id, []):
            if self._queue.cancel(child_id):
                cancelled += 1
        return cancelled
