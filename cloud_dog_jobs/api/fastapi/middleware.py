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

# cloud_dog_jobs — FastAPI RBAC middleware
"""Optional RBAC middleware for job admin HTTP routes."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class JobsRBACMiddleware(BaseHTTPMiddleware):
    """Method/path based permission checks for `/jobs` endpoints."""

    def __init__(self, app, permission_checker: Callable[[Request, str], bool]) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._permission_checker = permission_checker

    @staticmethod
    def _required_permission(request: Request) -> str | None:
        path = request.url.path
        if not path.startswith("/jobs"):
            return None
        if request.method == "GET":
            return "jobs.read"
        if request.method == "POST":
            return "jobs.write"
        if request.method == "DELETE":
            return "jobs.delete"
        return "jobs.write"

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        """Handle dispatch."""
        required = self._required_permission(request)
        if required and not self._permission_checker(request, required):
            return JSONResponse(status_code=403, content={"detail": "Forbidden"})
        return await call_next(request)
