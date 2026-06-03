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

# cloud_dog_jobs — Dependency-aware scheduler (PS-95 §6.3, W28D-305)
"""Track job dependency edges, detect cycles, and determine runnable status."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.errors import DependencyCycleError

# Terminal states that mean a dependency will never succeed
_DEP_FAILED_STATES = frozenset({
    JobStatus.FAILED,
    JobStatus.CANCELLED,
    JobStatus.TIMEOUT,
    JobStatus.TTL_EXPIRED,
    JobStatus.DEAD_LETTERED,
})


class DependencyTracker:
    """In-process dependency graph for job scheduling.

    Maintains a map of job_id → list[dependency_job_ids]. Provides:
    - Submit-time cycle detection (PS-95 §6.3)
    - Runnable-job filtering (deps satisfied check)
    - Blocked-jobs visibility with reasons (PS-95 §6.6)

    Thread-safe via a reentrant lock.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._edges: dict[str, list[str]] = {}  # job_id → [dep_ids]

    def register(self, job_id: str, depends_on: list[str]) -> None:
        """Record dependency edges for a job.

        Call this after cycle detection passes, during submit.
        """
        with self._lock:
            if depends_on:
                self._edges[job_id] = list(depends_on)

    def unregister(self, job_id: str) -> None:
        """Remove tracked edges for a completed/removed job."""
        with self._lock:
            self._edges.pop(job_id, None)

    def detect_cycle(self, job_id: str, depends_on: list[str]) -> bool:
        """Return True if adding job_id → depends_on would create a cycle.

        Algorithm: BFS from each dependency through the existing graph.
        If any path leads back to job_id, a cycle exists.
        """
        if not depends_on:
            return False
        with self._lock:
            visited: set[str] = set()
            stack = list(depends_on)
            while stack:
                current = stack.pop()
                if current == job_id:
                    return True
                if current in visited:
                    continue
                visited.add(current)
                stack.extend(self._edges.get(current, []))
            return False

    def validate_and_register(self, job_id: str, depends_on: list[str]) -> None:
        """Detect cycle and register in one atomic operation.

        Raises DependencyCycleError if adding the edges would create a cycle.
        """
        if not depends_on:
            return
        with self._lock:
            if self.detect_cycle(job_id, depends_on):
                raise DependencyCycleError(
                    f"Adding depends_on={depends_on} for job {job_id} would create a dependency cycle"
                )
            self._edges[job_id] = list(depends_on)

    def get_dependencies(self, job_id: str) -> list[str]:
        """Return the dependency list for a job."""
        with self._lock:
            return list(self._edges.get(job_id, []))

    def is_runnable(
        self,
        job_id: str,
        status_getter: Callable[[str], JobStatus | None],
    ) -> bool:
        """Return True if all dependencies of job_id have SUCCEEDED."""
        with self._lock:
            deps = self._edges.get(job_id, [])
        if not deps:
            return True
        for dep_id in deps:
            status = status_getter(dep_id)
            if status != JobStatus.SUCCEEDED:
                return False
        return True

    def has_failed_dependency(
        self,
        job_id: str,
        status_getter: Callable[[str], JobStatus | None],
    ) -> tuple[bool, list[str]]:
        """Check if any dependency has terminally failed.

        Returns (has_failed, [failed_dep_ids]).
        """
        with self._lock:
            deps = self._edges.get(job_id, [])
        if not deps:
            return False, []
        failed: list[str] = []
        for dep_id in deps:
            status = status_getter(dep_id)
            if status in _DEP_FAILED_STATES:
                failed.append(dep_id)
        return len(failed) > 0, failed

    def blocked_jobs_with_reasons(
        self,
        status_getter: Callable[[str], JobStatus | None],
    ) -> list[dict[str, Any]]:
        """Return all jobs blocked on dependencies with blocking reasons.

        Each entry: {"job_id": str, "blocked_by": [{"dep_id": str, "status": str}]}
        """
        with self._lock:
            edges_snapshot = dict(self._edges)
        result: list[dict[str, Any]] = []
        for job_id, deps in edges_snapshot.items():
            blockers: list[dict[str, str]] = []
            for dep_id in deps:
                dep_status = status_getter(dep_id)
                if dep_status != JobStatus.SUCCEEDED:
                    blockers.append({
                        "dep_id": dep_id,
                        "status": dep_status.value if dep_status else "unknown",
                    })
            if blockers:
                result.append({"job_id": job_id, "blocked_by": blockers})
        return result
