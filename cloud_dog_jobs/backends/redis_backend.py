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
"""Redis backend using sorted-set priority queue and hash storage."""

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


class RedisQueueBackend(QueueBackend):
    """Redis queue backend with key prefix isolation for tests and deployments."""

    def __init__(self, redis_url: str, key_prefix: str = "cloud_dog_ai_jobs") -> None:
        self._client = Redis.from_url(redis_url, decode_responses=True)
        self._prefix = key_prefix
        self._queue_key = f"{key_prefix}:queue"

    def enqueue(self, job: Job) -> str:
        """Handle enqueue."""
        job_key = self._job_key(job.job_id)
        self._client.hset(
            job_key,
            mapping={
                "job_id": job.job_id,
                "job_type": job.job_type,
                "queue_name": job.queue_name,
                "payload": json.dumps(job.payload),
                "meta": json.dumps(job.to_meta_dict()),
                "status": job.status.value,
                "priority": str(job.priority),
                "claimed_by": job.claimed_by or "",
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat(),
            },
        )
        score = (job.priority * 10_000_000_000) - int(time.time() * 1000)
        self._client.zadd(self._queue_key, {job.job_id: score})
        return job.job_id

    def dequeue(self, limit: int, job_type: str | None = None) -> list[Job]:
        """Handle dequeue."""
        ids = self._client.zrevrange(self._queue_key, 0, max(0, limit - 1))
        jobs: list[Job] = []
        for job_id in ids:
            job = self.get(job_id)
            if job and job.status == JobStatus.QUEUED and (job_type is None or job.job_type == job_type):
                jobs.append(job)
        return jobs

    def claim(self, job_id: str, host_id: str, worker_id: str) -> bool:
        """Handle claim."""
        job_key = self._job_key(job_id)
        with self._client.pipeline() as pipe:
            try:
                pipe.watch(job_key)
                status = pipe.hget(job_key, "status")
                if status != JobStatus.QUEUED.value:
                    pipe.unwatch()
                    return False
                raw_meta = pipe.hget(job_key, "meta") or "{}"
                meta = json.loads(raw_meta)
                meta["host_id"] = host_id
                meta["worker_id"] = worker_id
                pipe.multi()
                pipe.hset(
                    job_key,
                    mapping={
                        "status": JobStatus.RUNNING.value,
                        "claimed_by": f"{host_id}:{worker_id}",
                        "meta": json.dumps(meta),
                        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
                    },
                )
                pipe.zrem(self._queue_key, job_id)
                pipe.execute()
                return True
            except RedisError:
                return False

    def release(self, job_id: str) -> bool:
        """Handle release."""
        job = self.get(job_id)
        if job is None:
            return False
        self._client.hset(self._job_key(job_id), mapping={"status": JobStatus.QUEUED.value, "claimed_by": ""})
        score = (job.priority * 10_000_000_000) - int(time.time() * 1000)
        self._client.zadd(self._queue_key, {job_id: score})
        return True

    def heartbeat(self, job_id: str) -> bool:
        """Handle heartbeat."""
        return (
            self._client.hset(self._job_key(job_id), mapping={"updated_at": datetime.now(tz=timezone.utc).isoformat()})
            >= 0
        )

    def get(self, job_id: str) -> Job | None:
        """Handle get."""
        data = self._client.hgetall(self._job_key(job_id))
        if not data:
            return None
        meta = json.loads(data.get("meta") or "{}")
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
        )

    def update_status(self, job_id: str, status: str) -> bool:
        """Update status."""
        result = self._client.hset(
            self._job_key(job_id),
            mapping={"status": status, "updated_at": datetime.now(tz=timezone.utc).isoformat()},
        )
        if status != JobStatus.QUEUED.value:
            self._client.zrem(self._queue_key, job_id)
        return result >= 0

    def get_queue_status(self) -> dict[str, int]:
        """Return queue status."""
        counts: Counter[str] = Counter()
        for key in self._client.scan_iter(f"{self._prefix}:job:*"):
            status = self._client.hget(key, "status")
            if status:
                counts[status] += 1
        return dict(counts)

    def health_check(self) -> bool:
        """Handle health check."""
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

    def _job_key(self, job_id: str) -> str:
        return f"{self._prefix}:job:{job_id}"

    def clear_prefix(self) -> None:
        """Delete keys for this prefix; used by tests to keep the backend tidy."""
        keys = list(self._client.scan_iter(f"{self._prefix}:*"))
        if keys:
            self._client.delete(*keys)
