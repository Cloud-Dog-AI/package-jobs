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

# cloud_dog_jobs — FastAPI router
"""Minimal FastAPI router for queue status and job lookup."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from cloud_dog_jobs.admin.service import AdminService


def build_router(admin: AdminService) -> APIRouter:
    """Build the jobs admin router with read-only endpoints."""
    router = APIRouter(prefix="/jobs", tags=["jobs"])

    @router.get("/queue/status")
    def queue_status() -> dict[str, int]:
        """Handle queue status."""
        return admin.queue_status()

    @router.get("")
    def list_jobs(limit: int = 100) -> list[dict]:
        """List jobs."""
        jobs = admin.list_jobs(limit=limit)
        return [
            {
                "job_id": job.job_id,
                "job_type": job.job_type,
                "status": job.status.value,
                "priority": job.priority,
            }
            for job in jobs
        ]

    @router.get("/{job_id}")
    def get_job(job_id: str) -> dict:
        """Return job."""
        job = admin.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return {
            "job_id": job.job_id,
            "job_type": job.job_type,
            "status": job.status.value,
            "priority": job.priority,
        }

    @router.delete("/{job_id}")
    def delete_job(job_id: str) -> dict[str, bool]:
        """Delete job."""
        return {"deleted": admin.delete_job(job_id)}

    @router.post("/{job_id}/resubmit")
    def resubmit_job(job_id: str) -> dict[str, str]:
        """Handle resubmit job."""
        new_job_id = admin.resubmit_job(job_id)
        if new_job_id is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"job_id": new_job_id}

    @router.post("/{job_id}/stop")
    def stop_job(job_id: str) -> dict[str, bool]:
        """Handle stop job."""
        return {"cancelled": admin.cancel_job(job_id)}

    return router
