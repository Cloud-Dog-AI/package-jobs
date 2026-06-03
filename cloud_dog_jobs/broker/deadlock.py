# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# Licensed under the Apache License, Version 2.0

"""Deadlock avoidance hooks for dependency-aware job scheduling."""

from __future__ import annotations

import threading
from typing import Any


class DeadlockGuard:
    """Detects and prevents circular dependencies in job graphs.

    Maintains a wait-for graph: job A waits for job B. If adding an edge
    would create a cycle, the edge is rejected (potential deadlock).
    """

    def __init__(self) -> None:
        self._graph: dict[str, set[str]] = {}  # job_id -> set of job_ids it waits for
        self._lock = threading.Lock()

    def add_dependency(self, job_id: str, depends_on: str) -> bool:
        """Register that job_id depends on depends_on.

        Returns True if the dependency is safe (no cycle).
        Returns False if adding it would create a deadlock cycle.
        """
        with self._lock:
            # Check if adding this edge creates a cycle
            if self._would_cycle(job_id, depends_on):
                return False
            self._graph.setdefault(job_id, set()).add(depends_on)
            return True

    def remove_job(self, job_id: str) -> None:
        """Remove a completed/cancelled job from the wait-for graph."""
        with self._lock:
            self._graph.pop(job_id, None)
            # Also remove from all dependency sets
            for deps in self._graph.values():
                deps.discard(job_id)

    def get_blocked_jobs(self) -> list[str]:
        """Return job IDs that are currently waiting on dependencies."""
        with self._lock:
            return [jid for jid, deps in self._graph.items() if deps]

    def get_dependencies(self, job_id: str) -> set[str]:
        """Return the set of jobs that job_id is waiting for."""
        with self._lock:
            return set(self._graph.get(job_id, set()))

    def yield_to(self, holder_id: str, waiter_id: str) -> bool:
        """Hook for priority inversion avoidance.

        Returns True if the yield is safe (waiter can proceed).
        Returns False if yielding would create a cycle.
        """
        return self.add_dependency(waiter_id, holder_id)

    def _would_cycle(self, from_id: str, to_id: str) -> bool:
        """Check if adding from_id -> to_id creates a cycle (DFS)."""
        if from_id == to_id:
            return True
        visited: set[str] = set()
        stack = [to_id]
        while stack:
            current = stack.pop()
            if current == from_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            stack.extend(self._graph.get(current, set()))
        return False
