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

# cloud_dog_jobs — Callback manager
"""Webhook registration, durable persistence, and at-least-once delivery."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import time
from typing import Any, Callable

import httpx
from sqlalchemy import MetaData, create_engine, delete, insert, select, update
from sqlalchemy.engine import Engine

from cloud_dog_jobs.security.validation import validate_callback_url
from cloud_dog_jobs.storage.sqlalchemy.models import build_job_callbacks_table


@dataclass(slots=True)
class RetryPolicy:
    """Delivery retry configuration."""

    max_attempts: int = 3
    base_delay_seconds: float = 0.1
    max_delay_seconds: float = 2.0
    backoff_multiplier: float = 2.0


@dataclass(slots=True)
class CallbackRegistration:
    """Callback endpoint metadata."""

    url: str
    method: str = "POST"
    headers: dict[str, str] = field(default_factory=dict)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    attempt_count: int = 0
    last_error: str | None = None


class CallbackManager:
    """Manage durable callback registrations and delivery semantics."""

    def __init__(
        self,
        *,
        database_url: str | None = None,
        requester: Callable[..., Any] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self._registry: dict[str, CallbackRegistration] = {}
        self._requester = requester
        self._sleep = sleeper or time.sleep
        self._engine: Engine | None = None
        self._table = None
        if database_url:
            self._engine = create_engine(database_url, future=True)
            metadata = MetaData()
            self._table = build_job_callbacks_table(metadata)
            metadata.create_all(self._engine)
            self._load_persisted()

    def _normalise_retry_policy(self, retry_policy: RetryPolicy | dict[str, Any] | None) -> RetryPolicy:
        if retry_policy is None:
            return RetryPolicy()
        if isinstance(retry_policy, RetryPolicy):
            return retry_policy
        return RetryPolicy(
            max_attempts=int(retry_policy.get("max_attempts", 3)),
            base_delay_seconds=float(retry_policy.get("base_delay_seconds", 0.1)),
            max_delay_seconds=float(retry_policy.get("max_delay_seconds", 2.0)),
            backoff_multiplier=float(retry_policy.get("backoff_multiplier", 2.0)),
        )

    def _delay_for_attempt(self, policy: RetryPolicy, attempt: int) -> float:
        raw = policy.base_delay_seconds * (policy.backoff_multiplier ** max(0, attempt - 1))
        return min(policy.max_delay_seconds, raw)

    def _load_persisted(self) -> None:
        if self._engine is None or self._table is None:
            return
        with self._engine.begin() as conn:
            rows = conn.execute(select(self._table)).mappings().all()
        for row in rows:
            retry_payload = row.get("retry_policy") or {}
            if isinstance(retry_payload, str):
                retry_payload = json.loads(retry_payload)
            headers = row.get("headers") or {}
            if isinstance(headers, str):
                headers = json.loads(headers)
            self._registry[str(row["job_id"])] = CallbackRegistration(
                url=str(row["callback_url"]),
                method=str(row["method"]),
                headers={str(k): str(v) for k, v in dict(headers).items()},
                retry_policy=self._normalise_retry_policy(dict(retry_payload)),
                attempt_count=int(row.get("attempt_count") or 0),
                last_error=row.get("last_error"),
            )

    def _persist(self, job_id: str, reg: CallbackRegistration) -> None:
        if self._engine is None or self._table is None:
            return
        now = datetime.now(tz=timezone.utc)
        values = {
            "job_id": job_id,
            "callback_url": reg.url,
            "method": reg.method,
            "headers": reg.headers,
            "retry_policy": {
                "max_attempts": reg.retry_policy.max_attempts,
                "base_delay_seconds": reg.retry_policy.base_delay_seconds,
                "max_delay_seconds": reg.retry_policy.max_delay_seconds,
                "backoff_multiplier": reg.retry_policy.backoff_multiplier,
            },
            "attempt_count": reg.attempt_count,
            "last_error": reg.last_error,
            "created_at": now,
            "updated_at": now,
        }
        with self._engine.begin() as conn:
            existing = conn.execute(select(self._table.c.job_id).where(self._table.c.job_id == job_id)).first()
            if existing is None:
                conn.execute(insert(self._table).values(**values))
            else:
                values.pop("created_at")
                values["updated_at"] = now
                conn.execute(update(self._table).where(self._table.c.job_id == job_id).values(**values))

    def _persist_attempt(self, job_id: str, reg: CallbackRegistration) -> None:
        if self._engine is None or self._table is None:
            return
        with self._engine.begin() as conn:
            conn.execute(
                update(self._table)
                .where(self._table.c.job_id == job_id)
                .values(
                    attempt_count=reg.attempt_count,
                    last_error=reg.last_error,
                    updated_at=datetime.now(tz=timezone.utc),
                )
            )

    def register_callback(
        self,
        job_id: str,
        callback_url: str,
        headers: dict[str, str] | None = None,
        retry_policy: RetryPolicy | dict[str, Any] | None = None,
    ) -> None:
        """Register durable callback configuration for a job."""
        validate_callback_url(callback_url)
        reg = CallbackRegistration(
            url=callback_url,
            headers=dict(headers or {}),
            retry_policy=self._normalise_retry_policy(retry_policy),
        )
        self._registry[job_id] = reg
        self._persist(job_id, reg)

    def register(self, job_id: str, url: str, method: str = "POST", headers: dict[str, str] | None = None) -> None:
        """Backwards-compatible register API used by existing tests."""
        validate_callback_url(url)
        reg = CallbackRegistration(url=url, method=method, headers=dict(headers or {}), retry_policy=RetryPolicy())
        self._registry[job_id] = reg
        self._persist(job_id, reg)

    def unregister(self, job_id: str) -> bool:
        """Remove callback registration."""
        removed = self._registry.pop(job_id, None) is not None
        if self._engine is not None and self._table is not None:
            with self._engine.begin() as conn:
                conn.execute(delete(self._table).where(self._table.c.job_id == job_id))
        return removed

    def trigger(self, job_id: str, payload: dict[str, Any], retries: int = 2) -> bool:
        """Trigger callback with bounded retries (backward-compatible API)."""
        cb = self._registry.get(job_id)
        if cb is None:
            return False
        effective_policy = RetryPolicy(
            max_attempts=max(1, retries + 1),
            base_delay_seconds=cb.retry_policy.base_delay_seconds,
            max_delay_seconds=cb.retry_policy.max_delay_seconds,
            backoff_multiplier=cb.retry_policy.backoff_multiplier,
        )
        return self._deliver(job_id, cb, payload, effective_policy)

    def trigger_job_completion(
        self,
        job_id: str,
        *,
        status: str,
        result_summary: dict[str, Any] | None,
        duration_ms: int,
    ) -> bool:
        """Trigger completion callback with standard payload shape."""
        cb = self._registry.get(job_id)
        if cb is None:
            return False
        payload = {
            "job_id": job_id,
            "status": status,
            "result_summary": dict(result_summary or {}),
            "duration_ms": int(duration_ms),
        }
        return self._deliver(job_id, cb, payload, cb.retry_policy)

    def _deliver(self, job_id: str, cb: CallbackRegistration, payload: dict[str, Any], policy: RetryPolicy) -> bool:
        for attempt in range(1, max(1, policy.max_attempts) + 1):
            cb.attempt_count += 1
            try:
                requester = self._requester or httpx.request
                response = requester(cb.method, cb.url, json=payload, headers=cb.headers, timeout=5.0)
                if 200 <= int(response.status_code) < 300:
                    cb.last_error = None
                    self._persist_attempt(job_id, cb)
                    return True
                cb.last_error = f"HTTP {int(response.status_code)}"
            except Exception as exc:  # pragma: no cover - exception shape is provider-dependent
                cb.last_error = str(exc)
            self._persist_attempt(job_id, cb)
            if attempt < policy.max_attempts:
                self._sleep(self._delay_for_attempt(policy, attempt))
        return False

    def close(self) -> None:
        """Dispose optional persistence resources."""
        if self._engine is not None:
            self._engine.dispose()
