# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# Licensed under the Apache License, Version 2.0

"""Redis-backed cross-service registration for broker discovery."""

from __future__ import annotations

import json
import time
import threading
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class ServiceRecord:
    """A registered service in the broker network."""

    service_id: str
    service_type: str
    endpoint: str
    capabilities: list[str] = field(default_factory=list)
    max_concurrent: int = 10
    registered_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_alive(self, timeout_seconds: float = 120.0) -> bool:
        """Check if the service has sent a heartbeat recently."""
        return (time.time() - self.last_heartbeat) < timeout_seconds

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ServiceRecord:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ServiceRegistry:
    """Cross-service registration and discovery.

    In-memory implementation. For Redis-backed persistence, pass a redis
    client and all operations will use Redis hash + expiry for durability
    across restarts.
    """

    REDIS_KEY = "cdjobs:broker:services"

    def __init__(self, *, redis_client: Any = None, heartbeat_timeout: float = 120.0) -> None:
        self._local: dict[str, ServiceRecord] = {}
        self._lock = threading.Lock()
        self._redis = redis_client
        self._heartbeat_timeout = heartbeat_timeout

    async def register(self, record: ServiceRecord) -> None:
        """Register or update a service."""
        with self._lock:
            self._local[record.service_id] = record
        if self._redis:
            await self._redis.hset(
                self.REDIS_KEY,
                record.service_id,
                json.dumps(record.to_dict(), default=str),
            )

    async def deregister(self, service_id: str) -> None:
        """Remove a service registration."""
        with self._lock:
            self._local.pop(service_id, None)
        if self._redis:
            await self._redis.hdel(self.REDIS_KEY, service_id)

    async def heartbeat(self, service_id: str) -> bool:
        """Update heartbeat timestamp. Returns False if service not found."""
        with self._lock:
            record = self._local.get(service_id)
            if record:
                record.last_heartbeat = time.time()
        if self._redis:
            raw = await self._redis.hget(self.REDIS_KEY, service_id)
            if raw:
                data = json.loads(raw)
                data["last_heartbeat"] = time.time()
                await self._redis.hset(self.REDIS_KEY, service_id, json.dumps(data, default=str))
                return True
        return record is not None

    async def list_services(self, *, service_type: str | None = None, alive_only: bool = True) -> list[ServiceRecord]:
        """List registered services, optionally filtered."""
        if self._redis:
            raw_all = await self._redis.hgetall(self.REDIS_KEY)
            records = [ServiceRecord.from_dict(json.loads(v)) for v in raw_all.values()]
        else:
            with self._lock:
                records = list(self._local.values())

        if alive_only:
            records = [r for r in records if r.is_alive(self._heartbeat_timeout)]
        if service_type:
            records = [r for r in records if r.service_type == service_type]
        return records

    async def get(self, service_id: str) -> ServiceRecord | None:
        """Get a specific service record."""
        if self._redis:
            raw = await self._redis.hget(self.REDIS_KEY, service_id)
            if raw:
                return ServiceRecord.from_dict(json.loads(raw))
            return None
        with self._lock:
            return self._local.get(service_id)
