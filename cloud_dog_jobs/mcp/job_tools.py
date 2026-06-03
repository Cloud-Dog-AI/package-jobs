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

# cloud_dog_jobs — MCP job tools
"""Expose job operations as MCP-compatible tool definitions."""

from __future__ import annotations

from typing import Any

from cloud_dog_jobs.domain.models import JobRequest


def _mcp_error(message: str, *, code: str = "internal_error") -> dict[str, Any]:
    return {"error": {"code": code, "message": message}}


def create_job_tools(job_manager: Any) -> list[dict[str, Any]]:
    """Create MCP tool definitions for create/status/cancel/list operations."""

    def create_handler(arguments: dict[str, Any]) -> dict[str, Any]:
        """Create handler."""
        try:
            request = JobRequest(
                job_type=str(arguments["job_type"]),
                payload=dict(arguments.get("payload") or {}),
                queue_name=str(arguments.get("queue_name") or "default"),
                priority=int(arguments.get("priority") or 0),
            )
            return {"job_id": job_manager.submit(request)}
        except Exception as exc:
            return _mcp_error(str(exc), code="invalid_request")

    def status_handler(arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle status handler."""
        try:
            job = job_manager.get(str(arguments["job_id"]))
            if job is None:
                return _mcp_error("job not found", code="not_found")
            return {
                "job_id": job.job_id,
                "status": job.status.value,
                "job_type": job.job_type,
                "queue_name": job.queue_name,
            }
        except Exception as exc:
            return _mcp_error(str(exc))

    def cancel_handler(arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle cancel handler."""
        try:
            job_id = str(arguments["job_id"])
            return {"job_id": job_id, "cancelled": bool(job_manager.cancel(job_id))}
        except Exception as exc:
            return _mcp_error(str(exc))

    def list_handler(arguments: dict[str, Any]) -> dict[str, Any]:
        """List handler."""
        try:
            limit = int(arguments.get("limit") or 50)
            job_type = arguments.get("job_type")
            jobs = job_manager.list(limit=limit, job_type=job_type)
            return {
                "items": [
                    {
                        "job_id": job.job_id,
                        "job_type": job.job_type,
                        "status": job.status.value,
                        "queue_name": job.queue_name,
                        "priority": job.priority,
                    }
                    for job in jobs
                ]
            }
        except Exception as exc:
            return _mcp_error(str(exc))

    return [
        {
            "name": "jobs.create",
            "description": "Create a new background job.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "job_type": {"type": "string"},
                    "payload": {"type": "object"},
                    "queue_name": {"type": "string"},
                    "priority": {"type": "integer"},
                },
                "required": ["job_type"],
            },
            "handler": create_handler,
        },
        {
            "name": "jobs.status",
            "description": "Get status for a job by identifier.",
            "inputSchema": {
                "type": "object",
                "properties": {"job_id": {"type": "string"}},
                "required": ["job_id"],
            },
            "handler": status_handler,
        },
        {
            "name": "jobs.cancel",
            "description": "Cancel an existing job.",
            "inputSchema": {
                "type": "object",
                "properties": {"job_id": {"type": "string"}},
                "required": ["job_id"],
            },
            "handler": cancel_handler,
        },
        {
            "name": "jobs.list",
            "description": "List jobs in queue order.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "minimum": 1, "maximum": 200},
                    "job_type": {"type": "string"},
                },
                "required": [],
            },
            "handler": list_handler,
        },
    ]
