# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# Licensed under the Apache License, Version 2.0

"""Resource capacity enforcement for broker-managed workloads."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class ResourceSlot:
    """A named resource with capacity limits."""

    name: str
    total: int
    used: int = 0

    @property
    def available(self) -> int:
        return max(0, self.total - self.used)

    def acquire(self, count: int = 1) -> bool:
        """Try to acquire resources. Returns True if successful."""
        if self.used + count > self.total:
            return False
        self.used += count
        return True

    def release(self, count: int = 1) -> None:
        """Release resources."""
        self.used = max(0, self.used - count)


class CapacityEnforcer:
    """Enforce resource capacity across multiple named resource types.

    Prevents oversubscription of LLM slots, GPU memory, concurrent connections, etc.
    """

    def __init__(self) -> None:
        self._slots: dict[str, ResourceSlot] = {}
        self._lock = threading.Lock()

    def register_resource(self, name: str, total: int) -> None:
        """Register a resource type with its total capacity."""
        with self._lock:
            self._slots[name] = ResourceSlot(name=name, total=total)

    def try_acquire(self, requirements: dict[str, int]) -> bool:
        """Try to acquire all required resources atomically.

        Returns True if ALL resources are available and acquired.
        Returns False if ANY resource is insufficient (no partial acquisition).
        """
        with self._lock:
            # Check all first
            for name, count in requirements.items():
                slot = self._slots.get(name)
                if slot is None or slot.available < count:
                    return False
            # Acquire all
            for name, count in requirements.items():
                self._slots[name].acquire(count)
            return True

    def release(self, requirements: dict[str, int]) -> None:
        """Release previously acquired resources."""
        with self._lock:
            for name, count in requirements.items():
                slot = self._slots.get(name)
                if slot:
                    slot.release(count)

    def available(self, name: str) -> int:
        """Return available capacity for a named resource."""
        with self._lock:
            slot = self._slots.get(name)
            return slot.available if slot else 0

    def stats(self) -> dict[str, dict[str, int]]:
        """Return capacity stats for all resources."""
        with self._lock:
            return {
                name: {"total": s.total, "used": s.used, "available": s.available}
                for name, s in self._slots.items()
            }
