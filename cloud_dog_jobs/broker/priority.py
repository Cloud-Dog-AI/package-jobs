# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# Licensed under the Apache License, Version 2.0

"""Priority queue with four levels: critical, high, normal, bulk."""

from __future__ import annotations

import enum
import heapq
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class Priority(enum.IntEnum):
    """Job priority levels. Lower numeric value = higher priority."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    BULK = 3


@dataclass(order=True)
class _PriorityItem:
    """Heap-ordered wrapper for queued items."""

    priority: int
    timestamp: float = field(compare=True)
    sequence: int = field(compare=True)
    item: Any = field(compare=False)


class PriorityQueue:
    """Thread-safe priority queue with four levels and dynamic adjustment.

    Items are dequeued in priority order (CRITICAL first, BULK last).
    Within the same priority, FIFO ordering is maintained via timestamp + sequence.
    """

    def __init__(self) -> None:
        self._heap: list[_PriorityItem] = []
        self._lock = threading.Lock()
        self._seq = 0

    def put(self, item: Any, priority: Priority = Priority.NORMAL) -> None:
        """Enqueue an item at the given priority level."""
        with self._lock:
            self._seq += 1
            entry = _PriorityItem(
                priority=priority.value,
                timestamp=time.monotonic(),
                sequence=self._seq,
                item=item,
            )
            heapq.heappush(self._heap, entry)

    def get(self) -> Any | None:
        """Dequeue the highest-priority item. Returns None if empty."""
        with self._lock:
            if not self._heap:
                return None
            return heapq.heappop(self._heap).item

    def peek(self) -> tuple[Any, Priority] | None:
        """Peek at the highest-priority item without removing it."""
        with self._lock:
            if not self._heap:
                return None
            entry = self._heap[0]
            return entry.item, Priority(entry.priority)

    def adjust_priority(self, predicate, new_priority: Priority) -> int:
        """Adjust priority of all items matching predicate. Returns count adjusted.

        predicate: callable(item) -> bool
        """
        with self._lock:
            adjusted = 0
            new_heap = []
            for entry in self._heap:
                if predicate(entry.item):
                    new_heap.append(_PriorityItem(
                        priority=new_priority.value,
                        timestamp=entry.timestamp,
                        sequence=entry.sequence,
                        item=entry.item,
                    ))
                    adjusted += 1
                else:
                    new_heap.append(entry)
            heapq.heapify(new_heap)
            self._heap = new_heap
            return adjusted

    def __len__(self) -> int:
        with self._lock:
            return len(self._heap)

    def count_by_priority(self) -> dict[Priority, int]:
        """Return item counts per priority level."""
        with self._lock:
            counts: dict[Priority, int] = {p: 0 for p in Priority}
            for entry in self._heap:
                counts[Priority(entry.priority)] += 1
            return counts
