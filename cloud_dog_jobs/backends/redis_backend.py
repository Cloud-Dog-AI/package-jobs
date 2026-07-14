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

# cloud_dog_jobs — Redis/Valkey backend implementation
"""Redis backend using sorted-set priority queue, hash storage, and
lease-based claim semantics compatible with Redis >= 6.2 and Valkey >= 7."""

from __future__ import annotations

import json
import time
from collections import Counter
from datetime import datetime, timezone

from redis import Redis
from redis.exceptions import RedisError

from cloud_dog_jobs.backends.base import QueueBackend
from cloud_dog_jobs.domain.enums import JobStatus
from cloud_dog_jobs.domain.models import Job

# Lua script for atomic claim.  Runs as a single Redis command so no
# other client can interleave between the status check and the state
# mutation.  Compatible with Redis >= 6.2 and Valkey.
_CLAIM_LUA = """\
local job_key   = KEYS[1]
local queue_key = KEYS[2]
local lease_key = KEYS[3]

local cur = redis.call('HGET', job_key, 'status')
if cur ~= ARGV[1] then
    return 0
end

redis.call('HSET', job_key,
    'status',    ARGV[2],
    'claimed_by', ARGV[3],
    'meta',      ARGV[4],
    'updated_at', ARGV[5],
    'started_at', ARGV[5],
    'last_heartbeat_at', ARGV[5])
redis.call('ZREM', queue_key, ARGV[6])
redis.call('SET', lease_key, ARGV[3], 'EX', ARGV[7])
return 1
"""

# Lua script for atomic heartbeat with lease renewal.
_HEARTBEAT_LUA = """\
local job_key   = KEYS[1]
local lease_key = KEYS[2]

local cur = redis.call('HGET', job_key, 'status')
if cur ~= ARGV[1] then
    return 0
end

redis.call('HSET', job_key,
    'updated_at', ARGV[2],
    'last_heartbeat_at', ARGV[2])
redis.call('EXPIRE', lease_key, ARGV[3])
return 1
"""


class RedisQueueBackend(QueueBackend):
    """Redis queue backend with lease-based claim semantics.

    Claim atomicity is enforced via Lua scripts so that concurrent
    workers across multiple processes cannot double-claim the same job.
    Each claimed job gets a lease key with a Redis TTL; if the worker
    dies without heartbeating, ``reap_expired_leases`` releases the job
    back to the queue.
    """

    def __init__(
        self,
        redis_url: str,
        key_prefix: str = "cloud_dog_ai_jobs",
        lease_timeout_seconds: int = 120,
    ) -> None:
        self._client = Redis.from_url(redis_url, decode_responses=True)
        self._prefix = key_prefix
        self._queue_key = f"{key_prefix}:queue"
        self._lease_timeout = lease_timeout_seconds
        self._claim_script = self._client.register_script(_CLAIM_LUA)
        self._heartbeat_script = self._client.register_script(_HEARTBEAT_LUA)

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _job_to_hash(job: Job) -> dict[str, str]:
        """Serialise a Job into a flat dict suitable for HSET."""
        meta = job.to_meta_dict()
        return {
            "job_id": job.job_id,
            "job_type": job.job_type,
            "queue_name": job.queue_name,
            "payload": json.dumps(job.payload),
            "meta": json.dumps(meta),
            "status": job.status.value,
            "priority": str(job.priority),
            "claimed_by": job.claimed_by or "",
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "resources": json.dumps(job.resources),
            "depends_on": json.dumps(job.depends_on),
            "attempt": str(job.attempt),
            "max_attempts": str(job.max_attempts),
            "started_at": job.started_at.isoformat() if job.started_at else "",
            "finished_at": job.finished_at.isoformat() if job.finished_at else "",
            "last_heartbeat_at": (
                job.last_heartbeat_at.isoformat() if job.last_heartbeat_at else ""
            ),
            "last_error": json.dumps(job.last_error) if job.last_error else "",
            "result_ref": job.result_ref or "",
            "progress": json.dumps(job.progress) if job.progress else "",
            "run_timeout_ms": (
                str(job.run_timeout_ms) if job.run_timeout_ms is not None else ""
            ),
            "claim_timeout_ms": (
                str(job.claim_timeout_ms) if job.claim_timeout_ms is not None else ""
            ),
            "trace_id": job.trace_id or "",
            "version": str(job.version),
        }

    @staticmethod
    def _hash_to_job(data: dict[str, str]) -> Job:
        """Deserialise a Redis hash into a Job."""
        meta = json.loads(data.get("meta") or "{}")

        def _opt_dt(key: str) -> datetime | None:
            v = data.get(key, "")
            return datetime.fromisoformat(v) if v else None

        def _opt_int(key: str) -> int | None:
            v = data.get(key, "")
            return int(v) if v else None

        def _opt_json_dict(key: str) -> dict | None:
            v = data.get(key, "")
            if not v:
                return None
            return json.loads(v)

        return Job(
            job_id=data["job_id"],
            job_type=data["job_type"],
            queue_name=data["queue_name"],
            payload=json.loads(data["payload"]),
            status=JobStatus(data["status"]),
            priority=int(data["priority"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            claimed_by=data.get("claimed_by") or None,
            app_id=meta.get("app_id"),
            tenant_id=meta.get("tenant_id"),
            host_id=meta.get("host_id"),
            worker_id=meta.get("worker_id"),
            idempotency_key=meta.get("idempotency_key"),
            correlation_id=meta.get("correlation_id"),
            user_id=meta.get("user_id"),
            session_id=meta.get("session_id"),
            channel_id=meta.get("channel_id"),
            callback_url=meta.get("callback_url"),
            callback_method=meta.get("callback_method", "POST"),
            callback_headers=meta.get("callback_headers") or {},
            request_source=meta.get("request_source"),
            request_ip=meta.get("request_ip"),
            request_auth_method=meta.get("request_auth_method"),
            request_auth_identity=meta.get("request_auth_identity"),
            request_user_agent=meta.get("request_user_agent"),
            resources=json.loads(data.get("resources") or "{}"),
            depends_on=json.loads(data.get("depends_on") or "[]"),
            attempt=int(data.get("attempt") or "0"),
            max_attempts=int(data.get("max_attempts") or "3"),
            started_at=_opt_dt("started_at"),
            finished_at=_opt_dt("finished_at"),
            last_heartbeat_at=_opt_dt("last_heartbeat_at"),
            last_error=_opt_json_dict("last_error"),
            result_ref=data.get("result_ref") or None,
            progress=_opt_json_dict("progress"),
            run_timeout_ms=_opt_int("run_timeout_ms"),
            claim_timeout_ms=_opt_int("claim_timeout_ms"),
            trace_id=data.get("trace_id") or None,
            version=int(data.get("version") or "0"),
        )

    # ------------------------------------------------------------------
    # Key helpers
    # ------------------------------------------------------------------

    def _job_key(self, job_id: str) -> str:
        return f"{self._prefix}:job:{job_id}"

    def _lease_key(self, job_id: str) -> str:
        return f"{self._prefix}:lease:{job_id}"

    # ------------------------------------------------------------------
    # QueueBackend contract
    # ------------------------------------------------------------------

    def enqueue(self, job: Job) -> str:
        """Persist a job hash and add to the priority queue."""
        job_key = self._job_key(job.job_id)
        self._client.hset(job_key, mapping=self._job_to_hash(job))
        score = (job.priority * 10_000_000_000) - int(time.time() * 1000)
        self._client.zadd(self._queue_key, {job.job_id: score})
        return job.job_id

    def dequeue(
        self,
        limit: int,
        job_type: str | None = None,
        queue_name: str | None = None,
    ) -> list[Job]:
        """Return queued jobs eligible for claiming, highest priority first."""
        ids = self._client.zrevrange(self._queue_key, 0, max(0, limit * 3 - 1))
        jobs: list[Job] = []
        for job_id in ids:
            if len(jobs) >= limit:
                break
            job = self.get(job_id)
            if (
                job
                and job.status == JobStatus.QUEUED
                and (job_type is None or job.job_type == job_type)
                and (queue_name is None or job.queue_name == queue_name)
            ):
                jobs.append(job)
        return jobs

    def claim(self, job_id: str, host_id: str, worker_id: str) -> bool:
        """Atomically claim a queued job via Lua script.

        Sets status to RUNNING, records the claimant, removes from the
        queue sorted set, and creates a lease key with TTL.  If any
        other worker has already claimed the job the script returns 0.
        """
        job_key = self._job_key(job_id)
        lease_key = self._lease_key(job_id)
        now_iso = datetime.now(tz=timezone.utc).isoformat()
        claimed_by = f"{host_id}:{worker_id}"

        raw_meta = self._client.hget(job_key, "meta") or "{}"
        meta = json.loads(raw_meta)
        meta["host_id"] = host_id
        meta["worker_id"] = worker_id

        try:
            result = self._claim_script(
                keys=[job_key, self._queue_key, lease_key],
                args=[
                    JobStatus.QUEUED.value,    # ARGV[1]
                    JobStatus.RUNNING.value,   # ARGV[2]
                    claimed_by,                # ARGV[3]
                    json.dumps(meta),          # ARGV[4]
                    now_iso,                   # ARGV[5]
                    job_id,                    # ARGV[6]
                    str(self._lease_timeout),  # ARGV[7]
                ],
            )
            return int(result) == 1
        except RedisError:
            return False

    def release(self, job_id: str) -> bool:
        """Release a claimed job back to queued state and remove its lease."""
        job = self.get(job_id)
        if job is None:
            return False
        self._client.hset(
            self._job_key(job_id),
            mapping={
                "status": JobStatus.QUEUED.value,
                "claimed_by": "",
                "updated_at": datetime.now(tz=timezone.utc).isoformat(),
            },
        )
        score = (job.priority * 10_000_000_000) - int(time.time() * 1000)
        self._client.zadd(self._queue_key, {job_id: score})
        self._client.delete(self._lease_key(job_id))
        return True

    def heartbeat(self, job_id: str) -> bool:
        """Update heartbeat timestamp and renew the lease TTL atomically."""
        job_key = self._job_key(job_id)
        lease_key = self._lease_key(job_id)
        now_iso = datetime.now(tz=timezone.utc).isoformat()
        try:
            result = self._heartbeat_script(
                keys=[job_key, lease_key],
                args=[
                    JobStatus.RUNNING.value,
                    now_iso,
                    str(self._lease_timeout),
                ],
            )
            return int(result) == 1
        except RedisError:
            return False

    def get(self, job_id: str) -> Job | None:
        """Return a single job by identifier."""
        data = self._client.hgetall(self._job_key(job_id))
        if not data:
            return None
        return self._hash_to_job(data)

    def update_status(self, job_id: str, status: str) -> bool:
        """Set job status and update timestamp."""
        job_key = self._job_key(job_id)
        if not self._client.exists(job_key):
            return False
        now_iso = datetime.now(tz=timezone.utc).isoformat()
        mapping: dict[str, str] = {"status": status, "updated_at": now_iso}
        terminal = {
            JobStatus.SUCCEEDED.value,
            JobStatus.FAILED.value,
            JobStatus.CANCELLED.value,
            JobStatus.TTL_EXPIRED.value,
            JobStatus.DEAD_LETTERED.value,
        }
        if status in terminal:
            mapping["finished_at"] = now_iso
        self._client.hset(job_key, mapping=mapping)
        if status != JobStatus.QUEUED.value:
            self._client.zrem(self._queue_key, job_id)
        if status in terminal:
            self._client.delete(self._lease_key(job_id))
        return True

    def get_queue_status(self) -> dict[str, int]:
        """Return counts grouped by status."""
        counts: Counter[str] = Counter()
        for key in self._client.scan_iter(f"{self._prefix}:job:*"):
            status = self._client.hget(key, "status")
            if status:
                counts[status] += 1
        return dict(counts)

    def health_check(self) -> bool:
        """Ping Redis/Valkey."""
        try:
            return self._client.ping()
        except RedisError:
            return False

    def all_jobs(self) -> list[Job]:
        """Return all jobs stored under the current key prefix."""
        jobs: list[Job] = []
        for key in self._client.scan_iter(f"{self._prefix}:job:*"):
            job_id = str(key).rsplit(":", 1)[-1]
            job = self.get(job_id)
            if job is not None:
                jobs.append(job)
        return jobs

    def record_attempt(self, job_id: str, error: str | None = None) -> bool:
        """Increment attempt count and optionally record last error."""
        job_key = self._job_key(job_id)
        if not self._client.exists(job_key):
            return False
        pipe = self._client.pipeline()
        pipe.hincrby(job_key, "attempt", 1)
        updates: dict[str, str] = {
            "updated_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        if error is not None:
            updates["last_error"] = json.dumps({"message": error})
        pipe.hset(job_key, mapping=updates)
        pipe.execute()
        return True

    def update_progress(self, job_id: str, progress: dict) -> bool:
        """Persist progress snapshot."""
        job_key = self._job_key(job_id)
        if not self._client.exists(job_key):
            return False
        self._client.hset(
            job_key,
            mapping={
                "progress": json.dumps(progress),
                "updated_at": datetime.now(tz=timezone.utc).isoformat(),
            },
        )
        return True

    def store_result(self, job_id: str, result: str | dict) -> bool:
        """Store handler result or result reference."""
        job_key = self._job_key(job_id)
        if not self._client.exists(job_key):
            return False
        result_str = json.dumps(result) if isinstance(result, dict) else result
        self._client.hset(
            job_key,
            mapping={
                "result_ref": result_str,
                "updated_at": datetime.now(tz=timezone.utc).isoformat(),
            },
        )
        return True

    # ------------------------------------------------------------------
    # Lease management
    # ------------------------------------------------------------------

    def reap_expired_leases(self) -> list[str]:
        """Find jobs whose lease key has expired and release them.

        Returns the list of job IDs that were released back to QUEUED.
        This should be called periodically by a maintenance loop.
        """
        reaped: list[str] = []
        for key in self._client.scan_iter(f"{self._prefix}:job:*"):
            job_id = str(key).rsplit(":", 1)[-1]
            status = self._client.hget(key, "status")
            if status != JobStatus.RUNNING.value:
                continue
            if self._client.exists(self._lease_key(job_id)):
                continue
            if self.release(job_id):
                reaped.append(job_id)
        return reaped

    def lease_ttl(self, job_id: str) -> int:
        """Return remaining lease TTL in seconds, or -2 if expired/missing."""
        return self._client.ttl(self._lease_key(job_id))

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the Redis connection pool."""
        self._client.close()

    def clear_prefix(self) -> None:
        """Delete keys for this prefix; used by tests to keep the backend tidy."""
        keys = list(self._client.scan_iter(f"{self._prefix}:*"))
        if keys:
            self._client.delete(*keys)
